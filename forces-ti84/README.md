# FORCES: Newton's laws solver for the TI-84 Plus and TI-84 Plus CE

FORCES is a plain TI-BASIC program (no assembly, no shell) that works every
problem type on the *Equilibrium & non-equilibrium* quiz prep: elevators and
apparent weight, Atwood machines, table + hanging mass, pulls on a level
floor, inclines, Newton's third law, and quick concept checks. Every result
screen shows the setup as well as the numbers:

1. the positive direction (`+ = UP`, `+=TOWARD PULLEY`, `+X=DOWNHILL`, …)
2. the force equation (`N-MG=MA`, `M1G-T=M1A`, `FCOSθ-FRIC=MA`, …)
3. the answers, rounded with `round(X,3)`, with units (`N=678 N`, `AY=⁻2 M/S²`)
4. the direction in words (`ACCEL: UP`, `HANGER: DOWN`, `TABLE: TO PULLEY`)

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
4. **TI-84 Plus:** the program must sit in RAM to run. If you archived it,
   press `2nd` `MEM` `2:Mem Mgmt/Del` `7:Prgm`, select FORCES and press
   `ENTER` to clear the `*`. A CE on OS 5.3+ can run it straight from Archive.
   The mono program is about 13.7 KB of the TI-84 Plus's ~24 KB of RAM.
5. Run it: `PRGM`, pick `FORCES`, press `ENTER` twice.

### Before you run it

* **Negative numbers:** type them with the `(-)` key, not the minus key
  (minus at the start of an entry means "Ans minus …").
* **Variables:** FORCES stores into A–Z, θ and Str1–Str9 (your old values there
  are overwritten). It never touches lists (L1–L6 or named lists) or matrices.
* **g is kept in G** and remembered between runs. It is checked at start: if G
  is not 9.8, 9.81 or 10, it is reset to 9.8. When it is 9.81 or 10, a NOTE
  screen reminds you on start-up.
* **Modes:** FORCES sets Degree, Float, Normal and Full. On QUIT it restores
  your previous angle mode (Degree/Radian). It does not restore Float/Normal.
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
| FIND SCALE N | mass M (kg), size of a (m/s², no sign); then the **acceleration direction** UP / DOWN / ZERO, or **FROM MOTION >** to pick MOVING UP / MOVING DOWN / AT REST and then SPEEDING UP / SLOWING DOWN / CONSTANT V | `N-MG=MA`, the reason for the direction (e.g. `A OPPOSITE TO V`), aᵧ with sign, N = m(g + aᵧ), true weight mg, `ACCEL: UP/DOWN/NONE`, and `HEAVIER (N>MG)` / `LIGHTER (N<MG)` / `NORMAL (N=MG)` / `WEIGHTLESS (N=0)`. If aᵧ < −g: `N<0: LIFTS OFF`, the scale reads 0. |
| ACCEL FROM N [FIND ACCEL FROM SCALE] | mass M, scale reading N (≥ 0); after the first screen, the **velocity direction** UP / DOWN / UNKNOWN | aᵧ = (N − mg)/m with sign and direction, mg; then `SPEEDING UP` or `SLOWING DOWN`. If UNKNOWN it lists both possibilities (`DOWN+SPEEDING OR UP+SLOWING`). If a = 0: constant velocity or at rest. |
| FREE FALL | nothing | N = 0, aᵧ = −g, `ACCEL: DOWN`, `WEIGHTLESS`. |
| FIND MASS | scale reading N (> 0), signed aᵧ | m = N/(g + aᵧ), mg. If aᵧ ≤ −g: `IMPOSSIBLE`. |

### 2 ATWOOD (2 HANG) — heavy side down is positive

| Option | Asks for | Shows |
|--------|----------|-------|
| FIND A AND T | M1, M2 (kg) | The heavier mass is picked automatically. Both equations (e.g. `M1G-T=M1A`, `T-M2G=M2A`), a = (M−m)g/(M+m), T = m(g+a), which mass goes DOWN and which goes UP, then a check screen with M1G, M2G, T and `M2G<T<M1G: OK`. Equal masses: a = 0, T = mg, `EQUILIBRIUM`. |
| FIND 2ND MASS [FIND OTHER MASS FROM A] | a (m/s²), known mass (kg), then whether the known mass is the HEAVIER (DOWN) or LIGHTER (UP) one | The other mass (light = heavy·(g−a)/(g+a) or heavy = light·(g+a)/(g−a)), T, both masses. If a ≥ g: `IMPOSSIBLE`. |

### 3 TABLE + HANGER — toward the pulley / down is positive

Asks for the table mass, the hanging mass, μk (0 = frictionless), then, only if
μk > 0, μs (ENTER alone or 0 = use μk; μs must be ≥ μk).

* **Moves** (frictionless, or mg > μs·Mg): `HANG: MG-T=MA`,
  `TABLE: T=MA` or `TABLE: T-FK=MA`, a = (mg − μk·Mg)/(M + m), T = m(g − a),
  `HANGER: DOWN`, `TABLE: TO PULLEY`, then N on the table = Mg and
  fk = μk·N.
* **Stays put** (mg ≤ μs·Mg): `BLOCK STAYS PUT`, a = 0, T = mg, static
  friction fs = mg (pointing away from the pulley), fs max = μs·N.

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
friction, aₓ and its direction. Special messages: `N<0: LIFTS OFF`; friction
< 0 means `NOT POSSIBLE`; friction > Fx means `IF AT REST, THE BLOCK STAYS PUT;
IF MOVING, IT SLOWS DOWN`.

### 5 INCLINE (submenu) — each asks for m and the slope angle θ (0 ≤ θ < 90)

Every option shows the components mg sin θ (downhill) and mg cos θ (into the
slope).

| Option | Extra input | Shows |
|--------|-------------|-------|
| AT REST | μs (ENTER alone or 0 = skip the check) | `+X=UPHILL`, `FS-MGSINθ=0`, `N-MGCOSθ=0`, N = mg cos θ, fs = mg sin θ (`FS POINTS UPHILL`); with μs: fs max = μs·N and `YES: STAYS PUT` or `NO: WILL SLIDE`; always the minimum μs = tan θ |
| SLIDING W/ MUK [SLIDING DOWN WITH MUK] | μk | `+X=DOWNHILL`, `MGSINθ-FK=MA`, a = g(sin θ − μk cos θ), fk = μk·N uphill. If a < 0 it says it slows down (and would not start sliding from rest). |
| FRICTIONLESS | — | a = g sin θ downhill, N |
| MIN MUS (HOLD) [MIN MUS TO HOLD AT REST] | — (m is asked only for the components) | μs min = tan θ (mass cancels) |

### 6 3RD LAW — + is the direction of the force on B

Asks for mA, mB and F (ENTER alone or 0 = just the ratio). Shows
`FAB=-FBA` (equal and opposite), aB = F/mB, aA = −F/mA, and the size ratio
aA/aB = mB/mA, then a reminder screen: N and mg are not a third-law pair; the
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
* **CONCEPT CHECK**: pick MOVING UP / DOWN / RIGHT / LEFT, AT REST, or
  V=0 1 INSTANT, then SPEEDING UP / SLOWING DOWN / CONSTANT V. Shows the
  acceleration direction, net force direction and whether it is in
  equilibrium. `V=0 1 INSTANT`: equilibrium is **not** guaranteed (top of a
  toss: a = g down).
* **SETTINGS (G)**: shows the current g, then pick 9.8, 9.81 or 10 (or KEEP).
* **QUIT**: restores your angle mode and ends the program.

Every result screen ends with a pause: press `ENTER` for the next screen.
After the last one you are back at the main menu.

## Cheat sheet: which menu answers which question

```
QUESTION                                   MENU PATH
Scale reading in an elevator (a given)     ELEVATOR > FIND SCALE N > m, a > UP/DOWN
...from "moving down, slowing" etc.        ELEVATOR > FIND SCALE N > m, a > FROM MOTION
Acceleration from a scale reading          ELEVATOR > ACCEL FROM N > m, N > V dir
Speeding up or slowing down?               ELEVATOR > ACCEL FROM N (pick V dir)
Free fall / weightless                     ELEVATOR > FREE FALL
Mass from scale reading + a                ELEVATOR > FIND MASS
Atwood: a, T, who goes up                  ATWOOD > FIND A AND T
Atwood: find a mass from a                 ATWOOD > FIND 2ND MASS
Table block + hanging mass (a, T, stuck?)  TABLE + HANGER
Pull/push at an angle on a level floor     FLAT SURF PULL > (friction / MUK / CONST V / AX)
Friction & N for constant velocity         FLAT SURF PULL > CONSTANT V
Block resting on a slope (N, fs, slips?)   INCLINE > AT REST
Sliding down a slope with friction         INCLINE > SLIDING W/ MUK
Frictionless slope                         INCLINE > FRICTIONLESS
Minimum mus to hold on a slope             INCLINE > MIN MUS (HOLD)
Collision / push forces and accelerations  3RD LAW
Rope tension, hanging at rest              MORE > SIMPLE CASES > HANGING, REST
Terminal velocity (air resistance)         MORE > SIMPLE CASES > TERMINAL VEL.
Tension, mass accelerating on a rope       MORE > SIMPLE CASES > HANG + ACCEL
Any 1-D problem: add forces, get a         MORE > SIMPLE CASES > SUM F=MA
"Which way is a / net F? Equilibrium?"     MORE > CONCEPT CHECK
Teacher uses g = 10 (or 9.81)              MORE > SETTINGS (G)
```

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

The mono program's line 6 stores a formula **inside a string**
(`"2+(X<0)+int(log(max(1,abs(X))))+…"→Str9`). Type the functions inside the
quotes with their keys (`int(` from MATH NUM, `log(` from the LOG key, etc.),
not as separate letters. It is the rule that places each unit right after
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
  * every `Disp`/`Output(` line fits the screen, with row 1 kept to 15
    columns on the mono version;
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
* `tools/test_program.py` runs the real `.8xp` files through it. It runs the
  12 required cases on both calculators (and both mono number styles, `.5`
  and `0.5`), every error and impossible-setup path, wrong-input re-prompts,
  blank-ENTER behavior both ways, mode restore, g settings, a 30-problem
  session (no leaks), and random problems compared with `reference.py`. It
  finishes by confirming **every line of both programs ran at least once**.
* Rebuild and re-test: `pip install tivars`, then
  `python3 tools/build.py && python3 reference.py && python3 tools/test_program.py`.

The programs have been verified in this simulator and against TI's
documentation, not yet on a physical calculator. If anything looks off on
your calculator (for example a unit one space away from its number), the
math is unaffected. Please note which screen it was.
