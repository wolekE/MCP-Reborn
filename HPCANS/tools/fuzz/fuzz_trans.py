#!/usr/bin/env python3
"""
Randomized differential testing of the transformations solver (main menu 4, program HATRANS
with its helpers HAABCK, HAEQN, HAPTXT).

Every case is a random problem typed from the main menu exactly as a student would press keys:
  * 1:LIST THE CHANGES  y = A*f(Bx+C)+K with negative / fractional / zero C and K, A or B = 1 or -1,
    ENTER defaults (A, B -> 1; C, K -> 0), a lone minus for -1 (either minus key), "-(4/3)",
    decimals, the signs and letters a beginner copies from the paper (C=+1, K=+3, B=3X, -X, X/2),
    A = 0 or B = 0 typed first (refused, the screen drawn again);
  * 2:NEW POINTS: one point (1:NEXT PT chains), or all corners of a graph / table (typed in any
    order, or the saved graph), solid / hollow end dots, flat pieces, extreme values at ends;
  * 3:NEW DOMAIN AND RANGE: both / domain only / range only, any brackets, infinite ends,
    one-point intervals, ends typed in the wrong order;
  * 4:WRITE THE EQUATION: random step sequences (reflections, stretches, compressions, 5:LEFT
    6:RIGHT 7:UP 8:DOWN), zero / ENTER amounts, a minus typed on a size;
  * WHY pages (factoring, h = -c/b), reached through 3:SAME EQ.
  Sessions chain problems with 1:AGAIN, 3:SAME EQ (same equation, another question: also after
  WRITE), 2:HOME, false starts ended with CLEAR at every submenu, and a saved graph kept between
  sessions, so state left by one problem is exercised.  --wide adds long numbers (HAFRAC's
  documented decimal fallback, split lines) and 9-12 corner graphs.

Oracle (independent of the TI code; Python Fractions + sympy):
  * changes: from a, b, h = -c/b, k by the class rules (Cram 5.2-5.5), in class order, after the
    factored equation (must equal a*f(b*x+c)+k as sympy expressions, f symbolic, and have the shape
    a*f(b(x-h))+k) and before the A= B= H= K= line; the WHY page equations are checked the same way;
  * points: (x, y) -> ((x-c)/b, a*y+k), each line "OLD TO NEW" in the order of the original points;
    the rules NEW X = (1/b)x + h and NEW Y = a*y + k;
  * graph D, R: the set of x of the corner-point graph and the set of its y values (union of the
    segments' value intervals, with hollow ends left out) pushed through the rules exactly;
  * D/R: the interval's end points pushed through x -> (x-c)/b, y -> a*y+k, reordered, the bracket
    travels with its number, infinity flips sign under a reflection;
  * write equation: each step applied to the sympy expression of the current function
    (reflect x: -y, reflect y: x -> -x, vertical t: t*y, horizontal stretch t: x -> x/t,
    right t: x -> x-t, up t: y+t); both printed forms must equal it, the factored form must be
    a*f(b*(x-h))+k in shape, and the A= B= H= K= line must match.

Run from tools/:   python3 fuzz/fuzz_trans.py [-n CASES] [-s SEED] [--kind changes] [-v]
"""

import argparse
import random
import re
import sys
import time
from fractions import Fraction as Fr
from pathlib import Path

import sympy as sp

HERE = Path(__file__).resolve().parent
TOOLS = HERE.parent
sys.path.insert(0, str(TOOLS))
from tibasic import D, Machine, TIError, load_programs  # noqa: E402

SRC = TOOLS.parent / "src"
INF = Fr(10) ** 99
XS = sp.Symbol("x")
FS = sp.Function("f")

FOOT = "1:AGAIN  2:HOME  3:SAME EQ"
FOOT_PT = "1:NEXT PT 2:HOME 3:SAME EQ"


# ============================================================================ text formats
def ft(v):
    """exact text of a number the way the class (and HAFRAC) writes it"""
    if v >= INF:
        return "INF"
    if v <= -INF:
        return "-INF"
    v = Fr(v)
    if v.denominator == 1:
        return str(v.numerator)
    if not shown_exact(v):
        # HELPERS.md: no n/d with d <= 9999 and d^2*max(1,|x|) <= 1E8 -> a 6-place decimal
        a = round(abs(v) * 10 ** 6)
        ip, fp = divmod(a, 10 ** 6)
        txt = str(ip) + ("." + f"{fp:06d}".rstrip("0") if fp else "")
        return ("-" if v < 0 else "") + txt
    return f"{v.numerator}/{v.denominator}"


def shown_exact(v):
    """HAFRAC prints v as a fraction (documented limits) rather than a 6-place decimal"""
    v = Fr(v)
    return v.denominator <= 9999 and v.denominator ** 2 * max(1, abs(v)) <= 10 ** 8


def pt(x, y):
    return f"({ft(x)},{ft(y)})"


def ivl(lo, hi, lc, rc):
    """an interval in the class notation (HADOM's rendering of one interval)"""
    if lo <= -INF and hi >= INF:
        return "ALL REALS"
    return ("[" if lc and lo > -INF else "(") + ft(lo) + "," + ft(hi) + ("]" if rc and hi < INF else ")")


def change_lines(a, b, c, k):
    """the transformations of y = a f(bx+c) + k in class order (Cram 5.2-5.5)"""
    h = -c / b
    out = []
    if a < 0:
        out.append("REFLECT OVER X-AXIS")
    if abs(a) > 1:
        out.append(f"VERT STRETCH BY {ft(abs(a))}")
    elif abs(a) < 1:
        out.append(f"VERT COMPRESS BY {ft(abs(a))}")
    if b < 0:
        out.append("REFLECT OVER Y-AXIS")
    if abs(b) > 1:
        out.append(f"HORIZ COMPRESS BY {ft(1 / abs(b))}")
    elif abs(b) < 1:
        out.append(f"HORIZ STRETCH BY {ft(1 / abs(b))}")
    if h > 0:
        out.append(f"RIGHT {ft(h)}")
    elif h < 0:
        out.append(f"LEFT {ft(-h)}")
    if k > 0:
        out.append(f"UP {ft(k)}")
    elif k < 0:
        out.append(f"DOWN {ft(-k)}")
    return out or ["NO CHANGE"]


def abhk_line(a, b, h, k):
    return f"A={ft(a)}  B={ft(b)}  H={ft(h)}  K={ft(k)}"


def abhk_lines(a, b, h, k):
    """the A= B= H= K= line, split before H= when it does not fit on one row"""
    line = abhk_line(a, b, h, k)
    if len(line) <= 26:
        return [line]
    i = line.index("  H=")
    return [line[:i], line[i + 2:]]


def lin(m, q, var):
    """m*var+q written as the class writes a rule: X-1, 2Y-3, (1/2)X, -(1/2)X+2, -X"""
    if m == 1:
        s = var
    elif m == -1:
        s = "-" + var
    elif m.denominator == 1:
        s = f"{m.numerator}{var}"
    else:
        s = ("-" if m < 0 else "") + f"({abs(m).numerator}/{abs(m).denominator}){var}"
    if q > 0:
        s += "+" + ft(q)
    elif q < 0:
        s += "-" + ft(-q)
    return s


# ============================================================================ parsing printed equations
def to_sympy(text):
    """'Y=(-1/2)F(-2(X-2))+1' or '=5F(2X-6)-1' -> sympy expression in f and x"""
    s = text.strip()
    if s.startswith("Y="):
        s = s[2:]
    elif s.startswith("="):
        s = s[1:]
    if re.search(r"[^0-9XF()+\-/.]", s):
        raise ValueError(f"unexpected characters in {text!r}")
    s = s.replace("X", "x").replace("F(", "f(")
    # implicit multiplication: 2f(  )(  2x  )x  2(  x(
    s = re.sub(r"(?<=[0-9)x])(?=[fx(])", "*", s)
    s = s.replace("f*(", "f(")
    return sp.sympify(s, locals={"f": FS, "x": XS})


def same(e1, e2):
    return sp.expand(e1 - e2) == 0


def abhk(expr):
    """a, b, h, k of an expression a*f(b*x+c)+k"""
    atoms = [t for t in sp.preorder_traversal(expr) if isinstance(t, sp.Function) and t.func == FS]
    fa = atoms[0]
    arg = sp.expand(fa.args[0])
    b = arg.coeff(XS, 1)
    c = arg.subs(XS, 0)
    e = sp.expand(expr)
    a = e.coeff(fa)
    k = sp.expand(e - a * fa)
    return Fr(str(a)), Fr(str(b)), Fr(str(-c / b)), Fr(str(k))


NUM = r"-?\d+(?:/\d+)?"
PNUM = r"(?:-?\d+|\(-?\d+/\d+\))"


def factored_ok(text):
    """the factored form y = a f(b(x-h)) + k, written as the class writes it"""
    m = re.fullmatch(r"Y=(-|" + PNUM + r")?F\((.*)\)([+-]\d+(?:/\d+)?)?", text)
    if not m:
        return False
    inside = m.group(2)
    pats = [r"X", r"X[+-]\d+(?:/\d+)?", r"-X", r"-\(X[+-]\d+(?:/\d+)?\)",
            PNUM + r"X", PNUM + r"\(X[+-]\d+(?:/\d+)?\)"]
    if m.group(1) in ("1", "-1"):
        return False
    return any(re.fullmatch(p, inside) for p in pats)


def expanded_ok(text):
    m = re.fullmatch(r"=(-|" + PNUM + r")?F\((.*)\)([+-]\d+(?:/\d+)?)?", text)
    if not m:
        return False
    inside = m.group(2)
    return bool(re.fullmatch(r"(?:-|-?" + PNUM + r")?X(?:[+-]\d+(?:/\d+)?)?", inside))


# ============================================================================ the simulator
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
    if zero and r < 0.15:
        return Fr(0)
    if WIDE[0] and r > 0.9:
        v = Fr(rng.randint(1, 400), rng.choice([1, 7, 9, 11, 12, 13]))  # long numbers: line splits
        return v if rng.random() < 0.5 else -v
    if r < 0.55:
        v = Fr(rng.randint(1, 6 if small else 12))
    elif r < 0.8:
        q = rng.choice([2, 3, 4, 5, 6, 8])
        v = Fr(rng.randint(1, 3 * q), q)
        if v.denominator == 1:
            v = Fr(rng.randint(1, 9), 7)
    else:
        v = Fr(rng.choice([1, 2, 3, 5, 7, 9, 11]), rng.choice([2, 3, 4, 5, 10]))
    return v if rng.random() < 0.5 else -v


def coef(rng):
    """a nonzero coefficient, often 1 or -1"""
    r = rng.random()
    if r < 0.2:
        return Fr(1)
    if r < 0.35:
        return Fr(-1)
    return rnum(rng, zero=False)


def typed(rng, v, default=None):
    """the text a student types for v (default = the value ENTER gives)"""
    if default is not None and v == default and rng.random() < 0.6:
        return ""
    neg = v < 0
    a = abs(v)
    minus = rng.choice(["-", "⁻"])
    if neg and a == 1 and default == 1 and rng.random() < 0.6:
        return minus
    if a.denominator == 1:
        body = str(a.numerator)
    else:
        r = rng.random()
        if a.denominator in (2, 4, 5, 8, 10) and r < 0.15:
            body = str(float(a)).lstrip("0") if rng.random() < 0.5 else str(float(a))
        elif neg and r < 0.3:
            return f"{minus}({a.numerator}/{a.denominator})"
        else:
            body = f"{a.numerator}/{a.denominator}"
    return (minus + body) if neg else body


def abck_actions(rng, a, b, c, k):
    acts = []
    if rng.random() < 0.06:
        acts.append("t:0")  # A = 0 is refused: the screen is drawn again and A asked again
    if rng.random() < 0.06:
        acts += ["t:" + typed(rng, a, 1), "t:0"]  # B = 0: drawn again, A and B asked again
    acts.append("t:" + typed(rng, a, 1))
    tb = typed(rng, b, 1)
    r = rng.random()
    if r < 0.12:
        tb += "X"  # the student copies the X too: 3X, -X, X, (1/2)X
    elif r < 0.18 and b.denominator > 1 and b.numerator in (1, -1):
        tb = ("-" if b < 0 else "") + f"X/{b.denominator}"  # f(x/2) typed as X/2
    acts.append("t:" + tb)
    for v in (c, k):
        tv = typed(rng, v, 0)
        if v > 0 and tv and rng.random() < 0.2:
            tv = "+" + tv  # the student copies the plus sign: f(x+1) -> +1
        acts.append("t:" + tv)
    return acts


# ============================================================================ problems
class Problem:
    """mode = submenu key; body = actions after the mode key; answers = expected answer
    screens (each a list of HAOUT lines); footer = expected footer of the last screen"""


def new_eq(rng, eq):
    """(a, b, c, k, typing actions): a new random equation, or the one kept by 3:SAME EQ"""
    if eq is not None:
        return eq + ([],)
    a, b, c, k = coef(rng), coef(rng), rnum(rng), rnum(rng)
    return a, b, c, k, abck_actions(rng, a, b, c, k)


def p_changes(rng, eq=None):
    a, b, c, k, acts = new_eq(rng, eq)
    p = Problem()
    p.kind, p.mode = "changes", "k1"
    p.desc = f"A={a} B={b} C={c} K={k}"
    p.body = acts
    p.answers = [["<EQ>"] + change_lines(a, b, c, k) + abhk_lines(a, b, -c / b, k)]
    p.footer = FOOT
    p.abck = (a, b, c, k)
    return p


def p_why(rng, eq):
    a, b, c, k, _ = new_eq(rng, eq)
    p = Problem()
    p.kind, p.mode = "why", None
    p.desc = f"WHY A={a} B={b} C={c} K={k}"
    p.body = []
    p.answers = [None]
    p.footer = FOOT
    p.abck = (a, b, c, k)
    return p


def p_point(rng, eq=None):
    a, b, c, k, acts = new_eq(rng, eq)
    p = Problem()
    p.kind, p.mode = "point", "k2"
    p.abck = (a, b, c, k)
    p.body = acts + ["k1"]
    pts = []
    for _ in range(rng.choice([1, 1, 2, 3])):
        x, y = rnum(rng), rnum(rng)
        pts.append((x, y))
    p.desc = f"A={a} B={b} C={c} K={k} points {pts}"
    p.pts = pts
    p.answers = []
    p.typed_pts = []
    for x, y in pts:
        p.typed_pts.append(["t:" + typed(rng, x, 0 if rng.random() < 0.5 else None),
                            "t:" + typed(rng, y, 0 if rng.random() < 0.5 else None)])
        p.answers.append([pt((x - c) / b, a * y + k), "FROM " + pt(x, y)])
    p.footer = FOOT_PT
    return p


def graph_image(xs, ys, lc, rc):
    """(domain interval, range interval) of the corner-point graph, exactly"""
    n = len(xs)
    dom = (xs[0], xs[-1], lc, rc)
    # range: union over the segments of the y values taken (hollow end points left out)
    pieces = []
    inc = [True] * n
    inc[0] = inc[0] and bool(lc)
    inc[-1] = inc[-1] and bool(rc)
    for i in range(n):
        if inc[i]:
            pieces.append((ys[i], ys[i], True, True))
    for i in range(n - 1):
        lo, hi = min(ys[i], ys[i + 1]), max(ys[i], ys[i + 1])
        if lo < hi:
            pieces.append((lo, hi, False, False))  # open segment interior
        else:
            pieces.append((lo, lo, True, True))  # a flat piece takes its value inside
    lo = min(pc[0] for pc in pieces)
    hi = max(pc[1] for pc in pieces)
    lcl = any(pc[0] == lo and pc[2] for pc in pieces)
    rcl = any(pc[1] == hi and pc[3] for pc in pieces)
    return dom, (lo, hi, lcl, rcl)


def map_x_ivl(iv, b, c):
    lo, hi, lc, rc = iv
    f = (lambda x: x if abs(x) >= INF else (x - c) / b)
    nl, nh = f(lo), f(hi)
    if b < 0:
        nl, nh = (-nl if abs(nl) >= INF else nl), (-nh if abs(nh) >= INF else nh)
        return (nh, nl, rc, lc)
    return (nl, nh, lc, rc)


def map_y_ivl(iv, a, k):
    lo, hi, lc, rc = iv
    f = (lambda y: y if abs(y) >= INF else a * y + k)
    nl, nh = f(lo), f(hi)
    if a < 0:
        nl, nh = (-nl if abs(nl) >= INF else nl), (-nh if abs(nh) >= INF else nh)
        return (nh, nl, rc, lc)
    return (nl, nh, lc, rc)


def p_graph(rng, saved, eq=None):
    a, b, c, k, acts = new_eq(rng, eq)
    p = Problem()
    p.kind, p.mode = "graph", "k2"
    p.abck = (a, b, c, k)
    p.body = acts + ["k2"]
    use_saved = saved is not None and rng.random() < 0.4
    if use_saved:
        xs, ys, lc, rc = saved
        p.body.append("k1")
    else:
        n = rng.choice([1, 2, 3, 4, 4, 5, 6] + ([9, 12] if WIDE[0] else []))
        xs = sorted(set(rnum(rng) for _ in range(n * 2)))[:n]
        while len(xs) < n:
            xs = sorted(set(xs + [rnum(rng)]))[:n]
        ys = [rnum(rng, small=True) for _ in xs]
        if n > 2 and rng.random() < 0.3:
            ys[1] = ys[0]  # a flat piece
        if n > 1 and rng.random() < 0.3:
            ys[-1] = max(ys) if rng.random() < 0.5 else min(ys)  # extreme value at an end
        dots = rng.choice([1, 1, 2, 3, 4]) if n > 1 else 1
        lc, rc = dots not in (2, 4), dots not in (3, 4)
        if saved is not None:
            p.body.append("k2")
        order = list(range(n))
        rng.shuffle(order)  # the student types the corners in any order (HAPTS sorts them)
        if rng.random() < 0.7:
            order = list(range(n))
        p.body.append(f"t:{n}")
        for i in order:
            p.body += ["t:" + typed(rng, xs[i]), "t:" + typed(rng, ys[i])]
        p.body.append(f"k{dots}")
    p.new_saved = (xs, ys, lc, rc)
    p.desc = f"A={a} B={b} C={c} K={k} graph {list(zip(xs, ys))} ends {lc},{rc} saved={use_saved}"
    lines = []
    for x, y in zip(xs, ys):
        old, new = pt(x, y), pt((x - c) / b, a * y + k)
        lines += [old + " TO " + new] if len(old + new) + 4 <= 26 else [old + " TO", "   " + new]
    dom, rngv = graph_image(xs, ys, lc, rc)
    dtxt = "D=" + ivl(*map_x_ivl(dom, b, c))
    rtxt = "R=" + ivl(*map_y_ivl(rngv, a, k))
    lines += [dtxt + "  " + rtxt] if len(dtxt) + len(rtxt) <= 24 else [dtxt, rtxt]
    lines += ["NEW X=" + lin(1 / b, -c / b, "X"), "NEW Y=" + lin(a, k, "Y")]
    p.answers = [lines]
    p.footer = FOOT
    return p


def rand_ivl(rng):
    r = rng.random()
    lo, hi = rnum(rng), rnum(rng)
    if lo > hi:
        lo, hi = hi, lo
    if r < 0.05:
        hi = lo  # one point
    lc, rc = rng.random() < 0.6, rng.random() < 0.6
    if rng.random() < 0.2:
        lo, lc = -INF, False
    if rng.random() < 0.2:
        hi, rc = INF, False
    return (lo, hi, lc, rc)


def ivl_actions(rng, iv):
    lo, hi, lc, rc = iv

    def t(v):
        # HAIVL: an infinity typed as the left end is -INF, as the right end +INF (sign or not)
        if v >= INF:
            return rng.choice(["I", "I", "I", "-I"])
        if v <= -INF:
            return rng.choice(["-I", "⁻I", "I"])
        return typed(rng, v)

    ends = [t(lo), t(hi)]
    if rng.random() < 0.1 and lo != hi and abs(lo) < INF and abs(hi) < INF:
        ends.reverse()  # finite ends typed in the wrong order: HAIVL puts them in order
    acts = ["t:" + e for e in ends]
    if lo > -INF or hi < INF:
        key = {(True, True): 1, (True, False): 2, (False, True): 3, (False, False): 4}[(lc, rc)]
        acts.append(f"k{key}")
    return acts


def p_dr(rng, eq=None):
    a, b, c, k, acts = new_eq(rng, eq)
    p = Problem()
    p.kind, p.mode = "dr", "k3"
    p.abck = (a, b, c, k)
    given = rng.choice([1, 1, 2, 3])
    p.body = acts + [f"k{given}"]
    exp = []
    dv = rv = None
    if given != 3:
        dv = rand_ivl(rng)
        p.body += ivl_actions(rng, dv)
        exp.append("D=" + ivl(*map_x_ivl(dv, b, c)))
    if given != 2:
        rv = rand_ivl(rng)
        p.body += ivl_actions(rng, rv)
        exp.append("R=" + ivl(*map_y_ivl(rv, a, k)))
    p.desc = f"A={a} B={b} C={c} K={k} given={given} D={dv} R={rv}"
    p.answers = [exp]
    p.footer = FOOT
    return p


STEP_KEYS = {"rx": "k1", "ry": "k2", "vf": "k3", "hf": "k4"}
DONE_KEY = "k9"


def apply_step(expr, kind, t):
    if kind == "rx":
        return -expr
    if kind == "ry":
        return expr.subs(XS, -XS)
    if kind == "vf":
        return expr * t if t != 0 else expr
    if kind == "hf":
        return expr.subs(XS, XS / t) if t != 0 else expr
    if kind == "lr":
        return expr.subs(XS, XS - t)
    if kind == "ud":
        return expr + t
    raise ValueError(kind)


def p_write(rng):
    p = Problem()
    p.kind, p.mode = "write", "k4"
    n = rng.choice([0, 1, 2, 3, 4, 4, 5, 6, 8])
    expr = FS(XS)
    p.body = []
    steps = []
    for _ in range(n):
        kind = rng.choice(["rx", "ry", "vf", "hf", "lr", "ud"])
        t = None
        if kind in STEP_KEYS:
            p.body.append(STEP_KEYS[kind])
        if kind in ("vf", "hf"):
            r = rng.random()
            if r < 0.05:
                t = Fr(0)
                p.body.append("t:" + rng.choice(["", "0"]))
            else:
                t = abs(rnum(rng, zero=False, small=True))
                p.body.append("t:" + typed(rng, t if rng.random() < 0.9 else -t))
        elif kind in ("lr", "ud"):
            t = rnum(rng)
            # 5:LEFT 6:RIGHT 7:UP 8:DOWN; the student types the size they see (sometimes with a minus)
            if kind == "lr":
                p.body.append("k6" if t > 0 else "k5")
            else:
                p.body.append("k7" if t > 0 else "k8")
            shown = abs(t) if rng.random() < 0.85 else -abs(t)
            p.body.append("t:" + typed(rng, shown, 0))
        steps.append((kind, t))
        expr = apply_step(expr, kind, t if t is not None else 0)
    p.body.append(DONE_KEY)
    p.expr = expr
    p.steps = steps
    p.desc = f"steps {steps}"
    p.footer = FOOT
    p.answers = [None]  # checked semantically
    a, b, h, k = abhk(expr)
    p.abck = (a, b, -b * h, k)
    return p


# ============================================================================ checking
def check_write(p, lines):
    errs = []
    if len(lines) < 2:
        return [f"short answer {lines}"]
    fac, rest = lines[0], lines[1:]
    a, b, h, k = abhk(p.expr)
    if not all(shown_exact(v) for v in (a, b, h, k, -b * h)):
        # a documented decimal fallback: only the A= B= H= K= values can be compared
        want = " ".join(abhk_lines(a, b, h, k))
        got = " ".join(r for r in rest if not r.startswith("="))
        return [] if got == want else [f"values {got!r} != {want!r}"]
    if rest[0].startswith("="):
        exp_, vals = rest[0], " ".join(rest[1:])
        if exp_ == "=" + fac[2:]:
            return [f"expanded line repeats the factored form {exp_}"]
    else:
        exp_, vals = "=" + fac[2:], " ".join(rest)
    try:
        e1 = to_sympy(fac)
        e2 = to_sympy(exp_)
    except Exception as e:  # noqa: BLE001
        return [f"cannot parse {fac!r} / {exp_!r}: {e}"]
    if not same(e1, p.expr):
        errs.append(f"factored {fac} != {sp.expand(p.expr)}")
    if not same(e2, p.expr):
        errs.append(f"expanded {exp_} != {sp.expand(p.expr)}")
    if not factored_ok(fac):
        errs.append(f"factored form not in a*f(b(x-h))+k shape: {fac}")
    if not expanded_ok(exp_):
        errs.append(f"expanded form not in a*f(bx+c)+k shape: {exp_}")
    want = " ".join(abhk_lines(a, b, h, k))
    if vals != want:
        errs.append(f"values {vals!r} != {want!r}")
    return errs


def check_why(p, lines):
    a, b, c, k = p.abck
    ex = a * FS(b * XS + c) + k
    errs = []
    want_head = ["PAGE WHY:", "AS TYPED:"]
    if lines[:2] != want_head:
        errs.append(f"WHY head {lines[:2]}")
        return errs
    try:
        typed_ = to_sympy(lines[2])
        fac = to_sympy(lines[4])
    except Exception as e:  # noqa: BLE001
        return [f"WHY cannot parse {lines[2:5]}: {e}"]
    if not same(typed_, ex):
        errs.append(f"WHY as typed {lines[2]} != {ex}")
    if not same(fac, ex):
        errs.append(f"WHY factored {lines[4]} != {ex}")
    if not factored_ok(lines[4]):
        errs.append(f"WHY factored shape {lines[4]}")
    if lines[5] != "SO H=-C/B=" + ft(-c / b):
        errs.append(f"WHY h line {lines[5]}")
    if lines[6:] != ["ORDER: A, THEN B, H, K", "FOOTER " + FOOT]:
        errs.append(f"WHY tail {lines[6:]}")
    return errs


def new_problem(rng, kind, state, eq=None):
    if kind == "changes":
        return p_changes(rng, eq)
    if kind == "why":
        return p_why(rng, eq)
    if kind == "point":
        return p_point(rng, eq)
    if kind == "graph":
        state["had_saved_before"] = state.get("saved") is not None
        p = p_graph(rng, state.get("saved"), eq)
        state["saved"] = p.new_saved
        return p
    if kind == "dr":
        return p_dr(rng, eq)
    return p_write(rng)


SAME_KEY = {"changes": "k1", "point": "k2", "graph": "k2", "dr": "k3", "why": "k4"}
AGAIN_TO = {"changes": ["changes"], "why": ["changes"], "graph": ["point", "graph"], "dr": ["dr"],
            "write": ["write"]}


def make_session(rng, kinds, state):
    """a few problems chained with 1:AGAIN (same submenu, new numbers), 3:SAME EQ (the same
    equation, another question: changes / points / D,R / WHY) or 2:HOME (main menu, menu 4 again)"""
    acts = []
    probs = []
    how = "home"
    p = None
    n = rng.choice([1, 1, 2, 3, 4])
    for i in range(n):
        if how == "same":
            kind = rng.choice([k for k in kinds if k in SAME_KEY] + ["why"])
            p = new_problem(rng, kind, state, eq=p.abck)
            acts.append(SAME_KEY[kind])
        elif how == "menu4":  # CLEAR at the SAME EQ menu: back on the menu-4 screen
            p = new_problem(rng, rng.choice(kinds), state)
            acts.append(p.mode)
        elif how == "again":
            p = new_problem(rng, rng.choice([k for k in AGAIN_TO[p.kind] if k in kinds] or AGAIN_TO[p.kind]), state)
        else:
            p = new_problem(rng, rng.choice(kinds), state)
            acts.append("k4")
            if rng.random() < 0.08:
                acts += ["k9", "CLEAR", "k4"]  # a dead key, CLEAR back to the main menu, back in
            if rng.random() < 0.15:
                acts += abort_actions(rng, p, state)  # start, then CLEAR back to the menu-4 screen
            acts.append(p.mode)
        acts += p.body
        if p.kind == "point":
            for j, tp in enumerate(p.typed_pts):
                acts += tp
                if j < len(p.typed_pts) - 1:
                    acts.append("k1")  # 1:NEXT PT
        probs.append(p)
        r = rng.random()
        how = "same" if r < 0.35 else "again" if r < 0.6 and p.kind != "point" else "home"
        if i == n - 1:
            how = "home"
        acts.append({"same": "k3", "again": "k1", "home": "k2"}[how])
        if how == "same" and rng.random() < 0.1:
            acts.append("CLEAR")
            how = "menu4"
    return acts, probs


def abort_actions(rng, p, state):
    """a false start that ends with CLEAR at a menu of the same submenu (back to the menu-4 screen)"""
    junk = abck_actions(rng, coef(rng), coef(rng), rnum(rng), rnum(rng))
    if p.kind in ("point", "graph"):
        if p.kind == "graph" and rng.random() < 0.5 and state.get("had_saved_before"):
            return ["k2"] + junk + ["k2", "CLEAR"]  # CLEAR at GRAPH CORNERS
        return ["k2"] + junk + ["CLEAR"]  # CLEAR at WHICH POINTS?
    if p.kind == "dr":
        return ["k3"] + junk + ["CLEAR"]  # CLEAR at WHAT ARE YOU GIVEN?
    if p.kind == "write":
        out = ["k4"]
        for _ in range(rng.randint(0, 3)):
            out += rng.choice([["k1"], ["k2"], ["k7", "t:2"], ["k3", "t:3"]])
        return out + ["CLEAR"]  # CLEAR at the step menu
    return []


def run_case(rng, kinds, state, verbose=False):
    acts, probs = make_session(rng, kinds, state)
    lists = None
    if state.get("saved_lists") is not None:
        lists = state["saved_lists"]
    m, res, err = run(acts, lists)
    errs = []
    if err:
        errs.append(f"TI error: {err}")
    elif res[0] != "stop":
        errs.append(f"did not stop cleanly: {res} last screen {[l for l in m.lines() if l.strip()]}")
    if m.problems:
        errs.append(f"screen problems: {m.problems[:3]}")
    screens = [x for x in m.out if x and x[0] in ("ANSWER:", "PAGE WHY:")]
    want = [(p, a) for p in probs for a in p.answers]
    if not errs:
        if len(screens) != len(want):
            errs.append(f"{len(screens)} answer screens, expected {len(want)}")
        for (p, a), s in zip(want, screens):
            body = [l for l in s[1:] if not l.startswith("FOOTER ")]
            foot = [l[7:] for l in s if l.startswith("FOOTER ")]
            if foot != [p.footer]:
                errs.append(f"[{p.kind}] footer {foot} != {p.footer}")
            if p.kind == "write":
                errs += [f"[write {p.desc}] " + e for e in check_write(p, body)]
            elif p.kind == "why":
                errs += [f"[why {p.desc}] " + e for e in check_why(p, s)]
            elif a and a[0] == "<EQ>":
                if body[1:] != a[1:]:
                    errs.append(f"[{p.kind} {p.desc}] got {body} want {a}")
                else:
                    pa, pb, pc, pk = p.abck
                    try:
                        ok = same(to_sympy(body[0]), pa * FS(pb * XS + pc) + pk) and factored_ok(body[0])
                    except Exception:  # noqa: BLE001
                        ok = False
                    if not ok:
                        errs.append(f"[{p.kind} {p.desc}] factored form {body[0]!r} wrong")
            elif body != a:
                errs.append(f"[{p.kind} {p.desc}] got {body} want {a}")
    for kind, detail, lines in m.events:
        if lines and lines[0] == "GRAPH CORNERS:":
            if not lines[1].startswith("SAVED: ") or len(lines[1]) > 26:
                errs.append(f"saved-graph line {lines[1]!r}")
    # saved graph persists for the next session (as on the calculator)
    if all(k in m.lists for k in ("ʟBX", "ʟBY", "ʟBC")) and m.lists["ʟBX"]:
        state["saved_lists"] = {k: list(m.lists[k]) for k in ("ʟBX", "ʟBY", "ʟBC")}
    else:
        state["saved"] = None
    return errs, acts, probs, m


KINDS = ["changes", "point", "graph", "dr", "write"]
ALLKINDS = KINDS + ["why"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-n", type=int, default=500)
    ap.add_argument("-s", type=int, default=1)
    ap.add_argument("--kind", default=None)
    ap.add_argument("-v", action="store_true")
    ap.add_argument("--wide", action="store_true", help="also long numbers and big graphs")
    args = ap.parse_args()
    rng = random.Random(args.s)
    WIDE[0] = args.wide
    kinds = args.kind.split(",") if args.kind else KINDS
    state = {}
    stats = {k: 0 for k in ALLKINDS}
    bad = 0
    t0 = time.time()
    shown = 0
    for i in range(args.n):
        errs, acts, probs, m = run_case(rng, kinds, state, args.v)
        for p in probs:
            stats[p.kind] += 1
        if errs:
            bad += 1
            if shown < 25:
                shown += 1
                print(f"--- case {i}: {[p.kind for p in probs]}")
                for e in errs[:6]:
                    print("   ", e)
                if args.v:
                    print("    actions:", acts)
    print(f"{args.n} sessions, {sum(stats.values())} problems {stats}; {bad} sessions with mismatches; "
          f"{time.time() - t0:.1f}s")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
