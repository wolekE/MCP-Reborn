"""Generate FORMBKEY.txt (TI-BASIC token names) from the Form B answer key text.

Pages are pre-wrapped to 16 columns x 7 lines so the same program reads well on the
TI-84 Plus (16x8 home screen) and the TI-84 Plus CE (26x10).
"""

import pathlib
import textwrap

ROOT = pathlib.Path(__file__).resolve().parent.parent
WIDTH, LINES = 16, 7

PART1 = [
    "PART I ANSWERS",
    "1:D  2:D  3:C",
    "4:C  5:B  6:C",
    "7:D",
    "",
    "1 D: DIVIDE THE SUBSCRIPTS BY 2. P4O10 BECOMES P2O5.",
    "2 D: CH2 = 14.03 g/mol. 70 / 14.03 = 5, SO C5H10.",
    "3 C: NO = 14.01 + 16.00 = 30. (N2O2 = 60 IS NOT A CHOICE.)",
    "4 C: 8 H PER MOLECULE x 4 MOLECULES = 32 ATOMS. NO AVOGADRO FACTOR: MOLECULES, NOT MOLES.",
    "5 B: AVOGADROS NUMBER = PARTICLES IN ONE MOLE.",
    "6 C: I AND II ARE TRUE. III IS FALSE BECAUSE MOLAR MASSES DIFFER.",
    "7 D: MOLAR MASS = GRAMS PER ONE MOLE.",
]

PART2 = [
    ("1 TIN ACETATE", [
        "1. MASS OF 4.87 MOL TIN(II) ACETATE",
        "ANSWER: 1153 g (1.15ᴇ3 g TO 3 SF)",
        "Sn2+ AND C2H3O2- GIVE Sn(C2H3O2)2",
        "M = 118.71 + 2[2(12.01) + 3(1.008) + 2(16.00)]",
        "= 118.71 + 2(59.044) = 236.80 g/mol",
        "4.87 mol x (236.80 g / 1 mol) = 1153 g",
    ]),
    ("2 Na ATOMS", [
        "2. ATOMS IN 5.0 g OF SODIUM",
        "ANSWER: 1.3ᴇ23 ATOMS (2 SF)",
        "5.0 g Na x (1 mol / 22.99 g) x (6.022ᴇ23 atoms / 1 mol)",
        "= 0.2175 mol x 6.022ᴇ23",
        "= 1.31ᴇ23 atoms",
    ]),
    ("3 Al IONS", [
        "3. Al3+ IONS IN 550 g Al2(SO4)3",
        "ANSWER: 1.94ᴇ24 IONS (1.9ᴇ24 TO 2 SF)",
        "M = 2(26.98) + 3[32.07 + 4(16.00)]",
        "= 53.96 + 288.21 = 342.17 g/mol",
        "550 g x (1 mol / 342.17 g) x (2 mol Al3+ / 1 mol) x (6.022ᴇ23 / 1 mol)",
        "= 1.607 mol x 2 = 3.214 mol Al3+",
        "= 1.94ᴇ24 Al3+ IONS",
    ]),
    ("4 EMP/MOLEC", [
        "4. 60.0% C, 4.48% H, 35.5% O, MOLECULAR MASS 540 u",
        "ANSWER: EMPIRICAL C9H8O4, MOLECULAR C27H24O12",
        "ASSUME 100 g:",
        "C: 60.0 / 12.01 = 4.996 mol",
        "H: 4.48 / 1.008 = 4.444 mol",
        "O: 35.5 / 16.00 = 2.219 mol",
        "DIVIDE BY 2.219: C 2.25, H 2.00, O 1",
        "2.25 IS NOT WHOLE, SO x4: C 9, H 8, O 4 = C9H8O4",
        "EMPIRICAL MASS = 9(12.01) + 8(1.008) + 4(16.00) = 180.15",
        "540 / 180.15 = 3, SO C27H24O12",
    ]),
    ("5 HYDRATE", [
        "5. 19.06 g OF HYDRATED CaSO4 HEATED TO 15.07 g",
        "ANSWER: CaSO4*2H2O",
        "WATER LOST = 19.06 - 15.07 = 3.99 g",
        "CaSO4: 15.07 g x (1 mol / 136.15 g) = 0.1107 mol",
        "H2O: 3.99 g x (1 mol / 18.02 g) = 0.2214 mol",
        "RATIO = 0.2214 / 0.1107 = 2.00",
        "SO THE FORMULA IS CaSO4*2H2O",
    ]),
    ("6 SAME MOLES", [
        "6. H2O MOLECULES WITH THE SAME MOLES AS 2.40 g CO2",
        "ANSWER: 3.28ᴇ22 MOLECULES",
        "CO2 = 12.01 + 2(16.00) = 44.01 g/mol",
        "2.40 g CO2 x (1 mol / 44.01 g) = 0.05453 mol",
        "SAME MOLES OF H2O, SO:",
        "0.05453 mol x (6.022ᴇ23 molecules / 1 mol)",
        "= 3.28ᴇ22 molecules H2O",
    ]),
]

FORBIDDEN = ['"', "->", ">=", "<=", "!=", "...", "|", "~", "'", ";"]


def wrap(paragraph):
    for bad in FORBIDDEN:
        assert bad not in paragraph, (bad, paragraph)
    return textwrap.wrap(paragraph, WIDTH, break_long_words=True, break_on_hyphens=False) or [""]


def pages(paragraphs):
    """Fill pages of LINES lines, starting a paragraph on a new page when it would not fit
    on the current one (a paragraph longer than a page starts a page and flows on)."""
    chunks = [[]]
    for p in paragraphs:
        lines = wrap(p)
        room = LINES - len(chunks[-1])
        if len(lines) > room and chunks[-1]:
            chunks.append([])
        for line in lines:
            if len(chunks[-1]) == LINES:
                chunks.append([])
            chunks[-1].append(line)
    out = []
    for k, chunk in enumerate(chunks):
        footer = "MORE: [ENTER]" if k < len(chunks) - 1 else "DONE: [ENTER]"
        out.append("ClrHome")
        out.append("Disp " + ",".join(f'"{s}"' for s in chunk))
        out.append(f'Pause "{footer}"')
    return out


def main():
    src = ["Lbl M"]
    src.append('Menu("UNIT IV FORM B","PART I (MC)",1,"PART II WORK",2,"QUIT",Q)')
    src.append("Lbl 1")
    src += pages(PART1)
    src.append("Goto M")
    labels = "ABCDEF"
    items = ",".join(f'"{title}",{labels[i]}' for i, (title, _) in enumerate(PART2))
    src.append("Lbl 2")
    src.append(f'Menu("PART II",{items},"BACK",M)')
    for i, (_, paras) in enumerate(PART2):
        src.append(f"Lbl {labels[i]}")
        src += pages(paras)
        src.append("Goto 2")
    src.append("Lbl Q")
    src.append("ClrHome")
    src.append('Disp "FORM B KEY: BYE"')
    (ROOT / "FORMBKEY.txt").write_text("\n".join(src) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
