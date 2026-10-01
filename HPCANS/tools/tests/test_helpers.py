"""Function-input helpers: HAFUNC HAGRAPH HAFSTR HAFEVAL HAFDOM HAFZERO HAWORDS.

These helpers have no main-menu entry of their own, so every case runs a small DRIVER
program in place of HPCANS (drivers live only in this file, never in src/).  A driver:
  1. calls prgmHAFUNC once or twice (the student's keys and numbers are the case's actions),
  2. shows an ANSWER: screen with what the helpers return (text, values, domains, zeros),
  3. ends with a 1-choice footer and Stop.

Run:   python3 tests/test_helpers.py        (from tools/)
CASES stays empty so tools/run_tests.py (which always starts at the real HPCANS) still loads
this module; the helper cases are HCASES, run by main().

Expected lines may be longer than 26 columns: HAOUT wraps them, and the matcher here
accepts a line that HAOUT split over 2-3 screen rows (see candidates()).
"""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from harness import answer_pages  # noqa: E402
from tibasic import D, Machine, TIError, load_programs  # noqa: E402

SRC = HERE.parent.parent / "src"
MINE = ["HAFUNC", "HAGRAPH", "HAFSTR", "HAFEVAL", "HAFDOM", "HAFZERO", "HAWORDS"]

CASES = []  # see module docstring

# ---------------------------------------------------------------------------
# driver building blocks (TI-BASIC lines; a driver is a solver-layer program)
# ---------------------------------------------------------------------------
HEAD = ["SetUpEditor ʟGFX,ʟGFY,ʟGFC,ʟGGX,ʟGGY,ʟGGC", "SetUpEditor"]
FOOT = ['"1:END"→Str9', "1→θ", "prgmHAEND", "Stop"]
ANS = ["prgmHAANS"]


def enter(slot, name, shape=0):
    """HAFUNC: N=slot, O=shape (0 = show the menu), Str9=name -> record ʟF<slot>, θ=1 ok / 0 back."""
    return [f"{slot}→N", f"{shape}→O", f'"{name}"→Str9', "prgmHAFUNC", "θ→M"]


def say(text):
    return [f'"{text}"→Str9', "prgmHAOUT"]


def show_str(slot, label):
    return [f"{slot}→N", "prgmHAFSTR", f'"{label}="+Str5→Str9', "prgmHAOUT"]


def val(slot, x):
    """value of record <slot> at x -> P (value), Q (1 defined, 0 undefined, 2 words: unknown)"""
    return [f"{slot}→N", f"{x}→O", "prgmHAFEVAL"]


def show_val(slot, x, label):
    return val(slot, x) + ["Q→B", "P→θ", "prgmHAFRAC", f'"{label}="+Str9→Str9',
                           "If B=0", f'"{label}=UNDEFINED"→Str9', "If B=2", f'"{label}=?"→Str9', "prgmHAOUT"]


def all_reals():
    return ["1→θ", "prgmHADOM"]


def dom(slot):
    """D = D ∩ domain(record)"""
    return [f"{slot}→N", "0→O", "prgmHAFDOM", "θ→M"]


def band(slot, lo, hi, flags):
    """D = D ∩ {x in domain : lo ≤ f(x) ≤ hi}; flags = 1*(lo included) + 2*(hi included)"""
    return [f"{slot}→N", "1→O", f"{lo}→P", f"{hi}→Q", f"{flags}→R", "prgmHAFDOM", "θ→M"]


def zeros(slot, level="0", remove=0):
    """solutions of f(x)=level -> ʟFZL ʟFZR (closed stretches), R = count; remove=1 also D = D minus them"""
    return [f"{slot}→N", f"{level}→O", f"{remove}→P", "prgmHAFZERO", "θ→M", "R→C"]


def show_dom(label):
    return ["9→θ", "prgmHADOM", f'"{label}="+Str6→Str9', "prgmHAOUT"]


def show_zeros(label="ZEROS"):
    return ['"NONE"→Str0', "For(I,1,C)", "ʟFZL(I)→θ", "prgmHAFRAC", "Str9→Str1",
            "If ʟFZL(I)≠ʟFZR(I)", "Then", "ʟFZR(I)→θ", "prgmHAFRAC", '"["+Str1+","+Str9+"]"→Str1', "End",
            "If I=1", "Str1→Str0", "If I>1", 'Str0+","+Str1→Str0', "End",
            f'"{label}="+Str0→Str9', "prgmHAOUT"]


def show_status(label="STATUS"):
    return ["M→θ", "prgmHAFRAC", f'"{label}="+Str9→Str9', "prgmHAOUT"]


def dom_of(slot, label="D"):
    return all_reals() + dom(slot) + show_dom(label)


def zeros_of(slot, label="ZEROS"):
    return zeros(slot) + show_zeros(label)


def quotient_domain(top, bottom, label):
    """the HAOPS recipe: D = Df ∩ Dg minus the zeros of the bottom function"""
    return all_reals() + dom(top) + dom(bottom) + zeros(bottom, "0", 1) + show_dom(label)


def comp_domain_rational_outer(outer, inner, label):
    """the HACOMP recipe for f(g(x)) when f is rational: x in Dg, and g(x) is not a zero of
    f's denominator: HAROOT on f's denominator, then remove {x : g(x) = r} for each root r."""
    return (all_reals() + dom(inner) +
            [f"{{ʟF{outer}(9),ʟF{outer}(10),ʟF{outer}(11)}}→ʟQC", "prgmHAROOT", "θ→E", "ʟRT→L₁",
             "For(J,1,E)", f"{inner}→N", "L₁(J)→O", "1→P", "prgmHAFZERO", "End"] + show_dom(label))


def comp(inner, outer):
    """D = D ∩ domain of outer(inner(x)): x in D_inner and inner(x) in D_outer (HAFDOM mode 2)"""
    return [f"{inner}→N", "2→O", f"{outer}→P", "prgmHAFDOM", "θ→M"]


def comp_domain(inner, outer, label):
    return all_reals() + comp(inner, outer) + show_dom(label)


def saved_values(cid, src, steps, expect, official):
    return dict(id=cid, source=src, lists=EX13, actions=[],
                driver=enter(1, "F", 9) + enter(2, "G", 9) + ANS + steps,
                expect=expect, official=official)


# EX-1.3 graphs (all corners labeled, closed ends)
F_PTS = [(-6, 2), (-3, -1), (1, 3), (4, 0), (7, 3)]
G_PTS = [(-5, 3), (-2, 0), (1, 0), (3, 2), (6, -1)]
EX13 = {"ʟGFX": [p[0] for p in F_PTS], "ʟGFY": [p[1] for p in F_PTS], "ʟGFC": [1, 1],
        "ʟGGX": [p[0] for p in G_PTS], "ʟGGY": [p[1] for p in G_PTS], "ʟGGC": [1, 1]}


def typed_graph(pts, ends="k1"):
    acts = [f"t:{len(pts)}"]
    for x, y in pts:
        acts += [f"t:{x}", f"t:{y}"]
    return acts + [ends]


HCASES = [
    # ------------------------------------------------------------------ shapes
    dict(id="H-AXB", source="AX+B: g(x)=3-x (PR-1.1)", actions=["k1", "t:-1", "t:3"],
         driver=enter(2, "G") + ANS + show_str(2, "G(X)") + show_val(2, "⁻2", "G(-2)") + dom_of(2) + zeros_of(2),
         expect=["G(X)=-X+3", "G(-2)=5", "D=ALL REALS", "ZEROS=3"], official="g(x)=3-x, g(-2)=5"),
    dict(id="PR-1.1", source="f=2x²-1, g=3-x: (f-g)(x) and (fg)(-2) from the records",
         actions=["k2", "t:2", "t:0", "t:-1", "k1", "t:-1", "t:3"],
         driver=enter(1, "F") + enter(2, "G") + ANS + show_str(1, "F(X)") + show_val(1, "⁻2", "F(-2)")
         + ["seq(ʟF1(I),I,2,6)-seq(ʟF2(I),I,2,6)→ʟPLY", "prgmHAPOLY", '"(F-G)(X)="+Str7→Str9', "prgmHAOUT"]
         + val(1, "⁻2") + ["P→A"] + val(2, "⁻2") + ["A*P→θ", "prgmHAFRAC", '"(FG)(-2)="+Str9→Str9', "prgmHAOUT"]
         + dom_of(1),
         expect=["F(X)=2X²-1", "F(-2)=7", "(F-G)(X)=2X²+X-4", "(FG)(-2)=35", "D=ALL REALS"],
         official="(f - g)(x) = 2x^2 + x - 4; (fg)(-2) = 35"),
    dict(id="H-QUAD", source="AX²+BX+C with ENTER defaults: g(x)=x²+x (PR-2.1)", actions=["k2", "t:", "t:", "t:"],
         driver=enter(2, "G") + ANS + show_str(2, "G(X)") + zeros_of(2) + show_val(2, "3", "G(3)"),
         expect=["G(X)=X²+X", "ZEROS=-1,0", "G(3)=12"], official="g(x)=x²+x"),
    dict(id="H-RAT1", source="(AX+B)/(CX+D): f(x)=(x+1)/(x-2) (PR-1.3)", actions=["k3", "t:", "t:1", "t:", "t:-2"],
         driver=enter(1, "F") + ANS + show_str(1, "F(X)") + dom_of(1) + zeros_of(1)
         + show_val(1, "2", "F(2)") + show_val(1, "0", "F(0)"),
         expect=["F(X)=(X+1)/(X-2)", "D=ALL REALS, X≠2", "ZEROS=-1", "F(2)=UNDEFINED", "F(0)=-1/2"],
         official="f restriction x≠2, zero x=-1 (SOL-1.3)"),
    dict(id="H-RAT2", source="(AX+B)/(CX+D): g(x)=(x-5)/x (PR-1.3)", actions=["k3", "t:", "t:-5", "t:", "t:"],
         driver=enter(2, "G") + ANS + show_str(2, "G(X)") + dom_of(2) + zeros_of(2),
         expect=["G(X)=(X-5)/X", "D=ALL REALS, X≠0", "ZEROS=5"], official="g restriction x≠0, zero x=5 (SOL-1.3)"),
    dict(id="H-RAT3", source="(AX+B)/(CX+D): g(x)=(x+2)/(4-x) (EX-1.2)", actions=["k3", "t:", "t:2", "t:-1", "t:4"],
         driver=enter(2, "G") + ANS + show_str(2, "G(X)") + dom_of(2) + zeros_of(2),
         expect=["G(X)=(X+2)/(-X+4)", "D=ALL REALS, X≠4", "ZEROS=-2"], official="g: x≠4; g(x)=0 at x=-2 (EX-1.2)"),
    dict(id="H-RECIP1", source="K/(AX+B): g(x)=2/x (PR-2.2)", actions=["k4", "t:2", "t:", "t:"],
         driver=enter(2, "G") + ANS + show_str(2, "G(X)") + dom_of(2) + zeros_of(2) + show_val(2, "1/2", "G(1/2)"),
         expect=["G(X)=2/X", "D=ALL REALS, X≠0", "ZEROS=NONE", "G(1/2)=4"], official="g(x)=2/x"),
    dict(id="H-RECIP2", source="K/(AX+B): B(x)=4/(x+1) (EX-2.3)", actions=["k4", "t:4", "t:", "t:1"],
         driver=enter(2, "B") + ANS + show_str(2, "B(X)") + dom_of(2) + show_val(2, "0", "B(0)"),
         expect=["B(X)=4/(X+1)", "D=ALL REALS, X≠-1", "B(0)=4"], official="B(x)=4/(x+1); B(0)=4 (EX-2.3 check)"),
    dict(id="H-RECIP3", source="K/(AX+B): f(x)=1/(x-3) (PR-2.2)", actions=["k4", "t:", "t:", "t:-3"],
         driver=enter(1, "F") + ANS + show_str(1, "F(X)") + dom_of(1) + show_val(1, "3", "F(3)"),
         expect=["F(X)=1/(X-3)", "D=ALL REALS, X≠3", "F(3)=UNDEFINED"], official="f(x)=1/(x-3)"),
    dict(id="H-ROOT1", source="K√(AX+B)+C, ENTER only: f(x)=√x", actions=["k5", "t:", "t:", "t:", "t:"],
         driver=enter(1, "F") + ANS + show_str(1, "F(X)") + dom_of(1) + zeros_of(1)
         + show_val(1, "4", "F(4)") + show_val(1, "⁻1", "F(-1)"),
         expect=["F(X)=√(X)", "D=[0,INF)", "ZEROS=0", "F(4)=2", "F(-1)=UNDEFINED"], official="√x: D=[0,∞)"),
    dict(id="H-ROOT2", source="K√(AX+B)+C: f(x)=√(5-x) (PR-1.2)", actions=["k5", "t:", "t:-1", "t:5", "t:"],
         driver=enter(1, "F") + ANS + show_str(1, "F(X)") + dom_of(1) + zeros_of(1)
         + show_val(1, "1", "F(1)") + show_val(1, "6", "F(6)"),
         expect=["F(X)=√(-X+5)", "D=(-INF,5]", "ZEROS=5", "F(1)=2", "F(6)=UNDEFINED"],
         official="D_f: (-∞, 5]; f(x)=0 at x=5 (SOL-1.2)"),
    dict(id="H-ROOT3", source="K√(AX+B)+C: f(x)=7√x+4", actions=["k5", "t:7", "t:", "t:", "t:4"],
         driver=enter(1, "F") + ANS + show_str(1, "F(X)") + dom_of(1) + zeros_of(1) + show_val(1, "4", "F(4)"),
         expect=["F(X)=7√(X)+4", "D=[0,INF)", "ZEROS=NONE", "F(4)=18"], official="7√x+4 is never 0"),
    dict(id="H-ROOT4", source="K√(AX+B)+C: f(x)=√(x+3) (EX-1.1)", actions=["k5", "t:", "t:", "t:3", "t:"],
         driver=enter(1, "F") + ANS + show_str(1, "F(X)") + dom_of(1) + zeros_of(1),
         expect=["F(X)=√(X+3)", "D=[-3,INF)", "ZEROS=-3"], official="D_f = [-3, ∞); f(-3)=0 (EX-1.1)"),
    dict(id="H-FRAC1", source="FRACTION WITH X²: f(x)=(x-3)/x² (EX-1.2)",
         actions=["k6", "t:0", "t:", "t:-3", "t:", "t:0", "t:"],
         driver=enter(1, "F") + ANS + show_str(1, "F(X)") + dom_of(1) + zeros_of(1) + show_val(1, "1", "F(1)"),
         expect=["F(X)=(X-3)/X²", "D=ALL REALS, X≠0", "ZEROS=3", "F(1)=-2"], official="f: x≠0; f(x)=0 at x=3 (EX-1.2)"),
    dict(id="H-FRAC2", source="FRACTION WITH X²: f(x)=(x+2)/x² (CRAM-EX-1)",
         actions=["k6", "t:0", "t:", "t:2", "t:", "t:0", "t:"],
         driver=enter(1, "F") + ANS + show_str(1, "F(X)") + dom_of(1) + zeros_of(1),
         expect=["F(X)=(X+2)/X²", "D=ALL REALS, X≠0", "ZEROS=-2"], official="f(-2)=0 (CRAM-EX-1)"),
    dict(id="H-GRAPHF", source="GRAPH typed: f of EX-1.3; values, domain, zeros; then read back the saved graph",
         actions=["k7"] + typed_graph(F_PTS),
         driver=enter(1, "F") + enter(3, "F", 9) + ANS + show_str(1, "F(X)") + dom_of(1) + zeros_of(1)
         + show_val(1, "0", "F(0)") + show_val(1, "⁻6", "F(-6)") + show_val(1, "⁻3", "F(-3)")
         + show_val(1, "3", "F(3)") + show_val(1, "8", "F(8)") + show_val(3, "0", "SAVED F(0)"),
         expect=["F(X)=", "D=[-6,7]", "ZEROS=-4,-2,4", "F(0)=2", "F(-6)=2", "F(-3)=-1", "F(3)=1",
                 "F(8)=UNDEFINED", "SAVED F(0)=2"],
         official="D_f=[-6,7]; zeros -4, -2, 4; f(-3)=-1, f(3)=1 (EX-1.3); f(0)=2 (EX-2.2a); f(-6)=2 (EX-2.2b)"),
    dict(id="H-GRAPHG", source="GRAPH typed: g of EX-1.3; values, domain, zeros (a whole segment)",
         actions=["k7"] + typed_graph(G_PTS),
         driver=enter(2, "G") + ANS + dom_of(2) + zeros_of(2) + show_val(2, "5", "G(5)") + show_val(2, "2", "G(2)")
         + show_val(2, "⁻6", "G(-6)") + show_val(2, "⁻3", "G(-3)") + show_val(2, "3", "G(3)")
         + show_val(2, "⁻5", "G(-5)") + show_val(2, "1", "G(1)"),
         expect=["D=[-5,6]", "ZEROS=[-2,1],5", "G(5)=0", "G(2)=1", "G(-6)=UNDEFINED", "G(-3)=1", "G(3)=2",
                 "G(-5)=3", "G(1)=0"],
         official="D_g=[-5,6]; g=0 on [-2,1] and at 5; g(-3)=1, g(3)=2 (EX-1.3); g(5)=0, g(2)=1, g(-6) undefined (EX-2.2)"),
    dict(id="H-SAVED", source="GRAPH menu: use the saved graphs of f and g; EX-1.3 (a) (f+g)(-3), (b) (fg)(3)",
         lists=EX13, actions=["k7", "k2", "k7", "k3"],
         driver=enter(1, "F") + enter(2, "G") + ANS
         + val(1, "⁻3") + ["P→A"] + val(2, "⁻3") + ["A+P→θ", "prgmHAFRAC", '"(F+G)(-3)="+Str9→Str9', "prgmHAOUT"]
         + val(1, "3") + ["P→A"] + val(2, "3") + ["A*P→θ", "prgmHAFRAC", '"(FG)(3)="+Str9→Str9', "prgmHAOUT"]
         + dom_of(1, "DF") + dom_of(2, "DG"),
         expect=["(F+G)(-3)=0", "(FG)(3)=2", "DF=[-6,7]", "DG=[-5,6]"],
         official="(a) 0  (b) 2 (EX-1.3); D_f=[-6,7], D_g=[-5,6]"),
    dict(id="H-OPEN", source="GRAPH with an open left end: (0,0),(2,2),(4,0), left dot hollow",
         actions=["k7"] + typed_graph([(0, 0), (2, 2), (4, 0)], "k2"),
         driver=enter(1, "F") + ANS + dom_of(1) + zeros_of(1) + show_val(1, "0", "F(0)") + show_val(1, "1", "F(1)")
         + all_reals() + band(1, "1", "ᴇ99", 1) + show_dom("F≥1"),
         expect=["D=(0,4]", "ZEROS=4", "F(0)=UNDEFINED", "F(1)=1", "F≥1=[1,3]"], official="(extra) open end dot"),
    dict(id="H-WORDS-F", source="WORDS: f has domain [-4,9], f(x)=0 only at x=-1 and x=6 (PR-1.4)",
         actions=["k8", "t:-4", "t:9", "k1", "t:2", "t:-1", "t:6", "t:"],
         driver=enter(1, "F") + ANS + show_str(1, "F(X)") + dom_of(1) + zeros_of(1)
         + show_val(1, "6", "F(6)") + show_val(1, "0", "F(0)") + show_val(1, "10", "F(10)"),
         expect=["F(X)=", "D=[-4,9]", "ZEROS=-1,6", "F(6)=0", "F(0)=?", "F(10)=UNDEFINED"],
         official="D_f = [-4, 9]; zeros of f: x = -1 and x = 6 only"),
    dict(id="H-WORDS-G", source="WORDS: g has domain [-6,5], g(x)=0 for every x in [2,3] (PR-1.4)",
         actions=["k8", "t:-6", "t:5", "k1", "t:", "t:1", "t:2", "t:3"],
         driver=enter(2, "G") + ANS + dom_of(2) + zeros_of(2) + show_val(2, "5/2", "G(5/2)"),
         expect=["D=[-6,5]", "ZEROS=[2,3]", "G(5/2)=0"], official="D_g = [-6, 5]; g(x) = 0 for every x in [2, 3]"),
    # ------------------------------------------------------- HAOPS recipes (domain of f+g, f/g, g/f)
    saved_values("EX-1.3cde", "EX-1.3 graphs: (c) D of f+g, (d) D of f/g, (e) D of g/f",
                 all_reals() + dom(1) + dom(2) + show_dom("D(F+G)") + quotient_domain(1, 2, "D(F/G)")
                 + quotient_domain(2, 1, "D(G/F)"),
                 ["D(F+G)=[-5,6]", "D(F/G)=[-5,-2)U(1,5)U(5,6]", "D(G/F)=[-5,-4)U(-4,-2)U(-2,4)U(4,6]"],
                 "(c) [-5, 6]  (d) [-5, -2) U (1, 5) U (5, 6]  (e) [-5, -4) U (-4, -2) U (-2, 4) U (4, 6]"),
    dict(id="PR-1.4", source="PR-1.4 words: domains of f+g, f/g, g/f",
         actions=["k8", "t:-4", "t:9", "k1", "t:2", "t:-1", "t:6", "t:", "k8", "t:-6", "t:5", "k1", "t:", "t:1", "t:2", "t:3"],
         driver=enter(1, "F") + enter(2, "G") + ANS + all_reals() + dom(1) + dom(2) + show_dom("D(F+G)")
         + quotient_domain(1, 2, "D(F/G)") + quotient_domain(2, 1, "D(G/F)"),
         expect=["D(F+G)=[-4,5]", "D(F/G)=[-4,2)U(3,5]", "D(G/F)=[-4,-1)U(-1,5]"],
         official="D_f+g = [-4, 5]; f/g: [-4, 2) U (3, 5]; g/f: [-4, -1) U (-1, 5]"),
    dict(id="PR-1.2", source="f=√(5-x), g=x+1: domains of f/g and g/f",
         actions=["k5", "t:", "t:-1", "t:5", "t:", "k1", "t:", "t:1"],
         driver=enter(1, "F") + enter(2, "G") + ANS + quotient_domain(1, 2, "D(F/G)") + quotient_domain(2, 1, "D(G/F)"),
         expect=["D(F/G)=(-INF,-1)U(-1,5]", "D(G/F)=(-INF,5)"], official="D_f/g: (-∞, -1) ∪ (-1, 5]; D_g/f: (-∞, 5)"),
    dict(id="PR-1.3", source="f=(x+1)/(x-2), g=(x-5)/x: domains of f/g and g/f",
         actions=["k3", "t:", "t:1", "t:", "t:-2", "k3", "t:", "t:-5", "t:", "t:"],
         driver=enter(1, "F") + enter(2, "G") + ANS + quotient_domain(1, 2, "D(F/G)") + quotient_domain(2, 1, "D(G/F)"),
         expect=["D(F/G)=ALL REALS, X≠0,2,5", "D(G/F)=ALL REALS, X≠-1,0,2"],
         official="D_f/g: ℝ, x ≠ 0, 2, 5; D_g/f: ℝ, x ≠ -1, 0, 2"),
    dict(id="EX-1.1", source="f=√(x+3), g=x-1: domains of f+g, f/g, g/f",
         actions=["k5", "t:", "t:", "t:3", "t:", "k1", "t:", "t:-1"],
         driver=enter(1, "F") + enter(2, "G") + ANS + all_reals() + dom(1) + dom(2) + show_dom("D(F+G)")
         + quotient_domain(1, 2, "D(F/G)") + quotient_domain(2, 1, "D(G/F)") + show_str(1, "F(X)"),
         expect=["D(F+G)=[-3,INF)", "D(F/G)=[-3,1)U(1,INF)", "D(G/F)=(-3,INF)", "F(X)=√(X+3)"],
         official="f+g, fg: [-3, ∞); f/g: [-3, 1) ∪ (1, ∞); g/f: (-3, ∞)"),
    dict(id="EX-1.2", source="f=(x-3)/x², g=(x+2)/(4-x): domains of f/g and g/f",
         actions=["k6", "t:0", "t:", "t:-3", "t:", "t:0", "t:", "k3", "t:", "t:2", "t:-1", "t:4"],
         driver=enter(1, "F") + enter(2, "G") + ANS + quotient_domain(1, 2, "D(F/G)") + quotient_domain(2, 1, "D(G/F)"),
         expect=["D(F/G)=ALL REALS, X≠-2,0,4", "D(G/F)=ALL REALS, X≠0,3,4"],
         official="D_f/g: ℝ, x ≠ -2, 0, 4; D_g/f: ℝ, x ≠ 0, 3, 4"),
    dict(id="CRAM-EX-1", source="f=(x+2)/x², g=(x+1)/(1-x): domains of f/g and g/f",
         actions=["k6", "t:0", "t:", "t:2", "t:", "t:0", "t:", "k3", "t:", "t:1", "t:-1", "t:1"],
         driver=enter(1, "F") + enter(2, "G") + ANS + quotient_domain(1, 2, "D(F/G)") + quotient_domain(2, 1, "D(G/F)"),
         expect=["D(F/G)=ALL REALS, X≠-1,0,1", "D(G/F)=ALL REALS, X≠-2,0,1"],
         official="D_f/g : R, x ≠ 0, 1, -1 ; D_g/f : R, x ≠ 0, 1, -2"),
    dict(id="CORR-6", source="g=√x, f given in words: D_f=[-4,8], f=0 at x=2 (in [0,8]); domain of g/f",
         actions=["k8", "t:-4", "t:8", "k1", "t:1", "t:2", "t:", "k5", "t:", "t:", "t:", "t:"],
         driver=enter(1, "F") + enter(2, "G") + ANS + quotient_domain(2, 1, "D(G/F)"),
         expect=["D(G/F)=[0,2)U(2,8]"], official="Domain of (g/f)(x) = [0, 2) ∪ (2, 8]"),
    # ------------------------------------------------------- HACOMP recipes
    dict(id="EX-2.5a", source="g=√x with the graph of f (EX-1.3): domain of g(f(x))=√(f(x)): where f ≥ 0",
         lists=EX13, actions=["k5", "t:", "t:", "t:", "t:"],
         driver=enter(1, "F", 9) + enter(2, "G") + ANS + comp_domain(1, 2, "D")
         + all_reals() + band(1, "0", "ᴇ99", 1) + show_dom("F≥0"),
         expect=["D=[-6,-4]U[-2,7]", "F≥0=[-6,-4]U[-2,7]"], official="D_{g o f} = [-6,-4] U [-2,7]"),
    dict(id="PR-2.5c", source="domain of y=√(g(x)) with the graph of g (EX-1.3); √x typed as the outside",
         lists=EX13, actions=["k5", "t:", "t:", "t:", "t:"],
         driver=enter(2, "G", 9) + enter(1, "F") + ANS + comp_domain(2, 1, "D")
         + all_reals() + band(2, "0", "ᴇ99", 1) + show_dom("G≥0"),
         expect=["D=[-5,5]", "G≥0=[-5,5]"], official="[-5,5]"),
    dict(id="EX-2.5b", source="g=√x, f = graph of EX-1.3: domain of (g/f)(x)", lists=EX13,
         actions=["k5", "t:", "t:", "t:", "t:"],
         driver=enter(1, "F", 9) + enter(2, "G") + ANS + quotient_domain(2, 1, "D"),
         expect=["D=[0,4)U(4,7]"], official="D = [0,4) U (4,7]"),
    dict(id="EX-2.5c", source="g=√x, f = graph of EX-1.3: domain of f(g(x)) = x in Dg and g(x) in Df", lists=EX13,
         actions=["k5", "t:", "t:", "t:", "t:"],
         driver=enter(1, "F", 9) + enter(2, "G") + ANS + comp_domain(2, 1, "D")
         + all_reals() + dom(1) + ["ʟDL(1)→A", "ʟDR(1)→B", "ʟDA(1)+2ʟDB(1)→C"]
         + all_reals() + dom(2) + ["2→N", "1→O", "A→P", "B→Q", "C→R", "prgmHAFDOM"] + show_dom("STEPS"),
         expect=["D=[0,49]", "STEPS=[0,49]"], official="D = [0,49]"),
    saved_values("EX-2.2", "f(g(5)), g(f(-6)), g(g(-5)), f(g(-6)) from the EX-1.3 graphs",
                 val(2, "5") + ["P→A"] + val(1, "A") + ["P→θ", "prgmHAFRAC", '"F(G(5))="+Str9→Str9', "prgmHAOUT"]
                 + val(1, "⁻6") + ["P→A"] + val(2, "A") + ["P→θ", "prgmHAFRAC", '"G(F(-6))="+Str9→Str9', "prgmHAOUT"]
                 + val(2, "⁻5") + ["P→A"] + val(2, "A") + ["P→θ", "prgmHAFRAC", '"G(G(-5))="+Str9→Str9', "prgmHAOUT"]
                 + val(2, "⁻6") + ["Q→B", "If B", "Then"] + val(1, "P") + ["End",
                    '"F(G(-6))=UNDEFINED"→Str9', "If B", '"F(G(-6))=DEFINED"→Str9', "prgmHAOUT"],
                 ["F(G(5))=2", "G(F(-6))=1", "G(G(-5))=2", "F(G(-6))=UNDEFINED"], "(a) 2 (b) 1 (c) 2 (d) undefined"),
    saved_values("PR-2.5ab", "f(g(1)) and g(f(4)) from the EX-1.3 graphs",
                 val(2, "1") + ["P→A"] + val(1, "A") + ["P→θ", "prgmHAFRAC", '"F(G(1))="+Str9→Str9', "prgmHAOUT"]
                 + val(1, "4") + ["P→A"] + val(2, "A") + ["P→θ", "prgmHAFRAC", '"G(F(4))="+Str9→Str9', "prgmHAOUT"],
                 ["F(G(1))=2", "G(F(4))=0"], "(a) 2 (b) 0"),
    dict(id="EX-2.3", source="A=(x+3)/(x-2), B=4/(x+1): domains of A(B(x)) and B(A(x))",
         actions=["k3", "t:", "t:3", "t:", "t:-2", "k4", "t:4", "t:", "t:1"],
         driver=enter(1, "A") + enter(2, "B") + ANS + comp_domain(2, 1, "D(A(B))") + comp_domain(1, 2, "D(B(A))")
         + comp_domain_rational_outer(1, 2, "STEPS A(B)") + comp_domain_rational_outer(2, 1, "STEPS B(A)"),
         expect=["D(A(B))=ALL REALS, X≠-1,1", "D(B(A))=ALL REALS, X≠-1/2,2",
                 "STEPS A(B)=ALL REALS, X≠-1,1", "STEPS B(A)=ALL REALS, X≠-1/2,2"],
         official="D_{A o B}: R, x != -1, 1; D_{B o A}: R, x != 2, -1/2"),
    dict(id="PR-2.2", source="f=1/(x-3), g=2/x: domain of f(g(x))",
         actions=["k4", "t:", "t:", "t:-3", "k4", "t:2", "t:", "t:"],
         driver=enter(1, "F") + enter(2, "G") + ANS + comp_domain(2, 1, "D"),
         expect=["D=ALL REALS, X≠0,2/3"], official="domain R, x != 0, 2/3"),
    dict(id="PR-2.3", source="A=(x-1)/(x+4), B=5/(x-2): domain of A(B(x))",
         actions=["k3", "t:", "t:-1", "t:", "t:4", "k4", "t:5", "t:", "t:-2"],
         driver=enter(1, "A") + enter(2, "B") + ANS + comp_domain(2, 1, "D"),
         expect=["D=ALL REALS, X≠3/4,2"], official="domain R, x != 2, 3/4"),
    dict(id="CRAM-2-EX", source="A=(x+2)/(x-4), B=3/(x+5): domain of A(B(x))",
         actions=["k3", "t:", "t:2", "t:", "t:-4", "k4", "t:3", "t:", "t:5"],
         driver=enter(1, "A") + enter(2, "B") + ANS + comp_domain(2, 1, "D"),
         expect=["D=ALL REALS, X≠-5,-17/4"], official="domain R, x != -5, -17/4"),
    dict(id="EX-2.4", source="f=√x, g=9-x²: domains of f(g(x)) and g(f(x))",
         actions=["k5", "t:", "t:", "t:", "t:", "k2", "t:-1", "t:0", "t:9"],
         driver=enter(1, "F") + enter(2, "G") + ANS + show_str(2, "G(X)")
         + comp_domain(2, 1, "D(F(G))") + comp_domain(1, 2, "D(G(F))")
         + all_reals() + dom(2) + band(2, "0", "ᴇ99", 1) + show_dom("STEPS F(G)"),
         expect=["G(X)=-X²+9", "D(F(G))=[-3,3]", "D(G(F))=[0,INF)", "STEPS F(G)=[-3,3]"], official="f(g(x)): [-3,3]; g(f(x)): [0,inf)"),
    dict(id="PR-2.4", source="f=√(x-1), g=x²-3x+1: domains of f(g(x)) and g(f(x)); the composite record √(x²-3x)",
         actions=["k5", "t:", "t:", "t:-1", "t:", "k2", "t:", "t:-3", "t:1"],
         driver=enter(1, "F") + enter(2, "G") + ANS
         + comp_domain(2, 1, "D(F(G))") + comp_domain(1, 2, "D(G(F))")
         + ["{2,0,0,1,⁻3,0,0,0,0,0,1,1,0}→ʟF3"] + show_str(3, "F(G(X))") + dom_of(3, "D3"),
         expect=["D(F(G))=(-INF,0]U[3,INF)", "D(G(F))=[1,INF)", "F(G(X))=√(X²-3X)", "D3=(-INF,0]U[3,INF)"],
         official="f(g(x)) = sqrt(x^2 - 3x), domain (-inf,0] U [3,inf); g(f(x)) domain [1,inf)"),
    dict(id="CORR-5", source="f=(x+2)/x², g=(x+1)/(1-x): domain of g(f(x)); the composite (x²+x+2)/(x²-x-2)",
         actions=["k6", "t:0", "t:", "t:2", "t:", "t:0", "t:", "k3", "t:", "t:1", "t:-1", "t:1"],
         driver=enter(1, "F") + enter(2, "G") + ANS + comp_domain(1, 2, "D")
         + ["{1,0,0,1,1,2,0,0,1,⁻1,⁻2,1,0}→ʟF3"] + show_str(3, "G(F(X))"),
         expect=["D=ALL REALS, X≠-1,0,2", "G(F(X))=(X²+X+2)/(X²-X-2)"],
         official="g(f(x)) = (x^2 + x + 2)/(x^2 - x - 2); domain ℝ, x ≠ -1, 0, 2"),
    # ------------------------------------------------------- extra inputs not in the guide
    dict(id="EXTRA-helpers-1", source="fractions and negatives: f(x)=(2/3)x-1/4", actions=["k1", "t:2/3", "t:-1/4"],
         driver=enter(1, "F") + ANS + show_str(1, "F(X)") + zeros_of(1) + show_val(1, "3", "F(3)"),
         expect=["F(X)=(2/3)X-1/4", "ZEROS=3/8", "F(3)=7/4"], official="(extra) zero 3/8, f(3)=7/4"),
    dict(id="EXTRA-helpers-2", source="(AX+B)/(CX+D) with C=0: (2x+4)/2 is just x+2",
         actions=["k3", "t:2", "t:4", "t:0", "t:2"],
         driver=enter(1, "F") + ANS + show_str(1, "F(X)") + dom_of(1) + zeros_of(1),
         expect=["F(X)=X+2", "D=ALL REALS", "ZEROS=-2"], official="(extra)"),
    dict(id="EXTRA-helpers-3", source="bottom typed as 0 is refused, then (x+1)/(x-3)",
         actions=["k3", "t:", "t:1", "t:0", "t:", "t:", "t:-3"],
         driver=enter(1, "F") + ANS + show_str(1, "F(X)"),
         expect=["F(X)=(X+1)/(X-3)"], official="(extra)"),
    dict(id="EXTRA-helpers-4", source="negative K and C: f(x)=-2√(5-x)+1 (the on-screen example)",
         actions=["k5", "t:-2", "t:-1", "t:5", "t:1"],
         driver=enter(1, "F") + ANS + show_str(1, "F(X)") + zeros_of(1) + show_val(1, "1", "F(1)")
         + show_val(1, "6", "F(6)") + all_reals() + band(1, "0", "ᴇ99", 1) + show_dom("F≥0"),
         expect=["F(X)=-2√(-X+5)+1", "ZEROS=19/4", "F(1)=-3", "F(6)=UNDEFINED", "F≥0=[19/4,5]"],
         official="(extra) -2√(5-x)+1=0 at x=19/4; ≥0 on [19/4,5]"),
    dict(id="EXTRA-helpers-5", source="WORDS with an infinite end: D=(-INF,3), f=0 on [0,1]",
         actions=["k8", "t:-I", "t:3", "k4", "t:", "t:1", "t:0", "t:1"],
         driver=enter(1, "F") + ANS + dom_of(1) + zeros_of(1) + all_reals() + dom(1) + zeros(1, "0", 1) + show_dom("D-Z"),
         expect=["D=(-INF,3)", "ZEROS=[0,1]", "D-Z=(-INF,0)U(1,3)"], official="(extra)"),
    dict(id="EXTRA-helpers-6", source="preimage of an interval: 2x+1 in [1,3] and in (1,3)", actions=["k1", "t:2", "t:1"],
         driver=enter(1, "F") + ANS + all_reals() + band(1, "1", "3", 3) + show_dom("CLOSED")
         + all_reals() + band(1, "1", "3", 0) + show_dom("OPEN") + all_reals() + band(1, "⁻ᴇ99", "3", 2) + show_dom("F≤3"),
         expect=["CLOSED=[0,1]", "OPEN=(0,1)", "F≤3=(-INF,1]"], official="(extra)"),
    dict(id="EXTRA-helpers-7", source="1/(x²+1): no real denominator zeros", actions=["k6", "t:0", "t:0", "t:1", "t:", "t:0", "t:1"],
         driver=enter(1, "F") + ANS + show_str(1, "F(X)") + dom_of(1) + zeros_of(1),
         expect=["F(X)=1/(X²+1)", "D=ALL REALS", "ZEROS=NONE"], official="(extra)"),
    dict(id="EXTRA-helpers-8", source="(x²-4)/(x-2): x=2 is not a zero (hole), only -2",
         actions=["k6", "t:", "t:0", "t:-4", "t:0", "t:", "t:-2"],
         driver=enter(1, "F") + ANS + show_str(1, "F(X)") + dom_of(1) + zeros_of(1) + show_val(1, "2", "F(2)"),
         expect=["F(X)=(X²-4)/(X-2)", "D=ALL REALS, X≠2", "ZEROS=-2", "F(2)=UNDEFINED"], official="(extra)"),
    saved_values("EXTRA-helpers-9", "graph level sets (where f(x)=2) and a band [0,2] crossing twice in one segment",
                 zeros(1, "2") + show_zeros("F=2") + all_reals() + band(1, "0", "2", 3) + show_dom("0≤F≤2"),
                 ["F=2=-6,0,2,6", "0≤F≤2=[-6,-4]U[-2,0]U[2,6]"], "(extra)"),
    dict(id="EXTRA-helpers-10", source="saved graph asked for but none saved: status 0", actions=[],
         driver=enter(1, "F", 9) + ANS + show_status(),
         expect=["STATUS=0"], official="(extra)"),
    dict(id="EXTRA-helpers-11", source="CLEAR on the graph menu goes back to the shape menu; then 1:AX+B", lists=EX13,
         actions=["k7", "CLEAR", "k1", "t:", "t:"],
         driver=enter(1, "F") + ANS + show_status() + show_str(1, "F(X)"),
         expect=["STATUS=1", "F(X)=X"], official="(extra)"),
    dict(id="EXTRA-helpers-12", source="CLEAR on the shape menu returns θ=0", actions=["CLEAR"],
         driver=enter(1, "F") + ANS + show_status(), expect=["STATUS=0"], official="(extra)"),
    dict(id="EXTRA-helpers-13", source="fractional K: (1/2)√(x-1); K=0 gives a constant",
         actions=["k5", "t:1/2", "t:", "t:-1", "t:", "k5", "t:0", "t:", "t:", "t:3"],
         driver=enter(1, "F") + enter(2, "G") + ANS + show_str(1, "F(X)") + dom_of(1) + show_val(1, "5", "F(5)")
         + show_str(2, "G(X)"),
         expect=["F(X)=(1/2)√(X-1)", "D=[1,INF)", "F(5)=1", "G(X)=3"], official="(extra)"),
    dict(id="EXTRA-helpers-14", source="records beyond degree 2 are refused (status 0), constant bottoms still work",
         actions=[],
         driver=["{1,0,0,0,0,1,1,0,0,0,⁻1,1,0}→ʟF3"] + ANS + all_reals() + dom(3) + show_status("DOM QUARTIC")
         + ["{1,1,0,0,0,⁻1,0,0,0,0,1,1,0}→ʟF3"] + all_reals() + dom(3) + show_status("DOM X^4-1")
         + zeros(3) + show_status("ZERO X^4-1"),
         expect=["DOM QUARTIC=0", "DOM X^4-1=1", "ZERO X^4-1=0"], official="(extra)"),
    dict(id="EXTRA-helpers-15", source="where a rational is ≥ 0: (x+1)/(x-2)", actions=["k3", "t:", "t:1", "t:", "t:-2"],
         driver=enter(1, "F") + ANS + all_reals() + band(1, "0", "ᴇ99", 1) + show_dom("F≥0"),
         expect=["F≥0=(-INF,-1]U(2,INF)"], official="(extra)"),
    dict(id="EXTRA-helpers-16", source="WORDS with 7 single zeros and 4 zero intervals (screens clear, no scrolling)",
         actions=["k8", "t:-10", "t:20", "k1", "t:7"] + [f"t:{i}" for i in range(1, 8)]
         + ["t:4", "t:8", "t:9", "t:11", "t:10", "t:12", "t:13", "t:14", "t:15"],
         driver=enter(1, "F") + ANS + zeros_of(1),
         expect=["ZEROS=1,2,3,4,5,6,7,[8,9],[10,11],[12,13],[14,15]"], official="(extra)"),
    dict(id="EXTRA-helpers-17", source="g ≥ 0 strictly (g > 0) on the EX-1.3 graph, and g ≤ 0", lists=EX13, actions=[],
         driver=enter(2, "G", 9) + ANS + all_reals() + band(2, "0", "ᴇ99", 0) + show_dom("G>0")
         + all_reals() + band(2, "⁻ᴇ99", "0", 2) + show_dom("G≤0"),
         expect=["G>0=[-5,-2)U(1,5)", "G≤0=[-2,1]U[5,6]"], official="(extra)"),
    dict(id="EXTRA-helpers-18", source="a 0 bottom is refused in K/(AX+B) and in FRACTION WITH X²",
         actions=["k4", "t:3", "t:0", "t:", "t:", "t:2", "k6", "t:0", "t:", "t:1", "t:0", "t:0", "t:", "t:", "t:0", "t:"],
         driver=enter(1, "F") + enter(2, "G") + ANS + show_str(1, "F(X)") + show_str(2, "G(X)") + dom_of(2),
         expect=["F(X)=3/(X+2)", "G(X)=(X+1)/X²", "D=ALL REALS, X≠0"], official="(extra)"),
    dict(id="EXTRA-helpers-19", source="graph menu: CLEAR when the shape was preset returns θ=0; a key for a graph "
         "that is not saved is ignored", lists={k: v for k, v in EX13.items() if k.startswith("ʟGG")},
         actions=["CLEAR", "k2", "k3"],
         driver=enter(1, "F", 7) + ["M→A"] + enter(1, "F", 7) + ANS
         + ["A→θ", "prgmHAFRAC", '"FIRST="+Str9→Str9', "prgmHAOUT"] + show_status("SECOND") + dom_of(1),
         expect=["FIRST=0", "SECOND=1", "D=[-5,6]"], official="(extra)"),
    dict(id="EXTRA-helpers-20", source="root bands: √x≥2, √x≤-1, -√x+2≥0; K=0 gives a constant",
         actions=["k5", "t:", "t:", "t:", "t:", "k5", "t:-1", "t:", "t:", "t:2", "k5", "t:0", "t:", "t:", "t:3"],
         driver=enter(1, "F") + enter(2, "G") + enter(3, "H") + ANS
         + all_reals() + band(1, "2", "ᴇ99", 1) + show_dom("F≥2")
         + all_reals() + band(1, "⁻ᴇ99", "⁻1", 2) + show_dom("F≤-1")
         + all_reals() + band(2, "0", "ᴇ99", 1) + show_dom("G≥0") + show_str(2, "G(X)")
         + all_reals() + band(3, "5", "ᴇ99", 1) + show_dom("H≥5")
         + all_reals() + band(3, "1", "ᴇ99", 1) + show_dom("H≥1"),
         expect=["F≥2=[4,INF)", "F≤-1=NO REAL NUMBERS", "G≥0=[0,4]", "G(X)=-√(X)+2", "H≥5=NO REAL NUMBERS",
                 "H≥1=[0,INF)"], official="(extra)"),
    dict(id="EXTRA-helpers-21", source="level sets that are everything: 0√x+3=3, (2x+4)/(x+2)=2; negative C text",
         actions=["k5", "t:0", "t:", "t:", "t:3", "k3", "t:2", "t:4", "t:", "t:2", "k5", "t:-1", "t:", "t:", "t:-3"],
         driver=enter(1, "F") + enter(2, "G") + enter(3, "H") + ANS
         + zeros(1, "3") + show_zeros("F=3") + zeros(1, "0") + show_zeros("F=0")
         + all_reals() + dom(2) + show_dom("DG") + zeros(2, "2", 1) + show_dom("DG-(G=2)") + show_str(3, "H(X)"),
         expect=["F=3=[-INF,INF]", "F=0=NONE", "DG=ALL REALS, X≠-2", "DG-(G=2)=NO REAL NUMBERS", "H(X)=-√(X)-3"],
         official="(extra)"),
    dict(id="EXTRA-helpers-22", source="WORDS records: a level other than 0 and a band are not known (status 0)",
         actions=["k8", "t:0", "t:4", "k1", "t:1", "t:2", "t:"],
         driver=enter(1, "F") + ANS + zeros(1, "1") + show_status("LEVEL 1")
         + all_reals() + band(1, "0", "ᴇ99", 1) + show_status("BAND") + show_dom("D")
         + ["{2,0,0,0,0,1,0,1,0,0,0,1,0}→ʟF3"] + all_reals() + dom(3) + show_status("ROOT X³"),
         expect=["LEVEL 1=0", "BAND=0", "D=[0,4]", "ROOT X³=0"], official="(extra)"),
    dict(id="EXTRA-helpers-23", source="degree limits and broken records: √(x³), x³ band, a 0 bottom",
         actions=[],
         driver=ANS + ["{2,0,1,0,0,0,0,0,0,0,1,1,0}→ʟF3"] + all_reals() + dom(3) + show_status("ROOT X³")
         + ["{1,0,1,0,0,0,0,0,0,0,1,1,0}→ʟF3"] + all_reals() + dom(3) + show_status("X³ DOM")
         + all_reals() + band(3, "0", "ᴇ99", 1) + show_status("X³ BAND")
         + ["{1,0,0,0,0,1,0,0,0,0,0,1,0}→ʟF3"] + show_str(3, "BAD") + dom_of(3, "BAD D"),
         expect=["ROOT X³=0", "X³ DOM=1", "X³ BAND=0", "BAD=", "BAD D=NO REAL NUMBERS"], official="(extra)"),
    dict(id="EXTRA-helpers-24", source="0 graph points is asked again; √(3x-1) at x=1/3 is 0, not an error",
         actions=["k7", "t:0"] + typed_graph([(0, 1), (2, 3)]) + ["k5", "t:", "t:3", "t:-1", "t:"],
         driver=enter(1, "F") + enter(2, "G") + ANS + dom_of(1) + show_val(1, "1", "F(1)") + show_val(2, "1/3", "G(1/3)"),
         expect=["D=[0,2]", "F(1)=2", "G(1/3)=0"], official="(extra)"),
    dict(id="EXTRA-helpers-25", source="composition domains: 1/(x-3) of √x; graph f of 2x+1; words [0,4] of x²",
         lists=EX13, actions=["k4", "t:", "t:", "t:-3", "k5", "t:", "t:", "t:", "t:", "k1", "t:2", "t:1",
                              "k8", "t:0", "t:4", "k1", "t:", "t:", "k2", "t:", "t:0", "t:"],
         driver=enter(1, "F") + enter(2, "G") + ["ʟF1→L₁", "ʟF2→L₂"] + enter(2, "G") + ["ʟF2→L₃"]
         + enter(1, "W") + enter(2, "Q") + ["ʟF1→L₄", "ʟF2→L₅"] + ANS
         + ["L₁→ʟF1", "L₂→ʟF2"] + comp_domain(2, 1, "F(√(X))")
         + ["L₃→ʟF2"] + enter(1, "F", 9) + comp_domain(2, 1, "GRAPH(2X+1)")
         + ["L₄→ʟF1", "L₅→ʟF2"] + comp_domain(2, 1, "WORDS(X²)"),
         expect=["F(√(X))=[0,9)U(9,INF)", "GRAPH(2X+1)=[-7/2,3]", "WORDS(X²)=[-2,2]"], official="(extra)"),
    dict(id="EXTRA-helpers-26", source="composition domains not handled (status 0) or empty",
         actions=["k8", "t:0", "t:4", "k1", "t:", "t:"],
         driver=enter(2, "W") + ANS
         + ["{2,0,0,0,1,1,0,0,0,1,⁻2,1,0}→ʟF3"] + all_reals() + comp(2, 3) + show_status("ROOT 2 PIECES")
         + ["{1,0,0,0,0,1,0,0,1,0,⁻1,1,0}→ʟF3"] + all_reals() + comp(2, 3) + show_status("RATIONAL OF WORDS")
         + ["{1,0,0,0,0,1,0,0,0,0,0,1,0}→ʟF3"] + comp_domain(2, 3, "ZERO BOTTOM"),
         expect=["ROOT 2 PIECES=0", "RATIONAL OF WORDS=0", "ZERO BOTTOM=NO REAL NUMBERS"], official="(extra)"),
    dict(id="EXTRA-helpers-27", source="composition status 0 for every shape the helpers can not do exactly",
         actions=["k8", "t:0", "t:4", "k1", "t:", "t:"],
         driver=enter(2, "W") + ANS
         + ["{2,0,1,0,0,0,0,0,0,0,1,1,0}→ʟF3"] + all_reals() + comp(2, 3) + show_status("OUT √(X³)")
         + ["{1,0,0,0,0,1,1,0,0,0,0,1,0}→ʟF3"] + all_reals() + comp(2, 3) + show_status("OUT 1/X^4")
         + ["{2,0,0,0,1,0,0,0,0,0,1,1,0}→ʟF3"] + all_reals() + comp(2, 3) + show_status("√(WORDS)")
         + ["{2,0,1,0,0,0,0,0,0,0,1,1,0}→ʟF1"] + all_reals() + comp(1, 3) + show_status("√(√(X³))")
         + ["{1,0,0,0,0,1,0,0,0,1,⁻3,1,0}→ʟF3"] + all_reals() + comp(1, 3) + show_status("1/(√(X³)-3)"),
         expect=["OUT √(X³)=0", "OUT 1/X^4=0", "√(WORDS)=0", "√(√(X³))=0", "1/(√(X³)-3)=0"], official="(extra)"),
    dict(id="EXTRA-helpers-28", source="graph on the x-axis up to a hollow end: (0,0),(2,0),(4,2), left dot hollow; "
         "domain of 1/g",
         actions=["k7"] + typed_graph([(0, 0), (2, 0), (4, 2)], "k2"),
         driver=enter(2, "G") + ANS + zeros_of(2) + quotient_domain(2, 2, "D(1/G)"),
         expect=["ZEROS=[0,2]", "D(1/G)=(2,4]"], official="(extra) zero stretch is reported closed; D(1/g)=(2,4]"),
]


# ---------------------------------------------------------------------------
# runner
# ---------------------------------------------------------------------------
def candidates(lines):
    """Every screen line, plus 2- and 3-row joins of a line HAOUT wrapped (a row 24+ wide)."""
    rows = [l.strip() for l in lines if l.strip() and l.strip() != "ENTER=MORE"]
    out = set(rows)
    for i in range(len(rows)):
        joined = rows[i]
        for k in (1, 2):
            if i + k >= len(rows) or len(rows[i + k - 1]) < 24:  # one screen cell per character
                break
            joined += rows[i + k]
            out.add(joined)
    return out


_BASE = None


def run_hcase(case):
    global _BASE
    if _BASE is None:
        _BASE = load_programs(SRC)
    progs = dict(_BASE)
    progs["DRV1"] = HEAD + case["driver"] + FOOT
    lists = {k: [D(str(x)) for x in v] for k, v in (case.get("lists") or {}).items()}
    m = Machine(progs, persistent_lists=lists)
    actions = list(case["actions"]) + ["ENTER"] * 4 + ["CLEAR"] * 6
    err = None
    try:
        res = m.run(actions, start="DRV1")
    except TIError as e:
        res, err = ("error", None), str(e)
    answers = answer_pages(m.events)
    got = candidates([l for a in answers for l in a])
    missing = [e for e in case["expect"] if e.strip() not in got]
    ok = err is None and res[0] == "stop" and not missing and not m.problems
    return dict(id=case["id"], ok=ok, error=err, end=res, missing=missing, answers=answers,
                problems=list(m.problems), machine=m)


def main():
    fails, covered = 0, set()
    for c in HCASES:
        r = run_hcase(c)
        covered |= r["machine"].covered
        if not r["ok"]:
            fails += 1
            print(f"FAIL {r['id']}: end={r['end']} error={r['error']}")
            if r["missing"]:
                print(f"   missing: {r['missing']}")
            if r["problems"]:
                print(f"   problems: {r['problems'][:5]}")
            for a in r["answers"][-2:]:
                print("   answer: " + " | ".join(a))
            if r["end"][0] != "stop":
                print("   last screen: " + " | ".join(l for l in r["machine"].lines() if l.strip()))
        elif "-v" in sys.argv:
            print(f"ok   {r['id']}: " + " | ".join(" | ".join(a) for a in r["answers"]))
    print(f"{len(HCASES)} helper cases, {len(HCASES) - fails} passed, {fails} failed")
    progs = load_programs(SRC)
    for name in MINE:
        miss = [i + 1 for i in range(len(progs[name])) if (name, i) not in covered]
        print(f"  {name}: {len(progs[name])} lines, not run: {miss if miss else 'none'}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
