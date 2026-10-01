"""Inverses F⁻¹(X) (main menu 3, program HAINV). Study guide Section 4, cram sheet 4,
cram 8d/e/f, Section 8 corrections 2 and 3.

Submenu: 1:FIND F⁻¹(X)  2:VERIFY TWO FUNCTIONS  3:DOMAIN/RANGE OF F⁻¹  4:HAS INVERSE? (HLT)
Shape menu (find, verify, D/R from the formula):
  1:AX+B  2:(AX+B)/(CX+D)  3:A/(BX+C)+D  4:A(BX+C)³+D  5:A³√(BX+C)+D  6:A√(BX+C)+D  7:A(BX+C)^(M/N)+D
Lines and the parts of a fraction are typed with the X key (TOP=5X+2, BOTTOM=X-4, INSIDE=2X+8);
A (front) and D (end number) are plain numbers; ENTER gives A=1, D=0, INSIDE=X.
HLT families: 1:LINE 2:PARABOLA 3:X³ ³√ √ 4:ABS 5:POWER 6:FRACTION 7:e^X LN X 8:[[X]] 9:GRAPH
"""

SHAPE = {"line": "k1", "frac": "k2", "recip": "k3", "cube": "k4", "cbrt": "k5", "sqrt": "k6", "pow": "k7"}
NAMES = {"line": "1:AX+B", "frac": "2:(AX+B)/(CX+D)", "recip": "3:A/(BX+C)+D", "cube": "4:A(BX+C)³+D",
         "cbrt": "5:A³√(BX+C)+D", "sqrt": "6:A√(BX+C)+D", "pow": "7:A(BX+C)^(M/N)+D"}
PROMPTS = {"line": ["Y="], "frac": ["TOP=", "BOTTOM="], "recip": ["A=", "BOTTOM=", "D="],
           "cube": ["A=", "INSIDE=", "D="], "cbrt": ["A=", "INSIDE=", "D="], "sqrt": ["A=", "INSIDE=", "D="],
           "pow": ["POWER=", "A=", "INSIDE=", "D="]}


def fn(shape, *vals):
    """Keys + typed inputs that enter one function on the shape screens, and its words for TESTS.md."""
    acts = [SHAPE[shape]] + [f"t:{v}" for v in vals]
    words = NAMES[shape] + " " + " ".join(f"{p}{v or 'ENTER'}" for p, v in zip(PROMPTS[shape], vals))
    return acts, words


def find(cid, src, shape, vals, expect, official):
    acts, words = fn(shape, *vals)
    return dict(id=cid, source=src, actions=["k3", "k1"] + acts + ["k2"], expect=expect, official=official,
                path=f"3 → 1:FIND F⁻¹(X); {words}")


def verify(cid, src, f, g, expect, official):
    fa, fw = fn(*f)
    ga, gw = fn(*g)
    return dict(id=cid, source=src, actions=["k3", "k2"] + fa + ga + ["k2"], expect=expect, official=official,
                path=f"3 → 2:VERIFY TWO FUNCTIONS; F: {fw}; G: {gw}")


def dr_formula(cid, src, shape, vals, expect, official):
    acts, words = fn(shape, *vals)
    return dict(id=cid, source=src, actions=["k3", "k3", "k2"] + acts + ["k2"], expect=expect, official=official,
                path=f"3 → 3:DOMAIN/RANGE → 2:THE FORMULA; {words}")


BRACKET = {"[]": "k1", "[)": "k2", "(]": "k3", "()": "k4"}


def dr_given(cid, src, dom, rng, expect, official):
    acts = ["k3", "k3", "k1"]
    for left, right, br in (dom, rng):
        acts += [f"t:{left}", f"t:{right}"]
        if "I" not in left or "I" not in right:
            acts.append(BRACKET[br])
    return dict(id=cid, source=src, actions=acts + ["k2"], expect=expect, official=official,
                path=f"3 → 3:DOMAIN/RANGE → 1:D AND R OF F; D: {dom[0]} to {dom[1]} {dom[2]}; "
                     f"R: {rng[0]} to {rng[1]} {rng[2]} (I = infinity)")


HLT_KEY = {"line": "k1", "parab": "k2", "odd": "k3", "abs": "k4", "pow": "k5", "frac": "k6", "exp": "k7",
           "floor": "k8", "graph": "k9"}
HLT_NAME = {"line": "1:LINE", "parab": "2:PARABOLA", "odd": "3:X³ ³√(X) √(X)", "abs": "4:ABS VALUE",
            "pow": "5:POWER", "frac": "6:FRACTION 1/X", "exp": "7:e^X OR LN X", "floor": "8:[[X]]",
            "graph": "9:A GRAPH"}
HLT_PROMPTS = {"parab": ["Y="], "abs": ["A=", "INSIDE=", "D="], "pow": ["POWER=", "A=", "INSIDE=", "D="]}
YES = ["YES, HAS INVERSE", "(PASSES THE HLT)"]


def hlt(cid, src, fam, vals, expect, official, extra=None):
    words = HLT_NAME[fam] + "".join(f" {p}{v or 'ENTER'}" for p, v in zip(HLT_PROMPTS.get(fam, []), vals))
    acts = ["k3", "k4", HLT_KEY[fam]] + (extra or []) + [f"t:{v}" for v in vals]
    return dict(id=cid, source=src, actions=acts + ["k2"], expect=expect, official=official,
                path=f"3 → 4:HAS INVERSE? (HLT); {words}")


def corners(pts, ends="k1"):
    acts = [f"t:{len(pts)}"]
    for x, y in pts:
        acts += [f"t:{x}", f"t:{y}"]
    return acts + [ends]


CASES = [
    # ---- Example 4.1: which have inverses that are functions? (HLT by family) ----
    hlt("EX-4.1a", "Has an inverse function? y=x³-2", "odd", [], YES, "YES: always increasing, passes the HLT"),
    hlt("EX-4.1b", "Has an inverse function? y=(x-1)²", "parab", ["(X-1)²"],
        ["NO, NOT ONE-TO-ONE", "F(0)=1", "F(2)=1", "Y=1 HITS TWICE"], "NO: x=0 and x=2 both give 1"),
    hlt("EX-4.1c", "Has an inverse function? y=|x|+3", "abs", ["", "", "3"],
        ["NO, NOT ONE-TO-ONE", "F(-1)=4", "F(1)=4", "Y=4 HITS TWICE", "(F IS EVEN)"], "NO: even"),
    hlt("EX-4.1d", "Has an inverse function? y=1/x", "frac", [], YES, "YES: each output once"),
    hlt("EX-4.1e", "Has an inverse function? y=√x", "odd", [], YES, "YES"),
    hlt("EX-4.1f", "Has an inverse function? y=e^x", "exp", [], YES, "YES"),
    hlt("EX-4.1g", "Has an inverse function? y=ln x", "exp", [], YES, "YES"),
    hlt("EX-4.1h", "Has an inverse function? y=³√x", "odd", [], YES, "YES"),
    hlt("EX-4.1i", "Has an inverse function? y=x²", "pow", ["2", "", "", ""],
        ["NO, NOT ONE-TO-ONE", "F(-1)=1", "F(1)=1", "Y=1 HITS TWICE", "(F IS EVEN)"], "NO"),
    hlt("EX-4.1j", "Has an inverse function? y=|x|", "abs", ["", "", ""],
        ["NO, NOT ONE-TO-ONE", "F(-1)=1", "F(1)=1", "(F IS EVEN)"], "NO"),
    hlt("EX-4.1k", "Has an inverse function? y=[[x]] (greatest integer)", "floor", [],
        ["NO, NOT ONE-TO-ONE", "F(0)=0", "F(1/2)=0", "Y=0 HITS TWICE"], "NO: flat steps repeat outputs"),
    # ---- worked examples: find ----
    find("EX-4.2", "Find f⁻¹(x) for f(x)=4x-7", "line", ["4X-7"], ["F⁻¹(X)=(X+7)/4"],
         "f^-1(x) = (x + 7)/4. Check: f(2) = 1 and f^-1(1) = 8/4 = 2."),
    find("EX-4.3", "Find f⁻¹(x) for f(x)=³√(2x+5)-1", "cbrt", ["", "2X+5", "-1"], ["F⁻¹(X)=((X+1)³-5)/2"],
         "f^-1(x) = ((x + 1)^3 - 5)/2"),
    find("EX-4.4a", "f(x)=(2x-5)/(3x+4): find the inverse", "frac", ["2X-5", "3X+4"], ["F⁻¹(X)=(-4X-5)/(3X-2)"],
         "f^-1(x) = (-4x - 5)/(3x - 2) (or (4x + 5)/(2 - 3x))"),
    verify("EX-4.4b", "Verify f(f⁻¹(x))=x for f=(2x-5)/(3x+4), f⁻¹=(-4x-5)/(3x-2)",
           ("frac", "2X-5", "3X+4"), ("frac", "-4X-5", "3X-2"),
           ["YES, INVERSES", "F(G(X))=-23X/-23=X"],
           "f(f^-1(x)) = (-8x - 10 - 15x + 10)/(-12x - 15 + 12x - 8) = -23x/-23 = x"),
    verify("EX-4.4c", "Verify f⁻¹(f(x))=x for the same pair (G is f⁻¹, so G(F(X)) is f⁻¹(f(x)))",
           ("frac", "2X-5", "3X+4"), ("frac", "-4X-5", "3X-2"),
           ["YES, INVERSES", "G(F(X))=-23X/-23=X"],
           "f^-1(f(x)) = (-8x + 20 - 15x - 20)/(6x - 15 - 6x - 8) = -23x/-23 = x. Both compositions give x."),
    find("EX-4.5", "f(x)=3√(x-1)+2: find f⁻¹(x) with its restriction", "sqrt", ["3", "X-1", "2"],
         ["F⁻¹(X)=((X-2)/3)²+1", "FOR X≥2", "D=[2,INF)", "R=[1,INF)"],
         "f^-1(x) = ((x - 2)/3)^2 + 1, x >= 2 (D_{f^-1} = R_f = [2, ∞))"),
    find("EX-4.6", "f(x)=2(x-4)^(3/5)+1: find f⁻¹(x)", "pow", ["3/5", "2", "X-4", "1"],
         ["F⁻¹(X)=((X-1)/2)^(5/3)+4"], "f^-1(x) = ((x - 1)/2)^(5/3) + 4 (no domain restriction)"),
    verify("EX-4.7a", "Are f(x)=2/(x-1) and g(x)=(x+2)/2 inverses?", ("frac", "2", "X-1"), ("frac", "X+2", "2"),
           ["NO, NOT INVERSES", "F(G(X))=4/X≠X"], "Not inverses: f(g(x)) = 4/x ≠ x."),
    find("EX-4.7b", "The true inverse of f(x)=2/(x-1)", "frac", ["2", "X-1"], ["F⁻¹(X)=(X+2)/X"],
         "f^-1(x) = 2/x + 1 = (x + 2)/x"),
    dr_given("EX-4.8", "f one-to-one, D_f=[-1,9), R_f=(-∞,4]: D and R of f⁻¹",
             ("-1", "9", "[)"), ("-I", "4", "(]"), ["D=(-INF,4]", "R=[-1,9)"],
             "D_{f^-1} = (-∞, 4]; R_{f^-1} = [-1, 9)"),
    # ---- practice 4 (answers from Section 9) ----
    find("PR-4.1", "Find f⁻¹(x) for f(x)=-3x+9", "line", ["-3X+9"], ["F⁻¹(X)=(9-X)/3"],
         "f^-1(x) = (9 - x)/3 = -x/3 + 3"),
    find("PR-4.2", "Find f⁻¹(x) for f(x)=(x+2)³-1", "cube", ["", "X+2", "-1"], ["F⁻¹(X)=³√(X+1)-2"],
         "f^-1(x) = cbrt(x + 1) - 2"),
    find("PR-4.3", "Find f⁻¹(x) for f(x)=(5x+2)/(x-4)", "frac", ["5X+2", "X-4"], ["F⁻¹(X)=(4X+2)/(X-5)"],
         "f^-1(x) = (4x + 2)/(x - 5)"),
    find("PR-4.4", "Find f⁻¹(x) for f(x)=6/(2x+1)", "frac", ["6", "2X+1"], ["F⁻¹(X)=(6-X)/(2X)"],
         "f^-1(x) = (6 - x)/(2x) (= 3/x - 1/2)"),
    verify("PR-4.5", "Verify both ways: f(x)=(x-1)/(x+2), g(x)=(2x+1)/(1-x)",
           ("frac", "X-1", "X+2"), ("frac", "2X+1", "1-X"),
           ["YES, INVERSES", "F(G(X))=3X/3=X", "G(F(X))=3X/3=X"],
           "f(g(x)) = 3x/3 = x and g(f(x)) = 3x/3 = x. Both give x: they are inverses."),
    find("PR-4.6", "f(x)=4√(x+2)-3: f⁻¹(x), its domain and range", "sqrt", ["4", "X+2", "-3"],
         ["F⁻¹(X)=((X+3)/4)²-2", "FOR X≥-3", "D=[-3,INF)", "R=[-2,INF)"],
         "f^-1(x) = ((x + 3)/4)^2 - 2, domain [-3, ∞), range [-2, ∞)"),
    dr_given("PR-4.7", "g one-to-one, domain (-5,3], range [0,12): domain and range of g⁻¹",
             ("-5", "3", "(]"), ("0", "12", "[)"), ["D=[0,12)", "R=(-5,3]"],
             "D_{g^-1} = [0, 12), R_{g^-1} = (-5, 3]"),
    hlt("PR-4.8", "Why does f(x)=x⁴+1 have no inverse function? (a specific pair of points)", "pow",
        ["4", "", "", "1"], ["NO, NOT ONE-TO-ONE", "F(-1)=2", "F(1)=2", "Y=2 HITS TWICE", "(F IS EVEN)"],
        "f(1) = 2 and f(-1) = 2. The horizontal line y = 2 hits the graph twice, so f fails the HLT. (f is even.)"),
    # ---- cram sheet ----
    find("CRAM-EX-4a", "f=(1+3x)/(5-2x): f⁻¹", "frac", ["1+3X", "5-2X"], ["F⁻¹(X)=(5X-1)/(2X+3)"],
         "f^-1(x) = (5x-1)/(2x+3)"),
    find("CRAM-EX-4b", "f=7√x+4: f⁻¹ with its restriction", "sqrt", ["7", "", "4"],
         ["F⁻¹(X)=((X-4)/7)²", "FOR X≥4"], "f^-1(x) = ((x-4)/7)^2 for x >= 4 (the range of f)"),
    find("CRAM-8d", "Find f⁻¹ (rational: factor out y): f(x)=(3x+1)/(x-2)", "frac", ["3X+1", "X-2"],
         ["F⁻¹(X)=(2X+1)/(X-3)"], "swap x and y, solve; rational: factor out y -> (2x+1)/(x-3)"),
    verify("CRAM-8e", "Are they inverses? compose both ways: f(x)=2x+3, g(x)=(x-3)/2",
           ("line", "2X+3"), ("frac", "X-3", "2"), ["YES, INVERSES", "F(G(X))=2X/2=X", "G(F(X))=2X/2=X"],
           "compose both ways; both must give x"),
    hlt("CRAM-8f", "Inverse is a function? (HLT; even => no): y=x²-2 (the page-13 graph)", "parab", ["X²-2"],
        ["NO, NOT ONE-TO-ONE", "F(-1)=-1", "F(1)=-1", "Y=-1 HITS TWICE", "(F IS EVEN)"],
        "horizontal line test; even => no (y = x^2 - 2 fails the HLT)"),
    # ---- Section 8 corrections ----
    verify("CORR-2", "Quiz review #8 (f(x)=36/(x+18), g(x)=x-3, read from the corrected work 36/(x-3+18))",
           ("frac", "36", "X+18"), ("line", "X-3"), ["NO, NOT INVERSES", "F(G(X))=36/(X+15)≠X"],
           "f(g(x)) = 36/(x + 15); not inverses"),
    verify("CORR-3", "Quiz review #9: f(x)=-³√(2x+8)+3 and g(x)=(1/2)(3-x)³-4", ("cbrt", "-", "2X+8", "3"),
           ("cube", "1/2", "3-X", "-4"), ["YES, INVERSES", "F(G(X))=X", "G(F(X))=X"],
           "They ARE inverses: f(g(x)) = x and g(f(x)) = x"),
    # ---- common mistakes with a program check ----
    find("MIST-4-7", "x^(2/3) is even: it has no inverse function", "pow", ["2/3", "", "", ""],
         ["NO INVERSE FUNCTION", "(NOT ONE-TO-ONE)", "F(-1)=1", "F(1)=1", "(F IS EVEN)"],
         "an even function like x^2 or x^(2/3) has no inverse function"),
    dict(id="FIG-4-GRAPHS", source="Page-13 figure: y=(1/4)x³ passes the HLT", path="3 → 4:HLT; 3:X³",
         actions=["k3", "k4", "k3", "k2"], expect=YES, official="y = (1/4)x^3: passes"),
    # ---- extra shapes and edge cases ----
    find("EXTRA-inv-1", "Negative and fraction numbers: f(x)=-(1/2)√(3-2x)+5", "sqrt", ["-1/2", "3-2X", "5"],
         ["F⁻¹(X)=(3-(10-2X)²)/2", "FOR X≤5", "D=(-INF,5]", "R=(-INF,3/2]"],
         "f^-1(x) = (3 - (10 - 2x)^2)/2, x <= 5; D = (-∞,5], R = (-∞,3/2]"),
    find("EXTRA-inv-2", "Zero coefficients: f(x)=5/x", "frac", ["5", "X"], ["F⁻¹(X)=5/X"], "f^-1(x) = 5/x"),
    find("EXTRA-inv-3", "All ENTER: f(x)=√x", "sqrt", ["", "", ""],
         ["F⁻¹(X)=X²", "FOR X≥0", "D=[0,INF)", "R=[0,INF)"], "f^-1(x) = x^2, x >= 0"),
    find("EXTRA-inv-4", "Fraction slope: f(x)=x/2+3", "line", ["X/2+3"], ["F⁻¹(X)=2X-6"], "f^-1(x) = 2x - 6"),
    find("EXTRA-inv-5", "Reciprocal plus a number: f(x)=3/(x-2)+1", "recip", ["3", "X-2", "1"],
         ["F⁻¹(X)=(2X+1)/(X-1)"], "f^-1(x) = 3/(x-1) + 2 = (2x+1)/(x-1)"),
    find("EXTRA-inv-6", "Constant fraction: f(x)=(2x+4)/(x+2)", "frac", ["2X+4", "X+2"],
         ["NO INVERSE FUNCTION", "(F IS A CONSTANT)"], "f = 2 for every allowed x: no inverse function"),
    find("EXTRA-inv-7", "Negative power: f(x)=x^(-3)", "pow", ["-3", "", "", ""],
         ["F⁻¹(X)=X^(-1/3)", "FOR X≠0", "D=ALL REALS, X≠0", "R=ALL REALS, Y≠0"], "f^-1(x) = x^(-1/3), x ≠ 0"),
    find("EXTRA-inv-8", "Cube with a front number: f(x)=-2(x+1)³+5", "cube", ["-2", "X+1", "5"],
         ["F⁻¹(X)=³√((5-X)/2)-1"], "f^-1(x) = cbrt((5 - x)/2) - 1"),
    dr_formula("EXTRA-inv-9", "D and R of the inverse from the formula: f(x)=(2x-5)/(3x+4)", "frac",
               ["2X-5", "3X+4"], ["FOR F⁻¹:", "D=ALL REALS, X≠2/3", "R=ALL REALS, Y≠-4/3"],
               "D_{f^-1} = R_f: x ≠ 2/3; R_{f^-1} = D_f: y ≠ -4/3"),
    dr_formula("EXTRA-inv-10", "D and R of the inverse from the formula: f(x)=4√(x+2)-3 (PR-4.6)", "sqrt",
               ["4", "X+2", "-3"], ["D=[-3,INF)", "R=[-2,INF)"], "domain [-3, ∞), range [-2, ∞)"),
    dr_given("EXTRA-inv-11", "Infinity ends: D_f=(-∞,∞), R_f=[2,∞)", ("-I", "I", "()"), ("2", "I", "[)"),
             ["D=[2,INF)", "R=ALL REALS"], "D_{f^-1} = [2, ∞); R_{f^-1} = all reals"),
    verify("EXTRA-inv-12", "Not inverses (power shapes, test points): f=(x+2)³-1, g=³√(x-1)-2",
           ("cube", "", "X+2", "-1"), ("cbrt", "", "X-1", "-2"), ["NO, NOT INVERSES", "F(G(X))=X-2≠X", "G(F(-1))=-3≠-1"],
           "f(g(x)) = x - 2 ≠ x: not inverses"),
    verify("EXTRA-inv-13", "Square-root pair: f=7√x+4 and g=((x-4)/7)²", ("sqrt", "7", "", "4"),
           ("pow", "2", "", "(X-4)/7", ""), ["YES, INVERSES", "F(G(X))=X", "G(F(X))=X", "(G NEEDS X≥4)"],
           "inverses when g keeps x >= 4 (the range of f)"),
    verify("EXTRA-inv-14", "Line and cube root: f=2x+1 and g=³√x", ("line", "2X+1"), ("cbrt", "", "", ""),
           ["NO, NOT INVERSES", "F(G(1))=3≠1", "G(F(0))=1≠0"], "f(g(x)) = 2cbrt(x)+1 ≠ x"),
    hlt("EXTRA-inv-15", "Graph with corners (-4,2),(-2,-2),(1,4),(3,0)", "graph", [],
        ["NO, NOT ONE-TO-ONE", "F(-4)=2", "F(0)=2", "Y=2 HITS TWICE"], "fails the HLT",
        extra=["k3"] + corners([(-4, 2), (-2, -2), (1, 4), (3, 0)])),
    hlt("EXTRA-inv-16", "Graph with corners (-2,-1),(0,1),(3,4) (always rising)", "graph", [], YES,
        "passes the HLT", extra=["k3"] + corners([(-2, -1), (0, 1), (3, 4)])),
    hlt("EXTRA-inv-17", "Graph: the student sees a flat line hit twice", "graph", [],
        ["NO, NOT ONE-TO-ONE", "(FAILS THE HLT)"], "fails the HLT", extra=["k1"]),
    hlt("EXTRA-inv-18", "Parabola in standard form: y=x²+4x+1", "parab", ["X²+4X+1"],
        ["NO, NOT ONE-TO-ONE", "F(-3)=-2", "F(-1)=-2"], "x=-3 and x=-1 both give -2"),
    hlt("EXTRA-inv-19", "Odd power: y=x^(3/5)", "pow", ["3/5"], YES, "passes the HLT"),
    find("EXTRA-inv-20", "Minus typed with the subtraction key inside ( ): f(x)=(-2/3)x+4", "line", ["(-2/3)X+4"],
         ["F⁻¹(X)=(12-3X)/2"], "f^-1(x) = (12 - 3x)/2"),
    hlt("EXTRA-inv-21", "Parabola typed with a leading minus: y=-x²+4", "parab", ["-X²+4"],
        ["NO, NOT ONE-TO-ONE", "F(-1)=3", "F(1)=3", "(F IS EVEN)"], "x=-1 and x=1 both give 3"),
    find("EXTRA-inv-22", "Long answer goes on its own line: f(x)=-2(3x+1)^(3/5)+5", "pow", ["3/5", "-2", "3X+1", "5"],
         ["F⁻¹(X)=", "(((5-X)/2)^(5/3)-1)/3"], "f^-1(x) = (((5 - x)/2)^(5/3) - 1)/3"),
    hlt("EXTRA-inv-23", "Has an inverse function? y=-3x+9 (a slanted line)", "line", [],
        ["YES, HAS INVERSE", "(PASSES THE HLT)", "(A FLAT LINE Y=5 IS NO)"], "YES"),
    # ---- adversarial review (fuzz/fuzz_inv.py): one case per bug fixed ----
    verify("REV-inv-1", "Restricted pair with a negative power: f=x^(-2), g=x^(-1/2) (f must keep x>0, not x>=0)",
           ("pow", "-2", "", "", ""), ("pow", "-1/2", "", "", ""),
           ["YES, INVERSES", "F(G(X))=X", "G(F(X))=X", "(F NEEDS X>0)"],
           "inverses when f is restricted to x > 0 (the range of g); was (F NEEDS X≥0)"),
    verify("REV-inv-2", "g undefined on the range of f: f=5√(3x+5)-1, g=-3√(-3x+2)-3",
           ("sqrt", "5", "3X+5", "-1"), ("sqrt", "-3", "-3X+2", "-3"),
           ["NO, NOT INVERSES", "F(G(1)) UNDEFINED", "G(F(-3)) UNDEFINED"],
           "not inverses: 1 is in R_f but g(1) is undefined; was the false claim G(F(X)) UNDEFINED"),
    verify("REV-inv-3", "Composite with a zero bottom: f=1/x, g=0", ("frac", "1", "X"), ("line", "0"),
           ["NO, NOT INVERSES", "F(G(X)) UNDEFINED", "G(F(X))=0≠X"],
           "f(g(x)) = 1/0 is undefined for every x; was F(G(X))=1/0≠X"),
    verify("REV-inv-4", "Constant composite: f=g=-5x/(2x)", ("frac", "-5X", "2X"), ("frac", "-5X", "2X"),
           ["NO, NOT INVERSES", "F(G(X))=-5/2≠X", "G(F(X))=-5/2≠X"],
           "f(g(x)) = -5/2 for every allowed x; was -5X/(2X)≠X"),
    hlt("REV-inv-5", "A flat line typed at PARABOLA: y=5", "parab", ["5"],
        ["NO, NOT ONE-TO-ONE", "F(-1)=5", "F(1)=5", "Y=5 HITS TWICE"], "y = 5 fails the HLT; was YES, HAS INVERSE"),
    hlt("REV-inv-6", "Graph (-2,4),(0,0),(3,6): fails the HLT but is NOT even", "graph", [],
        ["NO, NOT ONE-TO-ONE", "F(-2)=4", "F(2)=4", "Y=4 HITS TWICE"],
        "f(-2) = f(2) = 4; (F IS EVEN) must not be printed (was printed)",
        extra=["k3"] + corners([(-2, 4), (0, 0), (3, 6)])),
    find("REV-inv-7", "Long inverse breaks at a + or - sign: f(x)=-4(-(2/3)x-9)^(-3/4)+7/2", "pow",
         ["-3/4", "-4", "-9-2X/3", "7/2"],
         ["F⁻¹(X)=", "(-3/2)((7-2X)/8)^(-4/3)", "-27/2", "FOR X<7/2", "D=(-INF,7/2)", "R=(-INF,-27/2)"],
         "f^-1(x) = (-3/2)((7-2x)/8)^(-4/3) - 27/2, x < 7/2; was one 29-column line cut inside -27/2"),
    verify("REV-inv-8", "Long composition line breaks after =: f=(5x+2)/(3x+7), g=(4x-9)/(6x+5)",
           ("frac", "5X+2", "3X+7"), ("frac", "4X-9", "6X+5"),
           ["NO, NOT INVERSES", "F(G(X))=(32X-35)/(54X+8)≠X", "G(F(X))=", "(-7X-55)/(45X+47)≠X"],
           "g(f(x)) = (-7x-55)/(45x+47); was cut by the screen edge"),
    find("REV-inv-9", "Fraction in front: f(x)=(2/3)(x-1)³+1", "cube", ["2/3", "X-1", "1"],
         ["F⁻¹(X)=³√((3X-3)/2)+1"], "f^-1(x) = cbrt((3x-3)/2) + 1; was cbrt((3/2)X-3/2)+1"),
    find("REV-inv-10", "Two minus signs cancel: f(x)=-³√(-3x)-8", "cbrt", ["-", "-3X", "-8"],
         ["F⁻¹(X)=(X+8)³/3"], "f^-1(x) = (x+8)^3/3; was -(-X-8)³/3"),
    find("REV-inv-11", "Two minus signs cancel: f(x)=-6(2-5x)³-1", "cube", ["-6", "2-5X", "-1"],
         ["F⁻¹(X)=(³√((X+1)/6)+2)/5"], "f^-1(x) = (cbrt((x+1)/6)+2)/5; was (2-³√((-X-1)/6))/5"),
    find("REV-inv-12", "Tiny coefficients are not a constant: f(x)=(x/9973+1/9967)/(x/9949+1/9941)", "frac",
         ["X/9973+1/9967", "X/9949+1/9941"], ["F⁻¹(X)=", "(1/9967-(1/9941)X)/", "((1/9949)X-1/9973)"],
         "f^-1(x) = (dx-b)/(a-cx); was NO INVERSE FUNCTION (an absolute 1E-10 test on ad-bc)"),
    verify("REV-inv-13", "Values too big to show: f=g=100(100x)^5", ("pow", "5", "100", "100X", ""),
           ("pow", "5", "100", "100X", ""), ["NO, NOT INVERSES", "F(G(1))≠1", "G(F(1))≠1"],
           "f(g(1)) is about 1E72 (shown without the number; it overflowed the screen and the real TI's range)"),
    verify("REV-inv-14", "g undefined on the range of f (rational and root): f=(-5x-1)/(-(7/5)x+2), g=5√(-5x)-7",
           ("frac", "-5X-1", "(-7/5)X+2"), ("sqrt", "5", "-5X", "-7"),
           ["NO, NOT INVERSES", "F(G(1)) UNDEFINED", "G(F(2)) UNDEFINED"],
           "not inverses: 1 is in R_f but g(1) is undefined (a point where g is undefined used to be skipped)"),
]

# lines that must NOT be on the answer screen (run_tests.py checks only lines that must be there;
# run this file directly to check these too)
ABSENT = {"REV-inv-6": ["(F IS EVEN)"]}


def main():
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from harness import describe_failure, run_case
    bad = 0
    for c in CASES:
        r = run_case(c)
        got = [l.strip() for a in r["answers"] for l in a]
        extra = [l for l in ABSENT.get(c["id"], []) if l in got]
        if not r["ok"] or extra:
            bad += 1
            print(describe_failure(r) + (f"\n   lines that must not be there: {extra}" if extra else ""))
    print(f"{len(CASES)} cases, {len(CASES) - bad} passed, {bad} failed")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
