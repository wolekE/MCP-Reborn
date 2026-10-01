"""Composition F(G(X)) (main menu 2, program HACOMP). Study guide Section 2, cram sheet 2 and 8.

Function entry is HAFUNC's shape menu (the same screens as solver 1):
  k1 AX+B   k2 AX²+BX+C   k3 (AX+B)/(CX+D)   k4 K/(AX+B)   k5 K√(AX+B)+C
  k6 (AX²+BX+C)/(DX²+EX+F)   k7 graph   k8 words.
ENTER (t:) on a coefficient of X or on K is 1; ENTER on a plain number is 0.
"""

# EX-1.3 graphs (all corners labeled, closed ends), as HPCANS keeps them saved
F_PTS = [(-6, 2), (-3, -1), (1, 3), (4, 0), (7, 3)]
G_PTS = [(-5, 3), (-2, 0), (1, 0), (3, 2), (6, -1)]
EX13 = {"ʟGFX": [p[0] for p in F_PTS], "ʟGFY": [p[1] for p in F_PTS], "ʟGFC": [1, 1],
        "ʟGGX": [p[0] for p in G_PTS], "ʟGGY": [p[1] for p in G_PTS], "ʟGGC": [1, 1]}


def typed(pts, ends="k1"):
    """corner points typed into HAPTS: how many, then X and Y of each, then the end dots"""
    acts = [f"t:{len(pts)}"]
    for x, y in pts:
        acts += [f"t:{x}", f"t:{y}"]
    return acts + [ends]


# shapes as the student types them (HAFUNC)
def lin(a, b):
    return ["k1", f"t:{a}", f"t:{b}"]


def quad(a, b, c):
    return ["k2", f"t:{a}", f"t:{b}", f"t:{c}"]


def ratlin(a, b, c, d):
    return ["k3", f"t:{a}", f"t:{b}", f"t:{c}", f"t:{d}"]


def recip(k, a, b):
    return ["k4", f"t:{k}", f"t:{a}", f"t:{b}"]


def root(k, a, b, c):
    return ["k5", f"t:{k}", f"t:{a}", f"t:{b}", f"t:{c}"]


def frac2(a, b, c, d, e, f):
    return ["k6", f"t:{a}", f"t:{b}", f"t:{c}", f"t:{d}", f"t:{e}", f"t:{f}"]


SQRTX = root("", "", "", "")

ORDER = {1: "F(G(X))", 2: "G(F(X))", 3: "F(F(X))", 4: "G(G(X))"}


def simp(cid, src, order, f, g, expect, official, path, after=None, lists=None):
    """menu 2 → 1:SIMPLIFY + DOMAIN → order → f (unless G(G)) → g (unless F(F)) → answer → 2:HOME"""
    acts = ["k2", "k1", f"k{order}"] + (f if order != 4 else []) + (g if order != 3 else []) \
        + (after or ["k2"])
    case = dict(id=cid, source=src, actions=acts, expect=expect, official=official,
                path=f"2:F(G(X)) → 1:SIMPLIFY + DOMAIN → {order}:{ORDER[order]}; {path}")
    if lists:
        case["lists"] = lists
    return case


VALUE_NAME = {1: "F(G(NUMBER))", 2: "G(F(NUMBER))", 3: "F(F(NUMBER))", 4: "G(G(NUMBER))"}


def saved_value(cid, src, order, x, expect, official):
    return dict(id=cid, source=src, lists=EX13,
                actions=["k2", "k2", f"k{order}", f"t:{x}", "k1", "k2"], expect=expect, official=official,
                graph="EX-1.3 graphs saved (typed once in any menu)",
                path=f"2:F(G(X)) → 2:F(G(5)) FROM GRAPHS → {order}:{VALUE_NAME[order]}; NUMBER={x}; "
                     "1:THE SAVED GRAPH(S)")


CASES = [
    # ----------------------------------------------------------------- Example 2.1
    simp("EX-2.1a", "f(x)=x²-1, g(x)=3x+2: f(g(x)) simplified (and domain)", 1,
         quad("", "0", "-1"), lin("3", "2"),
         ["F(G(X))=9X²+12X+3", "D=ALL REALS"], "f(g(x)) = 9x^2 + 12x + 3; domain R",
         "F: 2:AX²+BX+C A=ENTER B=0 C=-1; G: 1:AX+B A=3 B=2"),
    simp("EX-2.1b", "f(x)=x²-1, g(x)=3x+2: g(f(x)) simplified (and domain)", 2,
         quad("", "0", "-1"), lin("3", "2"),
         ["G(F(X))=3X²-1", "D=ALL REALS"], "g(f(x)) = 3x^2 - 1; domain R",
         "F: 2:AX²+BX+C A=ENTER B=0 C=-1; G: 1:AX+B A=3 B=2"),
    dict(id="EX-2.1c", source="f(x)=x²-1, g(x)=3x+2: check (f o g)(1) = f(g(1)) = f(5) = 24",
         actions=["k2", "k5", "k1", "t:1"] + quad("", "0", "-1") + lin("3", "2") + ["k2"],
         expect=["F(G(1))=24", "G(1)=5", "F(5)=24"], official="(f o g)(1) = f(g(1)) = f(5) = 24",
         path="2:F(G(X)) → 5:F(G(5)) FROM FORMULAS → 1:F(G(NUMBER)); NUMBER=1; F: 2 A=ENTER B=0 C=-1; "
              "G: 1 A=3 B=2"),
    # ----------------------------------------------------------------- Example 2.2 (graphs of Example 1.3)
    saved_value("EX-2.2a", "f(g(5)) from the graphs of Example 1.3", 1, "5",
                ["F(G(5))=2", "G(5)=0", "F(0)=2"], "2"),
    dict(id="EX-2.2b", source="g(f(-6)) from the graphs of Example 1.3 (both graphs typed as corner points)",
         actions=["k2", "k2", "k2", "t:-6", "k2"] + typed(F_PTS) + ["k1"] + typed(G_PTS) + ["k2"],
         expect=["G(F(-6))=1", "F(-6)=2", "G(2)=1"], official="1",
         graph="corners of f and g typed from the figure",
         path="2:F(G(X)) → 2:F(G(5)) FROM GRAPHS → 2:G(F(NUMBER)); NUMBER=-6; 2:TYPE THE CORNER POINTS; "
              "F: 5 points (-6,2) (-3,-1) (1,3) (4,0) (7,3), 1:BOTH SOLID; G: 1:TYPE, 5 points (-5,3) (-2,0) "
              "(1,0) (3,2) (6,-1), 1:BOTH SOLID"),
    dict(id="EX-2.2c", source="g(g(-5)) from the graph of g in Example 1.3 (student reads the two values)",
         actions=["k2", "k2", "k4", "t:-5", "k3", "t:3", "t:2", "k2"],
         expect=["G(G(-5))=2", "G(-5)=3", "G(3)=2"], official="2",
         graph="values read off the figure: g(-5)=3, g(3)=2",
         path="2:F(G(X)) → 2:F(G(5)) FROM GRAPHS → 4:G(G(NUMBER)); NUMBER=-5; 3:READ THEM OFF THE GRAPH; "
              "G(-5)=? 3; G(3)=? 2"),
    saved_value("EX-2.2d", "f(g(-6)) from the graphs of Example 1.3 (-6 is not in D_g=[-5,6])", 1, "-6",
                ["F(G(-6))=UNDEFINED", "G(-6) DOES NOT EXIST"], "undefined"),
    # ----------------------------------------------------------------- Example 2.3 (both orders)
    simp("EX-2.3a", "A(x)=(x+3)/(x-2), B(x)=4/(x+1): simplified A(B(x)) and its domain", 1,
         ratlin("", "3", "", "-2"), recip("4", "", "1"),
         ["F(G(X))=(3X+7)/(-2X+2)", "D=ALL REALS, X≠-1,1"],
         "A(B(x)) = (3x+7)/(2-2x), D_{A o B}: R, x != -1, 1",
         "A as F: 3:(AX+B)/(CX+D) A=ENTER B=3 C=ENTER D=-2; B as G: 4:K/(AX+B) K=4 A=ENTER B=1"),
    simp("EX-2.3b", "A(x)=(x+3)/(x-2), B(x)=4/(x+1): then B(A(x)) and its domain (footer 3:OTHER ORDER)", 1,
         ratlin("", "3", "", "-2"), recip("4", "", "1"),
         ["G(F(X))=(4X-8)/(2X+1)", "D=ALL REALS, X≠-1/2,2"],
         "B(A(x)) = (4x-8)/(2x+1), D_{B o A}: R, x != 2, -1/2",
         "same inputs as EX-2.3a, then 3:OTHER ORDER on the answer screen", after=["k3", "k2"]),
    # ----------------------------------------------------------------- Example 2.4 radicals
    simp("EX-2.4a", "f(x)=√x, g(x)=9-x²: f(g(x)) and its domain", 1,
         SQRTX, quad("-1", "0", "9"),
         ["F(G(X))=√(-X²+9)", "D=[-3,3]"], "f(g(x)) = sqrt(9 - x^2), D: [-3,3]",
         "F: 5:K√(AX+B)+C ENTER×4; G: 2:AX²+BX+C A=-1 B=0 C=9"),
    simp("EX-2.4b", "f(x)=√x, g(x)=9-x²: g(f(x)) and its domain", 2,
         SQRTX, quad("-1", "0", "9"),
         ["G(F(X))=-X+9", "D=[0,INF)"], "g(f(x)) = 9 - x, D: [0,inf)",
         "F: 5:K√(AX+B)+C ENTER×4; G: 2:AX²+BX+C A=-1 B=0 C=9"),
    # ----------------------------------------------------------------- Example 2.5 (graph of f, g = √x)
    dict(id="EX-2.5a", source="g(x)=√x, f = graph of Example 1.3: domain of g(f(x)) = √(f(x))", lists=EX13,
         actions=["k2", "k3", "k1", "k2", "k2"], expect=["D=[-6,-4]U[-2,7]"],
         official="D_{g o f} = [-6,-4] U [-2,7]", graph="EX-1.3 graph of f saved",
         path="2:F(G(X)) → 3:DOMAIN OF √(GRAPH) → 1:THE GRAPH OF F → 2:USE SAVED GRAPH OF F"),
    dict(id="EX-2.5b", source="g(x)=√x, f = graph of Example 1.3: domain of (g/f)(x) = √x/f(x) "
         "(an operations question: main menu 1, solver HAOPS)", lists=EX13,
         actions=["k1", "k1", "k5", "k7", "k2"] + SQRTX + ["k2"], expect=["D(G/F)=[0,4)U(4,7]"],
         official="D = [0,4) U (4,7]", graph="EX-1.3 graph of f saved",
         path="main menu 1:F+G OR F/G → 1:DOMAIN → 5:G/F; F: 7:A GRAPH → 2:USE SAVED GRAPH OF F; "
              "G: 5:K√(AX+B)+C ENTER×4"),
    dict(id="EX-2.5c", source="g(x)=√x, f = graph of Example 1.3: domain of f(g(x)) = f(√x)", lists=EX13,
         actions=["k2", "k4", "k1", "k2", "k1", "k2"], expect=["D=[0,49]"], official="D = [0,49]",
         graph="EX-1.3 graph of f saved",
         path="2:F(G(X)) → 4:DOMAIN OF GRAPH(√(X)) → 1:THE GRAPH OF F → 2:USE SAVED GRAPH OF F → 1:√(X)"),
    # ----------------------------------------------------------------- Practice 2
    simp("PR-2.1a", "f(x)=2x-5, g(x)=x²+x: f(g(x))", 1, lin("2", "-5"), quad("", "", ""),
         ["F(G(X))=2X²+2X-5"], "f(g(x)) = 2x^2 + 2x - 5",
         "F: 1:AX+B A=2 B=-5; G: 2:AX²+BX+C A=ENTER B=ENTER C=ENTER"),
    simp("PR-2.1b", "f(x)=2x-5, g(x)=x²+x: g(f(x))", 2, lin("2", "-5"), quad("", "", ""),
         ["G(F(X))=4X²-18X+20"], "g(f(x)) = 4x^2 - 18x + 20",
         "F: 1:AX+B A=2 B=-5; G: 2:AX²+BX+C A=ENTER B=ENTER C=ENTER"),
    simp("PR-2.2", "f(x)=1/(x-3), g(x)=2/x: f(g(x)) simplified and its domain", 1,
         recip("", "", "-3"), recip("2", "", ""),
         ["F(G(X))=X/(-3X+2)", "D=ALL REALS, X≠0,2/3"], "f(g(x)) = x/(2 - 3x); domain R, x != 0, 2/3",
         "F: 4:K/(AX+B) K=ENTER A=ENTER B=-3; G: 4:K/(AX+B) K=2 A=ENTER B=ENTER"),
    simp("PR-2.3", "A(x)=(x-1)/(x+4), B(x)=5/(x-2): A(B(x)) simplified and its domain", 1,
         ratlin("", "-1", "", "4"), recip("5", "", "-2"),
         ["F(G(X))=(-X+7)/(4X-3)", "D=ALL REALS, X≠3/4,2"], "A(B(x)) = (7 - x)/(4x - 3); domain R, x != 2, 3/4",
         "A as F: 3:(AX+B)/(CX+D) A=ENTER B=-1 C=ENTER D=4; B as G: 4:K/(AX+B) K=5 A=ENTER B=-2"),
    simp("PR-2.4a", "f(x)=√(x-1), g(x)=x²-3x+1: f(g(x)) and its domain", 1,
         root("", "", "-1", ""), quad("", "-3", "1"),
         ["F(G(X))=√(X²-3X)", "D=(-INF,0]U[3,INF)"], "f(g(x)) = sqrt(x^2 - 3x), domain (-inf,0] U [3,inf)",
         "F: 5:K√(AX+B)+C K=ENTER A=ENTER B=-1 C=ENTER; G: 2:AX²+BX+C A=ENTER B=-3 C=1"),
    simp("PR-2.4b", "f(x)=√(x-1), g(x)=x²-3x+1: g(f(x)) and its domain", 2,
         root("", "", "-1", ""), quad("", "-3", "1"),
         ["G(F(X))=X-3√(X-1)", "D=[1,INF)"], "g(f(x)) = x - 3sqrt(x - 1), domain [1,inf)",
         "F: 5:K√(AX+B)+C K=ENTER A=ENTER B=-1 C=ENTER; G: 2:AX²+BX+C A=ENTER B=-3 C=1"),
    saved_value("PR-2.5a", "f(g(1)) from the graphs of Example 1.3", 1, "1", ["F(G(1))=2", "G(1)=0", "F(0)=2"], "2"),
    saved_value("PR-2.5b", "g(f(4)) from the graphs of Example 1.3", 2, "4", ["G(F(4))=0", "F(4)=0", "G(0)=0"], "0"),
    dict(id="PR-2.5c", source="domain of y=√(g(x)) with the graph of g in Example 1.3", lists=EX13,
         actions=["k2", "k3", "k2", "k3", "k2"], expect=["D=[-5,5]"], official="[-5,5]",
         graph="EX-1.3 graph of g saved",
         path="2:F(G(X)) → 3:DOMAIN OF √(GRAPH) → 2:THE GRAPH OF G → 3:USE SAVED GRAPH OF G"),
    # ----------------------------------------------------------------- cram sheet
    simp("CRAM-EX-2", "A=(x+2)/(x-4), B=3/(x+5): A(B(x)) simplified and its domain", 1,
         ratlin("", "2", "", "-4"), recip("3", "", "5"),
         ["F(G(X))=(2X+13)/(-4X-17)", "D=ALL REALS, X≠-5,-17/4"],
         "A(B(x)) = (2x+13)/(-4x-17); Domain: R, x != -5, -17/4",
         "A as F: 3:(AX+B)/(CX+D) A=ENTER B=2 C=ENTER D=-4; B as G: 4:K/(AX+B) K=3 A=ENTER B=5"),
    simp("CRAM-2-EX", "same cram example, B typed as (AX+B)/(CX+D) with a 0 X coefficient on top", 1,
         ratlin("", "2", "", "-4"), ratlin("0", "3", "", "5"),
         ["F(G(X))=(2X+13)/(-4X-17)", "D=ALL REALS, X≠-5,-17/4"],
         "A(B(x)) = (2x + 13)/(-4x - 17); domain R, x != -5, -17/4",
         "A as F: 3 A=ENTER B=2 C=ENTER D=-4; B as G: 3:(AX+B)/(CX+D) A=0 B=3 C=ENTER D=5"),
    simp("CRAM-8b", "f(g(x)) with fractions (new numbers): f=(x+1)/(x-1), g=1/x", 1,
         ratlin("", "1", "", "-1"), recip("", "", ""),
         ["F(G(X))=(X+1)/(-X+1)", "D=ALL REALS, X≠0,1"],
         "substitute, × LCD; domain: x ∈ D_g and g(x) ∈ D_f (here (1+x)/(1-x); R, x ≠ 0, 1)",
         "F: 3 A=ENTER B=1 C=ENTER D=-1; G: 4:K/(AX+B) ENTER×3"),
    dict(id="CRAM-8c", source="√ of a graphed f (new graph): corners (0,-2),(2,2),(4,-2), solid ends; keep f ≥ 0",
         actions=["k2", "k3", "k1"] + typed([(0, -2), (2, 2), (4, -2)]) + ["k2"],
         expect=["D=[1,3]"], official="keep the x's where f ≥ 0 (here [1,3])", graph="corners typed",
         path="2:F(G(X)) → 3:DOMAIN OF √(GRAPH) → 1:THE GRAPH OF F; 3 points (0,-2) (2,2) (4,-2); 1:BOTH SOLID"),
    # ----------------------------------------------------------------- Section 8 correction
    simp("CORR-5", "Review key #6a (corrected): f=(x+2)/x², g=(x+1)/(1-x); g(f(x)) and its domain", 2,
         frac2("0", "", "2", "", "0", ""), ratlin("", "1", "-1", "1"),
         ["G(F(X))=(X²+X+2)/(X²-X-2)", "D=ALL REALS, X≠-1,0,2"],
         "g(f(x)) = (x^2 + x + 2)/(x^2 - x - 2); domain ℝ, x ≠ -1, 0, 2",
         "F: 6:FRACTION WITH X² A=0 B=ENTER C=2 D=ENTER E=0 F=ENTER; G: 3:(AX+B)/(CX+D) A=ENTER B=1 C=-1 D=1"),
    # ----------------------------------------------------------------- extra inputs not in the guide
    simp("EXTRA-comp-1", "negative and fractional coefficients: f=(1/2)x-3, g=-2x²+(1/3)x", 1,
         lin("1/2", "-3"), quad("-2", "1/3", ""),
         ["F(G(X))=-X²+(1/6)X-3", "D=ALL REALS"], "(extra) -x² + x/6 - 3, all reals",
         "F: 1 A=1/2 B=-3; G: 2 A=-2 B=1/3 C=ENTER"),
    simp("EXTRA-comp-2", "fraction coefficient inside a fraction: f=1/(x-3), g=(1/2)x → clear the 1/2", 1,
         recip("", "", "-3"), lin("1/2", ""),
         ["F(G(X))=2/(X-6)", "D=ALL REALS, X≠6"], "(extra) 1/((1/2)x-3) = 2/(x-6), x ≠ 6",
         "F: 4 K=ENTER A=ENTER B=-3; G: 1 A=1/2 B=ENTER"),
    simp("EXTRA-comp-3", "common factor cancels but its restriction stays: f=(x-1)/(x²-1), g=x+2", 1,
         frac2("0", "", "-1", "", "0", "-1"), lin("", "2"),
         ["F(G(X))=1/(X+3)", "D=ALL REALS, X≠-3,-1"], "(extra) (x+1)/((x+1)(x+3)) = 1/(x+3); x ≠ -3, -1",
         "F: 6 A=0 B=ENTER C=-1 D=ENTER E=0 F=-1; G: 1 A=ENTER B=2"),
    simp("EXTRA-comp-4", "zero coefficient and ENTER defaults: f=√(x+4), g=x² (B=0, C=ENTER)", 1,
         root("", "", "4", ""), quad("", "0", ""),
         ["F(G(X))=√(X²+4)", "D=ALL REALS"], "(extra) sqrt(x² + 4), all reals",
         "F: 5 K=ENTER A=ENTER B=4 C=ENTER; G: 2 A=ENTER B=0 C=ENTER"),
    simp("EXTRA-comp-5", "rational outside, root inside: f=1/(x-3), g=√x (an infinity end and a hole)", 1,
         recip("", "", "-3"), SQRTX,
         ["F(G(X))=1/(√(X)-3)", "D=[0,9)U(9,INF)"], "(extra) 1/(sqrt(x)-3), [0,9) U (9,inf)",
         "F: 4 K=ENTER A=ENTER B=-3; G: 5 ENTER×4"),
    simp("EXTRA-comp-6", "root of a root: f=√(x-1), g=√x", 1, root("", "", "-1", ""), SQRTX,
         ["F(G(X))=√(√(X)-1)", "D=[1,INF)"], "(extra) sqrt(sqrt(x)-1), [1,inf)",
         "F: 5 K=ENTER A=ENTER B=-1 C=ENTER; G: 5 ENTER×4"),
    simp("EXTRA-comp-7", "K and C on the outside root, negative inside: f=-2√(4-x)+3, g=x²", 1,
         root("-2", "-1", "4", "3"), quad("", "0", ""),
         ["F(G(X))=-2√(-X²+4)+3", "D=[-2,2]"], "(extra) -2sqrt(4-x²)+3, [-2,2]",
         "F: 5 K=-2 A=-1 B=4 C=3; G: 2 A=ENTER B=0 C=ENTER"),
    simp("EXTRA-comp-8", "F(F(X)) for f=1/x: x, but x ≠ 0 stays", 3, recip("", "", ""), [],
         ["F(F(X))=X", "D=ALL REALS, X≠0"], "(extra) f(f(x)) = x, x ≠ 0", "F: 4:K/(AX+B) ENTER×3"),
    simp("EXTRA-comp-9", "G(G(X)) for g=(2x+1)/(x-3)", 4, [], ratlin("2", "1", "", "-3"),
         ["G(G(X))=(5X-1)/(-X+10)", "D=ALL REALS, X≠3,10"], "(extra) (5x-1)/(10-x), x ≠ 3, 10",
         "G: 3 A=2 B=1 C=ENTER D=-3"),
    simp("EXTRA-comp-10", "root inside a quadratic with a front number: f=x²+2x, g=3√(x+1)-1", 1,
         quad("", "2", ""), root("3", "", "1", "-1"),
         ["F(G(X))=9X+8", "D=[-1,INF)"], "(extra) (3√(x+1)-1)²+2(3√(x+1)-1) = 9x+8, x ≥ -1",
         "F: 2 A=ENTER B=2 C=ENTER; G: 5 K=3 A=ENTER B=1 C=-1"),
    simp("EXTRA-comp-11", "graph outside, formula inside, through menu 1: f = graph of EX-1.3, g=√x", 1,
         ["k7", "k2"], SQRTX, ["D=[0,49]"], "(extra) same as EX-2.5c: [0,49]",
         "F: 7:A GRAPH → 2:USE SAVED GRAPH OF F; G: 5 ENTER×4", lists=EX13),
    simp("EXTRA-comp-12", "formula outside, graph inside, through menu 1: √(f(x)) with f = graph of EX-1.3", 2,
         ["k7", "k2"], SQRTX, ["D=[-6,-4]U[-2,7]"], "(extra) same as EX-2.5a",
         "F: 7:A GRAPH → 2:USE SAVED GRAPH OF F; G: 5 ENTER×4", lists=EX13),
    simp("EXTRA-comp-18", "root inside a quadratic, x and √ terms both stay: f=x²+x, g=3√(x+1)-1", 1,
         quad("", "", ""), root("3", "", "1", "-1"),
         ["F(G(X))=9X+9-3√(X+1)", "D=[-1,INF)"], "(extra) 9(x+1)-3√(x+1) = 9x+9-3√(x+1), x ≥ -1",
         "F: 2 ENTER×3 (x²+x); G: 5 K=3 A=ENTER B=1 C=-1"),
    simp("EXTRA-comp-19", "all-negative top and bottom are flipped: f=(-x-1)/(-x-2), g=x", 1,
         ratlin("-1", "-1", "-1", "-2"), lin("", ""),
         ["F(G(X))=(X+1)/(X+2)", "D=ALL REALS, X≠-2"], "(extra) (x+1)/(x+2), x ≠ -2",
         "F: 3 A=-1 B=-1 C=-1 D=-2; G: 1 ENTER×2"),
    simp("EXTRA-comp-20", "constant outside keeps the inside's restriction: f=5 (A=0), g=1/x", 1,
         lin("0", "5"), recip("", "", ""),
         ["F(G(X))=5", "D=ALL REALS, X≠0"], "(extra) 5, x ≠ 0",
         "F: 1 A=0 B=5; G: 4 ENTER×3"),
    simp("EXTRA-comp-21", "the composite is 0: f=x-1, g=1 (A=0, B=1)", 1,
         lin("", "-1"), lin("0", "1"),
         ["F(G(X))=0", "D=ALL REALS"], "(extra) 0, all reals",
         "F: 1 A=ENTER B=-1; G: 1 A=0 B=1"),
    simp("EXTRA-comp-22", "root of a fraction: f=√x, g=(x+1)/(x-2)", 1,
         SQRTX, ratlin("", "1", "", "-2"),
         ["F(G(X))=√((X+1)/(X-2))", "D=(-INF,-1]U(2,INF)"], "(extra) sqrt((x+1)/(x-2)), (-inf,-1] U (2,inf)",
         "F: 5 ENTER×4; G: 3 A=ENTER B=1 C=ENTER D=-2"),
    simp("EXTRA-comp-23", "fraction outside, root inside: f=(x+1)/(x-1), g=√x", 1,
         ratlin("", "1", "", "-1"), SQRTX,
         ["F(G(X))=(√(X)+1)/(√(X)-1)", "D=[0,1)U(1,INF)"], "(extra) (√x+1)/(√x-1), [0,1) U (1,inf)",
         "F: 3 A=ENTER B=1 C=ENTER D=-1; G: 5 ENTER×4"),
    simp("EXTRA-comp-24", "f given in words (domain [-4,9], no zeros), g=x²: only the domain", 1,
         ["k8", "t:-4", "t:9", "k1", "t:", "t:"], quad("", "0", ""),
         ["D=[-3,3]"], "(extra) x² in [-4,9]: [-3,3]",
         "F: 8:WORDS -4 to 9 [ ], no zeros; G: 2 A=ENTER B=0 C=ENTER"),
    simp("EXTRA-comp-25", "2/x of √x: a lone √ on the bottom", 1,
         recip("2", "", ""), SQRTX,
         ["F(G(X))=2/√(X)", "D=(0,INF)"], "(extra) 2/√x, (0,inf)",
         "F: 4 K=2 A=ENTER B=ENTER; G: 5 ENTER×4"),
    dict(id="EXTRA-comp-26", source="CLEAR always goes back one menu; then f(f(2)) for f=3x+1 from formulas",
         actions=["k2", "k1", "CLEAR", "k3", "CLEAR", "k2", "k1", "t:5", "CLEAR", "k5", "k3", "t:2"]
         + lin("3", "1") + ["k2"],
         expect=["F(F(2))=22", "F(2)=7", "F(7)=22"], official="(extra) f(f(2)) = f(7) = 22",
         path="2 → 1, CLEAR; 3, CLEAR; 2 → 1 → NUMBER=5 → CLEAR; 5 → 3:F(F(NUMBER)); NUMBER=2; F: 1 A=3 B=1"),
    simp("EXTRA-comp-27", "14-digit rounding: A=1/(3x-1), B=(x+1)/(3x); B(x)=1/3 has no solution", 1,
         recip("", "3", "-1"), ratlin("", "1", "3", "0"),
         ["F(G(X))=X", "D=ALL REALS, X≠0"], "(extra) A(B(x)) = 3x/3 = x; R, x ≠ 0",
         "F: 4 K=ENTER A=3 B=-1; G: 3 A=ENTER B=1 C=3 D=0"),
    simp("EXTRA-comp-28", "14-digit rounding in a √ band: f=-2√(1-3x)+1/2, g=(x-1)/(3x-2)", 1,
         root("-2", "-3", "1", "1/2"), ratlin("", "-1", "3", "-2"),
         ["F(G(X))=-2√(1/(3X-2))+1/2", "D=(2/3,INF)"], "(extra) g(x) ≤ 1/3 ⇔ x > 2/3",
         "F: 5 K=-2 A=-3 B=1 C=1/2; G: 3 A=ENTER B=-1 C=3 D=-2"),
    simp("EXTRA-comp-29", "G(G(X)) of g=(-x-2)/(3x+1) is x; g(x)=-1/3 never happens", 4,
         [], ratlin("-1", "-2", "3", "1"),
         ["G(G(X))=X", "D=ALL REALS, X≠-1/3"], "(extra) x, x ≠ -1/3", "G: 3 A=-1 B=-2 C=3 D=1"),
    simp("EXTRA-comp-30", "f(g(x)) is never defined: f=2/(-2x), g=0/(x/2+1/2)", 1,
         ratlin("0", "2", "-2", "0"), recip("0", "1/2", "1/2"),
         ["D=NO REAL NUMBERS"], "(extra) g(x)=0 is a bad input for f everywhere: no real numbers",
         "F: 3 A=0 B=2 C=-2 D=0; G: 4 K=0 A=1/2 B=1/2"),
    dict(id="EXTRA-comp-13", source="read values: f(g(-6)) where -6 is off the graph of g (ENTER = no point)",
         actions=["k2", "k2", "k1", "t:-6", "k3", "t:", "k2"],
         expect=["F(G(-6))=UNDEFINED", "G(-6) DOES NOT EXIST"], official="(extra) undefined",
         path="2 → 2 → 1:F(G(NUMBER)); NUMBER=-6; 3:READ THEM OFF THE GRAPH; G(-6)=? ENTER"),
    dict(id="EXTRA-comp-14", source="formulas: f(g(2)) with f=1/(x-3), g=x+1: g(2)=3 is not in D_f",
         actions=["k2", "k5", "k1", "t:2"] + recip("", "", "-3") + lin("", "1") + ["k2"],
         expect=["F(G(2))=UNDEFINED", "G(2)=3", "F(3) DOES NOT EXIST"], official="(extra) undefined",
         path="2 → 5:F(G(5)) FROM FORMULAS → 1; NUMBER=2; F: 4 K=ENTER A=ENTER B=-3; G: 1 A=ENTER B=1"),
    dict(id="EXTRA-comp-15", source="graph(2x+1) with f = graph of EX-1.3: -6 ≤ 2x+1 ≤ 7", lists=EX13,
         actions=["k2", "k4", "k1", "k2", "k2", "k1", "t:2", "t:1", "k2"],
         expect=["D=[-7/2,3]"], official="(extra) [-7/2,3]",
         path="2 → 4:DOMAIN OF GRAPH(√(X)) → 1:F → 2:SAVED F → 2:SOMETHING ELSE → 1:AX+B A=2 B=1"),
    dict(id="EXTRA-comp-16", source="√(graph) with a hollow end: corners (-2,1),(0,-1),(3,2), left dot open",
         actions=["k2", "k3", "k2"] + typed([(-2, 1), (0, -1), (3, 2)], "k2") + ["k2"],
         expect=["D=(-2,-1]U[1,3]"], official="(extra) (-2,-1] U [1,3]",
         path="2 → 3:DOMAIN OF √(GRAPH) → 2:G; 3 points (-2,1) (0,-1) (3,2); 2:LEFT OPEN"),
    simp("EXTRA-comp-17", "WHY page, then AGAIN: EX-2.3 A(B(x)) then PR-2.2 f(g(x))", 1,
         ratlin("", "3", "", "-2"), recip("4", "", "1"),
         ["F(G(X))=(3X+7)/(-2X+2)", "D=ALL REALS, X≠-1,1", "F(G(X))=X/(-3X+2)", "D=ALL REALS, X≠0,2/3"],
         "(extra) the WHY page leads back; AGAIN asks for new functions",
         "EX-2.3a inputs; 4:WHY; 1:AGAIN; 1:F(G(X)); PR-2.2 inputs",
         after=["k4", "k1", "k1"] + recip("", "", "-3") + recip("2", "", "") + ["k2"]),
]
