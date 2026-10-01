# HPCANS: design

Goal: the student looks at a quiz question, picks the menu entry that **looks like** the
question, types the numbers they can see, and reads `ANSWER:`. The calculator does the
thinking (factoring the inside, finding h, parity rules, inverse algebra, domain rules).

Source of truth: *HPC Unit 1 Topic 2 Study Guide* (33 pp.) and *Cram Sheet*. Every practice
problem in Sections 1–7 has a solver path (see COVERAGE.md) and a test (see TESTS.md).

## Target

* **TI-84 Plus CE** (the student's calculator). Home screen 26 columns × 10 rows.
  All code uses only tokens that exist since TI-83 Plus OS 1.x (no CE-OS-version
  features), but screens are laid out for 26 × 10 and the full set of programs needs
  more RAM than a TI-84 Plus has, so the older model is not supported.
* All programs must be in **RAM** (not Archive).

## Programs (names ≤ 8 characters)

| Program | Role |
|---|---|
| `HPCANS` | The only one the student runs. Splash + main menu, calls solvers. |
| `HAOPS` (+ `HAOPS2`–`HAOPS9`) | 1 F+G OR F/G: domain, value, formula. 2 formula builder, 3 line printer, 4 domain of a combination, 5/9 exact or decimal values, 6 values, 7/8 exact domain text with roots |
| `HACOMP` (+ `HACOMP2`–`HACOMP9`, `HACOMPA`–`HACOMPD`, `HACOMPW`) | 2 F(G(X)): formula + domain, graph values, formula values. 2–5, 7 composite formula and simplifying, 6 domain clean-up, 8/9 exact values, A–D exact domain ends, W line breaker |
| `HAINV` (+ `HAINV2`–`HAINV9`, `HAINVL`, `HAINVS`, `HAINVW`) | 3 F⁻¹: find inverse, verify, D/R, HLT. 2 shape entry, 3 typed line, 4 evaluate, 5 rational text, 6 power inverse, 7 verify engine, 8 HLT from a graph, 9/W printing, L line text, S integer scaling |
| `HATRANS` | 4 A*F(BX+C)+K: list changes, new points, D/R, write equation (uses `HAABCK`, `HAEQN`, `HAPTXT`) |
| `HAABS` (+ `HAABS2`–`HAABS5`, `HAABS7`) | 5 ABS BARS: graph points + D/R, domain only, range only, D and R, order of steps |
| `HAPOWER` (+ `HAPOWR2`–`HAPOWR4`) | 6 KX^P / ROOTS: find k,p, symmetry/quadrants, all properties, build function |
| `HADECOMP` (+ `HADECMP2`) | 7 DECOMPOSE |
| `HAFUNC` `HAGRAPH` `HAFSTR` `HAFEVAL` `HAFDOM` `HAFZERO` `HAWORDS` | (high helpers) function records: shape entry, graphs, words, text, values, domains, zeros |
| `HAABCK` `HAEQN` `HAPTXT` `HAPTS` | (high helpers) ask A,B,C,K; equation text; point text; ask graph corners |
| `HADOM` | (mid helper) sets of reals as unions of intervals: ∩, remove point/segment, sign chart, render |
| `HAPOLY` `HAPMUL` | (mid helpers) polynomial → text, polynomial multiply |
| `HAIVL` | (mid helper) ask for an interval (ends, brackets, ∞) |
| `HAROOT` | (low helper) real roots of ax²+bx+c (stable formula) |
| `HAFRAC` `HADIG` | (low helpers) number → exact text (`-17/4`, `6`, `INF`); digits |
| `HANUM` | (low helper) typed text → number (minus key, `+`, `X`, `I` = ∞) |
| `HAKEY` | (low helper) wait for a number key 1..N or CLEAR |
| `HAANS` `HAPAGE` `HAOUT` `HAEND` | (low helpers) answer screen: start, page title, print a line (word-safe wrap, ENTER=MORE / CLEAR=SKIP), footer + choice |

Programs with a number or letter after the solver name are that solver's own sub-programs (solver
layer, sharing A–M with it). `HAOPS7`–`HAOPS9` and `HACOMPA`–`HACOMPD` also use S–Z, θ and Str6–Str9
as scratch and keep θ / Str9 across `HADIG` / `HAFRAC` calls, which works because those helpers do not
write them (checked by `tools/poison.py`); keep it that way if HAFRAC or HADIG changes.

A solver returns to `HPCANS` with `Return`; nothing ever calls `HPCANS` again, so the call
stack stays shallow. Only `HPCANS` uses `Stop` (when the student presses CLEAR on the main menu).

## Screens and keys

* **Menus** are drawn with `Disp` and read with `getKey` (helper `HAKEY`): press the number;
  no arrow keys, no ENTER needed. **CLEAR always goes back** (submenu → main menu → quit).
* **Inputs** use `Input "LABEL=",Str8` then `HANUM` converts the text to a number, so a
  leading minus typed with the subtraction key still works, `2/3` works, ENTER on an
  empty line can mean "none" where a default exists, and `I` means infinity where allowed.
* **Answer screens** always start with `ANSWER:` on row 1, show the answer (rows 2–8),
  and end with a footer on row 10, e.g. `1:AGAIN 2:HOME 3:WHY`. Long answers page with
  `ENTER=MORE`. Nothing is explained before the answer.
* Splash (once per run): `USE (-) FOR NEGATIVES`, `TYPE 2/3 AS 2÷3`, `CLEAR = BACK`.

## Variables (TI-BASIC has only globals, so they are split by layer)

| Layer | Reals | Strings | Lists |
|---|---|---|---|
| Solvers | A–M | Str0–Str3 | L₁–L₅ |
| High helpers (`HAFUNC`, `HAGRAPH`) | N–R | Str4, Str5 | `ʟF1` `ʟF2` (function records), graph lists |
| Mid helpers (`HADOM`, `HAPOLY`, `HAIVL`) | S–V | Str6, Str7 | `ʟDL..` `ʟEL..`, `ʟPLY`, `ʟPA` `ʟPB` `ʟPC` |
| Low helpers (`HAFRAC`, `HAROOT`, `HANUM`, `HAKEY`, `HAOUT`…) | W–Z, θ | Str8, Str9 | `ʟQC` `ʟRT` |

A helper may clobber its own layer and any lower layer, never a higher one.
Arguments/results: θ (number), Str9 (text), and the lists named in each API.

## Exact numbers

The TI-84 computes with 14 significant digits. Every displayed number goes through `HAFRAC`, which finds the exact fraction n/d that matches
the value to 1e-11·max(1,|x|), with d ≤ 9999 and d²·max(1,|x|) ≤ 1e8 (so `-17/4` is shown, never
`-4.25`, and an irrational number cannot match a big-denominator fraction by accident). If no
such fraction exists the value is shown as a 6-place decimal. The operations and composition
solvers print quadratic irrationals exactly (`X≠-√(2),√(2)`, `(29±4√(6))/5`) by testing each end
against the quadratics it can come from. Integer work (gcd, parity, reduction) uses `gcd(` on
exact integers. Values that should be 0 but carry rounding residue (|v| < 1e-9) are snapped to 0.

## Data formats

* **Interval-union set** (`HADOM`): `ʟDL` left ends, `ʟDR` right ends, `ʟDA` left closed
  (1/0), `ʟDB` right closed (1/0); second operand `ʟEL ʟER ʟEA ʟEB`. ±∞ = ±1ᴇ99.
* **Function record** `ʟF1` (f) / `ʟF2` (g), 13 numbers:
  `{kind, n4,n3,n2,n1,n0, d4,d3,d2,d1,d0, K, C}`
  * kind 1: rational `N(x)/D(x)` (linear, quadratic, (ax+b)/(cx+d), general)
  * kind 2: root `K·√(N(x)/D(x)) + C` (the shapes use N linear, D = 1)
  * kind 3: graph (corner points in `ʟGFX ʟGFY` for f, `ʟGGX ʟGGY` for g; ends closed flags in `ʟGFC`/`ʟGGC`)
  * kind 4: words (domain interval + zero points + zero stretches in `ʟWF*` / `ʟWG*`)
* **Graph**: corner points in x order; straight segments between them (as in every graph
  in the study guide). Zeros are found from corners, sign changes between corners, and
  whole segments with y = 0.

## Solvers

### 1 F+G OR F/G (`HAOPS`)
`WHAT DO THEY WANT?` 1:DOMAIN 2:VALUE AT A NUMBER 3:FORMULA
* combination (one key): 1:F+G 2:F-G 3:F*G 4:F/G 5:G/F
* f and g shapes (`HAFUNC`): 1:AX+B 2:AX²+BX+C 3:(AX+B)/(CX+D) 4:K√(AX+B)+C
  5:FRACTION WITH X² (general (AX²+BX+C)/(DX²+EX+F)) 6:GRAPH (corners) 7:WORDS
  (domain + zeros) 8:SAVED GRAPH
* DOMAIN = Df ∩ Dg, minus zeros of the bottom function (points and whole segments);
  restrictions are taken from the original functions, never from a simplified result.
  Output `ALL REALS EXCEPT X=a,b,c` or a union of intervals with correct brackets.
* VALUE: x, then f(x) and g(x) from the shapes (or the graph) → the number.
* FORMULA: the combined function (polynomials combined; rationals as one fraction).

### 2 F(G(X)) (`HACOMP`)
`WHAT DO THEY WANT?` 1:SIMPLIFY+DOMAIN 2:GRAPH VALUES 3:√(GRAPH) DOMAIN 4:GRAPH(√X) DOMAIN 5:ONE NUMBER
* 1: f shape, g shape, then 1:F(G(X)) 2:G(F(X)). Result simplified exactly as the class does
  (multiply top and bottom by the LCD), domain = x in Dg and g(x) in Df, found before
  simplifying. Footer `3:OTHER ORDER`.
  Supported: polynomial/rational ∘ polynomial/rational (degrees ≤ 2), √ ∘ polynomial/rational,
  polynomial ∘ √.
* 2: `OUTSIDE` (F/G) `INSIDE` (F/G) `NUMBER=` → uses saved graphs, or asks only the two values
  needed (`G(5)=`, then `F(0)=`); 999 = not on the graph → `UNDEFINED`.
* 3: √(graph): where the graph is ≥ 0. 4: graph(K√(AX+B)+C) or graph(AX+B): x with g(x) in the graph's domain.

### 3 F⁻¹ (`HAINV`)
`WHAT DO THEY WANT?` 1:FIND F⁻¹(X) 2:ARE THEY INVERSES 3:D,R OF F⁻¹ 4:HAS INVERSE? (HLT)
* shapes: 1:AX+B 2:(AX+B)/(CX+D) 3:A(BX+C)³+D 4:A³√(BX+C)+D 5:A√(BX+C)+D 6:A(BX+C)^(M/N)+D
* output the inverse in the class's form, with restriction, domain and range for roots.
* verify: compose both ways (exactly for rational shapes, at test points for the others).
* D,R: swap, brackets kept. HLT: shape → YES / NO with two points that share a y.

### 4 A*F(BX+C)+K (`HATRANS`)
`WHAT DO THEY WANT?` 1:LIST THE CHANGES 2:NEW POINTS (TABLE) 3:NEW DOMAIN AND RANGE 4:WRITE THE EQUATION
* inputs exactly as printed: `A (FRONT)=`, `B (X COEF)=`, `C (INSIDE NUMBER)=`, `K (END NUMBER)=`;
  ENTER on A or B = 1, on C or K = 0; a lone (-) = -1; a copied `+` and an `X` (3X → 3) are accepted.
  h = −C/B internally; the student never factors.
* changes: the factored `Y=AF(B(X-H))+K` first, then the changes in class order
  (`REFLECT OVER X-AXIS`, `VERT STRETCH BY 3`, `REFLECT OVER Y-AXIS`, `HORIZ COMPRESS BY 1/3`,
  `RIGHT 2`, `UP 1`), then `A= B= H= K=`.
* new points: one point at a time, or every corner / table point as `(x,y) TO (x',y')` in table
  order, then `D=..  R=..` (flat pieces and hollow ends handled).
* D/R: ends through the rules, reordered, brackets follow their numbers, ∞ allowed.
* write: 1:REFLECT X 2:REFLECT Y 3:VERT 4:HORIZ 5:LEFT 6:RIGHT 7:UP 8:DOWN 9:DONE, in the order
  the words say (handles THEN); sizes typed as seen → `Y=…` in both forms.
* every answer: `1:AGAIN 2:HOME 3:SAME EQ` (same equation: changes / points / D,R / WHY).

### 5 ABS BARS (`HAABS`)
`WHAT DO THEY WANT?` 1:POINTS + D,R 2:DOMAIN ONLY 3:RANGE ONLY
* bar shapes: 1:A|F(BX+C)+D|+K 2:A·F(B|X|+C)+K 3:A·F(|BX+C|)+K
* points: graph corners (saved or new); inside steps, then f, then outside steps; new
  x-intercepts are added before |y|; f(|x|) keeps x ≥ 0 (adds the point at x = 0) and mirrors.
  Output every new corner, D and R.
* domain only / range only from the given intervals (two intervals when needed, e.g.
  [2,7] → [-7,-2]U[2,7]).

### 6 KX^P / ROOTS (`HAPOWER`)
`WHAT DO THEY WANT?` 1:FIND K AND P 2:EVEN/ODD+QUADS 3:ALL PROPERTIES 4:BUILD A FUNCTION
* find k,p: what is on top (number, x power, root index, number and x power under the root),
  what is on the bottom (same) → k (roots of numbers taken exactly) and p reduced.
  Also: plain number → not a power function; x in the exponent → not a power function.
  Footer `3:PROPERTIES`.
* properties from K and P (typed as a fraction): p, a/b parity, symmetry, quadrants, domain,
  range, increasing, decreasing, bounded, asymptotes, end behavior, continuity, Q1/Q4 shape.
* build: quadrants + near 0 (through origin / asymptotes) + shape → one valid k·x^(a/b).

### 7 DECOMPOSE (`HADECOMP`)
shapes: 1:K(STUFF)^N+C 2:K√(STUFF)+C 3:K/(STUFF)^N+C 4:K/√(STUFF)+C 5:K|STUFF|+C
6:A(STUFF)²+B(STUFF)+C 7:K/(M+𝑒^(STUFF)) 8:√(K/STUFF). The student types the inside
STUFF as text; the answer gives g(x) and f(x), two or three ways when the class expects it.

## Testing

`tools/tibasic.py` runs the TI-BASIC source on a model of the TI-84 Plus CE home screen
(26 × 10, 14-digit arithmetic, strings, lists, loops, program calls). `tools/tests/*.py`
script every practice problem and worked example (inputs → expected answer from the study
guide); `tools/run_tests.py` runs them all and writes TESTS.md. Static checks: every
label/jump, no jumps out of blocks, every token on the allowed list.

Also:
* `tools/fuzz/fuzz_<group>.py` drive each solver from the main menu with thousands of random
  problems (negatives, fractions, zeros, ENTER defaults, infinite ends, CLEAR detours) and compare
  the ANSWER lines with an independent exact oracle (sympy / fractions).
* `tools/poison.py` reruns the tests or a fuzzer with every variable a helper really writes (except
  its outputs) set to junk after each helper call, so a solver that keeps a value across a call fails.
* `tools/check_static.py` (layers, blocks, labels, widths, tokens), `tools/build.py` (one `.8xp` per
  program, every token cross-checked with the TI-Toolkit token sheet) and `tools/verify.py`
  (byte-level check of each file: header, checksum, RAM flag, tokens decode back to the source).
* `tools/coverage.py` writes COVERAGE.md from the inventory, the coverage maps and the test runs.
