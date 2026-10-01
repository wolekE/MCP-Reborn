#!/usr/bin/env python3
"""
Randomized differential testing of the decomposition solver (main menu 7, programs HADECOMP and
HADECMP2).

Every case is a random h(x) of one of the nine menu shapes
    1:K(STUFF)^N+C  2:K√(STUFF)+C  3:K/(STUFF)^N+C  4:K/√(STUFF)+C  5:K|STUFF|+C
    6:A(STUFF)²+B(STUFF)+C  7:K𝑒^(STUFF)+C  8:K/(M+𝑒^(STUFF))  9:√(K/STUFF)
typed from the main menu exactly as a student presses keys:
  * STUFF from random templates typed the TI-84 way (X key, (-) key or the subtraction key, ^ or ²/³,
    √( ³√( 𝑒^( abs(, implicit multiplication 2X and X(X+1), / fractions, decimals, the chunk typed
    with its own parentheses "(5X-1)", a closing parenthesis left off at the end as TI users do);
    linear, quadratic, cubic, monomials, roots, exponentials, fractions, products, and STUFF = X;
  * the outside numbers: negative (either minus key, a lone minus = -1), fractions, decimals,
    a copied "+", zero end numbers, ENTER defaults (K=1, N=1, ROOT INDEX=2, C=0, M=0; shape 6:
    A=1, B=1, C=0), powers 1, negative and fractional, root index 2-6;
  * refused entries asked again (STUFF without X or empty, K=0, N=0, root index 1 or 2.5);
  * sessions chain problems with 1:AGAIN, the 3:WHY page (then 1:AGAIN or 2:HOME), 2:HOME and
    CLEAR at the shape menu.

Oracle (independent of the TI code): h is built from the shape and the numbers as an expression
tree, with STUFF parsed by a TI-84 precedence parser (implied multiplication = explicit, left to
right; negation below powers; a missing ")" at the end closed).  Every printed way "G(X)=..." /
"F(X)=..." is parsed the same way and must satisfy f(g(x)) = h(x): first sympy simplify(f(g(x))-h)
= 0 (x real); if sympy can not show it (branch questions such as (1/u)^(1/5) vs 1/u^(1/5)), the
two are compared at sample points in TI-84 real mode (odd roots of negatives are real, even roots
undefined) at 40 digits, wherever h is defined.  Neither g nor f may be x (defined and equal to x
at every sample point, so G(X)=1/(1/X) counts as x); the first way must use the typed chunk as g
(Cram 3: g = the inside chunk; Example 3.3's order puts g = e^(STUFF) first for shape 8) unless h
has no outside part; at least one way is printed (the only exception is the NONE screen when the
student typed the whole h as STUFF with power 1 and nothing outside); numbers are exact (a "." only
where the student typed one); the WHY page's "H(X)=..." must equal h; the footers are
1:AGAIN 2:HOME 3:WHY and 1:AGAIN 2:HOME; every screen line fits 26 columns (the shared HAOUT
width bug for a typed abs( is counted separately, see KNOWN).

Run from tools/:   python3 fuzz/fuzz_decomp.py [-n CASES] [-s SEED] [--shape 3] [-v] [--numeric-only]
"""

import argparse
import cmath
import random
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
FOOT = "1:AGAIN  2:HOME  3:WHY"
FOOT_WHY = "1:AGAIN  2:HOME"


# ============================================================================ TI-84 text -> sympy
TOKS = ["³√(", "√(", "𝑒^(", "abs(", "⁻¹", "²", "³", "^", "(", ")", "+", "-", "⁻", "*", "/", "|", "X",
        "0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "."]


def lex(text):
    out, i = [], 0
    while i < len(text):
        if text[i] == " ":
            i += 1
            continue
        for t in TOKS:
            if text.startswith(t, i):
                out.append(t)
                i += len(t)
                break
        else:
            raise ValueError(f"cannot read {text[i:]!r} in {text!r}")
    return out


class TIParse:
    """TI-84 Plus CE precedence: ^ and postfix ² ³ ⁻¹ highest (left to right), then negation, then
    * / and implied multiplication (one level, left to right), then + -.  A missing ) at the end
    is closed, as the calculator does.  |u| bars (the program prints them) are read as abs.
    Builds a small tree: ("n", Fraction) ("x",) (op, a, b) for + - * / ^, (fn, a) for
    neg sqrt cbrt exp abs."""

    def __init__(self, text):
        self.t = lex(text)
        self.i = 0
        self.bars = 0

    def peek(self):
        return self.t[self.i] if self.i < len(self.t) else None

    def take(self):
        tok = self.peek()
        self.i += 1
        return tok

    def parse(self):
        e = self.expr()
        if self.i != len(self.t):
            raise ValueError(f"extra text {self.t[self.i:]}")
        return e

    def expr(self):
        e = self.term()
        while self.peek() in ("+", "-"):
            op = self.take()
            e = (op, e, self.term())
        return e

    def starts_atom(self, tok):
        if tok is None:
            return False
        if tok == "|":
            return self.bars == 0
        return tok in ("(", "√(", "³√(", "𝑒^(", "abs(", "X", ".") or tok.isdigit()

    def term(self):
        e = self.neg()
        while True:
            tok = self.peek()
            if tok in ("*", "/"):
                self.take()
                e = (tok, e, self.neg())
            elif self.starts_atom(tok):
                e = ("*", e, self.neg())
            else:
                return e

    def neg(self):
        if self.peek() in ("-", "⁻"):
            self.take()
            return ("neg", self.neg())
        return self.power()

    def power(self):
        e = self.post()
        while self.peek() == "^":
            self.take()
            sign = 1
            while self.peek() in ("-", "⁻"):
                self.take()
                sign = -sign
            r = self.post()
            e = ("^", e, r if sign > 0 else ("neg", r))
        return e

    def post(self):
        e = self.atom()
        while self.peek() in ("²", "³", "⁻¹"):
            t = self.take()
            e = ("^", e, ("n", Fr(2))) if t == "²" else ("^", e, ("n", Fr(3))) if t == "³" else ("/", ("n", Fr(1)), e)
        return e

    def close(self):
        if self.peek() == ")":
            self.take()
        elif self.peek() is not None:
            raise ValueError(f"expected ) at {self.t[self.i:]}")

    def atom(self):
        t = self.take()
        if t is None:
            raise ValueError("unexpected end")
        if t.isdigit() or t == ".":
            s = t
            while self.peek() is not None and (self.peek().isdigit() or self.peek() == "."):
                s += self.take()
            return ("n", Fr(s))
        if t == "X":
            return ("x",)
        fn = {"(": None, "√(": "sqrt", "³√(": "cbrt", "𝑒^(": "exp", "abs(": "abs"}
        if t in fn:
            e = self.expr()
            self.close()
            return e if fn[t] is None else (fn[t], e)
        if t == "|":
            self.bars += 1
            e = self.expr()
            self.bars -= 1
            if self.take() != "|":
                raise ValueError("unclosed |")
            return ("abs", e)
        raise ValueError(f"unexpected {t!r}")


def ti(text):
    return TIParse(text).parse()


# ============================================================================ the oracle's arithmetic
mp.mp.dps = 40


def tipow(b, e):
    """b^e in TI-84 real mode: a negative base needs an exponent p/q with q odd (real root)"""
    if b is None or e is None:
        return None
    if e == int(e):
        if b == 0 and e < 0:
            return None
        return b ** int(e)
    if b > 0:
        return b ** e
    if b == 0:
        return mp.mpf(0) if e > 0 else None
    q = Fr(str(e)).limit_denominator(1000)
    if abs(q - Fr(str(e))) > Fr(1, 10 ** 20) or q.denominator % 2 == 0:
        return None  # ERR:NONREAL ANS
    v = abs(b) ** e
    return -v if q.numerator % 2 else v


def ev(t, xv):
    """value of tree t at x = xv (mpf), TI-84 real mode; None = undefined (error on the TI)"""
    if xv is None:
        return None
    k = t[0]
    if k == "n":
        return mp.mpf(t[1].numerator) / t[1].denominator
    if k == "x":
        return xv
    if k in ("neg", "sqrt", "cbrt", "exp", "abs"):
        a = ev(t[1], xv)
        if a is None:
            return None
        if k == "neg":
            return -a
        if k == "sqrt":
            return mp.sqrt(a) if a >= 0 else None
        if k == "cbrt":
            return mp.cbrt(a) if a >= 0 else -mp.cbrt(-a)
        if k == "exp":
            return mp.exp(a) if a < 1000 else None
        return abs(a)
    a, b = ev(t[1], xv), ev(t[2], xv)
    if a is None or b is None:
        return None
    if k == "+":
        return a + b
    if k == "-":
        return a - b
    if k == "*":
        return a * b
    if k == "/":
        return a / b if b != 0 else None
    if k == "^":
        return tipow(a, b)
    raise ValueError(k)


def to_sympy(t, x):
    k = t[0]
    if k == "n":
        return sp.Rational(t[1].numerator, t[1].denominator)
    if k == "x":
        return x
    if k in ("neg", "sqrt", "cbrt", "exp", "abs"):
        a = to_sympy(t[1], x)
        return {"neg": lambda: -a, "sqrt": lambda: sp.sqrt(a), "cbrt": lambda: sp.real_root(a, 3),
                "exp": lambda: sp.exp(a), "abs": lambda: sp.Abs(a)}[k]()
    a, b = to_sympy(t[1], x), to_sympy(t[2], x)
    return {"+": a + b, "-": a - b, "*": a * b, "/": a / b if b != 0 else sp.zoo, "^": a ** b}[k]


def subst(t, g):
    """the tree of t with x replaced by the tree g (f(g(x)))"""
    if t[0] == "x":
        return g
    if t[0] == "n":
        return t
    return (t[0],) + tuple(subst(a, g) for a in t[1:])


BASE_PTS = [Fr(n, 100) for n in (37, 173, 261, -83, -191, 337, 11, -329, 470, -530, 93, 1291, -1717, 59,
                                  2311, -2903, 7, -41)]
STATS = {"symbolic": 0, "numeric": 0}
KNOWN = {"HAOUT abs( width": 0}
SYMBOLIC = [True]


def points_for(h, rng_seed=7):
    """at least 5 x values where h is defined (TI real mode)"""
    out = [p for p in BASE_PTS if ev(h, mp.mpf(p.numerator) / p.denominator) is not None]
    r = random.Random(rng_seed)
    tries = 0
    while len(out) < 5 and tries < 600:
        tries += 1
        p = Fr(r.randint(-6000, 6000), r.choice([7, 11, 13, 100, 1000, 9973]))
        if ev(h, mp.mpf(p.numerator) / p.denominator) is not None:
            out.append(p)
    return out


def same_fn(a, h, pts):
    """a(x) = h(x) at every sample point where h is defined (a must be defined there too)"""
    if len(pts) < 3:
        return False
    for p in pts:
        xv = mp.mpf(p.numerator) / p.denominator
        vh, va = ev(h, xv), ev(a, xv)
        if va is None or abs(va - vh) > mp.mpf(10) ** -25 * max(1, abs(vh)):
            return False
    return True


def same_symbolic(a, h):
    """sympy: a - h simplifies to 0 (x real)"""
    x = sp.Symbol("x", real=True)
    try:
        d = to_sympy(a, x) - to_sympy(h, x)
        return sp.simplify(d) == 0
    except Exception:  # noqa: BLE001
        return False


def is_x(t, pts):
    """the tree t is just x: defined and equal to x at every sample point (1/(1/X) counts as x;
    (√(X))² does not, it is undefined for x < 0)"""
    for p in pts + BASE_PTS:
        xv = mp.mpf(p.numerator) / p.denominator
        v = ev(t, xv)
        if v is None or abs(v - xv) > mp.mpf(10) ** -25 * max(1, abs(xv)):
            return False
    return True


# ============================================================================ random problems
def fr_text(v, rng, minus=None, plus=False):
    """how a student types the number v ("-" or "⁻" for minus; fractions as a/b; some decimals;
    plus=True: sometimes a copied leading +, as at a prompt)"""
    v = Fr(v)
    mk = minus if minus is not None else rng.choice(["⁻", "-"])
    a = abs(v)
    if a.denominator == 1:
        s = str(a.numerator)
    elif a.denominator in (2, 4, 5, 8, 10) and rng.random() < 0.3:
        s = str(a.numerator / a.denominator)
        if s.startswith("0.") and rng.random() < 0.5:
            s = s[1:]
    else:
        s = f"{a.numerator}/{a.denominator}"
    if v < 0:
        return mk + s
    if plus and rng.random() < 0.05:
        return "+" + s
    return s


def rnum(rng, zero=True, small=False):
    r = rng.random()
    if zero and r < 0.15:
        return Fr(0)
    if r < 0.6:
        v = Fr(rng.randint(1, 5 if small else 9))
    elif r < 0.85:
        q = rng.choice([2, 3, 4, 5])
        v = Fr(rng.randint(1, 2 * q), q)
        if v.denominator == 1:
            v = Fr(rng.randint(1, 7), q + 1)
    else:
        v = Fr(rng.choice([1, 3, 5, 7]), rng.choice([2, 4, 10]))
    return v if rng.random() < 0.55 else -v


def coef_txt(rng, a, mk):
    """coefficient a written in front of a term (1 -> "", -1 -> "-")"""
    if a == 1:
        return ""
    if a == -1:
        return mk
    if a.denominator != 1:
        if rng.random() < 0.5:
            return fr_text(a, rng, mk) + "*"
        return (mk if a < 0 else "") + "(" + fr_text(abs(a), rng, mk) + ")"
    return fr_text(a, rng, mk)


def poly_text(rng, coefs, mk, sq_style):
    """coefs highest power first -> typed text like 2X²-3X+1 (terms in order), never empty"""
    deg = len(coefs) - 1
    parts = []
    for i, c in enumerate(coefs):
        p = deg - i
        if c == 0:
            continue
        c = Fr(c)
        if p == 0:
            body = fr_text(abs(c), rng, mk)
        else:
            xp = "X" if p == 1 else ("X²" if p == 2 and sq_style else "X³" if p == 3 and sq_style else f"X^{p}")
            ac = abs(c)
            if ac == 1:
                body = xp
            elif ac.denominator != 1:
                body = "(" + fr_text(ac, rng, mk) + ")" + xp
            else:
                body = str(ac.numerator) + xp
        if not parts:
            parts.append((mk if c < 0 else "") + body)
        else:
            parts.append(("-" if c < 0 else "+") + body)
    return "".join(parts)


def rand_stuff(rng):
    """(typed text, sympy) of a random inside chunk"""
    mk = rng.choice(["⁻", "-"])
    sq = rng.random() < 0.75
    k = rng.random()
    if k < 0.10:
        txt = "X"
    elif k < 0.32:  # linear aX+b, either order
        a = rnum(rng, zero=False)
        b = rnum(rng)
        if rng.random() < 0.25 and b != 0:
            txt = fr_text(b, rng, mk) + ("-" if a < 0 else "+") + (("" if abs(a) == 1 else
                                                                   coef_txt(rng, abs(a), mk)) + "X")
        else:
            txt = poly_text(rng, [a, b], mk, sq)
    elif k < 0.50:  # quadratic
        cs = [rnum(rng, zero=False, small=True), rnum(rng, small=True) if rng.random() < 0.5 else Fr(0),
              rnum(rng, small=True)]
        txt = poly_text(rng, cs, mk, sq)
        if rng.random() < 0.15 and cs[2] != 0 and cs[1] == 0:  # 4-X² style
            txt = fr_text(cs[2], rng, mk) + ("-" if cs[0] < 0 else "+") + poly_text(rng, [abs(cs[0]), 0, 0], mk, sq)
    elif k < 0.58:  # cubic / higher monomial + constant
        p = rng.choice([3, 3, 4, 5])
        cs = [rnum(rng, zero=False, small=True)] + [Fr(0)] * (p - 1) + [rnum(rng, small=True)]
        txt = poly_text(rng, cs, mk, sq)
    elif k < 0.66:  # roots
        inner = poly_text(rng, [rnum(rng, zero=False, small=True), rnum(rng, small=True)], mk, sq)
        fn = rng.choice(["√(", "√(", "³√("])
        c = rnum(rng)
        a = rnum(rng, zero=False, small=True) if rng.random() < 0.4 else Fr(1)
        txt = coef_txt(rng, a, mk) + fn + inner + ")"
        if c != 0:
            txt += ("-" if c < 0 else "+") + fr_text(abs(c), rng, mk)
        elif rng.random() < 0.3:
            txt = txt[:-1]  # closing parenthesis left off at the end
    elif k < 0.73:  # exponentials
        a = rnum(rng, zero=False, small=True)
        inner = poly_text(rng, [a, 0], mk, sq)
        c = rnum(rng)
        txt = "𝑒^(" + inner + ")"
        if c != 0:
            txt += ("-" if c < 0 else "+") + fr_text(abs(c), rng, mk)
        elif rng.random() < 0.3:
            txt = txt[:-1]
    elif k < 0.82:  # fractions
        t = rng.random()
        if t < 0.3:
            txt = "1/X" if rng.random() < 0.5 else f"{rng.randint(2, 9)}/X"
            c = rnum(rng)
            if c != 0:
                txt += ("-" if c < 0 else "+") + fr_text(abs(c), rng, mk)
        elif t < 0.65:
            txt = f"{rng.randint(1, 9)}/(" + poly_text(rng, [Fr(1), rnum(rng, zero=False, small=True)], mk, sq) + ")"
        else:
            txt = "(" + poly_text(rng, [Fr(1), rnum(rng, zero=False, small=True)], mk, sq) + ")/(" + \
                poly_text(rng, [rnum(rng, zero=False, small=True), rnum(rng, zero=False, small=True)], mk, sq) + ")"
            c = rnum(rng)
            if c != 0 and rng.random() < 0.4:
                txt += ("-" if c < 0 else "+") + fr_text(abs(c), rng, mk)
    elif k < 0.90:  # products (implied multiplication)
        t = rng.random()
        lin = poly_text(rng, [Fr(1), rnum(rng, zero=False, small=True)], mk, sq)
        if t < 0.4:
            txt = "X(" + lin + ")"
        elif t < 0.7:
            txt = f"{rng.randint(2, 5)}X(" + lin + ")"
        else:
            txt = "X√(X)" if rng.random() < 0.5 else "X²(" + lin + ")"
        c = rnum(rng)
        if c != 0 and rng.random() < 0.5:
            txt += ("-" if c < 0 else "+") + fr_text(abs(c), rng, mk)
    elif k < 0.94:  # decimals and abs(
        if rng.random() < 0.5:
            txt = rng.choice(["0.5X+1.5", ".5X-2", "1.2X²-0.4", "2.5-X"])
        else:
            txt = rng.choice(["abs(X)+1", "abs(X-2)", "2abs(X)-3", "abs(X)²+1"])
    elif k < 0.97:  # negative powers, x^-1, 2^X style
        txt = rng.choice(["X^" + mk + "2+1", "X⁻¹+3", "2^X+1", "X^(1/2)+1", "3^X", mk + "X²+4", mk + "X"])
    elif k < 0.985:  # reciprocal chunks (1/STUFF must not give G(X)=X)
        txt = rng.choice(["1/X", "X⁻¹", "X^-1", "X^(-1)", "2/X", "1/X+1", "(1/X)"])
    else:  # a sign typed twice (x - (-3) copied as X-⁻3)
        txt = rng.choice(["X-⁻3", "X²+⁻4", "4-⁻X", "2+⁻X²", "5X-⁻1", "1-⁻2X"])
    if rng.random() < 0.08 and txt != "X":
        txt = "(" + txt + ")"
    return txt, ti(txt)


class Prob:
    def __init__(self):
        self.shape = None
        self.keys = []
        self.h = None
        self.stuff = ""
        self.stuff_e = None
        self.vals = {}
        self.why = False
        self.desc = ""


def entry(rng, v, default, minus=None):
    """text typed for v at a prompt whose ENTER value is default"""
    if v == default and rng.random() < 0.65:
        return ""
    if v == -1 and rng.random() < 0.25:
        return rng.choice(["-", "⁻"])
    return fr_text(v, rng, minus, plus=True)


def make_problem(rng, shape=None):
    """a random problem whose h is defined at enough sample points (TI real mode)"""
    for _ in range(50):
        p = make_problem1(rng, shape)
        if len(points_for(p.h)) >= 5:
            return p
    raise RuntimeError("no usable problem")


def make_problem1(rng, shape=None):
    p = Prob()
    p.shape = G = shape or rng.choice([1, 1, 2, 2, 3, 3, 4, 4, 5, 6, 6, 7, 8, 8, 9])
    keys = [f"k{G}"]
    # refused STUFF / numbers first (asked again)
    stuff_txt, stuff_e = rand_stuff(rng)
    if rng.random() < 0.06:
        bad = rng.choice(["", "", "5", "2+3", "⁻4"])
        keys.append("t:" + bad)
        if bad == "":  # ENTER alone at STUFF= goes back to the shape menu: pick the shape again
            keys.append(f"k{G}")
    p.stuff, p.stuff_e = stuff_txt, stuff_e
    S_ = stuff_e
    K = Fr(1)
    N = Fr(1)
    A = 2
    C = Fr(0)
    M = Fr(0)

    def bad_retry(text_list):
        """type STUFF and refused numbers, then the screen asks again from STUFF"""
        keys.append("t:" + stuff_txt)
        keys.extend("t:" + t for t in text_list)

    if G == 6:
        A6 = rnum(rng, zero=False, small=True) if rng.random() < 0.8 else Fr(1)
        B6 = rnum(rng, small=True) if rng.random() < 0.8 else Fr(1)
        C6 = rnum(rng, small=True)
        if rng.random() < 0.06:  # h = A(STUFF)² with no other term (STUFF = X: h = X²)
            B6, C6 = Fr(0), Fr(0)
            A6 = Fr(1) if rng.random() < 0.6 else A6
        if rng.random() < 0.05:
            bad_retry(["0"])
        keys.append("t:" + stuff_txt)
        keys.append("t:" + entry(rng, A6, 1))
        b_txt = entry(rng, B6, 1)
        if B6 == 0:
            b_txt = "0"
        keys.append("t:" + b_txt)
        keys.append("t:" + entry(rng, C6, 0))
        p.h = ("+", ("+", ("*", ("n", A6), ("^", S_, ("n", Fr(2)))), ("*", ("n", B6), S_)), ("n", C6))
        p.vals = dict(A=A6, B=B6, C=C6)
        p.keys = keys
        p.desc = f"6 STUFF={stuff_txt} A={A6} B={B6} C={C6}"
        return p
    K = rnum(rng, zero=False) if rng.random() < 0.6 else Fr(rng.choice([1, 1, -1]))
    if G in (1, 3):
        r = rng.random()
        if r < 0.55:
            N = Fr(rng.choice([2, 2, 3, 4, 5]))
        elif r < 0.7:
            N = Fr(1)
        elif r < 0.85:
            N = Fr(rng.choice([-1, -2, -3]))
        else:
            N = Fr(rng.choice([1, 3, 5, 2]), rng.choice([2, 3]))
            if N.denominator == 1:
                N = Fr(3, 2)
    if G in (2, 4):
        A = rng.choice([2, 2, 2, 3, 3, 4, 5])
    if G in (1, 2, 3, 4, 5, 7):
        C = rnum(rng) if rng.random() < 0.7 else Fr(0)
    if G in (1, 2, 3, 4) and rng.random() < 0.06:  # a root that undoes the chunk's power: ³√(X³) is X
        if G in (2, 4):
            A = rng.choice([3, 5, 3])
            stuff_txt = rng.choice(["X³", "X^3", "(X³)"]) if A == 3 else "X^5"
        else:
            N, stuff_txt = rng.choice([(Fr(3), "³√(X)"), (Fr(3), "X^(1/3)"), (Fr(1, 3), "X³"), (Fr(1, 5), "X^5"),
                                       (Fr(1, 3), "X^3")])
        stuff_e = ti(stuff_txt)
        p.stuff, p.stuff_e, S_ = stuff_txt, stuff_e, stuff_e
    if G in (1, 3) and rng.random() < 0.08:  # degenerate: power 1 (or -1 on the bottom), often STUFF = X
        N = Fr(1) if G == 1 else Fr(-1)
        K = Fr(rng.choice([1, 1, -1, 2, -3, 1])) if rng.random() < 0.8 else Fr(1, 2)
        C = Fr(rng.choice([0, 0, 1, -1, 5, 2]))
        if rng.random() < 0.6:
            stuff_txt, stuff_e = "X", ("x",)
            p.stuff, p.stuff_e, S_ = stuff_txt, stuff_e, stuff_e
    if G == 8:
        M = rnum(rng) if rng.random() < 0.85 else Fr(0)
        if rng.random() < 0.5:
            M = Fr(1)
    # a refused entry, then the real one
    if rng.random() < 0.12:
        opts = ["K"]
        if G in (1, 3):
            opts.append("N")
        if G in (2, 4):
            opts.append("R")
        w = rng.choice(opts)
        if w == "K":
            bad_retry(["0"])
        elif w == "N":
            bad_retry([entry(rng, K, 1), "0"])
        else:
            bad_retry([entry(rng, K, 1), rng.choice(["1", "2.5", "0"])])
    keys.append("t:" + stuff_txt)
    keys.append("t:" + entry(rng, K, 1))
    if G in (1, 3):
        keys.append("t:" + entry(rng, N, 1))
    if G in (2, 4):
        keys.append("t:" + entry(rng, Fr(A), 2))
    if G in (1, 2, 3, 4, 5, 7):
        keys.append("t:" + entry(rng, C, 0))
    if G == 8:
        keys.append("t:" + entry(rng, M, 0))
    k, n, c, m = (("n", Fr(v)) for v in (K, N, C, M))

    def root(u, a):
        return ("sqrt", u) if a == 2 else ("cbrt", u) if a == 3 else ("^", u, ("n", Fr(1, a)))

    h = {1: lambda: ("+", ("*", k, ("^", S_, n)), c),
         2: lambda: ("+", ("*", k, root(S_, A)), c),
         3: lambda: ("+", ("/", k, ("^", S_, n)), c),
         4: lambda: ("+", ("/", k, root(S_, A)), c),
         5: lambda: ("+", ("*", k, ("abs", S_)), c),
         7: lambda: ("+", ("*", k, ("exp", S_)), c),
         8: lambda: ("/", k, ("+", m, ("exp", S_))),
         9: lambda: ("sqrt", ("/", k, S_))}[G]()
    p.h = h
    p.vals = dict(K=K, N=N, A=A, C=C, M=M)
    p.keys = keys
    p.desc = f"{G} STUFF={stuff_txt} " + " ".join(f"{a}={b}" for a, b in p.vals.items())
    return p


def make_session(rng, shape=None):
    """keys from the main menu and the problems they enter"""
    keys = ["ENTER", "k7"]
    probs = []
    n = rng.choice([1, 1, 2, 2, 3])
    for i in range(n):
        if rng.random() < 0.05:
            keys += ["CLEAR", "k7"]  # back to the main menu and in again
        p = make_problem(rng, shape)
        keys += p.keys
        p.why = rng.random() < 0.3
        probs.append(p)
        last = i == n - 1
        if p.why:
            keys.append("k3")
            keys.append("k2" if last else "k1")
        else:
            keys.append("k2" if last else "k1")
    return keys, probs


# ============================================================================ the simulator
class RecMachine(Machine):
    """records every line handed to HAOUT (whole, before wrapping), page starts and footers"""

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.out = []

    def exec(self, f):
        st = self.stmt(f.name, f.pc)
        if st[0] == "prgm":
            if st[1] == "HAANS":
                self.out.append(["ANSWER:"])
            elif st[1] == "HAPAGE":
                self.out.append(["PAGE " + "".join(self.strs.get("Str9", ()))])
            elif st[1] == "HAOUT" and self.out:
                self.out[-1].append("".join(self.strs["Str9"]))
            elif st[1] == "HAEND" and self.out:
                self.out[-1].append("FOOTER " + "".join(self.strs["Str9"]))
        super().exec(f)

    def getkey(self):
        if self.frames and self.frames[-1].name == "HAOUT":
            self.snap("key", "ENTER")
            return D(105)
        return super().getkey()


PROGS = None
SRC_DIR = [SRC]


def run(actions):
    global PROGS
    if PROGS is None:
        PROGS = load_programs(SRC_DIR[0])
    m = RecMachine(PROGS)
    err = None
    try:
        res = m.run(list(actions) + ["CLEAR"] * 6)
    except TIError as e:
        res, err = ("error", None), str(e)
    return m, res, err


# ============================================================================ checks
def ways_of(body):
    """[(g text, f text)] from the answer lines, and the other lines"""
    ways, other, g = [], [], None
    for line in body:
        s = line.strip()
        if s.startswith("OR "):
            s = s[3:]
        if s.startswith("G(X)=") and "IS NOT ALLOWED" not in s:
            g = s[5:]
        elif s.startswith("F(X)=") and g is not None:
            ways.append((g, s[5:]))
            g = None
        else:
            other.append(s)
    return ways, other


def check_answer(p, page):
    errs = []
    body = [l for l in page[1:] if not l.startswith("FOOTER ")]
    foot = [l[7:] for l in page if l.startswith("FOOTER ")]
    if foot != [FOOT]:
        errs.append(f"footer {foot}")
    ways, other = ways_of(body)
    G = p.shape
    pts = points_for(p.h)
    if len(pts) < 3:
        return [f"oracle: h is defined at too few points ({p.h})"]
    stuff_is_x = p.stuff_e == ("x",)
    # h = STUFF itself (power 1, nothing outside): no "inside chunk" way; the program may say NONE
    bare = (G == 1 and p.vals["N"] == 1 or G == 3 and p.vals["N"] == -1) and p.vals["K"] == 1 \
        and p.vals["C"] == 0
    none_ok = bare and not stuff_is_x
    if not ways:
        if not (none_ok and any(o.startswith("NONE") for o in other)):
            errs.append(f"no decomposition printed: {body}")
        return errs
    typed_dot = "." in p.stuff
    for n, (gt, ft) in enumerate(ways):
        for t in (gt, ft):
            if "." in t and not typed_dot:
                errs.append(f"decimal shown: {t!r}")
        try:
            ge, fe = ti(gt), ti(ft)
        except Exception as e:  # noqa: BLE001
            errs.append(f"cannot read way {n + 1}: G={gt!r} F={ft!r} ({e})")
            continue
        if is_x(ge, pts):
            errs.append(f"way {n + 1}: G(X)=X ({gt!r})")
        if is_x(fe, pts):
            errs.append(f"way {n + 1}: F(X)=X ({ft!r})")
        comp = subst(fe, ge)
        if SYMBOLIC[0] and same_symbolic(comp, p.h):
            STATS["symbolic"] += 1
        elif same_fn(comp, p.h, pts):
            STATS["numeric"] += 1
        else:
            errs.append(f"way {n + 1}: F(G(X)) != H: G={gt!r} F={ft!r}  STUFF={p.stuff!r}")
    # g = the inside chunk on the first way (shape 8: the guide's way 1 is g = e^(STUFF))
    if not stuff_is_x and not bare and ways:
        g1 = ti(ways[0][0])
        want = ("exp", p.stuff_e) if G == 8 else p.stuff_e
        if not same_fn(g1, want, points_for(want)):
            errs.append(f"first way's G is not the chunk: {ways[0][0]!r} (STUFF={p.stuff!r})")
    return errs


def check_why(p, page):
    errs = []
    foot = [l[7:] for l in page if l.startswith("FOOTER ")]
    if foot != [FOOT_WHY]:
        errs.append(f"WHY footer {foot}")
    hl = [l for l in page if l.startswith("H(X)=")]
    if len(hl) != 1:
        return errs + [f"WHY page has no H(X)= line: {page}"]
    try:
        he = ti(hl[0][5:])
    except Exception as e:  # noqa: BLE001
        return errs + [f"cannot read WHY line {hl[0]!r} ({e})"]
    if not same_fn(he, p.h, points_for(p.h)):
        errs.append(f"WHY {hl[0]!r} != h = {p.h}")
    return errs


def run_case(rng, shape=None):
    keys, probs = make_session(rng, shape)
    m, res, err = run(keys)
    errs = []
    if err:
        errs.append(f"TI error: {err}")
    elif res[0] != "stop":
        errs.append(f"did not stop cleanly: {res} last screen {[l for l in m.lines() if l.strip()]}")
    probs_left = [q for q in m.problems if not ("HAOUT" in q and "abs(" in q)]
    if len(probs_left) < len(m.problems):
        KNOWN["HAOUT abs( width"] += 1  # shared issue: HAOUT counts the 4-column abs( token as 1
    if probs_left:
        errs.append(f"screen problems: {probs_left[:3]}")
    if errs:
        return errs, keys, probs, m
    ans = [pg for pg in m.out if pg[0] == "ANSWER:"]
    why = [pg for pg in m.out if pg[0] == "PAGE WHY:"]
    if len(ans) != len(probs):
        errs.append(f"{len(ans)} answer pages for {len(probs)} problems")
    if len(why) != sum(p.why for p in probs):
        errs.append(f"{len(why)} WHY pages, expected {sum(p.why for p in probs)}")
    wi = 0
    for p, pg in zip(probs, ans):
        errs += [f"[{p.desc}] {e}" for e in check_answer(p, pg)]
        if p.why and wi < len(why):
            errs += [f"[{p.desc}] {e}" for e in check_why(p, why[wi])]
            wi += 1
    # the answer screen starts with ANSWER: on row 1
    for kind, detail, lines in m.events:
        if lines and lines[0].startswith("ANSWER") and lines[0] != "ANSWER:":
            errs.append(f"row 1 is {lines[0]!r}")
    return errs, keys, probs, m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-n", type=int, default=500)
    ap.add_argument("-s", type=int, default=1)
    ap.add_argument("--shape", type=int, default=None)
    ap.add_argument("-v", action="store_true")
    ap.add_argument("--numeric-only", action="store_true",
                    help="skip sympy simplify(f(g(x))-h) and use only the TI-mode sample-point check")
    ap.add_argument("--src", default=None, help="program folder (default ../src)")
    args = ap.parse_args()
    SYMBOLIC[0] = not args.numeric_only
    if args.src:
        SRC_DIR[0] = Path(args.src)
    rng = random.Random(args.s)
    stats = {g: 0 for g in range(1, 10)}
    bad = 0
    t0 = time.time()
    shown = 0
    nprob = 0
    for i in range(args.n):
        errs, keys, probs, m = run_case(rng, args.shape)
        for p in probs:
            stats[p.shape] += 1
            nprob += 1
        if errs:
            bad += 1
            if shown < 30:
                shown += 1
                print(f"--- case {i}: {[p.desc for p in probs]}")
                for e in errs[:6]:
                    print("   ", e)
                if args.v:
                    print("    keys:", keys)
    print(f"{args.n} sessions, {nprob} problems (by shape {stats}); {bad} sessions with mismatches; "
          f"{time.time() - t0:.1f}s; ways checked {STATS}; known shared-helper issues (not counted) {KNOWN}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
