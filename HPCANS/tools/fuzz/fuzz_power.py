#!/usr/bin/env python3
"""
Randomized differential testing of the power-function solver (main menu 6 "KX^P OR ROOTS",
program HAPOWER with its helpers HAPOWR2 (find k, p), HAPOWR3 (properties), HAPOWR4 (root form)).

Every case is a random session typed from the main menu exactly as a student presses keys:
  * 1:FIND K,P: all eight shapes (1 -3X^5, 2 -7ROOT(16X^3), 3 -1/(4X^6), 4 5/(2ROOT(9X)), 5 3X ROOT(X),
    6 2/(X ROOT(X)), 7 Y=7, 8 Y=2^X) with negative / fractional / zero numbers, ENTER defaults, a lone
    minus for -1 (either minus key), perfect and non-perfect powers under any root index 1-9
    (fractions under the root, negative numbers under odd and even roots), x powers that are
    negative, zero or fractions, root indexes typed wrong (0, 2.5, 100: asked again), infinity typed
    by mistake (the shape menu comes back), a rounded decimal power (0.6667), p = 0, k = 0, a
    zero bottom; then 3:ALL PROPS on the k, p it found (also 3:WHY there);
  * 2:SYMMETRY/QUADS and 3:ALL PROPERTIES: K and P typed as integers, fractions (reduced or not),
    decimals, ENTER (K = 1, P = 1), a lone minus (K = -1), irrational K (sqrt(2)), K = 0, P = 0,
    infinity (asked again); WHY pages;
  * 4:BUILD EQUATION: every quadrant choice x every shape choice, WHY pages.
  Sessions chain problems with 1:AGAIN, 2:HOME, CLEAR at every menu and footer, keys that do
  nothing (ignored), so state left by one problem is exercised by the next.

Oracle (independent of the TI code):
  * find: sympy builds the expression of the shape for x > 0 from the typed numbers
    (C*x^E*sign(D)*(|D|*x^G)^(1/F) etc.), p = x*y'/y (sympy), k = y(1) (sympy); the exact form of k
    (rational * integer radicand^(1/n), radicand free of n-th powers, n minimal) is computed from
    |k|^F (a rational) by prime factorisation and checked equal to sympy's k.  Degenerate inputs
    (zero bottom, k = 0, even root of a negative, p = 0) give the matching "not a power function"
    screen;
  * properties: f(x) = k*x^(a/b) evaluated numerically (mpmath, 60 digits) with the real b-th root
    for x < 0 when b is odd, nothing for x < 0 when b is even, f(0) only when p > 0.  Symmetry from
    f(-x) vs f(x); quadrants, range, boundedness from the signs of f on each side (each side's
    values cover (0, INF) in size: checked at x = 1E-1000 and 1E1000); increasing/decreasing from
    samples on each side; concavity from second differences at x = 1 and x = -1; asymptotes, end
    behaviour and the kind of discontinuity from f at 1E-1000 / 1E1000.  None of the class's
    parity rules are used;
  * root form X^(a/b)=(b-th root of X)^a: the printed form is parsed and evaluated at x = 2 and
    (b odd) x = -2;
  * build: the printed k*x^(a/b) is checked numerically to lie in exactly the chosen quadrants, to
    have the chosen Q1/Q4 shape (rising or falling, curving up or down, flat start / vertical
    tangent / asymptotes), and a non-integer, reduced power;
  * WHY pages: the lines are rebuilt from a, b, k and the choices.

Run from tools/:   python3 fuzz/fuzz_power.py [-n SESSIONS] [-s SEED] [--kind find,props,build] [-v]
"""

import argparse
import math
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
XP = sp.Symbol("x", positive=True)

FOOT_FIND = "1:AGAIN 2:HOME 3:ALL PROPS"
FOOT_3 = "1:AGAIN  2:HOME  3:WHY"
FOOT_2 = "1:AGAIN  2:HOME"


# ============================================================================ text formats
def ft(v):
    """exact text of a rational the way HAFRAC writes it (or its 6-place decimal fallback)"""
    v = Fr(v)
    if v.denominator == 1:
        return str(v.numerator)
    if v.denominator <= 9999 and v.denominator ** 2 * max(1, abs(v)) <= 10 ** 8:
        return f"{v.numerator}/{v.denominator}"
    return dec6(float(v))


def dec6(x):
    a = round(abs(x) * 10 ** 6)
    ip, fp = divmod(a, 10 ** 6)
    txt = str(ip) + ("." + f"{fp:06d}".rstrip("0") if fp else "")
    return ("-" if x < 0 else "") + txt


def ft_sym(v):
    """text of a sympy real: exact when rational, else the 6-place decimal"""
    v = sp.nsimplify(v) if not isinstance(v, sp.Basic) else v
    if v.is_Rational:
        return ft(Fr(int(v.p), int(v.q)))
    return dec6(float(v))


def coef_text(q):
    """coefficient in front of a radical or of X: 1 -> '', -1 -> '-', 5, (5/6), -(5/6)"""
    q = Fr(q)
    if q == 1:
        return ""
    if q == -1:
        return "-"
    if q.denominator == 1:
        return str(q.numerator)
    return ("-" if q < 0 else "") + f"({abs(q.numerator)}/{q.denominator})"


def rad_text(r, n):
    if n == 2:
        return f"√({r})"
    if n == 3:
        return f"³√({r})"
    return f"({r}^(1/{n}))"


def pexp_text(p):
    p = Fr(p)
    if p == 1:
        return ""
    if p.denominator == 1 and p > 1:
        return f"^{p.numerator}"
    return f"^({ft(p)})"


PAR = {0: "EVEN", 1: "ODD"}


# ============================================================================ the machine
class RecMachine(Machine):
    """records every line handed to HAOUT (whole, before wrapping), page starts and footers;
    presses ENTER for the student at an ENTER=MORE wait"""

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.out = []
        self.more = 0

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


# ============================================================================ typing
def typed(rng, v, default=None):
    """the text a student types for the rational v (default = the value ENTER gives)"""
    v = Fr(v)
    if default is not None and v == default and rng.random() < 0.6:
        return ""
    neg = v < 0
    a = abs(v)
    minus = rng.choice(["-", "⁻"])
    if neg and a == 1 and rng.random() < 0.4:
        return minus
    if a.denominator == 1:
        body = str(a.numerator)
    else:
        r = rng.random()
        if a.denominator in (2, 4, 5, 8, 10) and r < 0.2:
            body = str(float(a))
            if body.startswith("0.") and rng.random() < 0.5:
                body = body[1:]
        elif neg and r < 0.35:
            return f"{minus}({a.numerator}/{a.denominator})"
        else:
            body = f"{a.numerator}/{a.denominator}"
    return (minus + body) if neg else body


def rfrac(rng, zero=0.0, maxn=9):
    """a random rational: mostly small integers, some fractions, sign random"""
    r = rng.random()
    if r < zero:
        return Fr(0)
    r = rng.random()
    if r < 0.2:
        v = Fr(1)
    elif r < 0.65:
        v = Fr(rng.randint(1, maxn))
    else:
        v = Fr(rng.randint(1, maxn), rng.choice([2, 3, 4, 5, 6, 7, 8]))
        if v.denominator == 1:
            v = Fr(rng.randint(1, 7), 3)
    return v if rng.random() < 0.6 else -v


# ============================================================================ FIND K,P
SHAPE_VARS = {1: "CE", 2: "CFDG", 3: "HCE", 4: "HCFDG", 5: "CEFDG", 6: "HCEFDG", 7: "", 8: ""}
DEFAULTS = {"C": Fr(1), "E": Fr(1), "F": Fr(2), "D": Fr(1), "G": Fr(1), "H": Fr(1)}
BOTTOM = {3: "C", 4: "CD", 6: "CD"}          # numbers that sit in a denominator
TOP = {1: "C", 2: "CD", 3: "H", 4: "H", 5: "CD", 6: "H"}   # numbers that multiply the top


def gen_under(rng, f):
    """a number to put under an f-th root: perfect powers, non-perfect, fractions, negatives"""
    r = rng.random()
    if r < 0.3:
        base = Fr(rng.choice([1, 2, 3, 4, 5]), rng.choice([1, 1, 1, 2, 3]))
        v = base ** f if f <= 4 else base ** min(f, 3) * (2 if f > 3 else 1)
    elif r < 0.6:
        v = Fr(rng.choice([2, 3, 5, 6, 7, 8, 10, 12, 18, 20, 24, 27, 32, 40, 48, 50, 54, 72, 75, 96, 128, 200]))
    elif r < 0.8:
        v = Fr(rng.randint(1, 9), rng.randint(2, 9))
    elif r < 0.9:
        v = Fr(rng.choice([4, 9, 16, 25, 36, 49, 64, 81, 100, 8, 27, 125]))
    else:
        v = Fr(1)
    if rng.random() < (0.25 if f % 2 else 0.05):
        v = -v
    return v


def gen_find(rng, shape=None):
    """random inputs for FIND K,P: returns dict(shape, vals, texts (list of typed strings))"""
    shape = shape or rng.choice([1, 2, 3, 4, 5, 6, 1, 2, 4, 6, 7, 8])
    vals, texts = {}, []
    names = SHAPE_VARS[shape]
    if "F" in names:
        vals["F"] = Fr(rng.choice([2, 2, 2, 3, 3, 4, 5, 6, 1, 7, 9]))
    for nm in names:
        if nm == "F":
            continue
        if nm in "CH":
            v = rfrac(rng, zero=0.04)
        elif nm == "E":
            r = rng.random()
            v = Fr(rng.randint(1, 7)) if r < 0.6 else Fr(rng.randint(-4, -1)) if r < 0.75 else \
                Fr(rng.choice([1, 2, 3, 5]), rng.choice([2, 3, 4])) if r < 0.92 else Fr(0)
            if shape in (3, 6) and v == 0 and rng.random() < 0.5:
                v = Fr(2)
        elif nm == "G":
            r = rng.random()
            v = Fr(rng.randint(1, 7)) if r < 0.75 else Fr(rng.randint(-3, -1)) if r < 0.85 else \
                Fr(0) if r < 0.92 else Fr(rng.choice([1, 3]), 2)
        elif nm == "D":
            v = gen_under(rng, int(vals["F"])) if rng.random() > 0.03 else Fr(0)
        vals[nm] = v
    # the typed text, in prompt order
    acts = []
    bad_inf = rng.random() < 0.03 and names
    inf_at = rng.choice(names.replace("F", "") or "C") if bad_inf else None
    for nm in names:
        if nm == "F":
            if rng.random() < 0.08:
                acts.append(rng.choice(["0", "2.5", "100", "-3", "1/2"]))
            acts.append(typed(rng, vals["F"], DEFAULTS["F"]))
            continue
        if nm == inf_at:
            acts.append(rng.choice(["I", "-I"]))
            continue
        acts.append(typed(rng, vals[nm], DEFAULTS[nm]))
    deci = None
    if not bad_inf and shape in (1, 3) and rng.random() < 0.04:
        deci = rng.choice(["0.6667", ".3333", "1.4142"])  # a rounded decimal power
        acts[-1] = deci
    return dict(shape=shape, vals=vals, acts=acts, inf=bool(bad_inf), deci=deci)


def kform(k, f):
    """exact canonical form of the real number k whose f-th power |k|^f is rational:
    (q, r, n) with k = q * r^(1/n), r a positive integer free of n-th powers, n minimal."""
    t = sp.nsimplify(sp.Abs(k) ** f)
    if not t.is_Rational:
        t = sp.Rational(sp.nsimplify(sp.N(sp.Abs(k) ** f, 80), rational=True))
    u, v = int(t.p), int(t.q)
    r0 = u * v ** (f - 1)  # |k| = (u v^(f-1))^(1/f) / v
    out, rem = 1, {}
    for pr, e in sp.factorint(r0).items():
        out *= pr ** (e // f)
        if e % f:
            rem[pr] = e % f
    g = f
    for e in rem.values():
        g = math.gcd(g, e)
    n = f // g
    r = 1
    for pr, e in rem.items():
        r *= pr ** (e // g)
    sign = -1 if sp.N(k) < 0 else 1
    q = Fr(sign * out, v)
    if r == 1:
        n = 1
    return q, r, n


def find_oracle(p):
    """-> ('err', set of acceptable answer bodies) or ('ok', k (sympy), p (Fr), (q, r, n))"""
    sh, v = p["shape"], p["vals"]
    if sh == 7:
        return "err", {("NOT A POWER FUNCTION", "CONSTANT FUNCTION", "(IT IS KX^0: POWER 0)")}
    if sh == 8:
        return "err", {("NOT A POWER FUNCTION", "EXPONENTIAL FUNCTION", "(X IS IN THE EXPONENT)")}
    UNDEF = ("UNDEFINED: BOTTOM IS 0",)
    KZERO = ("NOT A POWER FUNCTION", "(K=0, SO Y=0)")
    EVENNEG = ("NOT A POWER FUNCTION", "(EVEN ROOT OF A NEGATIVE)")
    PZERO = ("NOT A POWER FUNCTION", "(P=0, SO Y=K: CONSTANT)")
    DECI = ("TYPE POWERS AS FRACTIONS,", "LIKE 2/3, NOT 0.667")
    bad = set()
    if any(v.get(nm, 1) == 0 for nm in BOTTOM.get(sh, "")):
        bad.add(UNDEF)
    if "F" in v and v["D"] < 0 and v["F"] % 2 == 0:
        bad.add(EVENNEG)
    if any(v.get(nm, 1) == 0 for nm in TOP[sh]) and UNDEF not in bad:
        bad.add(KZERO)
    if p["deci"]:
        bad.add(DECI)
    if bad:
        return "err", bad
    S = {nm: sp.Rational(val.numerator, val.denominator) for nm, val in v.items()}
    x = XP
    rad = 1
    if "F" in S:
        Fv, Dv, Gv = S["F"], S["D"], S["G"]
        rad = sp.sign(Dv) * (sp.Abs(Dv) * x ** Gv) ** (1 / Fv)
    C, E, H = S.get("C", 1), S.get("E", 0), S.get("H", 1)
    expr = {1: C * x ** E, 2: C * rad, 3: H / (C * x ** E), 4: H / (C * rad), 5: C * x ** E * rad,
            6: H / (C * x ** E * rad)}[sh]
    pp = sp.simplify(x * sp.diff(expr, x) / expr)
    kk = sp.simplify(expr.subs(x, 1))
    assert pp.is_Rational, (p, pp)
    if pp == 0:
        return "err", {PZERO}
    f = int(S["F"]) if "F" in S else 1
    q, r, n = kform(kk, f)
    chk = sp.Rational(q.numerator, q.denominator) * sp.Integer(r) ** sp.Rational(1, n)
    assert abs(sp.N(chk - kk, 50)) < 1e-40, (p, kk, chk)
    return "ok", kk, Fr(int(pp.p), int(pp.q)), (q, r, n), p


def find_expect(o):
    """the answer lines for an 'ok' FIND oracle result and the K text"""
    _, kk, pp, (q, r, n), _ = o
    if r == 1:
        ktxt = ft(q)
        ycoef = coef_text(q)
    else:
        ktxt = coef_text(q) + rad_text(r, n)
        ycoef = ktxt
    return ["Y=" + ycoef + "X" + pexp_text(pp), "K=" + ktxt, "P=" + ft(pp), "YES, A POWER FUNCTION"], ktxt


def fallback_ok(o):
    p = o[4]
    v = p["vals"]
    if "F" not in v:
        return False
    f = int(v["F"])
    u, w = abs(v["D"]).numerator, abs(v["D"]).denominator
    g = w * u ** (f - 1) if p["shape"] in (4, 6) else u * w ** (f - 1)
    return g >= 10 ** 11 or g ** (1 / f) > 900


def check_find(o, body):
    want, ktxt = find_expect(o)
    if body == want:
        return []
    _, kk, pp, (q, r, n), _ = o
    # the documented decimal fallback when the radicand work would be too big for the TI
    # (14 digits) or too slow: the radicand before taking out n-th powers is u*v^(F-1) for
    # sqrt[F](u/v) on top, v*u^(F-1) for it in the bottom
    if fallback_ok(o) and len(body) == 4 and body[1].startswith("K="):
        try:
            got = float(body[1][2:])
            if abs(got - float(kk)) < 1e-5 * max(1, abs(float(kk))) and body[2:] == want[2:]:
                return []
        except ValueError:
            pass
    return [f"got {body} want {want}"]


# ============================================================================ properties (numeric oracle)
def fval(k, a, b, x):
    """real value of k*x^(a/b) (None where undefined); k an mpf"""
    x = mp.mpf(x)
    if x > 0:
        return k * x ** (mp.mpf(a) / b)
    if x == 0:
        return mp.mpf(0) if a > 0 else None
    if b % 2 == 0:
        return None
    root = -((-x) ** (mp.mpf(1) / b))   # the real b-th root of a negative number
    return k * root ** a


def sgn(v):
    return 1 if v > 0 else -1 if v < 0 else 0


def mono(k, a, b, side):
    xs = [mp.mpf(t) for t in ("0.001", "0.1", "0.5", "1", "2", "10", "1000")]
    if side < 0:
        xs = [-t for t in reversed(xs)]
    ys = [fval(k, a, b, t) for t in xs]
    d = [sgn(y2 - y1) for y1, y2 in zip(ys, ys[1:])]
    assert len(set(d)) == 1 and d[0] != 0, (k, a, b, side, d)
    return d[0]


def conc(k, a, b, x0):
    h = mp.mpf("1e-12")
    v = (fval(k, a, b, x0 + h) + fval(k, a, b, x0 - h) - 2 * fval(k, a, b, x0)) / h ** 2
    if abs(v) < mp.mpf("1e-15"):
        return 0
    return sgn(v)


def limit_text(v):
    if abs(v) < mp.mpf("1e-3"):
        return "0"
    return "INF" if v > 0 else "-INF"


def props_lines(k, a, b, ktxt, mode):
    """expected answer lines for K = k (sympy), P = a/b (reduced), mode 2 or 3; root-form line(s)
    are represented by the marker '<ROOT>' (checked separately)"""
    kf = mp.mpf(str(sp.N(k, 70)))
    neg = fval(kf, a, b, -1) is not None
    zero = fval(kf, a, b, 0) is not None
    s_pos = sgn(fval(kf, a, b, 1))
    s_neg = sgn(fval(kf, a, b, -1)) if neg else 0
    # every side's values cover (0, INF) in size
    for side in ([1, -1] if neg else [1]):
        lo, hi = fval(kf, a, b, side * mp.mpf("1e-1000")), fval(kf, a, b, side * mp.mpf("1e1000"))
        mags = sorted([abs(lo), abs(hi)])
        assert mags[0] < 1e-3 and mags[1] > 1e3
    L = [f"P={ft(Fr(a, b))}  ({PAR[a % 2]}/{PAR[b % 2]})"]
    if mode == 3 and b > 1:
        L.append("<ROOT>")
    if not neg:
        L.append("UNDEFINED FOR X<0")
    else:
        t1, t2 = mp.mpf("2"), mp.mpf("0.7")
        if all(abs(fval(kf, a, b, -t) - fval(kf, a, b, t)) < 1e-40 for t in (t1, t2)):
            L.append("SYMMETRY: EVEN (Y-AXIS)")
        elif all(abs(fval(kf, a, b, -t) + fval(kf, a, b, t)) < 1e-40 for t in (t1, t2)):
            L.append("SYMMETRY: ODD (ORIGIN)")
        else:
            raise AssertionError("neither even nor odd")
    if mode == 3 and not neg:
        L.append("(NOT EVEN, NOT ODD)")
    quads = []
    if s_pos > 0:
        quads.append("I")
    if s_neg > 0:
        quads.append("II")
    if s_neg < 0:
        quads.append("III")
    if s_pos < 0:
        quads.append("IV")
    L.append(f"QUADRANT: {quads[0]} ONLY" if len(quads) == 1 else "QUADRANTS: " + ",".join(quads))
    if mode == 3:
        L.append("DOMAIN: " + ("(-INF,INF)" if neg and zero else "(-INF,0)U(0,INF)" if neg else
                               "[0,INF)" if zero else "(0,INF)"))
        sides = {s_pos} | ({s_neg} if neg else set())
        if sides == {1, -1}:
            rng_t = "(-INF,INF)" if zero else "(-INF,0)U(0,INF)"
        elif sides == {1}:
            rng_t = "[0,INF)" if zero else "(0,INF)"
        else:
            rng_t = "(-INF,0]" if zero else "(-INF,0)"
        L.append("RANGE: " + rng_t)
        m_pos = mono(kf, a, b, 1)
        m_neg = mono(kf, a, b, -1) if neg else 0
        ipos = "[0,INF)" if zero else "(0,INF)"
        ineg = "(-INF,0]" if zero else "(-INF,0)"
        for want, word in ((1, "INCREASING"), (-1, "DECREASING")):
            parts = ([ineg] if m_neg == want else []) + ([ipos] if m_pos == want else [])
            if len(parts) == 2 and zero:
                parts = ["(-INF,INF)"]
            L.append(f"{word}: " + (parts[0] if parts else "NEVER"))
            if len(parts) == 2:
                L.append("AND ON " + parts[1])
        if sides == {1, -1}:
            L.append("NOT BOUNDED ABOVE OR BELOW")
        else:
            L.append("BOUNDED BELOW" if sides == {1} else "BOUNDED ABOVE")
        vert = abs(fval(kf, a, b, mp.mpf("1e-1000"))) > 1e3
        horiz = abs(fval(kf, a, b, mp.mpf("1e1000"))) < 1e-3
        assert vert == horiz
        L.append("ASYMPTOTES: X=0, Y=0" if vert else "ASYMPTOTES: NONE")
        right = limit_text(fval(kf, a, b, mp.mpf("1e1000")))
        if not neg:
            L += [f"AS X->INF, F(X)->{right}", "NO LEFT END BEHAVIOR"]
        else:
            left = limit_text(fval(kf, a, b, -mp.mpf("1e1000")))
            if left == right:
                L.append(f"AS X->+-INF, F(X)->{right}")
            else:
                L += [f"AS X->INF, F(X)->{right}", f"AS X->-INF, F(X)->{left}"]
        if not zero:
            assert abs(fval(kf, a, b, mp.mpf("1e-1000"))) > 1e3
            L += ["DISCONTINUOUS AT X=0", "(INFINITE DISCONTINUITY)"]
        elif not neg:
            L.append("CONTINUOUS ON [0,INF)")
        else:
            L.append("CONTINUOUS EVERYWHERE")
    CONC = {1: "CURVING UP, CONCAVE UP", -1: "CURVING DOWN, CONCAVE DOWN", 0: "STRAIGHT LINE"}
    L.append(("Q1: " if s_pos > 0 else "Q4: ") + ("INCREASING" if mono(kf, a, b, 1) > 0 else "DECREASING"))
    L.append(CONC[conc(kf, a, b, mp.mpf(1))])
    if mode == 3 and neg:
        L.append(("Q2: " if s_neg > 0 else "Q3: ") + ("INCREASING" if mono(kf, a, b, -1) > 0 else "DECREASING"))
        L.append(CONC[conc(kf, a, b, mp.mpf(-1))])
    if mode == 2 and a < 0:
        L.append("ASYMPTOTES: X=0, Y=0")
    if zero:
        L.append("<THROUGH0>")
    else:
        L.append(f"THROUGH (1,{ktxt})")
    return L


ROOT_RE = re.compile(r"(1/)?(\()?(√\(X\)|³√\(X\)|\((\d+)TH ROOT X\))(\))?(²|³|\^(\d+))?")


def root_value(txt, x):
    m = ROOT_RE.fullmatch(txt)
    if not m:
        return None
    inv, op, base, nth, cp, ex, exn = m.groups()
    if bool(op) != bool(cp):
        return None
    n = 2 if base == "√(X)" else 3 if base == "³√(X)" else int(nth)
    e = 1 if not ex else 2 if ex == "²" else 3 if ex == "³" else int(exn)
    if e > 1 and n <= 3 and not op:
        return None   # (√(X))² needs its brackets
    x = mp.mpf(x)
    if x < 0 and n % 2 == 0:
        return None
    r = x ** (mp.mpf(1) / n) if x > 0 else -((-x) ** (mp.mpf(1) / n))
    v = r ** e
    return 1 / v if inv else v


def check_root(lines, a, b):
    """lines = the root-form line(s): ['X^(a/b)=FORM'] or ['X^(a/b)=', 'FORM']"""
    head = f"X^({ft(Fr(a, b))})="
    if len(lines) == 1 and lines[0].startswith(head):
        form = lines[0][len(head):]
    elif len(lines) == 2 and lines[0] == head:
        form = lines[1]
        if len(head) + len(form) <= 26:
            return [f"root form split although it fits: {lines}"]
    else:
        return [f"root form lines {lines}"]
    for x in ([2, mp.mpf("0.3")] + ([-2] if b % 2 else [])):
        got = root_value(form, x)
        want = fval(mp.mpf(1), a, b, x)
        if got is None or abs(got - want) > 1e-30:
            return [f"root form {form!r} wrong at x={x}"]
    return []


def check_props(k, a, b, ktxt, mode, body):
    want = props_lines(k, a, b, ktxt, mode)
    errs = []
    got = list(body)
    # root form
    if "<ROOT>" in want:
        i = want.index("<ROOT>")
        head = f"X^({ft(Fr(a, b))})="
        nroot = 2 if i < len(got) and got[i] == head else 1
        errs += check_root(got[i:i + nroot], a, b)
        got = got[:i] + ["<ROOT>"] + got[i + nroot:]
    if want and want[-1] == "<THROUGH0>":
        one = f"THROUGH (0,0) AND (1,{ktxt})"
        if got[-1:] == [one] and len(one) <= 26:
            got = got[:-1] + ["<THROUGH0>"]
        elif got[-2:] == ["THROUGH (0,0)", f"AND (1,{ktxt})"]:
            got = got[:-2] + ["<THROUGH0>"]
    if got != want:
        errs.append(f"props got {body} want {want}")
    return errs


def why_props_lines(k, a, b):
    kf = float(sp.N(k))
    L = [f"A={a} {PAR[a % 2]}, B={b} {PAR[b % 2]}"]
    L.append("B EVEN: NO GRAPH FOR X<0" if b % 2 == 0 else "A EVEN: EVEN SYMMETRY" if a % 2 == 0 else
             "BOTH ODD: ODD SYMMETRY")
    if b > 1:
        L.append("<ROOT>")
    if kf < 0:
        L.append("K<0: FLIP OVER X-AXIS")
    p = Fr(a, b)
    L.append("P<0: ASYMPTOTES X=0, Y=0" if p < 0 else "P>1: X^P CURVES UP" if p > 1 else
             "0<P<1: X^P CURVES DOWN" if p < 1 else "P=1: STRAIGHT LINE")
    return L


def check_why_props(k, a, b, body):
    want = why_props_lines(k, a, b)
    errs, got = [], list(body)
    if "<ROOT>" in want:
        i = want.index("<ROOT>")
        head = f"X^({ft(Fr(a, b))})="
        nroot = 2 if i < len(got) and got[i] == head else 1
        errs += check_root(got[i:i + nroot], a, b)
        got = got[:i] + ["<ROOT>"] + got[i + nroot:]
    if got != want:
        errs.append(f"why got {body} want {want}")
    return errs


def gen_props(rng):
    """random K and P for 2:SYMMETRY/QUADS or 3:ALL PROPERTIES"""
    acts = []
    r = rng.random()
    special = None
    if r < 0.06:
        kv, ktyped = sp.sqrt(2), rng.choice(["√(2)"])
    elif r < 0.09:
        kv, ktyped = -sp.sqrt(3), rng.choice(["-√(3)", "⁻√(3)"])
    else:
        kf = rfrac(rng, zero=0.03, maxn=12)
        if rng.random() < 0.05:
            kf = Fr(17, 10)
        kv, ktyped = sp.Rational(kf.numerator, kf.denominator), typed(rng, kf, Fr(1))
        if kf.denominator in (2, 5, 10) and rng.random() < 0.2:
            ktyped = (("-" if kf < 0 else "") + str(float(abs(kf))))
    r = rng.random()
    if r < 0.04:
        pa, pb, ptyped = 0, 1, rng.choice(["0", "0/3"])
    elif r < 0.07:
        pa, pb, ptyped = None, None, rng.choice(["0.6667", "-.3333", "0.1428"])
    elif r < 0.12:
        pa, pb, ptyped = 1, 1, rng.choice(["", "1"])
    else:
        pb = rng.choice([1, 2, 3, 3, 4, 5, 5, 6, 7, 8, 9, 11, 12])
        pa = rng.choice([x for x in range(-15, 16) if x != 0])
        g = math.gcd(pa, pb)
        pa, pb = pa // g, pb // g
        m = rng.choice([1, 1, 1, 1, 2, 3])
        num, den = pa * m, pb * m
        minus = rng.choice(["-", "⁻"])
        if den == 1 and rng.random() < 0.7:
            ptyped = (minus if num < 0 else "") + str(abs(num))
        elif m == 1 and pb in (2, 4, 5, 8) and rng.random() < 0.25:
            ptyped = (minus if pa < 0 else "") + str(abs(pa) / pb)
        else:
            ptyped = (minus if num < 0 else "") + f"{abs(num)}/{den}"
    if rng.random() < 0.03:
        acts += rng.choice([["I", ptyped], [ktyped, "-I"]])   # infinity typed: K and P asked again
        special = "inf"
    acts += [ktyped, ptyped]
    return dict(k=kv, a=pa, b=pb, acts=acts, special=special)


def props_oracle(p, mode):
    """-> ('err', body) or ('ok', expected body via check function)"""
    if p["k"] == 0:
        return "err", ["NOT A POWER FUNCTION", "(K=0, SO Y=0)"]
    if p["a"] is None:
        return "err", ["TYPE POWERS AS FRACTIONS,", "LIKE 2/3, NOT 0.667"]
    if p["a"] == 0:
        return "err", ["NOT A POWER FUNCTION", "(P=0, SO Y=K: CONSTANT)"]
    return "ok", None


# ============================================================================ BUILD
QUADSETS = {1: {"I"}, 2: {"IV"}, 3: {"I", "II"}, 4: {"III", "IV"}, 5: {"I", "III"}, 6: {"II", "IV"}}


def check_build(quad, shape, body):
    if len(body) != 2:
        return [f"build body {body}"]
    m = re.fullmatch(r"Y=(-?)X\^\((-?\d+)/(\d+)\)", body[0])
    if not m:
        return [f"build equation {body[0]!r} not Y=±X^(a/b) with a non-integer power"]
    k = -1 if m.group(1) else 1
    a, b = int(m.group(2)), int(m.group(3))
    errs = []
    if math.gcd(abs(a), b) != 1 or b < 2:
        errs.append(f"power {a}/{b} not reduced / integer")
    if body[1] != f"K={k}, P={a}/{b}":
        errs.append(f"second line {body[1]!r}")
    kf = mp.mpf(k)
    neg = fval(kf, a, b, -1) is not None
    quads = set()
    s_pos = sgn(fval(kf, a, b, 1))
    quads.add("I" if s_pos > 0 else "IV")
    if neg:
        quads.add("II" if fval(kf, a, b, -1) > 0 else "III")
    if quads != QUADSETS[quad]:
        errs.append(f"{body[0]} lies in {sorted(quads)} not {sorted(QUADSETS[quad])}")
    mo = mono(kf, a, b, 1)
    cc = conc(kf, a, b, mp.mpf(1))
    near0 = fval(kf, a, b, mp.mpf("1e-1000"))
    slope0 = None if near0 is None else abs(near0) / mp.mpf("1e-1000")
    far = abs(fval(kf, a, b, mp.mpf("1e1000")))
    up = s_pos > 0
    if shape == 1:   # rising (Q1) / falling (Q4), levelling off, sharp point / vertical tangent at 0
        ok = (mo == (1 if up else -1)) and cc == (-1 if up else 1) and slope0 is not None and slope0 > 1e3 \
            and far > 1e3
    elif shape == 2:  # gets steeper, flat start at 0
        ok = (mo == (1 if up else -1)) and cc == (1 if up else -1) and slope0 is not None and slope0 < 1e-3
    else:             # toward the x-axis, asymptotes x = 0 and y = 0
        ok = (mo == (-1 if up else 1)) and fval(kf, a, b, 0) is None and far < 1e-3 and \
            near0 is not None and abs(near0) > 1e3
    if not ok:
        errs.append(f"{body[0]} does not have Q1/Q4 shape {shape} (quad {quad})")
    return errs


BUILD_QRULE = {1: "I ONLY: B EVEN", 2: "IV ONLY: B EVEN", 3: "I AND II: A EVEN, B ODD",
               4: "III AND IV: A EVEN, B ODD", 5: "I AND III: A, B BOTH ODD", 6: "II AND IV: A, B BOTH ODD"}


def check_build_why(quad, shape, eq, body):
    m = re.fullmatch(r"Y=(-?)X\^\((-?\d+)/(\d+)\)", eq)
    if not m:
        return ["no equation"]
    k = -1 if m.group(1) else 1
    a, b = int(m.group(2)), int(m.group(3))
    p = Fr(a, b)
    want = [BUILD_QRULE[quad], "K>0: NOT FLIPPED" if k > 0 else "K<0: FLIPPED OVER X-AXIS",
            {1: "LEVELS OFF: 0<P<1", 2: "GETS STEEPER: P>1", 3: "ASYMPTOTES: P<0"}[shape]]
    errs = []
    if body != want:
        errs.append(f"build why got {body} want {want}")
    # the rules quoted must hold for the equation shown
    par_ok = {1: b % 2 == 0, 2: b % 2 == 0, 3: a % 2 == 0 and b % 2 == 1, 4: a % 2 == 0 and b % 2 == 1,
              5: a % 2 == 1 and b % 2 == 1, 6: a % 2 == 1 and b % 2 == 1}[quad]
    size_ok = {1: 0 < p < 1, 2: p > 1, 3: p < 0}[shape]
    if not (par_ok and size_ok):
        errs.append(f"why rules do not fit {eq}")
    return errs


# ============================================================================ sessions
class Prob:
    def __init__(self, kind, desc, check, footer):
        self.kind, self.desc, self.check, self.footer = kind, desc, check, footer


def make_session(rng, kinds):
    """returns (actions, list of expected screens: (Prob, check function on the body))"""
    acts = []
    screens = []   # list of (kind, desc, footer, checker)
    where = "MAIN"
    nprob = rng.randint(1, 5)
    done = 0
    mode = None
    while done < nprob:
        if where == "MAIN":
            if rng.random() < 0.04:
                acts.append(rng.choice(["k8", "k9", "k0"]))   # nothing happens
            acts.append("k6")
            where = "SUB"
            continue
        if where == "SUB":
            if rng.random() < 0.05:
                acts.append("CLEAR")
                where = "MAIN"
                continue
            if rng.random() < 0.04:
                acts.append(rng.choice(["k5", "k9", "k0"]))
            choices = []
            if "find" in kinds:
                choices += [1, 1]
            if "props" in kinds:
                choices += [2, 3, 3]
            if "build" in kinds:
                choices += [4]
            mode = rng.choice(choices)
            acts.append(f"k{mode}")
            where = {1: "SHAPE", 2: "KP", 3: "KP", 4: "QUAD"}[mode]
            continue
        if where == "SHAPE":
            if rng.random() < 0.04:
                acts.append("CLEAR")
                where = "SUB"
                continue
            if rng.random() < 0.03:
                acts.append("k9")
            p = gen_find(rng)
            acts.append(f"k{p['shape']}")
            acts += [f"t:{t}" for t in p["acts"]]
            if p["inf"]:
                where = "SHAPE"   # the shape menu comes back
                continue
            o = find_oracle(p)
            desc = f"find shape {p['shape']} {dict((k, str(v)) for k, v in p['vals'].items())} typed {p['acts']}"
            done += 1
            if o[0] == "err":
                screens.append(("find-err", desc, FOOT_2, lambda body, o=o: [] if tuple(body) in o[1] else
                                [f"got {body} want one of {sorted(o[1])}"]))
                nxt = rng.random()
                if nxt < 0.55:
                    acts.append("k1")
                    where = "SHAPE"
                else:
                    acts.append(rng.choice(["k2", "CLEAR"]))
                    where = "MAIN"
                continue
            screens.append(("find", desc, FOOT_FIND, lambda body, o=o: check_find(o, body)))
            nxt = rng.random()
            if nxt < 0.4:
                acts.append("k1")
                where = "SHAPE"
            elif nxt < 0.7:
                # 3:ALL PROPS on the k, p found
                acts.append("k3")
                _, kk, pp, _, _ = o
                _, ktxt = find_expect(o)
                a, b = pp.numerator, pp.denominator
                screens.append(("find-props", desc, FOOT_3,
                                lambda body, kk=kk, a=a, b=b, ktxt=ktxt: check_props(kk, a, b, ktxt, 3, body)))
                r2 = rng.random()
                if r2 < 0.3:
                    acts.append("k3")
                    screens.append(("find-why", desc, FOOT_2,
                                    lambda body, kk=kk, a=a, b=b: check_why_props(kk, a, b, body)))
                    if rng.random() < 0.5:
                        acts.append("k1")
                        where = "SHAPE"
                    else:
                        acts.append(rng.choice(["k2", "CLEAR"]))
                        where = "MAIN"
                elif r2 < 0.65:
                    acts.append("k1")
                    where = "SHAPE"
                else:
                    acts.append(rng.choice(["k2", "CLEAR"]))
                    where = "MAIN"
            else:
                acts.append(rng.choice(["k2", "CLEAR"]))
                where = "MAIN"
            continue
        if where == "KP":
            p = gen_props(rng)
            acts += [f"t:{t}" for t in p["acts"]]
            o = props_oracle(p, mode)
            desc = f"props mode {mode} k={p['k']} p={p['a']}/{p['b']} typed {p['acts']}"
            done += 1
            if o[0] == "err":
                screens.append(("props-err", desc, FOOT_2, lambda body, o=o: [] if body == o[1] else
                                [f"got {body} want {o[1]}"]))
                if rng.random() < 0.5:
                    acts.append("k1")
                    where = "KP"
                else:
                    acts.append(rng.choice(["k2", "CLEAR"]))
                    where = "MAIN"
                continue
            k, a, b = p["k"], p["a"], p["b"]
            ktxt = ft_sym(k)
            screens.append(("props", desc, FOOT_3,
                            lambda body, k=k, a=a, b=b, ktxt=ktxt, md=mode: check_props(k, a, b, ktxt, md, body)))
            r2 = rng.random()
            if r2 < 0.25:
                acts.append("k3")
                screens.append(("props-why", desc, FOOT_2, lambda body, k=k, a=a, b=b: check_why_props(k, a, b, body)))
                if rng.random() < 0.5:
                    acts.append("k1")
                    where = "KP"
                else:
                    acts.append(rng.choice(["k2", "CLEAR"]))
                    where = "MAIN"
            elif r2 < 0.7:
                acts.append("k1")
                where = "KP"
            else:
                acts.append(rng.choice(["k2", "CLEAR"]))
                where = "MAIN"
            continue
        if where == "QUAD":
            if rng.random() < 0.04:
                acts.append("CLEAR")
                where = "SUB"
                continue
            quad = rng.randint(1, 6)
            acts.append(f"k{quad}")
            if rng.random() < 0.05:
                acts.append("CLEAR")   # back to the quadrant menu
                continue
            if rng.random() < 0.03:
                acts.append("k7")
            shape = rng.randint(1, 3)
            acts.append(f"k{shape}")
            desc = f"build quad {quad} shape {shape}"
            done += 1
            holder = {}

            def chk(body, quad=quad, shape=shape, holder=holder):
                holder["eq"] = body[0] if body else ""
                return check_build(quad, shape, body)
            screens.append(("build", desc, FOOT_3, chk))
            r2 = rng.random()
            if r2 < 0.3:
                acts.append("k3")
                screens.append(("build-why", desc, FOOT_2,
                                lambda body, quad=quad, shape=shape, holder=holder:
                                check_build_why(quad, shape, holder.get("eq", ""), body)))
                if rng.random() < 0.5:
                    acts.append("k1")
                    where = "QUAD"
                else:
                    acts.append(rng.choice(["k2", "CLEAR"]))
                    where = "MAIN"
            elif r2 < 0.7:
                acts.append("k1")
                where = "QUAD"
            else:
                acts.append(rng.choice(["k2", "CLEAR"]))
                where = "MAIN"
            continue
    if where == "KP":
        # 1:AGAIN left the student at the K= prompt (CLEAR cannot leave an Input): press 2:HOME instead
        assert acts[-1] == "k1"
        acts[-1] = "k2"
    return acts, screens


def run_case(rng, kinds):
    acts, want = make_session(rng, kinds)
    m, res, err = run(acts)
    errs = []
    if err:
        errs.append(f"TI error: {err}")
    elif res[0] != "stop":
        errs.append(f"did not stop cleanly: {res} last screen {[l for l in m.lines() if l.strip()]}")
    if m.problems:
        errs.append(f"screen problems: {m.problems[:3]}")
    screens = [x for x in m.out if x and x[0] in ("ANSWER:", "PAGE WHY:")]
    if not errs and len(screens) != len(want):
        errs.append(f"{len(screens)} answer screens, expected {len(want)}")
    if not err:
        for (kind, desc, foot, chk), s in zip(want, screens):
            body = [l for l in s[1:] if not l.startswith("FOOTER ")]
            footer = [l[7:] for l in s if l.startswith("FOOTER ")]
            if footer != [foot]:
                errs.append(f"[{kind}] {desc}: footer {footer} != {foot}")
            if kind.endswith("why") != (s[0] == "PAGE WHY:"):
                errs.append(f"[{kind}] {desc}: page kind {s[0]}")
            try:
                e = chk(body)
            except AssertionError as ex:   # oracle refused
                e = [f"oracle assertion {ex}"]
            errs += [f"[{kind}] {desc}: {x}" for x in e]
    return errs, acts, want, m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-n", type=int, default=400)
    ap.add_argument("-s", type=int, default=1)
    ap.add_argument("--kind", default="find,props,build")
    ap.add_argument("-v", action="store_true")
    args = ap.parse_args()
    rng = random.Random(args.s)
    kinds = args.kind.split(",")
    stats = {}
    bad = 0
    shown = 0
    t0 = time.time()
    for i in range(args.n):
        errs, acts, want, m = run_case(rng, kinds)
        for w in want:
            stats[w[0]] = stats.get(w[0], 0) + 1
        if errs:
            bad += 1
            if shown < 20:
                shown += 1
                print(f"--- session {i}: {[w[0] for w in want]}")
                for e in errs[:5]:
                    print("   ", e)
                if args.v:
                    print("    actions:", acts)
    total = sum(stats.values())
    print(f"{args.n} sessions, {total} answer screens {dict(sorted(stats.items()))}; "
          f"{bad} sessions with mismatches; {time.time() - t0:.1f}s")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
