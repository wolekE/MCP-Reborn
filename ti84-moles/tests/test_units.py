"""Unit checks: call MOLES's own subroutines (number formatter, sig-fig counter, formula parser)
through a small driver program in the TI-BASIC simulator and compare every result with the
independent Python oracle.

    python3 -I tests/test_units.py
"""

import itertools
import pathlib
import sys
from decimal import Decimal

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import oracle  # noqa: E402
from tisim import run_text  # noqa: E402

MOLES_SRC = (ROOT / "MOLES.txt").read_text(encoding="utf-8")
# the element tables, copied from MOLES's own start-up code
TABLES = "\n".join(l for l in MOLES_SRC.splitlines() if l.endswith("→Str0") or l.endswith("→ʟAMASS"))
SEP = "|"


def ti_number(x):
    """Python number -> TI-BASIC literal."""
    s = format(Decimal(str(x)), "E") if abs(x) >= 1e10 or (x and abs(x) < 1e-3) else format(Decimal(str(x)), "f")
    if "E" in s:
        mant, exp = s.split("E")
        mant = mant.rstrip("0").rstrip(".") if "." in mant else mant
        s = mant + "ᴇ" + str(int(exp))
    return s.replace("-", "⁻")


def drive(body, model="84p", script=()):
    src = f"16→W\n8→H\n0→R\n{TABLES}\n\"\"→Str5\n{{0}}→ʟRES\n{body}"
    res = run_text(src, model=model, script=list(script), programs={"MOLES": MOLES_SRC})
    assert res.error is None, res.error
    return res


def check_format():
    values = [0, 1, 2, 9.9996, 0.00012345, 1e-5, 99999.5, 1e10, 12345678901, 0.05453306067,
              342.17, 192, 1153.1673, 1.30969987e23, 3.011e23, 1.935938276e24, 18.016, 32,
              0.5, 2.000426055, 236.788, 27.28925244, 1150, 1000, 0.001, 0.000999, 7.5, 0.25,
              123.456789, 6.022e23, 4.9825887902, 98, 16, 1.008, 207.2, 0.0999, 9.99, 99.95]
    cases = []
    for v in values:
        for S, T in itertools.product(range(1, 11), (0, 1)):
            cases.append((v, S, T))
        if v < 1e6:
            for S in range(0, 5):
                cases.append((v, S, 2))
    cases += [(-v, 4, 0) for v in (1.5, 0.0123, 6.022e23)]
    body = []
    for v, S, T in cases:
        body.append(f"{ti_number(v)}→X\n{S}→S\n{T}→T\n⁻1.07→θ\nprgmMOLES\nStr5+Str3+\"{SEP}\"→Str5")
    res = drive("\n".join(body))
    got = res.vars["Str5"].split(SEP)[:-1]
    bad = 0
    for (v, S, T), g in zip(cases, got):
        exp = oracle.fmt(Decimal(ti_number(v).replace("ᴇ", "E").replace("⁻", "-")), S, T)
        if g != exp:
            bad += 1
            print(f"  format({v}, S={S}, T={T}): MOLES {g!r} oracle {exp!r}")
    print(f"format: {len(cases) - bad}/{len(cases)} agree")
    return bad


def check_sigfigs():
    texts = ["5.0", "36.0", "550", "4.87", "0.500", "6.022ᴇ23", "100.", "105", "0.00500", "2.40",
             "1.204ᴇ24", "3", "0.0", "1200", "1200.0", "⁻4.50", "19.06", "15.07", "7", "0.03", "10.10ᴇ⁻3"]
    body = [f"\"{t}\"→Str2\n⁻4.07→θ\nprgmMOLES\nD→ʟRES({i + 1})" for i, t in enumerate(texts)]
    res = drive("\n".join(body))
    bad = 0
    for t, d in zip(texts, res.vars["ʟRES"]):
        exp = oracle.sigfigs(t)
        if int(d) != exp:
            bad += 1
            print(f"  sigfigs({t!r}): MOLES {int(d)} oracle {exp}")
    print(f"sigfigs: {len(texts) - bad}/{len(texts)} agree")
    return bad


def check_parser():
    # (typed text, ambiguity key presses: 92 = "1" two-letter element, 93 = "2" separate elements)
    cases = [
        ("Al2(SO4)3", []), ("Sn(C2H3O2)2", []), ("CaSO4*2H2O", []), ("CuSO4.5H2O", []),
        ("Ca3(PO4)2", []), ("Fe2(Cr2O7)3", []), ("NH4NO3", []), ("(NH4)2SO4", []),
        ("C6H12O6", []), ("Mg(OH)2", []), ("Ba(NO3)2", []), ("K2Cr2O7", []), ("H2O", []),
        ("NaCl", []), ("Hg2Cl2", []), ("Pb(C2H3O2)2", []), ("AuCl3", []), ("AgNO3", []),
        ("KI", []), ("C12H22O11", []), ("Ca(C2H3O2)2*H2O", []), ("Na2CO3*10H2O", [93]),
        ("Fe(NO3)3*9H2O", []), ("Mg3(PO4)2", []), ("Al2(SO4)3*18H2O", []),
        ("NACL", []), ("AL2(SO4)3", []), ("CACO3", [93]), ("CO2", [93]), ("CO", [92]),
        ("COCL2", [92]), ("COCL2", [93]), ("SIO2", [92]), ("SCN", [93]), ("NI3", [93]),
        ("PBCL2", [92]), ("SN(C2H3O2)2", [92]), ("CUSO4*5H2O", []), ("MGCL2", []),
        ("FE2O3", []), ("BACL2", []), ("NAHCO3", [93]), ("KMNO4", []), ("HGO", []),
        ("Ca((OH)2)", []), ("PBr3", []), ("SCl2", []), ("BAs", []), ("NBr3", []),
    ]
    body, script = [], []
    for i, (text, keys) in enumerate(cases):
        body.append(f"\"{text}\"→Str1\n⁻3.07→θ\nprgmMOLES\nM→ʟRES({i + 1})\nStr5+Str1+\"{SEP}\"→Str5")
        script += [f"key:{k}" for k in keys]
    res = drive("\n".join(body), script=script)
    got_m, got_s = res.vars["ʟRES"], res.vars["Str5"].split(SEP)[:-1]
    bad = 0
    for (text, keys), m, canon in zip(cases, got_m, got_s):
        choices = [1 if k == 92 else 2 for k in keys]
        exp_canon = oracle.resolve_caps(text, choices) if text.upper() == text else text.replace(".", "*")
        exp_m = oracle.parse(exp_canon)["M_exact"]
        if canon != exp_canon or Decimal(m) != Decimal(exp_m):
            bad += 1
            print(f"  parse({text!r}): MOLES {canon!r} M={m}  oracle {exp_canon!r} M={exp_m}")
    print(f"parser: {len(cases) - bad}/{len(cases)} agree")
    if res.unused_script_items:
        print(f"  {res.unused_script_items} key presses were not consumed")
        bad += 1
    return bad


def check_parser_errors():
    bad_inputs = ["2H2O", "H2O*", "*H2O", "Al2(SO4", "Al2SO4)3", "Xx", "Q", "H2O**H2O", "(H2O*H2O)", "Al2#3"]
    bad = 0
    for text in bad_inputs:
        res = drive(f"\"{text}\"→Str1\n⁻3.07→θ\nprgmMOLES\nM→ʟRES(1)")
        if res.vars["ʟRES"][0] != 0 or not any("FORMULA ERROR" in l for l in res.displayed()):
            bad += 1
            print(f"  {text!r} was accepted (M={res.vars['ʟRES'][0]})")
    print(f"parser errors: {len(bad_inputs) - bad}/{len(bad_inputs)} rejected")
    return bad


def check_stale_theta():
    """A θ left over by another program must not hijack MOLES's start-up."""
    bad = 0
    for theta in ("⁻1", "⁻2", "⁻3", "⁻9", "0", "1.5"):
        res = run_text(f"{theta}→θ\nprgmMOLES", script=["menu:7"], programs={"MOLES": MOLES_SRC})
        menus = [e for e in res.transcript if e.get("type") == "menu"]
        if res.error or not menus or menus[0]["title"] != "MOLE UNIT SOLVER":
            bad += 1
            print(f"  θ={theta} at start-up: error={res.error} menus={len(menus)}")
    print(f"stale θ: {6 - bad}/6 start at the main menu")
    return bad


if __name__ == "__main__":
    total = check_format() + check_sigfigs() + check_parser() + check_parser_errors() + check_stale_theta()
    print("ALL UNIT CHECKS PASS" if not total else f"{total} mismatches")
    sys.exit(1 if total else 0)
