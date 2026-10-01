"""Power functions y = k x^p (main menu 6 "KX^P OR ROOTS", program HAPOWER + HAPOWR2..4).
Study guide Section 7, Section 9 (SOL-7.x), cram sheet 7, cram 8j, cram 9 #9, Section 8 correction 4.

Submenu: 1:FIND K,P  2:SYMMETRY/QUADS  3:ALL PROPERTIES  4:BUILD EQUATION
FIND K,P shape menu (pick the example that looks like the question):
  1:-3X^5  2:-7√(16X^3) (any root)  3:-1/(4X^6)  4:5/(2√(9X)) (any root)  5:3X√(X)  6:2/(X√(X))
  7:Y=7 (no x)  8:Y=2^X (x in the power)
Every number is typed as printed; ENTER = "not shown" (a number or a power of 1, the square root index 2).
"""

FORMS = {1: "1:-3X^5", 2: "2:-7√(16X^3)", 3: "3:-1/(4X^6)", 4: "4:5/(2√(9X))", 5: "5:3X√(X)",
         6: "6:2/(X√(X))", 7: "7:Y=7", 8: "8:Y=2^X"}
PROMPTS = {
    1: ["NUMBER IN FRONT=", "POWER ON X="],
    2: ["NUMBER IN FRONT=", "ROOT INDEX=", "NUMBER UNDER ROOT=", "X POWER UNDER ROOT="],
    3: ["TOP NUMBER=", "BOTTOM NUMBER=", "POWER ON X="],
    4: ["TOP NUMBER=", "NUMBER BEFORE ROOT=", "ROOT INDEX=", "NUMBER UNDER ROOT=", "X POWER UNDER ROOT="],
    5: ["NUMBER IN FRONT=", "X POWER OUTSIDE ROOT=", "ROOT INDEX=", "NUMBER UNDER ROOT=", "X POWER UNDER ROOT="],
    6: ["TOP NUMBER=", "BOTTOM NUMBER=", "X POWER OUTSIDE ROOT=", "ROOT INDEX=", "NUMBER UNDER ROOT=",
        "X POWER UNDER ROOT="],
    7: [], 8: []}
MODES = {2: "2:SYMMETRY/QUADS", 3: "3:ALL PROPERTIES"}
QUADS = {1: "1:I ONLY", 2: "2:IV ONLY", 3: "3:I AND II", 4: "4:III AND IV", 5: "5:I AND III", 6: "6:II AND IV"}
SHAPES_Q1 = {1: "1:INCREASING, CURVING DOWN (LEVELS OFF/SHARP POINT)", 2: "2:INCREASING, CURVING UP (GETS STEEPER)",
             3: "3:DECREASING TOWARD X-AXIS (ASYMPTOTES)"}
SHAPES_Q4 = {1: "1:DECREASING, CURVING UP (LEVELS OFF/SHARP POINT)", 2: "2:DECREASING, CURVING DOWN (GETS STEEPER)",
             3: "3:INCREASING TOWARD X-AXIS (ASYMPTOTES)"}
MORE = ["ENTER", "ENTER", "ENTER"]  # page through ENTER=MORE (extra ENTERs are ignored at the footer)


def show(v):
    return "(-)" if v in ("-", "⁻") else (v if v else "ENTER")


def find(cid, src, form, vals, expect, official, after=("k2",), extra=""):
    words = " ".join(f"{p}{show(v)}" for p, v in zip(PROMPTS[form], vals))
    return dict(id=cid, source=src, actions=["k6", "k1", f"k{form}"] + [f"t:{v}" for v in vals] + list(after),
                expect=expect, official=official,
                path=f"6 → 1:FIND K,P; {FORMS[form]}; {words}{extra}".rstrip("; "))


def props(cid, src, mode, k, p, expect, official):
    return dict(id=cid, source=src, actions=["k6", f"k{mode}", f"t:{k}", f"t:{p}"] + MORE + ["k2"],
                expect=expect, official=official,
                path=f"6 → {MODES[mode]}; K={show(k)} P={p}")


def build(cid, src, quad, shape, expect, official):
    return dict(id=cid, source=src, actions=["k6", "k4", f"k{quad}", f"k{shape}", "k2"],
                expect=expect, official=official,
                path=f"6 → 4:BUILD EQUATION; {QUADS[quad]}; {(SHAPES_Q1 if quad % 2 else SHAPES_Q4)[shape]}")


def again(mode, runs):
    """Several K,P pairs in one session through 1:AGAIN."""
    acts = ["k6", f"k{mode}"]
    for i, (k, p) in enumerate(runs):
        acts += [f"t:{k}", f"t:{p}"] + MORE + (["k1"] if i < len(runs) - 1 else ["k2"])
    return acts


CASES = [
    # ---- mandatory regressions from the student -------------------------------------------------
    props("REG-P1", "K=1, P=3/7", 2, "1", "3/7", ["SYMMETRY: ODD (ORIGIN)", "QUADRANTS: I,III"], "ODD, QI,QIII"),
    props("REG-P2", "K=1, P=4/7", 2, "1", "4/7", ["SYMMETRY: EVEN (Y-AXIS)", "QUADRANTS: I,II"], "EVEN, QI,QII"),
    props("REG-P3", "K=1, P=3/2", 3, "1", "3/2",
          ["UNDEFINED FOR X<0", "QUADRANT: I ONLY", "DOMAIN: [0,INF)"], "NEGATIVE X UNDEFINED (D=[0,INF)), QI"),
    props("REG-P4", "K=-1, P=4/7", 2, "-1", "4/7", ["SYMMETRY: EVEN (Y-AXIS)", "QUADRANTS: III,IV"],
          "EVEN, QIII,QIV"),
    props("REG-P5", "K=1, P=-2/1", 3, "1", "-2/1",
          ["P=-2  (EVEN/ODD)", "SYMMETRY: EVEN (Y-AXIS)", "QUADRANTS: I,II", "DOMAIN: (-INF,0)U(0,INF)",
           "ASYMPTOTES: X=0, Y=0", "DISCONTINUOUS AT X=0"],
          "EVEN, X=0 EXCLUDED, ASYMPTOTES X=0,Y=0, QI,QII"),
    find("REG-P6", "Y=-4/(cube root(X^2))", 4, ["-4", "", "3", "", "2"],
         ["Y=-4X^(-2/3)", "K=-4", "P=-2/3"], "K=-4, P=-2/3"),

    # ---- Example 7.1: power function or not? ------------------------------------------------------
    find("EX-7.1-1", "Power function or not? Identify k and p: y = x^5", 1, ["", "5"],
         ["YES, A POWER FUNCTION", "Y=X^5", "K=1", "P=5"], "yes: k = 1, p = 5"),
    find("EX-7.1-2", "Power function or not? Identify k and p: y = -3/x^2", 3, ["-3", "", "2"],
         ["YES, A POWER FUNCTION", "Y=-3X^(-2)", "K=-3", "P=-2"], "yes: k = -3, p = -2"),
    find("EX-7.1-3", "Power function or not? Identify k and p: y = sqrt(25x)", 2, ["", "", "25", ""],
         ["YES, A POWER FUNCTION", "Y=5X^(1/2)", "K=5", "P=1/2"], "yes: k = 5, p = 1/2"),
    find("EX-7.1-4", "Power function or not? Identify k and p: y = 4/cbrt(x)", 4, ["4", "", "3", "", ""],
         ["YES, A POWER FUNCTION", "Y=4X^(-1/3)", "K=4", "P=-1/3"], "yes: k = 4, p = -1/3"),
    find("EX-7.1-5", "Power function or not? y = 7", 7, [],
         ["NOT A POWER FUNCTION", "CONSTANT FUNCTION", "(IT IS KX^0: POWER 0)"],
         "no: constant function (7x^0 has power 0)"),
    find("EX-7.1-6", "Power function or not? y = 2^x", 8, [],
         ["NOT A POWER FUNCTION", "EXPONENTIAL FUNCTION", "(X IS IN THE EXPONENT)"],
         "no: exponential (the variable is in the exponent)"),

    # ---- Example 7.2: in disguise -------------------------------------------------------------------
    find("EX-7.2a", "Write as y = kx^p: y = sqrt(16x^5)", 2, ["", "", "16", "5"],
         ["Y=4X^(5/2)", "K=4", "P=5/2"], "4x^(5/2): k = 4, p = 5/2"),
    find("EX-7.2b", "Write as y = kx^p: y = -6/(4th root of x^3)", 4, ["-6", "", "4", "", "3"],
         ["Y=-6X^(-3/4)", "K=-6", "P=-3/4"], "-6x^(-3/4): k = -6, p = -3/4"),
    find("EX-7.2c", "Write as y = kx^p: y = 5/(2 sqrt(9x))", 4, ["5", "2", "", "9", ""],
         ["Y=(5/6)X^(-1/2)", "K=5/6", "P=-1/2"], "(5/6)x^(-1/2): k = 5/6, p = -1/2"),

    # ---- Examples 7.3, 7.4: full descriptions --------------------------------------------------------
    props("EX-7.3", "Full description of f(x) = -2x^(-2/3)", 3, "-2", "-2/3",
          ["SYMMETRY: EVEN (Y-AXIS)", "QUADRANTS: III,IV", "DOMAIN: (-INF,0)U(0,INF)", "RANGE: (-INF,0)",
           "DISCONTINUOUS AT X=0", "(INFINITE DISCONTINUITY)", "INCREASING: (0,INF)", "DECREASING: (-INF,0)",
           "BOUNDED ABOVE", "ASYMPTOTES: X=0, Y=0", "AS X->+-INF, F(X)->0", "Q4: INCREASING",
           "CURVING DOWN, CONCAVE DOWN"],
          "Domain: (-∞, 0) ∪ (0, ∞) (x ≠ 0); Range: (-∞, 0); Continuity: discontinuous at x = 0 (infinite); "
          "Increasing: (0, ∞); Decreasing: (-∞, 0); Boundedness: bounded above (never reaches 0); "
          "Asymptotes: x = 0 and y = 0; End behavior: lim_{x→±∞} f(x) = 0; Symmetry: even (\"even for x < 0\")"),
    props("EX-7.4", "Describe f(x) = 3x^(5/4)", 3, "3", "5/4",
          ["UNDEFINED FOR X<0", "QUADRANT: I ONLY", "Q1: INCREASING", "CURVING UP, CONCAVE UP",
           "DOMAIN: [0,INF)", "RANGE: [0,INF)", "INCREASING: [0,INF)", "BOUNDED BELOW", "ASYMPTOTES: NONE",
           "AS X->INF, F(X)->INF", "NO LEFT END BEHAVIOR", "THROUGH (0,0) AND (1,3)"],
          "Q1 only, undefined for x < 0; increasing and curving up; Domain [0, ∞), range [0, ∞), increasing on "
          "[0, ∞), bounded below, no asymptotes, lim_{x→∞} f(x) = ∞, no left end behavior. Passes through (0, 0) "
          "and (1, 3)."),

    # ---- Example 7.5: write an equation for each graph ---------------------------------------------
    build("EX-7.5a", "Graph: Q1 & Q2, cusp at the origin, both sides rise concave down", 3, 1,
          ["Y=X^(2/3)"], "y = x^(4/5) (or x^(2/3), x^(8/11))"),
    build("EX-7.5b", "Graph: Q2 & Q4 with asymptotes x=0, y=0", 6, 3,
          ["Y=-X^(-3/5)"], "y = -x^(-3/5) (or -x^(-1/3), -x^(-5/3))"),
    build("EX-7.5c", "Graph: Q4 only, starts flat at the origin and falls more and more steeply", 2, 2,
          ["Y=-X^(3/2)"], "y = -x^(3/2) (or -x^(5/2), -x^(7/4))"),
    build("EX-7.5d", "Graph: Q4 only, vertical tangent at the origin, levels off", 2, 1,
          ["Y=-X^(1/2)"], "y = -x^(1/2) (or -x^(3/4), -x^(5/6))"),

    # ---- Practice 7.1 --------------------------------------------------------------------------------
    find("PR-7.1a", "Write y = -7 (4th root of x) as y = kx^p; state k and p", 2, ["-7", "4", "", ""],
         ["Y=-7X^(1/4)", "K=-7", "P=1/4"], "-7x^(1/4): k = -7, p = 1/4."),
    find("PR-7.1b", "Write y = 2/(x sqrt(x)) as y = kx^p; state k and p", 6, ["2", "", "", "", "", ""],
         ["Y=2X^(-3/2)", "K=2", "P=-3/2"], "2/(x · x^(1/2)) = 2/x^(3/2) = 2x^(-3/2): k = 2, p = -3/2."),
    find("PR-7.1c", "Write y = sqrt(49x^3) as y = kx^p; state k and p", 2, ["", "", "49", "3"],
         ["Y=7X^(3/2)", "K=7", "P=3/2"], "sqrt(49) sqrt(x^3) = 7x^(3/2): k = 7, p = 3/2."),
    find("PR-7.1d", "Write y = -1/(4x^6) as y = kx^p; state k and p", 3, ["-1", "4", "6"],
         ["Y=-(1/4)X^(-6)", "K=-1/4", "P=-6"], "-(1/4)x^(-6): k = -1/4, p = -6."),

    # ---- Practice 7.2 (even / odd / undefined for x<0; quadrants) ----------------------------------
    props("PR-7.2a", "Even, odd, or undefined for x<0, and quadrants: 5x^(3/7)", 2, "5", "3/7",
          ["P=3/7  (ODD/ODD)", "SYMMETRY: ODD (ORIGIN)", "QUADRANTS: I,III"],
          "3/7: odd/odd, so odd; k > 0: Q1 & Q3."),
    props("PR-7.2b", "Even, odd, or undefined for x<0, and quadrants: -x^(6/5)", 2, "-", "6/5",
          ["P=6/5  (EVEN/ODD)", "SYMMETRY: EVEN (Y-AXIS)", "QUADRANTS: III,IV"],
          "6/5: even/odd, so even; k < 0: Q3 & Q4."),
    props("PR-7.2c", "Even, odd, or undefined for x<0, and quadrants: 2x^(-5/2)", 2, "2", "-5/2",
          ["P=-5/2  (ODD/EVEN)", "UNDEFINED FOR X<0", "QUADRANT: I ONLY"],
          "-5/2: denominator even, so undefined for x < 0; k > 0: Q1."),
    props("PR-7.2d", "Even, odd, or undefined for x<0, and quadrants: -4x^(-1/3)", 2, "-4", "-1/3",
          ["P=-1/3  (ODD/ODD)", "SYMMETRY: ODD (ORIGIN)", "QUADRANTS: II,IV"],
          "-1/3: odd/odd, so odd; k < 0: Q2 & Q4."),

    # ---- Practice 7.3 (the part in Q1 or Q4) ---------------------------------------------------------
    props("PR-7.3a", "Describe the Q1/Q4 part of 5x^(3/7)", 2, "5", "3/7",
          ["Q1: INCREASING", "CURVING DOWN, CONCAVE DOWN", "THROUGH (0,0) AND (1,5)"],
          "Q1: increasing, curving down, through (0, 0) and (1, 5)."),
    props("PR-7.3b", "Describe the Q1/Q4 part of -x^(6/5)", 2, "-", "6/5",
          ["Q4: DECREASING", "CURVING DOWN, CONCAVE DOWN", "THROUGH (0,0) AND (1,-1)"],
          "Q4: decreasing, curving down (the p > 1 shape flipped), through (0, 0) and (1, -1)."),
    props("PR-7.3c", "Describe the Q1/Q4 part of 2x^(-5/2)", 2, "2", "-5/2",
          ["Q1: DECREASING", "CURVING UP, CONCAVE UP", "ASYMPTOTES: X=0, Y=0", "THROUGH (1,2)"],
          "Q1: decreasing, curving up, asymptotes x = 0 and y = 0, through (1, 2)."),
    props("PR-7.3d", "Describe the Q1/Q4 part of -4x^(-1/3)", 2, "-4", "-1/3",
          ["Q4: INCREASING", "CURVING DOWN, CONCAVE DOWN", "ASYMPTOTES: X=0, Y=0", "THROUGH (1,-4)"],
          "Q4: increasing toward the x-axis, curving down, asymptotes x = 0 and y = 0, through (1, -4)."),

    # ---- Practice 7.4 ------------------------------------------------------------------------------------
    props("PR-7.4", "Domain, range, increase/decrease, boundedness, asymptotes, end behavior of x^(-4/3)",
          3, "", "-4/3",
          ["SYMMETRY: EVEN (Y-AXIS)", "QUADRANTS: I,II", "DOMAIN: (-INF,0)U(0,INF)", "RANGE: (0,INF)",
           "INCREASING: (-INF,0)", "DECREASING: (0,INF)", "BOUNDED BELOW", "ASYMPTOTES: X=0, Y=0",
           "AS X->+-INF, F(X)->0", "DISCONTINUOUS AT X=0", "(INFINITE DISCONTINUITY)"],
          "p = -4/3: numerator even, denominator odd, so even symmetry; k = 1 > 0, so Q1 & Q2; p < 0, so "
          "asymptotes. Domain (-∞, 0) ∪ (0, ∞); range (0, ∞); increasing on (-∞, 0); decreasing on (0, ∞); "
          "bounded below; asymptotes x = 0, y = 0; lim_{x→±∞} f(x) = 0; infinite discontinuity at x = 0."),

    # ---- Practice 7.5 (write a power function) ------------------------------------------------------
    build("PR-7.5a", "Q1 and Q3, increasing, curving down in Q1", 5, 1, ["Y=X^(3/5)"],
          "Odd/odd with 0 < p < 1, k > 0: y = x^(3/5) (or x^(1/3))."),
    build("PR-7.5b", "Q3 and Q4 with a sharp point at the origin", 4, 1, ["Y=-X^(2/3)"],
          "Even/odd with 0 < p < 1 (that's what makes the sharp point), k < 0: y = -x^(2/3) (or -x^(4/5))."),
    build("PR-7.5c", "Q1 only and decreases toward the x-axis", 1, 3, ["Y=X^(-1/2)"],
          "Even denominator, p < 0, k > 0: y = x^(-1/2) (or x^(-3/4))."),

    # ---- Practice 7.6 ----------------------------------------------------------------------------------
    dict(id="PR-7.6", source="Explain why y = x^(2/3) has a graph for x < 0 but y = x^(3/2) does not",
         actions=again(3, [("", "2/3"), ("", "3/2")]),
         expect=["X^(2/3)=(³√(X))²", "SYMMETRY: EVEN (Y-AXIS)", "DOMAIN: (-INF,INF)",
                 "X^(3/2)=(√(X))³", "UNDEFINED FOR X<0", "DOMAIN: [0,INF)"],
         official="x^(2/3) = (cbrt(x))^2. A cube root of a negative number is real (cbrt(-8) = -2), and squaring "
                  "makes it positive. So x^(2/3) exists for x < 0, with even symmetry. x^(3/2) = (sqrt(x))^3 needs a "
                  "square root first, and sqrt(negative) isn't real. So x^(3/2) is undefined for x < 0.",
         path="6 → 3:ALL PROPERTIES; K=ENTER P=2/3; 1:AGAIN; K=ENTER P=3/2 (3:WHY also shows the root form)"),

    # ---- Cram sheet 7 -----------------------------------------------------------------------------------
    find("CRAM-7.2a", "Rewrite sqrt(4x^3)", 2, ["", "", "4", "3"], ["Y=2X^(3/2)", "K=2", "P=3/2"],
         "sqrt(4x^3) = 2x^(3/2)"),
    find("CRAM-7.2b", "Rewrite -3/sqrt(4x)", 4, ["-3", "", "", "4", ""], ["Y=-(3/2)X^(-1/2)", "K=-3/2", "P=-1/2"],
         "−3/sqrt(4x) = −(3/2)x^(−1/2)"),
    find("CRAM-7.2c", "Rewrite 1/(2 cbrt(x^2))", 4, ["", "2", "3", "", "2"], ["Y=(1/2)X^(-2/3)", "K=1/2", "P=-2/3"],
         "1/(2cbrt(x^2)) = (1/2)x^(−2/3)"),
    props("CRAM-EX-7a", "Ex -x^(4/7)", 3, "-", "4/7",
          ["SYMMETRY: EVEN (Y-AXIS)", "QUADRANTS: III,IV", "RANGE: (-INF,0]", "BOUNDED ABOVE",
           "AS X->+-INF, F(X)->-INF"],
          "even, QIII + QIV, range (−∞, 0], bounded above, f(x) → −∞ as x → ±∞"),
    props("CRAM-EX-7b", "x^(-3/5)", 3, "", "-3/5",
          ["SYMMETRY: ODD (ORIGIN)", "DOMAIN: (-INF,0)U(0,INF)", "RANGE: (-INF,0)U(0,INF)", "ASYMPTOTES: X=0, Y=0",
           "INCREASING: NEVER", "DECREASING: (-INF,0)", "AND ON (0,INF)"],
          "odd, D: x ≠ 0, R: y ≠ 0, asymptotes x = 0, y = 0, decreasing on (−∞, 0) and on (0, ∞)"),
    dict(id="CRAM-8j", source="k x^(a/b): b even QI only; a even even; odd/odd odd; k<0 flip (x^(1/2), x^(2/3), "
                              "x^(1/3), -x^(1/2))",
         actions=again(2, [("", "1/2"), ("", "2/3"), ("", "1/3"), ("-", "1/2")]),
         expect=["UNDEFINED FOR X<0", "QUADRANT: I ONLY", "SYMMETRY: EVEN (Y-AXIS)", "QUADRANTS: I,II",
                 "SYMMETRY: ODD (ORIGIN)", "QUADRANTS: I,III", "QUADRANT: IV ONLY"],
         official="b even: QI only; a even: even; odd/odd: odd; k < 0: flip",
         path="6 → 2:SYMMETRY/QUADS; P=1/2, 1:AGAIN P=2/3, 1:AGAIN P=1/3, 1:AGAIN K=(-) P=1/2"),

    # ---- Section 8 correction ---------------------------------------------------------------------------
    props("CORR-4", "Review key #24 (corrected): f(x) = (2/3)x^(-4)", 3, "2/3", "-4",
          ["SYMMETRY: EVEN (Y-AXIS)", "DECREASING: (0,INF)", "INCREASING: (-INF,0)", "Q1: DECREASING",
           "Q2: INCREASING", "CURVING UP, CONCAVE UP", "THROUGH (1,2/3)"],
          "Decreasing in Q1 (on (0, ∞)); increasing on (-∞, 0) (Q2); concave up; even; k = 2/3"),

    # ---- Common mistakes (Section 7 and cram 9) ---------------------------------------------------------
    props("MIST-7-1", "Not reducing p: x^(2/4) is x^(1/2), so it's Q1 only", 2, "", "2/4",
          ["P=1/2  (ODD/EVEN)", "UNDEFINED FOR X<0", "QUADRANT: I ONLY"], "Not reducing p: x^(2/4) is x^(1/2), so it's Q1 only."),
    dict(id="MIST-7-2", source="Numerator decides even/odd; denominator decides whether x<0 exists (x^(2/3) vs "
                               "x^(3/2))",
         actions=again(2, [("", "2/3"), ("", "3/2")]),
         expect=["P=2/3  (EVEN/ODD)", "SYMMETRY: EVEN (Y-AXIS)", "QUADRANTS: I,II", "P=3/2  (ODD/EVEN)",
                 "UNDEFINED FOR X<0", "QUADRANT: I ONLY"],
         official="Swapping the roles: the numerator decides even or odd; the denominator decides whether x < 0 exists.",
         path="6 → 2:SYMMETRY/QUADS; P=2/3; 1:AGAIN; P=3/2"),
    props("MIST-7-3", "x^(-2) is not odd: numerator -2 is even, so Q1 & Q2", 2, "", "-2",
          ["P=-2  (EVEN/ODD)", "SYMMETRY: EVEN (Y-AXIS)", "QUADRANTS: I,II"], "Calling x^(-2) \"odd\" because of the minus sign. The numerator is -2, which is even, so the graph is in Q1 & Q2."),
    props("CRAM-MIST-9", "Calling x^-2 odd: its numerator -2 is even, so it lives in QI + QII", 2, "", "-2",
          ["SYMMETRY: EVEN (Y-AXIS)", "QUADRANTS: I,II"], "even; QI + QII"),
    find("MIST-7-4", "Number inside k: sqrt(4x^3) = 2x^(3/2), not 4x^(3/2)", 2, ["", "", "4", "3"],
         ["Y=2X^(3/2)", "K=2", "P=3/2"], "Leaving a number inside k unsimplified: sqrt(4x^3) = 2x^(3/2), not 4x^(3/2)."),
    props("MIST-7-5", "k < 0 flips increasing/decreasing: -2x^(3/4) is decreasing in Q4", 2, "-2", "3/4",
          ["QUADRANT: IV ONLY", "Q4: DECREASING"], "Increasing vs. decreasing with k < 0: the flip reverses both. (-2x^(3/4) is decreasing in Q4.)"),
    props("MIST-7-6", "p < 0 is not continuous everywhere: x = 0 isn't in the domain (x^(-1))", 3, "", "-1",
          ["DOMAIN: (-INF,0)U(0,INF)", "DISCONTINUOUS AT X=0"], "Saying a function with p < 0 is continuous everywhere: x = 0 isn't in the domain."),

    # ---- FIND -> ALL PROPERTIES chain, WHY pages -----------------------------------------------------------
    find("EXTRA-power-1", "FIND then 3:ALL PROPS: y = -4/(cube root(x^2)) -> properties of -4x^(-2/3)",
         4, ["-4", "", "3", "", "2"],
         ["K=-4", "P=-2/3", "SYMMETRY: EVEN (Y-AXIS)", "QUADRANTS: III,IV", "RANGE: (-INF,0)",
          "INCREASING: (0,INF)", "THROUGH (1,-4)"],
         "-4x^(-2/3): even, Q3 & Q4, range (-∞,0), increasing on (0,∞)",
         after=["k3"] + MORE + ["k2"], extra="; 3:ALL PROPS"),

    # ---- extra shapes and inputs not in the guide ---------------------------------------------------------
    find("EXTRA-power-2", "sqrt(8x^3): the 8 is not a perfect square", 2, ["", "", "8", "3"],
         ["Y=2√(2)X^(3/2)", "K=2√(2)", "P=3/2"], "2√2 x^(3/2): k = 2√2, p = 3/2"),
    find("EXTRA-power-3", "3/sqrt(2x): root left in the bottom", 4, ["3", "", "", "2", ""],
         ["Y=(3/2)√(2)X^(-1/2)", "K=(3/2)√(2)", "P=-1/2"], "3/√2 = (3/2)√2: k = (3/2)√2, p = -1/2"),
    find("EXTRA-power-4", "cube root of (-8x^2): negative number under an odd root", 2, ["", "3", "-8", "2"],
         ["Y=-2X^(2/3)", "K=-2", "P=2/3"], "-2x^(2/3): k = -2, p = 2/3"),
    find("EXTRA-power-5", "sqrt(-4x): negative under an even root", 2, ["", "", "-4", ""],
         ["NOT A POWER FUNCTION", "(EVEN ROOT OF A NEGATIVE)"], "not of the form kx^p (it is 2√(-x))"),
    find("EXTRA-power-6", "3x sqrt(x)", 5, ["3", "", "", "", ""], ["Y=3X^(3/2)", "K=3", "P=3/2"],
         "3x·x^(1/2) = 3x^(3/2)"),
    find("EXTRA-power-7", "4th root of 81x^2 (p reduces to 1/2)", 2, ["", "4", "81", "2"],
         ["Y=3X^(1/2)", "K=3", "P=1/2"], "3x^(2/4) = 3x^(1/2)"),
    find("EXTRA-power-8", "x^5/4 (fraction in front)", 1, ["1/4", "5"], ["Y=(1/4)X^5", "K=1/4", "P=5"],
         "(1/4)x^5"),
    find("EXTRA-power-9", "-1/x^2 with the top typed as a lone (-)", 3, ["-", "", "2"],
         ["Y=-X^(-2)", "K=-1", "P=-2"], "-x^(-2): k = -1, p = -2"),
    find("EXTRA-power-10", "Bottom number 0 typed by mistake: 5/(0x^2)", 3, ["5", "0", "2"],
         ["UNDEFINED: BOTTOM IS 0"], "undefined"),
    find("EXTRA-power-11", "1/(cube root of 2) x: 1/(cbrt(2x))", 4, ["", "", "3", "2", ""],
         ["Y=(1/2)³√(4)X^(-1/3)", "K=(1/2)³√(4)", "P=-1/3"], "1/∛2 = ∛4/2: k = ∛4/2, p = -1/3"),
    props("EXTRA-power-12", "y = 2x (p = 1)", 3, "2", "1",
          ["P=1  (ODD/ODD)", "SYMMETRY: ODD (ORIGIN)", "QUADRANTS: I,III", "INCREASING: (-INF,INF)",
           "DECREASING: NEVER", "STRAIGHT LINE", "NOT BOUNDED ABOVE OR BELOW", "AS X->INF, F(X)->INF",
           "AS X->-INF, F(X)->-INF", "CONTINUOUS EVERYWHERE"],
          "line through the origin, odd, increasing everywhere"),
    props("EXTRA-power-13", "-(3/4)x^(5/3): k<0 fraction, odd, p>1", 3, "-3/4", "5/3",
          ["SYMMETRY: ODD (ORIGIN)", "QUADRANTS: II,IV", "DOMAIN: (-INF,INF)", "RANGE: (-INF,INF)",
           "INCREASING: NEVER", "DECREASING: (-INF,INF)", "AS X->INF, F(X)->-INF", "AS X->-INF, F(X)->INF",
           "Q4: DECREASING", "CURVING DOWN, CONCAVE DOWN", "Q2: DECREASING", "CURVING UP, CONCAVE UP",
           "THROUGH (0,0) AND (1,-3/4)"],
          "odd, Q2 & Q4, decreasing on (-∞,∞), f→-∞ as x→∞ and f→∞ as x→-∞"),
    props("EXTRA-power-14", "-x^(-1/2): Q4 only with asymptotes", 3, "-", "-1/2",
          ["UNDEFINED FOR X<0", "QUADRANT: IV ONLY", "DOMAIN: (0,INF)", "RANGE: (-INF,0)", "INCREASING: (0,INF)",
           "DECREASING: NEVER", "BOUNDED ABOVE", "AS X->INF, F(X)->0", "NO LEFT END BEHAVIOR",
           "Q4: INCREASING", "CURVING DOWN, CONCAVE DOWN"],
          "x>0 only, range (-∞,0), increasing on (0,∞), bounded above"),
    props("EXTRA-power-15", "x^2 (integer power, even)", 3, "", "2",
          ["SYMMETRY: EVEN (Y-AXIS)", "INCREASING: [0,INF)", "DECREASING: (-INF,0]", "RANGE: [0,INF)",
           "AS X->+-INF, F(X)->INF", "BOUNDED BELOW"],
          "parabola: decreasing (-∞,0], increasing [0,∞)"),
    props("EXTRA-power-16", "K=0 typed: y = 0x^3", 2, "0", "3", ["NOT A POWER FUNCTION", "(K=0, SO Y=0)"],
          "k ≠ 0 for a power function"),
    props("EXTRA-power-17", "P=0 typed: y = 5x^0", 2, "5", "0", ["NOT A POWER FUNCTION", "(P=0, SO Y=K: CONSTANT)"],
          "p ≠ 0 for a power function"),
    build("EXTRA-power-18", "Q1 and Q3, gets steeper (odd, p>1)", 5, 2, ["Y=X^(5/3)", "K=1, P=5/3"],
          "y = x^(5/3)"),
    build("EXTRA-power-19", "Q1 and Q2 with asymptotes (even, p<0)", 3, 3, ["Y=X^(-2/3)", "K=1, P=-2/3"],
          "y = x^(-2/3)"),
    build("EXTRA-power-20", "Q3 and Q4, gets steeper (even, p>1, flipped)", 4, 2, ["Y=-X^(4/3)", "K=-1, P=4/3"],
          "y = -x^(4/3)"),
    dict(id="EXTRA-power-21", source="AGAIN from FIND K,P, then CLEAR back: -3/x^2 then 2/(x sqrt x)",
         actions=["k6", "k1", "k3", "t:-3", "t:", "t:2", "k1", "k6", "t:2", "t:", "t:", "t:", "t:", "t:", "k2"],
         expect=["Y=-3X^(-2)", "Y=2X^(-3/2)"], official="-3x^(-2); 2x^(-3/2)",
         path="6 → 1:FIND K,P; 3: TOP=-3 BOTTOM=ENTER POWER=2; 1:AGAIN; 6: TOP=2, ENTER x5"),
    dict(id="EXTRA-power-22", source="Root index typed wrong (0) is asked again: sqrt(9x)",
         actions=["k6", "k1", "k2", "t:", "t:0", "t:", "t:9", "t:", "k2"],
         expect=["Y=3X^(1/2)", "K=3"], official="3x^(1/2)",
         path="6 → 1:FIND K,P; 2; FRONT=ENTER INDEX=0 (asked again) INDEX=ENTER UNDER=9 POWER=ENTER"),
    # ---- WHY pages (run every WHY branch; the answer lines are checked, the WHY page must not crash) ----
    dict(id="EXTRA-power-23", source="WHY pages: -2x^(-2/3), then 3x^(5/4), then x^(3/7), then x^(-11/4)",
         actions=["k6", "k3", "t:-2", "t:-2/3"] + MORE + ["k3", "k1", "t:3", "t:5/4"] + MORE + ["k3", "k1",
                  "t:", "t:3/7"] + MORE + ["k3", "k1", "t:", "t:-11/4"] + MORE + ["k3", "k2"],
         expect=["X^(-2/3)=1/(³√(X))²", "X^(5/4)=(4TH ROOT X)^5", "X^(3/7)=(7TH ROOT X)³",
                 "X^(-11/4)=", "1/(4TH ROOT X)^11"],
         official="root forms x^(a/b) = (b-th root of x)^a",
         path="6 → 3:ALL PROPERTIES; each time 3:WHY then 1:AGAIN"),
    dict(id="EXTRA-power-24", source="BUILD with WHY for every quadrant choice",
         actions=["k6", "k4", "k1", "k1", "k3", "k1", "k2", "k2", "k3", "k1", "k3", "k3", "k3", "k1", "k4", "k2",
                  "k3", "k1", "k5", "k3", "k3", "k1", "k6", "k1", "k3", "k2"],
         expect=["Y=X^(1/2)", "Y=-X^(3/2)", "Y=X^(-2/3)", "Y=-X^(4/3)", "Y=X^(-3/5)", "Y=-X^(3/5)"],
         official="one valid function per graph description",
         path="6 → 4:BUILD EQUATION; each quadrant choice, 3:WHY, 1:AGAIN"),
    dict(id="EXTRA-power-25", source="FIND typed with a rounded decimal power: x^0.6667 (meant 2/3)",
         actions=["k6", "k1", "k1", "t:", "t:0.6667", "k2"],
         expect=["TYPE POWERS AS FRACTIONS,", "LIKE 2/3, NOT 0.667"], official="type 2/3",
         path="6 → 1:FIND K,P; 1; FRONT=ENTER POWER=0.6667"),
    # ---- Section 7 rules used as problems ----------------------------------------------------------------
    dict(id="RULE-7-MATCHING", source="Matching equations to curves: 2x^(1/4), 1.7x^(2/3), (1/2)x^(-5), -2x^(-2), "
                                      "-(2/3)x^4, -x^(5/3)",
         actions=again(2, [("2", "1/4"), ("1.7", "2/3"), ("1/2", "-5"), ("-2", "-2"), ("-2/3", "4"), ("-", "5/3")]),
         expect=["THROUGH (0,0) AND (1,2)", "THROUGH (0,0)", "AND (1,17/10)", "THROUGH (1,1/2)", "THROUGH (1,-2)",
                 "THROUGH (0,0) AND (1,-2/3)", "THROUGH (0,0) AND (1,-1)", "CURVING DOWN, CONCAVE DOWN",
                 "QUADRANTS: I,III", "QUADRANTS: III,IV", "QUADRANTS: II,IV", "ASYMPTOTES: X=0, Y=0"],
         official="Matching equations to curves (textbook #37–42). Every k x^p passes through (1, k), so look at x = 1 first. A bigger |k| puts the curve farther from the axis there, and k < 0 puts it below. Then use shape: 0 < p < 1 rises fast near 0 and levels off (like curve d for 2x^(1/4) and 1.7x^(2/3)); p < 0 hugs the y-axis near 0 (curve a for (1/2)x^(-5), curve h for -2x^(-2)); p > 1 starts flat and bends away (like g for -(2/3)x^4 and -x^(5/3)).",
         path="6 → 2:SYMMETRY/QUADS for each equation (1:AGAIN between)"),
    dict(id="RULE-7-ORGANIZER", source="Graphic organizer (k=1): x^(3/2), x^(1/2), x^(-1/2), x^3, x^(1/3), x^(-1/3), "
                                       "x^2, x^(2/3), x^(-2)",
         actions=again(2, [("", "3/2"), ("", "1/2"), ("", "-1/2"), ("", "3"), ("", "1/3"), ("", "-1/3"),
                           ("", "2"), ("", "2/3"), ("", "-2")]),
         expect=["QUADRANT: I ONLY", "QUADRANTS: I,III", "QUADRANTS: I,II", "CURVING UP, CONCAVE UP",
                 "CURVING DOWN, CONCAVE DOWN", "Q1: DECREASING", "ASYMPTOTES: X=0, Y=0"],
         official="Your graphic organizer (p. 41), drawn to scale. Shown with k = 1. 3x3 grid. Column headers: \"p > 1\" | \"0 < p < 1\" | \"p < 0 (asymptotes)\". Row 1 label: \"Q1 only\", odd/even, \"D: [0,∞)\" — cells: x^(3/2) | x^(1/2) | x^(-1/2). Row 2 label: \"Q1 & Q3\", odd/odd, \"odd sym.\" — cells: x^3 | x^(1/3) | x^(-1/3), x^(-1). Row 3 label: \"Q1 & Q2\", even/odd, \"even sym.\" — cells: x^2 | x^(2/3), x^(4/5) | x^(-2), x^(-2/3).",
         path="6 → 2:SYMMETRY/QUADS for each cell (1:AGAIN between)"),
    dict(id="EXTRA-power-26", source="Infinity typed by mistake for P (letter I): asked again, then 1/3",
         actions=["k6", "k2", "t:1", "t:I", "t:1", "t:1/3", "k2"],
         expect=["P=1/3  (ODD/ODD)", "SYMMETRY: ODD (ORIGIN)"], official="x^(1/3): odd",
         path="6 → 2:SYMMETRY/QUADS; K=1 P=I (asked again); K=1 P=1/3"),
]
