# MOLES and FORMBKEY for the TI-84 Plus / TI-84 Plus CE

| File | What it is |
|---|---|
| `MOLES.8xp` | Mole-unit solver. Send it to the calculator. |
| `MOLES.txt` | Its TI-BASIC source, written in token names (the same text you see in the program editor). |
| `FORMBKEY.8xp` | Unit IV Test, Form B answer key with the factor-label work for Part II. |
| `FORMBKEY.txt` | Its source. |
| `tools/` | Build script (tivars_lib_py), TI-BASIC simulator, and an independent Python answer checker. |
| `tests/run_sessions.py` | Scripted calculator sessions that check every feature on both screen sizes. |

The same `.8xp` file works on the TI-84 Plus (black and white) and the TI-84 Plus CE. Neither program uses commands that only exist on the CE.

## Sending the programs to the calculator

1. Install **TI Connect CE** (free from education.ti.com). It talks to both the TI-84 Plus and the TI-84 Plus CE.
2. Connect the calculator with its USB cable and turn it on.
3. Drag `MOLES.8xp` and `FORMBKEY.8xp` into the *Calculator Explorer* window, or use *Actions → Send to Calculators*. Choose **RAM** as the destination.
4. On the calculator press `prgm`, pick `MOLES`, and press `enter`.

**Keep the name `MOLES`.** The program runs copies of itself for its shared routines (wrapping text, formatting numbers, reading formulas), so a renamed copy will fail with `ERR:UNDEFINED`.

## Using MOLES

The main menu has six features and QUIT. Each result screen shows:

* the factor-label setup as text lines, e.g. `5.0 g Na x (1 mol / 22.99 g) x (6.022ᴇ23 / 1 mol)`,
* `UNROUNDED:` followed by the full calculator answer,
* a sig-fig prompt, then `ANSWER:` rounded to that many significant figures.

Press `enter` at `MORE: [ENTER]` for the next screen. After every problem, `[ENTER]=MENU` takes you back to the main menu.

### Typing formulas

* **Element symbols**: lowercase is optional. `Al2(SO4)3` and `AL2(SO4)3` both work. If a pair of capitals could mean two things (`CO` = cobalt or carbon + oxygen; also `CS NI NB PB SI SC SN SB IN`), the program asks: press `1` for the two-letter element or `2` for two separate elements. Typing the second letter in lowercase (if your calculator has lowercase enabled) skips the question.
* **Subscripts**: just type the digits: `C6H12O6`.
* **Parentheses**: `Ca3(PO4)2`, `Sn(C2H3O2)2`. Nested parentheses work too.
* **Hydrates**: use `*` (the × key) or `.` for the dot: `CaSO4*2H2O`, `CuSO4*5H2O`.
* **Scientific notation**: use the `EE` key (`2nd` `,`): `6.022ᴇ23`. The answer shows the number exactly as you typed it.
* **Sig figs**: the program counts the significant figures in the number you typed and offers that as the default. Press `enter` (or type `0`) to accept it, or type another number from 1 to 9. Trailing zeros without a decimal point (e.g. `550`) are treated as not significant.

### Features

1. **MOLAR MASS**: `count x atomic mass = subtotal` for each element, then the total in g/mol.
2. **CONVERSIONS**: g→mol, mol→g, mol→particles, particles→mol, g→particles, particles→g, and g→atoms/ions of one element in the compound. The last one asks which element and multiplies by its total count, so Al in Al2(SO4)3 counts 2 and O counts 12.
3. **PERCENT COMP**: percent by mass of every element, or percent water in a hydrate (the formula must contain `*`).
4. **EMPIRICAL FORM**: choose percents or grams, then enter 1–4 symbols and amounts. The work shows moles, division by the smallest, every ratio, and any ×2…×5 trial. A ratio counts as whole if it is within 0.1 of a whole number. You can then enter a molar mass to get n and the molecular formula, or press `enter` to skip.
5. **HYDRATE (HEAT)**: mass before heating, mass after, and the anhydrous formula. The work shows water lost, moles of each, the ratio, and the final formula, e.g. `CaSO4*2H2O`.
6. **SAME # MOLES**: grams or particles of substance A → moles → grams or particles of substance B.

### Numbers the program uses

* **Avogadro's number**: 6.022ᴇ23.
* **Atomic masses** (4 significant figures, H = 1.008), stored in the list `ʟAMASS` with the symbols in `Str0`, for elements 1–56 plus Au, Hg and Pb:
  H 1.008, He 4.003, Li 6.941, Be 9.012, B 10.81, C 12.01, N 14.01, O 16.00, F 19.00, Ne 20.18, Na 22.99, Mg 24.31, Al 26.98, Si 28.09, P 30.97, S 32.07, Cl 35.45, Ar 39.95, K 39.10, Ca 40.08, Sc 44.96, Ti 47.87, V 50.94, Cr 52.00, Mn 54.94, Fe 55.85, Co 58.93, Ni 58.69, Cu 63.55, Zn 65.38, Ga 69.72, Ge 72.63, As 74.92, Se 78.97, Br 79.90, Kr 83.80, Rb 85.47, Sr 87.62, Y 88.91, Zr 91.22, Nb 92.91, Mo 95.95, Tc (98), Ru 101.1, Rh 102.9, Pd 106.4, Ag 107.9, Cd 112.4, In 114.8, Sn 118.7, Sb 121.8, Te 127.6, I 126.9, Xe 131.3, Cs 132.9, Ba 137.3, Au 197.0, Hg 200.6, Pb 207.2.
* **Molar masses** in conversions, percent composition, hydrates and same-moles problems are rounded to 0.01 g/mol before use, as in the answer key (H2O = 18.02, CO2 = 44.01). Feature 1 shows the unrounded sum as well.
* **Tin** is 118.7 at 4 significant figures, so tin(II) acetate comes out to 236.79 g/mol. The printed key uses 118.71 and gets 236.80; both round to 1.15ᴇ3 g for 4.87 mol.

### Things MOLES changes on your calculator

* It sets the modes `Float`, `Normal` and `Full`.
* It overwrites the real variables A–Z and θ and the strings Str0–Str9.
* It creates the list `ʟAMASS`, which stays after you quit, plus scratch lists `ʟMRE ʟMRC ʟMSTK ʟMEL ʟMCT`, which QUIT deletes.
* The screen size (16×8 on the TI-84 Plus, 26×10 on the CE) is detected from the graph window's pixel count. The window settings themselves are not changed.

## Using FORMBKEY

`PART I (MC)` lists the seven answers and then explains each one. `PART II WORK` has a menu for problems 1–6, each with its factor-label setup and final answer. The pages are 16 characters wide, so they read the same on both calculators.

## Rebuilding and testing

```
pip install tivars
python3 tools/make_formbkey.py      # regenerate FORMBKEY.txt from the key text
python3 tools/build.py              # tokenize, lint, write MOLES.8xp and FORMBKEY.8xp
python3 -I tests/run_sessions.py    # scripted sessions on 16x8 and 26x10 screens
python3 -I tools/oracle.py all      # independent Python answers for the test cases
```

`build.py` refuses to build if any of these turn up:

* a token that needs an OS newer than TI-84 Plus 2.43,
* a `→` inside a string (on the calculator it ends the string),
* a `Goto` or `Menu(` to a missing label,
* an unbalanced `If`/`Then`/`End` block,
* a `Disp` or `Pause` text wider than 16 characters,
* a source line that doesn't decode back to the same text.
