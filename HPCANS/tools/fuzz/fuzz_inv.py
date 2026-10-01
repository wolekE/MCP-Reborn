#!/usr/bin/env python3
"""
Randomized differential testing of the inverse solver (main menu 3, programs HAINV*).

Every case is a random problem a student could meet, typed from the main menu exactly as the
student would press keys:
  * 1:FIND F⁻¹(X) for every shape (AX+B, (AX+B)/(CX+D), A/(BX+C)+D, A(BX+C)³+D, A³√(BX+C)+D,
    A√(BX+C)+D, A(BX+C)^(M/N)+D) with negative / fractional / zero coefficients, ENTER defaults,
    both minus keys, lines typed in several styles (3-2X, (X-4)/7, 2(X-3), (-2/3)X+4), constant
    fractions, even powers (no inverse) and refused inputs (A=0, a constant inside, X² in a line);
  * 2:VERIFY TWO FUNCTIONS with true inverse pairs written in another shape, perturbed pairs,
    random pairs, restricted even-power pairs and f with itself;
  * 3:DOMAIN/RANGE from intervals (brackets, infinite ends) and from a formula;
  * 4:HAS INVERSE? (HLT) for every family: parabolas in several typed forms, |x|, powers,
    [[x]], fixed families and graphs typed as corner points (solid / hollow ends);
  * footers: 1:AGAIN chains, 3:WHY pages (their CHECK lines are verified too) and CLEAR.

Oracle (written independently of the TI code, in Python with Fractions / mpmath / sympy):
  * FIND: rational shapes: sympy solves x = f(y) for y and the printed inverse must equal it as
    a rational function, written as one fraction with whole-number coefficients in lowest terms
    and a positive leading bottom coefficient.  Power / root shapes: the printed inverse must
    compose to x both ways (f(f⁻¹(x)) = x on R_f and f⁻¹(f(x)) = x on D_f) at many exact sample
    points (60-digit real arithmetic, real odd roots of negatives), the restriction must be the
    range of f, and D=/R= must be R_f / D_f exactly.  Even powers: the two printed witnesses
    must give the same printed value; "(F IS EVEN)" only when f is even.
  * VERIFY: f and g are inverses iff f(g(x)) = x for every x in R_f and g(f(x)) = x for every x
    in R_g (so an even power restricted to the other function's range counts, as in the class),
    tested at exact sample points; every printed composition line must be true (a formula equal
    to the composite, a point value f(g(a)) = b, an UNDEFINED claim); a "(F NEEDS X≥c)" note
    must name R_g.
  * D/R: swap, brackets kept.  HLT: one-to-one iff strictly monotone (graphs: strictly monotone
    corner values; parabolas: a ≠ 0, or a line); a NO must come with two different x in the
    domain that really share the printed y.

Run from tools/:   python3 fuzz/fuzz_inv.py [-n CASES] [-s SEED] [--kind find] [-v]
"""

import argparse
import random
import re
import sys
import time
from fractions import Fraction as Fr
from pathlib import Path

import mpmath as mp
import sympy as sp

HERE = Path(__file__).resolve().parent
TOOLS = HERE.parent
sys.path.insert(0, str(TOOLS))
from tibasic import D, Machine, TIError, load_programs  # noqa: E402

SRC = TOOLS.parent / "src"
mp.mp.dps = 60
TINY = mp.mpf("1e-40")
XS = sp.Symbol("x")
FOOT = "1:AGAIN  2:HOME  3:WHY"
FOOT2 = "1:AGAIN  2:HOME"


class Undef(Exception):
    """value not defined (outside the domain)"""


class Bad(Exception):
    """printed text the oracle can not read"""


# ============================================================================ exact / real values
# A value is a Fraction when it is exact, else an mpmath mpf (60 digits).

def mpv(v):
    if isinstance(v, Fr):
        return mp.mpf(v.numerator) / v.denominator
    return mp.mpf(v)


def iszero(v):
    return v == 0 if isinstance(v, Fr) else abs(v) < TINY


def sgn(v):
    if iszero(v):
        return 0
    return 1 if v > 0 else -1


def add(a, b):
    return a + b if isinstance(a, Fr) and isinstance(b, Fr) else mpv(a) + mpv(b)


def sub(a, b):
    return a - b if isinstance(a, Fr) and isinstance(b, Fr) else mpv(a) - mpv(b)


def mul(a, b):
    return a * b if isinstance(a, Fr) and isinstance(b, Fr) else mpv(a) * mpv(b)


def div(a, b):
    if iszero(b):
        raise Undef
    return a / b if isinstance(a, Fr) and isinstance(b, Fr) else mpv(a) / mpv(b)


def iroot(n, k):
    """exact integer k-th root of n >= 0, or None"""
    if n < 0:
        return None
    r = int(round(n ** (1.0 / k))) if n < 10 ** 200 else None
    if r is None:
        return None
    for c in (r - 1, r, r + 1):
        if c >= 0 and c ** k == n:
            return c
    return None


def rpow(b, p):
    """b^p for a Fraction exponent p, with the real-mode rules of the class / TI-84:
    an odd root of a negative is negative, an even root of a negative is undefined."""
    if p.denominator == 1:
        e = p.numerator
        if iszero(b) and e < 0:
            raise Undef
        if isinstance(b, Fr):
            return b ** e
        return mpv(b) ** e
    s = sgn(b)
    if s == 0:
        if p > 0:
            return Fr(0)
        raise Undef
    if s < 0 and p.denominator % 2 == 0:
        raise Undef
    ab = abs(b)
    res = None
    if isinstance(ab, Fr):
        rn, rd = iroot(ab.numerator, p.denominator), iroot(ab.denominator, p.denominator)
        if rn is not None and rd is not None:
            res = Fr(rn, rd) ** p.numerator
    if res is None:
        res = mpv(ab) ** (mp.mpf(p.numerator) / p.denominator)
    if s < 0 and p.numerator % 2:
        res = -res
    return res


def same(a, b, rel=None):
    """equal: exactly for two Fractions, else to a relative tolerance (default 1e-28)"""
    if rel is None and isinstance(a, Fr) and isinstance(b, Fr):
        return a == b
    rel = mp.mpf("1e-28") if rel is None else rel
    a, b = mpv(a), mpv(b)
    return abs(a - b) <= rel * max(1, abs(a), abs(b))


# ============================================================================ the student's functions
class Rat:
    """(a x + b)/(c x + d)"""
    kind = "rat"

    def __init__(self, a, b, c, d):
        self.a, self.b, self.c, self.d = map(Fr, (a, b, c, d))

    def __call__(self, x):
        return div(add(mul(self.a, x), self.b), add(mul(self.c, x), self.d))

    def constant(self):
        return self.a * self.d - self.b * self.c == 0

    def sym(self):
        return (sp.Rational(self.a) * XS + sp.Rational(self.b)) / (sp.Rational(self.c) * XS + sp.Rational(self.d))

    def domain(self):
        if self.c == 0:
            return [(None, None, False, False)]
        return punctured(-self.d / self.c)

    def range(self):
        if self.constant():
            v = self.b / self.d if self.c == 0 else self.a / self.c
            return [(v, v, True, True)]
        if self.c == 0:
            return [(None, None, False, False)]
        return punctured(self.a / self.c)

    def one_to_one(self):
        return not self.constant()

    def even(self):
        return False

    def __repr__(self):
        return f"({self.a}x+{self.b})/({self.c}x+{self.d})"


class Pw:
    """A (B x + C)^(m/n) + D, m/n reduced, n > 0 (real-mode powers)"""
    kind = "pow"

    def __init__(self, A, B, C, Dd, m, n=1):
        g = Fr(m, n)
        self.A, self.B, self.C, self.D = map(Fr, (A, B, C, Dd))
        self.p = g

    @property
    def m(self):
        return self.p.numerator

    @property
    def n(self):
        return self.p.denominator

    def __call__(self, x):
        u = add(mul(self.B, x), self.C)
        return add(mul(self.A, rpow(u, self.p)), self.D)

    def constant(self):
        return False

    def h(self):
        return -self.C / self.B

    def domain(self):
        h, up = self.h(), self.B > 0
        if self.n % 2 == 0:
            closed = self.m > 0
            return [(h, None, closed, False)] if up else [(None, h, False, closed)]
        if self.m < 0:
            return punctured(h)
        return [(None, None, False, False)]

    def range(self):
        """the set of values A·w + D, w = u^p"""
        if self.n % 2 == 0 or self.m % 2 == 0:
            closed = self.m > 0          # w >= 0 (or w > 0 for a negative power)
            return [(self.D, None, closed, False)] if self.A > 0 else [(None, self.D, False, closed)]
        if self.m < 0:
            return punctured(self.D)
        return [(None, None, False, False)]

    def one_to_one(self):
        return self.m % 2 == 1

    def even(self):
        return self.m % 2 == 0 and self.C == 0

    def __repr__(self):
        return f"{self.A}({self.B}x+{self.C})^({self.p})+{self.D}"


class Ab:
    """A |B x + C| + D"""
    kind = "abs"

    def __init__(self, A, B, C, Dd):
        self.A, self.B, self.C, self.D = map(Fr, (A, B, C, Dd))

    def __call__(self, x):
        return add(mul(self.A, abs(add(mul(self.B, x), self.C))), self.D)

    def domain(self):
        return [(None, None, False, False)]

    def even(self):
        return self.C == 0


class Graph:
    """corner points, straight segments, ends solid (True) or hollow"""
    kind = "graph"

    def __init__(self, pts, lc, rc):
        self.pts, self.lc, self.rc = sorted(pts), lc, rc

    def __call__(self, x):
        p = self.pts
        x0, xn = p[0][0], p[-1][0]
        if not isinstance(x, Fr):
            raise Undef
        if x < x0 or x > xn or (x == x0 and not self.lc) or (x == xn and not self.rc):
            raise Undef
        for (a, ya), (b, yb) in zip(p, p[1:]):
            if a <= x <= b:
                return ya + (yb - ya) * (x - a) / (b - a)
        return p[0][1]

    def one_to_one(self):
        ys = [y for _, y in self.pts]
        return all(b > a for a, b in zip(ys, ys[1:])) or all(b < a for a, b in zip(ys, ys[1:]))

    def even(self):
        s = set(self.pts)
        return all((-x, y) in s for x, y in self.pts) and self.lc == self.rc


class Quad:
    """a x² + b x + c typed at the PARABOLA prompt"""
    kind = "quad"

    def __init__(self, a, b, c):
        self.a, self.b, self.c = map(Fr, (a, b, c))

    def __call__(self, x):
        return add(add(mul(self.a, mul(x, x)), mul(self.b, x)), self.c)

    def domain(self):
        return [(None, None, False, False)]

    def one_to_one(self):
        return self.a == 0 and self.b != 0

    def even(self):
        return self.b == 0


# ============================================================================ sets of reals
def punctured(p):
    return [(None, p, False, False), (p, None, False, False)]


def lt(a, b):
    """a < b with None = -inf as a left end... used only on finite numbers"""
    return a < b


def in_set(x, ivs):
    for lo, hi, lc, rc in ivs:
        okl = lo is None or (mpv(x) > mpv(lo) if not (isinstance(x, Fr) and isinstance(lo, Fr)) else x > lo) \
            or (lc and same(x, lo))
        okr = hi is None or (mpv(x) < mpv(hi) if not (isinstance(x, Fr) and isinstance(hi, Fr)) else x < hi) \
            or (rc and same(x, hi))
        if okl and okr:
            return True
    return False


def canon(ivs):
    """sort and merge touching pieces"""
    def key(iv):
        return (-10 ** 99 if iv[0] is None else iv[0])
    out = []
    for iv in sorted(ivs, key=key):
        if out:
            lo, hi, lc, rc = out[-1]
            if hi is not None and iv[0] is not None and iv[0] == hi and (rc or iv[2]):
                out[-1] = (lo, iv[1], lc, iv[3])
                continue
        out.append(iv)
    return out


def samples(ivs, rng, k=6):
    """exact sample points inside a set"""
    out = []
    steps = [Fr(1, 3), Fr(1), Fr(7, 2), Fr(12), Fr(150)]
    for lo, hi, lc, rc in ivs:
        if lo is not None and hi is not None:
            if lo == hi:
                out.append(lo)
                continue
            if lc:
                out.append(lo)
            if rc:
                out.append(hi)
            for t in (Fr(1, 7), Fr(1, 3), Fr(1, 2), Fr(5, 6)):
                out.append(lo + (hi - lo) * t)
        elif lo is not None:
            if lc:
                out.append(lo)
            out += [lo + s for s in steps]
        elif hi is not None:
            if rc:
                out.append(hi)
            out += [hi - s for s in steps]
        else:
            out += [Fr(0), Fr(1), Fr(-1), Fr(5, 2), Fr(-7, 3), Fr(13), Fr(-40)]
    rng.shuffle(out)
    return out[:k * 3]


def set_text(ivs):
    return " U ".join(f"{'[' if lc else '('}{'-INF' if lo is None else lo},{'INF' if hi is None else hi}{']' if rc else ')'}"
                      for lo, hi, lc, rc in ivs) or "{}"


# ============================================================================ reading the TI text
def ti_num(s):
    """'-17/4' '6' 'INF' '-INF' '1.414214' -> (value or 'INF'/'-INF', exact?)"""
    s = s.strip()
    if s in ("INF", "-INF"):
        return s, True
    if re.fullmatch(r"-?\d+(/\d+)?", s):
        return Fr(s), True
    if re.fullmatch(r"-?\d*\.\d+", s):
        return mp.mpf(s), False
    raise Bad(f"bad number {s!r}")


def parse_set(text, var):
    t = text
    if t == "NO REAL NUMBERS":
        return [], True
    if t == "ALL REALS":
        return [(None, None, False, False)], True
    pre = f"ALL REALS, {var}≠"
    if t.startswith(pre):
        vals = [ti_num(v) for v in t[len(pre):].split(",")]
        out, lo, ex = [], None, True
        for v, e in vals:
            if isinstance(v, str):
                raise Bad(text)
            out.append((lo, v, False, False))
            lo, ex = v, ex and e
        out.append((lo, None, False, False))
        return out, ex
    out, ex = [], True
    for part in t.split("U"):
        m = re.fullmatch(r"([\[(])([^,]+),([^,]+)([\])])", part)
        if not m:
            raise Bad(f"bad interval {part!r} in {text!r}")
        (lo, e1), (hi, e2) = ti_num(m.group(2)), ti_num(m.group(3))
        if lo == "INF" or hi == "-INF":
            raise Bad(f"bad infinite end in {text!r}")
        lo = None if lo == "-INF" else lo
        hi = None if hi == "INF" else hi
        if (lo is None and m.group(1) == "[") or (hi is None and m.group(4) == "]"):
            raise Bad(f"closed bracket at infinity in {text!r}")
        out.append((lo, hi, m.group(1) == "[", m.group(4) == "]"))
        ex = ex and e1 and e2
    return out, ex


def same_set(a, b):
    a, b = canon(a), canon(b)
    if len(a) != len(b):
        return False
    for (l1, h1, a1, b1), (l2, h2, a2, b2) in zip(a, b):
        for u, v in ((l1, l2), (h1, h2)):
            if (u is None) != (v is None):
                return False
            if u is not None and not same(u, v, mp.mpf("1e-6") if not isinstance(v, Fr) else mp.mpf("1e-28")):
                return False
        if bool(a1) != bool(a2) or bool(b1) != bool(b2):
            return False
    return True


TOKS = ["³√(", "√(", "²", "³", "^", "(", ")", "+", "-", "⁻", "/", "*", "X"]


def lex(s):
    out, i = [], 0
    while i < len(s):
        if s[i] in "0123456789.":
            j = i
            while j < len(s) and s[j] in "0123456789.":
                j += 1
            out.append(("num", s[i:j]))
            i = j
            continue
        for t in TOKS:
            if s.startswith(t, i):
                out.append(t)
                i += len(t)
                break
        else:
            raise Bad(f"can not read {s[i:]!r} in {s!r}")
    return out


class Parser:
    """printed TI text -> tree.  Implicit and explicit products/quotients go left to right
    (as on the TI-84); a minus sign binds looser than a power (-X² = -(X²))."""

    def __init__(self, text):
        self.t, self.i, self.text = lex(text), 0, text

    def peek(self):
        return self.t[self.i] if self.i < len(self.t) else None

    def take(self, want=None):
        tok = self.peek()
        if want is not None and tok != want:
            raise Bad(f"expected {want!r} in {self.text!r}")
        self.i += 1
        return tok

    def parse(self):
        node = self.expr()
        if self.i != len(self.t):
            raise Bad(f"extra text in {self.text!r}")
        return node

    def expr(self):
        node = self.term()
        while self.peek() in ("+", "-"):
            op = self.take()
            node = (op, node, self.term())
        return node

    def starts(self, tok):
        return tok is not None and (tok in ("(", "√(", "³√(", "X") or (isinstance(tok, tuple)))

    def term(self):
        node = self.unary()
        while True:
            tok = self.peek()
            if tok in ("*", "/"):
                self.take()
                node = (tok, node, self.unary())
            elif self.starts(tok):
                node = ("*", node, self.power())
            else:
                return node

    def unary(self):
        if self.peek() in ("-", "⁻"):
            self.take()
            return ("neg", self.unary())
        return self.power()

    def power(self):
        node = self.post()
        while self.peek() == "^":
            self.take()
            neg = False
            while self.peek() in ("-", "⁻"):
                self.take()
                neg = not neg
            e = self.post()
            node = ("^", node, ("neg", e) if neg else e)
        return node

    def post(self):
        node = self.atom()
        while self.peek() in ("²", "³"):
            node = ("^", node, ("num", "2" if self.take() == "²" else "3"))
        return node

    def atom(self):
        tok = self.peek()
        if isinstance(tok, tuple):
            self.take()
            return tok
        if tok == "X":
            self.take()
            return ("x",)
        if tok in ("(", "√(", "³√("):
            self.take()
            node = self.expr()
            self.take(")")
            return node if tok == "(" else (("sqrt" if tok == "√(" else "cbrt"), node)
        raise Bad(f"unexpected {tok!r} in {self.text!r}")


def const(node):
    """a constant subtree -> Fraction"""
    k = node[0]
    if k == "num":
        return Fr(node[1])
    if k == "neg":
        return -const(node[1])
    if k in "+-*/":
        a, b = const(node[1]), const(node[2])
        return a + b if k == "+" else a - b if k == "-" else a * b if k == "*" else a / b
    if k == "^":
        a, b = const(node[1]), const(node[2])
        if b.denominator != 1:
            raise Bad("constant power")
        return a ** b.numerator
    raise Bad(f"not a constant {node}")


def ev(node, x):
    k = node[0]
    if k == "num":
        return Fr(node[1])
    if k == "x":
        return x
    if k == "neg":
        v = ev(node[1], x)
        return -v
    if k == "+":
        return add(ev(node[1], x), ev(node[2], x))
    if k == "-":
        return sub(ev(node[1], x), ev(node[2], x))
    if k == "*":
        return mul(ev(node[1], x), ev(node[2], x))
    if k == "/":
        return div(ev(node[1], x), ev(node[2], x))
    if k == "^":
        return rpow(ev(node[1], x), const(node[2]))
    if k == "sqrt":
        return rpow(ev(node[1], x), Fr(1, 2))
    if k == "cbrt":
        return rpow(ev(node[1], x), Fr(1, 3))
    raise Bad(str(node))


def to_sym(node):
    """tree -> sympy rational function (powers must be whole numbers)"""
    k = node[0]
    if k == "num":
        return sp.Rational(node[1])
    if k == "x":
        return XS
    if k == "neg":
        return -to_sym(node[1])
    if k in "+-*/":
        a, b = to_sym(node[1]), to_sym(node[2])
        return a + b if k == "+" else a - b if k == "-" else a * b if k == "*" else a / b
    if k == "^":
        e = const(node[2])
        if e.denominator != 1:
            raise Bad("not rational")
        return to_sym(node[1]) ** e.numerator
    raise Bad("not rational")


def formula(text):
    return Parser(text).parse()


STYLE_BAD = [
    (r"\+-|--|-\+|\+\+|\+⁻|-⁻", "double sign"),
    (r"(?<![0-9/.])1X", "coefficient 1 shown"),
    (r"(?<![0-9/.^(])1(³√|√)", "coefficient 1 shown"),
    (r"(?<![0-9/.])0X", "zero term shown"),
    (r"[+-]0(?![0-9./])", "zero term shown"),
    (r"\^1(?![0-9/])|\^\(1\)", "power 1 shown"),
    (r"\(\)", "empty parentheses"),
    (r"^\+", "leading plus"),
    (r"\d\.\d", "decimal (not exact)"),
    (r"(?<!√)\(X\)", "bare X in parentheses"),
]


def style_problems(text):
    return [f"{why}: {text!r}" for pat, why in STYLE_BAD if re.search(pat, text)]


def int_fraction_form(text):
    """a printed rational inverse must be one fraction (or one polynomial) with whole-number
    coefficients, no common factor, and a positive leading coefficient in the bottom."""
    probs = []
    node = formula(text)
    if node[0] == "/":
        top, bot = to_sym(node[1]), to_sym(node[2])
    else:
        top, bot = to_sym(node), sp.Integer(1)
    try:
        pt, pb = sp.Poly(sp.expand(top), XS), sp.Poly(sp.expand(bot), XS)
    except sp.PolynomialError:
        return [f"top or bottom is not a polynomial: {text!r}"]
    cs = pt.all_coeffs() + pb.all_coeffs()
    if any(not c.is_Integer for c in cs):
        probs.append(f"fraction inside the top or bottom: {text!r}")
    elif sp.igcd(*[int(c) for c in cs if c != 0] or [1]) != 1:
        probs.append(f"top and bottom share a number factor: {text!r}")
    if pb.LC() < 0:
        probs.append(f"bottom starts with a minus: {text!r}")
    if sp.degree(sp.gcd(pt.as_expr(), pb.as_expr()), XS) > 0:
        probs.append(f"top and bottom share a factor: {text!r}")
    return probs


# ============================================================================ typing like a student
def rcoef(rng, lo=-6, hi=6, p_zero=0.0, p_frac=0.2, nonzero=False):
    while True:
        r = rng.random()
        if r < p_zero:
            v = Fr(0)
        elif r < p_zero + p_frac:
            v = Fr(rng.choice([1, 2, 3, 5, 7]) * rng.choice([1, -1]), rng.choice([2, 3, 4, 5]))
        else:
            v = Fr(rng.randint(lo, hi))
        if not (nonzero and v == 0):
            return v


def minus(rng):
    return rng.choice(["-", "⁻"])


def num_text(rng, v, paren_ok=True):
    """a number typed at a number prompt"""
    a = abs(v)
    s = str(a.numerator) if a.denominator == 1 else f"{a.numerator}/{a.denominator}"
    if a.denominator in (2, 4, 5) and rng.random() < 0.15:
        s = str(float(a)).rstrip("0").rstrip(".")
        if s.startswith("0.") and rng.random() < 0.5:
            s = s[1:]
    if v < 0:
        if paren_ok and a.denominator > 1 and rng.random() < 0.2:
            return "(" + minus(rng) + s + ")"
        return minus(rng) + s
    return s


def front_text(rng, v):
    """A (FRONT)= / A (TOP NUMBER)=: ENTER means 1, a lone minus means -1"""
    if v == 1 and rng.random() < 0.6:
        return ""
    if v == -1 and rng.random() < 0.5:
        return minus(rng)
    return num_text(rng, v)


def end_text(rng, v):
    """D (END NUMBER)=: ENTER means 0"""
    if v == 0:
        return "" if rng.random() < 0.7 else "0"
    return num_text(rng, v)


def term_text(rng, k):
    """k·X as the student would type the X part with the X key"""
    a = abs(k)
    if a == 1:
        body = "X"
    elif a.denominator == 1:
        body = f"{a.numerator}X"
    else:
        style = rng.random()
        if style < 0.4:
            body = f"({a.numerator}/{a.denominator})X"
        elif style < 0.75 or a.numerator != 1:
            body = f"{a.numerator}X/{a.denominator}" if a.numerator != 1 else f"X/{a.denominator}"
        else:
            body = f"X/{a.denominator}"
        if k < 0 and body.startswith("(") and rng.random() < 0.5:
            return f"({minus(rng)}{a.numerator}/{a.denominator})X"
    return (minus(rng) if k < 0 else "") + body


def lin_text(rng, k, l, inside=False):
    """k x + l typed with the X key (several styles)"""
    k, l = Fr(k), Fr(l)
    if k == 0:
        return num_text(rng, l, paren_ok=False)
    if inside and k == 1 and l == 0 and rng.random() < 0.6:
        return ""
    r = rng.random()
    lt_ = num_text(rng, abs(l), paren_ok=False)
    if l != 0 and r < 0.2:  # number first: 3-2X, 1+3X
        a = abs(k)
        body = term_text(rng, a)
        return (minus(rng) if l < 0 else "") + lt_ + ("-" if k < 0 else "+") + body
    if l != 0 and r < 0.35 and k.denominator == 1 and abs(k) != 1 and (l / k).denominator <= 3:
        q = l / k  # 2(X-3)
        inner = "X" + ("+" if q > 0 else "-") + num_text(rng, abs(q), paren_ok=False)
        return (minus(rng) if k < 0 else "") + (str(abs(k.numerator)) if abs(k) != 1 else "") + "(" + inner + ")"
    if l != 0 and r < 0.45 and k.numerator == 1 and k.denominator > 1 and (l * k.denominator).denominator == 1:
        c = l * k.denominator  # (X-4)/7
        return "(X" + ("+" if c > 0 else "-") + str(abs(c)) + ")/" + str(k.denominator)
    s = term_text(rng, k)
    if l != 0:
        s += ("+" if l > 0 else "-") + lt_
    return s


# ============================================================================ the simulator
class RecMachine(Machine):
    """records every line handed to HAOUT (whole), the page starts and the footers; presses
    ENTER for the student at an ENTER=MORE wait"""

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.out = []
        self.more = 0
        self.wrap_problems = []
        self.broken = set()
        self._pieces = None

    def exec(self, f):
        st = self.stmt(f.name, f.pc)
        if st[0] == "prgm":
            if st[1] == "HAANS":
                self.out.append(["ANSWER:"])
            elif st[1] == "HAPAGE":
                self.out.append(["PAGE " + "".join(self.strs.get("Str9", ()))])
            elif st[1] == "HAINVW" and self.out:
                text = "".join(self.strs["Str9"])
                self.out[-1].append(text)
                self.broken.add(text)
                self._pieces = (text, [])
            elif st[1] == "HAOUT" and self.out:
                line = "".join(self.strs["Str9"])
                if f.name == "HAINVW" and self._pieces is not None:
                    self._pieces[1].append(line)
                else:
                    self.out[-1].append(line)
            elif st[1] == "HAEND" and self.out:
                self.out[-1].append("FOOTER " + "".join(self.strs["Str9"]))
        super().exec(f)
        if self._pieces is not None and (not self.frames or self.frames[-1].name not in ("HAINVW", "HAOUT")):
            self.check_pieces(*self._pieces)
            self._pieces = None

    def check_pieces(self, text, pieces):
        """the line breaker: pieces fit the screen, rebuild the text, never split a number"""
        if "".join(pieces) != text:
            self.wrap_problems.append(f"pieces {pieces} do not make {text!r}")
        for a, b in zip(pieces, pieces[1:]):
            if a and b and a[-1] in "0123456789." and b[0] in "0123456789./":
                self.wrap_problems.append(f"number split across lines: {a!r} | {b!r}")
            if a and a[-1] in "(^":
                self.wrap_problems.append(f"line ends inside a group: {a!r} | {b!r}")
        for pc in pieces:
            if width(pc) > 26:
                self.wrap_problems.append(f"piece wider than 26: {pc!r}")

    def getkey(self):
        if self.frames and self.frames[-1].name == "HAOUT":
            self.more += 1
            self.snap("key", "ENTER")
            return D(105)
        return super().getkey()


PROGS = None


def run(actions):
    global PROGS
    if PROGS is None:
        PROGS = load_programs(SRC)
    m = RecMachine(PROGS)
    err = None
    try:
        res = m.run(["ENTER"] + list(actions) + ["CLEAR"] * 6)
    except TIError as e:
        res, err = ("error", None), str(e)
    return m, res, err


# ============================================================================ random functions
SHAPE_KEYS = {"line": "k1", "frac": "k2", "recip": "k3", "cube": "k4", "cbrt": "k5", "sqrt": "k6", "pow": "k7"}


def lin(rng, nonconst=True, p_zero=0.1):
    k = rcoef(rng, -5, 5, p_zero=0 if nonconst else p_zero, nonzero=nonconst)
    l = rcoef(rng, -9, 9, p_zero=0.2)
    return k, l


def power_text(rng, p):
    a = abs(p)
    s = str(a.numerator) if a.denominator == 1 else f"{a.numerator}/{a.denominator}"
    if a in (Fr(1, 2), Fr(3, 2), Fr(5, 2)) and rng.random() < 0.2:
        s = str(float(a))
    return (minus(rng) + s) if p < 0 else s


def rand_power(rng):
    while True:
        m, n = rng.choice([1, 1, 2, 3, 3, 4, 5, -1, -2, -3]), rng.choice([1, 1, 2, 3, 3, 5, 4])
        p = Fr(m, n)
        if p != 1 or rng.random() < 0.05:
            return p


def rand_function(rng, shapes=None, allow_bad=True):
    """-> (function, shape name, keys from the shape menu on)"""
    shape = rng.choice(shapes or ["line", "line", "frac", "frac", "frac", "recip", "cube", "cbrt", "sqrt", "sqrt", "pow", "pow"])
    keys = [SHAPE_KEYS[shape]]
    bad = []
    if shape == "line":
        k, l = lin(rng, nonconst=rng.random() > 0.06)
        f = Rat(k, l, 0, 1)
        if allow_bad and rng.random() < 0.05:
            bad = ["t:X²+1", "ENTER"]
        keys += bad + [f"t:{lin_text(rng, k, l)}"]
        return f, shape, keys
    if shape == "frac":
        a, b = lin(rng, nonconst=rng.random() > 0.25)
        c, d = lin(rng, nonconst=rng.random() > 0.1)
        if c == 0 and d == 0:
            d = Fr(2)
        if rng.random() < 0.05:   # a constant fraction like (2x+4)/(x+2)
            t = rcoef(rng, -3, 3, nonzero=True)
            a, b = t * c, t * d
        f = Rat(a, b, c, d)
        if allow_bad and rng.random() < 0.05:
            bad = [f"t:{lin_text(rng, a, b)}", "t:0", "ENTER"]
        keys += bad + [f"t:{lin_text(rng, a, b)}", f"t:{lin_text(rng, c, d)}"]
        return f, shape, keys
    if shape == "recip":
        A = rcoef(rng, -9, 9, p_zero=0.03)
        B, C = lin(rng)
        Dd = rcoef(rng, -6, 6, p_zero=0.3)
        f = Rat(Dd * B, A + Dd * C, B, C)
        if allow_bad and rng.random() < 0.05:
            bad = [f"t:{front_text(rng, A)}", "t:5", "ENTER"]
        keys += bad + [f"t:{front_text(rng, A)}", f"t:{lin_text(rng, B, C)}", f"t:{end_text(rng, Dd)}"]
        return f, shape, keys
    A = rcoef(rng, -6, 6, nonzero=True)
    B, C = lin(rng)
    Dd = rcoef(rng, -9, 9, p_zero=0.3)
    p = {"cube": Fr(3), "cbrt": Fr(1, 3), "sqrt": Fr(1, 2)}.get(shape) or rand_power(rng)
    f = Pw(A, B, C, Dd, p.numerator, p.denominator)
    head = [f"t:{power_text(rng, p)}"] if shape == "pow" else []
    if allow_bad and rng.random() < 0.06:
        bad = head + ["t:0", "ENTER"] if rng.random() < 0.5 else head + [f"t:{front_text(rng, A)}", "t:4", "ENTER"]
    keys += bad + head + [f"t:{front_text(rng, A)}", f"t:{lin_text(rng, B, C, inside=True)}", f"t:{end_text(rng, Dd)}"]
    return f, shape, keys


def keys_for(rng, f):
    """keys that enter a known function f (Rat or Pw) in some shape that fits it"""
    if isinstance(f, Rat):
        opts = ["frac"]
        if f.c == 0:
            opts += ["line", "line"]
        elif f.a * f.d != f.b * f.c:
            opts += ["recip"]
        shape = rng.choice(opts)
        if shape == "line":
            return [SHAPE_KEYS["line"], f"t:{lin_text(rng, f.a / f.d, f.b / f.d)}"]
        if shape == "frac":
            a, b, c, d = f.a, f.b, f.c, f.d
            if rng.random() < 0.5:   # clear fractions the way a student copies a printed answer
                den = 1
                for v in (a, b, c, d):
                    den = den * v.denominator // sp.igcd(den, v.denominator)
                a, b, c, d = a * den, b * den, c * den, d * den
            return [SHAPE_KEYS["frac"], f"t:{lin_text(rng, a, b)}", f"t:{lin_text(rng, c, d)}"]
        # recip: (ax+b)/(cx+d) = A'/(cx+d) + a/c
        Dd = f.a / f.c
        A = f.b - Dd * f.d
        return [SHAPE_KEYS["recip"], f"t:{front_text(rng, A)}", f"t:{lin_text(rng, f.c, f.d)}", f"t:{end_text(rng, Dd)}"]
    shape = {Fr(3): "cube", Fr(1, 3): "cbrt", Fr(1, 2): "sqrt"}.get(f.p, "pow")
    if shape != "pow" and rng.random() < 0.15:
        shape = "pow"
    head = [f"t:{power_text(rng, f.p)}"] if shape == "pow" else []
    return [SHAPE_KEYS[shape]] + head + [f"t:{front_text(rng, f.A)}", f"t:{lin_text(rng, f.B, f.C, inside=True)}",
                                         f"t:{end_text(rng, f.D)}"]


def true_inverse(f):
    """f⁻¹ as a Rat / Pw (an even power gets its + branch, i.e. the restricted inverse)"""
    if isinstance(f, Rat):
        return Rat(f.d, -f.b, -f.c, f.a)
    q = 1 / f.p
    return Pw(1 / f.B, 1 / f.A, -f.D / f.A, -f.C / f.B, q.numerator, q.denominator)


# ============================================================================ checks
def lines_of(m):
    """answer pages (list of lines, without the ANSWER:/PAGE head)"""
    return m.out


def width(text):
    """columns on the TI screen (⁻¹ is one character there)"""
    return len(text.replace("⁻¹", "~"))


def find_line(lines, pre):
    return [l for l in lines if l.startswith(pre)]


def check_witness(f, lines, probs, want_head):
    """a NO answer: the head lines, F(a)=v, F(b)=v, Y=v HITS TWICE, (F IS EVEN) only if even"""
    for h in want_head:
        if h not in lines:
            probs.append(f"missing {h!r}")
    pts = []
    for l in lines:
        mm = re.fullmatch(r"F\(([^)]+)\)=(.+)", l)
        if mm:
            pts.append((ti_num(mm.group(1)), ti_num(mm.group(2))))
    if len(pts) != 2:
        probs.append(f"want 2 witness lines F(a)=v, got {pts}")
        return
    (a, ea), (va, eva) = pts[0]
    (b, eb), (vb, evb) = pts[1]
    if not (ea and eb and eva and evb):
        probs.append(f"witness not exact: {pts}")
    if same(a, b):
        probs.append(f"witness x values are the same: {pts}")
    for x, v in ((a, va), (b, vb)):
        try:
            fx = f(x)
        except Undef:
            probs.append(f"witness x={x} is outside the domain")
            continue
        if not same(fx, v, mp.mpf("1e-9")):
            probs.append(f"F({x}) is {fx}, printed {v}")
    if not same(va, vb):
        probs.append(f"witness values differ: {pts}")
    hits = find_line(lines, "Y=")
    if not hits or not hits[0].endswith(" HITS TWICE") or not same(ti_num(hits[0][2:-len(" HITS TWICE")])[0], va):
        probs.append(f"Y=v HITS TWICE line wrong or missing: {hits}")
    even_printed = "(F IS EVEN)" in lines
    if even_printed and not f.even():
        probs.append("(F IS EVEN) printed but f is not even")
    if not even_printed and f.even() and f.kind != "graph":
        probs.append("f is even but (F IS EVEN) not printed")


def check_inverse_formula(f, text, rng, probs):
    """the printed f⁻¹ composes to x both ways"""
    try:
        node = formula(text)
    except Bad as e:
        probs.append(f"can not read F⁻¹: {e}")
        return
    probs += style_problems(text)
    if isinstance(f, Rat):
        want = sp.solve(sp.Eq(XS, f.sym().subs(XS, sp.Symbol("y"))), sp.Symbol("y"))
        try:
            got = to_sym(node)
        except Bad as e:
            probs.append(f"F⁻¹ not rational: {e}")
            return
        if len(want) != 1 or sp.cancel(got - want[0]) != 0:
            probs.append(f"F⁻¹ wrong: printed {text!r}, sympy {want}")
            return
        probs += int_fraction_form(text)
        return
    R, Dm = f.range(), f.domain()
    n_ok = 0
    for x in samples(R, rng):
        try:
            y = ev(node, x)
        except Undef:
            probs.append(f"printed F⁻¹({x}) undefined but {x} is in R_f")
            continue
        if not in_set(y, Dm):
            probs.append(f"F⁻¹({x})={y} is outside D_f")
            continue
        try:
            back = f(y)
        except Undef:
            probs.append(f"f(F⁻¹({x})) undefined")
            continue
        if not same(back, x, mp.mpf("1e-25")):
            probs.append(f"f(F⁻¹({x})) = {mp.nstr(mpv(back), 12)} != {x}")
        else:
            n_ok += 1
    for y in samples(Dm, rng):
        try:
            fy = f(y)
            back = ev(node, fy)
        except Undef:
            probs.append(f"F⁻¹(f({y})) undefined")
            continue
        if not same(back, y, mp.mpf("1e-25")):
            probs.append(f"F⁻¹(f({y})) = {mp.nstr(mpv(back), 12)} != {y}")
    if not n_ok:
        probs.append("no sample point checked")


def restriction_text(R):
    """the FOR X.. line the class writes for a restricted inverse (None: no restriction)"""
    R = canon(R)
    if R == [(None, None, False, False)]:
        return None
    if len(R) == 2 and R[0][0] is None and R[1][1] is None and R[0][1] == R[1][0]:
        return ("≠", R[0][1])
    lo, hi, lc, rc = R[0]
    if hi is None:
        return ("≥" if lc else ">", lo)
    return ("≤" if rc else "<", hi)


def check_dr(f, lines, probs, need):
    """D= and R= lines of F⁻¹ (need: they must be there)"""
    dl, rl = find_line(lines, "D="), find_line(lines, "R=")
    if not need and not dl and not rl:
        return
    if len(dl) != 1 or len(rl) != 1:
        probs.append(f"want one D= and one R= line, got {dl} {rl}")
        return
    try:
        ds, ex1 = parse_set(dl[0][2:], "X")
        rs, ex2 = parse_set(rl[0][2:], "Y")
    except Bad as e:
        probs.append(f"can not read D/R: {e}")
        return
    if not (ex1 and ex2):
        probs.append(f"D/R not exact: {dl} {rl}")
    if not same_set(ds, f.range()):
        probs.append(f"D of F⁻¹ printed {dl[0]!r}, R_f is {set_text(f.range())}")
    if not same_set(rs, f.domain()):
        probs.append(f"R of F⁻¹ printed {rl[0]!r}, D_f is {set_text(f.domain())}")


def check_find(case, page, rng, probs, mode="find"):
    f = case["f"]
    lines = page[1:]
    if isinstance(f, Rat) and f.constant():
        for h in ("NO INVERSE FUNCTION", "(F IS A CONSTANT)"):
            if h not in lines:
                probs.append(f"constant f: missing {h!r}")
        return
    if not f.one_to_one():
        check_witness(f, lines, probs, ["NO INVERSE FUNCTION", "(NOT ONE-TO-ONE)"])
        return
    if mode == "dr":
        if "FOR F⁻¹:" not in lines:
            probs.append("missing FOR F⁻¹:")
        check_dr(f, lines, probs, True)
        if find_line(lines, "F⁻¹(X)="):
            probs.append("D/R question shows the formula too")
        return
    i = [k for k, l in enumerate(lines) if l.startswith("F⁻¹(X)=")]
    if len(i) != 1:
        probs.append(f"want one F⁻¹(X)= line, got {lines}")
        return
    text = lines[i[0]][len("F⁻¹(X)="):]
    case["inv_text"] = text
    check_inverse_formula(f, text, rng, probs)
    want = None if isinstance(f, Rat) else restriction_text(f.range())
    fl = find_line(lines, "FOR X")
    if want is None:
        if fl:
            probs.append(f"restriction printed but none needed: {fl}")
        if isinstance(f, Pw):
            check_dr(f, lines, probs, False)
    else:
        if len(fl) != 1:
            probs.append(f"want restriction FOR X{want[0]}{want[1]}, got {fl}")
        else:
            mm = re.fullmatch(r"FOR X([≥≤<>≠])(.+)", fl[0])
            v = ti_num(mm.group(2))[0] if mm else None
            if not mm or mm.group(1) != want[0] or not same(v, want[1]):
                probs.append(f"restriction printed {fl[0]!r}, want X{want[0]}{want[1]}")
        check_dr(f, lines, probs, True)


def check_why_find(case, page, probs):
    """the WHY page: CHECK: F(e)=v AND F⁻¹(v)=e; for fractions Y(P)=Q must give F⁻¹"""
    f = case["f"]
    lines = page[1:]
    if not page[0].startswith("PAGE WHY"):
        probs.append(f"WHY page head {page[0]!r}")
    if isinstance(f, Rat) and (f.constant() or not f.one_to_one()):
        return
    if isinstance(f, Pw) and not f.one_to_one():
        return
    c1 = [l for l in lines if l.startswith("CHECK: F(")]
    c2 = [l for l in lines if l.startswith("AND F⁻¹(")]
    if len(c1) != 1 or len(c2) != 1:
        probs.append(f"WHY: want CHECK lines, got {lines}")
        return
    m1 = re.fullmatch(r"CHECK: F\(([^)]+)\)=(.+)", c1[0])
    m2 = re.fullmatch(r"AND F⁻¹\(([^)]+)\)=(.+)", c2[0])
    if not m1 or not m2:
        probs.append(f"WHY: bad CHECK lines {c1} {c2}")
        return
    e, v = ti_num(m1.group(1))[0], ti_num(m1.group(2))[0]
    try:
        fe = f(e)
        if not same(fe, v, mp.mpf("1e-9")):
            probs.append(f"WHY: F({e}) is {fe}, printed {v}")
    except Undef:
        probs.append(f"WHY: check point {e} outside D_f")
    if not same(ti_num(m2.group(1))[0], v) or not same(ti_num(m2.group(2))[0], e):
        probs.append(f"WHY: second check line does not match: {c2[0]!r}")
    if isinstance(f, Rat) and f.c != 0:
        yl = [l for l in lines if l.startswith("Y(")]
        mm = re.fullmatch(r"Y\((.+)\)=(.+)", yl[0]) if yl else None
        if not mm:
            probs.append(f"WHY: no Y(..)=.. line: {lines}")
            return
        try:
            got = to_sym(formula(mm.group(2))) / to_sym(formula(mm.group(1)))
            want = to_sym(formula(case["inv_text"])) if case.get("inv_text") else None
            if want is not None and sp.cancel(got - want) != 0:
                probs.append(f"WHY: {yl[0]!r} does not give F⁻¹ {case['inv_text']!r}")
        except Bad as e2:
            probs.append(f"WHY: can not read {yl[0]!r}: {e2}")


def comp_identity(outer, inner, rng):
    """f(g(x)) = x for every x in R_f (outer = f)? -> (True/False, a failing x or None, its value)"""
    R = outer.range()
    pts = samples(R, rng, k=8)
    defined = 0
    for x in pts:
        try:
            gx = inner(x)
        except Undef:
            return False, x, None
        try:
            v = outer(gx)
        except Undef:
            return False, x, None
        defined += 1
        if not same(v, x, mp.mpf("1e-20")):
            return False, x, v
    return defined > 0, None, None


def check_comp_line(line, name_o, name_i, outer, inner, rng, probs, case):
    """one printed line F(G(X))=... (outer = F)"""
    pre = f"{name_o}({name_i}("
    if not line.startswith(pre):
        probs.append(f"composition line {line!r} does not start with {pre!r}")
        return None
    rest = line[len(pre):]
    if rest == "X))=X" or re.fullmatch(r"X\)\)=-?\d+X/-?\d+=X", rest):
        ok, x, v = comp_identity(outer, inner, rng)
        if not ok:
            probs.append(f"{line!r} but at x={x} it gives {v}")
        if rest != "X))=X":
            a = rest[4:].split("X/")[0]
            b = rest[4:].split("X/")[1][:-2]
            if a != b:
                probs.append(f"{line!r}: aX/a with two different numbers")
        return True
    mm = re.fullmatch(r"X\)\)=(.+)≠X", rest)
    if mm:
        try:
            node = formula(mm.group(1))
        except Bad as e:
            probs.append(f"can not read {line!r}: {e}")
            return False
        probs.extend(p for p in style_problems(mm.group(1)) if not p.startswith("decimal"))
        tol = mp.mpf("1e-9") if not re.search(r"\d\.\d", mm.group(1)) else mp.mpf("1e-5")
        defined = []
        for x in samples(inner.domain(), rng, k=10):
            try:
                defined.append((x, outer(inner(x))))
            except Undef:
                pass
        if not defined:
            probs.append(f"{line!r}: {name_o}({name_i}(X)) is undefined for every x")
            return False
        if isinstance(outer, Rat) and isinstance(inner, Rat):
            try:
                got = to_sym(node)
                for x, v in defined:
                    if sp.Rational(v) != got.subs(XS, sp.Rational(x)):
                        probs.append(f"{line!r}: at x={x} the composite is {v}")
                        break
                if sp.cancel(got - XS) == 0:
                    probs.append(f"{line!r}: that IS x")
            except Bad as e:
                probs.append(f"{line!r}: {e}")
        else:
            n = 0
            for x in samples(inner.domain(), rng, k=8):
                try:
                    v = outer(inner(x))
                except Undef:
                    continue
                try:
                    p = ev(node, x)
                except Undef:
                    probs.append(f"{line!r}: printed formula undefined at {x}")
                    continue
                n += 1
                if not same(v, p, tol):
                    probs.append(f"{line!r}: at x={x} composite is {mp.nstr(mpv(v), 10)}, formula {mp.nstr(mpv(p), 10)}")
                    break
            ok, _, _ = comp_identity(outer, inner, rng)
            if ok:
                probs.append(f"{line!r} but the composite is x on R_{name_o}")
        return False
    mm = re.fullmatch(r"([^)]+)\)\)=(.+)≠(.+)", rest)
    if mm:
        a, ea = ti_num(mm.group(1))
        v, ev_ = ti_num(mm.group(2))
        a2, _ = ti_num(mm.group(3))
        if not same(a, a2):
            probs.append(f"{line!r}: the two x numbers differ")
        try:
            real = outer(inner(a))
            if not same(real, v, mp.mpf("1e-6")):
                probs.append(f"{line!r}: really {name_o}({name_i}({a}))={mp.nstr(mpv(real), 12)}")
            elif ev_ and not same(real, v, mp.mpf("1e-25")):
                case["fake_exact"] = case.get("fake_exact", 0) + 1
                probs.append(f"{line!r}: {mp.nstr(mpv(real), 20)} is not a fraction (HAFRAC shows it as one)")
            if same(real, a, mp.mpf("1e-12")):
                probs.append(f"{line!r}: but that equals x")
        except Undef:
            probs.append(f"{line!r}: really undefined")
        case["inexact"] += 0 if ev_ else 1
        return False
    if rest == "X)) UNDEFINED":
        for x in samples(inner.domain(), rng, k=10):
            try:
                outer(inner(x))
                probs.append(f"{line!r}: but {name_o}({name_i}({x})) is defined")
                break
            except Undef:
                pass
        return False
    mm = re.fullmatch(r"([^)]+)\)\) UNDEFINED", rest)
    if mm:
        a = ti_num(mm.group(1))[0]
        try:
            outer(inner(a))
            probs.append(f"{line!r}: but it is defined")
        except Undef:
            pass
        if not in_set(a, outer.range()) and not (isinstance(outer, Rat) and outer.constant()):
            probs.append(f"{line!r}: {a} is not in R_{name_o}, so it proves nothing")
        return False
    probs.append(f"unknown composition line {line!r}")
    return None


def check_verify(case, page, rng, probs):
    f, g = case["f"], case["g"]
    lines = page[1:]
    if isinstance(f, Rat) and isinstance(g, Rat) and (f.constant() or g.constant()):
        truth = False
    else:
        truth = comp_identity(f, g, rng)[0] and comp_identity(g, f, rng)[0]
    head = "YES, INVERSES" if truth else "NO, NOT INVERSES"
    if head not in lines:
        probs.append(f"want {head!r} (f={f}, g={g})")
    fg = [l for l in lines if l.startswith("F(G(")]
    gf = [l for l in lines if l.startswith("G(F(")]
    if len(fg) != 1 or len(gf) != 1:
        probs.append(f"want one F(G( and one G(F( line: {lines}")
        return
    r1 = check_comp_line(fg[0], "F", "G", f, g, rng, probs, case)
    r2 = check_comp_line(gf[0], "G", "F", g, f, rng, probs, case)
    if truth and not (r1 and r2):
        probs.append("YES expected but a composition line shows a failure")
    if not truth and r1 and r2:
        probs.append("both lines say =X but they are not inverses")
    # restriction notes for an even power
    notes = [l for l in lines if "NEEDS" in l]
    want_notes = []
    if truth:
        for name, h, other in (("F", f, g), ("G", g, f)):
            if isinstance(h, Pw) and not h.one_to_one():
                r = restriction_text(other.range())
                want_notes.append(f"({name} NEEDS X{r[0]}{Fr(r[1]) if isinstance(r[1], Fr) else r[1]})" if r else None)
    for w in want_notes:
        if w is None:
            continue
        mm = [n for n in notes if n.startswith(w[:9])]
        if not mm:
            probs.append(f"missing restriction note like {w!r}")
            continue
        m2 = re.fullmatch(r"\((F|G) NEEDS X([≥≤<>])(.+)\)", mm[0])
        m3 = re.fullmatch(r"\((F|G) NEEDS X([≥≤<>])(.+)\)", w)
        if not m2 or m2.group(2) != m3.group(2) or not same(ti_num(m2.group(3))[0], Fr(m3.group(3))):
            probs.append(f"restriction note {mm[0]!r}, want {w!r}")
    if len(notes) > len([w for w in want_notes if w]):
        probs.append(f"unexpected restriction notes {notes}")


def check_hlt(case, page, rng, probs):
    f = case["f"]
    lines = page[1:]
    if case["yes"]:
        for h in ("YES, HAS INVERSE", "(PASSES THE HLT)"):
            if h not in lines:
                probs.append(f"want {h!r}, got {lines}")
        if "NO, NOT ONE-TO-ONE" in lines:
            probs.append("says NO for a one-to-one function")
        return
    if f is None:     # the student said a flat line hits twice
        for h in ("NO, NOT ONE-TO-ONE", "(FAILS THE HLT)"):
            if h not in lines:
                probs.append(f"want {h!r}")
        return
    check_witness(f, lines, probs, ["NO, NOT ONE-TO-ONE"])


def check_dr_given(case, page, rng, probs):
    lines = page[1:]
    if "FOR F⁻¹:" not in lines:
        probs.append("missing FOR F⁻¹:")
    dl, rl = find_line(lines, "D="), find_line(lines, "R=")
    if len(dl) != 1 or len(rl) != 1:
        probs.append(f"want D= and R= lines: {lines}")
        return
    ds, _ = parse_set(dl[0][2:], "X")
    rs, _ = parse_set(rl[0][2:], "Y")
    if not same_set(ds, [case["rng"]]):
        probs.append(f"D printed {dl[0]!r}, want {set_text([case['rng']])}")
    if not same_set(rs, [case["dom"]]):
        probs.append(f"R printed {rl[0]!r}, want {set_text([case['dom']])}")


# ============================================================================ case makers
def one_find(rng):
    f, shape, keys = rand_function(rng)
    return dict(f=f, keys=keys, desc=f"FIND {shape} f={f}", check=check_find)


def one_verify(rng):
    f, shape, kf = rand_function(rng, allow_bad=False)
    r = rng.random()
    can = (isinstance(f, Rat) and not f.constant()) or isinstance(f, Pw)
    if can and r < 0.5:
        g = true_inverse(f)
        how = "true inverse"
    elif can and r < 0.7:
        g0 = true_inverse(f)
        if isinstance(g0, Rat):
            g = Rat(g0.a, g0.b + g0.d * rng.choice([1, -1, 2]), g0.c, g0.d)
        else:
            g = Pw(g0.A, g0.B, g0.C, g0.D + rng.choice([1, -1, Fr(1, 2)]), g0.p.numerator, g0.p.denominator)
        how = "perturbed inverse"
    elif r < 0.8:
        g = f
        how = "f with itself"
    else:
        g, _, _ = rand_function(rng, allow_bad=False)
        how = "random"
    kg = keys_for(rng, g) if how != "random" else None
    if kg is None:
        g, _, kg = rand_function(rng, allow_bad=False)
    if rng.random() < 0.5:   # the inverse typed first
        f, g, kf, kg = g, f, kg, kf
    return dict(f=f, g=g, keys=kf + kg, desc=f"VERIFY {how}: f={f} g={g}", check=check_verify)


def one_dr_formula(rng):
    f, shape, keys = rand_function(rng, allow_bad=False)
    return dict(f=f, keys=["k2"] + keys, desc=f"D/R formula {shape} f={f}",
                check=lambda c, p, r, pr: check_find(c, p, r, pr, mode="dr"))


BR = {(True, True): "k1", (True, False): "k2", (False, True): "k3", (False, False): "k4"}


def rand_interval(rng):
    lo = None if rng.random() < 0.2 else rcoef(rng, -12, 12, p_frac=0.15)
    hi = None if rng.random() < 0.25 else rcoef(rng, -12, 12, p_frac=0.15)
    if lo is not None and hi is not None:
        if lo == hi:
            hi = lo + rng.choice([1, 3, Fr(1, 2)])
        if lo > hi:
            lo, hi = hi, lo
    lc = lo is not None and rng.random() < 0.5
    rc = hi is not None and rng.random() < 0.5
    keys = [f"t:{minus(rng) + 'I' if lo is None else num_text(rng, lo)}",
            f"t:{'I' if hi is None else num_text(rng, hi)}"]
    if lo is not None or hi is not None:
        keys.append(BR[(lc if lo is not None else rng.random() < 0.5, rc if hi is not None else rng.random() < 0.5)])
    return (lo, hi, lc, rc), keys


def one_dr_given(rng):
    dom, k1 = rand_interval(rng)
    rg, k2 = rand_interval(rng)
    return dict(dom=dom, rng=rg, keys=["k1"] + k1 + k2, desc=f"D/R given D={set_text([dom])} R={set_text([rg])}",
                check=check_dr_given)


def quad_text(rng, a, b, c):
    """a parabola typed at Y= (standard form, vertex form, or X^2)"""
    if a != 0 and rng.random() < 0.4:
        h = -b / (2 * a)
        k = c - b * b / (4 * a)
        inner = "X" if h == 0 else "(X" + ("-" if h > 0 else "+") + num_text(rng, abs(h), paren_ok=False) + ")"
        sq = inner + ("²" if rng.random() < 0.8 else "^2")
        coef = "" if a == 1 else minus(rng) if a == -1 else (("(" + num_text(rng, a) + ")") if a.denominator > 1 else num_text(rng, a))
        s = coef + sq
        if k != 0:
            s += ("+" if k > 0 else "-") + num_text(rng, abs(k), paren_ok=False)
        return s
    parts = []
    for coef, body in ((a, "X²"), (b, "X"), (c, "")):
        if coef == 0:
            continue
        ac = abs(coef)
        if body:
            t = ("" if ac == 1 else (f"({ac.numerator}/{ac.denominator})" if ac.denominator > 1 else str(ac))) + body
        else:
            t = num_text(rng, ac, paren_ok=False)
        sign = "-" if coef < 0 else "+"
        if not parts:
            parts.append((minus(rng) if coef < 0 else "") + t)
        else:
            parts.append(sign + t)
    return "".join(parts) or "0"


def one_hlt(rng):
    fam = rng.choice(["line", "parab", "parab", "parab", "odd", "abs", "abs", "pow", "pow", "pow", "frac", "exp",
                      "floor", "graph", "graph", "graph", "graph"])
    keys = ["k4"]
    if fam in ("line", "odd", "frac", "exp"):
        k = {"line": "k1", "odd": "k3", "frac": "k6", "exp": "k7"}[fam]
        return dict(f=None, yes=True, keys=keys + [k], desc=f"HLT {fam}", check=check_hlt)
    if fam == "floor":
        return dict(f=FloorF(), yes=False, keys=keys + ["k8"], desc="HLT [[x]]", check=check_hlt)
    if fam == "parab":
        a = rcoef(rng, -4, 4, p_zero=0.08, p_frac=0.2)
        b = rcoef(rng, -8, 8, p_zero=0.3)
        c = rcoef(rng, -9, 9, p_zero=0.2)
        f = Quad(a, b, c)
        return dict(f=f, yes=f.one_to_one(), keys=keys + ["k2", f"t:{quad_text(rng, a, b, c)}"],
                    desc=f"HLT parabola {a}x²+{b}x+{c}", check=check_hlt)
    if fam == "abs":
        A = rcoef(rng, -5, 5, nonzero=True)
        B, C = lin(rng)
        Dd = rcoef(rng, -9, 9, p_zero=0.3)
        f = Ab(A, B, C, Dd)
        return dict(f=f, yes=False, keys=keys + ["k4", f"t:{front_text(rng, A)}", f"t:{lin_text(rng, B, C, inside=True)}",
                                                  f"t:{end_text(rng, Dd)}"],
                    desc=f"HLT abs {A}|{B}x+{C}|+{Dd}", check=check_hlt)
    if fam == "pow":
        p = rand_power(rng)
        if p.numerator % 2:
            return dict(f=None, yes=True, keys=keys + ["k5", f"t:{power_text(rng, p)}"], desc=f"HLT power {p}",
                        check=check_hlt)
        A = rcoef(rng, -5, 5, nonzero=True)
        B, C = lin(rng)
        Dd = rcoef(rng, -9, 9, p_zero=0.3)
        f = Pw(A, B, C, Dd, p.numerator, p.denominator)
        return dict(f=f, yes=False, keys=keys + ["k5", f"t:{power_text(rng, p)}", f"t:{front_text(rng, A)}",
                                                  f"t:{lin_text(rng, B, C, inside=True)}", f"t:{end_text(rng, Dd)}"],
                    desc=f"HLT power f={f}", check=check_hlt)
    # graph
    r = rng.random()
    if r < 0.12:
        return dict(f=None, yes=False, keys=keys + ["k9", "k1"], desc="HLT graph: student says hits twice", check=check_hlt)
    if r < 0.22:
        return dict(f=None, yes=True, keys=keys + ["k9", "k2"], desc="HLT graph: student says no", check=check_hlt)
    n = rng.choice([1, 2, 2, 3, 3, 4, 4, 5, 6])
    xs = sorted(rng.sample(range(-9, 10), n))
    style = rng.random()
    if style < 0.3:
        ys = sorted(rng.sample(range(-9, 10), n), reverse=rng.random() < 0.5)
    else:
        ys = [rng.randint(-6, 6) for _ in range(n)]
    if n >= 2 and style > 0.9:
        k = rng.randrange(n - 1)
        ys[k + 1] = ys[k]          # a flat piece
    pts = [(Fr(x), Fr(y)) for x, y in zip(xs, ys)]
    lc, rc = rng.random() < 0.6, rng.random() < 0.6
    f = Graph(pts, lc, rc)
    order = list(pts)
    if rng.random() < 0.2:
        rng.shuffle(order)       # typed out of order (HAPTS sorts)
    gk = [f"t:{n}"]
    for x, y in order:
        gk += [f"t:{num_text(rng, x)}", f"t:{num_text(rng, y)}"]
    gk.append({(True, True): "k1", (False, True): "k2", (True, False): "k3", (False, False): "k4"}[(lc, rc)])
    return dict(f=f, yes=f.one_to_one(), keys=keys + ["k9", "k3"] + gk, desc=f"HLT graph {pts} ends {lc},{rc}",
                check=check_hlt)


class FloorF:
    kind = "floor"

    def __call__(self, x):
        return Fr(int(mp.floor(mpv(x))))

    def even(self):
        return False


KINDS = [("find", one_find, ["k1"], 0.34), ("verify", one_verify, ["k2"], 0.30), ("dr_given", one_dr_given, ["k3"], 0.08),
         ("dr_formula", one_dr_formula, ["k3"], 0.08), ("hlt", one_hlt, ["k4"], 0.20)]


def pick(rng, only=None):
    pool = [k for k in KINDS if not only or k[0] == only]
    r, acc = rng.random() * sum(k[3] for k in pool), 0
    for k in pool:
        acc += k[3]
        if r < acc:
            return k
    return pool[-1]


def build(rng, only=None):
    """one session: 1-3 problems of one kind (1:AGAIN between them), WHY sometimes, then HOME"""
    name, make, sub, _ = pick(rng, only)
    probs = []
    keys = ["k3"] + sub
    n = 1 if rng.random() < 0.75 else rng.choice([2, 3])
    for j in range(n):
        c = make(rng)
        c["kind"] = name
        k = list(c["keys"])
        if name == "hlt":
            k = k[1:]       # the k4 is in `sub`
        c["why"] = rng.random() < 0.2
        keys += k
        keys += ["k3", "k1" if j < n - 1 else "k2"] if c["why"] else ["k1" if j < n - 1 else "k2"]
        probs.append(c)
    # sometimes a CLEAR from the submenu first (it must go back to the main menu)
    if rng.random() < 0.05:
        keys = ["k3", "CLEAR"] + keys
    return name, probs, keys


def check_session(probs, m, rng):
    out = []
    pages = list(m.out)
    for c in probs:
        c.setdefault("inexact", 0)
        if not pages or pages[0][0] != "ANSWER:":
            out.append(f"no ANSWER page for {c['desc']}")
            return out
        page = pages.pop(0)
        if not page or page[-1] != "FOOTER " + FOOT:
            out.append(f"footer {page[-1] if page else None!r}, want {FOOT!r}")
        body = [l for l in page if not l.startswith("FOOTER")]
        p = [f"line wider than the screen (HAOUT splits it anywhere): {l!r}" for l in body
             if width(l) > 26 and l not in m.broken]
        try:
            c["check"](c, body, rng, p)
        except Bad as e:
            p.append(f"can not read the answer: {e}")
        if c["why"]:
            if not pages or not pages[0][0].startswith("PAGE WHY"):
                p.append("no WHY page")
            else:
                why = pages.pop(0)
                if why[-1] != "FOOTER " + FOOT2:
                    p.append(f"WHY footer {why[-1]!r}")
                if c["kind"] == "find":
                    check_why_find(c, [l for l in why if not l.startswith("FOOTER")], p)
        out += [f"[{c['desc']}] {x}" for x in p]
    if pages:
        out.append(f"extra pages {pages}")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-n", type=int, default=600)
    ap.add_argument("-s", type=int, default=1)
    ap.add_argument("-v", action="store_true")
    ap.add_argument("--kind", default=None)
    args = ap.parse_args()
    rng = random.Random(args.s)
    stats = dict(sessions=0, problems=0, mismatch=0, sim_error=0, more_pages=0, inexact=0)
    by_kind = {}
    t0 = time.time()
    for i in range(args.n):
        name, probs, keys = build(rng, args.kind)
        m, res, err = run(keys)
        stats["sessions"] += 1
        stats["problems"] += len(probs)
        bk = by_kind.setdefault(name, [0, 0])
        bk[0] += len(probs)
        bad = []
        if err or res[0] != "stop":
            bad.append(f"simulator end={res} error={err}; last screen: " + " | ".join(l for l in m.lines() if l.strip()))
            stats["sim_error"] += 1
        else:
            bad += check_session(probs, m, rng)
        if m.problems:
            bad.append(f"screen problems: {m.problems[:3]}")
        if m.wrap_problems:
            bad.append(f"line breaking: {m.wrap_problems[:3]}")
        stats["more_pages"] += m.more
        stats["inexact"] += sum(c.get("inexact", 0) for c in probs)
        if bad:
            stats["mismatch"] += 1
            bk[1] += 1
            print(f"MISMATCH #{i} [{name}] " + " ; ".join(c["desc"] for c in probs))
            print(f"   keys: {' '.join(keys)}")
            for b in bad[:8]:
                print(f"   - {b}")
            for a in m.out[-3:]:
                print("   answer: " + " | ".join(a))
        elif args.v:
            print(f"ok #{i} [{name}] " + " ; ".join(c["desc"] for c in probs) + " -> "
                  + " / ".join(" | ".join(a) for a in m.out))
    print(f"\n{stats['sessions']} sessions ({stats['problems']} problems) in {time.time() - t0:.0f}s: "
          f"{stats['mismatch']} mismatching sessions, {stats['sim_error']} simulator errors, "
          f"{stats['more_pages']} ENTER=MORE waits, {stats['inexact']} decimal witness values")
    for k, (n, bad) in by_kind.items():
        print(f"   {k}: {n} problems, {bad} mismatching sessions")
    return 1 if stats["mismatch"] else 0


if __name__ == "__main__":
    sys.exit(main())
