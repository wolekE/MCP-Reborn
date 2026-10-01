"""Function operations F+G, F-G, FG, F/G, G/F (main menu 1, program HAOPS).
Study guide Section 1 (Examples 1.1-1.3, Practice 1.1-1.4), cram sheet 1, cram 8a, Section 8 correction 6.

Submenu:  WHAT DO THEY WANT?  1:DOMAIN  2:A VALUE  3:FORMULA
Then:     WHICH ONE IS IT?    1:F+G  2:F-G  3:FG  4:F/G  5:G/F  6:G-F
Then f and g from the shape menu of HAFUNC ("F(X) LOOKS LIKE?"):
  1:AX+B  2:AX²+BX+C  3:(AX+B)/(CX+D)  4:K/(AX+B)  5:K√(AX+B)+C  6:FRACTION WITH X²  7:A GRAPH  8:WORDS
VALUE then asks X=.  DOMAIN of F/G (or G/F) also shows the other order.  FORMULA also shows the domain.
Footer: 1:AGAIN 2:HOME 3:WHY, and row 9 "4:SAME F,G  NEW QUESTION" (keeps f and g, back to WHAT DO THEY WANT?).
The WHY page footer is 1:AGAIN 2:HOME 4:SAME F,G (the same 4 as on the answer screen).
"""

ASK = {"domain": "k1", "value": "k2", "formula": "k3"}
ASK_WORDS = {"domain": "1:DOMAIN", "value": "2:A VALUE", "formula": "3:FORMULA"}
COMBO = {"F+G": "k1", "F-G": "k2", "FG": "k3", "F/G": "k4", "G/F": "k5", "G-F": "k6"}
COMBO_NUM = {"F+G": "1", "F-G": "2", "FG": "3", "F/G": "4", "G/F": "5", "G-F": "6"}

SHAPES = {"line": ("k1", "1:AX+B", ["A=", "B="]),
          "quad": ("k2", "2:AX²+BX+C", ["A=", "B=", "C="]),
          "frac": ("k3", "3:(AX+B)/(CX+D)", ["A=", "B=", "C=", "D="]),
          "recip": ("k4", "4:K/(AX+B)", ["K=", "A=", "B="]),
          "root": ("k5", "5:K√(AX+B)+C", ["K=", "A=", "B=", "C="]),
          "frac2": ("k6", "6:FRACTION WITH X²", ["A=", "B=", "C=", "D=", "E=", "F="])}

# EX-1.3 graphs (every corner labeled, closed ends)
F_PTS = [(-6, 2), (-3, -1), (1, 3), (4, 0), (7, 3)]
G_PTS = [(-5, 3), (-2, 0), (1, 0), (3, 2), (6, -1)]
EX13 = {"ʟGFX": [p[0] for p in F_PTS], "ʟGFY": [p[1] for p in F_PTS], "ʟGFC": [1, 1],
        "ʟGGX": [p[0] for p in G_PTS], "ʟGGY": [p[1] for p in G_PTS], "ʟGGC": [1, 1]}


def fn(shape, *vals):
    """keys for one function on HAFUNC's shape screens, and the words for TESTS.md"""
    key, name, prompts = SHAPES[shape]
    acts = [key] + [f"t:{v}" for v in vals]
    words = name + " " + " ".join(f"{p}{v or 'ENTER'}" for p, v in zip(prompts, vals))
    return acts, words


def graph(pts, ends="k1", menu=None):
    """typed corner points (menu='k1' when a saved graph already exists and the graph menu shows)"""
    acts = ["k7"] + ([menu] if menu else []) + [f"t:{len(pts)}"]
    for x, y in pts:
        acts += [f"t:{x}", f"t:{y}"]
    words = "7:A GRAPH; " + ("1:TYPE THE CORNER POINTS; " if menu else "") + f"{len(pts)} points " + \
        " ".join(f"({x},{y})" for x, y in pts) + ("; 1:BOTH SOLID" if ends == "k1" else "; 2:LEFT OPEN")
    return acts + [ends], words


SAVED_F = (["k7", "k2"], "7:A GRAPH; 2:USE SAVED GRAPH OF F")
SAVED_G = (["k7", "k3"], "7:A GRAPH; 3:USE SAVED GRAPH OF G")


def words(left, right, zeros=(), stretches=(), br="k1"):
    acts = ["k8", f"t:{left}", f"t:{right}"]
    if "I" not in left or "I" not in right:
        acts.append(br)
    acts.append(f"t:{len(zeros) if zeros else ''}")
    acts += [f"t:{z}" for z in zeros]
    acts.append(f"t:{len(stretches) if stretches else ''}")
    for a, b in stretches:
        acts += [f"t:{a}", f"t:{b}"]
    bname = {"k1": "[ ]", "k2": "[ )", "k3": "( ]", "k4": "( )"}[br]
    w = (f"8:WORDS; domain {left} to {right} {bname}; zeros at x: {', '.join(zeros) or 'ENTER (none)'}; "
         f"zero intervals: {', '.join(f'[{a},{b}]' for a, b in stretches) or 'ENTER (none)'}")
    return acts, w


def case(cid, src, ask, combo, f, g, expect, official, x=None, lists=None, extra=None, graph_note=None, then=None):
    acts = ["k1", ASK[ask], COMBO[combo]] + f[0] + g[0] + ([f"t:{x}"] if x is not None else []) + (extra or [])
    path = (f"1:F+G OR F/G → {ASK_WORDS[ask]} → {COMBO_NUM[combo]}:{combo}; F: {f[1]}; G: {g[1]}"
            + (f"; X={x}" if x is not None else "") + (f"; then {then}" if then else ""))
    c = dict(id=cid, source=src, path=path, actions=acts, expect=expect, official=official)
    if lists:
        c["lists"] = lists
    if graph_note:
        c["graph"] = graph_note
    return c


# functions used by several cases
EX11_F = fn("root", "", "", "3", "")          # f = √(x+3)
EX11_G = fn("line", "", "-1")                 # g = x - 1
EX12_F = fn("frac2", "0", "", "-3", "", "0", "")   # f = (x-3)/x²
EX12_G = fn("frac", "", "2", "-1", "4")       # g = (x+2)/(4-x)
PR11_F = fn("quad", "2", "0", "-1")           # f = 2x² - 1
PR11_G = fn("line", "-1", "3")                # g = 3 - x
PR12_F = fn("root", "", "-1", "5", "")        # f = √(5-x)
PR12_G = fn("line", "", "1")                  # g = x + 1
PR13_F = fn("frac", "", "1", "", "-2")        # f = (x+1)/(x-2)
PR13_G = fn("frac", "", "-5", "", "")         # g = (x-5)/x
PR14_F = words("-4", "9", zeros=("-1", "6"))
PR14_G = words("-6", "5", stretches=(("2", "3"),))
CRAM_F = fn("frac2", "0", "", "2", "", "0", "")    # f = (x+2)/x²
CRAM_G = fn("frac", "", "1", "-1", "1")       # g = (x+1)/(1-x)
SQRTX = fn("root", "", "", "", "")            # √x, ENTER four times
GRAPH_NOTE = "corners of the Example 1.3 graphs"

CASES = [
    # ---------------------------------------------------------------- Example 1.1
    case("EX-1.1a", "f=√(x+3), g=x-1: (f+g)(x) and its domain", "formula", "F+G", EX11_F, EX11_G,
         ["(F+G)(X)=√(X+3)+X-1", "D(F+G)=[-3,INF)"], "(f + g)(x) = sqrt(x + 3) + x − 1, domain [−3, ∞)"),
    case("EX-1.1b", "f=√(x+3), g=x-1: (fg)(x) and its domain", "formula", "FG", EX11_F, EX11_G,
         ["(FG)(X)=(X-1)√(X+3)", "D(FG)=[-3,INF)"], "(fg)(x) = (x − 1)sqrt(x + 3), domain [−3, ∞)"),
    case("EX-1.1c", "f=√(x+3), g=x-1: (f/g)(x) and its domain", "formula", "F/G", EX11_F, EX11_G,
         ["(F/G)(X)=√(X+3)/(X-1)", "D(F/G)=[-3,1)U(1,INF)"],
         "(f/g)(x) = sqrt(x + 3)/(x − 1), domain [−3, 1) ∪ (1, ∞)"),
    case("EX-1.1d", "f=√(x+3), g=x-1: (g/f)(x) and its domain", "formula", "G/F", EX11_F, EX11_G,
         ["(G/F)(X)=(X-1)/√(X+3)", "D(G/F)=(-3,INF)"], "(g/f)(x) = (x − 1)/sqrt(x + 3), domain (−3, ∞)"),
    case("EX-1.1e", "f=√(x+3), g=x-1: the domains alone (DOMAIN menu): f+g, f/g, g/f", "domain", "F/G",
         EX11_F, EX11_G, ["D(F/G)=[-3,1)U(1,INF)", "D(G/F)=(-3,INF)", "D(F+G)=[-3,INF)"],
         "f + g, fg: [−3, ∞); f/g: [−3, 1) ∪ (1, ∞); g/f: (−3, ∞)",
         extra=["k4", "k1", "k1"], then="4:SAME F,G → 1:DOMAIN → 1:F+G"),
    # ---------------------------------------------------------------- Example 1.2
    case("EX-1.2a", "f=(x-3)/x², g=(x+2)/(4-x): domain of (f/g)(x)", "domain", "F/G", EX12_F, EX12_G,
         ["D(F/G)=ALL REALS, X≠-2,0,4", "D(G/F)=ALL REALS, X≠0,3,4"], "D_f/g: ℝ, x ≠ −2, 0, 4"),
    case("EX-1.2b", "f=(x-3)/x², g=(x+2)/(4-x): domain of (g/f)(x)", "domain", "G/F", EX12_F, EX12_G,
         ["D(G/F)=ALL REALS, X≠0,3,4"], "D_g/f: ℝ, x ≠ 0, 3, 4"),
    case("EX-1.2c", "f=(x-3)/x², g=(x+2)/(4-x): (f/g)(x), keeping x≠0 and x≠4", "formula", "F/G", EX12_F, EX12_G,
         ["(F/G)(X)=", "(X-3)(-X+4)/(X²(X+2))", "D(F/G)=ALL REALS, X≠-2,0,4"],
         "(f/g)(x) = (x − 3)(4 − x)/(x^2(x + 2)); D_f/g: ℝ, x ≠ −2, 0, 4"),
    case("EX-1.2d", "f=(x-3)/x², g=(x+2)/(4-x): (g/f)(x), keeping x≠0", "formula", "G/F", EX12_F, EX12_G,
         ["(G/F)(X)=", "X²(X+2)/((-X+4)(X-3))", "D(G/F)=ALL REALS, X≠0,3,4"],
         "(g/f)(x) = x^2(x + 2)/((4 − x)(x − 3)); D_g/f: ℝ, x ≠ 0, 3, 4"),
    # ---------------------------------------------------------------- Example 1.3 (graphs)
    case("EX-1.3a", "graphs of Example 1.3: (f+g)(-3)", "value", "F+G", SAVED_F, SAVED_G,
         ["(F+G)(-3)=0"], "(a) 0", x="-3", lists=EX13, graph_note="saved graphs of f and g (Example 1.3)"),
    case("EX-1.3b", "graphs of Example 1.3: (fg)(3)", "value", "FG", SAVED_F, SAVED_G,
         ["(FG)(3)=2"], "(b) 2", x="3", lists=EX13, graph_note="saved graphs of f and g (Example 1.3)"),
    case("EX-1.3c", "graphs of Example 1.3: domain of f+g", "domain", "F+G", graph(F_PTS), graph(G_PTS, menu="k1"),
         ["D(F+G)=[-5,6]"], "(c) [−5, 6]", graph_note=GRAPH_NOTE),
    case("EX-1.3d", "graphs of Example 1.3: domain of f/g (g=0 on the whole segment [-2,1] and at 5)", "domain",
         "F/G", graph(F_PTS), graph(G_PTS, menu="k1"),
         ["D(F/G)=[-5,-2)U(1,5)U(5,6]"], "(d) D_f/g = [−5, −2) ∪ (1, 5) ∪ (5, 6]", graph_note=GRAPH_NOTE),
    case("EX-1.3e", "graphs of Example 1.3: domain of g/f", "domain", "G/F", SAVED_F, SAVED_G,
         ["D(G/F)=[-5,-4)U(-4,-2)U", "(-2,4)U(4,6]"], "(e) D_g/f = [−5, −4) ∪ (−4, −2) ∪ (−2, 4) ∪ (4, 6]",
         lists=EX13, graph_note="saved graphs of f and g (Example 1.3)"),
    # ---------------------------------------------------------------- Practice 1
    case("PR-1.1a", "f=2x²-1, g=3-x: (f-g)(x)", "formula", "F-G", PR11_F, PR11_G,
         ["(F-G)(X)=2X²+X-4", "D(F-G)=ALL REALS"], "(f − g)(x) = 2x^2 + x − 4"),
    case("PR-1.1b", "f=2x²-1, g=3-x: (fg)(-2)", "value", "FG", PR11_F, PR11_G,
         ["(FG)(-2)=35"], "(fg)(−2) = 35", x="-2"),
    case("PR-1.2a", "f=√(5-x), g=x+1: domain of (f/g)(x)", "domain", "F/G", PR12_F, PR12_G,
         ["D(F/G)=(-INF,-1)U(-1,5]", "D(G/F)=(-INF,5)"], "D_f/g: (−∞, −1) ∪ (−1, 5]"),
    case("PR-1.2b", "f=√(5-x), g=x+1: domain of (g/f)(x)", "domain", "G/F", PR12_F, PR12_G,
         ["D(G/F)=(-INF,5)"], "D_g/f: (−∞, 5)"),
    case("PR-1.3a", "f=(x+1)/(x-2), g=(x-5)/x: domain of (f/g)(x)", "domain", "F/G", PR13_F, PR13_G,
         ["D(F/G)=ALL REALS, X≠0,2,5"], "D_f/g: ℝ, x ≠ 0, 2, 5"),
    case("PR-1.3b", "f=(x+1)/(x-2), g=(x-5)/x: domain of (g/f)(x)", "domain", "G/F", PR13_F, PR13_G,
         ["D(G/F)=ALL REALS, X≠-1,0,2"], "D_g/f: ℝ, x ≠ −1, 0, 2"),
    case("PR-1.4a", "f: D=[-4,9], zeros -1, 6; g: D=[-6,5], g=0 on [2,3]: domain of f+g", "domain", "F+G",
         PR14_F, PR14_G, ["D(F+G)=[-4,5]"], "D_f+g = [−4, 5]"),
    case("PR-1.4b", "same words: domain of f/g", "domain", "F/G", PR14_F, PR14_G,
         ["D(F/G)=[-4,2)U(3,5]"], "f/g: [−4, 2) ∪ (3, 5]"),
    case("PR-1.4c", "same words: domain of g/f", "domain", "G/F", PR14_F, PR14_G,
         ["D(G/F)=[-4,-1)U(-1,5]"], "g/f: [−4, −1) ∪ (−1, 5]"),
    # ---------------------------------------------------------------- cram sheet and corrections
    case("CRAM-EX-1a", "f=(x+2)/x², g=(x+1)/(1-x): domain of f/g", "domain", "F/G", CRAM_F, CRAM_G,
         ["D(F/G)=ALL REALS, X≠-1,0,1"], "D_f/g : R, x ≠ 0, 1, −1"),
    case("CRAM-EX-1b", "f=(x+2)/x², g=(x+1)/(1-x): domain of g/f", "domain", "G/F", CRAM_F, CRAM_G,
         ["D(G/F)=ALL REALS, X≠-2,0,1"], "D_g/f : R, x ≠ 0, 1, −2 (since f(−2) = 0)"),
    case("CRAM-8a", "'Domain of f/g: D_f ∩ D_g, then drop the zeros of g' on f=√x, g=x²-4", "domain", "F/G",
         SQRTX, fn("quad", "", "0", "-4"), ["D(F/G)=[0,2)U(2,INF)", "D(G/F)=(0,INF)"],
         "D_f ∩ D_g, then drop the zeros of g: [0,∞) minus x=2 (x=-2 is already out)"),
    case("CORR-6", "g=√x; f has D_f=[-4,8] and f(x)=0 at x=2 (words): domain of (g/f)(x)", "domain", "G/F",
         words("-4", "8", zeros=("2",)), SQRTX, ["D(G/F)=[0,2)U(2,8]"],
         "Domain of (g/f)(x) = [0, 2) ∪ (2, 8] (not (2, ∞))"),
    # ---------------------------------------------------------------- common mistakes (Section 1)
    case("MIST-1-1", "zeros of the TOP are not removed: f=x-3, g=x+1, domain of f/g keeps x=3", "domain", "F/G",
         fn("line", "", "-3"), PR12_G, ["D(F/G)=ALL REALS, X≠-1", "D(G/F)=ALL REALS, X≠3"],
         "only the denominator's zeros are removed"),
    case("MIST-1-2", "cancelling keeps the restriction: f=x²-9, g=x+3, (f/g)(x)", "formula", "F/G",
         fn("quad", "", "0", "-9"), fn("line", "", "3"), ["(F/G)(X)=X-3", "D(F/G)=ALL REALS, X≠-3"],
         "(f/g)(x) = x − 3, but x ≠ −3 stays (domain found before simplifying)"),
    # ---------------------------------------------------------------- extra inputs not in the guide
    case("EXTRA-ops-1", "negative and fractional coefficients: f=(1/2)x-3, g=-2x+1: (f+g)(x)", "formula", "F+G",
         fn("line", "1/2", "-3"), fn("line", "-2", "1"), ["(F+G)(X)=-(3/2)X-2", "D(F+G)=ALL REALS"],
         "(1/2)x-3-2x+1 = -(3/2)x-2"),
    case("EXTRA-ops-2", "same f, g: (fg)(1/2) is 0 because g(1/2)=0; (f/g)(1/2) is undefined", "value", "FG",
         fn("line", "1/2", "-3"), fn("line", "-2", "1"), ["(FG)(1/2)=0", "(F/G)(1/2)=UNDEFINED"],
         "g(1/2)=0, so fg=0 and f/g is undefined there", x="1/2", extra=["k4", "k2", "k4", "t:1/2"],
         then="4:SAME F,G → 2:A VALUE → 4:F/G; X=1/2"),
    case("EXTRA-ops-3", "zero coefficients and ENTER: f=3 (A=0), g=x² (B=0, ENTER): (f/g)(x)", "formula", "F/G",
         fn("line", "0", "3"), fn("quad", "", "0", ""), ["(F/G)(X)=3/X²", "D(F/G)=ALL REALS, X≠0"],
         "3/x², x ≠ 0"),
    case("EXTRA-ops-4", "polynomial over a constant: f=3, g=x², (g/f)(x)", "formula", "G/F",
         fn("line", "0", "3"), fn("quad", "", "0", ""), ["(G/F)(X)=(1/3)X²", "D(G/F)=ALL REALS"],
         "x²/3, all reals"),
    case("EXTRA-ops-5", "infinity end in words: f: D=(-INF,3), f=0 on [0,1]; g=x+2: domains of g/f and f/g",
         "domain", "G/F", words("-I", "3", stretches=(("0", "1"),), br="k4"), fn("line", "", "2"),
         ["D(G/F)=(-INF,0)U(1,3)", "D(F/G)=(-INF,-2)U(-2,3)"], "(-∞,0)∪(1,3) and (-∞,-2)∪(-2,3)"),
    case("EXTRA-ops-6", "a sum that cancels: f=x/(x-1), g=-1/(x-1): (f+g)(x)=1 but x≠1 stays", "formula", "F+G",
         fn("frac", "", "0", "", "-1"), fn("recip", "-1", "", "-1"), ["(F+G)(X)=1", "D(F+G)=ALL REALS, X≠1"],
         "(x-1)/(x-1) = 1, x ≠ 1"),
    case("EXTRA-ops-7", "different bottoms: f=(x+1)/(x-2), g=(x-5)/x: (f+g)(x) as one fraction", "formula", "F+G",
         PR13_F, PR13_G, ["(F+G)(X)=", "(2X²-6X+10)/(X(X-2))", "D(F+G)=ALL REALS, X≠0,2"],
         "((x+1)x+(x-5)(x-2))/(x(x-2)) = (2x²-6x+10)/(x(x-2))"),
    case("EXTRA-ops-8", "exact root values: f=√(x+3), g=x-1 at x=0: (f+g)(0)=√3-1", "value", "F+G",
         EX11_F, EX11_G, ["(F+G)(0)=√(3)-1", "(F/G)(0)=-√(3)", "(G/F)(0)=-(1/3)√(3)"],
         "√3-1; √3/(-1) = -√3; -1/√3 = -√3/3", x="0", extra=["k4", "k2", "k4", "t:0", "k4", "k2", "k5", "t:0"],
         then="4:SAME F,G → 2 → 4:F/G X=0; 4:SAME F,G → 2 → 5:G/F X=0"),
    case("EXTRA-ops-9", "√12 simplifies: f=√x, g=x: (f+g)(12)=12+2√3; (fg)(1/2)", "value", "F+G",
         SQRTX, fn("line", "", ""), ["(F+G)(12)=12+2√(3)", "(FG)(1/2)=(1/4)√(2)"],
         "12+√12 = 12+2√3; (1/2)√(1/2) = √2/4", x="12", extra=["k4", "k2", "k3", "t:1/2"],
         then="4:SAME F,G → 2:A VALUE → 3:FG; X=1/2"),
    case("EXTRA-ops-10", "undefined values: f=√(x+3), g=x-1: (f/g)(1) (g=0) and (f+g)(-4) (not in D_f)", "value",
         "F/G", EX11_F, EX11_G, ["(F/G)(1)=UNDEFINED", "(F+G)(-4)=UNDEFINED"], "undefined, undefined",
         x="1", extra=["k3", "k3", "k2", "k1", "t:-4", "k3"],
         then="3:WHY → 3:SAME F,G → 2:A VALUE → 1:F+G; X=-4; 3:WHY"),
    case("EXTRA-ops-11", "graph with a hollow left end (0,0),(2,2),(4,0); g=x-1: domains of f/g and g/f", "domain",
         "F/G", graph([(0, 0), (2, 2), (4, 0)], ends="k2"), fn("line", "", "-1"),
         ["D(F/G)=(0,1)U(1,4]", "D(G/F)=(0,4)"], "(0,1)∪(1,4]; (0,4)", graph_note="typed corners, left dot hollow"),
    case("EXTRA-ops-12", "product of fractions that cancels: f=(x+1)/(x-2), g=(x-2)/(x+3): (fg)(x)", "formula",
         "FG", PR13_F, fn("frac", "", "-2", "", "3"), ["(FG)(X)=(X+1)/(X+3)", "D(FG)=ALL REALS, X≠-3,2"],
         "(x+1)/(x+3), x ≠ -3, 2"),
    case("EXTRA-ops-13", "two polynomials multiplied out: f=2x²-1, g=3-x: (fg)(x)", "formula", "FG",
         PR11_F, PR11_G, ["(FG)(X)=-2X³+6X²+X-3", "D(FG)=ALL REALS"], "(2x²-1)(3-x) = -2x³+6x²+x-3"),
    case("EXTRA-ops-14", "f-g with a root: f=x², g=2√(x-1)+3: (f-g)(x)", "formula", "F-G",
         fn("quad", "", "0", ""), fn("root", "2", "", "-1", "3"), ["(F-G)(X)=X²-3-2√(X-1)", "D(F-G)=[1,INF)"],
         "x²-3-2√(x-1), x ≥ 1"),
    case("EXTRA-ops-15", "SAME F,G: PR-1.1 in one session: (f-g)(x), then 4:SAME F,G for (fg)(-2), then WHY",
         "formula", "F-G", PR11_F, PR11_G, ["(F-G)(X)=2X²+X-4", "(FG)(-2)=35"], "2x² + x − 4; 35",
         extra=["k4", "k2", "k3", "t:-2", "k3", "k2"],
         then="4:SAME F,G → 2:A VALUE → 3:FG; X=-2; 3:WHY; 2:HOME"),
    case("EXTRA-ops-16", "g is 0 everywhere (A=0, B=ENTER): f/g has no domain", "formula", "F/G",
         EX11_G, fn("line", "0", ""), ["(F/G)(X)=UNDEFINED", "D(F/G)=NO REAL NUMBERS"], "undefined for every x"),
    case("EXTRA-ops-17", "x²+1 cancels (no real zeros): f=(x²+1)/x, g=(x²+1)/(x-1): (f/g)(x)", "formula", "F/G",
         fn("frac2", "", "0", "1", "0", "", "0"), fn("frac2", "", "0", "1", "0", "", "-1"),
         ["(F/G)(X)=(X-1)/X", "D(F/G)=ALL REALS, X≠0,1"], "(x-1)/x, x ≠ 0, 1"),
    case("EXTRA-ops-18", "root with an end number: f=√x+2, g=x: fg, f/g, g/f", "formula", "FG",
         fn("root", "", "", "", "2"), fn("line", "", ""),
         ["(FG)(X)=X(√(X)+2)", "(F/G)(X)=(√(X)+2)/X", "(G/F)(X)=X/(√(X)+2)", "D(G/F)=[0,INF)"],
         "x(√x+2); (√x+2)/x; x/(√x+2)", extra=["k4", "k3", "k4", "k4", "k3", "k5"],
         then="4:SAME F,G → 3 → 4:F/G; 4:SAME F,G → 3 → 5:G/F"),
    case("EXTRA-ops-19", "two roots: f=√x, g=√(4-x): fg and f/g", "formula", "FG",
         SQRTX, fn("root", "", "-1", "4", ""),
         ["(FG)(X)=√(X)√(-X+4)", "D(FG)=[0,4]", "(F/G)(X)=√(X)/√(-X+4)", "D(F/G)=[0,4)"],
         "√x·√(4-x) on [0,4]; √x/√(4-x) on [0,4)", extra=["k4", "k3", "k4"],
         then="4:SAME F,G → 3:FORMULA → 4:F/G"),
    case("EXTRA-ops-20", "a fraction constant: f=1/(2x), g=x+1: (f/g)(x)", "formula", "F/G",
         fn("recip", "", "2", ""), PR12_G, ["(F/G)(X)=1/(2X(X+1))", "D(F/G)=ALL REALS, X≠-1,0"],
         "1/(2x(x+1)), x ≠ -1, 0"),
    case("EXTRA-ops-21", "words values: f: D=[-4,9], zeros -1, 6; g=x-1: (f+g)(0) unknown, (f/g)(1) undefined",
         "value", "F+G", PR14_F, EX11_G, ["(F+G)(0)=", "CAN NOT TELL FROM WORDS", "(F/G)(1)=UNDEFINED", "(FG)(6)=0"],
         "f(0) is not given; g(1)=0; f(6)=0", x="0",
         extra=["k4", "k2", "k4", "t:1", "k4", "k2", "k3", "t:6"],
         then="4:SAME F,G → 2 → 4:F/G X=1; 4:SAME F,G → 2 → 3:FG X=6"),
    case("EXTRA-ops-22", "AGAIN keeps the question type; CLEAR on the shape menu goes back: then PR-1.3",
         "domain", "F/G", PR12_F, PR12_G, ["D(F/G)=(-INF,-1)U(-1,5]", "D(F/G)=ALL REALS, X≠0,2,5"],
         "PR-1.2 then PR-1.3 via 1:AGAIN", extra=["k1", "k4", "CLEAR", "k4"] + PR13_F[0] + PR13_G[0],
         then="1:AGAIN → 4:F/G → CLEAR (back) → 4:F/G; F: " + PR13_F[1] + "; G: " + PR13_G[1]),
    case("EXTRA-ops-23", "WHY pages for domain, value and formula open and return (no errors)", "domain", "G/F",
         SAVED_F, SAVED_G, ["(F+G)(-3)=0", "(F/G)(X)=√(X+3)/(X-1)"], "(pages only)", lists=EX13,
         extra=["k3", "k3", "k2", "k1", "t:-3", "k3", "k2", "k1", "k3", "k4"] + EX11_F[0] + EX11_G[0] + ["k3", "k2"],
         then="3:WHY → 3:SAME F,G → 2 → 1:F+G X=-3 → 3:WHY → 2:HOME; 1 → 3:FORMULA → 4:F/G with EX-1.1 f, g → 3:WHY → 2:HOME"),
    case("EXTRA-ops-24", "VALUE with a quadratic bottom and a fraction x: f=(x+2)/x², g=(x+1)/(1-x): (f-g)(-1/2)",
         "value", "F-G", CRAM_F, CRAM_G, ["(F-G)(-1/2)=17/3"], "f(-1/2)=6, g(-1/2)=1/3, 6-1/3=17/3", x="-1/2"),
    case("EXTRA-ops-25", "FORMULA with a graph: no formula, but the domain is still given (EX-1.3 graphs, f+g)",
         "formula", "F+G", SAVED_F, SAVED_G, ["NO FORMULA: F OR G IS", "A GRAPH OR WORDS", "D(F+G)=[-5,6]"],
         "a graph has no formula; D_f+g = [-5, 6]", lists=EX13, graph_note="saved graphs of f and g (Example 1.3)"),
    # ---------------------------------------------------------------- adversarial review (REV-ops-n)
    case("REV-ops-1", "root value at its end point: f=4√(3x+4), g=5x+1: (g/f)(-4/3) (f=0 there; 3(-4/3)+4 left a "
         "1E-13 residue under the root, so f looked nonzero and the answer was -14166666666666√(0))", "value", "G/F",
         fn("root", "4", "3", "4", ""), fn("line", "5", "1"), ["(G/F)(-4/3)=UNDEFINED"], "f(-4/3)=0, so g/f is undefined",
         x="-4/3"),
    case("REV-ops-2", "the same residue made two radicals look different: f=-4√(-3x-5), g=5√(-4x+6)-19/5: (f-g)(-5/3)",
         "value", "F-G", fn("root", "-4", "-3", "-5", ""), fn("root", "5", "-4", "6", "-19/5"),
         ["(F-G)(-5/3)=", "19/5-(5/3)√(114)"], "0-(5√(38/3)-19/5) = 19/5-(5/3)√114 (was ABOUT -13.995132)", x="-5/3"),
    case("REV-ops-3", "words: f/g where f=0 and g is not 0 (only its listed zeros are 0) is 0, not 'CAN NOT TELL'; "
         "PR-1.4 f, g: (f/g)(-1), (g/f)(2), (f+g)(-1)", "value", "F/G", PR14_F, PR14_G,
         ["(F/G)(-1)=0", "(G/F)(2)=0", "CAN NOT TELL FROM WORDS"], "0/g(-1)=0; 0/f(2)=0; f(-1)+g(-1) unknown",
         x="-1", extra=["k4", "k2", "k5", "t:2", "k4", "k2", "k1", "t:-1"],
         then="4:SAME F,G → 2 → 5:G/F X=2; 4:SAME F,G → 2 → 1:F+G X=-1"),
    case("REV-ops-4", "exact value with a denominator over 9999: f=-x/(4x²+4x-1), g=(-5x-1)/(-5x+2): (f+g)(8)",
         "value", "F+G", fn("frac2", "0", "-1", "0", "4", "4", "-1"), fn("frac", "-5", "-1", "-5", "2"),
         ["(F+G)(8)=11463/10906"], "-8/287+41/38 = 11463/10906 (was ABOUT 1.051073)", x="8"),
    case("REV-ops-5", "irrational zeros of a quadratic bottom are shown exactly: f=1, g=3x²-3x-1: domain of f/g",
         "domain", "F/G", fn("line", "0", "1"), fn("quad", "3", "-3", "-1"),
         ["D(F/G)=ALL REALS,", "X≠(3-√(21))/6,(3+√(21))/6", "D(G/F)=ALL REALS"],
         "3x²-3x-1=0 at (3±√21)/6 (was X≠-0.263763,1.263763)"),
    case("REV-ops-6", "irrational interval ends: f=√x, g=x²-2: domain of f/g", "domain", "F/G", SQRTX,
         fn("quad", "", "0", "-2"), ["D(F/G)=[0,√(2))U(√(2),INF)", "D(G/F)=(0,INF)"], "[0,√2)∪(√2,∞); (0,∞)"),
    case("REV-ops-7", "a long excluded list wraps at a comma, never inside -√(3)/2: f=4x²-3, g=x: domain of g/f",
         "domain", "G/F", fn("quad", "4", "0", "-3"), fn("line", "", ""),
         ["D(G/F)=ALL REALS,", "X≠-√(3)/2,√(3)/2", "D(F/G)=ALL REALS, X≠0"], "ℝ, x≠±√3/2; ℝ, x≠0"),
    case("REV-ops-8", "(g-f)(x) has its own entry 6:G-F (2:F-G would give the opposite sign): PR-1.1 f, g",
         "formula", "G-F", PR11_F, PR11_G, ["(G-F)(X)=-2X²-X+4", "D(G-F)=ALL REALS", "(G-F)(-2)=-2"],
         "(3-x)-(2x²-1) = -2x²-x+4; g(-2)-f(-2) = 5-7 = -2", extra=["k4", "k2", "k6", "t:-2"],
         then="4:SAME F,G → 2:A VALUE → 6:G-F; X=-2"),
    case("REV-ops-9", "two different radicals are added exactly: f=√x, g=√(x+1): (f+g)(2), (f-g)(2)", "value", "F+G",
         SQRTX, fn("root", "", "", "1", ""), ["(F+G)(2)=√(2)+√(3)", "(F-G)(2)=√(2)-√(3)"],
         "√2+√3; √2-√3 (was ABOUT 3.146264)", x="2", extra=["k4", "k2", "k2", "t:2"],
         then="4:SAME F,G → 2:A VALUE → 2:F-G; X=2"),
    case("REV-ops-10", "radicals that simplify to the same √: f=√(4x), g=√x: (f+g)(2)=2√2+√2", "value", "F+G",
         fn("root", "", "4", "", ""), SQRTX, ["(F+G)(2)=3√(2)", "(F/G)(2)=2"], "√8+√2 = 3√2; √8/√2 = 2",
         x="2", extra=["k4", "k2", "k4", "t:2"], then="4:SAME F,G → 2:A VALUE → 4:F/G; X=2"),
    case("REV-ops-11", "the WHY page footer uses the same 4:SAME F,G as the answer screen: EX-1.1 domain, WHY, 4",
         "domain", "F/G", EX11_F, EX11_G, ["D(F/G)=[-3,1)U(1,INF)", "D(F+G)=[-3,INF)"], "[-3,1)∪(1,∞); [-3,∞)",
         extra=["k3", "k4", "k1", "k1"], then="3:WHY → 4:SAME F,G → 1:DOMAIN → 1:F+G"),
    case("REV-ops-12", "a typo in HOW MANY X VALUES (22) is asked again instead of 22 X= prompts: PR-1.4 f/g",
         "domain", "F/G", (["k8", "t:-4", "t:9", "k1", "t:22", "t:2", "t:-1", "t:6", "t:"], "8:WORDS with a typo"),
         PR14_G, ["D(F/G)=[-4,2)U(3,5]", "D(G/F)=[-4,-1)U(-1,5]"], "f/g: [−4, 2) ∪ (3, 5]; g/f: [−4, −1) ∪ (−1, 5]"),
    case("REV-ops-13", "a wrapped list of fractions never splits -2/3 into '-2/' and '3': f=1/(x+1), "
         "g=(8x²-30x+13)/(3x+2): domain of f/g", "domain", "F/G", fn("recip", "", "", "1"),
         fn("frac2", "8", "-30", "13", "0", "3", "2"),
         ["D(F/G)=ALL REALS, X≠-1,", "-2/3,1/2,13/4", "ALL REALS, X≠-1,-2/3"],
         "f: x≠-1; g: x≠-2/3, zeros 1/2, 13/4"),
    case("REV-ops-14", "an irrational value is never shown as a look-alike fraction: f=(-6x²+3)/(-3x²-6), g=5√6 "
         "(A=0, B=6): (f/g)(-29/4) = 833√6/13095 was shown as 1496/9601", "value", "F/G",
         fn("frac2", "-6", "0", "3", "-3", "0", "-6"), fn("root", "5", "0", "6", ""),
         ["(F/G)(-29/4)=", "ABOUT 0.155817"], "833√6/13095 ≈ 0.155817", x="-29/4"),
    case("REV-ops-15", "an approximate answer is a decimal, never 'ABOUT 33227/5000': f=-2√(2x-3), g=-6√(6x-6)-3: "
         "(g/f)(10/3) = (6√14+3)/(2√(11/3))", "value", "G/F", fn("root", "-2", "2", "-3", ""),
         fn("root", "-6", "6", "-6", "-3"), ["(G/F)(10/3)=ABOUT 6.6454"], "≈ 6.6454 (two different radicals)",
         x="10/3"),
    case("REV-ops-16", "a zero of K√(AX+B)+C with a big denominator is exact: f=(17/3)√(-6x-2/5)-13/4, g=x: "
         "domain of g/f", "domain", "G/F", fn("root", "17/3", "-6", "-2/5", "-13/4"), fn("line", "", ""),
         ["D(G/F)=", "(-INF,-16853/138720)U", "(-16853/138720,-1/15]"],
         "f=0 at -6x-2/5=(39/68)², x=-16853/138720; D_f=(-∞,-1/15] (was -0.121489)"),
    case("REV-ops-17", "equal radicals combine: f=√x, g=√x: (fg)(x)=x, (f/g)(x)=1; f=√(x+3), g=√(x+3): "
         "(f+g)(x)=2√(x+3) (was √(X)√(X), √(X)/√(X), √(X+3)+√(X+3))", "formula", "FG", SQRTX, SQRTX,
         ["(FG)(X)=X", "D(FG)=[0,INF)", "(F/G)(X)=1", "D(F/G)=(0,INF)", "(F+G)(X)=2√(X+3)", "D(F+G)=[-3,INF)"],
         "x on [0,∞); 1 on (0,∞); 2√(x+3) on [-3,∞)",
         extra=["k4", "k3", "k4", "k1", "k1"] + EX11_F[0] + EX11_F[0],
         then="4:SAME F,G → 3 → 4:F/G; 1:AGAIN → 1:F+G with f=g=√(x+3)"),
    case("REV-ops-18", "equal radicals with a zero front number on the bottom: f=-√(3x+5), g=0√(3x+5) (K=0): "
         "(f/g)(x) is undefined everywhere (crashed with ERR:DIVIDE BY 0)", "formula", "F/G",
         fn("root", "-", "3", "5", ""), fn("root", "0", "3", "5", ""),
         ["(F/G)(X)=UNDEFINED", "D(F/G)=NO REAL NUMBERS", "(G/F)(X)=0", "D(G/F)=(-5/3,INF)"],
         "g=0 for every x; g/f=0 on (-5/3,∞)", extra=["k4", "k3", "k5"], then="4:SAME F,G → 3 → 5:G/F"),
]
