"""
A model of the TI-84 Plus CE running TI-BASIC on the home screen, for testing.

Covers the subset the HPCANS programs use: real/string/list variables, the
14-digit arithmetic, expressions with TI precedence and implicit multiplication,
If/Then/Else/End, For(/While/Repeat, Lbl/Goto, prgm calls + Return/Stop,
Disp/Output(/Input/ClrHome/Pause/getKey on a 26 x 10 screen, and the string
and list functions.  It is strict where the real calculator is merely
forgiving: reading a variable never stored in this run, a Disp line wider than
the screen, a jump out of a block, or a closing parenthesis left off are errors.

A run is driven by a script of user actions:
    "k1".."k9","k0"  number keys     "ENTER", "CLEAR"  keys
    "t:TEXT"         type TEXT at an Input prompt and press ENTER
"""

import decimal
import math
import re
from pathlib import Path

from tokens import tokenize, tokenize_text, width as tok_width

COLS, ROWS = 26, 10
D = decimal.Decimal
CTX = decimal.Context(prec=14, rounding=decimal.ROUND_HALF_UP, Emax=999, Emin=-999)
BIG = D("1E99")

KEYCODES = {"k1": 92, "k2": 93, "k3": 94, "k4": 82, "k5": 83, "k6": 84, "k7": 72, "k8": 73,
            "k9": 74, "k0": 102, "ENTER": 105, "CLEAR": 45, "UP": 25, "DOWN": 34}


class TIError(Exception):
    pass


class Halt(Exception):
    pass


def num(x):
    if isinstance(x, D):
        return CTX.plus(x)
    return CTX.create_decimal(repr(float(x))) if isinstance(x, float) else CTX.create_decimal(x)


def is_int(v):
    return v == v.to_integral_value()


class TIStr(tuple):
    """A string value: a tuple of token names."""


# ----------------------------------------------------------------------------
# expression parsing
# ----------------------------------------------------------------------------

FUNC1 = {"abs(", "fPart(", "iPart(", "int(", "not(", "√(", "³√(", "length(", "expr(", "dim(", "sum("}
FUNCN = {"round(", "gcd(", "lcm(", "min(", "max(", "sub(", "inString(", "augment(", "seq("}
VARS = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ") | {"θ"}
STRVARS = {f"Str{i}" for i in range(10)}
LISTVARS = {"L₁", "L₂", "L₃", "L₄", "L₅", "L₆"}
NAMECH = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789θ")


class P:
    """Recursive-descent parser over one line's tokens (from position i)."""

    def __init__(self, toks, i=0, where=""):
        self.t, self.i, self.where = toks, i, where

    def peek(self, k=0):
        j = self.i + k
        return self.t[j] if j < len(self.t) else None

    def take(self, want=None):
        tok = self.peek()
        if want is not None and tok != want:
            raise TIError(f"{self.where}: ERR:SYNTAX expected {want!r} got {tok!r}")
        self.i += 1
        return tok

    def close(self):
        # every ( must be closed in the sources (the checker is strict about it)
        if self.peek() != ")":
            raise TIError(f"{self.where}: ERR:SYNTAX missing ')' at {self.peek()!r}")
        self.i += 1

    def expr(self):
        node = self.p_and()
        while self.peek() in (" or ", " xor "):
            node = (self.take().strip(), node, self.p_and())
        return node

    def p_and(self):
        node = self.p_rel()
        while self.peek() == " and ":
            self.take()
            node = ("and", node, self.p_rel())
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

    STARTS = {"(", "{", '"', "θ", "ʟ", "getKey", "ᴇ", "."} | VARS | STRVARS | LISTVARS | FUNC1 | FUNCN \
        | set("0123456789")

    def p_mul(self):
        node = self.p_neg()
        while True:
            t = self.peek()
            if t in ("*", "/"):
                self.take()
                node = (t, node, self.p_neg())
            elif t in self.STARTS and t != '"':
                node = ("*", node, self.p_neg())  # implicit multiplication
            else:
                return node

    def p_neg(self):
        if self.peek() == "⁻":
            self.take()
            return ("neg", self.p_neg())
        if self.peek() == "-":
            raise TIError(f"{self.where}: ERR:SYNTAX subtraction sign used as a negative")
        return self.p_pow()

    def p_pow(self):
        node = self.p_post()
        while self.peek() == "^":
            self.take()
            neg = False
            while self.peek() == "⁻":
                self.take()
                neg = not neg
            rhs = self.p_post()
            node = ("^", node, ("neg", rhs) if neg else rhs)
        return node

    def p_post(self):
        node = self.p_atom()
        while self.peek() in ("²", "³", "⁻¹"):
            t = self.take()
            node = ("^", node, ("num", D(2))) if t == "²" else ("^", node, ("num", D(3))) if t == "³" \
                else ("/", ("num", D(1)), node)
        return node

    def number(self):
        s = ""
        while self.peek() is not None and (self.peek().isdigit() or self.peek() == "."):
            s += self.take()
        if self.peek() == "ᴇ":
            self.take()
            e = ""
            if self.peek() == "⁻":
                self.take()
                e = "-"
            while self.peek() is not None and self.peek().isdigit():
                e += self.take()
            s = (s or "1") + "E" + e
        if s in ("", "."):
            raise TIError(f"{self.where}: ERR:SYNTAX bad number")
        return ("num", num(s))

    def listname(self):
        self.take("ʟ")
        name = ""
        while self.peek() in NAMECH and len(name) < 5:
            name += self.take()
        if not name or not name[0].isalpha():
            raise TIError(f"{self.where}: bad list name")
        return "ʟ" + name

    def p_atom(self):
        t = self.peek()
        if t is None:
            raise TIError(f"{self.where}: ERR:SYNTAX unexpected end")
        if t.isdigit() or t in (".", "ᴇ"):
            return self.number()
        if t == '"':
            self.take()
            body = []
            while self.peek() not in ('"', "→", None):
                body.append(self.take())
            if self.peek() == '"':
                self.take()
            return ("str", TIStr(body))
        if t == "(":
            self.take()
            node = self.expr()
            self.close()
            return node
        if t == "{":
            self.take()
            items = [self.expr()]
            while self.peek() == ",":
                self.take()
                items.append(self.expr())
            self.take("}")
            return ("listlit", items)
        if t in VARS:
            self.take()
            return ("var", t)
        if t in STRVARS:
            self.take()
            return ("svar", t)
        if t in LISTVARS or t == "ʟ":
            name = self.take() if t in LISTVARS else self.listname()
            if self.peek() == "(":
                self.take()
                idx = self.expr()
                self.close()
                return ("elem", name, idx)
            return ("lvar", name)
        if t == "getKey":
            self.take()
            return ("getkey",)
        if t in FUNC1 or t in FUNCN:
            self.take()
            args = [self.expr()]
            while self.peek() == ",":
                self.take()
                args.append(self.expr())
            self.close()
            return ("call", t, args)
        raise TIError(f"{self.where}: ERR:SYNTAX unexpected {t!r}")


def parse_target(p):
    """Parse what follows → : a variable, string, list, list element or dim(list)."""
    t = p.peek()
    if t in VARS:
        p.take()
        return ("var", t)
    if t in STRVARS:
        p.take()
        return ("svar", t)
    if t in LISTVARS or t == "ʟ":
        name = p.take() if t in LISTVARS else p.listname()
        if p.peek() == "(":
            p.take()
            idx = p.expr()
            p.close()
            return ("elem", name, idx)
        return ("lvar", name)
    if t == "dim(":
        p.take()
        name = p.take() if p.peek() in LISTVARS else p.listname()
        p.close()
        return ("dim", name)
    raise TIError(f"{p.where}: ERR:SYNTAX bad store target {t!r}")


def parse_statement(toks, where):
    """Return a statement tuple for one line of tokens."""
    if not toks:
        raise TIError(f"{where}: empty line")
    head = toks[0]
    p = P(toks, 1, where)

    def done(st):
        if p.i != len(toks):
            raise TIError(f"{where}: ERR:SYNTAX extra tokens {toks[p.i:]}")
        return st

    if head == "SetUpEditor" and len(toks) == 1:
        return ("SetUpEditor", [])
    if head in ("ClrHome", "Then", "Else", "End", "Return", "Stop", "Float", "Normal", "Func") and len(toks) == 1:
        return (head,)
    if head == "Pause":
        return ("Pause",) if len(toks) == 1 else done(("Pause", p.expr()))
    if head in ("If ", "While ", "Repeat "):
        return done((head.strip(), p.expr()))
    if head == "For(":
        var = p.take()
        if var not in VARS:
            raise TIError(f"{where}: For( needs a real variable")
        p.take(",")
        a = p.expr()
        p.take(",")
        b = p.expr()
        s = ("num", D(1))
        if p.peek() == ",":
            p.take()
            s = p.expr()
        p.close()
        return done(("For", var, a, b, s))
    if head in ("Lbl ", "Goto "):
        name = "".join(toks[1:])
        if not re.fullmatch(r"[A-Z0-9θ]{1,2}", name):
            raise TIError(f"{where}: bad label {name!r}")
        return (head.strip(), name)
    if head == "prgm":
        name = "".join(toks[1:])
        if not re.fullmatch(r"[A-Zθ][A-Z0-9θ]{0,7}", name):
            raise TIError(f"{where}: bad program name {name!r}")
        return ("prgm", name)
    if head == "Disp ":
        args = [p.expr()]
        while p.peek() == ",":
            p.take()
            args.append(p.expr())
        return done(("Disp", args))
    if head == "Output(":
        r = p.expr()
        p.take(",")
        c = p.expr()
        p.take(",")
        v = p.expr()
        p.close()
        return done(("Output", r, c, v))
    if head == "Input ":
        prompt = None
        if p.peek() == '"':
            prompt = p.p_atom()[1]
            p.take(",")
        tgt = parse_target(p)
        if tgt[0] not in ("var", "svar"):
            raise TIError(f"{where}: Input needs a real or string variable")
        return done(("Input", prompt, tgt))
    if head == "SortA(":
        names = [p.take() if p.peek() in LISTVARS else p.listname()]
        while p.peek() == ",":
            p.take()
            names.append(p.take() if p.peek() in LISTVARS else p.listname())
        p.close()
        return done(("SortA", names))
    if head == "SetUpEditor ":
        names = [p.take() if p.peek() in LISTVARS else p.listname()]
        while p.peek() == ",":
            p.take()
            names.append(p.take() if p.peek() in LISTVARS else p.listname())
        return done(("SetUpEditor", names))
    if head == "DelVar ":
        return done(("DelVar", parse_target(p)))
    # expression [→ target]
    p = P(toks, 0, where)
    e = p.expr()
    if p.peek() == "→":
        p.take()
        tgt = parse_target(p)
        return done(("Store", e, tgt))
    raise TIError(f"{where}: expression without → (TI would show it as Ans)")


# ----------------------------------------------------------------------------
# the machine
# ----------------------------------------------------------------------------

def fmt_number(v):
    """How the home screen shows a number in Float mode (10 significant digits)."""
    v = num(v)
    if v == 0:
        return "0"
    if is_int(v) and abs(v) < D("1E10"):
        s = str(int(v))
    else:
        s = f"{float(v):.10g}"
        if "e" in s:
            m, e = s.split("e")
            s = f"{m}ᴇ{int(e)}"
        if s.startswith("0."):
            s = s[1:]
        elif s.startswith("-0."):
            s = "-" + s[2:]
    return s.replace("-", "⁻")


class Frame:
    def __init__(self, name):
        self.name, self.pc, self.blocks = name, 0, []


class Machine:
    def __init__(self, programs, persistent_lists=None, max_steps=400000):
        self.src = programs  # name -> list of source lines
        self.parsed = {}
        self.labels = {}
        self._toks = {}
        self.reals, self.strs = {}, {}
        self.lists = {k: list(v) for k, v in (persistent_lists or {}).items()}
        self.screen = [[" "] * COLS for _ in range(ROWS)]
        self.row = 0
        self.events = []  # (kind, detail, screen lines)
        self.nstmt, self.last_poll = 0, -100
        self.problems = []
        self.covered = set()
        self.max_steps = max_steps
        self.idle = 0

    # -- screen ---------------------------------------------------------------
    def lines(self):
        return ["".join(r).rstrip() for r in self.screen]

    def clear(self):
        self.screen = [[" "] * COLS for _ in range(ROWS)]
        self.row = 0

    def _cells(self, toks):
        cells = []
        for t in toks:
            if tok_width(t) == 1:
                cells.append(t)
            else:
                cells.extend(list(t))
        return cells

    def newline(self):
        if self.row >= ROWS:
            self.screen = self.screen[1:] + [[" "] * COLS]
            self.row = ROWS - 1
            self.problems.append(f"{self.where()}: screen scrolled")
        r = self.row
        self.row += 1
        return r

    def put(self, r, c, cells, wrap_ok=False):
        if c + len(cells) > COLS and not wrap_ok:
            self.problems.append(f"{self.where()}: text {''.join(cells)!r} wraps past column {COLS}")
        for k, ch in enumerate(cells):
            rr, cc = r + (c + k) // COLS, (c + k) % COLS
            if rr < ROWS:
                self.screen[rr][cc] = ch

    def snap(self, kind, detail=""):
        self.events.append((kind, detail, self.lines()))

    # -- values -----------------------------------------------------------------
    def where(self):
        f = self.frames[-1] if getattr(self, "frames", None) else None
        return f"{f.name}:{f.pc + 1}" if f else "?"

    def getvar(self, kind, name):
        store = {"var": self.reals, "svar": self.strs, "lvar": self.lists}[kind]
        if name not in store:
            raise TIError(f"{self.where()}: ERR:UNDEFINED {name} read before it was stored in this run")
        return store[name]

    def ev(self, n):
        k = n[0]
        if k == "num":
            return n[1]
        if k == "str":
            return n[1]
        if k == "var":
            return self.getvar("var", n[1])
        if k == "svar":
            return self.getvar("svar", n[1])
        if k == "lvar":
            return list(self.getvar("lvar", n[1]))
        if k == "elem":
            lst = self.getvar("lvar", n[1])
            i = self.ev(n[2])
            if not is_int(i) or not 1 <= i <= len(lst):
                raise TIError(f"{self.where()}: ERR:INVALID DIM {n[1]}({i}) dim {len(lst)}")
            return lst[int(i) - 1]
        if k == "listlit":
            return [self.real(self.ev(x)) for x in n[1]]
        if k == "getkey":
            return self.getkey()
        if k == "neg":
            v = self.ev(n[1])
            return [CTX.minus(x) for x in v] if isinstance(v, list) else CTX.minus(self.real(v))
        if k == "call":
            return self.call(n[1], n[2])
        a, b = self.ev(n[1]), self.ev(n[2])
        if k == "+" and isinstance(a, TIStr) and isinstance(b, TIStr):
            return TIStr(a + b)
        if k in ("=", "≠") and isinstance(a, TIStr) and isinstance(b, TIStr):
            return D(int((a == b) == (k == "=")))
        if isinstance(a, list) or isinstance(b, list):
            if isinstance(a, list) and isinstance(b, list) and len(a) != len(b):
                raise TIError(f"{self.where()}: ERR:DIM MISMATCH")
            n_ = len(a) if isinstance(a, list) else len(b)
            aa = a if isinstance(a, list) else [a] * n_
            bb = b if isinstance(b, list) else [b] * n_
            return [self.binop(k, self.real(x), self.real(y)) for x, y in zip(aa, bb)]
        return self.binop(k, self.real(a), self.real(b))

    def real(self, v):
        if not isinstance(v, D):
            raise TIError(f"{self.where()}: ERR:DATA TYPE expected a number, got {v!r}")
        return v

    def binop(self, k, a, b):
        r = self._binop(k, a, b)
        if isinstance(r, D) and k in ("+", "-", "*", "/", "^") and abs(r) >= D("1E100"):
            raise TIError(f"{self.where()}: ERR:OVERFLOW {a} {k} {b}")
        return r

    def _binop(self, k, a, b):
        if k == "+":
            return CTX.add(a, b)
        if k == "-":
            return CTX.subtract(a, b)
        if k == "*":
            return CTX.multiply(a, b)
        if k == "/":
            if b == 0:
                raise TIError(f"{self.where()}: ERR:DIVIDE BY 0")
            return CTX.divide(a, b)
        if k == "^":
            if is_int(b):
                if a == 0 and b < 0:
                    raise TIError(f"{self.where()}: ERR:DIVIDE BY 0")
                return CTX.power(a, int(b))
            if a < 0:
                raise TIError(f"{self.where()}: ERR:NONREAL ANS {a}^{b}")
            if a == 0:
                return D(0)
            return num(float(a) ** float(b))
        if k == "=":
            return D(int(a == b))
        if k == "≠":
            return D(int(a != b))
        if k == "<":
            return D(int(a < b))
        if k == ">":
            return D(int(a > b))
        if k == "≤":
            return D(int(a <= b))
        if k == "≥":
            return D(int(a >= b))
        if k == "and":
            return D(int(a != 0 and b != 0))
        if k == "or":
            return D(int(a != 0 or b != 0))
        if k == "xor":
            return D(int((a != 0) != (b != 0)))
        raise TIError(f"{self.where()}: unknown operator {k}")

    def call(self, f, args):
        if f == "seq(":
            body, var = args[0], args[1]
            if var[0] != "var":
                raise TIError(f"{self.where()}: seq( needs a variable")
            a, b = self.real(self.ev(args[2])), self.real(self.ev(args[3]))
            s = self.real(self.ev(args[4])) if len(args) > 4 else D(1)
            old = self.reals.get(var[1])
            out, x = [], a
            while (s > 0 and x <= b) or (s < 0 and x >= b):
                self.reals[var[1]] = x
                out.append(self.real(self.ev(body)))
                x = CTX.add(x, s)
            if old is None:
                self.reals.pop(var[1], None)
            else:
                self.reals[var[1]] = old
            if not out:
                raise TIError(f"{self.where()}: ERR:INVALID DIM seq( gives no elements")
            return out
        v = [self.ev(a) for a in args]
        if f == "abs(":
            return [abs(x) for x in v[0]] if isinstance(v[0], list) else abs(self.real(v[0]))
        if f == "fPart(":
            x = self.real(v[0])
            return CTX.subtract(x, x.to_integral_value(rounding=decimal.ROUND_DOWN))
        if f == "iPart(":
            return self.real(v[0]).to_integral_value(rounding=decimal.ROUND_DOWN)
        if f == "int(":
            return self.real(v[0]).to_integral_value(rounding=decimal.ROUND_FLOOR)
        if f == "not(":
            return D(int(self.real(v[0]) == 0))
        if f == "round(":
            places = int(self.real(v[1])) if len(v) > 1 else 9
            x = self.real(v[0])
            if x == 0 or x.adjusted() + places + 1 > 28:  # finer than any stored digit: unchanged
                return CTX.plus(x)
            return CTX.plus(x.quantize(D(1).scaleb(-places), rounding=decimal.ROUND_HALF_UP))
        if f == "√(":
            x = self.real(v[0])
            if x < 0:
                raise TIError(f"{self.where()}: ERR:NONREAL ANS sqrt({x})")
            return CTX.sqrt(x)
        if f == "³√(":
            x = self.real(v[0])
            r = num(math.copysign(abs(float(x)) ** (1 / 3), float(x)))
            rr = r.to_integral_value()
            if CTX.power(rr, 3) == x:
                r = rr
            return r
        if f in ("gcd(", "lcm("):
            a, b = self.real(v[0]), self.real(v[1])
            if a < 0 or b < 0 or not is_int(a) or not is_int(b) or a >= D("1E12") or b >= D("1E12"):
                raise TIError(f"{self.where()}: ERR:DOMAIN {f}{a},{b})")
            g = math.gcd(int(a), int(b))
            return D(g) if f == "gcd(" else D(int(a) * int(b) // g if g else 0)
        if f in ("min(", "max("):
            pick = min if f == "min(" else max
            if len(v) == 1:
                if not isinstance(v[0], list) or not v[0]:
                    raise TIError(f"{self.where()}: ERR:DATA TYPE {f} of a non-list")
                return pick(v[0])
            return pick(self.real(v[0]), self.real(v[1]))
        if f == "sum(":
            if not isinstance(v[0], list):
                raise TIError(f"{self.where()}: ERR:DATA TYPE sum(")
            t = D(0)
            for x in v[0]:
                t = CTX.add(t, x)
            return t
        if f == "dim(":
            if not isinstance(v[0], list):
                raise TIError(f"{self.where()}: ERR:DATA TYPE dim(")
            return D(len(v[0]))
        if f == "augment(":
            if not (isinstance(v[0], list) and isinstance(v[1], list)):
                raise TIError(f"{self.where()}: ERR:DATA TYPE augment(")
            if not v[0] or not v[1]:
                raise TIError(f"{self.where()}: ERR:INVALID DIM augment( of an empty list")
            return v[0] + v[1]
        if f == "length(":
            if not isinstance(v[0], TIStr):
                raise TIError(f"{self.where()}: ERR:DATA TYPE length(")
            return D(len(v[0]))
        if f == "sub(":
            s, a, n = v
            if not isinstance(s, TIStr):
                raise TIError(f"{self.where()}: ERR:DATA TYPE sub(")
            a, n = int(self.real(a)), int(self.real(n))
            if a < 1 or n < 1 or a + n - 1 > len(s):
                raise TIError(f"{self.where()}: ERR:DOMAIN sub(len {len(s)},{a},{n})")
            return TIStr(s[a - 1:a - 1 + n])
        if f == "inString(":
            s, sub = v[0], v[1]
            start = int(self.real(v[2])) if len(v) > 2 else 1
            if not (isinstance(s, TIStr) and isinstance(sub, TIStr)):
                raise TIError(f"{self.where()}: ERR:DATA TYPE inString(")
            if len(sub) == 0:
                raise TIError(f"{self.where()}: ERR:INVALID inString( empty")
            for i in range(start - 1, len(s) - len(sub) + 1):
                if tuple(s[i:i + len(sub)]) == tuple(sub):
                    return D(i + 1)
            return D(0)
        if f == "expr(":
            s = v[0]
            if not isinstance(s, TIStr) or len(s) == 0:
                raise TIError(f"{self.where()}: ERR:SYNTAX expr( of {s!r}")
            p = P(list(s), 0, f"{self.where()} expr")
            node = p.expr()
            if p.i != len(s):
                raise TIError(f"{self.where()}: ERR:SYNTAX in expr( {s!r}")
            return self.ev(node)
        raise TIError(f"{self.where()}: unsupported function {f}")

    def store(self, tgt, val):
        k = tgt[0]
        if k == "var":
            self.reals[tgt[1]] = self.real(val) if not isinstance(val, list) else self._bad(val)
        elif k == "svar":
            if not isinstance(val, TIStr):
                raise TIError(f"{self.where()}: ERR:DATA TYPE store {val!r} to {tgt[1]}")
            self.strs[tgt[1]] = val
        elif k == "lvar":
            if not isinstance(val, list):
                raise TIError(f"{self.where()}: ERR:DATA TYPE store to list")
            self.lists[tgt[1]] = list(val)
        elif k == "elem":
            lst = self.lists.setdefault(tgt[1], []) if tgt[1] in self.lists else None
            if lst is None:
                raise TIError(f"{self.where()}: ERR:UNDEFINED list {tgt[1]}")
            i = self.ev(tgt[2])
            if not is_int(i) or not 1 <= i <= len(lst) + 1:
                raise TIError(f"{self.where()}: ERR:INVALID DIM store {tgt[1]}({i}) dim {len(lst)}")
            if i == len(lst) + 1:
                lst.append(self.real(val))
            else:
                lst[int(i) - 1] = self.real(val)
        elif k == "dim":
            n = self.real(val)
            if not is_int(n) or n < 1 or n > 999:
                raise TIError(f"{self.where()}: ERR:INVALID DIM")
            lst = self.lists.get(tgt[1], [])
            n = int(n)
            self.lists[tgt[1]] = (lst + [D(0)] * n)[:n]
        else:
            raise TIError(f"{self.where()}: bad target")

    def _bad(self, v):
        raise TIError(f"{self.where()}: ERR:DATA TYPE list stored to a real")

    # -- user actions -------------------------------------------------------------
    def next_action(self):
        return self.actions[self.ai] if self.ai < len(self.actions) else None

    def getkey(self):
        # A scripted key is a key pressed while the program WAITS for one, i.e. while it polls
        # getKey in a loop.  A lone getKey (like the one HAEND/HAOUT use to throw away a key
        # pressed during a long calculation) finds no key: it returns 0 and keeps the script.
        polling = self.nstmt - self.last_poll <= 10
        self.last_poll = self.nstmt
        if not polling:
            return D(0)
        a = self.next_action()
        if a in KEYCODES:
            self.snap("key", a)
            self.ai += 1
            self.idle = 0
            return D(KEYCODES[a])
        self.idle += 1
        if self.idle > 3000:
            raise Halt(("waiting_key", a))
        return D(0)

    # -- running ------------------------------------------------------------------
    def load(self, name):
        if name in self._toks:
            return
        toks = [tokenize(line) for line in self.src[name]]
        self._toks[name] = toks
        self.parsed[name] = [None] * len(toks)
        self.labels[name] = {"".join(tk[1:]): i for i, tk in enumerate(toks) if tk and tk[0] == "Lbl "}

    def stmt(self, name, i):
        st = self.parsed[name][i]
        if st is None:
            st = parse_statement(self._toks[name][i], f"{name}:{i + 1}")
            self.parsed[name][i] = st
        return st

    def find_end(self, name, i, stop_at_else):
        """From line i (just after a block opener) find the matching Else/End."""
        depth = 1
        lines = self._toks[name]
        j = i
        while j < len(lines):
            h = lines[j][0] if lines[j] else None
            if h in ("Then", "For(", "While ", "Repeat "):
                depth += 1
            elif h == "End":
                depth -= 1
                if depth == 0:
                    return j
            elif h == "Else" and depth == 1 and stop_at_else:
                return j
            j += 1
        raise TIError(f"{name}:{i}: ERR:SYNTAX no matching End")

    def after_return(self, name):
        """Hook: program `name` just returned to self.frames[-1] (tools/poison.py uses it)."""

    def run(self, actions, start="HPCANS"):
        self.actions, self.ai = list(actions), 0
        self.frames = [Frame(start)]
        steps = 0
        try:
            while self.frames:
                steps += 1
                if steps > self.max_steps:
                    raise Halt(("step_limit", None))
                f = self.frames[-1]
                self.load(f.name)
                lines = self.src[f.name]
                if f.pc >= len(lines):
                    if f.blocks:
                        self.problems.append(f"{f.name}: program ended inside a block")
                    self.frames.pop()
                    self.after_return(f.name)
                    continue
                self.covered.add((f.name, f.pc))
                self.exec(f)
            return ("done", None)
        except Halt as h:
            return h.args[0]

    def exec(self, f):
        self.nstmt += 1
        st = self.stmt(f.name, f.pc)
        k = st[0]
        name, i = f.name, f.pc
        nxt = i + 1
        if k == "Store":
            self.store(st[2], self.ev(st[1]))
        elif k == "Disp":
            for a in st[1]:
                v = self.ev(a)
                r = self.newline()
                if isinstance(v, TIStr):
                    cells = self._cells(v)
                    if len(cells) > COLS:
                        self.problems.append(f"{self.where()}: Disp text wider than {COLS}: {''.join(cells)}")
                    self.put(r, 0, cells[:COLS])
                else:
                    s = fmt_number(self.real(v))
                    self.put(r, COLS - len(s), list(s))
        elif k == "Output":
            r, c, v = self.real(self.ev(st[1])), self.real(self.ev(st[2])), self.ev(st[3])
            if not (is_int(r) and is_int(c) and 1 <= r <= ROWS and 1 <= c <= COLS):
                raise TIError(f"{self.where()}: ERR:DOMAIN Output({r},{c})")
            cells = self._cells(v) if isinstance(v, TIStr) else list(fmt_number(self.real(v)))
            self.put(int(r) - 1, int(c) - 1, cells)
        elif k == "ClrHome":
            self.clear()
        elif k == "Pause":
            if len(st) > 1:
                v = self.ev(st[1])
                r = self.newline()
                self.put(r, 0, self._cells(v) if isinstance(v, TIStr) else list(fmt_number(v)))
            self.snap("pause")
            if self.next_action() == "ENTER":
                self.ai += 1
        elif k == "Input":
            prompt, tgt = st[1], st[2]
            a = self.next_action()
            if a is None or not a.startswith("t:"):
                raise Halt(("waiting_input", (self.where(), "".join(prompt or ("?",)), a)))
            text = a[2:]
            r = self.newline()
            ptoks = list(prompt) if prompt is not None else ["?"]
            self.put(r, 0, self._cells(ptoks) + list(text), wrap_ok=True)
            self.snap("input", "".join(ptoks) + text)
            self.ai += 1
            toks = TIStr(tokenize_text(text)) if text else TIStr(())
            if tgt[0] == "svar":
                self.strs[tgt[1]] = toks
            else:
                if not toks:
                    raise TIError(f"{self.where()}: ERR:SYNTAX empty numeric input")
                p = P(list(toks), 0, f"{self.where()} typed {text!r}")
                v = self.real(self.ev(p.expr()))
                if p.i != len(toks):
                    raise TIError(f"{self.where()}: ERR:SYNTAX typed {text!r}")
                self.reals[tgt[1]] = v
        elif k == "If":
            cond = self.real(self.ev(st[1])) != 0
            nst = self._toks[name][i + 1][0] if i + 1 < len(self._toks[name]) else None
            if nst == "Then":
                if cond:
                    f.blocks.append(("if", i))
                    nxt = i + 2
                else:
                    j = self.find_end(name, i + 2, True)
                    if self._toks[name][j][0] == "Else":
                        f.blocks.append(("else", j))
                    nxt = j + 1
            else:
                nxt = i + 1 if cond else i + 2
        elif k == "Then":
            raise TIError(f"{self.where()}: Then without If")
        elif k == "Else":
            if not f.blocks or f.blocks[-1][0] != "if":
                raise TIError(f"{self.where()}: Else outside an If-Then")
            f.blocks.pop()
            nxt = self.find_end(name, i + 1, False) + 1
        elif k == "End":
            if not f.blocks:
                raise TIError(f"{self.where()}: End without a block")
            kind, line = f.blocks[-1][0], f.blocks[-1][1]
            if kind in ("if", "else"):
                f.blocks.pop()
            elif kind == "while":
                f.blocks.pop()
                nxt = line
            elif kind == "repeat":
                rst = self.stmt(name, line)
                if self.real(self.ev(rst[1])) != 0:
                    f.blocks.pop()
                else:
                    nxt = line + 1
            elif kind == "for":
                _, line, var, end, step = f.blocks[-1]
                v = CTX.add(self.reals[var], step)
                self.reals[var] = v
                if (step > 0 and v <= end) or (step < 0 and v >= end):
                    nxt = line + 1
                else:
                    f.blocks.pop()
        elif k == "While":
            if self.real(self.ev(st[1])) != 0:
                f.blocks.append(("while", i))
            else:
                nxt = self.find_end(name, i + 1, False) + 1
        elif k == "Repeat":
            f.blocks.append(("repeat", i))
        elif k == "For":
            var, a, b, s = st[1], self.real(self.ev(st[2])), self.real(self.ev(st[3])), self.real(self.ev(st[4]))
            self.reals[var] = a
            if (s > 0 and a <= b) or (s < 0 and a >= b):
                f.blocks.append(("for", i, var, b, s))
            else:
                nxt = self.find_end(name, i + 1, False) + 1
        elif k == "Lbl":
            pass
        elif k == "Goto":
            if f.blocks:
                self.problems.append(f"{self.where()}: Goto inside a block (memory leak on a real TI)")
                f.blocks = []
            if st[1] not in self.labels[name]:
                raise TIError(f"{self.where()}: ERR:LABEL {st[1]}")
            nxt = self.labels[name][st[1]]
        elif k == "prgm":
            if st[1] not in self.src:
                raise TIError(f"{self.where()}: ERR:UNDEFINED prgm{st[1]}")
            f.pc = nxt
            self.frames.append(Frame(st[1]))
            if len(self.frames) > 12:
                raise TIError(f"{self.where()}: call depth > 12 (recursion?)")
            return
        elif k == "Return":
            if f.blocks:
                self.problems.append(f"{self.where()}: Return inside a block")
            self.frames.pop()
            self.after_return(f.name)
            return
        elif k == "Stop":
            raise Halt(("stop", None))
        elif k in ("Float", "Normal", "Func"):
            pass
        elif k == "SortA":
            names = st[1]
            base = self.getvar("lvar", names[0])
            if not base:
                raise TIError(f"{self.where()}: ERR:INVALID DIM SortA( of an empty list")
            order = sorted(range(len(base)), key=lambda j: base[j])
            for nm in names:
                lst = self.getvar("lvar", nm)
                if len(lst) != len(base):
                    raise TIError(f"{self.where()}: ERR:DIM MISMATCH SortA")
                self.lists[nm] = [lst[j] for j in order]
        elif k == "SetUpEditor":
            for nm in st[1]:
                self.lists.setdefault(nm, [])
        elif k == "DelVar":
            tgt = st[1]
            {"var": self.reals, "svar": self.strs, "lvar": self.lists}[tgt[0]].pop(tgt[1], None)
        else:
            raise TIError(f"{self.where()}: unsupported statement {k}")
        f.pc = nxt


def load_programs(src_dir):
    progs = {}
    for p in sorted(Path(src_dir).glob("*.txt")):
        lines = p.read_text(encoding="utf-8").rstrip("\n").split("\n")
        progs[p.stem] = lines
    return progs
