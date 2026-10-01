#!/usr/bin/env python3
"""
Randomized differential testing of main menu 1 (F+G OR F/G, program HAOPS).

Every case is a random Section-1 style problem.  The script types it into the simulator
exactly as a student would (main menu 1, WHAT DO THEY WANT?, WHICH ONE IS IT?, the f and g
shape menus of HAFUNC, the coefficients / corner points / words, X=), reads the ANSWER
screen(s), and compares every answer line with an exact oracle written independently here
with sympy (domains as sympy sets, values as exact algebraic numbers, formulas checked
at exact sample points).

    python3 fuzz/fuzz_ops.py [N] [SEED] [-v]       (from tools/; default N=600, SEED=1)
    python3 fuzz/fuzz_ops.py --seed S              one case: every screen, then the verdict
    python3 fuzz/fuzz_ops.py --helpers N [SEED]    HAFDOM band / f(g(x)) domain, HAFZERO levels,
                                                   HAFSTR text, from a driver program
    python3 fuzz/fuzz_ops.py --monkey N [SEED]     random keys and inputs inside main menu 1:
                                                   no error, clean screen, CLEAR gets out

A session has 1-4 rounds: the first from the main menu, later ones through 4:SAME F,G (new
question, same f and g) or 1:AGAIN (same question type, new f and g, saved graphs kept).
Categories: a mismatch is any wrong or missing answer line, crash, scroll or flow error;
"inexact-*" marks a correct answer shown as an ABOUT decimal (reported, not counted).

Shapes covered: AX+B, AX²+BX+C, (AX+B)/(CX+D), K/(AX+B), K√(AX+B)+C, (AX²+BX+C)/(DX²+EX+F),
typed graphs (1-6 corners, hollow/solid ends, flat zero pieces), saved graphs, words
(finite or infinite ends, zero points, zero stretches).  Coefficients: negative (typed
with the subtraction minus or the (-) key), fractions, decimals, zero, ENTER defaults.
Questions: DOMAIN, VALUE, FORMULA for F+G, F-G, FG, F/G, G/F, G-F; then, at random,
4:SAME F,G with a second question, 3:WHY, 1:AGAIN or 2:HOME.
"""

import random
import re
import sys
from fractions import Fraction
from pathlib import Path

import sympy as sp
from sympy.parsing.sympy_parser import (implicit_multiplication, parse_expr,
                                        standard_transformations)

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from tibasic import D, Halt, Machine, TIError, load_programs  # noqa: E402

SRC = HERE.parent.parent / "src"
x = sp.Symbol("x", real=True)
R = sp.S.Reals
EMPTY = sp.S.EmptySet
COMBOS = ["F+G", "F-G", "FG", "F/G", "G/F", "G-F"]
SHAPE_KEY = {"line": "k1", "quad": "k2", "frac": "k3", "recip": "k4", "root": "k5", "frac2": "k6",
             "graph": "k7", "words": "k8"}


# ----------------------------------------------------------------------------- numbers
def q(v):
    return sp.Rational(Fraction(v).numerator, Fraction(v).denominator)


def ttext(v):
    """plain text of an exact rational"""
    v = sp.Rational(v)
    return str(v.p) if v.q == 1 else f"{v.p}/{v.q}"


class Gen:
    def __init__(self, rng):
        self.r = rng

    def num(self, lo=-6, hi=6, frac=0.15, zero=0.12):
        r = self.r
        if r.random() < zero:
            return sp.Integer(0)
        if r.random() < frac:
            d = r.choice([2, 3, 4, 5])
            n = r.randint(lo * d, hi * d)
            return sp.Rational(n, d)
        return sp.Integer(r.randint(lo, hi))

    def typed(self, v, default):
        """what the student types for the value v at a prompt whose ENTER default is `default`"""
        r = self.r
        v = sp.Rational(v)
        if v == default and r.random() < 0.6:
            return ""
        if v == -1 and default == 1 and r.random() < 0.3:
            return r.choice(["-", "⁻"])
        s = ttext(v)
        if v.q in (2, 4, 5) and r.random() < 0.2:
            s = str(float(v)).rstrip("0").rstrip(".")
            if s.startswith("0."):
                s = s[1:] if r.random() < 0.3 else s
        if s.startswith("-") and r.random() < 0.5:
            s = "⁻" + s[1:]
        if s.startswith("-") and "/" in s and r.random() < 0.15:
            s = "(" + s + ")"
        return s


# ----------------------------------------------------------------------------- functions
class Fn:
    """a function as the student sees it on paper, with exact facts for the oracle"""

    def value(self, x0):
        raise NotImplementedError


def is_zero(e):
    """exact zero test that also works for unsimplified surd expressions"""
    e = sp.sympify(e)
    if e == 0:
        return True
    if e.is_Rational:
        return False
    v = sp.N(e, 60)
    if abs(v) > sp.Float("1e-40"):
        return False
    return sp.simplify(e) == 0 or abs(v) < sp.Float("1e-55")


def sign(e):
    """-1, 0 or 1 for an exact real number"""
    if is_zero(e):
        return 0
    return 1 if sp.N(e, 60) > 0 else -1


def poly_val(cs, x0):
    v = sp.Integer(0)
    for c in cs:
        v = v * x0 + c
    return v


def real_roots(cs):
    """real zeros of a polynomial with highest-first coefficients (None if it is 0)"""
    p = sp.Integer(0)
    for c in cs:
        p = p * x + c
    p = sp.expand(p)
    if p == 0:
        return None
    return sorted(sp.solveset(p, x, R), key=lambda t: float(t)) if p.has(x) else []


class Rational(Fn):
    def __init__(self, kind, num, den, keys, text):
        self.kind, self.num, self.den, self.keys, self.text = kind, num, den, keys, text
        droots = real_roots(den)
        assert droots is not None
        self.dom = R - sp.FiniteSet(*droots) if droots else R
        nroots = real_roots(num)
        if nroots is None:
            self.zeros = self.dom
        else:
            self.zeros = sp.FiniteSet(*[t for t in nroots if t not in droots])
        self.formula = True

    def value(self, x0):
        d = poly_val(self.den, x0)
        if is_zero(d):
            return ("undef",)
        v = poly_val(self.num, x0) / d
        return ("val", sp.Integer(0) if is_zero(v) else v)

    def sym(self):
        return poly_val(self.num, x) / poly_val(self.den, x)


class Root(Fn):
    def __init__(self, K, A, B, C, keys):
        self.kind, self.K, self.A, self.B, self.C, self.keys = "root", K, A, B, C, keys
        if A > 0:
            self.dom = sp.Interval(-B / A, sp.oo)
        elif A < 0:
            self.dom = sp.Interval(-sp.oo, -B / A)
        else:
            self.dom = R if B >= 0 else EMPTY
        # zeros: K*sqrt(u)+C = 0
        if K == 0:
            self.zeros = self.dom if C == 0 else EMPTY
        else:
            s = -C / K
            if s < 0:
                self.zeros = EMPTY
            elif A == 0:
                self.zeros = self.dom if B == s ** 2 else EMPTY
            else:
                self.zeros = sp.FiniteSet((s ** 2 - B) / A)
        self.formula = True
        self.text = f"{K}*sqrt({A}x+{B})+{C}"

    def value(self, x0):
        u = self.A * x0 + self.B
        if sign(u) < 0:
            return ("undef",)
        v = self.K * sp.sqrt(0 if is_zero(u) else u) + self.C
        return ("val", sp.Integer(0) if is_zero(v) else v)

    def sym(self):
        return self.K * sp.sqrt(self.A * x + self.B) + self.C


class Graph(Fn):
    def __init__(self, pts, lc, rc, keys, saved=None):
        self.kind, self.pts, self.lc, self.rc, self.keys = "graph", pts, lc, rc, keys
        self.saved = saved
        x1, xn = pts[0][0], pts[-1][0]
        if x1 == xn:
            self.dom = sp.FiniteSet(x1) if (lc and rc) else EMPTY
        else:
            self.dom = sp.Interval(x1, xn, not lc, not rc)
        z = EMPTY
        for (a, ya), (b, yb) in zip(pts, pts[1:]):
            if ya == 0 and yb == 0:
                z = z | sp.Interval(a, b)
            elif ya * yb < 0:
                z = z | sp.FiniteSet(a - ya * (b - a) / (yb - ya))
        for a, ya in pts:
            if ya == 0:
                z = z | sp.FiniteSet(a)
        self.zeros = z & self.dom
        self.formula = False
        self.text = f"graph{pts} {'[' if lc else '('}{']' if rc else ')'}"

    def value(self, x0):
        pts = self.pts
        lo_s, hi_s = sign(x0 - pts[0][0]), sign(x0 - pts[-1][0])
        if lo_s < 0 or hi_s > 0 or (lo_s == 0 and not self.lc) or (hi_s == 0 and not self.rc):
            return ("undef",)
        for (a, ya), (b, yb) in zip(pts, pts[1:]):
            if sign(x0 - a) >= 0 and sign(x0 - b) <= 0:
                v = ya + (yb - ya) * (x0 - a) / (b - a)
                return ("val", sp.Integer(0) if is_zero(v) else v)
        return ("val", pts[0][1])


class Words(Fn):
    def __init__(self, L, Rr, lc, rc, zpts, zstr, keys):
        self.kind, self.keys = "words", keys
        self.dom = sp.Interval(L, Rr, not lc, not rc)
        z = sp.FiniteSet(*zpts)
        for a, b in zstr:
            z = z | sp.Interval(a, b)
        self.zeros = z & self.dom
        self.formula = False
        self.text = f"words {self.dom} zeros {self.zeros}"
        self.L, self.Rr, self.lc, self.rc, self.zpts, self.zstr = L, Rr, lc, rc, zpts, zstr

    def value(self, x0):
        lo = 1 if self.L == -sp.oo else sign(x0 - self.L)
        hi = -1 if self.Rr == sp.oo else sign(x0 - self.Rr)
        if lo < 0 or hi > 0 or (lo == 0 and not self.lc) or (hi == 0 and not self.rc):
            return ("undef",)
        if any(is_zero(x0 - p) for p in self.zpts) or any(sign(x0 - a) >= 0 and sign(x0 - b) <= 0
                                                          for a, b in self.zstr):
            return ("val", sp.Integer(0))
        return ("unk",)


# ----------------------------------------------------------------------------- generators
def gen_fn(g, name, state, shape=None, inside=None):
    """random function for the slot `name` ("F"/"G"); returns Fn with .keys = actions after the
    shape menu is shown (including the shape key)."""
    r = g.r
    shape = shape or r.choices(["line", "quad", "frac", "recip", "root", "frac2", "graph", "words"],
                               [14, 12, 14, 8, 14, 10, 14, 12])[0]
    k = [SHAPE_KEY[shape]]
    if shape == "line":
        A, B = g.num(), g.num()
        k += [f"t:{g.typed(A, 1)}", f"t:{g.typed(B, 0)}"]
        return Rational(shape, [A, B], [1], k, f"{A}x+{B}")
    if shape == "quad":
        A, B, C = g.num(zero=0.05), g.num(zero=0.3), g.num()
        k += [f"t:{g.typed(A, 1)}", f"t:{g.typed(B, 1)}", f"t:{g.typed(C, 0)}"]
        return Rational(shape, [A, B, C], [1], k, f"{A}x²+{B}x+{C}")
    if shape in ("frac", "recip", "frac2"):
        while True:
            if shape == "frac":
                A, B = g.num(), g.num()
                C, Dd = g.num(zero=0.2), g.num()
                num, den = [A, B], [C, Dd]
                vals = [(A, 1), (B, 0), (C, 1), (Dd, 0)]
            elif shape == "recip":
                K, A, B = g.num(zero=0.05), g.num(zero=0.15), g.num()
                num, den = [K], [A, B]
                vals = [(K, 1), (A, 1), (B, 0)]
            else:
                A, B, C = g.num(zero=0.4), g.num(zero=0.3), g.num()
                Dd, E, F = g.num(zero=0.2), g.num(zero=0.3), g.num()
                num, den = [A, B, C], [Dd, E, F]
                vals = [(A, 1), (B, 1), (C, 0), (Dd, 1), (E, 1), (F, 0)]
            if any(c != 0 for c in den):
                break
        k += [f"t:{g.typed(v, d)}" for v, d in vals]
        return Rational(shape, num, den, k, f"({num})/({den})")
    if shape == "root":
        K, A, B, C = g.num(zero=0.05), g.num(zero=0.08), g.num(), g.num(zero=0.5)
        if inside is not None:
            A, B = inside  # same radicand as the other function
        k += [f"t:{g.typed(K, 1)}", f"t:{g.typed(A, 1)}", f"t:{g.typed(B, 0)}", f"t:{g.typed(C, 0)}"]
        return Root(K, A, B, C, k)
    if shape == "graph":
        other = "G" if name == "F" else "F"
        if state.get(name) and r.random() < 0.3:
            pts, lc, rc = state[name]
            k += ["k2" if name == "F" else "k3"]
            return Graph(pts, lc, rc, k, saved=name)
        if state.get(other) and r.random() < 0.15:
            pts, lc, rc = state[other]
            k += ["k3" if other == "G" else "k2"]
            return Graph(pts, lc, rc, k, saved=other)
        n = r.choices([1, 2, 3, 4, 5, 6], [2, 10, 20, 25, 25, 18])[0]
        xs = sorted(r.sample(range(-8, 9), n))
        if r.random() < 0.15:
            xs = [sp.Rational(v, 2) for v in sorted(r.sample(range(-16, 17), n))]
        ys = []
        for i in range(n):
            if ys and ys[-1] == 0 and r.random() < 0.35:
                ys.append(sp.Integer(0))
            else:
                ys.append(sp.Integer(r.choice([-3, -2, -1, 0, 0, 1, 2, 3, 4])))
        pts = [(sp.Integer(a) if not isinstance(a, sp.Basic) else a, b) for a, b in zip(xs, ys)]
        ends = r.choices(["k1", "k2", "k3", "k4"], [60, 15, 15, 10])[0]
        lc, rc = ends in ("k1", "k3"), ends in ("k1", "k2")
        if state.get("F") or state.get("G"):
            k += ["k1"]
        k += [f"t:{n}"]
        order = list(range(n))
        if r.random() < 0.1:
            r.shuffle(order)  # typed out of order: HAPTS sorts them
        for i in order:
            k += [f"t:{g.typed(pts[i][0], None)}", f"t:{g.typed(pts[i][1], None)}"]
        k += [ends]
        state[name] = (pts, lc, rc)
        return Graph(pts, lc, rc, k)
    # words
    inf_l, inf_r = r.random() < 0.15, r.random() < 0.15
    a, b = sorted(r.sample(range(-8, 9), 2))
    L = -sp.oo if inf_l else sp.Integer(a)
    Rr = sp.oo if inf_r else sp.Integer(b)
    br = r.choices(["k1", "k2", "k3", "k4"], [55, 15, 15, 15])[0]
    lc = (not inf_l) and br in ("k1", "k2")
    rc = (not inf_r) and br in ("k1", "k3")
    lo = a - 4 if inf_l else a
    hi = b + 4 if inf_r else b
    cand = [v for v in range(lo, hi + 1) if (v > lo or lc or inf_l) and (v < hi or rc or inf_r)]
    zpts = sorted(r.sample(cand, min(len(cand), r.choice([0, 0, 1, 1, 2, 3])))) if cand else []
    zstr = []
    if r.random() < 0.3 and hi - lo >= 3:
        s = r.randint(lo + 1, hi - 2)
        e = r.randint(s + 1, min(hi - 1, s + 3))
        zstr.append((sp.Integer(s), sp.Integer(e)))
    k += [f"t:{'-I' if inf_l else g.typed(L, None)}", f"t:{'I' if inf_r else g.typed(Rr, None)}"]
    if r.random() < 0.1 and not (inf_l or inf_r):
        k[-2], k[-1] = k[-1], k[-2]  # typed right end first: HAIVL swaps them
    if not (inf_l and inf_r):
        k += [br]
    k += [f"t:{len(zpts) if zpts or r.random() < 0.5 else ''}"]
    k += [f"t:{g.typed(sp.Integer(v), None)}" for v in zpts]
    k += [f"t:{len(zstr) if zstr or r.random() < 0.5 else ''}"]
    for s, e in zstr:
        if r.random() < 0.2:
            s, e = e, s  # typed backwards: HAWORDS sorts each pair
        k += [f"t:{s}", f"t:{e}"]
    return Words(L, Rr, lc, rc, [sp.Integer(v) for v in zpts], zstr, k)


# ----------------------------------------------------------------------------- oracle
def combo_domain(f, g, K):
    d = f.dom & g.dom
    if K == "F/G":
        d = d - g.zeros
    elif K == "G/F":
        d = d - f.zeros
    return sp.simplify(d) if not isinstance(d, (sp.Interval, sp.Union, sp.FiniteSet)) else d


def combo_value(f, g, K, x0):
    a, b = f.value(x0), g.value(x0)
    if a[0] == "undef" or b[0] == "undef":
        return ("undef",)
    if K == "F/G" and b == ("val", 0):
        return ("undef",)
    if K == "G/F" and a == ("val", 0):
        return ("undef",)
    if K == "FG" and (a == ("val", 0) or b == ("val", 0)):
        return ("val", sp.Integer(0))
    # words: a value not given but known to be nonzero (x in the domain, not a listed zero)
    if K == "F/G" and a == ("val", 0) and b[0] == "unk":
        return ("val", sp.Integer(0))
    if K == "G/F" and b == ("val", 0) and a[0] == "unk":
        return ("val", sp.Integer(0))
    if a[0] == "unk" or b[0] == "unk":
        return ("unk",)
    u, v = a[1], b[1]
    val = {"F+G": u + v, "F-G": u - v, "FG": u * v, "F/G": u / v if v != 0 else None,
           "G/F": v / u if u != 0 else None, "G-F": v - u}[K]
    return ("val", sp.radsimp(val) if val is not None else None)


def combo_sym(f, g, K):
    u, v = f.sym(), g.sym()
    return {"F+G": u + v, "F-G": u - v, "FG": u * v, "F/G": u / v, "G/F": v / u, "G-F": v - u}[K]


# ----------------------------------------------------------------------------- parsing
NUM = r"-?(?:\d+(?:\.\d*)?|\.\d+)(?:/\d+)?|-?INF"


def pnum(s):
    """one end or excluded point: INF, -INF, a fraction, a surd like (3+√(21))/6, or a decimal"""
    s = s.strip()
    if s == "INF":
        return sp.oo, True
    if s == "-INF":
        return -sp.oo, True
    if re.fullmatch(r"-?\d*\.\d+|-?\d+\.\d*", s):
        return sp.Float(s), False
    v = parse_expr_text(s)
    if v.free_symbols or not v.is_real:
        raise ValueError(f"bad number {s!r}")
    return v, True


def split0(s, sep):
    """split at sep characters that are outside every bracket"""
    out, depth, cur = [], 0, ""
    for ch in s:
        if ch in "([":
            depth += 1
        elif ch in ")]":
            depth -= 1
        if ch == sep and depth == 0:
            out.append(cur)
            cur = ""
        else:
            cur += ch
    return out + [cur]


def parse_set(s):
    """program set text -> (sympy set, exact?)"""
    s = s.replace(" ", "")
    if s == "ALLREALS":
        return R, True
    if s == "NOREALNUMBERS":
        return EMPTY, True
    m = re.fullmatch(r"ALLREALS,X≠(.*)", s)
    if m:
        vals = [pnum(t) for t in split0(m.group(1), ",")]
        return R - sp.FiniteSet(*[v for v, _ in vals]), all(e for _, e in vals)
    out, exact = EMPTY, True
    for part in split0(s, "U"):
        if len(part) < 5 or part[0] not in "[(" or part[-1] not in "])":
            raise ValueError(f"bad set text {s!r}")
        ends = split0(part[1:-1], ",")
        if len(ends) != 2:
            raise ValueError(f"bad set text {s!r}")
        a, ea = pnum(ends[0])
        b, eb = pnum(ends[1])
        exact = exact and ea and eb
        out = out | sp.Interval(a, b, part[0] == "(", part[-1] == ")")
    return out, exact


TRANS = standard_transformations + (implicit_multiplication,)


def parse_expr_text(s):
    t = s.replace(" ", "").replace("√(", "sqrt(").replace("²", "**2").replace("³", "**3").replace("^", "**")
    t = t.replace("X", "x")
    if re.search(r"[^0-9x+\-*/().sqrt]", t):
        raise ValueError(f"bad expression text {s!r}")
    # explicit products: 8x, x(, )x, )(, 2(, xsqrt(, 2sqrt(, )sqrt(
    t = re.sub(r"(?<=[0-9x)])(?=[x(]|sqrt)", "*", t)
    t = t.replace("sqrt*(", "sqrt(")
    return parse_expr(t, local_dict={"x": x, "sqrt": sp.sqrt}, transformations=standard_transformations)


def set_close(a, b):
    """approximate set equality for decimals: compare boundary points"""
    def pts(S):
        return sorted(float(p) for p in S.boundary) if S not in (EMPTY,) else []
    pa, pb = pts(a), pts(b)
    return len(pa) == len(pb) and all(abs(u - v) < 1e-5 for u, v in zip(pa, pb))


# ----------------------------------------------------------------------------- running
def answers(m):
    """list of (title, [content rows]) for each ANSWER:/WHY: screen sequence"""
    out, cur = [], None
    for kind, detail, lines in m.events:
        top = lines[0].strip() if lines else ""
        if cur is None and top in ("ANSWER:", "WHY:"):
            cur = (top, [])
            pages = []
        if cur is not None:
            if not pages or pages[-1] != lines:
                pages.append(lines)
            if kind == "key" and detail != "ENTER":
                rows = []
                for i, p in enumerate(pages):
                    if i and pages[i - 1][9].strip() != "ENTER=MORE":
                        continue
                    rows += [r for r in (p[1:8] if i == 0 else p[0:8])]
                rows = [r for r in rows if r.strip() and r.strip() != "ENTER=MORE"]
                out.append((cur[0], rows))
                cur = None
    return out


def split_answer(rows):
    text = "".join(r.rstrip() for r in rows)
    lab = r"(D\((?:F\+G|F-G|FG|F/G|G/F|G-F)\)=|\((?:F\+G|F-G|FG|F/G|G/F|G-F)\)\([^=]*?\)=|NO FORMULA: F OR G IS)"
    parts = re.split(lab, text)
    res, pre = {}, parts[0]
    for i in range(1, len(parts), 2):
        res[parts[i]] = parts[i + 1]
    return res, pre


class Case:
    """one student session: a list of rounds.  Round 0 starts from the main menu; a later round
    is reached with 4:SAME F,G (new question, same f and g) or 1:AGAIN (same question type,
    new combination, new f and g; typed graphs stay saved)."""

    def __init__(self, seed):
        self.rng = random.Random(seed)
        self.seed = seed
        g = Gen(self.rng)
        self.g = g
        self.state = {}
        r = self.rng
        self.lists = None
        if r.random() < 0.15:
            # graphs already saved from an earlier run (e.g. the Example 1.3 graphs)
            fp = [(-6, 2), (-3, -1), (1, 3), (4, 0), (7, 3)]
            gp = [(-5, 3), (-2, 0), (1, 0), (3, 2), (6, -1)]
            self.state["F"] = ([(sp.Integer(a), sp.Integer(b)) for a, b in fp], True, True)
            self.state["G"] = ([(sp.Integer(a), sp.Integer(b)) for a, b in gp], True, True)
            self.lists = {"ʟGFX": [a for a, _ in fp], "ʟGFY": [b for _, b in fp], "ʟGFC": [1, 1],
                          "ʟGGX": [a for a, _ in gp], "ʟGGY": [b for _, b in gp], "ʟGGC": [1, 1]}
        f, gg = self.new_pair()
        ask = self.pick_ask()
        self.rounds = [dict(how="start", f=f, g=gg, ask=ask, combo=r.choice(COMBOS), x0=self.pick_x(ask, f, gg))]
        while len(self.rounds) < 4 and r.random() < 0.45:
            how = r.choice(["same", "same", "again"])
            if how == "same":
                f, gg, ask = f, gg, self.pick_ask()
            else:
                f, gg = self.new_pair()
            self.rounds.append(dict(how=how, f=f, g=gg, ask=ask, combo=r.choice(COMBOS),
                                    x0=self.pick_x(ask, f, gg)))
        self.after = r.choices(["home", "why", "again-exit"], [55, 35, 10])[0]
        # the typed x is chosen once, so the actions are reproducible
        for rd in self.rounds:
            rd["xtext"] = self.g.typed(rd["x0"], None) if rd["x0"] is not None else None

    def new_pair(self):
        r = self.rng
        pair = (None, None)
        if r.random() < 0.12:
            pair = ("root", "root")  # two radicals: same / different radicands
        elif r.random() < 0.08:
            pair = ("graph", "words")
        f = gen_fn(self.g, "F", self.state, pair[0])
        same = pair[1] == "root" and r.random() < 0.4
        gg = gen_fn(self.g, "G", self.state, pair[1], inside=(f.A, f.B) if same else None)
        return f, gg

    def pick_ask(self):
        return self.rng.choices(["domain", "value", "formula"], [40, 35, 25])[0]

    def pick_x(self, ask, f, gg):
        r = self.rng
        if ask != "value":
            return None
        cands = [sp.Integer(r.randint(-8, 8)), self.g.num(-8, 8, frac=0.5)]
        for fn in (f, gg):
            for S in (fn.zeros, fn.dom):
                try:
                    bd = [p for p in S.boundary if p.is_finite and p.is_rational]
                except Exception:
                    bd = []
                if isinstance(S, sp.FiniteSet):
                    bd += [p for p in S if p.is_rational]
                cands += bd[:4]
        cands = [c for c in cands if sp.Rational(c).q <= 1000]  # what a quiz would ask
        return sp.Rational(r.choice(cands))

    @property
    def questions(self):
        return [(rd["ask"], rd["combo"], rd["x0"]) for rd in self.rounds]

    def actions(self):
        acts = ["ENTER", "k1"]
        for i, rd in enumerate(self.rounds):
            ck = f"k{COMBOS.index(rd['combo']) + 1}"
            ak = {"domain": "k1", "value": "k2", "formula": "k3"}[rd["ask"]]
            if rd["how"] == "start":
                acts += [ak, ck] + rd["f"].keys + rd["g"].keys
            elif rd["how"] == "same":
                acts += ["k4", ak, ck]  # 4:SAME F,G  NEW QUESTION
            else:
                acts += ["k1", ck] + rd["f"].keys + rd["g"].keys  # 1:AGAIN keeps the question type
            if rd["ask"] == "value":
                acts += [f"t:{rd['xtext']}"]
            acts += ["ENTER"] * 4  # turns ENTER=MORE pages; ignored by the footer menu
        if self.after == "why":
            acts += ["k3", "ENTER", "ENTER", "ENTER", "k2"]
        elif self.after == "again-exit":
            acts += ["k1", "CLEAR", "CLEAR"]
        else:
            acts += ["k2"]
        return acts + ["CLEAR"] * 4

    def describe(self):
        parts = [f"seed={self.seed}"]
        for rd in self.rounds:
            parts.append(f"[{rd['how']}: f={rd['f'].text} g={rd['g'].text} {rd['ask']} {rd['combo']} x={rd['x0']}]")
        return " ".join(parts) + f" after={self.after}"


PROGS = None


def check_question(f, g, ask, combo, x0, title, rows):
    """returns list of (category, message) problems"""
    probs = []
    if title != "ANSWER:":
        return [("flow", f"expected ANSWER:, got {title}")]
    parts, pre = split_answer(rows)
    if pre.strip():
        probs.append(("format", f"text before the first label: {pre!r}"))
    other = {"F/G": "G/F", "G/F": "F/G"}.get(combo)

    def check_dom(K):
        lab = f"D({K})="
        if lab not in parts:
            probs.append(("missing", f"no {lab} line in {rows}"))
            return
        txt = parts[lab]
        want = combo_domain(f, g, K)
        if "CAN NOT DO" in txt:
            probs.append(("domain", f"{lab}{txt} (oracle {want})"))
            return
        try:
            got, exact = parse_set(txt)
        except ValueError as e:
            probs.append(("parse", str(e)))
            return
        if exact:
            if sp.simplify(sp.SymmetricDifference(got, want)) != EMPTY and got != want:
                probs.append(("domain", f"{lab}{txt} but oracle {want}"))
        else:
            if set_close(got, want):
                probs.append(("inexact-domain", f"{lab}{txt} (decimal ends; oracle {want})"))
            else:
                probs.append(("domain", f"{lab}{txt} but oracle {want}"))

    if ask == "domain":
        check_dom(combo)
        if other:
            check_dom(other)
    elif ask == "value":
        labs = [k for k in parts if k.startswith(f"({combo})(")]
        if not labs:
            probs.append(("missing", f"no ({combo})(x)= line in {rows}"))
            return probs
        lab = labs[0]
        xs = lab[len(combo) + 3:-2]
        try:
            xv = sp.Rational(xs)
            if xv != x0:
                probs.append(("value", f"label shows x={xs}, typed {x0}"))
        except Exception:
            probs.append(("format", f"x in label not exact: {lab}"))
        txt = parts[lab].strip()
        want = combo_value(f, g, combo, x0)
        if want[0] == "undef":
            if txt != "UNDEFINED":
                probs.append(("value", f"{lab}{txt} but oracle UNDEFINED"))
        elif want[0] == "unk":
            if txt != "CAN NOT TELL FROM WORDS":
                probs.append(("value", f"{lab}{txt} but oracle: not given (words)"))
        else:
            wv = want[1]
            if txt.startswith("ABOUT "):
                try:
                    approx = float(txt[6:])
                    if abs(approx - float(wv)) < 1e-5 * max(1, abs(float(wv))):
                        probs.append(("inexact-value", f"{lab}{txt} (exact {wv})"))
                    else:
                        probs.append(("value", f"{lab}{txt} but oracle {wv}"))
                except ValueError:
                    probs.append(("parse", f"{lab}{txt}"))
            else:
                try:
                    gv = parse_expr_text(txt)
                    if sp.N(gv - wv, 40) != 0 and abs(sp.N(gv - wv, 40)) > 1e-25:
                        probs.append(("value", f"{lab}{txt} = {gv} but oracle {wv}"))
                except Exception as e:
                    probs.append(("value", f"{lab}{txt} not a number ({e}); oracle {wv}"))
    else:  # formula
        check_dom(combo)
        lab = f"({combo})(X)="
        if not (f.formula and g.formula):
            if "NO FORMULA: F OR G IS" not in parts:
                probs.append(("formula", f"graph/words but no NO FORMULA line: {rows}"))
            return probs
        if lab not in parts:
            probs.append(("missing", f"no {lab} line in {rows}"))
            return probs
        txt = parts[lab]
        dom = combo_domain(f, g, combo)
        try:
            gx = parse_expr_text(txt) if txt not in ("UNDEFINED",) else None
        except Exception as e:
            probs.append(("formula", f"{lab}{txt} unparsable: {e}"))
            return probs
        if gx is None:
            if dom != EMPTY:
                probs.append(("formula", f"{lab}UNDEFINED but domain {dom}"))
            return probs
        if re.search(r"\d\.\d", txt):
            probs.append(("inexact-formula", f"{lab}{txt} has a decimal"))
        want = combo_sym(f, g, combo)
        pts = sample_points(dom)
        for p in pts:
            a, b = combo_value(f, g, combo, p), gx.subs(x, p)
            if a[0] != "val":
                continue
            try:
                diff = sp.N(b - a[1], 40)
                bad = (not diff.is_real) or abs(diff) > 1e-20
            except Exception:
                bad = True
            if bad:
                probs.append(("formula", f"{lab}{txt} at x={p}: {b} but oracle {a[1]} (want {want})"))
                break
    return probs


def sample_points(S, k=6):
    out = []
    for p in [sp.Rational(n, d) for d in (1, 3, 7) for n in range(-20 * d, 20 * d + 1, d * 2 + 1)]:
        if S.contains(p) == sp.true:
            out.append(p)
    random.Random(len(out)).shuffle(out)
    return out[:k]


def run_case(case, verbose=False):
    global PROGS
    if PROGS is None:
        PROGS = load_programs(SRC)
    lists = {k: [D(str(v)) for v in vals] for k, vals in (case.lists or {}).items()}
    m = Machine(PROGS, persistent_lists=lists)
    acts = case.actions()
    try:
        res = m.run(acts)
    except TIError as e:
        return [("crash", str(e))], m, acts
    probs = []
    if res[0] != "stop":
        probs.append(("flow", f"run ended {res}"))
    if m.problems:
        probs.append(("screen", "; ".join(m.problems[:3])))
    ans = [a for a in answers(m)]
    main = [a for a in ans if a[0] == "ANSWER:"]
    if len(main) < len(case.questions):
        probs.append(("flow", f"{len(main)} answer screens for {len(case.questions)} questions"))
        return probs, m, acts
    for rd, (title, rows) in zip(case.rounds, main):
        probs += check_question(rd["f"], rd["g"], rd["ask"], rd["combo"], rd["x0"], title, rows)
    if case.after == "why" and not any(a[0] == "WHY:" for a in ans):
        probs.append(("flow", "WHY page did not show"))
    return probs, m, acts


def show_one(seed):
    case = Case(seed)
    probs, m, acts = run_case(case)
    print(case.describe())
    print("actions:", " ".join(acts))
    for kind, detail, lines in m.events:
        if kind == "key" or kind == "input":
            print(f"--- {kind} {detail}")
            for ln in lines:
                if ln.strip():
                    print("   |" + ln)
    for c, msg in probs:
        print(f"[{c}] {msg}")


def resume(m, more):
    """continue a halted run with more actions (the simulator stops at an Input or a key wait
    before the statement completes, so running the same statement again is exact)"""
    m.actions.extend(more)
    m.idle = 0
    try:
        steps = 0
        while m.frames:
            steps += 1
            if steps > 200000:
                return ("step_limit", None)
            f = m.frames[-1]
            m.load(f.name)
            if f.pc >= len(m.src[f.name]):
                m.frames.pop()
                continue
            m.exec(f)
        return ("done", None)
    except Halt as h:
        return h.args[0]


KNOWN_SHARED = ("HAPTS:7: screen scrolled",)


class FastMachine(Machine):
    """halts at once when a key is needed and none is queued (the plain Machine spins 3000 polls)"""

    def getkey(self):
        a = self.next_action()
        if a is None:
            raise Halt(("waiting_key", None))
        return super().getkey()


def at_main_menu(m):
    return len(m.frames) >= 2 and m.frames[-1].name == "HAKEY" and m.frames[-2].name == "HPCANS"


def monkey(n, seed0):
    """random keys from main menu 1: menu digits, CLEAR, ENTER, and plausible typed numbers;
    every run must stay error-free, keep the screen clean, and end at Stop after CLEARs."""
    global PROGS
    if PROGS is None:
        PROGS = load_programs(SRC)
    bad, sigs, shared = 0, {}, 0
    for i in range(n):
        r = random.Random(seed0 * 7919 + i)
        m = FastMachine(PROGS)
        acts = ["ENTER", "k1"]
        try:
            res = m.run(list(acts))
            for _ in range(80):
                if res[0] == "waiting_input":
                    prompt = res[1][1]
                    if "END=" in prompt and r.random() < 0.2:
                        t = r.choice(["I", "-I", "⁻I"])
                    else:
                        t = r.choice(["", "", "0", "1", "-1", "-", "⁻", "2", "-3", "1/2", "-5/4", "7", "12",
                                      "0.5", "(-2/3)", "4", "-8", "3"])
                    nxt = "t:" + t
                elif res[0] == "waiting_key" and at_main_menu(m):
                    nxt = r.choices(["k1", "CLEAR"], [80, 20])[0]  # stay inside main menu 1 (or quit)
                elif res[0] == "waiting_key":
                    nxt = r.choices(["k1", "k2", "k3", "k4", "k5", "k6", "k7", "k8", "k9", "k0", "CLEAR",
                                     "ENTER"], [12, 12, 10, 10, 8, 6, 5, 5, 2, 2, 8, 6])[0]
                else:
                    break
                acts.append(nxt)
                res = resume(m, [nxt])
            for _ in range(60):  # leave: CLEAR at every menu; an Input cannot be left, so type 1
                if res[0] == "stop":
                    break
                scr = " ".join(m.lines())
                nxt = "t:1" if res[0] == "waiting_input" else "ENTER" if "ENTER=MORE" in scr else \
                    "k1" if "BRACKETS?" in scr else "CLEAR"  # (shared HAOUT / HAIVL ignore CLEAR there)
                acts.append(nxt)
                res = resume(m, [nxt])
        except TIError as e:
            res = ("error", str(e))
        own = [p for p in m.problems if not p.startswith(KNOWN_SHARED)]
        if res[0] == "stop" and m.problems and not own:
            shared += 1  # only the known shared-helper issue (reported, not in this group's files)
            continue
        if res[0] != "stop" or own:
            bad += 1
            where = m.where() if res[0] != "stop" else ""
            sig = (res[0], where, tuple(sorted({p.split(": ")[0] + ": " + p.split(": ")[1][:30]
                                                for p in m.problems})))
            if sig not in sigs:
                sigs[sig] = 0
                print("MONKEY", res, where, m.problems[:3])
                print("   last screen:", " | ".join(ln for ln in m.lines() if ln.strip()))
                print("   actions:", " ".join(acts))
            sigs[sig] += 1
    print(f"monkey: {n} random sessions, {n - bad - shared} clean, {bad} with problems, "
          f"{shared} with only the known shared HAPTS scroll (re-asked HOW MANY POINTS=)")
    for sig, k in sorted(sigs.items(), key=lambda t: -t[1]):
        print(f"   {k:4d} x {sig}")
    return bad


# ----------------------------------------------------------------------------- helper-level fuzz
# HAOPS uses HAFDOM mode 0 and HAFZERO at level 0; the composition solver also uses HAFDOM mode 1
# (where P ≤ f(x) ≤ Q) and mode 2 (domain of f(g(x))) and HAFZERO at other levels.  These run
# the helpers from a small driver program (as tools/tests/test_helpers.py does) and compare
# with an oracle built only from exact values: the answer set is found by testing f at every
# critical point and at one point inside each gap between them.

def tinum(v):
    """a number as TI-BASIC source"""
    if v == sp.oo:
        return "ᴇ99"
    if v == -sp.oo:
        return "⁻ᴇ99"
    t = ttext(v)
    return t.replace("-", "⁻")


def level_points(fn, c):
    """finite candidate x's where fn may reach the level c, or where its domain has an end"""
    pts = set()
    if isinstance(fn, Rational):
        for cs in ([a - c * b for a, b in zip([0] * (len(fn.den) - len(fn.num)) + fn.num,
                                               [0] * (len(fn.num) - len(fn.den)) + fn.den)], fn.den):
            rr = real_roots(cs)
            if rr:
                pts |= set(rr)
    elif isinstance(fn, Root):
        if fn.A != 0:
            pts.add(-fn.B / fn.A)
            if fn.K != 0:
                sv = (c - fn.C) / fn.K
                if sv >= 0:
                    pts.add((sv ** 2 - fn.B) / fn.A)
    elif isinstance(fn, Graph):
        for (a, ya), (b2, yb) in zip(fn.pts, fn.pts[1:]):
            if (ya - c) * (yb - c) < 0:
                pts.add(a + (c - ya) * (b2 - a) / (yb - ya))
        pts |= {a for a, _ in fn.pts}
    else:
        pts |= {p for p in fn.dom.boundary if p.is_finite}
        pts |= {p for p in fn.zeros.boundary if p.is_finite} if fn.zeros != EMPTY else set()
    return {p for p in pts if p.is_real and p.is_finite}


def probe_between(a, b):
    if a == -sp.oo and b == sp.oo:
        return sp.Integer(0)
    if a == -sp.oo:
        return sp.floor(b) - 1
    if b == sp.oo:
        return sp.ceiling(a) + 1
    m = sp.Rational(round(float((a + b) / 2) * 10 ** 6), 10 ** 6)
    return m if a < m < b else (a + b) / 2


def set_from_test(pts, test):
    pts = sorted(pts, key=float)
    S = EMPTY
    edges = [-sp.oo] + pts + [sp.oo]
    for a, b in zip(edges, edges[1:]):
        if test(probe_between(a, b)):
            S = S | sp.Interval.open(a, b)
    for p in pts:
        if test(p):
            S = S | sp.FiniteSet(p)
    return S


def in_dom(fn, v):
    return fn.value(v)[0] != "undef"


def band_oracle(f, lo, hi, flags):
    def test(v):
        r = f.value(v)
        if r[0] != "val":
            return False
        y = r[1]
        okl = lo == -sp.oo or (sign(y - lo) >= 0 if flags & 1 else sign(y - lo) > 0)
        okh = hi == sp.oo or (sign(y - hi) <= 0 if flags & 2 else sign(y - hi) < 0)
        return bool(okl and okh)
    pts = set()
    for c in (lo, hi):
        if c.is_finite:
            pts |= level_points(f, c)
    pts |= level_points(f, 0)
    return set_from_test(pts, test)


def comp_oracle(f, g):
    """domain of f(g(x)): x in Dg and g(x) in Df"""
    def test(v):
        r = g.value(v)
        return r[0] == "val" and in_dom(f, r[1])
    pts = level_points(g, 0)
    for b2 in f.dom.boundary if f.dom not in (R, EMPTY) else []:
        if b2.is_finite:
            pts |= level_points(g, b2)
    return set_from_test(pts, test)


def zero_oracle(f, c):
    """closure of {x in Df : f(x) = c}, as sorted (a, b) stretches"""
    def test(v):
        r = f.value(v)
        return r[0] == "val" and is_zero(r[1] - c)
    S = set_from_test(level_points(f, c) | {p for p in f.dom.boundary if p.is_finite}, test)
    S = sp.closure(S) if hasattr(sp, "closure") else S.closure
    out = []
    for part in (S.args if isinstance(S, sp.Union) else [S]):
        if part == EMPTY:
            continue
        if isinstance(part, sp.FiniteSet):
            out += [(p, p) for p in part]
        else:
            out.append((part.start, part.end))
    return sorted(out, key=lambda t: float(t[0]) if t[0].is_finite else -1e300)


SHOW_ZEROS = ['"NONE"→Str0', "For(I,1,C)", "ʟFZL(I)→θ", "prgmHAFRAC", "Str9→Str1",
              "If ʟFZL(I)≠ʟFZR(I)", "Then", "ʟFZR(I)→θ", "prgmHAFRAC", '"["+Str1+","+Str9+"]"→Str1', "End",
              "If I=1", "Str1→Str0", "If I>1", 'Str0+","+Str1→Str0', "End"]


def helper_case(seed):
    rng = random.Random(seed)
    g = Gen(rng)
    state = {}
    shapes = ["line", "quad", "frac", "recip", "root", "frac2", "graph", "words"]
    f = gen_fn(g, "F", state, rng.choice(shapes))
    gg = gen_fn(g, "G", state, rng.choice([s2 for s2 in shapes if s2 != "words"]))
    lo = rng.choice([-sp.oo, sp.Integer(rng.randint(-4, 3)), sp.Rational(rng.randint(-8, 6), 2)])
    hi = rng.choice([sp.oo, lo + rng.choice([0, 1, 2, 3, sp.Rational(1, 2)])]) if lo != -sp.oo else \
        rng.choice([sp.oo, sp.Integer(rng.randint(-3, 4))])
    flags = rng.randint(0, 3)
    level = rng.choice([0, 0, rng.randint(-3, 3)])
    if f.kind == "words":
        level = 0
    return f, gg, lo, hi, flags, sp.Integer(level)


def run_helper_case(seed):
    global PROGS
    if PROGS is None:
        PROGS = load_programs(SRC)
    f, gg, lo, hi, flags, level = helper_case(seed)
    drv = ["SetUpEditor ʟGFX,ʟGFY,ʟGFC,ʟGGX,ʟGGY,ʟGGC", "SetUpEditor",
           "1→N", "0→O", '"F"→Str9', "prgmHAFUNC", "2→N", "0→O", '"G"→Str9', "prgmHAFUNC", "prgmHAANS",
           "1→N", "prgmHAFSTR", '"TEXT:"+Str5→Str9', "prgmHAOUT"]
    if f.kind != "words":
        drv += ["1→θ", "prgmHADOM", "1→N", "1→O", f"{tinum(lo)}→P", f"{tinum(hi)}→Q", f"{flags}→R",
                "prgmHAFDOM", "θ→M", "9→θ", "prgmHADOM", '"BAND:"+Str6→Str9', "prgmHAOUT"]
    drv += ["1→θ", "prgmHADOM", "2→N", "2→O", "1→P", "prgmHAFDOM", "θ→M", "9→θ", "prgmHADOM",
            '"COMP:"+Str6→Str9', "If M=0", '"COMP:NOT SUPPORTED"→Str9', "prgmHAOUT",
            "1→N", f"{tinum(level)}→O", "0→P", "prgmHAFZERO", "R→C"] + SHOW_ZEROS + \
           ['"ZERO:"+Str0→Str9', "prgmHAOUT", '"END:"→Str9', "prgmHAOUT",
            '"1:END"→Str9', "1→θ", "prgmHAEND", "Stop"]
    progs = dict(PROGS)
    progs["DRVOPS"] = drv
    m = Machine(progs)
    acts = f.keys + gg.keys + ["ENTER"] * 6 + ["k1"] + ["CLEAR"] * 3
    probs = []
    try:
        res = m.run(acts, start="DRVOPS")
    except TIError as e:
        return [("crash", str(e))], (f, gg, lo, hi, flags, level), acts
    if res[0] != "stop":
        probs.append(("flow", f"ended {res}"))
    if m.problems:
        probs.append(("screen", "; ".join(m.problems[:3])))
    ans = answers(m)
    if not ans:
        return probs + [("flow", "no answer screen")], (f, gg, lo, hi, flags, level), acts
    text = "".join(r.rstrip() for r in ans[0][1])
    parts = dict(re.findall(r"(TEXT|BAND|COMP|ZERO|END):(.*?)(?=(?:TEXT|BAND|COMP|ZERO|END):|$)", text))

    def cmp_set(name, txt, want):
        try:
            got, exact = parse_set(txt)
        except ValueError as e:
            probs.append(("parse", f"{name}: {e}"))
            return
        if exact:
            if got != want and sp.simplify(sp.SymmetricDifference(got, want)) != EMPTY:
                probs.append((name, f"{txt} but oracle {want}"))
        elif set_close(got, want):
            probs.append(("inexact-domain", f"{name}: {txt}"))
        else:
            probs.append((name, f"{txt} but oracle {want}"))

    # text
    if f.kind in ("line", "quad", "frac", "recip", "frac2", "root"):
        try:
            tx = parse_expr_text(parts.get("TEXT", ""))
            for v in sample_points(f.dom):
                a, b2 = f.value(v), tx.subs(x, v)
                if a[0] == "val" and abs(sp.N(b2 - a[1], 30)) > 1e-20:
                    probs.append(("text", f"HAFSTR {parts.get('TEXT')} at {v}: {b2} but f={a[1]}"))
                    break
        except Exception as e:
            probs.append(("text", f"HAFSTR {parts.get('TEXT')!r}: {e}"))
    elif parts.get("TEXT", "") != "":
        probs.append(("text", f"HAFSTR of a {f.kind} gave {parts.get('TEXT')!r}"))
    if f.kind != "words":
        cmp_set("band", parts.get("BAND", ""), band_oracle(f, lo, hi, flags))
    ctxt = parts.get("COMP", "")
    if ctxt == "NOT SUPPORTED":
        probs.append(("comp-unsupported", f"f={f.text} g={gg.text}"))
    else:
        cmp_set("comp", ctxt, comp_oracle(f, gg))
    # zeros at a level
    want = zero_oracle(f, level)
    ztxt = parts.get("ZERO", "")
    got = []
    if ztxt != "NONE":
        for item in split0(ztxt, ","):
            if item.startswith("["):
                a2, b2 = split0(item[1:-1], ",")
                got.append((pnum(a2)[0], pnum(b2)[0]))
            else:
                v = pnum(item)[0]
                got.append((v, v))
    cl = f.dom.closure if f.dom != EMPTY else EMPTY
    gset = EMPTY
    for a2, b2 in got:
        gset = gset | (sp.FiniteSet(a2) if a2 == b2 else sp.Interval(a2, b2))
    gset = gset & cl
    got = []
    for part in (gset.args if isinstance(gset, sp.Union) else [gset]):
        if part == EMPTY:
            continue
        got += [(p2, p2) for p2 in part] if isinstance(part, sp.FiniteSet) else [(part.start, part.end)]
    got.sort(key=lambda t: float(t[0]) if t[0].is_finite else -1e300)
    if [tuple(map(float, t)) for t in got] != [tuple(map(float, t)) for t in want] and \
            not (len(got) == len(want) and all(abs(float(a2) - float(c2)) < 1e-5 and abs(float(b2) - float(d2)) < 1e-5
                                              for (a2, b2), (c2, d2) in zip(got, want))):
        probs.append(("zeros", f"HAFZERO level {level}: {ztxt} but oracle {want}"))
    return probs, (f, gg, lo, hi, flags, level), acts


def helpers_fuzz(n, seed0):
    stats, bad, shown = {}, 0, 0
    for i in range(n):
        probs, info, acts = run_helper_case(seed0 * 100000 + i)
        for c in sorted({c for c, _ in probs}):
            stats[c] = stats.get(c, 0) + 1
        real = [p for p in probs if not p[0].startswith("inexact")]
        if real:
            bad += 1
            if shown < 25:
                shown += 1
                f, gg, lo, hi, flags, level = info
                print(f"HELPER MISMATCH seed={seed0 * 100000 + i} f={f.text} g={gg.text} band=({lo},{hi},{flags}) "
                      f"level={level}")
                for c, msg in probs:
                    print(f"   [{c}] {msg}")
                print("   actions:", " ".join(acts))
    print(f"helpers: {n} cases, {n - bad} agree with the oracle, {bad} mismatches; categories: {stats}")
    return bad


def main():
    if "--helpers" in sys.argv:
        k = sys.argv.index("--helpers")
        return 1 if helpers_fuzz(int(sys.argv[k + 1]), int(sys.argv[k + 2]) if len(sys.argv) > k + 2 else 1) else 0
    if "--monkey" in sys.argv:
        k = sys.argv.index("--monkey")
        return 1 if monkey(int(sys.argv[k + 1]), int(sys.argv[k + 2]) if len(sys.argv) > k + 2 else 1) else 0
    if "--seed" in sys.argv:
        show_one(int(sys.argv[sys.argv.index("--seed") + 1]))
        return 0
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    n = int(args[0]) if args else 600
    seed0 = int(args[1]) if len(args) > 1 else 1
    verbose = "-v" in sys.argv
    stats, shown, noted = {}, 0, 0
    bad_cases = 0
    for i in range(n):
        case = Case(seed0 * 100000 + i)
        probs, m, acts = run_case(case)
        cats = sorted({c for c, _ in probs})
        for c in cats:
            stats[c] = stats.get(c, 0) + 1
        real = [p for p in probs if not p[0].startswith("inexact")]
        if real:
            bad_cases += 1
        if real and shown < 40 or verbose and probs and not real and noted < 40:
            if real:
                shown += 1
            else:
                noted += 1
            print("MISMATCH" if real else "NOTE", case.describe())
            for c, msg in probs:
                print(f"   [{c}] {msg}")
            print("   actions:", " ".join(acts))
    print(f"{n} cases, {n - bad_cases} agree with the oracle, {bad_cases} mismatches; categories: {stats}")
    return 1 if bad_cases else 0


if __name__ == "__main__":
    sys.exit(main())
