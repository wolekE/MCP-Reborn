"""Absolute value y = A|F(BX+C)+D|+K, A*F(B|X|+C)+K, A*F(|BX+C|)+K (main menu 5). Study guide Section 6, cram 6."""

# base graph from Section 5: A(-4,2), B(-2,-2), C(1,4), D(3,0), solid ends
BASE = ["t:4", "t:-4", "t:2", "t:-2", "t:-2", "t:1", "t:4", "t:3", "t:0", "k1"]
BASE_SAVED = {"ʟBX": [-4, -2, 1, 3], "ʟBY": [2, -2, 4, 0], "ʟBC": [1, 1]}

SHAPE = {1: "1:A|F(BX+C)+D|+K", 2: "2:A*F(B|X|+C)+K", 3: "3:A*F(|BX+C|)+K"}


def _t(v):
    return f"t:{v}"


def _w(v):
    return v if v else "ENTER"


def pts(cid, src, shape, a, b, c, d, k, expect, official, saved=True, graph=None, gdesc=None):
    """1:SKETCH/GRAPH: PTS, D, R on the base graph (saved, or typed with BASE)."""
    acts = ["k5", "k1", f"k{shape}", _t(a), _t(b), _t(c)] + ([_t(d)] if shape == 1 else []) + [_t(k)]
    acts += (["k1"] if saved else []) + (graph if graph is not None else ([] if saved else BASE)) + ["k2"]
    coef = f"A={_w(a)} B={_w(b)} C={_w(c)}" + (f" D={_w(d)}" if shape == 1 else "") + f" K={_w(k)}"
    case = dict(id=cid, source=src, actions=acts, expect=expect, official=official,
                path=f"5 → 1:SKETCH/GRAPH: PTS, D, R → {SHAPE[shape]}; {coef}; "
                     + ("1:USE THE SAVED GRAPH" if saved else
                        (gdesc or "type the corners (-4,2) (-2,-2) (1,4) (3,0), 1:SOLID")),
                graph="base graph corners from the Section 5 figure")
    if saved:
        case["lists"] = BASE_SAVED
    return case


def ivl(lo, hi, br="k1"):
    return [_t(lo), _t(hi), br]


def dom(cid, src, shape, b, c, d_f, expect, official, br="k1"):
    """2:DOMAIN ONLY: asks B, C, then D_f."""
    acts = ["k5", "k2", f"k{shape}", _t(b), _t(c)] + ivl(*d_f, br=br) + ["k2"]
    return dict(id=cid, source=src, actions=acts, expect=expect, official=official,
                path=f"5 → 2:DOMAIN ONLY → {SHAPE[shape]}; B={_w(b)} C={_w(c)}; D_f {d_f[0]} to {d_f[1]}")


def rng1(cid, src, a, d, k, r_f, expect, official, br="k1"):
    """3:RANGE ONLY with bars around f (shape 1): asks A, D, K, then R_f."""
    acts = ["k5", "k3", "k1", _t(a), _t(d), _t(k)] + ivl(*r_f, br=br) + ["k2"]
    return dict(id=cid, source=src, actions=acts, expect=expect, official=official,
                path=f"5 → 3:RANGE ONLY → 1:A|F(BX+C)+D|+K; A={_w(a)} D={_w(d)} K={_w(k)}; R_f {r_f[0]} to {r_f[1]}")


def order(cid, src, shape, a, b, c, d, k, expect, official):
    """5:ORDER OF THE STEPS."""
    acts = ["k5", "k5", f"k{shape}", _t(a), _t(b), _t(c)] + ([_t(d)] if shape == 1 else []) + [_t(k), "k2"]
    coef = f"A={_w(a)} B={_w(b)} C={_w(c)}" + (f" D={_w(d)}" if shape == 1 else "") + f" K={_w(k)}"
    return dict(id=cid, source=src, actions=acts, expect=expect, official=official,
                path=f"5 → 5:ORDER OF THE STEPS → {SHAPE[shape]}; {coef}")


CASES = [
    # ---- Section 6 worked examples ------------------------------------------------------------
    pts("EX-6.1", "y=|f(x)| on the base graph: corners and x-intercepts, D, R", 1, "", "", "", "", "",
        ["(-4,2)  (-3,0)  (-2,2)", "(-1,0)  (1,4)  (3,0)", "D=[-4,3]", "R=[0,4]"],
        "Points (-4,2), (-3,0), (-2,2), (-1,0), (1,4), (3,0); D = [-4, 3], R = [0, 4]"),
    pts("EX-6.2", "y=f(|x|) on the base graph", 2, "", "", "", None, "",
        ["(-3,0)  (-1,4)  (0,2)", "(1,4)  (3,0)", "D=[-3,3]", "R=[0,4]"],
        "Points (-3,0), (-1,4), (0,2), (1,4), (3,0); D = [-3, 3], R = [0, 4]"),
    order("EX-6.3a", "m(x)=-2|f(x-1)|+3: order of the steps", 1, "-2", "", "-1", "", "3",
          ["(1) RIGHT 1", "(2) |Y|: FLIP NEGATIVES UP", "(3) REFLECT X-AXIS", "(4) VERT STRETCH 2", "(5) UP 3"],
          "(1) right 1 (2) |y| (3) multiply y by -2 (reflect over x-axis, vertical stretch by 2) (4) up 3"),
    pts("EX-6.3b", "m(x)=-2|f(x-1)|+3: mapping table with the x-intercepts, D_m, R_m", 1, "-2", "", "-1", "", "3",
        ["(-3,-1)  (-2,3)  (-1,-1)", "(0,3)  (2,-5)  (4,3)", "D=[-3,4]", "R=[-5,3]"],
        "Points (-3,-1), (-2,3), (-1,-1), (0,3), (2,-5), (4,3); D_m = [-3, 4], R_m = [-5, 3]"),
    pts("EX-6.4", "k(x)=|f(x)-3|: points, new x-intercepts, D_k, R_k", 1, "", "", "", "-3", "",
        ["(-4,1)  (-2,5)  (1/2,0)", "(1,1)  (3/2,0)  (3,3)", "D=[-4,3]", "R=[0,5]"],
        "Points (-4,1), (-2,5), (1/2,0), (1,1), (3/2,0), (3,3); D_k = [-4, 3], R_k = [0, 5]"),
    pts("EX-6.4x", "EX-6.4 note: |f(x)|-3 (|y| first, then down 3) has range [-3,1]", 1, "", "", "", "", "-3",
        ["(-4,-1)  (-3,-3)  (-2,-1)", "(-1,-3)  (1,1)  (3,-3)", "D=[-4,3]", "R=[-3,1]"],
        "(|f(x)| - 3 would have range [-3, 1])"),
    dom("EX-6.5-a", "D_f=[-3,4], R_f=[-5,2]: domain of 3f(|x|)-2", 2, "", "", ("-3", "4"),
        ["D=[-4,4]"], "[-4, 4]"),
    rng1("EX-6.5-b", "D_f=[-3,4], R_f=[-5,2]: range of 3|f(x)|-2", "3", "", "-2", ("-5", "2"),
         ["R=[-2,13]"], "[-2, 13]"),
    dict(id="EX-6.5-c", source="D_f=[-3,4], R_f=[-5,2]: domain and range of k(x)=-f(2x-6)+1 (no bars)",
         actions=["k4", "k3", "t:-1", "t:2", "t:-6", "t:1", "k1", "t:-3", "t:4", "k1", "t:-5", "t:2", "k1", "k2"],
         expect=["D=[3/2,5]", "R=[-1,6]"], official="D_k = [3/2, 5], R_k = [-1, 6]",
         path="no bars, so main menu 4 → 3:NEW DOMAIN AND RANGE; A=-1 B=2 C=-6 K=1; 1:D AND R; D -3 to 4 [ ]; "
              "R -5 to 2 [ ]"),
    dict(id="EX-6.5-d", source="D_f=[-3,4], R_f=[-5,2]: why not the range of f(|x|)?",
         actions=["k5", "k3", "k2", "t:", "t:", "t:", "t:"] + ivl("-3", "4") + ["k2"],
         expect=["R CAN NOT BE FOUND FROM", "D AND R ALONE: IT DEPENDS", "ON WHAT F DOES FOR X≥0"],
         official="It depends on which outputs f reaches for x >= 0, and D and R alone don't tell you that.",
         path="5 → 3:RANGE ONLY → 2:A*F(B|X|+C)+K; A,B,C,K=ENTER; D_f -3 to 4 [ ] (R_f is not asked)"),
    # ---- Practice 6 (official answers from Section 9) ----------------------------------------
    pts("PR-6.1", "Sketch y=|f(x)|-2; domain and range (typed base graph)", 1, "", "", "", "", "-2",
        ["(-4,0)  (-3,-2)  (-2,0)", "(-1,-2)  (1,2)  (3,-2)", "D=[-4,3]", "R=[-2,2]"],
        "(-4,0), (-3,-2), (-2,0), (-1,-2), (1,2), (3,-2). D = [-4, 3], R = [-2, 2]", saved=False),
    pts("PR-6.2", "Sketch y=f(|x|)+1; domain and range", 2, "", "", "", None, "1",
        ["(-3,1)  (-1,5)  (0,3)", "(1,5)  (3,1)", "D=[-3,3]", "R=[1,5]"],
        "(-3,1), (-1,5), (0,3), (1,5), (3,1). D = [-3, 3], R = [1, 5]"),
    pts("PR-6.3", "Sketch y=-f(|x|); domain and range", 2, "⁻", "", "", None, "",
        ["(-3,0)  (-1,-4)  (0,-2)", "(1,-4)  (3,0)", "D=[-3,3]", "R=[-4,0]"],
        "(-3,0), (-1,-4), (0,-2), (1,-4), (3,0). D = [-3, 3], R = [-4, 0]"),
    pts("PR-6.4", "Sketch y=|f(x+2)|; domain and range", 1, "", "", "2", "", "",
        ["(-6,2)  (-5,0)  (-4,2)", "(-3,0)  (-1,4)  (1,0)", "D=[-6,1]", "R=[0,4]"],
        "(-6,2), (-5,0), (-4,2), (-3,0), (-1,4), (1,0). D = [-6, 1], R = [0, 4]"),
    dom("PR-6.5a", "D_f=[-5,1], R_f=[-6,-2]: (a) domain of f(|x|)", 2, "", "", ("-5", "1"),
        ["D=[-1,1]"], "(a) [-1, 1]"),
    rng1("PR-6.5b", "D_f=[-5,1], R_f=[-6,-2]: (b) range of |f(x)|", "", "", "", ("-6", "-2"),
         ["R=[2,6]"], "(b) [2, 6]"),
    rng1("PR-6.5c", "D_f=[-5,1], R_f=[-6,-2]: (c) range of -3|f(x)|+1", "-3", "", "1", ("-6", "-2"),
         ["R=[-17,-5]"], "(c) [-17, -5]"),
    dom("PR-6.6", "A function has domain [2,7]. Domain of f(|x|)?", 2, "", "", ("2", "7"),
        ["D=[-7,-2]U[2,7]"], "[-7, -2] U [2, 7]"),
    # ---- Section 9 solution items (same paths; the solution graphs' points) --------------------
    pts("SOL-6.1", "|f(x)| first, then down 2 (saved base graph)", 1, "", "", "", "", "-2",
        ["(-4,0)  (-3,-2)  (-2,0)", "(-1,-2)  (1,2)  (3,-2)", "D=[-4,3]", "R=[-2,2]"],
        "(-4, 0), (-3, -2), (-2, 0), (-1, -2), (1, 2), (3, -2). D = [-4, 3], R = [-2, 2]"),
    pts("SOL-6.4", "Left 2 (intercepts move to -5, -3), then |y| (saved base graph)", 1, "", "", "2", "", "",
        ["(-6,2)  (-5,0)  (-4,2)", "(-3,0)  (-1,4)  (1,0)", "D=[-6,1]", "R=[0,4]"],
        "(-6, 2), (-5, 0), (-4, 2), (-3, 0), (-1, 4), (1, 0). D = [-6, 1], R = [0, 4]"),
    # ---- cram sheet ---------------------------------------------------------------------------
    dom("CRAM-EX-6a", "D_f=[-2,5], R_f=[-4,3]: domain of 2f(|x|)+1", 2, "", "", ("-2", "5"),
        ["D=[-5,5]"], "domain of 2f(|x|) + 1: [-5, 5]"),
    rng1("CRAM-EX-6b", "D_f=[-2,5], R_f=[-4,3]: range of 2|f(x)|+1", "2", "", "1", ("-4", "3"),
         ["R=[1,9]"], "range of 2|f(x)| + 1: [1, 9]"),
    order("CRAM-6.3a", "f(|x|-3): order of the steps", 2, "", "", "-3", None, "",
          ["(1) RIGHT 3", "(2) KEEP X≥0, MIRROR LEFT"], "f(|x| − 3): right 3, then mirror"),
    order("CRAM-6.3b", "f(|x-3|): order of the steps", 3, "", "", "-3", None, "",
          ["(1) KEEP X≥0, MIRROR LEFT", "(2) RIGHT 3"], "f(|x − 3|): mirror, then right 3"),
    order("CRAM-6.3c", "2|f(x+1)|-1: order of the steps", 1, "2", "", "1", "", "-1",
          ["(1) LEFT 1", "(2) |Y|: FLIP NEGATIVES UP", "(3) VERT STRETCH 2", "(4) DOWN 1"],
          "2|f(x + 1)| − 1: left 1, |y|, ×2, down 1"),
    order("CRAM-6.3d", "|f(x)-1|+2: order of the steps", 1, "", "", "", "-1", "2",
          ["(1) DOWN 1", "(2) |Y|: FLIP NEGATIVES UP", "(3) UP 2"], "|f(x) − 1| + 2: down 1, |y|, up 2 (new x-ints)"),
    order("CRAM-8i-a", "|f(x)| → flip the negatives up", 1, "", "", "", "", "",
          ["(1) |Y|: FLIP NEGATIVES UP"], "|f(x)|: flip the negatives up"),
    order("CRAM-8i-b", "f(|x|) → mirror the right side", 2, "", "", "", None, "",
          ["(1) KEEP X≥0, MIRROR LEFT"], "f(|x|): mirror the right side"),
    # ---- common mistakes ----------------------------------------------------------------------
    rng1("MIST-6-5", "Range of |f| from R_f=[-5,2] (not [2,5], not [0,2])", "", "", "", ("-5", "2"),
         ["R=[0,5]"], "[0, 5]"),
    pts("MIST-6-3", "Forgetting x-intercepts: |f(x)| must keep (-3,0) and (-1,0) as corners", 1, "", "", "", "", "",
        ["(-4,2)  (-3,0)  (-2,2)", "(-1,0)  (1,4)  (3,0)"], "x-intercepts become the V corners"),
    # ---- extra checks (not in the guide) ------------------------------------------------------
    pts("EXTRA-abs-1", "f(|x-3|) on the base graph: mirror, then right 3", 3, "", "", "-3", None, "",
        ["(0,0)  (2,4)  (3,2)  (4,4)", "(6,0)", "D=[0,6]", "R=[0,4]"],
        "mirror gives (-3,0),(-1,4),(0,2),(1,4),(3,0); right 3: (0,0),(2,4),(3,2),(4,4),(6,0); D=[0,6], R=[0,4]"),
    pts("EXTRA-abs-2", "f(|x|-3) on the base graph: right 3, then mirror (new point at x=0)", 2, "", "", "-3", None, "",
        ["(-6,0)  (-4,4)  (-1,-2)", "(0,0)  (1,-2)  (4,4)", "(6,0)", "D=[-6,6]", "R=[-2,4]"],
        "shifted corners (-1,2),(1,-2),(4,4),(6,0); cut at x=0 gives (0,0); mirror; D=[-6,6], R=[-2,4]"),
    pts("EXTRA-abs-3", "fractions: (1/2)|f(2x+1)|-1/3 on the base graph", 1, "1/2", "2", "1", "", "-1/3",
        ["(-5/2,2/3)  (-2,-1/3)", "(-3/2,2/3)  (-1,-1/3)", "(0,5/3)  (1,-1/3)", "D=[-5/2,1]", "R=[-1/3,5/3]"],
        "x=(u-1)/2, y=|v|/2-1/3: (-5/2,2/3),(-2,-1/3),(-3/2,2/3),(-1,-1/3),(0,5/3),(1,-1/3); D=[-5/2,1], R=[-1/3,5/3]"),
    pts("EXTRA-abs-4", "|f(-x)| (B negative)", 1, "", "⁻", "", "", "",
        ["(-3,0)  (-1,4)  (1,0)", "(2,2)  (3,0)  (4,2)", "D=[-3,4]", "R=[0,4]"],
        "x=-u: (-3,0),(-1,4),(1,0),(2,2),(3,0),(4,2); D=[-3,4], R=[0,4]"),
    pts("EXTRA-abs-5", "EX-6.3 with the intercepts (-3,0),(-1,0),(0,2) also typed: same corners",
        1, "-2", "", "-1", "", "3",
        ["(-3,-1)  (-2,3)  (-1,-1)", "(0,3)  (2,-5)  (4,3)", "D=[-3,4]", "R=[-5,3]"],
        "the old y-intercept lands at (1,-1) on a segment, so it is not a corner (EX-6.3 note)", saved=False,
        gdesc="type 7 points (-4,2) (-3,0) (-2,-2) (-1,0) (0,2) (1,4) (3,0), 1:SOLID",
        graph=["t:7", "t:-4", "t:2", "t:-3", "t:0", "t:-2", "t:-2", "t:-1", "t:0", "t:0", "t:2", "t:1", "t:4",
               "t:3", "t:0", "k1"]),
    pts("EXTRA-abs-6", "f(|x|) when f lives only on [1,5]: corners (1,1),(3,3),(5,5)", 2, "", "", "", None, "",
        ["(-5,5)  (-1,1)  (1,1)", "(5,5)", "D=[-5,-1]U[1,5]", "R=[1,5]"],
        "two pieces: D=[-5,-1]U[1,5]; (3,3) is not a corner", saved=False,
        gdesc="type 3 points (1,1) (3,3) (5,5), 1:SOLID",
        graph=["t:3", "t:1", "t:1", "t:3", "t:3", "t:5", "t:5", "k1"]),
    pts("EXTRA-abs-7", "|f(x)| with the right end dot hollow", 1, "", "", "", "", "",
        ["(-4,2)  (-3,0)  (-2,2)", "(-1,0)  (1,4)  (3,0)", "D=[-4,3)", "R=[0,4]"],
        "domain [-4,3) (open right end); 0 is still reached at x=-3, -1", saved=False,
        gdesc="type the corners (-4,2) (-2,-2) (1,4) (3,0), 3:RIGHT OPEN",
        graph=BASE[:-1] + ["k3"]),
    dom("EXTRA-abs-8", "D_f=[-2,INF): domain of f(|x|)", 2, "", "", ("-2", "I"), ["D=ALL REALS"], "all reals"),
    dom("EXTRA-abs-9", "D_f=[3,INF): domain of f(|x|)", 2, "", "", ("3", "I"), ["D=(-INF,-3]U[3,INF)"],
        "(-inf,-3] U [3,inf)"),
    dom("EXTRA-abs-10", "D_f=(0,4]: domain of f(|x|) (0 is left out)", 2, "", "", ("0", "4"),
        ["D=[-4,0)U(0,4]"], "[-4,0) U (0,4]", br="k3"),
    dom("EXTRA-abs-11", "D_f=[-6,-1]: domain of f(|x|) (all negative)", 2, "", "", ("-6", "-1"),
        ["D=NO REAL NUMBERS"], "no real numbers"),
    dom("EXTRA-abs-12", "D_f=[-3,5]: domain of f(|2x-1|)", 3, "2", "-1", ("-3", "5"), ["D=[-2,3]"],
        "|2x-1| <= 5: [-2,3]"),
    dom("EXTRA-abs-13", "D_f=[2,7]: domain of f(|x|-3)", 2, "", "-3", ("2", "7"), ["D=[-10,-5]U[5,10]"],
        "5 <= |x| <= 10: [-10,-5] U [5,10]"),
    dom("EXTRA-abs-14", "D_f=[-4,3]: domain of 2|f(-x+1)|-5", 1, "⁻", "1", ("-4", "3"), ["D=[-2,5]"],
        "-x+1 in [-4,3]: [-2,5]"),
    rng1("EXTRA-abs-15", "R_f=(-INF,3]: range of |f(x)|", "", "", "", ("-I", "3"), ["R=[0,INF)"], "[0,inf)",
         br="k3"),
    rng1("EXTRA-abs-16", "R_f=[-4,6]: range of -2|f(x)-1|+3", "-2", "-1", "3", ("-4", "6"), ["R=[-7,3]"],
         "f-1 in [-5,5], |.| in [0,5], -2y+3: [-7,3]"),
    rng1("EXTRA-abs-17", "R_f=(-6,-2]: range of |f(x)| (open end moves)", "", "", "", ("-6", "-2"), ["R=[2,6)"],
         "[2,6)", br="k3"),
    dict(id="EXTRA-abs-18", source="D_f=[1,6], R_f=[-3,2]: domain and range of 2f(|x|)+1 (all of f is used)",
         actions=["k5", "k4", "k2", "t:2", "t:", "t:", "t:1"] + ivl("1", "6") + ivl("-3", "2") + ["k2"],
         expect=["D=[-6,-1]U[1,6]", "R=[-5,5]"], official="D=[-6,-1]U[1,6]; R=2[-3,2]+1=[-5,5]",
         path="5 → 4:D AND R → 2:A*F(B|X|+C)+K; A=2 B,C=ENTER K=1; D_f 1 to 6; R_f -3 to 2"),
    dict(id="EXTRA-abs-19", source="AGAIN: range of |f(x)|, then range of -3|f(x)|+1 (R_f=[-6,-2])",
         actions=["k5", "k3", "k1", "t:", "t:", "t:"] + ivl("-6", "-2")
         + ["k1", "k1", "t:-3", "t:", "t:1"] + ivl("-6", "-2") + ["k2"],
         expect=["R=[2,6]", "R=[-17,-5]"], official="PR-6.5 (b) [2,6] and (c) [-17,-5]",
         path="5 → 3 → 1; ENTER x3; R_f -6 to -2; 1:AGAIN → 1; A=-3 D=ENTER K=1; R_f -6 to -2"),
    dict(id="EXTRA-abs-20", source="A typed as 0 is asked again; then |f(x)| points", lists=BASE_SAVED,
         actions=["k5", "k1", "k1", "t:0", "t:", "t:", "t:", "t:", "t:", "k1", "k2"],
         expect=["(-4,2)  (-3,0)  (-2,2)", "D=[-4,3]", "R=[0,4]"], official="same as EX-6.1",
         path="5 → 1:SKETCH/GRAPH → 1; A=0 (asked again) then ENTER; rest ENTER; saved graph"),
    dict(id="EXTRA-abs-22", source="D_f=[0,5], R_f=[-2,3]: range of f(|x|)+1 (no negative inputs, so all of f is used)",
         actions=["k5", "k3", "k2", "t:", "t:", "t:", "t:1"] + ivl("0", "5") + ivl("-2", "3") + ["k2"],
         expect=["R=[-1,4]"], official="R_f + 1 = [-1,4]",
         path="5 → 3:RANGE ONLY → 2; A,B,C=ENTER K=1; D_f 0 to 5; R_f -2 to 3"),
    dict(id="EXTRA-abs-23", source="D_f=[-3,4], R_f=[-5,2]: domain and range of 3|f(x)|-2 together",
         actions=["k5", "k4", "k1", "t:3", "t:", "t:", "t:", "t:-2"] + ivl("-3", "4") + ivl("-5", "2") + ["k2"],
         expect=["D=[-3,4]", "R=[-2,13]"], official="EX-6.5: D unchanged [-3,4]; R [-2,13]",
         path="5 → 4:D AND R → 1; A=3 B,C,D=ENTER K=-2; D_f -3 to 4; R_f -5 to 2"),
    dict(id="EXTRA-abs-24", source="D_f=[-6,-2]: domain and range of f(|x-1|) (nothing is left)",
         actions=["k5", "k4", "k3", "t:", "t:", "t:-1", "t:"] + ivl("-6", "-2") + ["k2"],
         expect=["D=NO REAL NUMBERS", "R=NO REAL NUMBERS"], official="|x-1| is never negative: empty",
         path="5 → 4:D AND R → 3; A,B=ENTER C=-1 K=ENTER; D_f -6 to -2 (R_f is not asked)"),
    dom("EXTRA-abs-25", "D_f=[10,17]: domain of f(3|x|) (long answer is split after U)", 2, "3", "", ("10", "17"),
        ["D=[-17/3,-10/3]U", "[10/3,17/3]"], "10/3 <= |x| <= 17/3: [-17/3,-10/3] U [10/3,17/3]"),
    # ---- review regressions (each failed before the fix) --------------------------------------
    dict(id="REV-abs-1", source="PR-6.4 |f(x+2)| with the plus sign copied: C typed +2 (was ERR:SYNTAX)",
         lists=BASE_SAVED, actions=["k5", "k1", "k1", "t:", "t:", "t:+2", "t:", "t:", "k1", "k2"],
         expect=["(-6,2)  (-5,0)  (-4,2)", "(-3,0)  (-1,4)  (1,0)", "D=[-6,1]", "R=[0,4]"],
         official="(-6,2), (-5,0), (-4,2), (-3,0), (-1,4), (1,0). D = [-6, 1], R = [0, 4]",
         path="5 → 1 → 1; A,B=ENTER C=+2 D,K=ENTER; saved graph"),
    dict(id="REV-abs-2", source="PR-6.2 f(|x|)+1 with K typed +1 (was ERR:SYNTAX)",
         lists=BASE_SAVED, actions=["k5", "k1", "k2", "t:", "t:", "t:", "t:+1", "k1", "k2"],
         expect=["(-3,1)  (-1,5)  (0,3)", "(1,5)  (3,1)", "D=[-3,3]", "R=[1,5]"],
         official="(-3,1), (-1,5), (0,3), (1,5), (3,1). D = [-3, 3], R = [1, 5]",
         path="5 → 1 → 2; A,B,C=ENTER K=+1; saved graph"),
    dom("REV-abs-3", "D_f=[-3,5]: domain of f(|2x-1|) with B typed 2X (the X was multiplied in)", 3, "2X", "-1",
        ("-3", "5"), ["D=[-2,3]"], "|2x-1| <= 5: [-2,3]"),
    pts("REV-abs-4", "|f(-x)| with B typed -X (the X was multiplied in)", 1, "", "-X", "", "", "",
        ["(-3,0)  (-1,4)  (1,0)", "(2,2)  (3,0)  (4,2)", "D=[-3,4]", "R=[0,4]"],
        "x=-u: (-3,0),(-1,4),(1,0),(2,2),(3,0),(4,2); D=[-3,4], R=[0,4]"),
    order("REV-abs-5", "f(|-x+3|) = f(|x-3|): mirror, then right 3 (no extra REFLECT Y-AXIS step)", 3, "", "⁻", "3",
          None, "", ["(1) KEEP X≥0, MIRROR LEFT", "(2) RIGHT 3"], "f(|x − 3|): mirror, then right 3"),
    order("REV-abs-6", "f(|-2x+3|) = f(|2x-3|): mirror, compress 1/2, right 3/2", 3, "", "-2", "3", None, "",
          ["(1) KEEP X≥0, MIRROR LEFT", "(2) HORIZ COMPRESS 1/2", "(3) RIGHT 3/2"],
          "|2x-3| = u: x = (±u+3)/2: mirror, then x/2, then right 3/2"),
    dict(id="REV-abs-7", source="A typed 0 twice and B typed 0: the screen is drawn again (it used to scroll)",
         lists=BASE_SAVED, actions=["k5", "k1", "k1", "t:0", "t:0", "t:", "t:0", "t:", "t:", "t:", "t:", "t:",
                                    "k1", "k2"],
         expect=["(-4,2)  (-3,0)  (-2,2)", "(-1,0)  (1,4)  (3,0)", "D=[-4,3]", "R=[0,4]"],
         official="same as EX-6.1",
         path="5 → 1 → 1; A=0, A=0 (redrawn), A=ENTER, B=0 (redrawn), then all ENTER; saved graph"),
    dict(id="REV-abs-8", source="saved graph lists that do not match (no end-dot list): asks for the graph "
                                "instead of ERR:INVALID DIM",
         lists={"ʟBX": [-4, -2, 1, 3], "ʟBY": [2, -2, 4, 0], "ʟBC": []},
         actions=["k5", "k1", "k1", "t:", "t:", "t:", "t:", "t:"] + BASE + ["k2"],
         expect=["(-4,2)  (-3,0)  (-2,2)", "(-1,0)  (1,4)  (3,0)", "D=[-4,3]", "R=[0,4]"],
         official="same as EX-6.1", path="5 → 1 → 1; all ENTER; type the base graph (the saved one is broken)"),
    dict(id="EXTRA-abs-26", source="-2|f(-3x+6)-1|+4: all 8 steps numbered (ENTER=MORE after step 7)",
         actions=["k5", "k5", "k1", "t:-2", "t:-3", "t:6", "t:-1", "t:4", "ENTER", "k2"],
         expect=["(1) REFLECT Y-AXIS", "(2) HORIZ COMPRESS 1/3", "(3) RIGHT 2", "(4) DOWN 1",
                 "(5) |Y|: FLIP NEGATIVES UP", "(6) REFLECT X-AXIS", "(7) VERT STRETCH 2", "(8) UP 4"],
         official="x -> (x-6)/(-3): reflect, compress 1/3, right 2; then y-1, |y|, times -2, up 4",
         path="5 → 5:ORDER OF THE STEPS → 1; A=-2 B=-3 C=6 D=-1 K=4; ENTER=MORE"),
    dict(id="EXTRA-abs-21", source="WHY page after a points answer, then AGAIN works", lists=BASE_SAVED,
         actions=["k5", "k1", "k1", "t:-2", "t:", "t:-1", "t:", "t:3", "k1", "k3", "k1", "k2", "t:", "t:", "t:",
                  "t:1", "k1", "k2"],
         expect=["(-3,1)  (-1,5)  (0,3)", "D=[-3,3]", "R=[1,5]"], official="PR-6.2 after EX-6.3's WHY",
         path="5 → 1 → 1 (EX-6.3); 3:WHY; 1:AGAIN → 2; PR-6.2 numbers; saved graph"),
]
