"""End-to-end sessions: drive MOLES.txt / FORMBKEY.txt through the TI-BASIC simulator with
scripted key presses on both screen models and check the printed work and answers.

    python3 -I tests/run_sessions.py            # all sessions, both models
    python3 -I tests/run_sessions.py -v NAME    # also print the screens of one session
"""

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

from tisim import run_program  # noqa: E402

MOLES = ROOT / "MOLES.txt"
KEY = ROOT / "FORMBKEY.txt"
QUIT = "menu:7"

# name: (program, scripted inputs, substrings that must appear in the displayed text)
# Substrings are compared with all spaces removed, because long lines wrap on the 16-column screen.
SESSIONS = {
    # practice cases from the request
    "practice 36.0 g H2O -> mol": (MOLES, ["menu:2", "menu:1", "H2O", "36.0", "", QUIT], [
        "MOLAR MASS H2O = 18.02 g/mol",
        "36.0 g H2O x (1 mol / 18.02 g)",
        "UNROUNDED: 1.997780244 mol H2O",
        "ANSWER: 2.00 mol H2O (3 SF)",
    ]),
    "practice 0.500 mol CO2 -> particles (caps, ambiguity)": (MOLES, ["menu:2", "menu:3", "CO2", "key:93", "0.500", "", QUIT], [
        "YOU TYPED CO.",
        "0.500 mol CO2 x (6.022ᴇ23 / 1 mol)",
        "UNROUNDED: 3.011ᴇ23 particles CO2",
        "ANSWER: 3.01ᴇ23 particles CO2 (3 SF)",
    ]),
    "practice CuSO4 hydrate": (MOLES, ["menu:5", "5.00", "3.20", "CuSO4", QUIT], [
        "5.00 g - 3.20 g = 1.8 g",
        "3.20 g x (1 mol / 159.62 g) = 0.02005 mol",
        "1.8 g x (1 mol / 18.02 g) = 0.09989 mol",
        "0.09989 / 0.02005 = 4.983",
        "x = 5",
        "FORMULA: CuSO4*5H2O",
    ]),
    "practice 85.6% C 14.4% H": (MOLES, ["menu:4", "menu:1", "2", "C", "85.6", "H", "14.4", "", QUIT], [
        "ASSUME 100 g",
        "C: 85.6 / 12.01 = 7.127 mol",
        "H: 14.4 / 1.008 = 14.29 mol",
        "H: 14.29 / 7.127 = 2.004",
        "EMPIRICAL FORMULA: CH2",
    ]),
    # Form B, Part II
    "formB 1 tin(II) acetate": (MOLES, ["menu:2", "menu:2", "Sn(C2H3O2)2", "4.87", "", QUIT], [
        "MOLAR MASS Sn(C2H3O2)2 = 236.79 g/mol",
        "4.87 mol Sn(C2H3O2)2 x (236.79 g / 1 mol)",
        "UNROUNDED: 1153.1673 g",
        "ANSWER: 1.15ᴇ3 g Sn(C2H3O2)2 (3 SF)",
    ]),
    "formB 1 tin(II) acetate typed in caps": (MOLES, ["menu:2", "menu:2", "SN(C2H3O2)2", "key:92", "4.87", "", QUIT], [
        "YOU TYPED SN.",
        "MOLAR MASS Sn(C2H3O2)2 = 236.79 g/mol",
        "ANSWER: 1.15ᴇ3 g Sn(C2H3O2)2 (3 SF)",
    ]),
    "formB 2 Na atoms": (MOLES, ["menu:2", "menu:5", "Na", "5.0", "", QUIT], [
        "5.0 g Na x (1 mol / 22.99 g) x (6.022ᴇ23 / 1 mol)",
        "UNROUNDED: 1.30969987ᴇ23 particles Na",
        "ANSWER: 1.3ᴇ23 particles Na (2 SF)",
    ]),
    "formB 3 Al ions": (MOLES, ["menu:2", "menu:7", "Al2(SO4)3", "Al", "550", "", QUIT], [
        "MOLAR MASS Al2(SO4)3 = 342.17 g/mol",
        "550 g Al2(SO4)3 x (1 mol / 342.17 g) x (2 mol Al / 1 mol Al2(SO4)3) x (6.022ᴇ23 / 1 mol)",
        "ANSWER: 1.9ᴇ24 atoms/ions Al (2 SF)",
    ]),
    "formB 4 empirical + molecular": (MOLES, ["menu:4", "menu:1", "3", "C", "60.0", "H", "4.48", "O", "35.5", "540", QUIT], [
        "C: 60 / 12.01 = 4.996 mol",
        "H: 4.48 / 1.008 = 4.444 mol",
        "O: 35.5 / 16.00 = 2.219 mol",
        "DIVIDE BY SMALLEST (2.219)",
        "C: 4.996 / 2.219 = 2.252",
        "NOT ALL WITHIN 0.1 OF A WHOLE NUMBER, SO MULTIPLY:",
        "x2: C 4.503 H 4.006 O 2.000",
        "x3: C 6.755 H 6.009 O 3.000",
        "x4: C 9.007 H 8.013 O 4.000",
        "EMPIRICAL FORMULA: C9H8O4",
        "EMPIRICAL MASS = 180.15 g/mol",
        "n = 540 / 180.15 = 2.998, ROUNDS TO 3",
        "MOLECULAR FORMULA: C27H24O12",
    ]),
    "formB 5 hydrate (caps)": (MOLES, ["menu:5", "19.06", "15.07", "CASO4", QUIT], [
        "19.06 g - 15.07 g = 3.99 g",
        "15.07 g x (1 mol / 136.15 g) = 0.1107 mol",
        "3.99 g x (1 mol / 18.02 g) = 0.2214 mol",
        "0.2214 / 0.1107 = 2.000",
        "FORMULA: CaSO4*2H2O",
    ]),
    "formB 6 same moles": (MOLES, ["menu:6", "menu:1", "menu:2", "CO2", "key:93", "2.40", "H2O", "", QUIT], [
        "2.40 g CO2 x (1 mol / 44.01 g) x (1 mol H2O / 1 mol CO2) x (6.022ᴇ23 / 1 mol)",
        "(MOLES OF A = MOLES OF B = 0.05453 mol)",
        "ANSWER: 3.28ᴇ22 particles H2O (3 SF)",
    ]),
    # other features
    "molar mass Al2(SO4)3": (MOLES, ["menu:1", "Al2(SO4)3", "", QUIT], [
        "Al: 2 x 26.98 = 53.96 g",
        "S: 3 x 32.07 = 96.21 g",
        "O: 12 x 16.00 = 192 g",
        "UNROUNDED: 342.17 g/mol",
        "ANSWER: 342.17 g/mol Al2(SO4)3 (5 SF)",
    ]),
    "molar mass hydrate CaSO4*2H2O": (MOLES, ["menu:1", "CaSO4*2H2O", "4", QUIT], [
        "H: 4 x 1.008 = 4.032 g",
        "O: 6 x 16.00 = 96 g",
        "UNROUNDED: 172.182 g/mol",
        "ANSWER: 172.2 g/mol",
    ]),
    "percent comp CO2": (MOLES, ["menu:3", "menu:1", "CO2", "key:93", "", QUIT], [
        "%C = (1 x 12.01) / 44.01 x 100",
        "UNROUNDED: 27.28925244 %",
        "ANSWER: 27.29 % C (4 SF)",
        "ANSWER: 72.71 % O (4 SF)",
    ]),
    "percent water CuSO4*5H2O": (MOLES, ["menu:3", "menu:2", "CuSO4*5H2O", "", QUIT], [
        "WATER PART = 249.70 - 159.62 = 90.08 g/mol",
        "% WATER = 90.08 / 249.70 x 100",
        "ANSWER: 36.08 % water (4 SF)",
    ]),
    "moles -> grams NaCl caps": (MOLES, ["menu:2", "menu:2", "NACL", "2.50", "", QUIT], [
        "MOLAR MASS NaCl = 58.44 g/mol",
        "ANSWER: 146 g NaCl (3 SF)",
    ]),
    "particles -> moles": (MOLES, ["menu:2", "menu:4", "H2O", "1.204ᴇ24", "", QUIT], [
        "1.204ᴇ24 particles H2O x (1 mol / 6.022ᴇ23)",
        "ANSWER: 1.999 mol H2O (4 SF)",
    ]),
    "particles -> grams": (MOLES, ["menu:2", "menu:6", "H2O", "3.011ᴇ23", "", QUIT], [
        "x (18.02 g / 1 mol)",
        "ANSWER: 9.010 g H2O (4 SF)",
    ]),
    "same moles particles -> grams": (MOLES, ["menu:6", "menu:2", "menu:1", "H2O", "6.022ᴇ23", "NaCl", "", QUIT], [
        "x (58.44 g NaCl / 1 mol)",
        "ANSWER: 58.44 g NaCl (4 SF)",
    ]),
    "error: unknown element": (MOLES, ["menu:1", "Xq2", QUIT], ["FORMULA ERROR:", "UNKNOWN Xq"]),
    "error: missing paren": (MOLES, ["menu:1", "Al2(SO4", QUIT], ["FORMULA ERROR:", "MISSING )"]),
    "error: element not in formula": (MOLES, ["menu:2", "menu:7", "H2O", "Na", QUIT], ["NOT IN FORMULA"]),
    "nested parens": (MOLES, ["menu:1", "Ca3(PO4)2", "", QUIT], ["UNROUNDED: 310.18 g/mol"]),
    "answer key part I": (KEY, ["menu:1", "menu:3"], ["1:D 2:D 3:C", "4:C 5:B 6:C", "7:D"]),
    "answer key part II #4": (KEY, ["menu:2", "menu:4", "menu:7", "menu:3"], ["C27H24O12", "C9H8O4"]),
}


def flat(res, key):
    return res[key] if isinstance(res, dict) else getattr(res, key)


PAGE_BREAK = "MORE: [ENTER]"


def displayed_text(res):
    return " ".join(line for line in res.displayed() if line != PAGE_BREAK)


def main():
    verbose = "-v" in sys.argv
    only = [a for a in sys.argv[1:] if a != "-v"]
    failures = 0
    for name, (prog, script, expected) in SESSIONS.items():
        if only and not any(o in name for o in only):
            continue
        for model in ("84p", "ce"):
            res = run_program(str(prog), model=model, script=list(script))
            text = displayed_text(res).replace(" ", "")
            problems = []
            err = flat(res, "error")
            if err and "script exhausted" not in str(err):
                problems.append(f"error: {err}")
            for w in flat(res, "warnings"):
                problems.append(f"warning: {w}")
            for exp in expected:
                if exp.replace(" ", "") not in text:
                    problems.append(f"missing: {exp}")
            status = "ok  " if not problems else "FAIL"
            print(f"{status} [{model}] {name}")
            for p in problems:
                print("      ", p)
            failures += bool(problems)
            if verbose:
                for snap in flat(res, "screens"):
                    print("      +" + "-" * (16 if model == "84p" else 26) + "+")
                    rows = snap["rows"]
                    for row in rows:
                        print("      |" + row + "|")
    print(f"\n{failures} failing session(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
