# Authoring spec — TI-84 Plus CE kinematics programs

This is the contract for every program in `src/`. Read it fully before writing or reviewing code.
The student has an AP Physics 1 Unit 1 (kinematics) test tomorrow and will run these on a
**TI-84 Plus CE** (home screen **26 columns × 10 rows**).

## 1. Files and tools

| Path | What |
|---|---|
| `src/NAME.txt` | TI-Basic source, one program per file, UTF-8, `\n` line endings, ends with exactly one `\n`. The file name is the program name (≤ 8 chars, A–Z/0–9, all caps). This file is also what the student types by hand if the transfer fails. |
| `8xp/NAME.8xp` | Built by `python3 tools/build.py` (tivars_lib_py tokenizer). Never hand-edit. |
| `tools/build.py` | Tokenize + lint + build + round-trip diff. `python3 tools/build.py --check --only ZVOVF` lints one program without writing files (use this while developing; other agents are editing other files at the same time). |
| `tools/tisim.py` | TI-Basic simulator that runs the token stream. `python3 tools/tisim.py --src PHYSOLVE 1 8 999 120 999 1.5 7` runs PHYSOLVE with scripted keys (menu choice numbers / typed values) and prints every Pause screen. |
| `reference/NAME.py` | Python reference implementation of a solver that mirrors the TI-Basic logic **line for line** (same branches, same equations, same order, same messages), returning the values shown on screen. Use `reference/common.py` (`G = 9.8`, `UNKNOWN = 999`, `fmt3()`). |
| `tests/test_NAME.py` | Runs the TI-Basic in the simulator through the real menus of PHYSOLVE, compares every displayed value with the reference implementation **and** with the hand-computed expected values, and checks there are no errors/leaks/scrolling/truncation. Use `tests/harness.py` (see `tests/test_helpers.py` for the style). Run with `python3 tests/test_NAME.py`. |

Only edit the files you own. Do not edit `tools/`, `tests/harness.py`, `reference/common.py`, or
another program's files; if you think one of them is wrong, say so in your final report.

## 2. Program map

```
PHYSOLVE (main menu; saves A–W,Z except O,R,T in ʟPSAV, restores them on QUIT)
  page 1: 1 VOVFSTA SOLVER  → 1→K, prgmZVOVF      (A)
          2 FREE FALL       → prgmZFREE           (B)  (its option "VOVFSTA (A=-9.8)" does 2→K, prgmZVOVF)
          3 HORIZONTAL LAUNCH → 1→K, prgmZPROJ    (C)
          4 ANGLED LAUNCH   → 2→K, prgmZPROJ      (D)
          5 THROW LAB (BACKWARD) → 3→K, prgmZPROJ (E)
          6 MORE >   7 QUIT
  page 2: 1 RIVER CROSSING  → prgmZRIVER          (F)
          2 CHASE PROBLEM   → prgmZCHASE          (G)
          3 VECTOR COMPONENTS → 1→K, prgmZTOOLS   (H)
          4 AVG SPEED/VELOCITY → 2→K, prgmZTOOLS  (I)
          5 FACTOR OF CHANGE → 3→K, prgmZTOOLS    (J)
          6 LAB TOOLS       → 4→K, prgmZTOOLS     (K)
          7 BACK
PHYSREF (reference screens; standalone; uses no variables)
Helpers: ZFMT (number → string), ZLINE (wrapped Disp), ZQUAD (quadratic in T)
```
When a subprogram returns, PHYSOLVE shows the menu page it came from again.

## 3. Variables (registers)

| Variable | Rule |
|---|---|
| **R, T, X, Y, θ** | **Never use** (graphing / solver / table clobber them). The linter rejects them. Labels must not contain them either. |
| **O** | Never use (looks like zero when typing by hand). |
| **U, W, Z** | Helper temporaries. `Z` is ZFMT's input. Never keep a value in U, W or Z across any `prgm` call. |
| **G, H, I, J** | ZQUAD outputs (overwritten by ZQUAD). Free scratch otherwise. |
| **L, M, N** | ZQUAD inputs (ZQUAD does not change them). Free scratch otherwise. |
| **K** | Dispatch code set by the caller just before `prgm…`. Read it at the top of the subprogram; do not overwrite it (exception: ZFREE sets `2→K` right before `prgmZVOVF`). |
| **A, B, C, D, E, F, P, Q, S, V** | Solver state. No helper touches them. Conventional meaning where it fits: `V`=v0, `F`=vf, `S`=s (displacement), `D`=t (time), `A`=a. |
| **Str8, Str9** | ZFMT (Str9 = result). |
| **Str0** | ZLINE input; ZQUAD overwrites it. |
| **Str1–Str4** | Your scratch for building lines; no helper touches them. |
| Lists | Do not create or touch any list (PHYSOLVE alone uses its own `ʟPSAV`). Never use L₁–L₆. |

All variables are global. Do not rely on any variable's value at program start other than `K`
(the simulator starts every run with random garbage in A–Z and the angle mode in Radian).

## 4. Helpers (already written and tested — call them, don't copy them)

* **`prgmZFMT`** — formats `Z` to 3 significant figures in `Str9`: `20.6`, `-29.7`, `0.774`, `600`,
  `2.00` (trailing zeros kept), `1.23E6` / `4.50E-4` outside 0.001…999999, `0` if |Z| < 1E-9. Uses
  U, W, Str8; does not change Z. Typical use:
  ```
  F→Z
  prgmZFMT
  Disp "VF = "+Str9+" M/S"
  ```
* **`prgmZLINE`** — `Disp`s `Str0`, wrapped into 26-character rows (uses W). Use it for any line
  built from several numbers, because such a line can exceed 26 characters.
  ```
  V→Z
  prgmZFMT
  "VF = "+Str9+" + ("→Str1
  A→Z
  prgmZFMT
  Str1+Str9+")("→Str1
  D→Z
  prgmZFMT
  Str1+Str9+")"→Str0
  prgmZLINE
  ```
* **`prgmZQUAD`** — solves `L·T² + M·T + N = 0`. It clears the screen and displays (without
  pausing) up to 7 rows: a title, the equation with numbers, the formula, B²-4AC, and the roots.
  Outputs: `J` = number of roots (0, 1 or 2), `H` = earlier (smaller) root, `I` = later (larger)
  root, `G` = discriminant. If L = 0 it solves the linear equation (J = 1, H = I) or reports no
  solution (J = 0). After it returns **you** add at most 3 more `Disp` rows explaining which root
  is physical (or why there is none), then `Pause `. Example (thrown up at 10 m/s from a 15 m roof):
  ```
  SOLVE QUADRATIC FOR T
  4.90T²-10.0T-15.0=0
  T=(-B+/-√(B²-4AC))/(2A)
  B²-4AC = 394
  T1 = -1.01 S
  T2 = 3.05 S
  T1<0 IS BEFORE THE THROW,   <- your rows
  SO T = 3.05 S
  ```

## 5. Physics conventions (the class's — must match)

* g = 9.8 m/s², **up is positive**, so free-fall acceleration is a = −9.8 m/s² at all times
  (including at the top). No air resistance.
* Displacement is **S**. The five variables are **V0, VF, S, T, A** ("VOVFSTA"). On screen write them
  uppercase: `V0`, `VF`, `S`, `T`, `A`.
* The five equations (with the variable each one is missing):
  `VF=V0+AT` (no S), `S=V0T+(1/2)AT²` (no VF), `S=VFT-(1/2)AT²` (no V0), `VF²=V0²+2AS` (no T),
  `S=(1/2)(V0+VF)T` (no A).
* Results: 3 significant figures via ZFMT, **always with units**, signs shown: `VF = -29.7 M/S`.
  For vertical motion add a direction word where it helps: `VF = -29.7 M/S (DOWN)`.
* Units on screen: `M`, `S`, `M/S`, `M/S²`, `°`. Angles in degrees (every program starts with `Degree`).

## 6. Screen and UI rules

* **Every program's first line is `Degree`.**
* Every screen starts with `ClrHome` and ends with `Pause `. Never more than **10 rows** on a
  screen (count ZLINE/ZQUAD rows; plan for a wrapped line taking 2 rows). The simulator reports
  any scrolling (`SCROLL`) as a failure.
* Every `Disp` string literal ≤ 26 characters; `Input` prompts ≤ 18 characters (room to type).
  Build any line containing numbers with ZFMT and keep it ≤ 26 characters for typical values, or
  send it through ZLINE.
* Inputs: use `Input "PROMPT=",VAR` (preferred) or `Prompt VAR`. Show what to enter (units, sign
  convention, sentinel) on a screen *before* the inputs, e.g. `ENTER 999 IF UNKNOWN`.
* Solvers: an input screen → one screen **per step** (which equation and why, the equation, the
  numbers substituted, the result/intermediate values) with `Pause ` → a final **SUMMARY** screen
  that lists every result as `NAME = VALUE UNIT`, one per row, then `Pause `.
* `Menu(`: ≤ **7** options, title ≤ 24 chars, option text ≤ 22 chars, and every menu has a
  `BACK` (or `QUIT`) option. After a menu choice, the target code starts with `ClrHome`.
* Impossible inputs (negative under a square root, division by zero, sin⁻¹ of more than 1, no
  positive root, …) must be detected **before** the operation and produce a clear message screen
  (`ClrHome`, what is wrong in plain words, `Pause `), then return to the menu. **No input may
  cause a calculator error.** (Typing letters where a number is expected is the user's problem.)
* Summary lines must be parseable as `NAME = VALUE UNIT` (spaces around `=`). Message lines must
  not look like that (do not write `X = something` in prose; write `X IS ...`).

## 7. TI-Basic rules (the linter and simulator enforce most of these)

* One statement per line. **No `:`** anywhere (not even inside strings).
* Use the **negative sign `⁻`** for negative numbers (`⁻9.8→A`, `If W<⁻3`), the **minus `-`** only
  for subtraction. `⁻` right after a value (`2⁻3`) is rejected.
* Strings: **uppercase letters only**, digits, space and `= + - * / ( ) . , ² √ ° < > ≤ ≥ ≠ ? ! % |`.
  Not allowed in strings: `:`, `→`, `"`, `...` (becomes one glyph), lowercase, and any multi-character
  token such as `⁻¹`, `sin(`, `tan⁻¹(` (they cannot round-trip). Write inverse trig in text as
  `TAN⁻1(`, `SIN⁻1(` (the `⁻` sign followed by digit 1), "squared" as `²`, square root as `√(`,
  "proportional to" as `PROP TO` or explain with a factor (`2X V GIVES 4X S`), ½ as `(1/2)`.
* Command names include their trailing space: `Disp `, `Input `, `Prompt `, `If `, `While `,
  `Repeat `, `Lbl `, `Goto `, `DelVar `, `Pause ` — so a bare pause is the line `Pause ` (with the
  trailing space). Keep those spaces; the linter checks the token stream.
* Allowed commands/functions (others are rejected): `ClrHome Disp Output( Pause Input Prompt
  Menu( Lbl Goto If Then Else End While Repeat For( Return prgm DelVar Degree` and `abs( int(
  iPart( fPart( round( log( ln( ₁₀^( 𝑒^( √( sin( cos( tan( sin⁻¹( cos⁻¹( tan⁻¹( R►Pr( R►Pθ(
  P►Rx( P►Ry( min( max( sub( length( not(`, operators `+ - * / ^ ² ⁻¹ = ≠ < > ≤ ≥ and or xor`,
  `π`, `ᴇ`, `Str0`–`Str9`. (`Stop` only in PHYSOLVE/PHYSREF; subprograms use `Return`.) No `toString(`
  (needs OS 5.2+), no `Ans`-dependent tricks.
* **Never write `/` followed by an implied product** (`A/2B` is ambiguous); write `A/(2B)`.
* Close every parenthesis and quote (the calculator allows omitting them; don't).
* **Labels**: 1–2 characters from A–Z/0–9, unique within the program, no R/T/X/Y/θ.
* **Control flow (memory leaks!):** `Goto`, `Menu(` and `Return` may only run when no
  `If-Then`, `While`, `Repeat` or `For(` block is open in the current program. Inside a block use
  flags and let the block reach its `End`, or put the jump on a **single-line `If`** (no Then):
  ```
  If G<0
  Goto E1
  ```
  The simulator reports a jump/Return from inside an open block as `LEAK` (on the calculator this
  slowly eats memory and ends in ERR:MEMORY). The single-line `If … / Goto …` form is only safe
  when that `If` is itself at top level (not inside another open block).
* A subprogram finishes by reaching its last line or a top-level `Return`. Never call PHYSOLVE or
  PHYSREF from a subprogram (recursion). A subprogram with its own menu loops with `Goto` to its
  menu label and leaves through `BACK` → a label whose code is `Return` (top level).
* Compare computed values with a tolerance, not `=` (e.g. `If abs(G)<1ᴇ⁻9`). Comparing typed
  inputs with the sentinel (`If V=999`) is fine.
* Use `round(` only with 0–9 decimal places.

### 7b. Real-calculator safety rules (from the simulator audit)

* **No empty strings.** Never store `""` or build a string by appending to an empty one (some OS
  versions reject it). Start every string from real text (`"T = "+Str9→Str1`). The only allowed
  empty literal is `Disp ""` for a blank row. Linter + simulator (`EMPTY STRING`) enforce this.
* **No blank lines** in a program (a blank line is an empty statement; a false single-line `If`
  would skip it instead of the next real line). The linter rejects them.
* **Negative inputs:** the student must type negatives with the `(-)` key; the subtraction key
  gives ERR:SYNTAX and kills the program. Every input screen where a negative value is possible
  shows a line such as `NEGATIVE = (-) KEY`. In tests, type negatives as numbers (`-9.8`) or as
  strings starting with `⁻`; a string starting with ASCII `-` simulates the wrong key (ERR:SYNTAX).
* **Width budget:** a ZFMT value can be up to 9 characters (`-1.23E-10`). Any line holding a value
  should fit 26 characters with a 9-character value; otherwise build it in Str0 and use ZLINE.
  `harness.run(..., wide=True)` replaces every ZFMT result by `-8.88E-88` to check this.
* Handle the zero vector before `R►Pθ(` (and any angle of a zero-length vector): show a message
  or define the angle explicitly.
* The calculator stays in Degree mode after the programs end (expected).

## 8. Testing (required before you report done)

1. `python3 tools/build.py --check --only <your programs>` → no problems.
2. `reference/<name>.py`: functions that mirror your TI-Basic line for line and return the values
   your screens show (as numbers; the tests format them with `fmt3`).
3. `tests/test_<name>.py`: drive PHYSOLVE through the menus with `harness.run([...])`, then
   * `assert_clean(res)` (no error, no LEAK/SCROLL/TRUNCATED, program finished — end every script
     with the keys that get back out to QUIT: page 1 option 7, or page 2 option 7 then page 1 option 7),
   * compare the summary values with the reference (`fmt3(ref) == screen`) and with the expected
     numbers from the task (3 significant figures),
   * cover every menu path of your program and the impossible/edge inputs (each must give a
     message, not an error).
4. Read the actual screens (`print(res.text())`) and check that they read well for a student:
   the right equation is named, the substitution shows the numbers, signs and units are right.
