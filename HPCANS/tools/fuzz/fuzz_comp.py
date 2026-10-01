#!/usr/bin/env python3
"""
Randomized differential testing of the composition solver (main menu 2, programs HACOMP*).

Each case is a random problem a student could meet: f and g of every HAFUNC shape
(AX+B, AX²+BX+C, (AX+B)/(CX+D), K/(AX+B), K√(AX+B)+C, fraction with X², graph, words), with
negative / fractional / zero coefficients, ENTER defaults, both minus keys, all four orders
(F(G), G(F), F(F), G(G)), 1:AGAIN chains, the 3:OTHER ORDER and 4:WHY footers, CLEAR navigation and
a refused 0 bottom, graph-value compositions (saved graphs, typed corners, values read off the
graph), 5:FROM FORMULAS values with 3:SAME F,G chains, √(graph) domains and graph(inside) domains.
The simulator is driven from the main menu exactly as a student would press keys.

The ANSWER lines are captured at every prgmHAOUT / prgmHACOMPW call (so a line the program breaks
over several rows is checked whole, and its pieces are checked separately: each fits 26 columns,
they rebuild the text, and no number is split) and compared with an exact oracle written
independently in Python/sympy:
  * formula: the printed text is parsed into sympy and compared with f(g(x)) evaluated exactly at
    sample points of the domain; a rational result must be one fraction in lowest terms with
    whole-number coefficients and no all-minus top and bottom (the class "× LCD" form);
  * domain: {x in Dg : g(x) in Df} built from exact critical points (sympy roots) and exact
    membership tests between them, never from the simplified formula; printed ends may be
    fractions, INF, or exact radicals like (3-√(21))/6 (parsed with sympy); a 6-digit decimal is
    accepted only for an irrational end (counted, and quadratic irrationals are listed) or a
    fraction whose denominator is over 9999;
  * values: exact f(g(x0)) with sympy, expected as a fraction or as q√(m)+p in lowest radical form
    (sympy radsimp), a decimal only for nested radicals.

Run from tools/:   python3 fuzz/fuzz_comp.py [-n CASES] [-s SEED] [--kind case_simplify] [-v]
"""

import argparse
import random
import re
import sys
import time
from fractions import Fraction as Fr
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOLS = HERE.parent
sys.path.insert(0, str(TOOLS))
from tibasic import D, Machine, TIError, load_programs  # noqa: E402

import sympy as sp  # noqa: E402

SRC = TOOLS.parent / "src"
X = sp.Symbol("x", real=True)
OO = sp.oo


class Unsupported(Exception):
    """the oracle (or the program, by design) does not handle this combination"""


# ----------------------------------------------------------------------------- exact helpers
def S(v):
    """Fraction / int -> sympy Rational"""
    if isinstance(v, Fr):
        return sp.Rational(v.numerator, v.denominator)
    return sp.sympify(v)


def sgn(e):
    """sign of a real algebraic sympy number: -1, 0, 1.  Rationals exactly; other algebraic
    numbers (small radicals of the problem's own numbers) at 100 digits, where a true nonzero
    value can not hide below 1e-70."""
    e = sp.sympify(e)
    if e.is_Rational:
        return 1 if e > 0 else -1 if e < 0 else 0
    v = sp.N(e, 100)
    if abs(sp.im(v)) > sp.Float("1e-70", 100):
        raise Unsupported(f"complex value {e}")
    v = sp.re(v)
    if abs(v) < sp.Float("1e-70", 100):
        return 0
    return 1 if v > 0 else -1


def cmp(a, b):
    if a == b:
        return 0
    if a == OO or b == -OO:
        return 1
    if a == -OO or b == OO:
        return -1
    return sgn(sp.sympify(a) - sp.sympify(b))


def pval(coefs, x):
    v = sp.Integer(0)
    for c in coefs:
        v = v * x + S(c)
    return v


def real_roots(expr):
    """exact real roots of a polynomial expression in X (empty for constants, incl. 0)"""
    expr = sp.expand(expr)
    if not expr.has(X):
        return []
    P = sp.Poly(expr, X)
    rs = sp.roots(P)
    if sum(rs.values()) != P.degree():
        raise Unsupported(f"roots of {expr}")
    out = []
    for r in rs:
        v = sp.N(r, 100)
        if abs(sp.im(v)) < sp.Float("1e-70", 100):
            out.append(r if r.is_Rational else sp.re(sp.expand(r)) if r.has(sp.I) else r)
    return out


UNKNOWN = "unknown"  # a words record: defined, value not given
QUAD_DECIMALS = []   # quadratic irrationals that were shown as decimals (should be rare: see report)


# ----------------------------------------------------------------------------- function models
class Rat:
    kind = "rat"

    def __init__(self, num, den):
        self.num, self.den = list(num), list(den)

    def value(self, x):
        if x is UNKNOWN:
            if self.crit_y():
                raise Unsupported("rational f of words g with a bottom zero")
            return UNKNOWN
        d = pval(self.den, x)
        if sgn(d) == 0:
            return None
        return pval(self.num, x) / d

    def expr(self, x):
        return pval(self.num, x) / pval(self.den, x)

    def crit_x(self):
        return real_roots(pval(self.den, X))

    def crit_y(self):
        return real_roots(pval(self.den, X))

    def preimages(self, c):
        return real_roots(pval(self.num, X) - c * pval(self.den, X))


class Root:
    kind = "root"

    def __init__(self, k, a, b, c):
        self.K, self.num, self.den, self.C = k, [a, b], [1], c

    def value(self, x):
        if x is UNKNOWN:
            raise Unsupported("root f of words g")
        d = pval(self.den, x)
        if sgn(d) == 0:
            return None
        u = pval(self.num, x) / d
        if sgn(u) < 0:
            return None
        return S(self.K) * sp.sqrt(u) + S(self.C)

    def expr(self, x):
        return S(self.K) * sp.sqrt(pval(self.num, x) / pval(self.den, x)) + S(self.C)

    def crit_x(self):
        return real_roots(pval(self.den, X)) + real_roots(pval(self.num, X))

    def crit_y(self):
        return self.crit_x()

    def preimages(self, c):
        if self.K == 0:
            return []
        s = (sp.sympify(c) - S(self.C)) / S(self.K)
        if sgn(s) < 0:
            return []
        return real_roots(pval(self.num, X) - s ** 2 * pval(self.den, X))


class Graph:
    kind = "graph"

    def __init__(self, pts, lc, rc):
        self.pts, self.lc, self.rc = sorted(pts), lc, rc

    def value(self, x):
        if x is UNKNOWN:
            raise Unsupported("graph of words")
        (x0, _), (xn, _) = self.pts[0], self.pts[-1]
        if cmp(x, S(x0)) < 0 or cmp(x, S(xn)) > 0:
            return None
        if (cmp(x, S(x0)) == 0 and not self.lc) or (cmp(x, S(xn)) == 0 and not self.rc):
            return None
        for (a, ya), (b, yb) in zip(self.pts, self.pts[1:]):
            if cmp(x, S(a)) >= 0 and cmp(x, S(b)) <= 0:
                return S(ya) + (S(yb) - S(ya)) * (x - S(a)) / (S(b) - S(a))
        return S(self.pts[-1][1])

    def crit_x(self):
        return [S(p[0]) for p in self.pts]

    def crit_y(self):
        return [S(self.pts[0][0]), S(self.pts[-1][0])]

    def preimages(self, c):
        out = []
        for (a, ya), (b, yb) in zip(self.pts, self.pts[1:]):
            ya_, yb_ = S(ya), S(yb)
            if ya_ == yb_:
                if cmp(ya_, c) == 0:
                    out += [S(a), S(b)]
            elif min(ya, yb) <= sp.N(c, 50) <= max(ya, yb) or cmp(c, ya_) == 0 or cmp(c, yb_) == 0:
                out.append(S(a) + (c - ya_) * (S(b) - S(a)) / (yb_ - ya_))
        return out


class Words:
    kind = "words"

    def __init__(self, lo, hi, lc, rc, zeros):
        self.lo, self.hi, self.lc, self.rc, self.zeros = lo, hi, lc, rc, zeros

    def inside(self, x):
        lo, hi = (S(self.lo) if self.lo is not None else -OO), (S(self.hi) if self.hi is not None else OO)
        if cmp(x, lo) < 0 or cmp(x, hi) > 0:
            return False
        if (cmp(x, lo) == 0 and not self.lc) or (cmp(x, hi) == 0 and not self.rc):
            return False
        return True

    def value(self, x):
        if x is UNKNOWN:
            raise Unsupported("words of words")
        if not self.inside(x):
            return None
        for a, b in self.zeros:
            if cmp(x, S(a)) >= 0 and cmp(x, S(b)) <= 0:
                return sp.Integer(0)
        return UNKNOWN

    def crit_x(self):
        out = [S(v) for v in (self.lo, self.hi) if v is not None]
        for a, b in self.zeros:
            out += [S(a), S(b)]
        return out

    def crit_y(self):
        return [S(v) for v in (self.lo, self.hi) if v is not None]

    def preimages(self, c):
        if cmp(c, 0) != 0:
            raise Unsupported("words g = nonzero level")
        out = []
        for a, b in self.zeros:
            out += [S(a), S(b)]
        return out


# ----------------------------------------------------------------------------- domain oracle
def between(a, b):
    """an exact rational strictly between a < b (either may be infinite)"""
    if a == -OO and b == OO:
        return sp.Integer(0)
    if a == -OO:
        return sp.floor(sp.N(b, 30)) - 1
    if b == OO:
        return sp.ceiling(sp.N(a, 30)) + 1
    fa, fb = sp.N(a, 50), sp.N(b, 50)
    m = sp.nsimplify((fa + fb) / 2, rational=True, tolerance=(fb - fa) / 8)
    if not (cmp(m, a) > 0 and cmp(m, b) < 0):
        m = sp.Rational(str(sp.N((fa + fb) / 2, 40)))
    return m


def composite_ok(f, g, x):
    y = g.value(x)
    if y is None:
        return False
    return f.value(y) is not None


def domain_of(member, crits):
    """union of intervals [(lo, hi, lc, rc)] from a membership test and the critical points"""
    pts = []
    for c in crits:
        c = sp.sympify(c)
        if all(cmp(c, p) != 0 for p in pts):
            pts.append(c)
    pts.sort(key=lambda v: sp.N(v, 60))
    bounds = [-OO] + pts + [OO]
    # the line as a sequence: gap0, p1, gap1, p2, ..., pn, gapn
    elems = []
    for i in range(len(bounds) - 1):
        if i > 0:
            elems.append((bounds[i], bounds[i], True, member(bounds[i])))
        elems.append((bounds[i], bounds[i + 1], False, member(between(bounds[i], bounds[i + 1]))))
    ivs, cur = [], None
    for lo, hi, is_pt, inn in elems:
        if inn:
            if cur is None:
                cur = [lo, hi, is_pt, is_pt]
            else:
                cur[1], cur[3] = hi, is_pt
        elif cur is not None:
            ivs.append(tuple(cur))
            cur = None
    if cur is not None:
        ivs.append(tuple(cur))
    return ivs


def comp_domain(f, g):
    crits = list(g.crit_x())
    for c in f.crit_y():
        crits += g.preimages(c)
    return domain_of(lambda x: composite_ok(f, g, x), crits)


def samples(ivs, k=5):
    out = []
    for lo, hi, lc, rc in ivs:
        if cmp(lo, hi) == 0:
            out.append(lo)
            continue
        out.append(between(lo, hi))
        if lo != -OO and hi != OO:
            fa, fb = sp.N(lo, 40), sp.N(hi, 40)
            for t in (sp.Rational(1, 7), sp.Rational(5, 6)):
                q = sp.nsimplify(fa + t * (fb - fa), rational=True, tolerance=(fb - fa) / 50)
                if cmp(q, lo) > 0 and cmp(q, hi) < 0:
                    out.append(q)
        elif lo == -OO and hi != OO:
            out.append(sp.floor(sp.N(hi, 30)) - 5)
        elif hi == OO and lo != -OO:
            out.append(sp.ceiling(sp.N(lo, 30)) + 7)
        else:
            out += [sp.Integer(-3), sp.Rational(5, 2)]
        if lc and lo != -OO:
            out.append(lo)
        if rc and hi != OO:
            out.append(hi)
    return out[:k * 3]


# ----------------------------------------------------------------------------- TI text <-> sympy
def ti_num(s):
    """'-17/4' '6' 'INF' '-INF' '1.414214' '-√(3)/2' '(3-√(21))/6' -> (sympy value, exact?)"""
    s = s.strip()
    if s in ("INF", "-INF"):
        return (OO if s == "INF" else -OO), True
    if re.fullmatch(r"-?\d+(/\d+)?", s):
        return sp.Rational(s), True
    if re.fullmatch(r"-?\d*\.\d+", s):
        return sp.Float(s, 30), False
    if "√" in s and re.fullmatch(r"[-+()/0-9√]+", s):
        return ti_formula(s), True
    raise ValueError(f"bad TI number {s!r}")


def split_depth0(t, sep):
    out, depth, cur = [], 0, ""
    for ch in t:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == sep and depth == 0:
            out.append(cur)
            cur = ""
        else:
            cur += ch
    return out + [cur]


def parse_domain(text):
    """'D=...' text -> list of (lo, hi, lc, rc, exact)"""
    t = text
    if t.startswith("D="):
        t = t[2:]
    if t == "NO REAL NUMBERS":
        return []
    if t == "ALL REALS":
        return [(-OO, OO, False, False, True)]
    if t.startswith("ALL REALS, X≠"):
        vals = [ti_num(v) for v in t[len("ALL REALS, X≠"):].split(",")]
        out, lo, lex = [], -OO, True
        for v, ex in vals:
            out.append((lo, v, False, False, ex and lex))
            lo, lex = v, ex
        out.append((lo, OO, False, False, lex))
        return out
    out = []
    for part in t.split("U"):
        if len(part) < 5 or part[0] not in "[(" or part[-1] not in "])":
            raise ValueError(f"bad interval {part!r} in {text!r}")
        ends = split_depth0(part[1:-1], ",")
        if len(ends) != 2:
            raise ValueError(f"bad interval {part!r} in {text!r}")
        lo, e1 = ti_num(ends[0])
        hi, e2 = ti_num(ends[1])
        out.append((lo, hi, part[0] == "[", part[-1] == "]", e1 and e2))
    return out


def same_domain(oracle, printed):
    """-> (ok, inexact_display)"""
    if len(oracle) != len(printed):
        return False, False
    inexact = False
    for (lo, hi, lc, rc), (plo, phi, plc, prc, ex) in zip(oracle, printed):
        for a, b in ((lo, plo), (hi, phi)):
            if a in (OO, -OO) or b in (OO, -OO):
                if a != b:
                    return False, inexact
                continue
            if isinstance(b, sp.Float):
                # a decimal is right only for an irrational end, or a fraction HAFRAC can not
                # show (denominator over 9999, by design)
                inexact = True
                a_ = sp.sympify(a)
                if (a_.is_Rational and a_.q <= 9999) or abs(sp.N(a, 30) - b) > 1e-6:
                    return False, inexact
                if not a_.is_Rational:
                    try:
                        if sp.degree(sp.minimal_polynomial(a_, X), X) == 2:
                            QUAD_DECIMALS.append(str(a_))
                    except Exception:  # noqa: BLE001
                        pass
            elif cmp(a, b) != 0:
                return False, inexact
        if bool(lc) != bool(plc) or bool(rc) != bool(prc):
            return False, inexact
    return True, inexact


def is_reals_minus_points(ivs):
    if len(ivs) < 2 or ivs[0][0] != -OO or ivs[-1][1] != OO:
        return False
    for (lo, hi, lc, rc), (lo2, hi2, lc2, rc2) in zip(ivs, ivs[1:]):
        if cmp(hi, lo2) != 0 or rc or lc2:
            return False
    return True


def ti_formula(text):
    """TI formula text (as printed) -> sympy expression in X"""
    s = text.replace("√(", "sqrt(").replace("²", "**2").replace("³", "**3").replace("^", "**")
    s = re.sub(r"(?<=[0-9)X])(?=[X(s])", "*", s)
    return sp.sympify(s, locals={"X": X, "sqrt": sp.sqrt})


def split_top(text):
    """split a printed rational result at its fraction bar.  HAFSTR puts a bar only between
    whole parts ('(A)/(B)', 'A/(B)', '(A)/X²', '2/X', '2/√(X)'); a '/' at depth 0 that is
    followed by digits is a number like the constant 4/9 in a polynomial."""
    depth = 0
    for i, ch in enumerate(text):
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        elif ch == "/" and depth == 0 and i + 1 < len(text) and text[i + 1] in "(X√":
            return text[:i], text[i + 1:]
    return text, None


STYLE_BAD = [
    (r"\+-|--|-\+|\+\+", "double sign"),
    (r"(?<![0-9/.])1X", "coefficient 1 shown"),
    (r"(?<![0-9/.])1√", "coefficient 1 shown"),
    (r"(?<![0-9/.])0X", "zero term shown"),
    (r"X\^1(?!\d)", "power 1 shown"),
    (r"\(\)", "empty parentheses"),
    (r"^\+", "leading plus"),
    (r"\.\d{3,}", "decimal coefficient (not exact)"),
]


def formula_checks(text, f, g, ivs):
    """-> list of problems with the printed formula"""
    probs = []
    for pat, what in STYLE_BAD:
        if re.search(pat, text):
            probs.append(f"style: {what} in {text!r}")
    try:
        e = ti_formula(text)
    except Exception as ex:  # noqa: BLE001
        return probs + [f"formula does not parse: {text!r} ({ex})"]
    # value check at sample points of the domain
    for x0 in samples(ivs):
        want = f.value(g.value(x0))
        if want is None or want is UNKNOWN:
            continue
        try:
            got = e.subs(X, x0)
        except Exception as ex:  # noqa: BLE001
            probs.append(f"formula {text!r} fails at x={x0}: {ex}")
            break
        if got.has(sp.zoo, sp.nan) or not got.is_real or sgn(got - want) != 0:
            probs.append(f"formula {text!r} at x={x0}: got {got}, want {want}")
            break
    # simplified-form check for rational results
    if "√" not in text:
        top, bot = split_top(text)
        try:
            pt = sp.Poly(ti_formula(top), X)
            if bot is not None:
                pb = sp.Poly(ti_formula(bot), X)
                if sp.degree(sp.gcd(pt, pb), X) > 0:
                    probs.append(f"not in lowest terms: {text!r} (common factor {sp.gcd(pt, pb)})")
                coefs = pt.all_coeffs() + pb.all_coeffs()
                if any(not c.is_Integer for c in coefs):
                    probs.append(f"fraction inside the fraction: {text!r}")
                elif sp.igcd(*[int(c) for c in coefs if c != 0] or [1]) != 1:
                    probs.append(f"top and bottom share a number factor: {text!r}")
                if pb.degree() == 0:
                    probs.append(f"constant bottom kept: {text!r}")
                if all(c <= 0 for c in pt.all_coeffs()) and all(c <= 0 for c in pb.all_coeffs()):
                    probs.append(f"minus signs on every term of top and bottom: {text!r}")
        except sp.PolynomialError:
            probs.append(f"not polynomial / polynomial: {text!r}")
    return probs


# ----------------------------------------------------------------------------- number typing
def fr_text(v):
    """exact text the way HAFRAC prints it"""
    v = Fr(v)
    if v.denominator == 1:
        return str(v.numerator)
    return f"{v.numerator}/{v.denominator}"


def decimal_text(e):
    v = float(sp.N(e, 30))
    t = f"{abs(v):.6f}".rstrip("0").rstrip(".")
    return ("-" if v < 0 else "") + t


def ti_value_text(e):
    """how the program should show an exact sympy value: a fraction, or p+q√m in lowest radical
    form (q√(m) first, like 2√(3)+1, (-1/2)√(5), -√(7)-3/2); a decimal only for other irrationals
    (nested roots) or fractions whose denominator is over 9999 -> (text, exact?)"""
    e = sp.sympify(e)
    if e.is_Rational:
        if e.q <= 9999:
            return (str(e.p) if e.q == 1 else f"{e.p}/{e.q}"), True
        return decimal_text(e), False
    ex = sp.expand(sp.radsimp(e))
    p, q, m = sp.Integer(0), sp.Integer(0), None
    for t in sp.Add.make_args(ex):
        if t.is_Rational:
            p += t
            continue
        c, r = t.as_coeff_Mul()
        if c.is_Rational and r.is_Pow and r.exp == sp.S.Half and r.base.is_Integer and (m is None or m == r.base):
            m, q = r.base, q + c
            continue
        return decimal_text(e), False
    if m is None or q == 0:
        return ti_value_text(p)
    if q.q > 9999 or p.q > 9999:
        return decimal_text(e), False
    qt = "" if q == 1 else "-" if q == -1 else str(q.p) if q.q == 1 else f"({q.p}/{q.q})"
    out = f"{qt}√({m})"
    if p > 0:
        out += "+" + (str(p.p) if p.q == 1 else f"{p.p}/{p.q}")
    elif p < 0:
        out += "-" + (str(-p.p) if p.q == 1 else f"{-p.p}/{p.q}")
    return out, True


def typed(rng, v):
    """how a student might type the number v (both minus keys, fractions)"""
    v = Fr(v)
    neg = v < 0
    a = abs(v)
    body = str(a.numerator) if a.denominator == 1 else f"{a.numerator}/{a.denominator}"
    if not neg:
        return body
    r = rng.random()
    if r < 0.45:
        return "⁻" + body
    if r < 0.85:
        return "-" + body
    return "(⁻" + body + ")"


def coef(rng, p_zero=0.12, p_frac=0.12, lo=-6, hi=6):
    r = rng.random()
    if r < p_zero:
        return Fr(0)
    if r < p_zero + p_frac:
        return Fr(rng.choice([-5, -3, -2, -1, 1, 2, 3, 5]), rng.choice([2, 3, 4]))
    v = 0
    while v == 0:
        v = rng.randint(lo, hi)
    return Fr(v)


def entry(rng, v, default):
    """keys for one coefficient: ENTER when the value is the default (sometimes)"""
    if v == default and rng.random() < 0.6:
        return "t:"
    return "t:" + typed(rng, v)


# ----------------------------------------------------------------------------- random functions
def rand_function(rng, shapes=(1, 2, 3, 4, 5, 6)):
    """-> (shape, model, keys after the shape menu, description)"""
    sh = rng.choice(shapes)
    if sh == 1:
        a, b = coef(rng), coef(rng)
        return sh, Rat([a, b], [1]), ["k1", entry(rng, a, 1), entry(rng, b, 0)], f"{a}x+{b}"
    if sh == 2:
        a, b, c = coef(rng, p_zero=0.05), coef(rng, p_zero=0.25), coef(rng, p_zero=0.25)
        return sh, Rat([a, b, c], [1]), ["k2", entry(rng, a, 1), entry(rng, b, 1), entry(rng, c, 0)], \
            f"{a}x²+{b}x+{c}"
    if sh == 3:
        while True:
            a, b, c, d = coef(rng), coef(rng), coef(rng), coef(rng)
            if c != 0 or d != 0:
                break
        return sh, Rat([a, b], [c, d]), ["k3", entry(rng, a, 1), entry(rng, b, 0), entry(rng, c, 1),
                                         entry(rng, d, 0)], f"({a}x+{b})/({c}x+{d})"
    if sh == 4:
        while True:
            k, a, b = coef(rng, p_zero=0.03), coef(rng, p_zero=0.08), coef(rng)
            if a != 0 or b != 0:
                break
        return sh, Rat([k], [a, b]), ["k4", entry(rng, k, 1), entry(rng, a, 1), entry(rng, b, 0)], \
            f"{k}/({a}x+{b})"
    if sh == 5:
        k, a, b, c = coef(rng, p_zero=0.03), coef(rng, p_zero=0.05), coef(rng), coef(rng, p_zero=0.4)
        return sh, Root(k, a, b, c), ["k5", entry(rng, k, 1), entry(rng, a, 1), entry(rng, b, 0),
                                      entry(rng, c, 0)], f"{k}√({a}x+{b})+{c}"
    if sh == 6:
        while True:
            a, b, c = coef(rng, p_zero=0.3), coef(rng, p_zero=0.3), coef(rng, p_zero=0.3)
            d, e, f = coef(rng, p_zero=0.3), coef(rng, p_zero=0.3), coef(rng, p_zero=0.3)
            if d != 0 or e != 0 or f != 0:
                break
        return sh, Rat([a, b, c], [d, e, f]), ["k6", entry(rng, a, 1), entry(rng, b, 1), entry(rng, c, 0),
                                               entry(rng, d, 1), entry(rng, e, 1), entry(rng, f, 0)], \
            f"({a}x²+{b}x+{c})/({d}x²+{e}x+{f})"
    raise ValueError(sh)


def rand_graph(rng, n=None):
    n = n or rng.randint(2, 6)
    xs = sorted(rng.sample(range(-8, 9), n))
    ys = [rng.randint(-4, 4) for _ in xs]
    if rng.random() < 0.15:
        ys = [Fr(y) + Fr(rng.choice([0, 1]), 2) for y in ys]
    lc, rc = rng.random() < 0.75, rng.random() < 0.75
    return Graph(list(zip(xs, ys)), lc, rc)


def graph_keys(rng, gr):
    keys = [f"t:{len(gr.pts)}"]
    for x, y in gr.pts:
        keys += ["t:" + typed(rng, x), "t:" + typed(rng, y)]
    ends = {(True, True): "k1", (False, True): "k2", (True, False): "k3", (False, False): "k4"}
    return keys + [ends[(gr.lc, gr.rc)]]


def graph_lists(name, gr):
    return {f"ʟG{name}X": [p[0] for p in gr.pts], f"ʟG{name}Y": [p[1] for p in gr.pts],
            f"ʟG{name}C": [int(gr.lc), int(gr.rc)]}


def lists_for(saved):
    out = {}
    for k, v in saved.items():
        out[k] = [D(str(Fr(x).numerator)) / D(str(Fr(x).denominator)) for x in v]
    return out


# ----------------------------------------------------------------------------- the machine
def disp_width(text):
    return len(text)  # "√(" is two characters here and two columns on the screen


class RecMachine(Machine):
    """records every answer page line as handed to HAOUT (whole, before wrapping); a line printed
    through HACOMPW (the comp line breaker) is recorded whole, and its pieces are checked"""

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.out = []
        self.wrap_problems = []
        self._pieces = None

    def exec(self, f):
        st = self.stmt(f.name, f.pc)
        if st[0] == "prgm":
            if st[1] == "HAANS":
                self.out.append(["ANSWER:"])
            elif st[1] == "HAPAGE":
                self.out.append(["PAGE " + "".join(self.strs.get("Str9", ()))])
            elif st[1] == "HACOMPW" and self.out:
                text = "".join(self.strs["Str9"])
                self.out[-1].append(text)
                self._pieces = (text, [])
            elif st[1] == "HAOUT" and self.out:
                line = "".join(self.strs["Str9"])
                if f.name == "HACOMPW" and self._pieces is not None:
                    self._pieces[1].append(line)
                else:
                    self.out[-1].append(line)
            elif st[1] == "HAEND" and self.out:
                self.out[-1].append("FOOTER " + "".join(self.strs["Str9"]))
        super().exec(f)
        if self._pieces is not None and (not self.frames or self.frames[-1].name not in ("HACOMPW", "HAOUT")):
            self.check_pieces(*self._pieces)
            self._pieces = None

    def check_pieces(self, text, pieces):
        if not pieces:
            self.wrap_problems.append(f"nothing printed for {text!r}")
            return
        joined = pieces[0]
        for a, b in zip(pieces, pieces[1:]):
            joined += (" " if text[len(joined):len(joined) + 1] == " " else "") + b
            if a and b and a[-1] in "0123456789/.√" and b[0] in "0123456789/)." :
                self.wrap_problems.append(f"number split across lines: {a!r} | {b!r}")
        if joined != text:
            self.wrap_problems.append(f"pieces {pieces} do not make {text!r}")
        for pc in pieces:
            if disp_width(pc) > 26:
                self.wrap_problems.append(f"piece wider than 26: {pc!r}")


PROGS = None


def run(actions, saved=None):
    global PROGS
    if PROGS is None:
        PROGS = load_programs(SRC)
    m = RecMachine(PROGS, persistent_lists=lists_for(saved or {}))
    err = None
    try:
        res = m.run(list(actions) + ["CLEAR"] * 6)
    except TIError as e:
        res, err = ("error", None), str(e)
    return m, res, err


# ----------------------------------------------------------------------------- case kinds
NAMES = {1: ("F", "G"), 2: ("G", "F"), 3: ("F", "F"), 4: ("G", "G")}


def one_simplify(rng, allow_special=True):
    """one problem of menu 1: keys from WHICH ONE IS ASKED? to the answer, and its checks"""
    J = rng.choice([1, 1, 2, 2, 3, 4])
    saved, keys, desc = {}, [f"k{J}"], ""
    fm = gm = None
    special = rng.random() if allow_special else 1
    if J != 4:
        if special < 0.06 and J in (1, 2):
            gr = rand_graph(rng)
            if rng.random() < 0.5:
                saved.update(graph_lists("F", gr))
                fk = ["k7", "k2"]
            else:
                fk = ["k7"] + graph_keys(rng, gr)
            fm, fd = gr, f"graph{gr.pts}{'[' if gr.lc else '('}{']' if gr.rc else ')'}"
        elif special < 0.10 and J == 1:
            lo, hi = rng.randint(-6, 0), rng.randint(1, 9)
            lc, rc = rng.random() < 0.6, rng.random() < 0.6
            br = {(True, True): "k1", (True, False): "k2", (False, True): "k3", (False, False): "k4"}[(lc, rc)]
            fm = Words(lo, hi, lc, rc, [])
            fk = ["k8", f"t:{typed(rng, lo)}", f"t:{hi}", br, "t:", "t:"]
            fd = f"words {lo}..{hi}"
        else:
            _, fm, fk, fd = rand_function(rng)
        keys += fk
        desc += f"f={fd} "
    if J != 3:
        _, gm, gk, gd = rand_function(rng)
        keys += gk
        desc += f"g={gd} "
    if J == 3:
        gm = fm
    if J == 4:
        fm = gm
    outer, inner = {1: (fm, gm), 2: (gm, fm), 3: (fm, fm), 4: (gm, gm)}[J]
    checks = [(f"{NAMES[J][0]}({NAMES[J][1]}(X))", outer, inner)]
    return J, keys, saved, desc, checks, (outer, inner)


def case_simplify(rng):
    """menu 2 → 1:SIMPLIFY + DOMAIN, every order, formula shapes (and sometimes graph / words);
    sometimes 1:AGAIN for a second / third problem, then 3:OTHER ORDER, 4:WHY or 2:HOME"""
    n = 1 if rng.random() < 0.8 else rng.choice([2, 2, 3])
    keys, saved, descs, checks = ["k2", "k1"], {}, [], []
    for i in range(n):
        J, k, sv, d, ch, (outer, inner) = one_simplify(rng, allow_special=(i == 0))
        saved.update(sv)
        keys += k
        descs.append(d)
        checks += ch
        if i < n - 1:
            keys += ["ENTER", "k1"]
    footer = rng.random()
    other = J <= 2 and footer < 0.2
    why = J <= 2 and 0.2 <= footer < 0.3
    keys += ["ENTER"] + (["k3", "ENTER", "k2"] if other else ["k4", "ENTER", "ENTER", "k2"] if why else ["k2"])
    if other:
        J2 = 3 - J
        checks.append((f"{NAMES[J2][0]}({NAMES[J2][1]}(X))", inner, outer))
    return dict(kind="simplify", keys=keys, saved=saved, desc=" ; ".join(descs), checks=checks, why=why)


def check_simplify(case, m):
    probs, info = [], {"inexact": 0}
    answers = [a for a in m.out if a[0] == "ANSWER:"]
    if len(answers) < len(case["checks"]):
        return [f"expected {len(case['checks'])} answer screen(s), got {len(answers)}: {m.out}"], info
    for (label, outer, inner), ans in zip(case["checks"], answers):
        lines = [l for l in ans[1:] if not l.startswith("FOOTER")]
        try:
            ivs = comp_domain(outer, inner)
        except Unsupported as ex:
            info["unsupported"] = str(ex)
            continue
        dl = [l for l in lines if l.startswith("D=")]
        if len(dl) != 1:
            probs.append(f"{label}: no single D= line: {lines}")
            continue
        if "NOT SUPPORTED" in dl[0]:
            probs.append(f"{label}: domain not supported: {dl[0]} (oracle {fmt_ivs(ivs)})")
            continue
        try:
            pd = parse_domain(dl[0])
        except ValueError as ex:
            probs.append(f"{label}: {ex}")
            continue
        ok, inexact = same_domain(ivs, pd)
        info["inexact"] += inexact
        if not ok:
            probs.append(f"{label}: domain {dl[0]} but oracle {fmt_ivs(ivs)}")
        elif is_reals_minus_points(ivs) and not dl[0].startswith("D=ALL REALS, X≠"):
            probs.append(f"{label}: style: {dl[0]} should be ALL REALS, X≠...")
        # formula
        formula_kinds = {"rat", "root"}
        fl = None
        for i, l in enumerate(lines):
            if l == label + "=" and i + 1 < len(lines):
                fl = lines[i + 1]
            elif l.startswith(label + "=") and len(l) > len(label) + 1:
                fl = l[len(label) + 1:]
        if outer.kind in formula_kinds and inner.kind in formula_kinds:
            if fl is None:
                if ivs:
                    probs.append(f"{label}: no formula line: {lines}")
                continue
            probs += [f"{label}: {p}" for p in formula_checks(fl, outer, inner, ivs)]
        elif fl is not None:
            probs.append(f"{label}: a formula for a graph/words composition: {fl}")
    if case["why"]:
        pages = [a for a in m.out if a[0].startswith("PAGE")]
        if not pages:
            probs.append("4:WHY showed no page")
    return probs, info


def fmt_ivs(ivs):
    if not ivs:
        return "{}"
    out = []
    for lo, hi, lc, rc in ivs:
        out.append(("[" if lc else "(") + str(lo) + "," + str(hi) + ("]" if rc else ")"))
    return "U".join(out)


def case_value_formula(rng):
    """menu 2 → 5:F(G(5)) FROM FORMULAS; sometimes more parts with 3:SAME F,G (only a function
    never typed before is asked)"""
    n = 1 if rng.random() < 0.7 else rng.choice([2, 3])
    keys, parts, known, desc = ["k2", "k5"], [], {}, ""
    for i in range(n):
        J = rng.choice([1, 2, 3, 4])
        x0 = Fr(rng.randint(-6, 6)) if rng.random() < 0.85 else \
            Fr(rng.choice([-5, -1, 1, 3, 7]), rng.choice([2, 3]))
        keys += [f"k{J}", "t:" + typed(rng, x0)]
        for name, need in (("F", J != 4), ("G", J != 3)):
            if need and name not in known:
                _, fn, fk, fd = rand_function(rng, (1, 2, 3, 4, 5, 5, 5, 6))
                known[name] = fn
                keys += fk
                desc += f"{name.lower()}={fd} "
        fm, gm = known.get("F"), known.get("G")
        outer, inner = {1: (fm, gm), 2: (gm, fm), 3: (fm, fm), 4: (gm, gm)}[J]
        parts.append((J, x0, outer, inner))
        desc += f"J={J} x={x0}; "
        keys += ["k3"] if i < n - 1 else ["k2"]
    return dict(kind="value", parts=parts, keys=keys, saved={}, desc=desc.strip())


def expected_value_lines(J, x0, outer, inner, typed_vals=None):
    """the three lines of a value answer, exact; -> (lines, exact?)"""
    on, inn = NAMES[J]
    xs = fr_text(x0)
    exact = True
    if typed_vals is not None:
        gv, fv = typed_vals
    else:
        gv = inner.value(S(x0))
        fv = outer.value(gv) if gv is not None else None
    lines = []
    if gv is None:
        lines.append(f"{on}({inn}({xs}))=UNDEFINED")
        lines.append(f"{inn}({xs}) DOES NOT EXIST")
        return lines, exact
    gt, e1 = ti_value_text(gv)
    lines.append(None)  # filled below
    lines.append(f"{inn}({xs})={gt}")
    if fv is None:
        lines[0] = f"{on}({inn}({xs}))=UNDEFINED"
        lines.append(f"{on}({gt}) DOES NOT EXIST")
    else:
        ft, e2 = ti_value_text(fv)
        exact = e1 and e2
        lines[0] = f"{on}({inn}({xs}))={ft}"
        lines.append(f"{on}({gt})={ft}")
    return lines, exact


def check_value(case, m):
    info = {"inexact": 0}
    answers = [a for a in m.out if a[0] == "ANSWER:"]
    parts = case.get("parts") or [(case["J"], case["x0"], case["outer"], case["inner"])]
    if len(answers) != len(parts):
        return [f"{len(answers)} answer screens for {len(parts)} parts: {m.out}"], info
    probs = []
    for (J, x0, outer, inner), ans in zip(parts, answers):
        got = [l for l in ans[1:] if not l.startswith("FOOTER")]
        want, exact = expected_value_lines(J, x0, outer, inner, case.get("typed_vals"))
        if not exact:
            info["inexact"] += 1
            if len(got) != len(want) or any(a != b and not close_decimal_line(a, b) for a, b in zip(got, want)):
                probs.append(f"value lines {got} want {want}")
        elif got != want:
            probs.append(f"value lines {got} want {want}")
    return probs, info


def close_decimal_line(a, b):
    na, nb = re.findall(r"-?\d+\.\d+|-?\d+(?:/\d+)?", a), re.findall(r"-?\d+\.\d+|-?\d+(?:/\d+)?", b)
    if re.sub(r"-?\d+\.\d+|-?\d+(?:/\d+)?", "#", a) != re.sub(r"-?\d+\.\d+|-?\d+(?:/\d+)?", "#", b):
        return False
    if len(na) != len(nb):
        return False
    for u, v in zip(na, nb):
        if abs(float(Fr(u) if "." not in u else float(u)) - float(Fr(v) if "." not in v else float(v))) > 2e-6:
            return False
    return True


def case_value_graph(rng):
    """menu 2 → 2:F(G(5)) FROM GRAPHS (saved / typed corners / read values)"""
    J = rng.choice([1, 2, 3, 4])
    fg, gg = rand_graph(rng), rand_graph(rng)
    outer, inner = {1: (fg, gg), 2: (gg, fg), 3: (fg, fg), 4: (gg, gg)}[J]
    lo, hi = inner.pts[0][0], inner.pts[-1][0]
    x0 = Fr(rng.choice([lo - 1, lo, hi, hi + 1] + [p[0] for p in inner.pts] + [rng.randint(lo, hi)] * 3))
    keys = ["k2", "k2", f"k{J}", "t:" + typed(rng, x0)]
    saved = {}
    src = rng.choice(["saved", "typed", "read"])
    case = dict(kind="value", J=J, x0=x0, saved=saved, outer=outer, inner=inner, src=src)
    if src == "saved":
        if J != 4:
            saved.update(graph_lists("F", fg))
        if J != 3:
            saved.update(graph_lists("G", gg))
        keys += ["k1"]
    elif src == "typed":
        if rng.random() < 0.4:
            # other graphs are already saved: typing must not ask about them
            saved.update(graph_lists("F", rand_graph(rng)))
            saved.update(graph_lists("G", rand_graph(rng)))
        keys += ["k2"]
        if J != 4:
            keys += graph_keys(rng, fg)
        if J != 3:
            keys += graph_keys(rng, gg)
    else:
        keys += ["k3"]
        gv = inner.value(S(x0))
        keys += ["t:" + (typed(rng, Fr(int(gv.p), int(gv.q))) if gv is not None else "")]
        fv = None
        if gv is not None:
            fv = outer.value(gv)
            keys += ["t:" + (typed(rng, Fr(int(fv.p), int(fv.q))) if fv is not None else "")]
        case["typed_vals"] = (gv, fv)
    keys += ["k2"]
    case["keys"] = keys
    case["desc"] = f"x={x0} f={fg.pts}{fg.lc}{fg.rc} g={gg.pts}{gg.lc}{gg.rc} src={src}"
    return case


def case_sqrt_graph(rng):
    """menu 2 → 3:DOMAIN OF √(GRAPH)"""
    B = rng.choice([1, 2])
    gr = rand_graph(rng)
    name = "FG"[B - 1]
    saved = {}
    if rng.random() < 0.5:
        saved.update(graph_lists(name, gr))
        other = rand_graph(rng)
        if rng.random() < 0.5:
            saved.update(graph_lists("GF"[B - 1], other))
        k = ["k2" if name == "F" else "k3"]
    else:
        k = graph_keys(rng, gr)
        if rng.random() < 0.3:
            saved.update(graph_lists("GF"[B - 1], rand_graph(rng)))
            k = ["k1"] + k
    keys = ["k2", "k3", f"k{B}"] + k + ["k2"]
    sq = Root(1, 1, 0, 0)
    return dict(kind="dom", keys=keys, saved=saved, outer=sq, inner=gr, desc=f"√ of {gr.pts}{gr.lc}{gr.rc}")


def case_graph_of_inside(rng):
    """menu 2 → 4:DOMAIN OF GRAPH(√(X)), inside √X or any shape"""
    A = rng.choice([1, 2])
    gr = rand_graph(rng)
    name = "FG"[A - 1]
    saved = {}
    if rng.random() < 0.5:
        saved.update(graph_lists(name, gr))
        k = ["k2" if name == "F" else "k3"]
    else:
        k = graph_keys(rng, gr)
    keys = ["k2", "k4", f"k{A}"] + k
    if rng.random() < 0.4:
        inner = Root(1, 1, 0, 0)
        keys += ["k1"]
        d = "√X"
    else:
        _, inner, ik, d = rand_function(rng)
        keys += ["k2"] + ik
    keys += ["k2"]
    return dict(kind="dom", keys=keys, saved=saved, outer=gr, inner=inner, desc=f"{gr.pts}{gr.lc}{gr.rc} of {d}")


def check_dom(case, m):
    info = {"inexact": 0}
    answers = [a for a in m.out if a[0] == "ANSWER:"]
    if not answers:
        return [f"no answer screen: {m.out}"], info
    lines = [l for l in answers[0][1:] if l.startswith("D=")]
    ivs = comp_domain(case["outer"], case["inner"])
    if len(lines) != 1:
        return [f"no single D= line {answers[0]}"], info
    if "NOT SUPPORTED" in lines[0]:
        return [f"not supported: {lines[0]} (oracle {fmt_ivs(ivs)})"], info
    ok, inexact = same_domain(ivs, parse_domain(lines[0]))
    info["inexact"] += inexact
    if not ok:
        return [f"domain {lines[0]} but oracle {fmt_ivs(ivs)}"], info
    return [], info


NAV_PREFIX = [
    ["k2", "CLEAR"],                       # composition menu → main menu
    ["k2", "k1", "CLEAR", "CLEAR"],        # order menu → composition menu → main menu
    ["k2", "k1", "k1", "CLEAR", "CLEAR"],  # f shape menu → composition menu → main menu
    ["k2", "k1", "k2", "k5", "t:", "t:", "t:", "t:", "CLEAR", "CLEAR"],  # g shape menu → back
    ["k2", "k2", "CLEAR", "CLEAR"],
    ["k2", "k2", "k3", "t:4", "CLEAR", "CLEAR"],   # values-from menu → back
    ["k2", "k3", "CLEAR", "CLEAR"],
    ["k2", "k4", "CLEAR", "CLEAR"],
    ["k2", "k5", "k1", "t:2", "CLEAR", "CLEAR"],   # f shape menu (values) → back
    ["k2", "k9", "k0", "ENTER", "CLEAR"],          # keys that are not choices do nothing
]


def case_nav(rng):
    """CLEAR goes back one menu at a time, stray keys do nothing; then a normal problem.
    Sometimes a bottom typed as 0 is refused and asked again."""
    pre = rng.choice(NAV_PREFIX)
    J = rng.choice([1, 2])
    _, fm, fk, fd = rand_function(rng, (1, 2, 4, 5))
    while True:
        a, b, c, d = coef(rng), coef(rng), coef(rng), coef(rng)
        if c != 0 or d != 0:
            break
    gm = Rat([a, b], [c, d])
    gk = ["k3", "t:" + typed(rng, a), "t:" + typed(rng, b), "t:0", "t:0", "t:" + typed(rng, c), "t:" + typed(rng, d)]
    outer, inner = (fm, gm) if J == 1 else (gm, fm)
    keys = pre + ["k2", "k1", f"k{J}"] + fk + gk + ["k2"]
    return dict(kind="simplify", keys=keys, saved={}, desc=f"nav {pre} f={fd} g=({a}x+{b})/({c}x+{d})",
                checks=[(f"{NAMES[J][0]}({NAMES[J][1]}(X))", outer, inner)], why=False)


KINDS = [(case_nav, check_simplify, 0.05), (case_simplify, check_simplify, 0.50), (case_value_formula, check_value, 0.15),
         (case_value_graph, check_value, 0.12), (case_sqrt_graph, check_dom, 0.08),
         (case_graph_of_inside, check_dom, 0.10)]


def one(rng):
    r, acc = rng.random(), 0
    for make, check, p in KINDS:
        acc += p
        if r < acc:
            return make, check
    return KINDS[0][0], KINDS[0][1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-n", type=int, default=500)
    ap.add_argument("-s", type=int, default=1)
    ap.add_argument("-v", action="store_true")
    ap.add_argument("--kind", default=None)
    args = ap.parse_args()
    rng = random.Random(args.s)
    stats = {"cases": 0, "mismatch": 0, "unsupported": 0, "inexact": 0, "sim_error": 0}
    by_kind = {}
    t0 = time.time()
    for i in range(args.n):
        make, check = one(rng)
        if args.kind and make.__name__ != args.kind:
            continue
        case = make(rng)
        m, res, err = run(case["keys"], case["saved"])
        stats["cases"] += 1
        bk = by_kind.setdefault(make.__name__, [0, 0])
        bk[0] += 1
        probs = []
        if err or res[0] != "stop":
            probs.append(f"simulator end={res} error={err}; last screen: "
                         + " | ".join(l for l in m.lines() if l.strip()))
            stats["sim_error"] += 1
        else:
            try:
                p, info = check(case, m)
                probs += p
                stats["inexact"] += info.get("inexact", 0)
                if "unsupported" in info:
                    stats["unsupported"] += 1
            except Unsupported as ex:
                stats["unsupported"] += 1
                if args.v:
                    print(f"  (oracle unsupported #{i}: {ex})")
        if m.problems:
            probs.append(f"screen problems: {m.problems[:3]}")
        if m.wrap_problems:
            probs.append(f"line breaking: {m.wrap_problems[:3]}")
        if probs:
            stats["mismatch"] += 1
            bk[1] += 1
            print(f"MISMATCH #{i} [{make.__name__}] {case['desc']}")
            print(f"   keys: {' '.join(case['keys'])}")
            for p in probs:
                print(f"   - {p}")
            for a in m.out[-3:]:
                print("   answer: " + " | ".join(a))
        elif args.v:
            print(f"ok #{i} [{make.__name__}] {case['desc']} -> "
                  + " / ".join(" | ".join(a) for a in m.out))
    print(f"\n{stats['cases']} cases in {time.time() - t0:.0f}s: {stats['mismatch']} mismatches, "
          f"{stats['sim_error']} simulator errors, {stats['unsupported']} oracle-unsupported, "
          f"{stats['inexact']} decimal (irrational) displays")
    print(f"   quadratic-irrational domain ends shown as decimals: {len(QUAD_DECIMALS)} {QUAD_DECIMALS[:5]}")
    for k, (n, bad) in by_kind.items():
        print(f"   {k}: {n} cases, {bad} mismatches")
    return 1 if stats["mismatch"] else 0


if __name__ == "__main__":
    sys.exit(main())
