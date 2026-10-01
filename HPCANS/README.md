# HPCANS: quiz answer helper for the TI-84 Plus CE

## 1. Put it on the calculator

1. Install **TI Connect CE** on the computer, plug in the calculator, and open **Calculator Explorer**.
2. Open the folder **`TRANSFER`**. Select **all** the `.8xp` files in it; HPCANS needs every one.
3. Drag them onto the calculator. Send them to **RAM**, not Archive. Afterwards, no name in the
   calculator's `prgm` list should have a `*` in front of it (a `*` means Archive).

HPCANS needs about **85 KB** of free RAM (the programs are about 76 KB; the rest is working space). If the calculator says ERR:MEMORY, delete or archive other
programs first. Keep the `TRANSFER` folder: a RAM reset erases the programs.
Do not paste the `.txt` files into the Program Editor; that gives "Bad token!".

## 2. Start it

Press `prgm`. HPCANS is at the bottom of the list, after its helpers, which all start with `HA`. Press
`▲` once to jump there, then press `ENTER`, `ENTER`, and `ENTER` again at PRESS ENTER. Run only HPCANS.

* Next time, on the home screen, just press `ENTER`; it runs `prgmHPCANS` again.
* An `ERR:` screen means a typo was typed. Choose **1:Quit** (never 2:Goto), then press `ENTER` to
  start again.
* To stop at any time, press `ON`, then 1:Quit.

## 3. Pick what the problem LOOKS like

```
WHAT DOES IT LOOK LIKE?
1:F+G  F-G  FG  F/G
2:F(G(X))  OR √(G(X))
3:F⁻¹(X)  INVERSE
4:A*F(BX+C)+K SHIFT/FLIP
5:ABS BARS |F(X)| F(|X|)
6:KX^P  POWER/ROOTS
7:DECOMPOSE H(X)
```

Then press the number for **WHAT DO THEY WANT?**, type the numbers you see on the paper, and copy
the lines under **ANSWER:**.

* On menus, just press the number; no `ENTER` is needed.
* `CLEAR` goes back one menu (on the main menu it quits). While you type a number, CLEAR only erases
  the line, so finish that screen first.
* An empty `ENTER` means a missing number in front: `X`, `F` or `√` counts as 1, and a missing plain
  `+ number` counts as 0.
* A missing `X` or `X²` term is typed as `0`. For example, 2X²-1 has no X term, so type 0 for it.
* At `ENTER=MORE`, press `ENTER` for the rest of the answer. `CLEAR` skips to the menu at the bottom.

## 4. Typing numbers

* **Negative numbers:** use the gray **`(-)`** key at the bottom row, left of `ENTER`. A lone `(-)` means
  -1: for `-F(X)` or `√(5-X)`, type `(-)` as the number in front.
* **Fractions:** type `2/3` with the `÷` key. Answers are always exact, like `-17/4`, never `-4.25`.
* **Infinity** (for domains and ranges): type the letter `I`, which is `ALPHA` then `x²`.
  `(-)` `I` is negative infinity.
* **X** (in INVERSE and DECOMPOSE, where you type whole expressions): use the `X,T,θ,n` key. Type X² with
  `x²` and X³ as `X^3`. If `^` moves the cursor into a small raised box, press `▶` before typing the rest.
