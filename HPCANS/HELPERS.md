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
  (|θ| ≥ 1ᴇ98), or a decimal like `1.414214` when no fraction with denominator ≤ 9999
  matches to 1e-11 (relative). Also X = signed numerator, Y = denominator,
  Z = 1 exact / 0 decimal. |θ| < 1ᴇ-9 counts as 0. Uses ʟFR, Str8.
* **HADIG** — Y (integer ≥ 0) → Str8 digits. (Used by HAFRAC.)
* **HANUM** — Str8 (text the student typed with `Input "…",Str8`) → θ.
  Empty → θ = 0 and Z = 1 (so a caller can apply a default); otherwise Z = 0.
  A leading subtraction minus is turned into the (-) sign; `-` or `(-)` alone means -1;
  any `I` in the text means infinity (±1ᴇ99). Pattern:
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
* **HAOUT** — prints Str9 on the next row (W+1). Wraps at 26 columns; after row 8 it
  shows `ENTER=MORE`, waits for ENTER, clears and continues. Use one call per line.
* **HAEND** — footer: Str9 = footer text (≤ 26 chars, e.g. `"1:AGAIN  2:HOME  3:WHY"`),
  θ = number of choices → shows it on row 10 and returns θ = chosen digit (0 = CLEAR).
  Always treat 0 like HOME.
* **HAROOT** — ʟQC = {a,b,c} → real roots of ax²+bx+c in ʟRT (sorted), θ = count
  (0, 1, 2; −1 if 0 = 0 for every x). Works for a = 0 (linear).

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
  Clears the screen itself.

## High

* **HAPTS** — Str9 = heading → asks for corner/end points of a graph (how many, then
  X and Y of each) and whether the end dots are solid → ʟHX, ʟHY (sorted by x),
  ʟHC = {left closed, right closed}.
* **HAABCK** — Str9 = template line (e.g. `"Y=A*F(BX+C)+K"`) → asks A (front),
  B (x coefficient, not 0), C (inside number), K (end number); ENTER = 1 for A and B,
  0 for C and K → N=A, O=B, P=C, Q=K.
* **HAEQN** — N=A, O=B, P=H, Q=K → Str5 = `Y=2F(-4/3(X-3))-3`-style factored form,
  Str4 = `Y=2F((-4/3)X+4)-3`-style expanded form.
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
