#!/usr/bin/env python3
"""
Randomized differential testing of the absolute-value solver (main menu 5: HAABS, HAABS2..HAABS6).

Every case is a session typed from the main menu exactly as a student would press keys:
  * shapes 1:A|F(BX+C)+D|+K  2:A*F(B|X|+C)+K  3:A*F(|BX+C|)+K with negative / fractional / zero
    coefficients, ENTER defaults (A, B -> 1; C, D, K -> 0), a lone minus for -1 (either minus key),
    "-(1/2)", decimals, a "+" copied in front of C/D/K, an "X" copied after B, A = 0 or B = 0 typed
    first (refused, asked again);
  * 1:SKETCH/GRAPH: random corner-point graphs (1-7 points, zeros, flat pieces, hollow end dots,
    all on one side of x = 0 or straddling it), typed or the saved graph;
  * 2:DOMAIN ONLY / 3:RANGE ONLY / 4:D AND R: random intervals with any brackets, infinite ends,
    ends typed in the wrong order, one-point intervals, D_f partly / fully / not reachable;
  * 5:ORDER OF THE STEPS and the 3:WHY page after every other answer.
  Sessions chain problems with AGAIN / HOME, dead keys and CLEAR at the menus.

Oracle (independent of the TI code; Python Fractions, infinity = float('inf')):
  * the transformed function g is built exactly: g(x) = A|f(Bx+C)+D|+K, A f(B|x|+C)+K or
    A f(|Bx+C|)+K, with f the piecewise-linear graph through the corners (closed segments, the
    end dots decide whether the ends belong to f);
  * the domain of g is found by testing membership (u(x) in D_f) at every candidate x (where the
    inside u(x) hits an end of D_f, and the kink of u) and at a sample inside every gap between
    candidates, then merging the pieces;
  * breakpoints of g: x where u(x) is a corner x of f, the kink of u, and (shape 1) where
    f(u)+D changes sign; between breakpoints g is linear, so its corners are the piece ends plus
    every breakpoint where the slopes on the two sides differ; the graph is also sampled densely
    (64 points per stretch) to confirm g is linear between the reported corners;
  * the range is the union of the images of the open stretches between breakpoints (open
    intervals, or one value when flat) and of every breakpoint that is in the domain;
  * D and R only: the domain is the same membership construction with D_f typed as an interval;
    the range of shape 1 is the image of R_f under y -> A|y+D|+K (same construction); for shapes
    2 and 3 the range is A*R_f+K when every input of D_f is reachable by the inside (B|x|+C covers
    [C,inf) or (-inf,C]; |Bx+C| covers [0,inf)), NO REAL NUMBERS when nothing is reachable, and
    "can not be found" otherwise (Example 6.5 d);
  * order of the steps: the class rules (Cram 6.3): inside steps in reverse (shape 3 mirrors first,
    shape 2 mirrors last; reflect / horizontal factor 1/|B| / shift -C/B), then D, |y|, A, K.
  Sets are written in the class notation (ALL REALS, ALL REALS, X≠a, unions with U, INF).

Run from tools/:   python3 fuzz/fuzz_abs.py [-n SESSIONS] [-s SEED] [--kind pts,dom,rng,dr,order] [-v]
"""

import argparse
import random
import sys
import time
from decimal import ROUND_HALF_UP, Decimal, localcontext
from fractions import Fraction as Fr
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOLS = HERE.parent
sys.path.insert(0, str(TOOLS))
from tibasic import D, Machine, TIError, load_programs  # noqa: E402

SRC = TOOLS.parent / "src"
INF = float("inf")
MIRROR = "KEEP X≥0, MIRROR LEFT"
FOOT3 = "1:AGAIN  2:HOME  3:WHY"
FOOT2 = "1:AGAIN  2:HOME"


# ============================================================================ numbers as text
def ft(v):
    """a number the way HAFRAC writes it: -17/4, 6, INF; a 6-place decimal when no small fraction fits"""
    if v == INF:
        return "INF"
    if v == -INF:
        return "-INF"
    v = Fr(v)
    x = abs(v)
    if x == 0:
        return "0"
    sign = "-" if v < 0 else ""
    n, d = x.numerator, x.denominator
    if d <= 9999 and d * d * max(1, x) <= 10 ** 8:
        return sign + (str(n) if d == 1 else f"{n}/{d}")
    with localcontext() as ctx:
        ctx.prec = 40
        q = (Decimal(n) / Decimal(d)).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
    s = format(q, "f").rstrip("0").rstrip(".")
    return sign + s


def pt(x, y):
    return f"({ft(x)},{ft(y)})"


# ============================================================================ sets of reals
def in_ivl(u, iv):
    lo, hi, lc, rc = iv
    if u < lo or u > hi:
        return False
    if u == lo and not lc:
        return False
    if u == hi and not rc:
        return False
    return True


def merge(pieces):
    """union of intervals [lo, hi, lc, rc] (infinite ends open) -> sorted disjoint list"""
    ps = sorted((list(p) for p in pieces if p[0] < p[1] or (p[0] == p[1] and p[2] and p[3])),
                key=lambda p: (p[0], 0 if p[2] else 1))
    out = []
    for p in ps:
        if out:
            q = out[-1]
            if q[1] > p[0] or (q[1] == p[0] and (q[3] or p[2])):
                if p[0] == q[0]:
                    q[2] = q[2] or p[2]
                if p[1] > q[1]:
                    q[1], q[3] = p[1], p[3]
                elif p[1] == q[1]:
                    q[3] = q[3] or p[3]
                continue
        out.append(p)
    for p in out:
        if p[0] == -INF:
            p[2] = 0
        if p[1] == INF:
            p[3] = 0
    return out


def build_set(member, cands):
    """{x : member(x)} when member is constant on every open gap between the candidates"""
    cs = sorted(set(c for c in cands if c not in (INF, -INF)))
    if not cs:
        cs = [Fr(0)]
    pieces = []
    if member(cs[0] - 1):
        pieces.append([-INF, cs[0], 0, 0])
    for i, c in enumerate(cs):
        if member(c):
            pieces.append([c, c, 1, 1])
        if i + 1 < len(cs) and member((c + cs[i + 1]) / 2):
            pieces.append([c, cs[i + 1], 0, 0])
    if member(cs[-1] + 1):
        pieces.append([cs[-1], INF, 0, 0])
    return merge(pieces)


def render(S):
    """class notation (as on the answer screen): NO REAL NUMBERS, ALL REALS, ALL REALS, X≠a,b, unions"""
    if not S:
        return "NO REAL NUMBERS"
    if S[0][0] == -INF and S[-1][1] == INF and all(
            S[i][1] == S[i + 1][0] and not S[i][3] and not S[i + 1][2] for i in range(len(S) - 1)):
        if len(S) == 1:
            return "ALL REALS"
        return "ALL REALS, X≠" + ",".join(ft(S[i][1]) for i in range(len(S) - 1))
    return "U".join(("[" if p[2] else "(") + ft(p[0]) + "," + ft(p[1]) + ("]" if p[3] else ")") for p in S)


def subset(S, T):
    """every point of S is in T (S, T merged lists)"""
    for p in S:
        ok = False
        for q in T:
            lo_ok = q[0] < p[0] or (q[0] == p[0] and (q[2] or not p[2]))
            hi_ok = q[1] > p[1] or (q[1] == p[1] and (q[3] or not p[3]))
            if lo_ok and hi_ok:
                ok = True
                break
        if not ok:
            return False
    return True


# ============================================================================ the transformation
def inner(shape, B, C, x):
    if shape == 1:
        return B * x + C
    if shape == 2:
        return B * abs(x) + C
    return abs(B * x + C)


def solve_inner(shape, B, C, e):
    """every x with inner(x) = e"""
    if e in (INF, -INF):
        return []
    if shape == 1:
        return [(e - C) / B]
    if shape == 2:
        t = (e - C) / B
        return [t, -t] if t > 0 else ([Fr(0)] if t == 0 else [])
    if e < 0:
        return []
    return [(e - C) / B, (-e - C) / B]


def kink(shape, B, C):
    return [] if shape == 1 else [Fr(0)] if shape == 2 else [-C / B]


def inner_image(shape, B, C):
    """the set of values the inside can take"""
    if shape == 1:
        return [[-INF, INF, 0, 0]]
    if shape == 2:
        return [[C, INF, 1, 0]] if B > 0 else [[-INF, C, 0, 1]]
    return [[Fr(0), INF, 1, 0]]


def preimage(shape, B, C, iv):
    lo, hi = iv[0], iv[1]
    cands = solve_inner(shape, B, C, lo) + solve_inner(shape, B, C, hi) + kink(shape, B, C)
    return build_set(lambda x: in_ivl(inner(shape, B, C, x), iv), cands)


def image(iv, fn, crit):
    """image of an interval under a continuous piecewise-linear fn whose kinks are in crit"""
    lo, hi, lc, rc = iv
    if lo > hi or (lo == hi and not (lc and rc)):
        return []
    if lo == hi:
        v = fn(lo)
        return [[v, v, 1, 1]]
    nodes = [lo] + sorted(set(p for p in crit if lo < p < hi)) + [hi]
    pieces = []
    for a, b in zip(nodes, nodes[1:]):
        va, vb = fn(a), fn(b)
        if va == vb and va not in (INF, -INF):
            pieces.append([va, va, 1, 1])
        else:
            pieces.append([min(va, vb), max(va, vb), 0, 0])
    for p in nodes:
        if p not in (INF, -INF) and in_ivl(p, iv):
            v = fn(p)
            pieces.append([v, v, 1, 1])
    return merge(pieces)


class Graph:
    def __init__(self, xs, ys, lc, rc):
        self.xs, self.ys, self.lc, self.rc = xs, ys, lc, rc

    def dom(self):
        return [self.xs[0], self.xs[-1], self.lc, self.rc]

    def f(self, u):
        xs, ys = self.xs, self.ys
        assert xs[0] <= u <= xs[-1], u
        for i in range(len(xs)):
            if u == xs[i]:
                return ys[i]
        for i in range(len(xs) - 1):
            if xs[i] < u < xs[i + 1]:
                return ys[i] + (ys[i + 1] - ys[i]) * (u - xs[i]) / (xs[i + 1] - xs[i])
        raise AssertionError(u)


def g_value(G, shape, A, B, C, Dv, K, x):
    """g at x (x in the closure of the domain: hollow ends get their limit value)"""
    u = inner(shape, B, C, x)
    if shape == 1:
        return A * abs(G.f(u) + Dv) + K
    return A * G.f(u) + K


def graph_oracle(G, shape, A, B, C, Dv, K):
    """-> (points [(x, y)], D set, R set)"""
    S = preimage(shape, B, C, G.dom())
    if not S:
        return [], S, []
    bp = set(kink(shape, B, C))
    for xv in G.xs:
        bp.update(solve_inner(shape, B, C, xv))
    if shape == 1:
        for i in range(len(G.xs) - 1):
            y0, y1 = G.ys[i] + Dv, G.ys[i + 1] + Dv
            if y0 * y1 < 0:
                u0 = G.xs[i] - y0 * (G.xs[i + 1] - G.xs[i]) / (y1 - y0)
                bp.update(solve_inner(shape, B, C, u0))
    pts, rng = {}, []
    member = lambda x: in_ivl(inner(shape, B, C, x), G.dom())  # noqa: E731
    for a, b, _, _ in S:
        nodes = [a] + sorted(p for p in bp if a < p < b) + ([b] if b != a else [])
        vals = [g_value(G, shape, A, B, C, Dv, K, x) for x in nodes]
        # dense sampling: g must be linear between consecutive nodes
        for (x0, v0), (x1, v1) in zip(zip(nodes, vals), zip(nodes[1:], vals[1:])):
            for j in range(1, 64):
                xs_ = x0 + (x1 - x0) * j / 64
                want = v0 + (v1 - v0) * j / 64
                assert g_value(G, shape, A, B, C, Dv, K, xs_) == want, "oracle: g not linear between nodes"
        pts[a] = vals[0]
        pts[nodes[-1]] = vals[-1]
        for i in range(1, len(nodes) - 1):
            sl = (vals[i] - vals[i - 1]) / (nodes[i] - nodes[i - 1])
            sr = (vals[i + 1] - vals[i]) / (nodes[i + 1] - nodes[i])
            if sl != sr:
                pts[nodes[i]] = vals[i]
        for i in range(len(nodes) - 1):
            va, vb = vals[i], vals[i + 1]
            rng.append([va, va, 1, 1] if va == vb else [min(va, vb), max(va, vb), 0, 0])
        for x, v in zip(nodes, vals):
            if member(x):
                rng.append([v, v, 1, 1])
    return sorted(pts.items()), S, merge(rng)


def lin_steps(shape, B, C):
    """the inside (x) steps in the order they happen to a point of f"""
    if shape == 3 and B < 0:  # |Bx+C| = |(-B)x-C|: no reflection is needed
        B, C = -B, -C
    out = []
    if shape == 3:
        out.append(MIRROR)
    if B < 0:
        out.append("REFLECT Y-AXIS")
    if abs(B) > 1:
        out.append("HORIZ COMPRESS " + ft(1 / abs(B)))
    elif abs(B) < 1:
        out.append("HORIZ STRETCH " + ft(1 / abs(B)))
    h = -C / B
    if h > 0:
        out.append("RIGHT " + ft(h))
    elif h < 0:
        out.append("LEFT " + ft(-h))
    if shape == 2:
        out.append(MIRROR)
    return out


def y_steps(shape, A, Dv, K):
    out = []
    if shape == 1 and Dv:
        out.append(("UP " if Dv > 0 else "DOWN ") + ft(abs(Dv)))
    if shape == 1:
        out.append("|Y|: FLIP NEGATIVES UP")
    if A < 0:
        out.append("REFLECT X-AXIS")
    if abs(A) > 1:
        out.append("VERT STRETCH " + ft(abs(A)))
    elif abs(A) < 1:
        out.append("VERT COMPRESS " + ft(abs(A)))
    if K:
        out.append(("UP " if K > 0 else "DOWN ") + ft(abs(K)))
    return out


def numbered(steps):
    """steps are written (1) ..., (2) ... as the class writes an order answer (Example 6.3)"""
    return [f"({i}) {s}" for i, s in enumerate(steps, 1)]


# ============================================================================ the simulator
class RecMachine(Machine):
    """records every line handed to HAOUT (whole, before wrapping), page starts and footers;
    presses ENTER for the student at an ENTER=MORE wait"""

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


def run(actions, lists=None):
    global PROGS
    if PROGS is None:
        PROGS = load_programs(SRC)
    m = RecMachine(PROGS, persistent_lists=lists)
    err = None
    try:
        res = m.run(["ENTER"] + list(actions) + ["CLEAR"] * 6)
    except TIError as e:
        res, err = ("error", None), str(e)
    return m, res, err


# ============================================================================ random numbers and typing
WIDE = [False]


def rnum(rng, zero=True, small=False):
    r = rng.random()
    if zero and r < 0.2:
        return Fr(0)
    if WIDE[0] and r > 0.9:
        v = Fr(rng.randint(1, 60), rng.choice([1, 6, 7, 9]))  # long numbers, big denominators
        return v if rng.random() < 0.5 else -v
    if r < 0.6:
        v = Fr(rng.randint(1, 5 if small else 9))
    elif r < 0.85:
        q = rng.choice([2, 3, 4])
        v = Fr(rng.randint(1, 3 * q), q)
    else:
        v = Fr(rng.choice([1, 3, 5, 7]), rng.choice([2, 3, 5]))
    return v if rng.random() < 0.5 else -v


def coef(rng):
    r = rng.random()
    if r < 0.3:
        return Fr(1)
    if r < 0.45:
        return Fr(-1)
    return rnum(rng, zero=False, small=True)


def typed(rng, v, default=None, plus=False):
    """the text a student types for v (default = what ENTER gives)"""
    if default is not None and v == default and rng.random() < 0.6:
        return ""
    neg = v < 0
    a = abs(v)
    minus = rng.choice(["-", "⁻"])
    if neg and a == 1 and default == 1 and rng.random() < 0.5:
        return minus
    if a.denominator == 1:
        body = str(a.numerator)
    else:
        r = rng.random()
        if a.denominator in (2, 4, 5) and r < 0.15:
            body = str(float(a))
        elif neg and r < 0.3:
            return f"{minus}({a.numerator}/{a.denominator})"
        else:
            body = f"{a.numerator}/{a.denominator}"
    if neg:
        return minus + body
    if plus and v > 0 and rng.random() < 0.2:
        return "+" + body  # the student copies the plus sign: f(x+2) -> +2
    return body


def t(s):
    return "t:" + s


def type_nonzero(rng, v, xcopy=False):
    s = typed(rng, v, 1)
    if xcopy and rng.random() < 0.15:
        s = s + "X"  # the student copies the X: 2X, -X, X
    return [t(s)]


def rand_end(rng):
    r = rng.random()
    if r < 0.6:
        return Fr(rng.randint(-8, 8))
    if r < 0.85:
        return Fr(rng.randint(-16, 16), rng.choice([2, 3, 4]))
    return Fr(rng.choice([0, 0, 1, -1, 2, -2]))


def rand_ivl(rng, inf_ok=True):
    """-> (interval, typing actions)"""
    lo, hi = rand_end(rng), rand_end(rng)
    if lo > hi:
        lo, hi = hi, lo
    if lo == hi and rng.random() < 0.7:
        hi = lo + rng.randint(1, 6)
    if inf_ok and rng.random() < 0.12:
        lo = -INF
    if inf_ok and rng.random() < 0.12:
        hi = INF
    br = rng.choice([1, 1, 1, 2, 3, 4]) if lo != hi else 1
    lc = int(br in (1, 2)) if lo != -INF else 0
    rc = int(br in (1, 3)) if hi != INF else 0

    def tx(v):
        if v == INF:
            return "I"
        if v == -INF:
            return rng.choice(["-I", "⁻I"])
        return typed(rng, v)

    a, b = tx(lo), tx(hi)
    if a == "":
        a = "0"
    if b == "":
        b = "0"
    acts = [t(a), t(b)] if rng.random() < 0.9 else [t(b), t(a)]  # ends typed in the wrong order
    if not (lo == -INF and hi == INF):
        acts.append(f"k{br}")
    return [lo, hi, lc, rc], acts


def rand_graph(rng):
    n = rng.choice([1, 2, 2, 3, 3, 4, 4, 4, 5, 5, 6, 7]) if rng.random() < 0.97 else 1
    if WIDE[0] and rng.random() < 0.3:
        n = rng.randint(8, 14)
    style = rng.random()
    x = Fr(rng.randint(-7, 3)) if style < 0.6 else (Fr(rng.randint(0, 4)) if style < 0.8 else Fr(rng.randint(-9, -3)))
    xs = []
    for _ in range(n):
        xs.append(x)
        x += rng.choice([Fr(1), Fr(1), Fr(2), Fr(2), Fr(3), Fr(1, 2), Fr(3, 2)] +
                        ([Fr(1, 3), Fr(7, 4), Fr(11), Fr(25, 7)] if WIDE[0] else []))
    ys = []
    for _ in range(n):
        r = rng.random()
        if r < 0.15:
            ys.append(Fr(0))
        elif r < 0.25 and ys:
            ys.append(ys[-1])  # flat piece
        elif r < 0.85:
            ys.append(Fr(rng.randint(-5, 5)) * (rng.choice([1, 1, 10, 40]) if WIDE[0] else 1))
        else:
            ys.append(Fr(rng.randint(-9, 9), rng.choice([2, 3, 7]) if WIDE[0] else 2))
    dots = rng.choice([1, 1, 1, 1, 2, 3, 4]) if n > 1 else 1
    lc, rc = int(dots in (1, 3)), int(dots in (1, 2))
    acts = [t(str(n))]
    for xv, yv in zip(xs, ys):
        acts += [t(typed(rng, xv) or "0"), t(typed(rng, yv) or "0")]
    acts.append(f"k{dots}")
    return Graph(xs, ys, lc, rc), acts


# ============================================================================ problems
class Problem:
    pass


MODES = {"pts": 1, "dom": 2, "rng": 3, "dr": 4, "order": 5}


def coef_actions(rng, p):
    """the A, B, C, D, K prompts this mode asks, in order.  A or B typed as 0 is refused: the screen
    is drawn again (with A AND B CAN NOT BE 0) and the questions start again at A."""
    J, I = p.J, p.shape
    acts = []
    a_acts = (lambda: type_nonzero(rng, p.A)) if J != 2 else (lambda: [])
    if J != 2 and rng.random() < 0.06:
        acts.append(t("0"))
    acts += a_acts()
    if not (J == 3 and I == 1):
        if rng.random() < 0.06:
            acts += [t("0")] + a_acts()
        acts += type_nonzero(rng, p.B, xcopy=(I != 2))
        acts.append(t(typed(rng, p.C, 0, plus=True)))
    if J != 2:
        if I == 1:
            acts.append(t(typed(rng, p.Dv, 0, plus=True)))
        acts.append(t(typed(rng, p.K, 0, plus=True)))
    return acts


def new_problem(rng, kind, state):
    p = Problem()
    p.kind = kind
    p.J = MODES[kind]
    p.shape = rng.choice([1, 2, 3])
    p.A, p.B = coef(rng), coef(rng)
    p.C, p.Dv, p.K = rnum(rng), rnum(rng), rnum(rng)
    if p.J == 2:
        p.A, p.Dv, p.K = Fr(1), Fr(0), Fr(0)
    if p.J == 3 and p.shape == 1:
        p.B, p.C = Fr(1), Fr(0)
    if p.shape != 1:
        p.Dv = Fr(0)
    p.body = coef_actions(rng, p)
    p.why = p.J != 5 and rng.random() < 0.35
    I, A, B, C, Dv, K = p.shape, p.A, p.B, p.C, p.Dv, p.K
    lines = []
    if kind == "pts":
        saved = state.get("saved")
        if saved is not None and rng.random() < 0.5:
            G = saved
            p.body.append("k1")
        else:
            G, gacts = rand_graph(rng)
            if saved is not None:
                p.body.append("k2")
            p.body += gacts
            state["saved"] = G
        p.G = G
        pts, S, R = graph_oracle(G, I, A, B, C, Dv, K)
        p.pts = pts
        if not S:
            lines = ["D=NO REAL NUMBERS", "(NOTHING TO GRAPH)"]
        else:
            lines = ["<PTS>", "D=" + render(S), "R=" + render(R)]
    elif kind == "order":
        lines = numbered(lin_steps(I, B, C) + y_steps(I, A, Dv, K))
    else:
        need_d = p.J in (2, 4) or (p.J == 3 and I != 1)
        Df = Rf = None
        if need_d:
            Df, acts = rand_ivl(rng)
            p.body += acts
        full = I == 1 or subset([Df] if Df[0] < Df[1] or (Df[2] and Df[3]) else [], inner_image(I, B, C))
        if p.J in (3, 4) and full:
            Rf, acts = rand_ivl(rng)
            p.body += acts
        if need_d:
            S = preimage(I, B, C, Df)
            if p.J in (2, 4):
                lines.append("D=" + render(S))
        if p.J in (3, 4):
            if full:
                if I == 1:
                    R = image(Rf, lambda y: A * abs(y + Dv) + K, [-Dv])
                else:
                    R = image(Rf, lambda y: A * y + K, [])
                lines.append("R=" + render(R))
            elif not S:
                lines.append("R=NO REAL NUMBERS")
            else:
                c = C if I == 2 else Fr(0)
                lines += ["R CAN NOT BE FOUND FROM", "D AND R ALONE: IT DEPENDS",
                          ("ON WHAT F DOES FOR X≤" if (I == 2 and B < 0) else "ON WHAT F DOES FOR X≥") + ft(c),
                          "(USE 1 WITH THE GRAPH)"]
        p.Df, p.Rf = Df, Rf
    p.lines = lines
    if p.J == 5:
        p.footer = FOOT2
    else:
        p.footer = FOOT3
        head = {2: "ONLY X STEPS CHANGE D:", 3: "ONLY Y STEPS CHANGE R:"}.get(p.J, "STEPS IN ORDER:")
        st = (lin_steps(I, B, C) if p.J != 3 else []) + (y_steps(I, A, Dv, K) if p.J != 2 else [])
        p.why_lines = [head] + (numbered(st) or ["NO CHANGE"])
    p.desc = f"J={p.J} shape={I} A={A} B={B} C={C} D={Dv} K={K}" + (
        f" Df={p.Df} Rf={p.Rf}" if kind in ("dom", "rng", "dr") else "") + (
        f" graph={list(zip(p.G.xs, p.G.ys))} ends={p.G.lc},{p.G.rc}" if kind == "pts" else "")
    return p


def make_session(rng, kinds, state):
    probs = []
    acts = []
    chained = False
    for i in range(rng.choice([1, 1, 2, 3])):
        probs.append(new_problem(rng, rng.choice(kinds), state))
    out = []
    for i, p in enumerate(probs):
        if not chained:
            acts.append("k5")
            if rng.random() < 0.08:
                acts += ["k9", "CLEAR", "k5"]  # a dead key, CLEAR back to the main menu, back in
            acts.append(f"k{p.J}")
        if rng.random() < 0.06:
            acts += ["k7", "CLEAR", f"k{p.J}"]  # a dead key at the shape menu, CLEAR back, same choice
        acts.append(f"k{p.shape}")
        acts += p.body
        if p.why:
            acts.append("k3")
        nxt = probs[i + 1] if i + 1 < len(probs) else None
        chained = nxt is not None and nxt.J == p.J and rng.random() < 0.7
        acts.append("k1" if chained else "k2")
        out.append(p)
    return acts, out


def answer_screens(m):
    return [s for s in m.out if s and s[0] == "ANSWER:"]


def join_lines(body):
    """a long D=...U line goes on with an indented line (the rest of the union)"""
    joined = []
    for ln in body:
        if joined and joined[-1].startswith("D=") and joined[-1].endswith("U"):
            if not ln.startswith("  "):
                joined.append("<CONTINUATION NOT INDENTED>")
            joined[-1] += ln.strip()
        else:
            joined.append(ln)
    return joined


def check_answer(p, body):
    """body = the HAOUT lines of one answer screen (footer removed) -> list of mismatches"""
    errs = []
    body = join_lines(body)
    for ln in body:
        if "<CONTINUATION" in ln:
            errs.append("D continuation line not indented")
    if p.lines and p.lines[0] == "<PTS>":
        ptl = [ln for ln in body if ln.startswith("(")]
        rest = [ln for ln in body if not ln.startswith("(")]
        got = [s for ln in ptl for s in ln.split("  ") if s]
        want = [pt(x, y) for x, y in p.pts]
        if got != want:
            errs.append(f"points got {got} want {want}")
        for ln in ptl:
            if len(ln) > 26:
                errs.append(f"point line too long {ln!r}")
        if rest != p.lines[1:]:
            errs.append(f"got {rest} want {p.lines[1:]}")
        return errs
    if body != p.lines:
        errs.append(f"got {body} want {p.lines}")
    return errs


BASE = Graph([Fr(-4), Fr(-2), Fr(1), Fr(3)], [Fr(2), Fr(-2), Fr(4), Fr(0)], 1, 1)  # Section 5 base graph


def run_case(rng, kinds, state):
    lists = state.get("saved_lists")
    acts, probs = make_session(rng, kinds, state)
    m, res, err = run(acts, lists)
    # the saved graph stays on the calculator for the next session
    if m.lists.get("ʟBX"):
        state["saved_lists"] = {k: list(m.lists[k]) for k in ("ʟBX", "ʟBY", "ʟBC")}
    errs = []
    if err:
        errs.append(f"TI error: {err}")
    elif res[0] != "stop":
        errs.append(f"did not stop cleanly: {res} last screen {[ln for ln in m.lines() if ln.strip()]}")
    if m.problems:
        errs.append(f"screen problems: {m.problems[:3]}")
    if not errs:
        screens = answer_screens(m)
        whys = [s for s in m.out if s and s[0] == "PAGE WHY:"]
        if len(screens) != len(probs):
            errs.append(f"{len(screens)} answer screens, expected {len(probs)}")
        wi = 0
        for p, s in zip(probs, screens):
            body = [ln for ln in s[1:] if not ln.startswith("FOOTER ")]
            foot = [ln[7:] for ln in s if ln.startswith("FOOTER ")]
            if foot != [p.footer]:
                errs.append(f"[{p.kind}] footer {foot} != {p.footer}")
            errs += [f"[{p.kind} {p.desc}] " + e for e in check_answer(p, body)]
            if p.why:
                if wi >= len(whys):
                    errs.append("WHY page missing")
                else:
                    wb = [ln for ln in whys[wi][1:] if not ln.startswith("FOOTER ")]
                    if wb != p.why_lines:
                        errs.append(f"[why {p.desc}] got {wb} want {p.why_lines}")
                    wi += 1
    return errs, acts, probs, m


KINDS = list(MODES)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-n", type=int, default=500)
    ap.add_argument("-s", type=int, default=1)
    ap.add_argument("--kind", default=None)
    ap.add_argument("-v", action="store_true")
    ap.add_argument("--wide", action="store_true", help="bigger numbers, more points, denominators 6-9")
    args = ap.parse_args()
    WIDE[0] = args.wide
    rng = random.Random(args.s)
    kinds = args.kind.split(",") if args.kind else KINDS
    state = {"saved": BASE, "saved_lists": {"ʟBX": [D(-4), D(-2), D(1), D(3)], "ʟBY": [D(2), D(-2), D(4), D(0)],
                                            "ʟBC": [D(1), D(1)]}}
    stats = {k: 0 for k in KINDS}
    bad = 0
    t0 = time.time()
    shown = 0
    for i in range(args.n):
        errs, acts, probs, m = run_case(rng, kinds, state)
        for p in probs:
            stats[p.kind] += 1
        if errs:
            bad += 1
            if shown < 25:
                shown += 1
                print(f"--- session {i}: {[p.kind for p in probs]}")
                for e in errs[:6]:
                    print("   ", e)
                if args.v:
                    print("    actions:", acts)
    print(f"{args.n} sessions, {sum(stats.values())} problems {stats}; {bad} sessions with mismatches; "
          f"{time.time() - t0:.1f}s")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
