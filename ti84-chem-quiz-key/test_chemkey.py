#!/usr/bin/env python3
"""Run the built CHEMKEY .8xp files in a small, strict TI-BASIC simulator.

Covers only the commands CHEMKEY uses, but follows the calculator's rules for
them: Output( must start on screen and wraps without scrolling, sub( raises
ERR:DOMAIN / ERR:INVALID DIM outside the string, Goto out of an open block is
flagged as a memory leak.

    python3 test_chemkey.py            # run checks
    python3 test_chemkey.py --show     # also print every question screen
"""

import re
import sys
from pathlib import Path

from tivars.types import TIProgram

import build_chemkey as build

HERE = Path(__file__).resolve().parent

LEFT, UP, RIGHT, DOWN, CLEAR, ENTER = 24, 25, 26, 34, 45, 105


class TIError(Exception):
    pass


class SessionOver(Exception):
    pass


TOKEN_RE = re.compile(r"""
    (?P<str>"[^"→\n]*"?)
  | (?P<num>\d+(?:\.\d*)?|\.\d+)
  | (?P<func>length\(|sub\(|min\(|max\(|int\(|fPart\()
  | (?P<name>Str9|getKey|Ans)
  | (?P<logic>\ and\ |\ or\ )
  | (?P<op>[-+*/=≠<>≤≥⁻(){},])
  | (?P<var>[A-Zθ])
""", re.VERBOSE)


def lex(text):
    pos, out = 0, []
    while pos < len(text):
        m = TOKEN_RE.match(text, pos)
        if not m:
            raise TIError(f"ERR:SYNTAX near {text[pos:pos + 15]!r}")
        kind = m.lastgroup
        value = m.group(kind)
        if kind == "str":
            value = value[1:-1] if value.endswith('"') and len(value) > 1 else value[1:]
        elif kind == "logic":
            value = value.strip()
        out.append((kind, value))
        pos = m.end()
    return out


class Expr:
    """Precedence climbing over TI-84 operator levels."""

    def __init__(self, calc, tokens):
        self.calc, self.toks, self.i = calc, tokens, 0

    def peek(self):
        return self.toks[self.i] if self.i < len(self.toks) else (None, None)

    def take(self, value=None):
        tok = self.peek()
        if value is not None and tok[1] != value:
            raise TIError(f"ERR:SYNTAX expected {value!r}, got {tok[1]!r}")
        self.i += 1
        return tok

    def parse(self):
        value = self.p_or()
        if self.i != len(self.toks):
            raise TIError(f"ERR:SYNTAX trailing {self.toks[self.i:]}")
        return value

    def p_or(self):
        v = self.p_and()
        while self.peek() == ("logic", "or"):
            self.take()
            v = bool_op(v, self.p_and(), lambda a, b: a or b)
        return v

    def p_and(self):
        v = self.p_rel()
        while self.peek() == ("logic", "and"):
            self.take()
            v = bool_op(v, self.p_rel(), lambda a, b: a and b)
        return v

    def p_rel(self):
        v = self.p_add()
        ops = {"=": lambda a, b: a == b, "≠": lambda a, b: a != b,
               "<": lambda a, b: a < b, ">": lambda a, b: a > b,
               "≤": lambda a, b: a <= b, "≥": lambda a, b: a >= b}
        while self.peek()[0] == "op" and self.peek()[1] in ops:
            fn = ops[self.take()[1]]
            v = bool_op(v, self.p_add(), fn)
        return v

    def p_add(self):
        v = self.p_mul()
        while self.peek() in (("op", "+"), ("op", "-")):
            op = self.take()[1]
            rhs = self.p_mul()
            if op == "+" and isinstance(v, str):
                if not isinstance(rhs, str):
                    raise TIError("ERR:DATA TYPE")
                v = v + rhs
            else:
                v = arith(v, rhs, (lambda a, b: a + b) if op == "+" else (lambda a, b: a - b))
        return v

    def starts_primary(self):
        kind, value = self.peek()
        return kind in ("num", "func", "name", "var", "str") or value in ("(", "{")

    def p_mul(self):
        v = self.p_neg()
        while True:
            if self.peek() in (("op", "*"), ("op", "/")):
                op = self.take()[1]
                rhs = self.p_neg()
            elif self.starts_primary():   # implicit multiplication
                op, rhs = "*", self.p_neg()
            else:
                return v
            if op == "/" and rhs == 0:
                raise TIError("ERR:DIVIDE BY 0")
            v = arith(v, rhs, (lambda a, b: a * b) if op == "*" else (lambda a, b: a / b))

    def p_neg(self):
        if self.peek() == ("op", "⁻"):
            self.take()
            return arith(self.p_neg(), -1, lambda a, b: a * b)
        return self.primary()

    def args(self):
        out = [self.p_or()]
        while self.peek() == ("op", ","):
            self.take()
            out.append(self.p_or())
        if self.peek() == ("op", ")"):
            self.take()
        return out

    def primary(self):
        kind, value = self.take()
        if kind == "num":
            return float(value)
        if kind == "str":
            return value
        if kind == "var":
            return self.calc.vars.get(value, 0.0)
        if kind == "name":
            if value == "getKey":
                return float(self.calc.get_key())
            if value == "Ans":
                return self.calc.ans
            if value not in self.calc.vars:
                raise TIError("ERR:UNDEFINED")
            return self.calc.vars[value]
        if value == "(":
            v = self.p_or()
            if self.peek() == ("op", ")"):
                self.take()
            return v
        if value == "{":
            items = [self.p_or()]
            while self.peek() == ("op", ","):
                self.take()
                items.append(self.p_or())
            self.take("}")
            return items
        if kind == "func":
            return call(value, self.args())
        raise TIError(f"ERR:SYNTAX unexpected {value!r}")


def arith(a, b, fn):
    if isinstance(a, str) or isinstance(b, str):
        raise TIError("ERR:DATA TYPE")
    if isinstance(a, list) or isinstance(b, list):
        al = a if isinstance(a, list) else [a] * len(b)
        bl = b if isinstance(b, list) else [b] * len(a)
        if len(al) != len(bl):
            raise TIError("ERR:DIM MISMATCH")
        return [float(fn(x, y)) for x, y in zip(al, bl)]
    return float(fn(a, b))


def bool_op(a, b, fn):
    if isinstance(a, str) or isinstance(b, str):
        # TI compares strings only with = and ≠; CHEMKEY never does.
        raise TIError("ERR:DATA TYPE")
    return arith(a, b, lambda x, y: 1.0 if fn(x, y) else 0.0)


def need_int(x, lo=None):
    if isinstance(x, (str, list)) or x != int(x) or (lo is not None and x < lo):
        raise TIError("ERR:DOMAIN")
    return int(x)


def call(name, args):
    if name == "length(":
        (s,) = args
        if not isinstance(s, str):
            raise TIError("ERR:DATA TYPE")
        return float(len(s))
    if name == "sub(":
        s, start, count = args
        start, count = need_int(start, 1), need_int(count, 1)
        if start + count - 1 > len(s):
            raise TIError("ERR:INVALID DIM")
        return s[start - 1:start - 1 + count]
    if name in ("min(", "max("):
        values = args[0] if len(args) == 1 and isinstance(args[0], list) else args
        if any(isinstance(v, (str, list)) for v in values):
            raise TIError("ERR:DATA TYPE")
        return float(min(values) if name == "min(" else max(values))
    if name == "int(":
        (x,) = args
        import math
        return float(math.floor(x))
    if name == "fPart(":
        (x,) = args
        return float(x - int(x))
    raise TIError(f"ERR:SYNTAX {name}")


def split_args(text):
    """Split a comma list at top level (outside strings and brackets)."""
    parts, depth, cur, in_str = [], 0, "", False
    for ch in text:
        if ch == '"':
            in_str = not in_str
        elif not in_str and ch in "({":
            depth += 1
        elif not in_str and ch in ")}":
            depth -= 1
        if ch == "," and depth == 0 and not in_str:
            parts.append(cur)
            cur = ""
        else:
            cur += ch
    parts.append(cur)
    return parts


class Calc:
    def __init__(self, layout, source, keys, menu_choices, inputs):
        self.layout = layout
        self.w, self.h = layout.width, layout.height
        self.lines = source.split("\n")
        self.keys = list(keys)
        self.menu_choices = list(menu_choices)
        self.inputs = list(inputs)
        self.vars = {}
        self.ans = 0.0
        self.blocks = []
        self.screens = []          # snapshot each time a key is read
        self.idle_polls = 0
        self.clear()

    # ---- home screen -------------------------------------------------
    def clear(self):
        self.screen = [[" "] * self.w for _ in range(self.h)]
        self.cursor_row = 0

    def snapshot(self):
        return ["".join(row) for row in self.screen]

    def output(self, row, col, value):
        row, col = need_int(row), need_int(col)
        if not (1 <= row <= self.h and 1 <= col <= self.w):
            raise TIError("ERR:DOMAIN")
        text = value if isinstance(value, str) else format_num(value)
        r, c = row - 1, col - 1
        for ch in text:
            if r >= self.h:
                break                       # Output( never scrolls
            self.screen[r][c] = ch
            c += 1
            if c == self.w:
                r, c = r + 1, 0

    def disp_line(self, text):
        if self.cursor_row == self.h:
            self.screen = self.screen[1:] + [[" "] * self.w]
            self.cursor_row -= 1
        line = text[:self.w]
        self.screen[self.cursor_row] = list(line.ljust(self.w))
        self.cursor_row += 1

    # ---- input -------------------------------------------------------
    def get_key(self):
        # Report "no key" a couple of times between presses, like a real loop.
        if self.idle_polls < 2:
            self.idle_polls += 1
            return 0
        if not self.keys:
            raise SessionOver
        self.idle_polls = 0
        self.screens.append(self.snapshot())
        return self.keys.pop(0)

    # ---- interpreter -------------------------------------------------
    def eval(self, text):
        return Expr(self, lex(text)).parse()

    def find_label(self, name):
        for i, line in enumerate(self.lines):
            if line == f"Lbl {name}":
                return i
        raise TIError(f"ERR:LABEL {name}")

    def goto(self, name):
        if self.blocks:
            raise TIError("memory leak: Goto out of an open block")
        return self.find_label(name) + 1

    def run(self, max_steps=200000):
        pc, steps = 0, 0
        try:
            while pc < len(self.lines):
                steps += 1
                if steps > max_steps:
                    raise TIError("runaway program")
                pc = self.step(pc)
        except SessionOver:
            return "session over"
        return "finished"

    def step(self, pc):
        line = self.lines[pc]
        if line in ("Full",) or line.startswith("Lbl "):
            return pc + 1
        if line == "ClrHome":
            self.clear()
            return pc + 1
        if line.startswith("Goto "):
            return self.goto(line[5:])
        if line.startswith("If "):
            cond = self.eval(line[3:])
            if isinstance(cond, (str, list)):
                raise TIError("ERR:DATA TYPE")
            return pc + 1 if cond else pc + 2
        if line.startswith("Repeat "):
            self.blocks.append(("Repeat", pc, line[7:]))
            return pc + 1
        if line == "End":
            if not self.blocks:
                raise TIError("ERR:SYNTAX End without block")
            kind, start, cond = self.blocks[-1]
            value = self.eval(cond)
            if isinstance(value, (str, list)):
                raise TIError("ERR:DATA TYPE")
            if value:
                self.blocks.pop()
                return pc + 1
            return start + 1
        if line.startswith("Menu("):
            parts = split_args(strip_call(line, "Menu("))
            items = parts[1:]
            if len(items) % 2:
                raise TIError("ERR:ARGUMENT")
            labels = items[1::2]
            names = [self.eval(t) for t in items[0::2]]
            if len(names) > 7 or any(len(n) > self.w - 2 for n in names):
                raise TIError("Menu( item too long or too many items")
            if not self.menu_choices:
                raise SessionOver
            choice = self.menu_choices.pop(0)
            return self.goto(labels[choice])
        if line.startswith("Disp "):
            self.disp_line(self.eval(line[5:]))
            return pc + 1
        if line.startswith("Input "):
            prompt, var = split_args(line[6:])
            if not self.inputs:
                raise SessionOver
            value = self.inputs.pop(0)
            self.disp_line(self.eval(prompt) + format_num(value))
            self.vars[var] = float(value)
            return pc + 1
        if line.startswith("Output("):
            args = [self.eval(a) for a in split_args(strip_call(line, "Output("))]
            if len(args) != 3:
                raise TIError("ERR:ARGUMENT")
            self.output(*args)
            return pc + 1
        if line.startswith("DelVar "):
            self.vars.pop(line[7:], None)
            return pc + 1
        if "→" in line:
            expr, var = line.rsplit("→", 1)
            value = self.eval(expr)
            if var == "Str9" and not isinstance(value, str):
                raise TIError("ERR:DATA TYPE")
            if var != "Str9" and not isinstance(value, float):
                raise TIError("ERR:DATA TYPE")
            self.vars[var] = value
            self.ans = value
            return pc + 1
        self.ans = self.eval(line)
        return pc + 1


def strip_call(line, name):
    """Arguments of a command line, minus its one optional closing paren."""
    body = line[len(name):]
    return body[:-1] if body.endswith(")") else body


def format_num(x):
    return str(int(x)) if x == int(x) else str(x)


def load_8xp(layout):
    program = TIProgram.open(str(HERE / f"{layout.stem}.8xp"))
    return program.string(model=layout.model).replace("\\'", "'")


def run(layout, keys=(), menu=(), inputs=()):
    calc = Calc(layout, load_8xp(layout), keys, menu, inputs)
    status = calc.run()
    return calc, status


def show(screen):
    border = "+" + "-" * len(screen[0]) + "+"
    return "\n".join([border] + [f"|{row}|" for row in screen] + [border])


def is_q(screen, n):
    """True if the screen is showing question n."""
    return re.match(rf"Question {n}(?!\d)", screen[0]) is not None


def pages_of(layout, n):
    text = build.question_text(n, layout)
    return -(-(len(text) - layout.width) // layout.page_chars)


def check_layout(layout, verbose):
    W = layout.width
    failures = []

    def expect(cond, message):
        if not cond:
            failures.append(message)

    # Browse every page of every question with ENTER, then wrap back to Q1.
    total_pages = sum(pages_of(layout, n) for n in range(1, 31))
    calc, status = run(layout, keys=[ENTER] * total_pages + [CLEAR], menu=[1])
    expect(status == "session over", f"browse ended with {status}")
    expect(len(calc.screens) == total_pages + 1, "wrong number of screens")

    i = 0
    for n in range(1, 31):
        letter, answer, _ = build.QUESTIONS[n - 1]
        k = pages_of(layout, n)
        for p in range(1, k + 1):
            screen = calc.screens[i]
            i += 1
            expect(is_q(screen, n), f"Q{n} p{p} header: {screen[0]!r}")
            expect(f"({letter})" in screen[0], f"Q{n} header lacks letter")
            expect(screen[-1].startswith("<PREV") and screen[-1].endswith("NEXT>"),
                   f"Q{n} footer: {screen[-1]!r}")
            if k > 1:
                expect(f"{p}/{k}" in screen[-1], f"Q{n} p{p} page marker: {screen[-1]!r}")
            else:
                expect("/" not in screen[-1], f"Q{n} unexpected page marker")
            if p == 1:
                expect(screen[1].startswith(f"({letter}) "), f"Q{n} answer row: {screen[1]!r}")
            if layout.key == "84PLUS":
                expect(screen[0][-1] == " ", f"Q{n} uses the run-indicator cell")
            if verbose:
                print(show(screen))
    # After Q30's last page, ENTER wraps to Q1.
    expect(is_q(calc.screens[-1], 1), "no wrap from 30 to 1")

    # Every word of every explanation appears on some page, in order.
    for n in range(1, 31):
        _, answer, explanation = build.QUESTIONS[n - 1]
        calc, _ = run(layout, keys=[DOWN] * 9 + [CLEAR], menu=[0], inputs=[n])
        seen = []
        for screen in calc.screens:
            for row in screen[1:-1]:
                seen += row.split()
        words = f"{answer} {explanation}".split()
        it = iter(seen)
        expect(all(word in it for word in words), f"Q{n}: text missing from screens")

    # LEFT from Q1 wraps to Q30; RIGHT from Q30 wraps to Q1; UP on page 1 stays.
    calc, _ = run(layout, keys=[LEFT, RIGHT, UP, CLEAR], menu=[1])
    expect(is_q(calc.screens[1], 30), "LEFT from 1 should go to 30")
    expect(is_q(calc.screens[2], 1), "RIGHT from 30 should go to 1")
    expect(is_q(calc.screens[3], 1), "UP on page 1 should stay")

    # A multi-page question: DOWN, UP, then RIGHT resets to page 1 of the next.
    multi = [n for n in range(1, 31) if pages_of(layout, n) > 1]
    if multi:
        n = multi[0]
        calc, _ = run(layout, keys=[DOWN, UP, RIGHT, CLEAR], menu=[0], inputs=[n])
        k = pages_of(layout, n)
        expect(f"1/{k}" in calc.screens[0][-1], "multi-page start")
        expect(f"2/{k}" in calc.screens[1][-1], "DOWN should turn the page")
        expect(f"1/{k}" in calc.screens[2][-1], "UP should turn back")
        expect(is_q(calc.screens[3], n + 1), "RIGHT goes to next")

    # Bad question numbers are rejected and re-asked.
    calc, _ = run(layout, keys=[CLEAR], menu=[0], inputs=[0, 31, 2.5, 17])
    expect(is_q(calc.screens[0], 17), "GO TO QUESTION validation")

    # Answer list, help, quit.
    calc, status = run(layout, keys=[ENTER, ENTER], menu=[2, 3, 4])
    expect(status == "finished", f"quit ended with {status}")
    grid, help_screen = calc.screens
    letters = "".join(q[0] for q in build.QUESTIONS)
    cells = re.findall(r"(\d+) ?([A-D])", " ".join(grid))
    expect([int(n) for n, _ in cells] == list(range(1, 31)), "answer list numbering")
    expect("".join(l for _, l in cells) == letters, "answer list letters")
    expect(help_screen[0].startswith("HOW TO USE"), "help screen")
    expect("Str9" not in calc.vars, "Str9 should be deleted on quit")
    if verbose:
        print(show(grid))
        print(show(help_screen))

    return failures


def main():
    verbose = "--show" in sys.argv
    ok = True
    for layout in build.LAYOUTS:
        print(f"== {layout.stem} ({layout.width}x{layout.height}) ==")
        try:
            failures = check_layout(layout, verbose)
        except TIError as e:
            failures = [f"calculator error: {e}"]
        for f in failures:
            print("FAIL:", f)
        print("all checks passed" if not failures else f"{len(failures)} failure(s)")
        ok &= not failures
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
