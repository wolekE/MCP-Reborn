#!/usr/bin/env python3
"""
tisim.py - a TI-Basic interpreter for the subset of TI-84 Plus CE BASIC used by these programs.

It executes the token stream of each program (read from the built .8xp files with tivars,
or tokenized from src/*.txt with the same tokenizer as build.py), so a trace runs exactly
what the calculator would run. It models:

  * the 26 x 10 home screen of the TI-84 Plus CE (Disp, Output(, Input, Prompt, Pause,
    ClrHome, scrolling) and Menu( (limited to 7 options, the TI-84 Plus limit)
  * 14-significant-digit decimal arithmetic (like the calculator's BCD floats)
  * TI order of operations, implied multiplication, negation vs. subtraction
  * the calculator's runtime errors: DIVIDE BY 0, NONREAL ANS, DOMAIN, OVERFLOW, SYNTAX,
    DATA TYPE, UNDEFINED, LABEL, INVALID DIM, ARGUMENT, MEMORY
  * If/Then/Else/End, While, Repeat, For(, Lbl/Goto, Menu(, prgm calls, Return, Stop
  * memory-leak detection: a Goto/Menu( jump or Return made from inside an open
    If-Then/While/Repeat/For( block is reported as an error (on a real calculator each one
    leaks memory and eventually causes ERR:MEMORY)

Run a program with scripted keypresses:

    python3 tools/tisim.py PHYSOLVE 1 8 999 120 999 1.5 9
    python3 tools/tisim.py --src PHYSOLVE ...      (use src/*.txt instead of 8xp/*.8xp)

Script items: for a Menu( give the option number (1-9) or a prefix of the option text;
for Input/Prompt give the value (a number or a TI expression such as 50/1.0936).
Pause screens continue automatically.
"""

import math
import random
import sys
from decimal import Decimal, Context, InvalidOperation, ROUND_HALF_UP, ROUND_FLOOR, ROUND_DOWN, localcontext
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ROWS, COLS = 10, 26
MENU_MAX = 7

CTX = Context(prec=14, rounding=ROUND_HALF_UP, Emax=999, Emin=-999)
D0, D1 = Decimal(0), Decimal(1)


class TIError(Exception):
    def __init__(self, code, detail=""):
        super().__init__(f"ERR:{code}" + (f" ({detail})" if detail else ""))
        self.code = code
        self.detail = detail


class ScriptEnd(Exception):
    """The program asked for input but the script has no more items."""


class StepLimit(Exception):
    pass


# --------------------------------------------------------------------------- numbers

def norm(x):
    """Round to 14 significant digits and apply the calculator's range limits."""
    if isinstance(x, float):
        if math.isnan(x) or math.isinf(x):
            raise TIError("OVERFLOW")
        x = Decimal(repr(x))
    x = CTX.plus(x)
    if x != 0 and abs(x) >= Decimal("1E100"):
        raise TIError("OVERFLOW")
    if x != 0 and abs(x) < Decimal("1E-99"):
        return D0
    return x


def num(x):
    if isinstance(x, str):
        raise TIError("DATA TYPE", "string used as a number")
    if isinstance(x, list):
        raise TIError("DATA TYPE", "list used as a number")
    return x


def fmt_num(x, mode=("Float", None)):
    """Format a number like the TI-84 Plus CE home screen (Normal, Float or Fix n)."""
    x = Decimal(x)
    if x == 0:
        return "0" if mode[0] == "Float" else "0." + "0" * mode[1] if mode[1] else "0"
    neg = x < 0
    a = abs(x)
    if mode[0] == "Fix" and Decimal("1E-3") <= a < Decimal("1E10"):
        s = f"{a.quantize(Decimal(1).scaleb(-mode[1]), rounding=ROUND_HALF_UP):f}"
    else:
        a10 = Decimal(f"{a:.9E}")          # 10 significant digits
        e = a10.adjusted()
        if -3 <= e < 10 or (e == -4 and False):
            s = f"{a10:f}"
            if "." in s:
                s = s.rstrip("0").rstrip(".")
        else:
            m = f"{a10.scaleb(-e):f}"
            if "." in m:
                m = m.rstrip("0").rstrip(".")
            s = m + "ᴇ" + ("⁻" if e < 0 else "") + str(abs(e))
    if s.startswith("0."):
        s = s[1:]
    return ("⁻" if neg else "") + s


# --------------------------------------------------------------------------- tokens

def load_tokens_from_8xp(path):
    from tivars.types import TIProgram
    prog = TIProgram.open(str(path))
    return [t.langs["en"].display for t in prog.tokens()]


def load_tokens_from_src(path):
    sys.path.insert(0, str(ROOT / "tools"))
    from build import tokenize_program
    text = Path(path).read_text(encoding="utf-8")
    if text.endswith("\n"):
        text = text[:-1]
    toks, _ = tokenize_program(text, Path(path).stem)
    return [t.langs["en"].display for t in toks]


FUNCS1 = {"abs(", "int(", "iPart(", "fPart(", "log(", "ln(", "₁₀^(", "𝑒^(", "√(", "sin(", "cos(",
          "tan(", "sin⁻¹(", "cos⁻¹(", "tan⁻¹(", "not(", "length(", "dim(", "sum(", "round("}
FUNCSN = {"R►Pr(", "R►Pθ(", "P►Rx(", "P►Ry(", "min(", "max(", "sub("}
POSTFIX = {"²", "⁻¹", "!", "°", "³"}
RELOPS = {"=", "≠", "<", ">", "≤", "≥"}
LETTERS = set("ABCDEFGHIJKLMNOPQRSTUVWXYZθ")
DIGITS = set("0123456789")
STRVARS = {f"Str{i}" for i in range(10)}
CMD_START = {"ClrHome", "Disp ", "Output(", "Pause ", "Input ", "Prompt ", "Menu(", "Lbl ", "Goto ",
             "If ", "Then", "Else", "End", "While ", "Repeat ", "For(", "Return", "Stop", "prgm",
             "DelVar ", "Degree", "Radian", "Float", "Normal", "Fix "}


class Stmt:
    def __init__(self, kind, line, text, **kw):
        self.kind = kind
        self.line = line
        self.text = text
        self.__dict__.update(kw)

    def __repr__(self):
        return f"<{self.kind} L{self.line}: {self.text}>"


class Parser:
    def __init__(self, lex, where):
        self.lex = lex
        self.i = 0
        self.where = where
        self.warnings = []

    def peek(self, k=0):
        j = self.i + k
        return self.lex[j] if j < len(self.lex) else None

    def take(self, expect=None):
        t = self.peek()
        if t is None:
            raise TIError("SYNTAX", f"unexpected end of statement, wanted {expect!r}")
        if expect is not None and t != expect:
            raise TIError("SYNTAX", f"expected {expect!r}, found {t!r}")
        self.i += 1
        return t

    def at_end(self):
        return self.i >= len(self.lex)

    def close_paren(self):
        # closing parentheses may be omitted at the end of a statement or before →
        if self.peek() == ")":
            self.i += 1
        elif self.peek() in (None, "→"):
            self.warnings.append("omitted closing parenthesis")
        else:
            raise TIError("SYNTAX", f"expected ')', found {self.peek()!r}")

    # ---- expressions
    def expr(self):
        return self.p_or()

    def p_or(self):
        a = self.p_and()
        while self.peek() in (" or ", " xor "):
            op = self.take().strip()
            a = ("bin", op, a, self.p_and())
        return a

    def p_and(self):
        a = self.p_rel()
        while self.peek() == " and ":
            self.take()
            a = ("bin", "and", a, self.p_rel())
        return a

    def p_rel(self):
        a = self.p_add()
        while self.peek() in RELOPS:
            op = self.take()
            a = ("bin", op, a, self.p_add())
        return a

    def p_add(self):
        a = self.p_mul()
        while self.peek() in ("+", "-"):
            op = self.take()
            a = ("bin", op, a, self.p_mul())
        return a

    def starts_factor(self, t):
        if t is None:
            return False
        return (t in DIGITS or t == "." or t == "ᴇ" or t in LETTERS or t == "(" or t in FUNCS1
                or t in FUNCSN or t in ("π", "Ans", "ʟ", "{", '"') or t in STRVARS)

    def p_mul(self):
        a = self.p_neg()
        last = None
        while True:
            t = self.peek()
            if t in ("*", "/"):
                self.take()
                b = self.p_neg()
                a = ("bin", t, a, b)
                last = t
            elif self.starts_factor(t):
                if last == "/":
                    raise TIError("SYNTAX", "implied multiplication right after a division is ambiguous; "
                                            "add parentheses or *")
                a = ("bin", "*", a, self.p_neg())
                last = "impl"
            elif t == "⁻":
                raise TIError("SYNTAX", "negation sign right after a value (did you mean subtraction '-'?)")
            else:
                return a

    def p_neg(self):
        if self.peek() == "⁻":
            self.take()
            return ("neg", self.p_neg())
        if self.peek() == "-":
            raise TIError("SYNTAX", "subtraction sign '-' used as a negative sign (use '⁻')")
        return self.p_pow()

    def p_pow(self):
        a = self.p_post()
        while self.peek() == "^":
            self.take()
            if self.peek() == "⁻":
                self.take()
                b = ("neg", self.p_post())
            else:
                b = self.p_post()
            a = ("bin", "^", a, b)
        return a

    def p_post(self):
        a = self.atom()
        while self.peek() in POSTFIX:
            a = ("post", self.take(), a)
        return a

    def number(self):
        s = ""
        while self.peek() in DIGITS or self.peek() == ".":
            s += self.take()
        if s.count(".") > 1 or s == ".":
            raise TIError("SYNTAX", f"bad number {s!r}")
        if self.peek() == "ᴇ":
            self.take()
            e = ""
            if self.peek() == "⁻":
                self.take()
                e = "-"
            d = ""
            while self.peek() in DIGITS:
                d += self.take()
            if not d:
                raise TIError("SYNTAX", "bad exponent")
            s = (s or "1") + "E" + e + d
        return ("num", norm(Decimal(s)))

    def string_lit(self):
        self.take('"')
        s = ""
        while self.peek() not in (None, '"', "→"):
            s += self.take()
        if self.peek() == '"':
            self.take()
        else:
            self.warnings.append("omitted closing quote")
        return ("str", s)

    def list_name(self):
        self.take("ʟ")
        name = ""
        while len(name) < 5 and (self.peek() in LETTERS or (name and self.peek() in DIGITS)):
            name += self.take()
        if not name:
            raise TIError("SYNTAX", "bad list name")
        return name

    def atom(self):
        t = self.peek()
        if t is None:
            raise TIError("SYNTAX", "missing value")
        if t in DIGITS or t == "." or t == "ᴇ":
            return self.number()
        if t in LETTERS:
            self.take()
            return ("var", t)
        if t in STRVARS:
            self.take()
            return ("strvar", t)
        if t == "π":
            self.take()
            return ("num", norm(Decimal("3.1415926535898")))
        if t == "Ans":
            self.take()
            return ("ans",)
        if t == '"':
            return self.string_lit()
        if t == "(":
            self.take()
            e = self.expr()
            self.close_paren()
            return e
        if t == "{":
            self.take()
            items = [self.expr()]
            while self.peek() == ",":
                self.take()
                items.append(self.expr())
            if self.peek() == "}":
                self.take()
            elif self.peek() not in (None, "→"):
                raise TIError("SYNTAX", "expected '}'")
            return ("list", items)
        if t == "ʟ":
            name = self.list_name()
            if self.peek() == "(":
                self.take()
                idx = self.expr()
                self.close_paren()
                return ("lidx", name, idx)
            return ("lvar", name)
        if t in FUNCS1 or t in FUNCSN:
            self.take()
            args = [self.expr()]
            while self.peek() == ",":
                self.take()
                args.append(self.expr())
            self.close_paren()
            return ("call", t, args)
        raise TIError("SYNTAX", f"unexpected {t!r}")

    def store_target(self):
        t = self.peek()
        if t in LETTERS:
            self.take()
            return ("var", t)
        if t in STRVARS:
            self.take()
            return ("strvar", t)
        if t == "ʟ":
            name = self.list_name()
            if self.peek() == "(":
                self.take()
                idx = self.expr()
                self.close_paren()
                return ("lidx", name, idx)
            return ("lvar", name)
        raise TIError("SYNTAX", f"cannot store to {t!r}")


def parse_statement(lex, line, text, where):
    p = Parser(lex, where)
    first = p.peek()
    kind = None
    kw = {}
    if first in ("ClrHome", "Then", "Else", "End", "Return", "Stop", "Degree", "Radian", "Float", "Normal"):
        p.take()
        kind = first
    elif first == "Disp ":
        p.take()
        items = []
        if not p.at_end():
            items.append(p.expr())
            while p.peek() == ",":
                p.take()
                items.append(p.expr())
        kind, kw = "Disp", {"items": items}
    elif first == "Output(":
        p.take()
        r = p.expr(); p.take(",")
        c = p.expr(); p.take(",")
        v = p.expr()
        p.close_paren()
        kind, kw = "Output", {"r": r, "c": c, "v": v}
    elif first == "Pause ":
        p.take()
        kind, kw = "Pause", {"v": None if p.at_end() else p.expr()}
    elif first == "Input ":
        p.take()
        prompt = None
        if p.peek() == '"':
            prompt = p.string_lit()[1]
            p.take(",")
        elif p.peek() in STRVARS and p.peek(1) == ",":
            raise TIError("SYNTAX", "string-variable prompts are not supported by this simulator")
        target = p.store_target() if not p.at_end() else None
        kind, kw = "Input", {"prompt": prompt, "target": target}
    elif first == "Prompt ":
        p.take()
        targets = [p.store_target()]
        while p.peek() == ",":
            p.take()
            targets.append(p.store_target())
        kind, kw = "Prompt", {"targets": targets}
    elif first == "Menu(":
        p.take()
        title = p.expr()
        opts = []
        while p.peek() == ",":
            p.take()
            txt = p.expr()
            p.take(",")
            lab = ""
            while p.peek() not in (None, ",", ")"):
                lab += p.take()
            opts.append((txt, lab))
        p.close_paren()
        kind, kw = "Menu", {"title": title, "opts": opts}
    elif first in ("Lbl ", "Goto "):
        p.take()
        lab = "".join(p.lex[p.i:])
        p.i = len(p.lex)
        kind, kw = first.strip(), {"label": lab}
    elif first == "If ":
        p.take()
        kind, kw = "If", {"cond": p.expr()}
    elif first in ("While ", "Repeat "):
        p.take()
        kind, kw = first.strip(), {"cond": p.expr()}
    elif first == "For(":
        p.take()
        var = p.store_target()
        if var[0] != "var":
            raise TIError("SYNTAX", "For( needs a real variable")
        p.take(",")
        a = p.expr(); p.take(",")
        b = p.expr()
        step = ("num", D1)
        if p.peek() == ",":
            p.take()
            step = p.expr()
        p.close_paren()
        kind, kw = "For", {"var": var[1], "a": a, "b": b, "step": step}
    elif first == "prgm":
        p.take()
        name = "".join(p.lex[p.i:])
        p.i = len(p.lex)
        kind, kw = "prgm", {"name": name}
    elif first == "DelVar ":
        p.take()
        kind, kw = "DelVar", {"target": p.store_target()}
    elif first == "Fix ":
        p.take()
        kind, kw = "Fix", {"n": p.expr()}
    else:
        e = p.expr()
        target = None
        if p.peek() == "→":
            p.take()
            target = p.store_target()
        kind, kw = "Expr", {"e": e, "target": target}
    if not p.at_end():
        raise TIError("SYNTAX", f"unexpected {p.peek()!r} after statement")
    st = Stmt(kind, line, text, **kw)
    st.warnings = p.warnings
    return st


class Program:
    def __init__(self, name, tokens):
        self.name = name
        self.stmts = []
        self.labels = {}
        self.syntax_errors = []
        cur, line = [], 1
        toks = tokens + ["\n"]
        for pos, tok in enumerate(toks):
            if tok in ("\n", ":"):
                text = "".join(cur)
                if not cur and pos < len(toks) - 1:
                    self.stmts.append(Stmt("Nop", line, ""))
                elif cur:
                    try:
                        st = parse_statement(cur, line, text, f"{name}:{line}")
                    except TIError as e:
                        st = Stmt("BadSyntax", line, text, err=e)
                        self.syntax_errors.append((line, text, str(e)))
                    self.stmts.append(st)
                    if st.kind == "Lbl":
                        self.labels.setdefault(st.label, len(self.stmts) - 1)
                cur = []
                if tok == "\n":
                    line += 1
            else:
                cur.append(tok)


# --------------------------------------------------------------------------- machine

class Frame:
    def __init__(self, prog):
        self.prog = prog
        self.pc = 0
        self.blocks = []     # entries: (kind, stmt_index)


class Result:
    def __init__(self):
        self.events = []          # ('screen', rows) | ('menu', title, items, choice) | ('input', prompt, value)
        self.error = None         # TIError
        self.error_at = None      # (program, line, text)
        self.problems = []        # non-fatal problems: leaks, truncation, scrolling
        self.waiting = False      # stopped because the script ran out
        self.finished = False
        self.steps = 0
        self.vars = {}
        self.strs = {}
        self.lists = {}
        self.calls = []

    @property
    def screens(self):
        return [e[1] for e in self.events if e[0] == "screen"]

    def text(self):
        out = []
        for e in self.events:
            if e[0] == "screen":
                out.append("+" + "-" * COLS + "+")
                for r in e[1]:
                    out.append("|" + r.ljust(COLS) + "|")
                out.append("+" + "-" * COLS + "+  [Pause: ENTER]")
            elif e[0] == "menu":
                out.append(f"MENU {e[1]!r}: " + "  ".join(f"{i}:{t}" for i, t in enumerate(e[2], 1))
                           + f"   -> chose {e[3]}")
            elif e[0] == "input":
                out.append(f"INPUT {e[1]!r} <- {e[2]}")
            elif e[0] == "note":
                out.append(f"... {e[1]}")
        if self.error:
            out.append(f"*** {self.error} at {self.error_at}")
        for p in self.problems:
            out.append(f"!!! {p}")
        if self.waiting:
            out.append("... (script ended while the program was waiting for input)")
        return "\n".join(out)


class TISim:
    def __init__(self, programs, seed=0):
        self.programs = programs
        self.seed = seed
        self.coverage = set()     # (program, statement index) executed in any run
        self.call_alias = None    # optional f(program name, variables) -> name to record in Result.calls

    @classmethod
    def load(cls, use_src=False, root=ROOT, **kw):
        progs = {}
        if use_src:
            for p in sorted((root / "src").glob("*.txt")):
                progs[p.stem] = Program(p.stem, load_tokens_from_src(p))
        else:
            for p in sorted((root / "8xp").glob("*.8xp")):
                progs[p.stem] = Program(p.stem, load_tokens_from_8xp(p))
        return cls(progs, **kw)

    def syntax_errors(self):
        out = []
        for name, prog in self.programs.items():
            for line, text, err in prog.syntax_errors:
                out.append(f"{name}:{line}: {err}: {text}")
        return out

    # ------------------------------------------------------------------ run
    def run(self, name, script=(), *, init_vars=None, init_strs=None, angle="Radian",
            disp_mode=("Float", None), max_steps=400000, random_init=True, seed=None,
            strict=True, responder=None, wide=False):
        """Run program `name` with scripted input. Returns a Result.

        responder: optional function(kind, info) used instead of `script`; kind is "menu"
        (info = (title, items)) or "input" (info = prompt). Raise ScriptEnd to stop."""
        rng = random.Random(self.seed if seed is None else seed)
        self.res = res = Result()
        self.script = list(script)
        self.responder = responder
        self.wide = wide        # worst-case widths: every ZFMT result shown as 9 chars, inputs typed as 9 chars
        self.angle = angle
        self.mode = disp_mode
        self.vars = {}
        if random_init:
            for v in LETTERS:
                self.vars[v] = norm(Decimal(rng.choice([-1, 1]) * rng.randint(0, 99999)) / 100)
        self.vars.update({k: norm(Decimal(str(v))) for k, v in (init_vars or {}).items()})
        self.strs = dict(init_strs or {})
        self.lists = {}
        self.ans = D0
        self.screen = [""] * ROWS
        self.row = 0            # next row Disp writes to (0-based)
        self.dirty_since_clear = False
        self.strict = strict
        if name not in self.programs:
            raise KeyError(name)
        stack = [Frame(self.programs[name])]
        res.calls.append(name)
        try:
            while stack:
                fr = stack[-1]
                if fr.pc >= len(fr.prog.stmts):
                    self._return(stack, implicit=True)
                    continue
                st = fr.prog.stmts[fr.pc]
                res.steps += 1
                self.coverage.add((fr.prog.name, fr.pc))
                if res.steps > max_steps:
                    raise StepLimit()
                try:
                    try:
                        self.exec(st, fr, stack)
                    except (ScriptEnd, StepLimit, TIError):
                        raise
                    except InvalidOperation as e:
                        raise TIError("DOMAIN", f"invalid operation {e!r}")
                    except OverflowError:
                        raise TIError("OVERFLOW")
                    except ZeroDivisionError:
                        raise TIError("DIVIDE BY 0")
                    except Exception as e:
                        raise TIError("SIMBUG", repr(e))
                except TIError as e:
                    res.error = e
                    res.error_at = (fr.prog.name, st.line, st.text)
                    break
            else:
                res.finished = True
        except ScriptEnd:
            res.waiting = True
        except StepLimit:
            res.error = TIError("TIMEOUT", f"more than {max_steps} statements (infinite loop?)")
        res.vars = dict(self.vars)
        res.strs = dict(self.strs)
        res.lists = {k: list(v) for k, v in self.lists.items()}
        res.angle = self.angle
        return res

    def problem(self, msg, fr=None, st=None):
        where = f"{fr.prog.name}:{st.line} `{st.text}`" if fr and st else ""
        self.res.problems.append(f"{msg} {where}".strip())

    def _return(self, stack, implicit=False):
        fr = stack.pop()
        if self.wide and fr.prog.name == "ZFMT" and "Str9" in self.strs:
            self.strs["Str9"] = "-8.88E-88"
        if fr.blocks and self.strict:
            st = fr.prog.stmts[min(fr.pc, len(fr.prog.stmts) - 1)]
            self.problem(f"LEAK: program {'ended' if implicit else 'returned'} inside an open "
                         f"{fr.blocks[-1][0]} block", fr, st)
        if stack:
            stack[-1].pc += 1

    # ------------------------------------------------------------------ screen
    def _newline_row(self):
        if self.row >= ROWS:
            self.screen = self.screen[1:] + [""]
            self.row = ROWS - 1
            self.res.problems.append("SCROLL: home screen scrolled (a line was pushed off the top)")
        r = self.row
        self.row += 1
        return r

    def _write_line(self, text, fr, st, right=False):
        if len(text) > COLS:
            self.problem(f"TRUNCATED: {len(text)}-char line shown as '{text[:COLS - 1]}…'", fr, st)
            text = text[:COLS - 1] + "…"
        r = self._newline_row()
        self.screen[r] = text.rjust(COLS) if right else text
        self.dirty_since_clear = True

    def _write_wrapped(self, text):
        """Write text starting on a new row, wrapping at 26 columns (Input/Prompt echo)."""
        while True:
            r = self._newline_row()
            self.screen[r] = text[:COLS]
            text = text[COLS:]
            if not text:
                break
        self.dirty_since_clear = True

    def snapshot(self):
        self.res.events.append(("screen", list(self.screen)))

    # ------------------------------------------------------------------ input
    def next_input(self, kind="input", info=None):
        if self.responder is not None:
            return self.responder(kind, info)
        if not self.script:
            raise ScriptEnd()
        return self.script.pop(0)

    def parse_input_value(self, raw, target):
        if target[0] == "strvar":
            return str(raw)
        if isinstance(raw, (int, float, Decimal)):
            return norm(Decimal(str(raw)))
        # a TI expression typed by the user, e.g. "50/1.0936" or "⁻9.8" (a string starting with the
        # subtraction sign '-' is what pressing [-] instead of [(-)] gives: ERR:SYNTAX)
        txt = str(raw)
        if txt.startswith("-"):
            raise TIError("SYNTAX", "typed the subtraction key '-' instead of the negative key '(-)'")
        lex = []
        i = 0
        multi = sorted(FUNCS1 | FUNCSN | {"⁻¹", "π"}, key=len, reverse=True)
        while i < len(txt):
            for m in multi:
                if txt.startswith(m, i):
                    lex.append(m)
                    i += len(m)
                    break
            else:
                lex.append(txt[i])
                i += 1
        p = Parser(lex, "input")
        v = self.eval(p.expr())
        if not p.at_end():
            raise TIError("SYNTAX", f"bad input {raw!r}")
        return num(v)

    # ------------------------------------------------------------------ exec
    def find_block_end(self, fr, start, want_else):
        """Index of the matching Else (if want_else) or End for a block opened at `start`."""
        depth = 0
        stmts = fr.prog.stmts
        for j in range(start + 1, len(stmts)):
            k = stmts[j].kind
            if k in ("Then", "While", "Repeat", "For"):
                depth += 1
            elif k == "End":
                if depth == 0:
                    return j
                depth -= 1
            elif k == "Else" and depth == 0 and want_else:
                return j
        raise TIError("SYNTAX", "missing End")

    def jump(self, fr, label, st):
        if label not in fr.prog.labels:
            raise TIError("LABEL", label)
        if fr.blocks and self.strict:
            self.problem(f"LEAK: jump to label {label} from inside an open {fr.blocks[-1][0]} block", fr, st)
            fr.blocks = []
        fr.pc = fr.prog.labels[label]

    def exec(self, st, fr, stack):
        k = st.kind
        if k == "BadSyntax":
            raise st.err
        if k == "Nop":
            fr.pc += 1
            return
        if k == "Expr":
            v = self.eval(st.e)
            self.ans = v
            if st.target is not None:
                self.store(st.target, v)
            fr.pc += 1
        elif k == "ClrHome":
            self.screen = [""] * ROWS
            self.row = 0
            self.dirty_since_clear = False
            fr.pc += 1
        elif k == "Disp":
            if not st.items:
                pass
            for it in st.items:
                v = self.eval(it)
                if isinstance(v, str):
                    self._write_line(v, fr, st)
                elif isinstance(v, list):
                    self._write_line("{" + " ".join(fmt_num(x, self.mode) for x in v) + "}", fr, st, right=True)
                else:
                    self._write_line(fmt_num(v, self.mode), fr, st, right=True)
            fr.pc += 1
        elif k == "Output":
            r = self.int_arg(self.eval(st.r))
            c = self.int_arg(self.eval(st.c))
            if not (1 <= r <= ROWS and 1 <= c <= COLS):
                raise TIError("DOMAIN", f"Output({r},{c},...)")
            v = self.eval(st.v)
            s = v if isinstance(v, str) else fmt_num(v, self.mode)
            pos = (r - 1) * COLS + (c - 1)
            for ch in s:
                if pos >= ROWS * COLS:
                    self.problem("TRUNCATED: Output( text ran off the bottom of the screen", fr, st)
                    break
                rr, cc = divmod(pos, COLS)
                line = self.screen[rr].ljust(COLS)
                self.screen[rr] = (line[:cc] + ch + line[cc + 1:]).rstrip()
                pos += 1
            self.dirty_since_clear = True
            fr.pc += 1
        elif k == "Pause":
            if st.v is not None:
                v = self.eval(st.v)
                self._write_line(v if isinstance(v, str) else fmt_num(v, self.mode), fr, st,
                                 right=not isinstance(v, str))
            self.snapshot()
            fr.pc += 1
        elif k == "Input":
            prompt = st.prompt if st.prompt is not None else "?"
            if st.target is None:
                raise TIError("SYNTAX", "Input without a variable is not supported")
            raw = self.next_input("input", prompt)
            val = self.parse_input_value(raw, st.target)
            shown = val if isinstance(val, str) else (str(raw) if not isinstance(raw, (int, float, Decimal))
                                                       else fmt_num(val))
            if self.wide:
                shown = shown.ljust(9, "_")
            self._write_wrapped(prompt + shown)
            self.res.events.append(("input", prompt, shown))
            self.store(st.target, val)
            fr.pc += 1
        elif k == "Prompt":
            for tg in st.targets:
                label = tg[1] if tg[0] in ("var", "strvar") else "ʟ" + tg[1]
                raw = self.next_input("input", f"{label}=?")
                val = self.parse_input_value(raw, tg)
                shown = val if isinstance(val, str) else fmt_num(val)
                self._write_wrapped(f"{label}=?{shown}")
                self.res.events.append(("input", f"{label}=?", shown))
                self.store(tg, val)
            fr.pc += 1
        elif k == "Menu":
            title = self.eval(st.title)
            items = [self.eval(t) for t, _ in st.opts]
            if not isinstance(title, str) or not all(isinstance(t, str) for t in items):
                raise TIError("DATA TYPE", "Menu( text must be strings")
            if len(items) > MENU_MAX or not items:
                raise TIError("ARGUMENT", f"Menu( with {len(items)} options")
            for t in [title] + items:
                if len(t) > COLS:
                    self.problem(f"TRUNCATED: menu text {t!r}", fr, st)
            raw = self.next_input("menu", (title, items))
            choice = None
            if isinstance(raw, int) and 1 <= raw <= len(items):
                choice = raw
            elif isinstance(raw, str):
                for i, t in enumerate(items, 1):
                    if t.startswith(raw) or t.strip().startswith(raw):
                        choice = i
                        break
            if choice is None:
                raise TIError("SCRIPT", f"menu {title!r} has no option {raw!r}; options: {items}")
            self.res.events.append(("menu", title, items, choice))
            self.jump(fr, st.opts[choice - 1][1], st)
        elif k == "Lbl":
            fr.pc += 1
        elif k == "Goto":
            self.jump(fr, st.label, st)
        elif k == "If":
            cond = self.truth(self.eval(st.cond))
            nxt = fr.prog.stmts[fr.pc + 1] if fr.pc + 1 < len(fr.prog.stmts) else None
            if nxt is not None and nxt.kind == "Then":
                then_i = fr.pc + 1
                if cond:
                    fr.blocks.append(("If", then_i))
                    fr.pc = then_i + 1
                else:
                    j = self.find_block_end(fr, then_i, want_else=True)
                    if fr.prog.stmts[j].kind == "Else":
                        fr.blocks.append(("Else", j))
                    fr.pc = j + 1
            else:
                if nxt is not None and nxt.kind in ("Else", "End", "Lbl"):
                    self.problem(f"single-line If followed by {nxt.kind}", fr, st)
                fr.pc += 1 if cond else 2
        elif k == "Then":
            raise TIError("SYNTAX", "Then without If")
        elif k == "Else":
            # reached the end of a true branch: skip to the matching End
            if not fr.blocks or fr.blocks[-1][0] != "If":
                raise TIError("SYNTAX", "Else without If-Then")
            fr.blocks.pop()
            fr.pc = self.find_block_end(fr, fr.pc, want_else=False) + 1
        elif k == "End":
            if not fr.blocks:
                raise TIError("SYNTAX", "End without a block")
            kind, at = fr.blocks[-1]
            if kind == "While":
                fr.blocks.pop()
                fr.pc = at           # re-test the While condition
            elif kind == "Repeat":
                if self.truth(self.eval(fr.prog.stmts[at].cond)):
                    fr.blocks.pop()
                    fr.pc += 1
                else:
                    fr.pc = at + 1
            elif kind == "For":
                fst = fr.prog.stmts[at]
                step = num(self.eval(fst.step))
                v = norm(self.vars.get(fst.var, D0) + step)
                self.vars[fst.var] = v
                end = num(self.eval(fst.b))
                if (step > 0 and v > end) or (step < 0 and v < end):
                    fr.blocks.pop()
                    fr.pc += 1
                else:
                    fr.pc = at + 1
            else:
                fr.blocks.pop()
                fr.pc += 1
        elif k == "While":
            if self.truth(self.eval(st.cond)):
                fr.blocks.append(("While", fr.pc))
                fr.pc += 1
            else:
                fr.pc = self.find_block_end(fr, fr.pc, want_else=False) + 1
        elif k == "Repeat":
            fr.blocks.append(("Repeat", fr.pc))
            fr.pc += 1
        elif k == "For":
            a = num(self.eval(st.a))
            b = num(self.eval(st.b))
            s = num(self.eval(st.step))
            if s == 0:
                raise TIError("INCREMENT")
            self.vars[st.var] = a
            if (s > 0 and a > b) or (s < 0 and a < b):
                fr.pc = self.find_block_end(fr, fr.pc, want_else=False) + 1
            else:
                fr.blocks.append(("For", fr.pc))
                fr.pc += 1
        elif k == "Return":
            if fr.blocks and self.strict:
                self.problem(f"LEAK: Return inside an open {fr.blocks[-1][0]} block", fr, st)
                fr.blocks = []
            self._return(stack)
        elif k == "Stop":
            stack.clear()
        elif k == "prgm":
            if st.name not in self.programs:
                raise TIError("UNDEFINED", f"prgm{st.name}")
            if len(stack) >= 12:
                raise TIError("MEMORY", "programs nested too deeply (recursion?)")
            self.res.calls.append(self.call_alias(st.name, self.vars) if self.call_alias else st.name)
            stack.append(Frame(self.programs[st.name]))
        elif k == "DelVar":
            tg = st.target
            if tg[0] == "var":
                self.vars[tg[1]] = D0
            elif tg[0] == "strvar":
                self.strs.pop(tg[1], None)
            elif tg[0] == "lvar":
                self.lists.pop(tg[1], None)
            else:
                raise TIError("SYNTAX", "DelVar of a list element")
            fr.pc += 1
        elif k in ("Degree", "Radian"):
            self.angle = k
            fr.pc += 1
        elif k in ("Float", "Normal"):
            if k == "Float":
                self.mode = ("Float", None)
            fr.pc += 1
        elif k == "Fix":
            n = self.int_arg(self.eval(st.n))
            if not 0 <= n <= 9:
                raise TIError("DOMAIN", "Fix")
            self.mode = ("Fix", n)
            fr.pc += 1
        else:
            raise TIError("SYNTAX", f"unknown statement kind {k}")

    # ------------------------------------------------------------------ eval
    def truth(self, v):
        return num(v) != 0

    def int_arg(self, v):
        v = num(v)
        if v != v.to_integral_value():
            raise TIError("DOMAIN", f"{v} is not an integer")
        return int(v)

    def store(self, target, v):
        kind = target[0]
        if kind == "var":
            if not isinstance(v, Decimal):
                raise TIError("DATA TYPE", f"storing {type(v).__name__} to {target[1]}")
            self.vars[target[1]] = v
        elif kind == "strvar":
            if not isinstance(v, str):
                raise TIError("DATA TYPE", f"storing a number to {target[1]}")
            if v == "":
                self.res.problems.append(f"EMPTY STRING stored to {target[1]} (may not work on the calculator)")
            self.strs[target[1]] = v
        elif kind == "lvar":
            if isinstance(v, Decimal):
                raise TIError("DATA TYPE", "storing a number to a list")
            if not isinstance(v, list):
                raise TIError("DATA TYPE", "storing a string to a list")
            self.lists[target[1]] = list(v)
        elif kind == "lidx":
            idx = self.int_arg(self.eval(target[2]))
            lst = self.lists.get(target[1])
            if lst is None:
                if idx == 1:
                    lst = self.lists[target[1]] = []
                else:
                    raise TIError("UNDEFINED", "ʟ" + target[1])
            if not 1 <= idx <= len(lst) + 1:
                raise TIError("INVALID DIM", f"ʟ{target[1]}({idx})")
            v = num(v)
            if idx == len(lst) + 1:
                lst.append(v)
            else:
                lst[idx - 1] = v

    def angle_in(self, x):
        """Convert an angle argument to radians (as float)."""
        x = float(x)
        return math.radians(x) if self.angle == "Degree" else x

    def angle_out(self, r):
        return math.degrees(r) if self.angle == "Degree" else r

    def trig(self, f, x):
        if self.angle == "Degree":
            xm = Decimal(x) % 360
            if f == "tan(" and (xm % 180) == 90:
                raise TIError("DOMAIN", f"tan({x})")
            exact = {"sin(": {0: 0, 90: 1, 180: 0, 270: -1}, "cos(": {0: 1, 90: 0, 180: -1, 270: 0},
                     "tan(": {0: 0, 180: 0}}[f]
            if xm in exact:
                return norm(Decimal(exact[int(xm)]))
        r = self.angle_in(x)
        val = {"sin(": math.sin, "cos(": math.cos, "tan(": math.tan}[f](r)
        if abs(val) < 1e-13:
            val = 0.0
        if f == "tan(" and abs(val) > 1e15:
            raise TIError("DOMAIN", f"tan({x})")
        return norm(val)

    def call(self, f, args):
        def need(n):
            if len(args) != n:
                raise TIError("ARGUMENT", f"{f} takes {n} argument(s)")
        if f == "round(":
            if len(args) not in (1, 2):
                raise TIError("ARGUMENT", "round(")
            x = num(args[0])
            n = 9 if len(args) == 1 else self.int_arg(args[1])
            if not 0 <= n <= 9:
                raise TIError("DOMAIN", f"round(x,{n})")
            return norm(x.quantize(Decimal(1).scaleb(-n), rounding=ROUND_HALF_UP, context=Context(prec=60)))
        if f == "sub(":
            need(3)
            s = args[0]
            if not isinstance(s, str):
                raise TIError("DATA TYPE", "sub( needs a string")
            a, n = self.int_arg(args[1]), self.int_arg(args[2])
            if a < 1 or n < 1 or a + n - 1 > len(s):
                raise TIError("DOMAIN" if (a < 1 or n < 1) else "INVALID DIM", f"sub(\"{s}\",{a},{n})")
            return s[a - 1:a - 1 + n]
        if f == "length(":
            need(1)
            if not isinstance(args[0], str):
                raise TIError("DATA TYPE", "length( needs a string")
            return Decimal(len(args[0]))
        if f in ("dim(", "sum("):
            need(1)
            if not isinstance(args[0], list):
                raise TIError("DATA TYPE", f"{f} needs a list")
            return Decimal(len(args[0])) if f == "dim(" else norm(sum(args[0], D0))
        if f in ("min(", "max("):
            need(2)
            a, b = num(args[0]), num(args[1])
            return min(a, b) if f == "min(" else max(a, b)
        if f in ("R►Pr(", "R►Pθ(", "P►Rx(", "P►Ry("):
            need(2)
            a, b = num(args[0]), num(args[1])
            if f == "R►Pr(":
                return norm((a * a + b * b).sqrt(CTX))
            if f == "R►Pθ(":
                if a == 0 and b == 0:
                    return D0
                return norm(self.angle_out(math.atan2(float(b), float(a))))
            r = self.angle_in(b)
            val = a * norm(math.cos(r) if f == "P►Rx(" else math.sin(r))
            if self.angle == "Degree":
                val = a * self.trig("cos(" if f == "P►Rx(" else "sin(", b)
            return norm(val)
        need(1)
        x = args[0]
        if f == "not(":
            return D1 if num(x) == 0 else D0
        x = num(x)
        if f == "abs(":
            return abs(x)
        if f == "int(":
            return x.to_integral_value(rounding=ROUND_FLOOR)
        if f == "iPart(":
            return x.to_integral_value(rounding=ROUND_DOWN)
        if f == "fPart(":
            return norm(x - x.to_integral_value(rounding=ROUND_DOWN))
        if f in ("log(", "ln("):
            if x == 0:
                raise TIError("DOMAIN", f"{f}0)")
            if x < 0:
                raise TIError("NONREAL ANS", f"{f}{x})")
            if f == "log(":
                return norm(x.log10(CTX))
            return norm(x.ln(CTX))
        if f == "₁₀^(":
            if x == x.to_integral_value() and abs(x) < 200:
                return norm(Decimal(1).scaleb(int(x)))
            return norm(10 ** float(x))
        if f == "𝑒^(":
            if float(x) > 231:
                raise TIError("OVERFLOW")
            return norm(math.exp(float(x)))
        if f == "√(":
            if x < 0:
                raise TIError("NONREAL ANS", f"√({x})")
            return norm(x.sqrt(CTX))
        if f in ("sin(", "cos(", "tan("):
            return self.trig(f, x)
        if f in ("sin⁻¹(", "cos⁻¹("):
            if abs(x) > 1:
                raise TIError("DOMAIN", f"{f}{x})")
            r = math.asin(float(x)) if f == "sin⁻¹(" else math.acos(float(x))
            return norm(self.angle_out(r))
        if f == "tan⁻¹(":
            return norm(self.angle_out(math.atan(float(x))))
        raise TIError("SYNTAX", f"unknown function {f}")

    def eval(self, e):
        k = e[0]
        if k == "num":
            return e[1]
        if k == "str":
            return e[1]
        if k == "var":
            return self.vars.get(e[1], D0)
        if k == "strvar":
            if e[1] not in self.strs:
                raise TIError("UNDEFINED", e[1])
            return self.strs[e[1]]
        if k == "ans":
            return self.ans
        if k == "list":
            return [num(self.eval(x)) for x in e[1]]
        if k == "lvar":
            if e[1] not in self.lists:
                raise TIError("UNDEFINED", "ʟ" + e[1])
            return list(self.lists[e[1]])
        if k == "lidx":
            if e[1] not in self.lists:
                raise TIError("UNDEFINED", "ʟ" + e[1])
            i = self.int_arg(self.eval(e[2]))
            lst = self.lists[e[1]]
            if not 1 <= i <= len(lst):
                raise TIError("INVALID DIM", f"ʟ{e[1]}({i})")
            return lst[i - 1]
        if k == "neg":
            return norm(-num(self.eval(e[1])))
        if k == "post":
            x = num(self.eval(e[2]))
            op = e[1]
            if op == "²":
                return norm(x * x)
            if op == "³":
                return norm(x * x * x)
            if op == "⁻¹":
                if x == 0:
                    raise TIError("DIVIDE BY 0")
                return norm(D1 / x)
            if op == "°":
                return x if self.angle == "Degree" else norm(math.radians(float(x)))
            if op == "!":
                if x < 0 or x != x.to_integral_value() or x > 69:
                    raise TIError("DOMAIN", "!")
                return norm(Decimal(math.factorial(int(x))))
        if k == "call":
            return self.call(e[1], [self.eval(a) for a in e[2]])
        if k == "bin":
            op = e[1]
            a = self.eval(e[2])
            b = self.eval(e[3])
            if op == "+" and isinstance(a, str) and isinstance(b, str):
                return a + b
            if isinstance(a, str) or isinstance(b, str):
                raise TIError("DATA TYPE", f"string in '{op}'")
            a, b = num(a), num(b)
            if op == "+":
                return norm(a + b)
            if op == "-":
                return norm(a - b)
            if op == "*":
                return norm(a * b)
            if op == "/":
                if b == 0:
                    raise TIError("DIVIDE BY 0")
                return norm(CTX.divide(a, b))
            if op == "^":
                if a == 0 and b == 0:
                    raise TIError("DOMAIN", "0^0")
                if a == 0 and b < 0:
                    raise TIError("DIVIDE BY 0")
                if b == b.to_integral_value() and abs(b) <= 400:
                    if b >= 0:
                        return norm(CTX.power(a, int(b)))
                    return norm(CTX.divide(D1, CTX.power(a, -int(b))))
                if a < 0:
                    raise TIError("NONREAL ANS", f"{a}^{b}")
                return norm(float(a) ** float(b))
            if op in RELOPS:
                r = {"=": a == b, "≠": a != b, "<": a < b, ">": a > b, "≤": a <= b, "≥": a >= b}[op]
                return D1 if r else D0
            if op == "and":
                return D1 if (a != 0 and b != 0) else D0
            if op == "or":
                return D1 if (a != 0 or b != 0) else D0
            if op == "xor":
                return D1 if ((a != 0) != (b != 0)) else D0
        raise TIError("SYNTAX", f"cannot evaluate {e!r}")


def main(argv):
    use_src = "--src" in argv
    argv = [a for a in argv if a != "--src"]
    if not argv:
        print(__doc__)
        return 2
    sim = TISim.load(use_src=use_src)
    errs = sim.syntax_errors()
    for e in errs:
        print("SYNTAX:", e)
    script = []
    for a in argv[1:]:
        try:
            script.append(int(a))
        except ValueError:
            try:
                script.append(float(a))
            except ValueError:
                script.append(a)
    res = sim.run(argv[0], script)
    print(res.text())
    return 1 if (res.error or errs) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
