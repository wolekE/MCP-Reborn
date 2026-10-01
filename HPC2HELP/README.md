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

* Reference topics are short pages (title shows `page/total`); press **ENTER** for the next page.
  After the last page you go back to that section's menu.
* Every section menu has **MAIN MENU**; every tool ends with a menu to run it again,
  go back to its section, or go to the main menu. You never have to quit to switch topics.
* Absolute value is written `ABS(...)` on screen because the TI-84 keypad has no `|` character:
  `ABS(F(X))` means |f(x)| and `F(ABS(X))` means f(|x|).
* `DF`, `DG`, `RF`, `DH` mean D<sub>f</sub>, D<sub>g</sub>, R<sub>f</sub>, D<sub>h</sub>. `INF` means ∞.
* The program switches the calculator to **Float** and **Normal** mode when it starts so
  numbers and fractions display cleanly (this is the default mode anyway).

_Transfer instructions, manual-entry guide and test checklist: being finalized after the review pass._
