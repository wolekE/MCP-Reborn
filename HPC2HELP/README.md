# HPC2HELP — TI-84 study helper for HPC Unit 1 · Topic 2

A single TI-BASIC program for the **TI-84 Plus / TI-84 Plus Silver Edition / TI-84 Plus CE**:
reference pages for every Topic 2 method (operations & domain, composition, decomposition,
inverses, transformations, absolute value, power functions, top mistakes) plus three
numeric tools (transform a point, transform a domain/range, power-function classifier).

| File | What it is |
|---|---|
| `HPC2HELP.8xp` | The program, ready to send to the calculator (built and verified, see below). |
| `HPC2HELP.txt` | Complete TI-BASIC source, one statement per line, written with the calculator's token names. |
| `SCREENS.txt` | Every menu and page exactly as it appears on a 16 × 8 TI-84 Plus screen. |
| `tools/` | The build, verification and simulation scripts used to check the program. |

## Menu map

```
MAIN: U1 TOPIC 2 HELP
 1 DOMAIN/COMP     OPS + DOMAIN, OPS MISTAKES, COMPOSITION, COMP DOMAIN,
                   COMP MISTAKES, COMP CHECK, MAIN MENU
 2 DECOMP/INVERSE  DECOMP RULES, DECOMP EXAMPLE, INVERSE BASICS, FIND INVERSE,
                   VERIFY INVERSE, BY FUNC TYPE, MAIN MENU
 3 TRANSFORM       OUTSIDE (Y), INSIDE (X), FACTOR + ORDER, MAP + D/R,
                   POINT TOOL, D/R TOOL, MAIN MENU
 4 ABS VALUE       ABS(F(X)) ON Y, F(ABS(X)) ON X, MNEMONIC, COMBINATIONS, MAIN MENU
 5 POWER FUNCS     DEFINITIONS, QI SHAPES, SYMMETRY, K<0 + REWRITE, MISTAKES,
                   CLASSIFIER, MAIN MENU
 6 TOP MISTAKES    READ ALL 12, 1-5 TRANSFORMS, 6-9 DOMAIN/INV, 10-12 POWER, MAIN MENU
 7 EXIT
```

* Reference topics are short pages (the title shows `page/total`); press **ENTER** for the next
  page. After the last page you go back to that section's menu.
* Every section menu has **MAIN MENU**; every tool ends with a menu to run it again,
  go back to its section, or go to the main menu. You never have to quit to switch topics.
* Absolute value is written `ABS(...)` on screen because the TI-84 keypad has no `|` character:
  `ABS(F(X))` means |f(x)| and `F(ABS(X))` means f(|x|).
* `DF`, `DG`, `RF`, `DH` mean D<sub>f</sub>, D<sub>g</sub>, R<sub>f</sub>, D<sub>h</sub>. `INF` means ∞.
* The program sets the calculator to **Float** and **Normal** mode when it starts so numbers and
  fractions display cleanly (these are the calculator's default modes).
* In the tools, type negative numbers with the **(−)** key and fractions with **÷**, e.g. `(−)4÷3`.
  Always type a number before pressing ENTER at an input prompt.

## Put it on your calculator with TI Connect CE

You need the free **TI Connect™ CE** software (education.ti.com) and the USB
calculator-to-computer cable. TI Connect CE works with both the TI-84 Plus and the TI-84 Plus CE.

1. **Connect.** Plug the cable into the computer and the calculator, then turn the calculator on
   (home screen).
2. **Open Calculator Explorer.** Start TI Connect CE and click the **Calculator Explorer**
   workspace (the calculator icon on the left edge). Your calculator should appear under
   *Connected Calculators*, with its files listed.
3. **Transfer the program.** Drag `HPC2HELP.8xp` from your file browser onto the calculator's file
   list (or use the *Actions* menu → add/send files from the computer and pick `HPC2HELP.8xp`;
   menu wording varies a little between versions). In the *Send to Calculators* window choose
   **RAM** as the location if it asks, then click **Send**.
4. **Check memory if the transfer fails.** The program is about **14.7 KB**. A TI-84 Plus has about
   24 KB of user RAM, so if it says there isn't enough memory, archive (don't delete) other
   programs: `2nd` `MEM` → `2:Mem Mgmt/Del` shows free RAM. A TI-84 Plus CE has plenty of room.
5. **Run it.** On the calculator press `PRGM`, stay on the **EXEC** tab, choose **HPC2HELP**
   (arrow to it or press its number), press `ENTER` to paste `prgmHPC2HELP` on the home screen,
   and press `ENTER` again.

If the PRGM list shows a `*` next to HPC2HELP, it went to Archive. Move it to RAM before running:
`2nd` `MEM` → `6:UnArchive` → `PRGM` → choose **HPC2HELP** → `ENTER` → `ENTER`.

## If you have to type it in by hand

The `.8xp` file is the easy way. Typing the source in by hand works, but it is about 1,070 lines
(613 of them `Disp` lines), so expect several hours.

1. `PRGM` → **NEW** → `1:Create New`, type the name `HPC2HELP` (alpha-lock is already on), `ENTER`.
2. Type each line of `HPC2HELP.txt` and press `ENTER` at the end of each line; the calculator adds the `:`.
   Do not type the line numbers some viewers show.
3. **Commands must come from the menus, never spelled with letters.** `Disp` typed as D-I-S-P will not work.
4. Text **inside quotes** is typed with `ALPHA` letters and keys. For example, the on-screen text
   `ABS(F(X))` is just the letters A, B, S and parentheses, not the `abs(` command.
5. `2nd` `QUIT` saves and leaves the editor. Run it as above.

| In the source | Keys (TI-84 Plus and CE) |
|---|---|
| `Float` / `Normal` | `MODE`, move to FLOAT (or NORMAL), `ENTER`: pastes the word into the program |
| `Lbl` `Goto` `Menu(` | `PRGM` → CTL → `9` / `0` / `C` |
| `If` `Then` `Else` `End` | `PRGM` → CTL → `1` / `2` / `3` / `7` |
| `Pause` `Stop` | `PRGM` → CTL → `8` / `F` |
| `Input` `Disp` `Output(` `ClrHome` | `PRGM` → I/O → `1` / `3` / `6` / `8` |
| `►Frac` | `MATH` → MATH → `1` |
| `abs(` `fPart(` `min(` `max(` `gcd(` | `MATH` → NUM → `1` / `4` / `6` / `7` / `9` |
| `=` `≠` `>` `≥` `<` `≤` | `2nd` `TEST` → `1`…`6` (also used inside quotes) |
| `and` `or` `xor` `not(` | `2nd` `TEST` → LOGIC → `1` / `2` / `3` / `4` |
| `→` | `STO►` |
| `⁻` (a negative, e.g. `⁻A→A`) | `(−)` key |
| `-` inside quotes | the `−` (subtract) key |
| `"` | `ALPHA` `+` |
| space | `ALPHA` `0` |
| `?` | `ALPHA` `(−)` |
| `²` `⁻¹` `^` | `x²` / `x⁻¹` / `^` |
| `√(` | `2nd` `x²` |
| `³` `³√(` | `MATH` → MATH → `3` / `4` |
| `[` `]` | `2nd` `×` / `2nd` `−` |

If you would rather type on a computer, a text-to-.8xp converter such as Cemetech's SourceCoder can
also turn `HPC2HELP.txt` into a `.8xp`. You don't need one, though; `HPC2HELP.8xp` is already built.

## Test checklist

Run the program, then try these. Menu numbers are the keys to press.

| Test | Keys and inputs | You should see |
|---|---|---|
| Transform point | `3` TRANSFORM → `5` POINT TOOL → `ENTER`; A=`2`, B=`(−)4÷3`, H=`3`, K=`(−)3`, OLD X=`(−)4`, OLD Y=`2` | `NEW POINT`, `X=X/B+H` **6**, `Y=A*Y+K` **1**, so the new point is (6, 1). Then menu: NEXT POINT / NEW A,B,H,K / TRANSFORM MENU / MAIN MENU |
| Transform D/R | `3` → `6` D/R TOOL → `ENTER`; A=`2`, B=`(−)4÷3`, H=`3`, K=`(−)3`; DOMAIN LOW=`(−)4`, HIGH=`8`; RANGE LOW=`(−)2`, HIGH=`4` | Page 1: `NEW DOMAIN` LOW END **−3**, HIGH END **6**, `B<0 ENDS SWAPPED`. Page 2: `NEW RANGE` LOW END **−7**, HIGH END **5**. So D = [−3, 6], R = [−7, 5]. |
| Fractional power, odd/odd | `5` POWER FUNCS → `6` CLASSIFIER → `ENTER`; K=`1`, TOP A=`3`, BOTTOM B=`7` | `P=3/7`, `A IS ODD`, `B IS ODD`, `0<P<1  POSITIVE`, `ODD SYMMETRY`, `IN QI AND QIII`; page 2 ALL REALS / ALL REALS; page 3 INCREASING, CURVES DOWN |
| Fractional power, even/odd | K=`1`, A=`4`, B=`7` | `A IS EVEN`, `EVEN SYMMETRY`, `IN QI AND QII`; range `[0,INF)` |
| Positive power > 1, even root | K=`1`, A=`3`, B=`2` | `B IS EVEN`, `P>1  POSITIVE`, `UNDEFINED X<0`, `IN QI ONLY`; domain `[0,INF)`; CURVES UP |
| k < 0 | K=`(−)1`, A=`4`, B=`7` | `EVEN SYMMETRY`, `K<0 FLIP X-AXIS`, `IN QIII AND QIV`; range `(-INF,0]`; page 3 `QIV PIECE (K<0)`, DECREASING |
| Negative power | K=`1`, A=`(−)2`, B=`1` | `P=−2/1`, `A IS EVEN`, `P<0  NEGATIVE`, `EVEN SYMMETRY`, `IN QI AND QII`; page 2 `ALL REALS, X≠0`, `(0,INF)`, `X=0 EXCLUDED`, `ASYMPTOTES` `X=0 AND Y=0`, `NOT CONT AT X=0` |
| Not in lowest terms | K=`1`, A=`2`, B=`4` | `P=1/2`, `B IS EVEN`, `(P WAS REDUCED)` |
| Bad B = 0 (classifier) | K=`1`, A=`2`, B=`0` | `ERROR` / `B CANNOT BE 0.`, then ENTER returns to the POWER FUNCS menu |
| Bad B = 0 (tools) | POINT TOOL with B=`0` | Menu titled `B CANNOT BE 0`: RE-ENTER / TRANSFORM MENU / MAIN MENU |
| Navigation | Open each main-menu item, read one topic, choose MAIN MENU; finally `7` EXIT | Every topic returns to its section menu; EXIT ends the program |

## How it was checked

All three scripts are in `tools/` and need Python 3. `build_8xp.py` and `verify_8xp.py` also need
the `tivars` package (`pip install tivars`, from TI-Toolkit's tivars_lib_py).

* `python tools/build_8xp.py` tokenizes `HPC2HELP.txt` and writes `HPC2HELP.8xp`. Quoted text is
  tokenized one keypad character at a time, and every line must decode back exactly as written.
* `python tools/verify_8xp.py` re-reads the `.8xp` byte by byte, without tivars: signature,
  TI-84 Plus header, lengths, name, RAM flag, checksum, and that only TI-83 Plus-era tokens are used.
  It then detokenizes the file and checks it against the source line by line.
* `python tools/check_tibasic.py` is a static checker plus a 16 × 8 home-screen simulator:
  * every statement parses; labels are unique and all used; every jump target exists
  * Menu( limits are respected; no jumps out of If-Then blocks; no unreachable lines; no
    non-interactive loops
  * it walks every option of every menu, and checks every page for scrolling, wrapping and the
    busy-indicator cell
  * it runs the sample validations, tests the classifier on 2,304 (k, a, b) inputs against an
    independent numeric oracle, and runs 800 random transform-tool trials against exact fractions
  * every one of the 1,069 lines executes in at least one test, and it writes `SCREENS.txt`

These checks use a simulator, not a physical calculator, so run through the checklist above once
on your own calculator too.
