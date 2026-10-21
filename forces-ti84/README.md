# FORCES: Newton's laws solver for the TI-84 Plus and TI-84 Plus CE

FORCES is a plain TI-BASIC program (no assembly, no shell) that works every
problem type on the *Equilibrium & non-equilibrium* quiz prep: elevators and
apparent weight, Atwood machines, table + hanging mass, pulls on a level
floor, inclines, Newton's third law, and quick concept checks. Every result
screen shows the setup as well as the numbers:

1. the positive direction (`+ = UP`, `+=TO PULLEY AND` / `HANGER DOWN`, `+X=DOWNHILL`, …)
2. the force equation (`N-MG=MA`, `M1G-T=M1A`, `FCOSθ-FRIC=MA`, …)
3. the answers, rounded with `round(X,3)`, with units (`N=678 N`, `AY=⁻2 M/S²`)
4. the direction in words (`ACCEL: UP`, `HANGER MOVES DN`, `TABLE: TO PULLEY`)

Screen text quoted below is the TI-84 Plus wording. The CE shows the same
rows with longer wording (for example `HANGER MOVES DOWN`), as listed in
`SCREENS.md`.

## Files

| File | What it is |
|------|------------|
| `TI-84_Plus/FORCES.8xp` | Program for the **monochrome TI-84 Plus / Silver Edition** (16×8 screen). Runs on any OS. |
| `TI-84_Plus/FORCES.txt` | Its readable source, one command per line. |
| `TI-84_Plus_CE/FORCES.8xp` | Program for the **TI-84 Plus CE** (26×10 screen). Needs CE OS 5.2 or newer (it uses `toString(`). |
| `TI-84_Plus_CE/FORCES.txt` | Its readable source. |
| `reference.py` | Python version of every solver with the same math, plus the test suite (`python3 reference.py`). |
| `TEST_RESULTS.md` | The 12 required cases: assignment vs. Python vs. what each calculator shows. |
| `SCREENS.md` | Every result screen for a tour of example problems, drawn at the real screen size for both calculators. |
| `tools/` | Build and verification tools (see [How it was built and checked](#how-it-was-built-and-checked)). |

**Why two programs?** The two calculators run the same math and the same
menus, but the screens differ. The TI-84 Plus has 16 columns × 8 rows, and
the busy/pause indicator sits on row 1, column 16. The CE has 26 × 10 and a
separate status bar. The mono version places each unit right after the number
with `Output(` and a column formula, and keeps every line to 16 characters.
The CE version uses `toString(` to print `LABEL=value UNIT` lines with longer,
clearer labels (`SCALE N=678 N`, `TRUE WEIGHT MG=588 N`). If your CE's OS is
older than 5.2 (check with `2nd` `MEM` `1:About`), use the TI-84 Plus file on
the CE instead: it runs unchanged in the top-left corner of the screen.

## Sending it to the calculator

1. Install **TI Connect CE** (free, education.ti.com). It handles both the CE
   and the monochrome TI-84 Plus over the USB cable. The old TI Connect 4.0 is
   only for serial-cable calculators.
2. Connect the calculator and turn it on.
3. Drag the right `FORCES.8xp` onto the calculator in TI Connect CE
   (*Calculator Explorer*), or use *Actions → Send to Calculators*.
4. **TI-84 Plus:** the program is about 16.5 KB and must sit in RAM to run
   (the calculator has about 24 KB). Before sending, check `2nd` `MEM`
   `2:Mem Mgmt/Del` `1:All`. If **RAM FREE** is under about 18,000 bytes,
   archive or delete programs and lists you aren't using (archive: select
   the item and press `ENTER` so a `*` appears), then send again. If you
   archived FORCES itself, go to `7:Prgm`, select it and press `ENTER` to
   clear the `*`. ERR:MEMORY when unarchiving means the same thing: free
   more RAM. A CE on OS 5.3+ can run FORCES straight from Archive.
5. Run it: `PRGM`, pick `FORCES`, press `ENTER` twice.

### Before you run it

* **Negative numbers:** type them with the `(-)` key, not the minus key.
  Minus at the start of an entry means "Ans minus …". Prompts that take a
  signed value show `USE (⁻) FOR NEG` and use the ⁻ sign
  (`AY (+UP/⁻DN)=`).
* **Variables:** FORCES overwrites A, C, D, F, G, H, K, L, M, N, P, Q, S–Z
  (X only on the TI-84 Plus), θ and Str1–Str8 (plus Str9 on the TI-84
  Plus). It never touches lists (L1–L6 or named lists) or matrices.
* **g is kept in G** and remembered between runs. It is checked at start: if G
  is not 9.8, 9.81 or 10, it is reset to 9.8. When it is 9.81 or 10, a NOTE
  screen reminds you on start-up.
* **Modes:** FORCES sets Degree, Float, Normal and Full. On QUIT it restores
  your previous angle mode (Degree/Radian). It does not restore Float, Normal
  or Full.
* **MathPrint OS on the TI-84 Plus (2.53MP/2.55MP):** keep *Answers* on AUTO
  or DEC in the MODE screen. FRAC could print answers as fractions.
* **Leaving a prompt blank:** the optional prompts (μs, the 3rd-law force,
  and the extra forces in ΣF = ma) take **ENTER alone or 0** to mean "skip".
* **Getting out:** use MORE > QUIT (this restores the angle mode). `ON` breaks
  out at any time.

## Menus and inputs

Main menu **NEWTON SOLVER** (CE wording in brackets where it differs):

### 1 ELEVATOR (submenu) — up is positive

| Option | Asks for | Shows |
|--------|----------|-------|
| FIND SCALE N | mass M (kg), size of a (m/s², no sign); then the **acceleration direction** UP / DOWN / ZERO, or **FROM MOTION >** to pick MOVING UP / MOVING DOWN / STAYS AT REST and then SPEEDING UP / SLOWING DOWN / CONSTANT V | `N-MG=MA`, the reason for the direction (e.g. `A OPPOSITE TO V`), aᵧ with sign, N = m(g + aᵧ), true weight mg, `ACCEL: UP/DOWN/NONE`, and `HEAVIER (N>MG)` / `LIGHTER (N<MG)` / `NORMAL (N=MG)` / `WEIGHTLESS (N=0)`. If you typed a nonzero a but then picked ZERO, STAYS AT REST or CONSTANT V, it says `A=0 (A IGNORED)`. "Starts from rest and speeds up" is MOVING UP/DOWN + SPEEDING UP. If aᵧ < −g: `N<0: LIFTS OFF`, the scale reads 0. |
| ACCEL FROM N [FIND ACCEL FROM SCALE] | mass M, scale reading N (≥ 0); after the first screen, the **velocity direction** UP / DOWN / UNKNOWN | aᵧ = (N − mg)/m with sign and direction, mg; then `SPEEDING UP` or `SLOWING DOWN`. If UNKNOWN it lists both possibilities (`DOWN+SPEEDING OR UP+SLOWING`). If a = 0: constant velocity (or at rest, when V is unknown). |
| FREE FALL | nothing | N = 0, aᵧ = −g, `ACCEL: DOWN`, `WEIGHTLESS`. |
| FIND MASS | scale reading N (> 0), signed aᵧ | m = N/(g + aᵧ), mg. If aᵧ ≤ −g: `IMPOSSIBLE`. |

### 2 ATWOOD (2 HANG) — heavy side down is positive

| Option | Asks for | Shows |
|--------|----------|-------|
| FIND A AND T | M1, M2 (kg) | The heavier mass is picked automatically. Both equations (e.g. `M1G-T=M1A`, `T-M2G=M2A`), a = (M−m)g/(M+m), T = m(g+a), which mass goes DOWN and which goes UP, then a check screen with M1G, M2G, T, `M2G<T<M1G` and `CHECK OK`. Equal masses: a = 0, T = mg, `EQUILIBRIUM`. |
| FIND 2ND MASS [FIND OTHER MASS FROM A] | a (m/s²), known mass (kg), then whether the known mass is the HEAVIER (DOWN) or LIGHTER (UP) one | The other mass (light = heavy·(g−a)/(g+a) or heavy = light·(g+a)/(g−a)), T, both masses, `HEAVY GOES DOWN`. If a = 0 the masses are equal: `EQUILIBRIUM`. If a ≥ g: `IMPOSSIBLE`. |

### 3 TABLE + HANGER — toward the pulley / down is positive

Asks for the table mass, the hanging mass, μk (0 = frictionless), then, only if
μk > 0, μs (ENTER alone or 0 = use μk; μs must be ≥ μk).

Both result screens give the + direction as `+=TO PULLEY AND` / `HANGER DOWN`
(CE: `+=TO PULLEY, HANGER DOWN`). On the stays-put screen it comes right
after `BLOCK STAYS PUT`.

* **Moves** (frictionless, or mg > μs·Mg): `HANG: MG-T=MA`,
  `TABLE: T=MA` or `TABLE: T-FK=MA`, a = (mg − μk·Mg)/(M + m), T = m(g − a),
  `HANGER MOVES DN`, `TABLE: TO PULLEY`, then N on the table = Mg and
  fk = μk·N.
* **Stays put** (mg ≤ μs·Mg): `BLOCK STAYS PUT`, `HANG: MG-T=0`,
  `TABLE: T-FS=0`, a = 0, T = mg, static friction fs = mg (pointing away
  from the pulley), fs max = μs·N.

### 4 FLAT SURF PULL [FLAT SURFACE PULL] — level floor, aᵧ = 0, +x = pull direction

Asks for m, the applied force F, and θ above horizontal (0 = horizontal,
negative = pushing down at an angle, −90 to 90). Then, what you know:

| Option | Extra input | Solves for |
|--------|-------------|------------|
| FRICTION (N) | friction force | aₓ = (F cos θ − f)/m |
| MUK | μk | f = μk·N, then aₓ |
| CONSTANT V | — | f = F cos θ (aₓ = 0), plus the μ needed = f/N |
| ACCEL AX | aₓ (signed) | f = F cos θ − m·aₓ |

Shows `N+FSINθ-MG=0`, `FCOSθ-FRIC=MA`, Fx, Fy, N = mg − F sin θ, the
friction and its direction (`FRIC POINTS LEFT`, or `NO FRICTION`), and aₓ
with its direction. Special messages:

* `N<0: LIFTS OFF`.
* Friction < 0: it would have to point right. That only happens if the box
  slides left; if it moves right, that aₓ is impossible.
* Friction > Fx: if at rest, the block stays put; if moving, it slows down.

### 5 INCLINE (submenu) — each asks for m and the slope angle θ (0 < θ < 90)

Every option ends with a components screen: `MGSINθ=…` with `SIN: DOWNHILL`
and `MGCOSθ=…` with `COS: INTO SLOPE`.

| Option | Extra input | Shows |
|--------|-------------|-------|
| AT REST | μs (ENTER alone or 0 = skip the check) | `+X=UPHILL`, `FS-MGSINθ=0`, `N-MGCOSθ=0`, N = mg cos θ, the friction needed to hold it fs = mg sin θ (`FS POINTS UPHILL`); with μs: fs max = μs·N and `YES: STAYS PUT`, or `NO: WILL SLIDE` + `USE SLIDING MUK`; always the minimum μs = tan θ |
| SLIDING W/ MUK [SLIDING DOWN WITH MUK] | μk | `+X=DOWNHILL`, `MGSINθ-FK=MA`, a = g(sin θ − μk cos θ), fk = μk·N uphill. If a < 0 it says it slows down (and would not start sliding from rest). |
| FRICTIONLESS | — | a = g sin θ downhill, N |
| MIN MUS (HOLD) [MIN MUS TO HOLD AT REST] | — (m is asked only for the components) | μs min = tan θ (mass cancels) |
| PUSHED UP [PUSHED/PULLED UP SLOPE] | F (pushing or pulling **up the slope, parallel to it**), μk (0 = none) | Assumes the block moves up. `+X=UPHILL`, `F-MGSINθ-FK=MA`, `N-MGCOSθ=0`, a = (F − mg sin θ − μk·N)/m, fk = μk·N downhill, and the **F needed for constant velocity** = mg sin θ + fk. If a < 0: if moving up it slows down; if at rest it won't start up the slope. |
| SLOPE + HANGER [SLOPE BLOCK + HANGER] | m is the **block on the slope**; then the hanging mass, μk (0 = frictionless) and, if μk > 0, μs (ENTER alone or 0 = use μk) | Rope parallel to the slope over a pulley at the top. Compares the hanger's weight with mg sin θ and max static friction μs·N. **Block moves up** (`BLOCK UPHILL: T-MGSINθ-FK=MA`, `HANGER DOWN: MG-T=MA`), **block slides down** (`MGSINθ-T-FK=MA`, `T-MG=MA`), or **`BLOCK STAYS PUT`** (`T+FS-MGSINθ=0`, T = mg, fs and its direction, fs max). Shows a, T, N, fk and which way each mass moves. |

### 6 3RD LAW — + is the direction of the force on B

Asks for mA, mB and F (ENTER alone or 0 = just the ratio). Shows
`FAB=-FBA` (equal and opposite), aB = F/mB, aA = −F/mA, and
`SIZE AA/AB=MB/MA` with the ratio, then two reminder screens: N and mg are not a third-law pair; the
partner of Earth's pull on you is your pull on Earth; pairs act on different
objects, so they never cancel on one diagram.

### 7 MORE > (submenu)

* **SIMPLE CASES**
  * HANGING, REST [HANGING AT REST (T=MG)]: m → T = mg.
  * TERMINAL VEL.: m → F_air = mg, a = 0, equilibrium at constant v.
  * HANG + ACCEL [HANGING, ACCELERATING]: m and signed aᵧ → T = m(g + aᵧ) and
    whether T > mg or T < mg. T < 0 means `ROPE SLACK`.
  * SUM F=MA: up to 4 signed forces (ENTER alone or 0 = none) and m → net
    force, a, `NET F: + DIR/- DIR/ZERO`, `EQUILIBRIUM: YES/NO`.
* **CONCEPT CHECK**: pick MOVING UP / DOWN / RIGHT / LEFT (then SPEEDING
  UP / SLOWING DOWN / CONSTANT V), AT REST, or V=0 1 INSTANT. Shows the
  acceleration direction, net force direction and whether it is in
  equilibrium. `V=0 1 INSTANT`: equilibrium is **not** guaranteed (top of a
  toss: a = g down).
* **SETTINGS (G)**: shows the current g, then pick 9.8, 9.81 or 10 (or KEEP).
* **QUIT**: restores your angle mode and ends the program.

Every result screen ends with a pause: press `ENTER` for the next screen.
After the last one you are back at the main menu.

## Cheat sheet: which menu answers which question

```
QUESTION                                  KEYS (menu option numbers)
Scale reading in an elevator, a given     1 ELEVATOR > 1 FIND SCALE N > UP/DOWN
...from "moving down, slowing" etc.       1 > 1 > 4 FROM MOTION > motion > change
Acceleration from a scale reading         1 ELEVATOR > 2 ACCEL FROM N
Speeding up or slowing down?              1 > 2 > (then pick the V direction)
Free fall / weightless                    1 ELEVATOR > 3 FREE FALL
Mass from scale reading + a               1 ELEVATOR > 4 FIND MASS
Atwood: a, T, who goes up/down            2 ATWOOD > 1 FIND A AND T
Atwood: find a mass from a                2 ATWOOD > 2 FIND 2ND MASS
Table block + hanging mass (stuck?)       3 TABLE + HANGER
Pull/push at an angle, level floor        4 FLAT PULL > 1 FRICTION / 2 MUK / 4 AX
Friction & N for constant velocity        4 FLAT PULL > 3 CONSTANT V
Block at rest on a slope (N, fs, slips?)  5 INCLINE > 1 AT REST
Sliding down a slope with friction        5 INCLINE > 2 SLIDING W/ MUK
Frictionless slope                        5 INCLINE > 3 FRICTIONLESS
Minimum mus to hold on a slope            5 INCLINE > 4 MIN MUS
Pushed/pulled up a slope (a, F for const v) 5 INCLINE > 5 PUSHED UP
Block on slope tied to a hanging mass     5 INCLINE > 6 SLOPE + HANGER
Collision/push: forces & accelerations    6 3RD LAW
Rope tension, hanging at rest             7 MORE > 1 SIMPLE > 1 HANGING, REST
Terminal velocity (air resistance)        7 MORE > 1 SIMPLE > 2 TERMINAL VEL.
Tension, mass accelerating on a rope      7 MORE > 1 SIMPLE > 3 HANG + ACCEL
Any 1-D problem: add forces, get a        7 MORE > 1 SIMPLE > 4 SUM F=MA
Which way is a / net F? Equilibrium?      7 MORE > 2 CONCEPT CHECK
Teacher uses g = 10 (or 9.81)             7 MORE > 3 SETTINGS (G)
```
The option numbers are the same on both calculators. The CE menus just
spell the names out (for example `FLAT SURFACE PULL`, `FIND OTHER MASS
FROM A`). Press the number key to pick an option.
## Typing it in by hand

`FORCES.txt` has one command per line (no `:` chains) and is exactly what the
`.8xp` holds. Create the program with `PRGM` `NEW` `FORCES` and type each line,
pressing `ENTER` at the end of each one. Key guide:

| In the listing | Key |
|----------------|-----|
| `→` | `STO→` |
| `⁻` (negative) | `(-)` |
| `θ` | `ALPHA` `3` |
| `²` (inside strings, e.g. `M/S²`) | `x²` |
| `≤ ≥ ≠ =` and `and or not(` | `2nd` `TEST` (and its LOGIC tab) |
| `Str8`, `Str9` | `VARS` `7:String` |
| `If Then Else End Repeat Pause Lbl Goto Menu( Stop` | `PRGM` CTL tab |
| `Input Disp Output( ClrHome` | `PRGM` I/O tab |
| `toString(` (CE only) | `PRGM` I/O tab, or `2nd` `CATALOG` |
| `round( abs( int( fPart( max( min(` | `MATH` NUM tab |
| `length( sub( expr(` | `2nd` `CATALOG` |
| `Degree Radian Float Normal Full` | `MODE` screen while editing, or `2nd` `CATALOG` |
| `"` / `:` / `?` / space | `ALPHA` `+` / `ALPHA` `.` / `ALPHA` `(-)` / `ALPHA` `0` |

The mono program's line 6 stores a formula **inside a string**
(`"2+(X<0)+int(log(max(1,abs(X))))-(0<abs(X) and abs(X)<1)+…"→Str9`).
Type the functions inside the quotes with their keys, not as separate
letters: `int(` from MATH NUM, `log(` from the LOG key, `and` from `2nd`
`TEST` LOGIC, and so on. The `!` in a few messages is `MATH` PRB `4`. It is the rule that places each unit right after
its number. In the listing, `Pause ` is followed by a space. That space is
part of the command, so you don't type it.

## Sign conventions and checks (from the study guide)

* Elevators and hanging masses: **up is positive**, N − mg = maᵧ.
* Speeding up means a is along v. Slowing down means a is opposite v.
* Atwood: heavier side down / lighter side up is positive. The check is
  m_light·g < T < m_heavy·g.
* Table + hanger: table toward the pulley and hanger down are positive.
* Level floor: +x is the pull direction, aᵧ = 0, N = mg − F sin θ.
* Incline: +x is uphill when at rest and downhill when sliding.
  Components: mg sin θ downhill, mg cos θ into the slope.

## How it was built and checked

* `tools/forces.tpl` is the single source for both programs. `tools/build.py`
  expands it per calculator (screen layout and wording), then **lints** it:
  * one command per line;
  * every `Goto`, `Lbl` and `Menu(` at top level and never inside an
    If-Then/For/While/Repeat block, so nothing jumps out of a block;
  * no conditional `Goto`;
  * `Menu(` has at most 7 options, with title and option widths checked;
  * every `Disp`/`Output(` line fits the screen. On the mono version, text
    that lands on row 1 (an `Output(` to row 1, or the first `Disp` after
    `ClrHome`) is kept to 15 columns, clear of the pause indicator;
  * strings are uppercase only, using only keypad characters;
  * only A–Z, θ and Str1–Str9 are used, with no lists or matrices.

  It then tokenizes each program with **tivars_lib_py** (`pip install
  tivars`), reloads the `.8xp`, and confirms it detokenizes to exactly
  `FORCES.txt`. It also audits every token: no command was mis-typed into
  lowercase letters, and the mono file uses no CE-only token.
* `tools/tisim.py` is a TI-BASIC interpreter for this program. It uses TI's
  14-digit decimal math and 10-digit Float display, degree trig, and the
  16×8 and 26×10 home screens. It reports a memory leak whenever a
  `Goto`/`Menu(` runs inside a block. It also reports any text that scrolls
  away, gets cleared or is hidden by a menu before you could read it, any
  text past the screen edge, and anything under the mono pause indicator.
* `tools/test_program.py` runs the real `.8xp` files through it. It runs:
  * the 12 required cases on both calculators, with both mono number styles
    (`.5` and `0.5`);
  * every error and impossible-setup path;
  * wrong inputs, checking that each one is refused and asked again;
  * blank ENTER handled both ways a calculator might treat it;
  * mode restore, the g settings, and a 30-problem session (no leaks);
  * random problems for every solver. Every answer row on every screen is
    compared with `reference.py`.

  It finishes by confirming **every line of both programs ran at least
  once**.
* The finished program was also reviewed by independent agents (physics,
  real-hardware TI-BASIC, spec compliance, hand traces of all 12 cases,
  simulator fidelity), and their confirmed findings were fixed.
* Rebuild and re-test: `pip install tivars`, then
  `python3 tools/build.py && python3 reference.py && python3 tools/test_program.py`.

On the TI-84 Plus a value next to a long label (MGSINθ, MGCOSθ, OTHER,
HEAVY, LIGHT) is rounded to a whole number when it would push its unit off
the 16-column row. For example, 1733.055 is shown as `MGCOSθ=1733 N`. This
only happens for values of 1000 or more.

The unit placement assumes the TI-84 Plus prints numbers below 1 without a
leading zero (`.5`), as TI's guidebook shows. If your OS prints `0.5`, the
unit just sits right against the number (`0.5M/S²`); the tests cover both.

The programs have been verified in this simulator and against TI's
documentation, not yet on a physical calculator. If anything looks off on
your calculator (for example a unit one space away from its number), the
math is unaffected. Please note which screen it was.
