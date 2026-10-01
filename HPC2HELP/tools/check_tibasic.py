#!/usr/bin/env python3
"""
Static checker + TI-84 Plus home-screen simulator for HPC2HELP.txt.

Static checks
  * every line parses as a supported TI-BASIC statement (Menu(, Disp, Output(,
    Input, Pause, ClrHome, Lbl, Goto, If/Then/Else/End, Stop, Float, Normal,
    expr→var); expressions use only real variables A-Z and the functions
    abs( fPart( iPart( int( gcd( min( max( not( with explicit * and closed ( )
  * labels: 1-2 chars, unique, every Goto/Menu target exists, every Lbl is used
  * Menu(: <= 7 options, title <= 16 chars, option text <= 14 chars
  * strings: keypad characters only, <= 16 chars wide
  * no Goto / Menu( / Lbl inside an If-Then / Else block (avoids the TI-BASIC
    memory leak and jumping into a block)
  * control flow: every line is reachable, nothing falls off the end, and
    every loop passes through a Menu(, Pause or Input (no infinite loops)

Simulation (exact rational arithmetic, 16 x 8 screen)
  * walks every option of every menu, rendering every page
  * no Disp scrolls a page, no text wraps, row 1 column 16 stays free for the
    TI-84 Plus busy indicator, and pages that show fractions keep spare rows
  * ERR: conditions (divide by 0, gcd( domain, Output( domain ...) are errors
  * a variable read before this run assigned it is an error
  * scripted tests: the sample validations from the assignment
  * exhaustive power-classifier test against an independent numeric oracle,
    randomized transform-tool tests against exact Fraction arithmetic
  * every line of the program is executed by at least one run

Writes SCREENS.txt (every page and menu as it appears on a TI-84 Plus).
Exit code 0 only if everything passes.
"""

import itertools
import math
import random
import re
import sys
from collections import deque
from fractions import Fraction
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE.parent / "HPC2HELP.txt"
SCREENS = HERE.parent / "SCREENS.txt" if len(sys.argv) <= 1 else SRC.with_suffix(".screens.txt")
ROWS, COLS = 8, 16  # TI-84 Plus home screen; the CE (10 x 26) is roomier

FAILURES = []


def fail(msg):
    FAILURES.append(msg)


# ----------------------------------------------------------------------------
# text helpers
# ----------------------------------------------------------------------------

def cells(s):
    """Split display text into screen cells ('⁻¹' is one character on a TI)."""
    out, i = [], 0
    while i < len(s):
        if s.startswith("⁻¹", i):
            out.append("⁻¹")
            i += 2
        else:
            out.append(s[i])
            i += 1
    return out


def width(s):
    return len(cells(s))


ALLOWED_STR = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 (),.+-*/^=<>≤≥≠?[]²³√") | {"⁻¹"}


def check_string(s, where):
    for c in cells(s):
        if c not in ALLOWED_STR:
            fail(f"{where}: character {c!r} in a string is not keypad-typeable / not allowed")
    if "√" in s and not re.fullmatch(r"(?:[^√]|(?<!³)√\(|³√\()*", s):
        fail(f"{where}: √ must be followed by '(' (the √( token)")
    if re.search(r"\[[A-J]\]", s):
        fail(f"{where}: '[A]'..'[J]' would be a matrix token")


# ----------------------------------------------------------------------------
# expression parser / evaluator
# ----------------------------------------------------------------------------

FUNCS = ["fPart(", "iPart(", "abs(", "int(", "gcd(", "min(", "max(", "not("]
LOGIC = [" and ", " xor ", " or "]
SINGLE = "≠≤≥=<>+-*/^⁻(),"


class TIError(Exception):
    pass


def lex(expr, where):
    toks, i = [], 0
    while i < len(expr):
        for w in LOGIC + FUNCS:
            if expr.startswith(w, i):
                toks.append(w.strip())
                i += len(w)
                break
        else:
            c = expr[i]
            m = re.match(r"\d+(?:\.\d+)?|\.\d+", expr[i:])
            if m:
                toks.append(("num", m.group()))
                i += len(m.group())
            elif c in "ABCDEFGHIJKLMNOPQRSTUVWXYZθ":
                toks.append(("var", c))
                i += 1
            elif c in SINGLE:
                toks.append(c)
                i += 1
            else:
                raise SyntaxError(f"{where}: cannot lex {expr[i:]!r}")
    return toks


class Parser:
    def __init__(self, toks, where):
        self.t, self.i, self.where = toks, 0, where

    def peek(self):
        return self.t[self.i] if self.i < len(self.t) else None

    def take(self, want=None):
        tok = self.peek()
        if want is not None and tok != want:
            raise SyntaxError(f"{self.where}: expected {want!r}, got {tok!r}")
        self.i += 1
        return tok

    def parse(self):
        node = self.p_or()
        if self.peek() is not None:
            raise SyntaxError(f"{self.where}: unexpected {self.peek()!r} (implicit multiplication or junk)")
        return node

    def p_or(self):
        node = self.p_and()
        while self.peek() in ("or", "xor"):
            node = (self.take(), node, self.p_and())
        return node

    def p_and(self):
        node = self.p_rel()
        while self.peek() == "and":
            node = (self.take(), node, self.p_rel())
        return node

    def p_rel(self):
        node = self.p_add()
        while self.peek() in ("=", "≠", "<", ">", "≤", "≥"):
            node = (self.take(), node, self.p_add())
        return node

    def p_add(self):
        node = self.p_mul()
        while self.peek() in ("+", "-"):
            node = (self.take(), node, self.p_mul())
        return node

    def p_mul(self):
        node = self.p_neg()
        while self.peek() in ("*", "/"):
            node = (self.take(), node, self.p_neg())
        return node

    def p_neg(self):
        if self.peek() == "⁻":
            self.take()
            return ("neg", self.p_neg())
        if self.peek() == "-":
            raise SyntaxError(f"{self.where}: '-' (subtract) used as a negative sign; TI needs (-)")
        return self.p_pow()

    def p_pow(self):
        node = self.p_atom()
        while self.peek() == "^":
            self.take()
            negs = 0
            while self.peek() == "⁻":
                self.take()
                negs += 1
            rhs = self.p_atom()
            for _ in range(negs):
                rhs = ("neg", rhs)
            node = ("^", node, rhs)
        return node

    def p_atom(self):
        tok = self.take()
        if isinstance(tok, tuple):
            return tok
        if tok == "(":
            node = self.p_or()
            self.take(")")
            return node
        if tok in [f.strip() for f in FUNCS]:
            args = [self.p_or()]
            while self.peek() == ",":
                self.take()
                args.append(self.p_or())
            self.take(")")
            return ("call", tok, args)
        raise SyntaxError(f"{self.where}: unexpected token {tok!r}")


def parse_expr(text, where):
    return Parser(lex(text, where), where).parse()


def expr_vars(node):
    if node[0] == "var":
        return {node[1]}
    if node[0] == "num":
        return set()
    if node[0] == "call":
        return set().union(*(expr_vars(a) for a in node[2]))
    return set().union(*(expr_vars(a) for a in node[1:]))


ARITY = {"abs(": 1, "fPart(": 1, "iPart(": 1, "int(": 1, "not(": 1, "gcd(": 2, "min(": 2, "max(": 2}


def check_arity(node, where):
    if node[0] == "call":
        if len(node[2]) != ARITY[node[1]]:
            fail(f"{where}: {node[1]} takes {ARITY[node[1]]} argument(s)")
        for a in node[2]:
            check_arity(a, where)
    elif node[0] not in ("var", "num"):
        for a in node[1:]:
            check_arity(a, where)


def truth(v):
    return Fraction(1 if v != 0 else 0)


def trunc(v):
    return Fraction(math.trunc(v))


def ev(node, env):
    k = node[0]
    if k == "num":
        return Fraction(node[1])
    if k == "var":
        name = node[1]
        if name not in env.assigned:
            raise TIError(f"variable {name} read before it was assigned in this run")
        return env.vars[name]
    if k == "neg":
        return -ev(node[1], env)
    if k == "call":
        f, args = node[1], [ev(a, env) for a in node[2]]
        if f == "abs(":
            return abs(args[0])
        if f == "fPart(":
            return args[0] - trunc(args[0])
        if f == "iPart(":
            return trunc(args[0])
        if f == "int(":
            return Fraction(math.floor(args[0]))
        if f == "not(":
            return truth(args[0] == 0)
        if f == "min(":
            return min(args)
        if f == "max(":
            return max(args)
        if f == "gcd(":
            a, b = args
            if a < 0 or b < 0 or a.denominator != 1 or b.denominator != 1 or a >= 10**12 or b >= 10**12:
                raise TIError(f"ERR:DOMAIN gcd({a},{b}) needs nonnegative integers")
            return Fraction(math.gcd(int(a), int(b)))
    a, b = ev(node[1], env), ev(node[2], env)
    if k == "+":
        return a + b
    if k == "-":
        return a - b
    if k == "*":
        return a * b
    if k == "/":
        if b == 0:
            raise TIError("ERR:DIVIDE BY 0")
        return a / b
    if k == "^":
        if b.denominator != 1:
            raise TIError("non-integer power not simulated")
        if a == 0 and b < 0:
            raise TIError("ERR:DIVIDE BY 0")
        return a ** int(b)
    if k == "=":
        return truth(a == b)
    if k == "≠":
        return truth(a != b)
    if k == "<":
        return truth(a < b)
    if k == ">":
        return truth(a > b)
    if k == "≤":
        return truth(a <= b)
    if k == "≥":
        return truth(a >= b)
    if k == "and":
        return truth(a != 0 and b != 0)
    if k == "or":
        return truth(a != 0 or b != 0)
    if k == "xor":
        return truth((a != 0) != (b != 0))
    raise TIError(f"unknown node {k}")


# ----------------------------------------------------------------------------
# number display (Float mode, Normal notation)
# ----------------------------------------------------------------------------

def fmt_num(v):
    v = Fraction(v)
    if v.denominator == 1 and abs(v) < 10**10:
        s = str(int(v))
    else:
        s = f"{float(v):.10g}"
        if "e" in s:
            m, e = s.split("e")
            s = f"{m}ᴇ{int(e)}"
        s = s.replace("0.", ".", 1) if s.startswith(("0.", "-0.")) else s
    return s.replace("-", "⁻")  # TI shows a raised negative sign


def fmt_frac(v):
    v = Fraction(v)
    if v.denominator == 1:
        return fmt_num(v), False
    if v.denominator <= 9999:
        return f"{fmt_num(v.numerator)}/{v.denominator}", True
    return fmt_num(v), False


# ----------------------------------------------------------------------------
# statement parser
# ----------------------------------------------------------------------------

LBL = r"[A-Z0-9θ]{1,2}"


def split_top(s):
    """Split on commas that are outside quotes and parentheses."""
    parts, depth, inq, cur = [], 0, False, ""
    for c in s:
        if c == '"':
            inq = not inq
        elif not inq and c == "(":
            depth += 1
        elif not inq and c == ")":
            depth -= 1
        if c == "," and not inq and depth == 0:
            parts.append(cur)
            cur = ""
        else:
            cur += c
    parts.append(cur)
    return parts


def strlit(s):
    m = re.fullmatch(r'"([^"]*)"', s)
    return m.group(1) if m else None


def parse_line(line, n):
    where = f"line {n}: {line}"
    if line in ("Pause", "ClrHome", "Then", "Else", "End", "Stop", "Float", "Normal"):
        return (line.lower(),)
    m = re.fullmatch(rf"Lbl ({LBL})", line)
    if m:
        return ("lbl", m.group(1))
    m = re.fullmatch(rf"Goto ({LBL})", line)
    if m:
        return ("goto", m.group(1))
    m = re.fullmatch(r"Menu\((.*)\)", line)
    if m:
        args = split_top(m.group(1))
        title = strlit(args[0])
        if title is None or len(args) % 2 != 1 or len(args) < 3:
            raise SyntaxError(f"{where}: Menu( needs a title string then text,label pairs")
        items = []
        for txt, lab in zip(args[1::2], args[2::2]):
            t = strlit(txt)
            if t is None or not re.fullmatch(LBL, lab):
                raise SyntaxError(f"{where}: bad Menu( item {txt},{lab}")
            items.append((t, lab))
        return ("menu", title, items)
    m = re.fullmatch(r"Disp (.*)", line)
    if m:
        arg = m.group(1)
        s = strlit(arg)
        if s is not None:
            return ("disp", "str", s)
        if arg.endswith("►Frac"):
            return ("disp", "frac", parse_expr(arg[:-5], where))
        return ("disp", "num", parse_expr(arg, where))
    m = re.fullmatch(r"Output\((.*)\)", line)
    if m:
        args = split_top(m.group(1))
        if len(args) != 3:
            raise SyntaxError(f"{where}: Output( takes row,col,value")
        r, c = parse_expr(args[0], where), parse_expr(args[1], where)
        s = strlit(args[2])
        if s is not None:
            return ("output", r, c, "str", s)
        return ("output", r, c, "num", parse_expr(args[2], where))
    m = re.fullmatch(r'Input "([^"]*)",([A-Zθ])', line)
    if m:
        return ("input", m.group(1), m.group(2))
    m = re.fullmatch(r"If (.*)", line)
    if m:
        return ("if", parse_expr(m.group(1), where))
    m = re.fullmatch(r"(.*)→([A-Zθ])", line)
    if m:
        return ("assign", parse_expr(m.group(1), where), m.group(2))
    raise SyntaxError(f"{where}: unsupported statement")


# ----------------------------------------------------------------------------
# load + static analysis
# ----------------------------------------------------------------------------

def load():
    raw = SRC.read_text(encoding="utf-8")
    if not raw.endswith("\n"):
        fail("source should end with a newline")
    lines = raw.rstrip("\n").split("\n")
    prog = []
    for n, line in enumerate(lines, 1):
        try:
            st = parse_line(line, n)
        except SyntaxError as e:
            fail(f"SYNTAX {e}")
            st = ("bad",)
        prog.append(st)
    return lines, prog


def static_checks(lines, prog):
    labels = {}
    for i, st in enumerate(prog):
        if st[0] == "lbl":
            if st[1] in labels:
                fail(f"duplicate label {st[1]} (lines {labels[st[1]] + 1} and {i + 1})")
            labels[st[1]] = i
    used = set()
    for i, st in enumerate(prog):
        where = f"line {i + 1}"
        targets = []
        if st[0] == "goto":
            targets = [st[1]]
        elif st[0] == "menu":
            title, items = st[1], st[2]
            targets = [lab for _, lab in items]
            if len(items) > 7:
                fail(f"{where}: Menu( has {len(items)} options (max 7)")
            if width(title) > 16:
                fail(f"{where}: Menu( title {title!r} wider than 16")
            check_string(title, where)
            for t, _ in items:
                check_string(t, where)
                if width(t) > 14:
                    fail(f"{where}: Menu( option {t!r} wider than 14 (TI-84 Plus shows 14)")
                if not t.strip():
                    fail(f"{where}: empty Menu( option")
        elif st[0] in ("disp", "output") and st[-2] == "str":
            check_string(st[-1], where)
            if width(st[-1]) > COLS:
                fail(f"{where}: string {st[-1]!r} is {width(st[-1])} wide (max {COLS})")
        elif st[0] == "input":
            check_string(st[1], where)
            if width(st[1]) > 12:
                fail(f"{where}: Input prompt {st[1]!r} leaves < 4 columns for typing")
        for node in [x for x in st[1:] if isinstance(x, tuple)]:
            check_arity(node, where)
        for t in targets:
            used.add(t)
            if t not in labels:
                fail(f"{where}: jump to missing label {t}")
    for lab, i in labels.items():
        if lab not in used:
            fail(f"label {lab} (line {i + 1}) is never the target of a Goto or Menu(")

    # block structure; no jumps or labels inside If-Then blocks
    stack = []
    match = {}  # If line -> (else line or None, end line)
    for i, st in enumerate(prog):
        if st[0] == "then":
            if i == 0 or prog[i - 1][0] != "if":
                fail(f"line {i + 1}: Then without If")
            stack.append([i - 1, None])
        elif st[0] == "else":
            if not stack or stack[-1][1] is not None:
                fail(f"line {i + 1}: Else without matching If-Then")
            else:
                stack[-1][1] = i
        elif st[0] == "end":
            if not stack:
                fail(f"line {i + 1}: End without block")
            else:
                ifl, el = stack.pop()
                match[ifl] = (el, i)
        elif st[0] in ("goto", "menu", "lbl") and stack:
            fail(f"line {i + 1}: {st[0]} inside an If-Then block (memory leak / bad jump)")
        if st[0] == "if" and (i + 1 >= len(prog) or prog[i + 1][0] in ("else", "end", "lbl")):
            fail(f"line {i + 1}: single-line If must be followed by an ordinary statement")
    if stack:
        fail(f"unclosed If-Then block starting line {stack[-1][0] + 1}")

    # control-flow graph
    def succ(i):
        st = prog[i]
        if st[0] == "goto":
            return [labels.get(st[1], -1)]
        if st[0] == "menu":
            return [labels.get(lab, -1) for _, lab in st[2]]
        if st[0] == "stop":
            return []
        if st[0] == "if":
            if i + 1 < len(prog) and prog[i + 1][0] == "then":
                el, end = match.get(i, (None, len(prog) - 1))
                return [i + 1, (el + 1) if el is not None else end + 1]
            return [i + 1, i + 2]
        if st[0] == "else":
            for ifl, (el, end) in match.items():
                if el == i:
                    return [end + 1]
        return [i + 1]

    graph = {i: succ(i) for i in range(len(prog))}
    for i, ss in graph.items():
        for s in ss:
            if s >= len(prog):
                fail(f"line {i + 1}: execution can fall off the end of the program")
    seen, todo = {0}, [0]
    while todo:
        for s in graph[todo.pop()]:
            if 0 <= s < len(prog) and s not in seen:
                seen.add(s)
                todo.append(s)
    for i in range(len(prog)):
        if i not in seen:
            fail(f"line {i + 1} is unreachable: {lines[i]}")

    interactive = {i for i, st in enumerate(prog) if st[0] in ("menu", "pause", "input")}
    # any cycle that avoids every interactive statement is an infinite loop
    color = {}

    def dfs(u, path):
        color[u] = 1
        for v in graph[u]:
            if v < 0 or v >= len(prog) or v in interactive:
                continue
            if color.get(v) == 1:
                fail(f"non-interactive loop through lines {sorted(p + 1 for p in path + [v])[:8]}")
            elif v not in color:
                dfs(v, path + [v])
        color[u] = 2

    sys.setrecursionlimit(10000)
    for i in range(len(prog)):
        if i not in color and i not in interactive:
            dfs(i, [i])
    return labels, match


# ----------------------------------------------------------------------------
# simulator
# ----------------------------------------------------------------------------

class Env:
    def __init__(self, vars=None, assigned=None):
        self.vars = dict(vars or {})
        self.assigned = set(assigned or ())

    def copy(self):
        return Env(self.vars, self.assigned)


class Screen:
    def __init__(self):
        self.clear()

    def clear(self):
        self.g = [[" "] * COLS for _ in range(ROWS)]
        self.row = 0
        self.fracs = 0
        self.problems = []

    def newline_row(self):
        if self.row >= ROWS:
            self.problems.append("Disp/Input scrolled the screen (more than 8 lines)")
            self.g = self.g[1:] + [[" "] * COLS]
            self.row = ROWS - 1
        r = self.row
        self.row += 1
        return r

    def put(self, r, c, text):
        cs = cells(text)
        if c + len(cs) > COLS:
            self.problems.append(f"text {text!r} wraps past column 16")
        for k, ch in enumerate(cs):
            rr, cc = r + (c + k) // COLS, (c + k) % COLS
            if rr < ROWS:
                self.g[rr][cc] = ch

    def lines(self):
        return ["".join(row).rstrip() for row in self.g]

    def boxed(self):
        top = "+" + "-" * COLS + "+"
        body = ["|" + "".join(row) + "|" for row in self.g]
        return "\n".join([top] + body + [top])


class Halt(Exception):
    pass


class Run:
    """Execute from pc with scripted menu choices and inputs."""

    def __init__(self, prog, labels, match, env=None, menu_choices=(), inputs=(), input_defaults=None,
                 stop_at_menu=False, max_steps=20000):
        self.prog, self.labels, self.match = prog, labels, match
        self.env = env.copy() if env else Env()
        self.menus = deque(menu_choices)
        self.inputs = deque(inputs)
        self.defaults = input_defaults or {}
        self.stop_at_menu = stop_at_menu
        self.max_steps = max_steps
        self.screen = Screen()
        self.pages = []      # (pause line, label context, screen lines, boxed)
        self.menus_seen = []  # (menu line, title, items)
        self.executed = set()
        self.blocks = []
        self.end = None
        self.context = None
        self.errors = []

    def jump(self, lab, i):
        if self.blocks:
            self.errors.append(f"line {i + 1}: jump while inside an If-Then block")
        self.blocks = []
        return self.labels[lab]

    def go(self, pc):
        steps = 0
        try:
            while True:
                steps += 1
                if steps > self.max_steps:
                    raise Halt("step limit (possible infinite loop)")
                if pc >= len(self.prog):
                    raise Halt("fell off the end")
                pc = self.step(pc)
        except Halt as h:
            self.end = h.args[0]
        except TIError as e:
            self.errors.append(f"line {pc + 1}: {e}")
            self.end = "error"
        return self

    def step(self, i):
        st, env, scr = self.prog[i], self.env, self.screen
        self.executed.add(i)
        k = st[0]
        if k == "lbl":
            self.context = st[1]
            return i + 1
        if k in ("float", "normal"):
            return i + 1
        if k == "clrhome":
            scr.clear()
            return i + 1
        if k == "goto":
            return self.jump(st[1], i)
        if k == "stop":
            raise Halt("stop")
        if k == "disp":
            if st[1] == "str":
                text = st[2]
                r = scr.newline_row()
                scr.put(r, 0, text)
            else:
                v = ev(st[2], env)
                if st[1] == "frac":
                    text, is_frac = fmt_frac(v)
                    scr.fracs += is_frac
                else:
                    text = fmt_num(v)
                r = scr.newline_row()
                scr.put(r, max(0, COLS - width(text)), text)
            return i + 1
        if k == "output":
            r, c = ev(st[1], env), ev(st[2], env)
            if not (1 <= r <= ROWS and 1 <= c <= COLS) or r.denominator != 1 or c.denominator != 1:
                raise TIError(f"ERR:DOMAIN Output({r},{c})")
            text = st[4] if st[3] == "str" else fmt_num(ev(st[4], env))
            scr.put(int(r) - 1, int(c) - 1, text)
            return i + 1
        if k == "input":
            prompt, var = st[1], st[2]
            if self.inputs:
                raw = self.inputs.popleft()
            elif prompt in self.defaults:
                raw = self.defaults[prompt]
            else:
                raise Halt(f"no input for {prompt!r}")
            val = ev(parse_expr(raw, f"input {raw!r}"), Env())
            r = scr.newline_row()
            scr.put(r, 0, prompt + raw)
            env.vars[var] = val
            env.assigned.add(var)
            return i + 1
        if k == "pause":
            lines = scr.lines()
            probs = list(scr.problems)
            if scr.g[0][COLS - 1] != " ":
                probs.append("row 1 column 16 is covered by the TI-84 Plus busy indicator during Pause")
            used = max((n + 1 for n, l in enumerate(lines) if l.strip()), default=0)
            if used + scr.fracs > ROWS:
                probs.append(f"{used} rows + {scr.fracs} fraction(s): MathPrint stacked fractions could scroll")
            self.pages.append((i, self.context, lines, scr.boxed(), probs))
            return i + 1
        if k == "menu":
            self.menus_seen.append((i, st[1], st[2]))
            if self.stop_at_menu or not self.menus:
                self.end = ("menu", i)
                raise Halt(("menu", i))
            choice = self.menus.popleft()
            if not 1 <= choice <= len(st[2]):
                raise TIError(f"menu choice {choice} out of range")
            self.stop_at_menu_next = False
            return self.jump(st[2][choice - 1][1], i)
        if k == "assign":
            env.vars[st[2]] = ev(st[1], env)
            env.assigned.add(st[2])
            return i + 1
        if k == "if":
            cond = ev(st[1], env) != 0
            if i + 1 < len(self.prog) and self.prog[i + 1][0] == "then":
                el, end = self.match[i]
                if cond:
                    self.blocks.append(i)
                    self.executed.add(i + 1)
                    return i + 2
                return (el + 1) if el is not None else end + 1
            return i + 1 if cond else i + 2
        if k == "then":
            return i + 1
        if k == "else":  # reached at the end of a true Then-branch
            for ifl, (el, end) in self.match.items():
                if el == i:
                    if self.blocks:
                        self.blocks.pop()
                    return end + 1
        if k == "end":
            if self.blocks:
                self.blocks.pop()
            return i + 1
        raise TIError(f"cannot execute {st}")


# ----------------------------------------------------------------------------
# helpers for tests
# ----------------------------------------------------------------------------

DEFAULTS = {
    "A=": "2", "B=": "⁻4/3", "H=": "3", "K=": "⁻3",
    "OLD X=": "⁻4", "OLD Y=": "2",
    "DOMAIN LOW=": "⁻4", "DOMAIN HIGH=": "8", "RANGE LOW=": "⁻2", "RANGE HIGH=": "4",
    "TOP A=": "3", "BOTTOM B=": "7",
}


def ti_input(v):
    """Format a Fraction the way a student would type it (with the (-) key)."""
    v = Fraction(v)
    s = str(v.numerator) if v.denominator == 1 else f"{v.numerator}/{v.denominator}"
    return s.replace("-", "⁻")


def page_text(page):
    return [l.strip() for l in page[2]]


def find_menu_line(prog, title):
    return [i for i, st in enumerate(prog) if st[0] == "menu" and st[1] == title]


# ----------------------------------------------------------------------------
# main
# ----------------------------------------------------------------------------

def main():
    lines, prog = load()
    if any(st[0] == "bad" for st in prog):
        report(lines)
        return
    labels, match = static_checks(lines, prog)
    executed = set()
    all_pages = {}
    all_menus = {}

    def absorb(run, what):
        executed.update(run.executed)
        for e in run.errors:
            fail(f"{what}: {e}")
        for p in run.pages:
            all_pages.setdefault(p[0], p)
            for prob in p[4]:
                fail(f"{what}: page at line {p[0] + 1} ({p[2][0].strip()}): {prob}")
        for m in run.menus_seen:
            all_menus.setdefault(m[0], m)
        return run

    # ---- exhaustive menu walk: every option of every menu ------------------
    # The walk is repeated with several input profiles so the tools' error
    # menus are walked too.  Every option's destination is checked:
    #   main-menu items open the submenu with the same name; MAIN MENU,
    #   TRANSFORM MENU and POWER MENU go where they say; tools and their
    #   repeat options end at that tool's own menu; RE-ENTER on an error menu
    #   comes back to the same tool; every reference topic returns to the
    #   menu it was chosen from.
    profiles = {
        "valid": dict(DEFAULTS),
        "tool B=0": dict(DEFAULTS, **{"B=": "0"}),
        "tool A=0": dict(DEFAULTS, **{"A=": "0"}),
        "power K=0": dict(DEFAULTS, **{"K=": "0"}),
        "power B=0": dict(DEFAULTS, **{"BOTTOM B=": "0"}),
        "power A=0": dict(DEFAULTS, **{"TOP A=": "0"}),
        "power A=1/2": dict(DEFAULTS, **{"TOP A=": "1/2"}),
        "power A=1000": dict(DEFAULTS, **{"TOP A=": "1000"}),
    }
    TOOLS = {"POINT TOOL", "D/R TOOL", "CLASSIFIER"}
    REPEAT = {"NEXT POINT", "NEW A,B,H,K", "NEW VALUES", "NEW FUNCTION", "RE-ENTER"}
    GOES = {"TRANSFORM MENU": "TRANSFORM", "POWER MENU": "POWER FUNCS"}
    all_states = {}
    main_menu = None
    for pname, prof in profiles.items():
        start = absorb(Run(prog, labels, match, input_defaults=prof, stop_at_menu=True).go(0), f"start [{pname}]")
        if not start.menus_seen:
            fail("program never reaches a menu")
            report(lines)
            return
        first = start.menus_seen[0][0]
        main_menu = first if main_menu is None else main_menu
        main_title = prog[main_menu][1]
        states = {first: start.env}
        edges = {}
        queue = deque([first])
        while queue:
            m = queue.popleft()
            title, items = prog[m][1], prog[m][2]
            for k in range(1, len(items) + 1):
                text = items[k - 1][0]
                r = Run(prog, labels, match, env=states[m], menu_choices=[k], input_defaults=prof)
                r.go(m)
                what = f"[{pname}] menu '{title}' option {k} '{text}'"
                absorb(r, what)
                if r.end != "stop" and not isinstance(r.end, tuple):
                    fail(f"{what}: run ended with {r.end!r}")
                    continue
                dest = "stop" if r.end == "stop" else prog[r.end[1]][1]
                edges[(m, k)] = r.end if r.end == "stop" else r.end[1]
                if isinstance(r.end, tuple) and r.end[1] not in states:
                    states[r.end[1]] = r.env
                    queue.append(r.end[1])
                # expected destination
                took_input = any(prog[i][0] == "input" for i in r.executed)
                if m == main_menu:
                    want = "stop" if text == "EXIT" else text
                elif text == "MAIN MENU":
                    want = main_title
                elif text in GOES:
                    want = GOES[text]
                elif "CANNOT" in title and text == "RE-ENTER":
                    want = title if pname.startswith("tool") else None
                    if dest != title:
                        fail(f"{what}: RE-ENTER with the same bad input should come back to '{title}', got '{dest}'")
                    if edges[(m, k)] != m:
                        fail(f"{what}: RE-ENTER went to a different tool's error menu (line {edges[(m, k)] + 1})")
                    continue
                elif text in TOOLS or text in REPEAT:
                    tool = text if text in TOOLS else title
                    if pname == "valid":
                        want = tool
                    else:
                        continue  # error outcomes are checked by the scripted error tests
                else:
                    want = title
                    if took_input:
                        fail(f"{what}: a reference topic asked for input")
                if want is not None and dest != want:
                    fail(f"{what}: goes to '{dest}', expected '{want}'")
        for m, env in states.items():
            all_states.setdefault(m, env)

    # every menu must offer MAIN MENU and EXIT must stop the program
    for m in all_states:
        if m != main_menu and not any(lab == "M0" for _, lab in prog[m][2]):
            fail(f"menu '{prog[m][1]}' (line {m + 1}) has no MAIN MENU option")
    if not any(t == "EXIT" for t, _ in prog[main_menu][2]):
        fail("main menu has no EXIT option")
    for m in (i for i, st in enumerate(prog) if st[0] == "menu"):
        if m not in all_states:
            fail(f"menu at line {m + 1} was never reached by the walk")

    def menu_index(title, text):
        m = find_menu_line(prog, title)
        if not m:
            fail(f"no menu titled {title!r}")
            return None
        items = [t for t, _ in prog[m[0]][2]]
        if text not in items:
            fail(f"menu {title!r} has no option {text!r}")
            return None
        return items.index(text) + 1

    MAIN = "U1 TOPIC 2 HELP"

    def path(*pairs):
        return [menu_index(t, o) for t, o in pairs]

    # ---- scripted tests: the sample validations ----------------------------
    def scripted(name, choices, inputs, expect_pages, end_choices=None):
        r = Run(prog, labels, match, menu_choices=choices + (end_choices or []), inputs=inputs)
        r.go(0)
        absorb(r, name)
        texts = [page_text(p) for p in r.pages]
        for want in expect_pages:
            if not any(all(any(w == line for line in t) for w in want) for t in texts):
                fail(f"{name}: no page shows all of {want}; pages were {texts[-3:]}")
        return r

    to_point = path((MAIN, "TRANSFORM"), ("TRANSFORM", "POINT TOOL"))
    to_dr = path((MAIN, "TRANSFORM"), ("TRANSFORM", "D/R TOOL"))
    to_cls = path((MAIN, "POWER FUNCS"), ("POWER FUNCS", "CLASSIFIER"))
    exit_ = [menu_index(MAIN, "EXIT")]

    scripted("TRANSFORM POINT sample", to_point + [menu_index("POINT TOOL", "MAIN MENU")] + exit_,
             ["2", "⁻4/3", "3", "⁻3", "⁻4", "2"], [["NEW POINT", "X=X/B+H", "6", "Y=A*Y+K", "1"]])
    r = scripted("TRANSFORM POINT next point", to_point + [menu_index("POINT TOOL", "NEXT POINT"),
                                                          menu_index("POINT TOOL", "MAIN MENU")] + exit_,
                 ["2", "⁻4/3", "3", "⁻3", "⁻4", "2", "8", "4"],
                 [["NEW POINT", "⁻3", "5"]])
    scripted("TRANSFORM D/R sample", to_dr + [menu_index("D/R TOOL", "MAIN MENU")] + exit_,
             ["2", "⁻4/3", "3", "⁻3", "⁻4", "8", "⁻2", "4"],
             [["NEW DOMAIN", "LOW END", "⁻3", "HIGH END", "6", "B<0 ENDS SWAPPED"],
              ["NEW RANGE", "LOW END", "⁻7", "HIGH END", "5"]])
    for tool, inputs, title in [(to_point, ["2", "0"], "B CANNOT BE 0"), (to_point, ["0", "1"], "A CANNOT BE 0"),
                                (to_dr, ["2", "0"], "B CANNOT BE 0"), (to_dr, ["0", "1"], "A CANNOT BE 0")]:
        r = Run(prog, labels, match, menu_choices=tool + [menu_index(title, "RE-ENTER")], inputs=inputs + ["3", "4"],
                input_defaults=DEFAULTS)
        r.go(0)
        absorb(r, f"tool error {title}")
        if not any(mt == title for _, mt, _ in r.menus_seen):
            fail(f"tool error test: menu {title!r} not shown for inputs {inputs}")

    def classify_pages(k, a, b, extra=()):
        r = Run(prog, labels, match, menu_choices=to_cls + [menu_index("CLASSIFIER", "MAIN MENU")] + exit_,
                inputs=[ti_input(k), ti_input(a), ti_input(b)])
        r.go(0)
        absorb(r, f"classifier k={k} a={a} b={b}")
        return r

    samples = [
        ((1, 3, 7), ["P=3/7", "A IS ODD", "B IS ODD", "ODD SYMMETRY", "IN QI AND QIII"]),
        ((1, 4, 7), ["P=4/7", "A IS EVEN", "B IS ODD", "EVEN SYMMETRY", "IN QI AND QII"]),
        ((1, 3, 2), ["P=3/2", "B IS EVEN", "UNDEFINED X<0", "IN QI ONLY", "P>1  POSITIVE"]),
        ((-1, 4, 7), ["EVEN SYMMETRY", "K<0 FLIP X-AXIS", "IN QIII AND QIV"]),
        ((1, -2, 1), ["P=⁻2/1", "A IS EVEN", "EVEN SYMMETRY", "P<0  NEGATIVE", "IN QI AND QII"]),
    ]
    for (k, a, b), want in samples:
        r = classify_pages(k, a, b)
        if not r.pages or not all(w in page_text(r.pages[-3]) for w in want):
            fail(f"classifier sample {(k, a, b)}: expected {want}, page 1 was "
                 f"{page_text(r.pages[-3]) if len(r.pages) >= 3 else r.pages}")
    r = classify_pages(1, -2, 1)
    p2, p3 = page_text(r.pages[-2]), page_text(r.pages[-1])
    for w in ["X=0 EXCLUDED", "ASYMPTOTES", "X=0 AND Y=0", "ALL REALS, X≠0", "(0,INF)"]:
        if w not in p2:
            fail(f"classifier x^-2: page 2 missing {w!r}: {p2}")

    # bad inputs: error page, then back to the POWER menu
    for k, a, b, msg in [(1, 2, 0, "B CANNOT BE 0."), (0, 2, 3, "K CANNOT BE 0."),
                         (1, Fraction(1, 2), 3, "INTEGERS."), (1, 0, 3, "A=0 MEANS P=0."),
                         (1, 1000, 3, "UNDER 1000.")]:
        r = Run(prog, labels, match,
                menu_choices=to_cls + [menu_index(MAIN, "EXIT")] if False else to_cls,
                inputs=[ti_input(k), ti_input(a), ti_input(b)], stop_at_menu=False)
        r.go(0)
        absorb(r, f"classifier error k={k} a={a} b={b}")
        if not r.pages or msg not in page_text(r.pages[-1]) or "ERROR" not in page_text(r.pages[-1]):
            fail(f"classifier error case {(k, a, b)}: expected error page with {msg!r}")
        if not (isinstance(r.end, tuple) and prog[r.end[1]][1] == "POWER FUNCS"):
            fail(f"classifier error case {(k, a, b)}: did not return to the POWER FUNCS menu (ended {r.end})")

    # ---- TOP MISTAKES "READ ALL" shows all 7 pages in order ------------
    r = Run(prog, labels, match, menu_choices=path((MAIN, "TOP MISTAKES"), ("TOP MISTAKES", "READ ALL 12")))
    r.go(0)
    absorb(r, "read all mistakes")
    heads = [p[2][0].strip() for p in r.pages]
    if heads != [f"TOP MISTAKES {n}" for n in range(1, 8)]:
        fail(f"READ ALL 12 showed {heads}")
    nums = [m.group(1) for p in r.pages for l in p[2] for m in [re.match(r"(\d+)\) ", l)] if m]
    if nums != [str(n) for n in range(1, 13)]:
        fail(f"READ ALL 12 numbering is {nums}")

    # READ ALL, then each group: each group must show only its own pages
    # (the W flag must be reset) and return to TOP MISTAKES.
    seq = path((MAIN, "TOP MISTAKES"), ("TOP MISTAKES", "READ ALL 12"), ("TOP MISTAKES", "1-5 TRANSFORMS"),
               ("TOP MISTAKES", "6-9 DOMAIN/INV"), ("TOP MISTAKES", "10-12 POWER"), ("TOP MISTAKES", "READ ALL 12"))
    r = Run(prog, labels, match, menu_choices=seq + [menu_index("TOP MISTAKES", "MAIN MENU"), menu_index(MAIN, "EXIT")])
    r.go(0)
    absorb(r, "mistakes sequence")
    heads = [p[2][0].strip() for p in r.pages]
    want = [f"TOP MISTAKES {n}" for n in list(range(1, 8)) + [1, 2, 3] + [4, 5] + [6, 7] + list(range(1, 8))]
    if heads != want:
        fail(f"TOP MISTAKES sequence showed pages {heads}, expected {want}")
    tm = find_menu_line(prog, "TOP MISTAKES")[0]
    if [m for m, _, _ in r.menus_seen].count(tm) != 6 or r.end != "stop":
        fail("TOP MISTAKES groups do not all return to the TOP MISTAKES menu")

    # RE-ENTER after a tool error, then valid values: back in the same tool
    for tool, bad, title in [("POINT TOOL", ["2", "0", "3", "⁻3"], "B CANNOT BE 0"),
                             ("POINT TOOL", ["0", "1", "3", "⁻3"], "A CANNOT BE 0"),
                             ("D/R TOOL", ["2", "0", "3", "⁻3"], "B CANNOT BE 0"),
                             ("D/R TOOL", ["0", "1", "3", "⁻3"], "A CANNOT BE 0")]:
        r = Run(prog, labels, match, menu_choices=path((MAIN, "TRANSFORM"), ("TRANSFORM", tool), (title, "RE-ENTER")),
                inputs=bad, input_defaults=DEFAULTS)
        r.go(0)
        absorb(r, f"{tool} {title} then RE-ENTER")
        if not (isinstance(r.end, tuple) and prog[r.end[1]][1] == tool):
            fail(f"{tool}: after '{title}' and RE-ENTER with valid values, ended at {r.end} instead of the {tool} menu")

    # ---- exhaustive classifier vs an independent numeric oracle -------------
    cls_env = None
    for (m, st) in states.items():
        if prog[m][1] == "CLASSIFIER":
            cls_env = st
    e7 = labels["E7"]
    count = 0
    for k in [Fraction(1), Fraction(-1), Fraction(3), Fraction(-2, 3)]:
        for a in range(-12, 13):
            for b in range(-12, 13):
                if a == 0 or b == 0:
                    continue
                r = Run(prog, labels, match, env=Env(), inputs=[ti_input(k), ti_input(a), ti_input(b)],
                        stop_at_menu=True)
                r.go(e7)
                absorb(r, f"classifier oracle k={k} a={a} b={b}")
                count += 1
                if len(r.pages) != 3:
                    fail(f"classifier oracle k={k} a={a} b={b}: expected 3 pages, got {len(r.pages)}")
                    continue
                check_classifier(k, a, b, [page_text(p) for p in r.pages])
    print(f"classifier oracle: {count} (k, a, b) combinations checked")

    # ---- randomized transform tools vs exact arithmetic --------------------
    rng = random.Random(2026)
    t3, t5 = labels["T3"], labels["T5"]
    nums = [Fraction(n, d) for n in range(-9, 10) for d in (1, 2, 3, 4)]
    for trial in range(400):
        A = rng.choice([n for n in nums if n != 0])
        B = rng.choice([n for n in nums if n != 0])
        H, K, X, Y = (rng.choice(nums) for _ in range(4))
        r = Run(prog, labels, match, env=Env(), inputs=[ti_input(v) for v in (A, B, H, K, X, Y)], stop_at_menu=True)
        r.go(t3)
        absorb(r, f"point tool trial {trial}")
        want = [fmt_frac(X / B + H)[0], fmt_frac(A * Y + K)[0]]
        t = page_text(r.pages[-1])
        if t[2] != want[0] or t[4] != want[1]:
            fail(f"point tool A={A} B={B} H={H} K={K} ({X},{Y}): showed {t}, want {want}")
        lo, hi = sorted([rng.choice(nums), rng.choice(nums)])
        rlo, rhi = sorted([rng.choice(nums), rng.choice(nums)])
        r = Run(prog, labels, match, env=Env(), inputs=[ti_input(v) for v in (A, B, H, K, lo, hi, rlo, rhi)],
                stop_at_menu=True)
        r.go(t5)
        absorb(r, f"D/R tool trial {trial}")
        d = sorted([lo / B + H, hi / B + H])
        rr = sorted([A * rlo + K, A * rhi + K])
        p1, p2 = page_text(r.pages[-2]), page_text(r.pages[-1])
        if p1[2] != fmt_frac(d[0])[0] or p1[4] != fmt_frac(d[1])[0]:
            fail(f"D/R domain A={A} B={B} H={H} [{lo},{hi}]: showed {p1}, want {d}")
        if p2[2] != fmt_frac(rr[0])[0] or p2[4] != fmt_frac(rr[1])[0]:
            fail(f"D/R range A={A} K={K} [{rlo},{rhi}]: showed {p2}, want {rr}")
        if (B < 0) != ("B<0 ENDS SWAPPED" in p1) or (A < 0) != ("A<0 ENDS SWAPPED" in p2):
            fail(f"D/R swap note wrong for A={A} B={B}")
    print("transform tools: 400 point + 400 domain/range trials checked")

    # ---- coverage ------------------------------------------------------------
    for i in range(len(prog)):
        if i not in executed:
            fail(f"line {i + 1} never executed by any test: {lines[i]}")

    write_screens(prog, lines, all_pages, all_menus, labels)
    print(f"{len(lines)} lines, {len(labels)} labels, {len(all_menus)} menus, "
          f"{len(all_pages)} distinct pages, {len(executed)}/{len(prog)} lines executed")
    report(lines)


def oracle(k, a, b):
    """Independent description of y = k*x^(a/b) from sampled real values."""
    p = Fraction(a, b)
    a2, b2 = p.numerator, p.denominator

    def f(x):
        if x < 0 and b2 % 2 == 0:
            return None
        if x == 0:
            return 0.0 if a2 > 0 else None
        root = math.copysign(abs(x) ** (1.0 / b2), x)
        return float(k) * root ** a2

    xs = [s * 10 ** (e / 4) for e in range(-12, 13) for s in (1, -1)]
    vals = [v for v in (f(x) for x in xs + [0.0]) if v is not None]
    left = f(-2.0) is not None
    zero = f(0.0) is not None
    dom = {(True, True): "ALL REALS", (True, False): "ALL REALS, X≠0",
           (False, True): "[0,INF)", (False, False): "(0,INF)"}[(left, zero)]
    pos, neg = any(v > 0 for v in vals), any(v < 0 for v in vals)
    hit0 = any(v == 0 for v in vals)
    if pos and neg:
        rng = "ALL REALS" if hit0 else "ALL REALS, Y≠0"
    elif pos:
        rng = "[0,INF)" if hit0 else "(0,INF)"
    else:
        rng = "(-INF,0]" if hit0 else "(-INF,0)"
    if not left:
        sym = "UNDEFINED X<0"
    elif math.isclose(f(-2.0), f(2.0)):
        sym = "EVEN SYMMETRY"
    elif math.isclose(f(-2.0), -f(2.0)):
        sym = "ODD SYMMETRY"
    else:
        sym = "?"
    quads = set()
    for x in (0.5, 2.0, -0.5, -2.0):
        y = f(x)
        if y is None:
            continue
        quads.add({(True, True): "QI", (False, True): "QII", (False, False): "QIII", (True, False): "QIV"}[(x > 0, y > 0)])
    inc = f(2.0) > f(1.0)
    mid, avg = f(1.5), (f(1.0) + f(2.0)) / 2
    shape = "STRAIGHT LINE" if math.isclose(mid, avg, rel_tol=1e-12) else ("CURVES UP" if mid < avg else "CURVES DOWN")
    return dict(a=a2, b=b2, dom=dom, rng=rng, sym=sym, quads=quads, inc=inc, shape=shape,
                asym=a2 < 0, reduced=math.gcd(a, b) > 1)


def check_classifier(k, a, b, pages):
    o = oracle(k, a, b)
    tag = f"classifier k={k} a={a} b={b}"
    p1, p2, p3 = pages
    want1 = [f"P={ti_input(o['a'])}/{o['b']}",
             "A IS EVEN" if o["a"] % 2 == 0 else "A IS ODD",
             "B IS EVEN" if o["b"] % 2 == 0 else "B IS ODD",
             o["sym"], "K>0  NO FLIP" if k > 0 else "K<0 FLIP X-AXIS"]
    p = Fraction(o["a"], o["b"])
    want1.append("P<0  NEGATIVE" if p < 0 else "0<P<1  POSITIVE" if p < 1 else "P=1  LINE" if p == 1 else "P>1  POSITIVE")
    for w in want1:
        if w not in p1:
            fail(f"{tag}: page 1 missing {w!r}: {p1}")
    qline = [l for l in p1 if l.startswith("IN Q")]
    got = set(re.findall(r"Q[IV]+", qline[0])) if qline else set()
    if got != o["quads"]:
        fail(f"{tag}: quadrants {got} but the graph is in {o['quads']}")
    if ("(P WAS REDUCED)" in p1) != o["reduced"]:
        fail(f"{tag}: reduced note wrong")
    if p2[1] != o["dom"] or p2[3] != o["rng"]:
        fail(f"{tag}: domain/range shown {p2[1]!r}/{p2[3]!r}, oracle {o['dom']!r}/{o['rng']!r}")
    if ("ASYMPTOTES" in p2) != o["asym"] or ("X=0 EXCLUDED" in p2) != o["asym"]:
        fail(f"{tag}: asymptote / x=0 lines wrong: {p2}")
    if ("NOT CONT AT X=0" in p2) != o["asym"]:
        fail(f"{tag}: continuity line wrong: {p2}")
    if p3[0] != ("QI PIECE (K>0)" if k > 0 else "QIV PIECE (K<0)"):
        fail(f"{tag}: page 3 header {p3[0]!r}")
    if p3[1] != ("INCREASING" if o["inc"] else "DECREASING"):
        fail(f"{tag}: page 3 says {p3[1]!r}, oracle increasing={o['inc']}")
    if p3[2] != o["shape"]:
        fail(f"{tag}: page 3 shape {p3[2]!r}, oracle {o['shape']!r}")
    if ("THROUGH (0,0)" in p3) != (o["a"] > 0) or "THROUGH (1,K)" not in p3:
        fail(f"{tag}: page 3 through-points wrong: {p3}")


def write_screens(prog, lines, pages, menus, labels):
    lab_at = {i: lab for lab, i in labels.items()}
    order = sorted(list(pages.items()) + [(i, m) for i, m in menus.items()], key=lambda x: x[0])
    out = ["HPC2HELP - every screen as it appears on a TI-84 Plus (16 x 8).",
           "Generated by tools/check_tibasic.py from HPC2HELP.txt. Menus are shown",
           "with the numbers the calculator adds. Tool pages use the sample inputs.", ""]
    for i, item in order:
        if len(item) == 3:  # menu
            _, title, items = item
            out.append(f"--- MENU (line {i + 1}) ---")
            out.append("+" + "-" * COLS + "+")
            out.append("|" + title.ljust(COLS) + "|")
            for n, (t, lab) in enumerate(items, 1):
                out.append("|" + f"{n}:{t}".ljust(COLS) + f"|  -> Lbl {lab}")
            out.append("+" + "-" * COLS + "+")
        else:
            _, ctx, _, boxed, _ = item
            out.append(f"--- page (Lbl {ctx}, Pause at line {i + 1}) ---")
            out.append(boxed)
        out.append("")
    SCREENS.write_text("\n".join(out), encoding="utf-8")


def report(lines):
    if FAILURES:
        seen = []
        for f in FAILURES:
            if f not in seen:
                seen.append(f)
        print(f"FAILED: {len(seen)} problem(s)")
        for f in seen[:200]:
            print("  -", f)
        sys.exit(1)
    print("ALL CHECKS PASSED")


if __name__ == "__main__":
    main()
