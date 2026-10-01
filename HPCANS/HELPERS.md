# Helper programs: API reference

All variables are global. Layers (see DESIGN.md): a program may store only to its own
layer's variables or lower ones (`tools/check_static.py` enforces this).

| Layer | Programs | Reals | Strings |
|---|---|---|---|
| low | HADIG HAFRAC HANUM HAKEY HAANS HAPAGE HAOUT HAEND HAROOT | W X Y Z θ | Str8 Str9 |
| mid | HAPOLY HAPMUL HADOM HAIVL | S T U V | Str6 Str7 |
| high | HAPTS HAABCK HAEQN HAPTXT HAFUNC HAGRAPH HAFSTR HAFEVAL HAFDOM HAFZERO HAWORDS | N O P Q R | Str4 Str5 |
| solver (default for any other program) | HPCANS HAOPS HACOMP HAINV HATRANS HAABS HAPOWER HADECOMP + their own helpers | A–M | Str0–Str3, L₁–L₅ |

A call to a helper may change every variable of that helper's layer **and all lower layers**.
Never keep a value in a lower-layer variable across such a call. θ is the usual argument
and result. Only HAANS/HAPAGE/HAOUT touch W (the answer-screen row).

## Low

* **HAFRAC** — θ (number) → Str9 exact text: `-17/4`, `6`, `0`, `INF`, `-INF`
  (|θ| ≥ 1ᴇ98), or a decimal like `1.414214` when no fraction n/d matches to 1e-11·max(1,|θ|)
  with d ≤ 9999 and d²·max(1,|θ|) ≤ 1ᴇ8 (the second limit keeps irrational numbers such as
  −24−4√17 from matching a large-denominator fraction by accident). Also X = signed numerator, Y = denominator,
  Z = 1 exact / 0 decimal. |θ| < 1ᴇ-9 counts as 0. Uses ʟFR, Str8.
* **HADIG** — Y (integer ≥ 0) → Str8 digits. (Used by HAFRAC.)
* **HANUM** — Str8 (text the student typed with `Input "…",Str8`) → θ.
  Empty → θ = 0 and Z = 1 (so a caller can apply a default); otherwise Z = 0.
  A subtraction minus typed first or right after `(`, an operator, `√(`, `³√(` or `,` is turned into
  the (-) sign (so `-3`, `2*-3`, `(-1/2)` all work); `-` or `(-)` alone means -1;
  a leading + is dropped (`+3` → 3, `+` alone → 1); an X in the text counts as 1 (`3X` → 3);
  any `I` (or the 𝑖 key) in the text means infinity (±1ᴇ99). Pattern:
  ```
  Input "B (X COEF)=",Str8
  prgmHANUM
  θ→B
  ```
* **HAKEY** — θ = N (largest choice) → waits for a number key 1..N or CLEAR;
  θ = the digit, or 0 for CLEAR (always means back/home). Draw the menu with
  `ClrHome` + `Disp` lines first (26 chars max per line, 10 rows).
* **HAANS** — starts an answer screen: ClrHome, `ANSWER:` on row 1, W = 1.
* **HAPAGE** — like HAANS but row 1 shows Str9 (e.g. `"WHY:"`).
* **HAOUT** — prints Str9 on the next row (W+1). A line wider than 26 columns is broken at
  the last space (dropped) or union U that fits, else after a comma, else before a + or - that
  joins terms, else at column 26. After row 8 it shows `ENTER=MORE  CLEAR=SKIP`: ENTER clears
  and continues; CLEAR skips the rest of this answer (later HAOUT calls print nothing until the
  next HAANS/HAPAGE), so the footer comes next. Use one call per line.
* **HAEND** — footer: Str9 = footer text (≤ 26 chars, e.g. `"1:AGAIN  2:HOME  3:WHY"`),
  θ = number of choices → shows it on row 10 and returns θ = chosen digit (0 = CLEAR).
  Always treat 0 like HOME.
* **HAROOT** — ʟQC = {a,b,c} → real roots of ax²+bx+c in ʟRT (sorted), θ = count
  (0, 1, 2; −1 if 0 = 0 for every x). Works for a = 0 (linear). Coefficients smaller than
  1ᴇ-12 × the largest are treated as 0 (rounding residue), and the roots use the stable
  formula q = −(b + sign(b)√disc)/2, roots q/a and c/q.

## Mid

* **HAPOLY** — ʟPLY = coefficients, highest degree first (any length ≤ 5) → Str7 text
  in X: `9X²+12X+3`, `-X+7`, `(3/4)X-2`, `X^4`, `0`.
* **HAPMUL** — ʟPA × ʟPB → ʟPC (polynomial product, highest degree first).
* **HADOM** — sets of reals as unions of intervals. Current set D in
  ʟDL (left ends) ʟDR (right ends) ʟDA (left closed 1/0) ʟDB (right closed 1/0);
  second set E in ʟEL ʟER ʟEA ʟEB. ±∞ = ±1ᴇ99. Opcode in θ:
  * 1: D = all reals 2: D = interval from S (left), T (right), U (left closed), V (right closed)
  * 3: E = all reals 4: E = interval S,T,U,V 10: E = D (copy)
  * 5: D = D ∩ E
  * 6: remove the point S from D 7: remove the closed stretch [S,T] from D
  * 8: E = { x : N(x)/Dn(x) ≥ 0 } (U = 1) or > 0 (U = 0), with ʟSN = {a,b,c} for N and
    ʟSD = {d,e,f} for Dn (quadratics; use 0 for missing terms; ʟSD = {0,0,1} for "no denominator")
  * 9: render D → Str6, in class notation: `ALL REALS`, `ALL REALS, X≠-5,-17/4`,
    `(-INF,-1)U(-1,5]`, `[-3,3]`, `NO REAL NUMBERS`.
* **HAIVL** — asks the student for an interval. Str9 = heading (e.g.
  `"ORIGINAL DOMAIN OF F:"`) → S, T (ends; ±1ᴇ99 for infinity), U, V (closed 1/0).
  Clears the screen itself. CLEAR at the bracket question is ignored (it asks again). A left end can only
  be -INF and a right end only INF (I or -I typed at either gives the right sign, so (-I,-I) is ALL
  REALS, never (-INF,-INF)); finite ends typed in the wrong order are swapped.

## High

* **HAPTS** — Str9 = heading → asks for corner/end points of a graph (how many, then
  X and Y of each) and whether the end dots are solid → ʟHX, ʟHY (sorted by x),
  ʟHC = {left closed, right closed}. The count is asked again until it is a whole number 1–50.
* **HAABCK** — Str9 = template line (e.g. `"Y=A*F(BX+C)+K"`) → asks A (front),
  B (x coefficient, not 0), C (inside number), K (end number); ENTER = 1 for A and B,
  0 for C and K; A = 0 or B = 0 redraws the screen (`A AND B CAN NOT BE 0`) and asks again;
  a leading + is dropped and an X typed at B counts as 1 (3X → 3, X/2 → 1/2)
  → N=A, O=B, P=C, Q=K. Uses Str4, Str5.
* **HAEQN** — N=A, O=B, P=H, Q=K → Str5 = `Y=2F(-4/3(X-3))-3`-style factored form,
  Str4 = `Y=2F((-4/3)X+4)-3`-style expanded form, Str9 = `A=2  B=-4/3  H=3  K=-3`.
  |H|, |K| < 1ᴇ-9 count as 0; an A or B that HAFRAC shows as 1 / -1 prints as no coefficient / -.
* **HAPTXT** — N, O → Str5 = `(x,y)` with exact numbers.

## Saved data (named lists, kept between runs)

`HPCANS` runs `SetUpEditor` on these so they always exist (dim 0 = nothing saved):
ʟBX ʟBY ʟBC (base graph for transformations / absolute value), ʟGFX ʟGFY ʟGFC (graph of f),
ʟGGX ʟGGY ʟGGC (graph of g). Check `dim(ʟBX)=0` before offering "use saved".

## Screen and text rules

* 26 columns × 10 rows. Every `Disp`/`Output(` text ≤ 26 characters (checker enforces).
* Allowed characters in quotes: A–Z 0–9 space ( ) , . + - * / ^ = < > ≤ ≥ ≠ ? [ ] : | ² ³ ⁻¹ ⁻ √( ³√( 𝑒^( θ.
  No lowercase, no `#`, no `"` or `→` inside text.
* Menus: `ClrHome`, `Disp` title + numbered lines, then `N→θ:prgmHAKEY`. CLEAR (θ = 0) = back.
* Answers: `prgmHAANS`, then each line via `…→Str9:prgmHAOUT`, then the footer via HAEND.
* No `Goto`, `Lbl` or `Return` inside If-Then / For / While / Repeat blocks: jump with a
  single-line `If` at top level. `Return` goes back to HPCANS (the menu).
* Numbers shown to the student always go through HAFRAC (never `Disp` a raw number).

## Function helpers

High layer (reals N–R, Str4, Str5). They ask for a function by its shape, keep it as a
**function record**, and answer questions about it. Tests: `python3 tests/test_helpers.py`
from `tools/` (70 driver cases; each recipe below is a test there).

### Function record (a list)

Slots: `ʟF1` (usually f), `ʟF2` (usually g), `ʟF3` (scratch, e.g. a composite a solver builds).
Every helper takes the slot number in **N** (1, 2 or 3).

| kind | list | meaning |
|---|---|---|
| 1 rational | `{1, n4,n3,n2,n1,n0, d4,d3,d2,d1,d0, 1, 0}` | f(x) = N(x)/D(x) (polynomials, highest power first; D = `{0,0,0,0,1}` for a polynomial). Items 12, 13 are ignored. |
| 2 root | `{2, n4..n0, d4..d0, K, C}` | f(x) = K·√(N(x)/D(x)) + C |
| 3 graph | `{3, n, Lc, Rc, x1..xn, y1..yn}` | corner points left to right, straight segments; Lc/Rc = end dot solid (1) or hollow (0) |
| 4 words | `{4, L, R, Lc, Rc, m, a1,b1, …, am,bm}` | domain is one interval L..R (±ᴇ99 = ∞); f(x)=0 exactly on the m closed stretches [ai,bi] (a point is ai = bi); other values unknown |

A solver may build kind 1/2 records itself (`{2,0,0,1,⁻3,0,0,0,0,0,1,1,0}→ʟF3` is √(X²−3X)).
Domain, zero and band work needs N and D of degree ≤ 2 (items 2, 3, 7, 8 = 0); otherwise the helper
returns θ = 0 ("not supported") and leaves D unchanged. Evaluating and text work for any degree.

### Calls

* **HAFUNC** (ask the student) — N = slot, Str9 = name shown (1–4 chars: `"F"`, `"G"`, `"A"`, `"B"`),
  O = shape: 0 shows the menu `F(X) LOOKS LIKE?`; 1–8 skips it (1 AX+B, 2 AX²+BX+C,
  3 (AX+B)/(CX+D), 4 K/(AX+B), 5 K√(AX+B)+C, 6 (AX²+BX+C)/(DX²+EX+F), 7 graph, 8 words);
  9 = the saved graph for this name with no questions.
  → record in ʟF<N>; **θ = 1** done, **θ = 0** the student pressed CLEAR (or O = 9 and nothing is saved):
  go back to your menu. N is still the slot afterwards.
  ENTER defaults: a coefficient of X (or K in front) = 1, a plain number = 0; in shape 6 "no X² / no X
  term" is typed as 0. A bottom that is 0 is refused and asked again. √X = shape 5 and ENTER ×4.
  Graph: a submenu offers `2:USE SAVED GRAPH OF F` / `3:…OF G` when saved; a typed graph (via HAPTS)
  is saved to ʟGGX ʟGGY ʟGGC when the name is `"G"`, else to ʟGFX ʟGFY ʟGFC (HPCANS must have run
  its `SetUpEditor`, so these lists exist). Words: HAIVL for the domain, then how many single x with
  f = 0, then how many intervals `FROM X=`/`TO X=` with f = 0 (each count 0–9; anything else is asked
  again, so a typo cannot start 22 prompts).
* **HAFSTR** (text) — N = slot → **Str5** = the function in X: `-X+3`, `2X²-1`, `(X+1)/(X-2)`, `2/X`,
  `(X-3)/X²`, `√(-X+5)`, `7√(X)+4`, `(1/2)√(X-1)`; `""` for graph and words.
* **HAFEVAL** (value) — N = slot, O = x → **P** = f(x), **Q** = 1 defined, 0 undefined (outside the
  domain, bottom 0, negative under √, x off the graph or at a hollow end), 2 = words record, x in the
  domain but the value was not given (P = 0; the value is known to be nonzero, since the words list
  every zero). Graphs: straight-line interpolation between corners. A value under √ within 1ᴇ-9 of 0
  counts as 0 (3(-4/3)+4 leaves a 1ᴇ-13 residue), so √ at a domain end point is exactly 0.
* **HAFDOM** (sets) — always **intersects into the current HADOM set D** (start with `1→θ:prgmHADOM`):
  * O = 0: D = D ∩ domain(f). Rational: all reals minus the bottom's zeros. Root: sign chart of the
    inside. Graph: [x1, xn] with the end dots. Words: the interval.
  * O = 1: D = D ∩ {x in domain(f) : P ≤ f(x) ≤ Q}. P, Q may be ⁻ᴇ99 / ᴇ99; R = 1·(P included) +
    2·(Q included). "Where f ≥ 0" (√ of a graph) is `0→P:ᴇ99→Q:1→R`. Not for words (θ = 0).
  * O = 2: D = D ∩ domain of **f(g(x))** with N = slot of the inside g, P = slot of the outside f:
    x in Dg and g(x) in Df. Outside rational: removes every x with g(x) = a zero of f's bottom.
    Outside root/graph/words: keeps g(x) inside f's domain interval (a root whose inside has a
    2-piece domain gives θ = 0).
  → **θ = 1** ok, 0 not supported. Render with `9→θ:prgmHADOM` (Str6).
* **HAFZERO** (where f = a level) — N = slot, O = level (0 for zeros), P = 1 to also remove them from D
  (D = D minus each stretch, HADOM op 7), P = 0 to only list them → **ʟFZL, ʟFZR** = closed stretches
  (a point has equal ends), **R** = how many (the lists are `{0}` when R = 0, so loop `For(I,1,R)`),
  θ = 1 ok / 0 not supported. Rational: N − level·D = 0 where D ≠ 0 (a hole is not a zero). Root:
  K√u + C = level. Graph: corners at the level, crossings between corners (exact), and whole flat
  segments. Words: the typed stretches (level 0 only). If f equals the level everywhere, one stretch
  [⁻ᴇ99, ᴇ99] is returned. Stretches are always reported closed (a zero piece that runs into a hollow
  end dot includes that end), so remove them from a D that is already inside f's domain, as the
  recipes below do.
* **HAGRAPH**, **HAWORDS**: internal (called by the helpers above with the record in ʟFNC).

**Clobbers.** Each call may change N–R, Str5 (HAFUNC also Str4), every mid/low variable, the E set
(ʟEL ʟER ʟEA ʟEB), HADOM/HAROOT/HAPOLY scratch lists, ʟHX ʟHY ʟHC, and its own lists (ʟFNA ʟFNC ʟFNN
ʟFND ʟFNR ʟFNS ʟFNT ʟFNV ʟFNX ʟFNY ʟFNB ʟFNW ʟFGL ʟFGR ʟFGA ʟFGB ʟFZL ʟFZR). HAFDOM/HAFZERO also change
D (that is their output). Records ʟF1–ʟF3 change only through HAFUNC (and your own stores); a graph
typed in HAFUNC also replaces the saved graph of that name (ʟGFX… or ʟGGX…).
Copy results into A–M / Str0–Str3 / L₁–L₅ before the next helper call.

### Recipes (all tested; `:` here = a new line in the src file)

```
1→N:0→O:"F"→Str9:prgmHAFUNC        f from the shape menu (θ=0 → back to your menu)
2→N:0→O:"G"→Str9:prgmHAFUNC        g
1→θ:prgmHADOM                      domain of F/G (drop the HAFZERO line for F+G, F-G, FG):
1→N:0→O:prgmHAFDOM
2→N:0→O:prgmHAFDOM
2→N:0→O:1→P:prgmHAFZERO            remove the zeros of the bottom function (points and segments)
9→θ:prgmHADOM                      Str6 = "ALL REALS, X≠0,2,5" or "[-5,-2)U(1,5)U(5,6]"
1→N:⁻2→O:prgmHAFEVAL               P = f(-2), Q = 1 if defined
1→θ:prgmHADOM:2→N:2→O:1→P:prgmHAFDOM   domain of f(g(x)) (g inside = slot 2, f outside = slot 1)
1→θ:prgmHADOM:1→N:1→O:0→P:ᴇ99→Q:1→R:prgmHAFDOM   where f ≥ 0 (√(f(x)) with f a graph)
1→N:9→O:"F"→Str9:prgmHAFUNC        f = saved graph of F, no questions (θ=0: none saved)
```
Coefficient arithmetic for formulas: kind-1 records hold N in items 2–6 and D in items 7–11, e.g.
`seq(ʟF1(I),I,2,6)-seq(ʟF2(I),I,2,6)→ʟPLY:prgmHAPOLY` gives `2X²+X-4` for PR-1.1 (both bottoms 1).
Note for the simulator: HADOM op 9 reads V before storing it when D is one interval; HAFDOM and
HAFZERO set V first, but if you render a D built only with HADOM ops, do `0→V` before `9→θ:prgmHADOM`.
