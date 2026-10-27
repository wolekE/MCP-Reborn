#!/usr/bin/env python3
"""Build the CHEMKEY TI-BASIC program for the TI-84 Plus CE and TI-84 Plus.

The answer key text is pre-wrapped for each calculator's home screen and padded
with spaces, so a single Output( call shows a whole page with clean word wrap.

    pip install tivars
    python3 build_chemkey.py
"""

import math
from pathlib import Path

from tivars.models import TI_84P, TI_84PCE
from tivars.types import TIProgram

OUT_DIR = Path(__file__).resolve().parent
PROGRAM_NAME = "CHEMKEY"

# (letter, answer, explanation) for questions 1-30.
# Calculator-safe text only: no double quotes, colons or store arrows.
# "ᴇ" is the calculator's scientific-notation E, "²" a superscript 2.
QUESTIONS = [
    ("B", "0.005 km", "500 cm = 5 m, and 5 m / 1000 = 0.005 km."),
    ("A", "5.80 g/mL", "Density = mass / volume = 16.3 g / 2.81 mL."),
    ("B", "iron (II) sulfide",
     "Sulfide is S²-, so iron is Fe²+. Iron has more than one possible "
     "charge, so a Roman numeral is needed."),
    ("B", "nickel (II) hydroxide",
     "Two OH- ions balance Ni²+. Ionic compounds do not use prefixes."),
    ("A", "CuSO4", "Cu²+ and SO4²- combine 1 to 1."),
    ("C", "nitrogen dioxide",
     "Molecular compounds use prefixes, and 'mono' is dropped on the first "
     "element."),
    ("D", "Al2O3",
     "The 2 to 3 ratio cannot be reduced. N2O4 reduces to NO2, P4O10 to "
     "P2O5, and C6H12O6 to CH2O."),
    ("B", "AsCl4", "Arsenic is As (Ar is argon). 'Tetra' means 4."),
    ("D", "36 protons and 44 neutrons",
     "Krypton's atomic number is 36, and 80 - 36 = 44. Electrons are not in "
     "the nucleus."),
    ("B", "the number of neutrons",
     "Neutrons require the mass number as well."),
    ("D", "310 g", "3(40.08) + 2(30.97) + 8(16.00) = 310.18 g/mol."),
    ("D", "H2S, CuCl2, KI", "The other sets contain elements or ions."),
    ("B", "-1", "Element 53 is iodine, a halogen, which gains one electron."),
    ("D", "27%", "Carbon is 24.02 g out of 90.04 g/mol, which is 26.7%."),
    ("B", "atom", ""),
    ("D", "sodium chloride",
     "Binary means exactly two elements. The other choices contain oxygen."),
    ("C", "10.2%", "(55.2 - 50.1) / 50.1 * 100 = 10.2%."),
    ("B", "ion", ""),
    ("C", "45.5 amu", "(45 * 0.83) + (48 * 0.17) = 45.51."),
    ("B", "7.26ᴇ16 Hz",
     "Frequency = c / wavelength = (3.00ᴇ8 m/s) / (4.13ᴇ⁻9 m)."),
    ("B", "2", "Alkaline earth metals are in Group 2."),
    ("A", "atomic numbers", ""),
    ("A", "anion", "Gaining an electron makes it negative."),
    ("C", "Mn", "Mn is [Ar]4s2 3d5. Cr is an exception that ends in 4s1 3d5."),
    ("A", "1380 g",
     "Mg3(PO4)2 is 262.9 g/mol, and 5.25 mol * 262.9 g/mol = 1380 g."),
    ("D", "12", "CH2O is 30 g/mol, and 180 / 30 = 6, giving C6H12O6."),
    ("B", "7.34ᴇ23",
     "100.0 g / 164.1 g/mol = 0.609 mol Ca(NO3)2. That gives 2 * 0.609 = "
     "1.219 mol NO3-, and 1.219 * 6.022ᴇ23 = 7.34ᴇ23 ions."),
    ("C", "carbonic acid", "Acids from '-ate' ions are named '-ic acid'."),
    ("C", "Beaker", "The short, wide cup with a pouring spout."),
    ("A", "Graduated cylinder",
     "The tall, narrow cylinder with volume markings."),
]

FORBIDDEN = set('":→')


class Layout:
    def __init__(self, key, model, width, height, header, grid, help_lines):
        self.key = key
        self.model = model
        self.width = width
        self.height = height
        self.header = header        # n, letter -> header text
        self.grid = grid            # -> list of answer-list screen rows
        self.help_lines = help_lines
        # Row 1 is the header and the last row is the footer.
        self.rows = height - 2
        self.page_chars = self.rows * width
        # The TI-84 Plus run indicator covers the top-right character cell.
        self.header_max = width - 1 if key == "84PLUS" else width

    @property
    def stem(self):
        return f"{PROGRAM_NAME}-{self.key}"


def grid_84plus():
    # 4 per row on 8 rows: " 1B  2A  3B  4B "
    cells = [f"{n:>2}{q[0]} " for n, q in enumerate(QUESTIONS, 1)]
    return ["".join(cells[i:i + 4]) for i in range(0, len(cells), 4)]


def grid_ce():
    # 5 per row on 6 rows: " 1 B  2 A  3 B  4 B  5 A "
    cells = [f"{n:>2} {q[0]} " for n, q in enumerate(QUESTIONS, 1)]
    rows = ["".join(cells[i:i + 5]) for i in range(0, len(cells), 5)]
    return ["ANSWER KEY", ""] + rows + ["", "Press any key"]


LAYOUTS = [
    Layout(
        "CE", TI_84PCE, 26, 10,
        lambda n, letter: f"Question {n}/30".ljust(16) + f"Answer ({letter})",
        grid_ce,
        ["HOW TO USE", "",
         "LEFT/RIGHT ARROWS", "  previous/next question",
         "UP/DOWN ARROWS", "  scroll a long answer",
         "ENTER  next page/question", "CLEAR  back to menu", "",
         "v1/2 means more below"],
    ),
    Layout(
        "84PLUS", TI_84P, 16, 8,
        lambda n, letter: f"Question {n}".ljust(12) + f"({letter})",
        grid_84plus,
        ["HOW TO USE", "",
         "LEFT/RIGHT ARROW", " prev/next ques.",
         "UP/DOWN ARROW", " scroll a page",
         "ENTER  continue", "CLEAR  menu"],
    ),
]


def wrap(text, width):
    """Greedy word wrap; breaks only at spaces."""
    lines, line = [], ""
    for word in text.split():
        if len(word) > width:
            raise ValueError(f"word too long for {width} columns: {word}")
        candidate = f"{line} {word}" if line else word
        if len(candidate) <= width:
            line = candidate
        else:
            lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


def screen_text(lines, layout):
    """Pad full-screen rows so one Output( call lays them out exactly."""
    if len(lines) > layout.height:
        raise ValueError(f"{layout.key}: screen has {len(lines)} rows")
    for line in lines:
        if len(line) > layout.width:
            raise ValueError(f"{layout.key}: row too wide: {line!r}")
    if len(lines[0].rstrip()) > layout.header_max:
        raise ValueError(f"{layout.key}: first row hits run indicator")
    return "".join(line.ljust(layout.width) for line in lines).rstrip()


def question_text(n, layout):
    """Header row followed by the answer and explanation, padded to rows."""
    letter, answer, explanation = QUESTIONS[n - 1]
    header = layout.header(n, letter)
    if len(header) > layout.header_max:
        raise ValueError(f"{layout.key}: header too wide: {header!r}")

    body = wrap(f"({letter}) {answer}", layout.width)
    if explanation:
        notes = wrap(explanation, layout.width)
        pages = math.ceil((len(body) + len(notes)) / layout.rows)
        # A blank line after the answer, but only if it costs no extra page.
        if math.ceil((len(body) + 1 + len(notes)) / layout.rows) == pages:
            body.append("")
        body += notes

    pages = math.ceil(len(body) / layout.rows)
    if pages > 9:
        raise ValueError(f"{layout.key}: question {n} needs {pages} pages")
    rows = [header.ljust(layout.width)] + [line.ljust(layout.width) for line in body]
    return "".join(rows).rstrip()


def program_source(layout):
    w, h, c = layout.width, layout.height, layout.page_chars
    lines = [
        "Full",
        "Lbl M",
        'Menu("CHEM QUIZ KEY","GO TO QUESTION",G,"BROWSE ALL",B,'
        '"ANSWER LIST",L,"HELP",H,"QUIT",Q)',
        "Lbl G",
        "ClrHome",
        'Disp "QUESTION NUMBER"',
        'Input "(1-30)? ",N',
        "If N<1 or N>30 or fPart(N)",
        "Goto G",
        "1→P",
        "Goto V",
        "Lbl B",
        "1→N",
        "1→P",
        # Show question N, page P.
        "Lbl V",
    ]
    for n in range(1, len(QUESTIONS) + 1):
        text = question_text(n, layout)
        if FORBIDDEN & set(text):
            raise ValueError(f"question {n} has a character TI-BASIC strings can't hold")
        lines += [f"If N={n}", f'"{text}"→Str9']
    lines += [
        # K = number of pages = ceil((length - header) / page size)
        f"int((length(Str9)+{c - 1 - w})/{c})→K",
        "ClrHome",
        f"Output(1,1,sub(Str9,1,{w}))",
        f"{c}(P-1)→A",
        f"Output(2,1,sub(Str9,{w + 1}+A,min({c},length(Str9)-{w}-A)))",
        f'Output({h},1,"<PREV")',
        f'Output({h},{w - 4},"NEXT>")',
        "If K>1",
        f'Output({h},{w // 2 - 1},sub("v^",1+(P=K),1)+sub("123456789",P,1)'
        '+"/"+sub("123456789",K,1))',
        "Repeat max(X={24,25,26,34,45,105})",
        "getKey→X",
        "End",
        "If X=45",
        "Goto M",
        # ENTER: next page if there is one, else next question.
        "If X=105",
        "26+8(P<K)→X",
        "P+(X=34 and P<K)-(X=25 and P>1)→P",
        "If X=24 or X=26",
        "1→P",
        "N+(X=26)-(X=24)→N",
        "N+30(N<1)-30(N>30)→N",
        "Goto V",
        "Lbl L",
        "ClrHome",
        f'Output(1,1,"{screen_text(layout.grid(), layout)}")',
        "Repeat getKey",
        "End",
        "Goto M",
        "Lbl H",
        "ClrHome",
        f'Output(1,1,"{screen_text(layout.help_lines, layout)}")',
        "Repeat getKey",
        "End",
        "Goto M",
        "Lbl Q",
        "ClrHome",
        "DelVar Str9",
    ]
    return "\n".join(lines)


def build():
    results = []
    for layout in LAYOUTS:
        source = program_source(layout)
        program = TIProgram(name=PROGRAM_NAME)
        program.load_string(source, model=layout.model)

        # The decoder spells the apostrophe token as \'
        decoded = program.string(model=layout.model).replace("\\'", "'")
        if decoded != source:
            raise RuntimeError(f"{layout.key}: tokenizer round trip changed the program")

        (OUT_DIR / f"{layout.stem}.txt").write_text(source + "\n", encoding="utf-8")
        program.save(str(OUT_DIR / f"{layout.stem}.8xp"), model=layout.model)
        results.append((layout, program))
        print(f"{layout.stem}.8xp: {len(program.data)} bytes of program data")
    return results


if __name__ == "__main__":
    build()
