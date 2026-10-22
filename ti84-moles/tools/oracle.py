#!/usr/bin/env python3
"""Independent reference implementation ("oracle") for the TI-84 MOLES program.

Computes the numbers and display strings the TI-BASIC program MOLES must
print, so its output can be cross-checked.  Standard library only.  All
arithmetic uses decimal.Decimal in a 14-significant-digit context to mirror
the TI-84's 14-digit BCD math.

Public API (all numeric results are Decimal):
  SYMBOLS, MASSES, MASS, NA, element_index(sym)
  parse(formula)                    -> dict  (Feature 1 data; molar_mass is an alias)
  resolve_caps(text, choices)       -> str   (ALL-CAPS formula -> properly cased)
  resolve_caps_detailed(text, choices) -> (str, ambiguity log)
  convert(kind, value, formula, element=None) -> dict   (Feature 2)
  percent_composition(formula)      -> dict  (Feature 3)
  percent_water(formula)            -> dict  (Feature 3)
  empirical(pairs, molar_mass=None, mode='percent') -> dict  (Feature 4)
  hydrate_from_heating(before, after, anhydrous) -> dict      (Feature 5)
  same_moles(amount, unit_a, formula_a, unit_b, formula_b=None) -> dict (Feature 6)
  fmt(x, S, T) -> str    TI-style number formatting (T=0 sig figs, T=1 up to S
                         sig figs with trailing zeros stripped, T=2 fixed decimals)
  sigfigs(text) -> int   significant-figure count of a typed number string
  CASES                  named acceptance cases (name -> zero-arg function)

CLI:
  python3 tools/oracle.py list
  python3 tools/oracle.py case NAME        expected numbers/strings for one case
  python3 tools/oracle.py all              every case as JSON
  python3 tools/oracle.py parse FORMULA    molar-mass breakdown as JSON
  python3 tools/oracle.py caps TEXT [CHOICE ...]
  python3 tools/oracle.py fmt X S T
  python3 tools/oracle.py sigfigs TEXT
"""
from __future__ import annotations

import json
import string
import sys
from decimal import ROUND_HALF_UP, Context, Decimal, localcontext
from functools import wraps

# ---------------------------------------------------------------------------
# Numeric context and constants
# ---------------------------------------------------------------------------
TI_CTX = Context(prec=14, rounding=ROUND_HALF_UP)   # TI-84: 14-digit mantissa
_WIDE = Context(prec=60, rounding=ROUND_HALF_UP)    # for exact rounding helpers

EXP = "ᴇ"   # 'ᴇ' TI scientific-notation marker
NEG = "⁻"   # '⁻' TI negative sign / negative exponent

_TABLE = (
    "H 1.008 He 4.003 Li 6.941 Be 9.012 B 10.81 C 12.01 N 14.01 O 16.00 "
    "F 19.00 Ne 20.18 Na 22.99 Mg 24.31 Al 26.98 Si 28.09 P 30.97 S 32.07 "
    "Cl 35.45 Ar 39.95 K 39.10 Ca 40.08 Sc 44.96 Ti 47.87 V 50.94 Cr 52.00 "
    "Mn 54.94 Fe 55.85 Co 58.93 Ni 58.69 Cu 63.55 Zn 65.38 Ga 69.72 Ge 72.63 "
    "As 74.92 Se 78.97 Br 79.90 Kr 83.80 Rb 85.47 Sr 87.62 Y 88.91 Zr 91.22 "
    "Nb 92.91 Mo 95.95 Tc 98 Ru 101.1 Rh 102.9 Pd 106.4 Ag 107.9 Cd 112.4 "
    "In 114.8 Sn 118.7 Sb 121.8 Te 127.6 I 126.9 Xe 131.3 Cs 132.9 Ba 137.3 "
    "Au 197.0 Hg 200.6 Pb 207.2"
).split()
SYMBOLS: list[str] = _TABLE[0::2]                       # index 0 -> element #1
MASSES: list[Decimal] = [Decimal(m) for m in _TABLE[1::2]]
MASS: dict[str, Decimal] = dict(zip(SYMBOLS, MASSES))
NA = Decimal("6.022E23")
WHOLE_TOL = Decimal("0.1")
assert len(SYMBOLS) == 59


def element_index(sym: str) -> int:
    """1-based position of `sym` in the program's list (L1 / symbol string)."""
    return SYMBOLS.index(sym) + 1


def D(x) -> Decimal:
    """Coerce int/float/str (TI-style 'ᴇ'/'⁻' allowed)/Decimal to Decimal."""
    if isinstance(x, Decimal):
        return x
    if isinstance(x, bool):
        raise TypeError("bool is not a number")
    if isinstance(x, int):
        return Decimal(x)
    if isinstance(x, float):
        return Decimal(repr(x))
    if isinstance(x, str):
        return Decimal(x.strip().replace(EXP, "E").replace(NEG, "-"))
    raise TypeError(f"cannot convert {type(x).__name__} to Decimal")


def ti_math(fn):
    """Run `fn` with the 14-digit TI context active."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        with localcontext(TI_CTX):
            return fn(*args, **kwargs)
    return wrapper


def round_places(x, places: int = 0) -> Decimal:
    """round(x, places), half away from zero (TI round())."""
    return D(x).quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP, context=_WIDE)


def round_int(x) -> int:
    return int(round_places(x, 0))


def round2(x) -> Decimal:
    return round_places(x, 2)


# ---------------------------------------------------------------------------
# Formula parsing (Feature 1)
# ---------------------------------------------------------------------------
_UP = set(string.ascii_uppercase)
_LO = set(string.ascii_lowercase)
_DIG = set(string.digits)


def _read_int(s: str, i: int):
    j = i
    while j < len(s) and s[j] in _DIG:
        j += 1
    if j == i:
        return None, i
    n = int(s[i:j])
    if n == 0:
        raise ValueError(f"zero subscript/coefficient at position {i} in {s!r}")
    return n, j


def _merge(into: dict, add: dict, mult: int = 1) -> None:
    for k, v in add.items():
        into[k] = into.get(k, 0) + v * mult


def _parse_group(s: str, i: int, depth: int):
    counts: dict[str, int] = {}
    while i < len(s):
        c = s[i]
        if c in _UP:
            sym = c
            i += 1
            if i < len(s) and s[i] in _LO:
                sym += s[i]
                i += 1
            if sym not in MASS:
                raise ValueError(f"unknown element {sym!r} in {s!r}")
            n, i = _read_int(s, i)
            _merge(counts, {sym: n or 1})
        elif c == "(":
            sub, i = _parse_group(s, i + 1, depth + 1)
            if i >= len(s) or s[i] != ")":
                raise ValueError(f"missing ')' in {s!r}")
            if not sub:
                raise ValueError(f"empty parentheses in {s!r}")
            n, i = _read_int(s, i + 1)
            _merge(counts, sub, n or 1)
        elif c == ")":
            if depth == 0:
                raise ValueError(f"unexpected ')' in {s!r}")
            return counts, i
        else:
            raise ValueError(f"unexpected character {c!r} at position {i} in {s!r}")
    if depth:
        raise ValueError(f"missing ')' in {s!r}")
    return counts, i


def _canon(formula: str) -> str:
    return formula.strip().replace(" ", "").replace("·", "*").replace(".", "*")


@ti_math
def parse(formula: str) -> dict:
    """Parse a properly-cased formula such as 'Al2(SO4)3' or 'CaSO4*2H2O'.

    Returns elements in order of first appearance with total counts, the
    per-element lines (symbol, count, atomic mass, count*mass), M_exact,
    M2 = round(M_exact, 2), and the anhydrous (pre-'*') mass.
    """
    s = _canon(formula)
    if not s:
        raise ValueError("empty formula")
    parts = s.split("*")
    if any(not p for p in parts):
        raise ValueError(f"empty part around '*' in {formula!r}")
    total: dict[str, int] = {}
    part_info = []
    for idx, p in enumerate(parts):
        coeff, j = (None, 0)
        if idx > 0:
            coeff, j = _read_int(p, 0)
        counts, _ = _parse_group(p, j, 0)
        if not counts:
            raise ValueError(f"no elements in part {p!r}")
        c = coeff or 1
        _merge(total, counts, c)
        unit_mass = sum((n * MASS[e] for e, n in counts.items()), Decimal(0))
        part_info.append({"part": p, "coefficient": c, "unit_mass": unit_mass,
                          "mass": c * unit_mass})
    lines = [(e, n, MASS[e], n * MASS[e]) for e, n in total.items()]
    m_exact = sum((ln[3] for ln in lines), Decimal(0))
    anh_exact = part_info[0]["mass"]
    return {
        "formula": s,
        "elements": [(e, n) for e, n in total.items()],
        "counts": dict(total),
        "lines": lines,
        "M_exact": m_exact,
        "M2": round2(m_exact),
        "anhydrous_formula": parts[0],
        "anhydrous_exact": anh_exact,
        "anhydrous2": round2(anh_exact),
        "parts": part_info,
    }


molar_mass = parse


class AmbiguityError(ValueError):
    """An ALL-CAPS pair needs a user choice but none was supplied."""


def resolve_caps_detailed(text: str, choices=None):
    """Resolve an ALL-CAPS formula to proper case.

    For an uppercase U followed by uppercase V: if U+lower(V) is an element and
    U and V are both elements, the pair is ambiguous and the next entry of
    `choices` decides (1 = two-letter element, 2 = two separate elements).
    If U+lower(V) is an element otherwise, it is taken.  Else U alone must be
    an element.  An already-lowercase following letter always forms a
    2-letter symbol.  Digits, parentheses and '*' are copied; '.' -> '*'.
    Returns (formula, log) where log lists each ambiguity and the choice used.
    """
    choices = [int(c) for c in (choices or [])]
    ci = 0
    out: list[str] = []
    log: list[dict] = []
    s = text.strip()
    i = 0
    while i < len(s):
        c = s[i]
        nxt = s[i + 1] if i + 1 < len(s) else ""
        if c in _UP:
            if nxt and nxt in _LO:
                sym = c + nxt
                if sym not in MASS:
                    raise ValueError(f"unknown element {sym!r} at position {i}")
                out.append(sym)
                i += 2
                continue
            if nxt and nxt in _UP:
                two = c + nxt.lower()
                if two in MASS:
                    if c in MASS and nxt in MASS:
                        if ci >= len(choices):
                            raise AmbiguityError(
                                f"ambiguous {c + nxt!r} at position {i}: "
                                f"1 = {two}, 2 = {c} + {nxt}")
                        ch = choices[ci]
                        ci += 1
                        if ch not in (1, 2):
                            raise ValueError(f"choice must be 1 or 2, got {ch}")
                        log.append({"position": i, "pair": c + nxt, "choice": ch,
                                    "result": two if ch == 1 else f"{c}+{nxt}"})
                        if ch == 1:
                            out.append(two)
                            i += 2
                            continue
                    else:
                        out.append(two)
                        i += 2
                        continue
            if c not in MASS:
                raise ValueError(f"unknown element {c!r} at position {i}")
            out.append(c)
            i += 1
        elif c in _DIG or c in "()*":
            out.append(c)
            i += 1
        elif c in ".·":
            out.append("*")
            i += 1
        elif c == " ":
            i += 1
        else:
            raise ValueError(f"unexpected character {c!r} at position {i}")
    return "".join(out), log


def resolve_caps(text: str, choices=None) -> str:
    return resolve_caps_detailed(text, choices)[0]


# ---------------------------------------------------------------------------
# Feature 2: conversions (molar mass M2 = rounded to 0.01)
# ---------------------------------------------------------------------------
CONVERSIONS = ("g->mol", "mol->g", "mol->particles", "particles->mol",
               "g->particles", "particles->g", "g->atoms")


@ti_math
def convert(kind: str, value, formula: str | None = None, element: str | None = None) -> dict:
    v = D(value)
    info = parse(formula) if formula else None
    m2 = info["M2"] if info else None
    out = {"kind": kind, "value": v, "formula": info["formula"] if info else None, "M2": m2}
    if kind in ("g->mol", "mol->g", "g->particles", "particles->g", "g->atoms") and m2 is None:
        raise ValueError(f"{kind} needs a formula")
    if kind == "g->mol":
        res = v / m2
        out["mol"] = res
    elif kind == "mol->g":
        res = v * m2
        out["mol"] = v
    elif kind == "mol->particles":
        res = v * NA
        out["mol"] = v
    elif kind == "particles->mol":
        res = v / NA
        out["mol"] = res
    elif kind == "g->particles":
        out["mol"] = v / m2
        res = v / m2 * NA
    elif kind == "particles->g":
        out["mol"] = v / NA
        res = v / NA * m2
    elif kind == "g->atoms":
        if element is None:
            raise ValueError("g->atoms needs an element")
        cnt = info["counts"].get(element)
        if cnt is None:
            raise ValueError(f"{element!r} is not in {info['formula']!r}")
        out["mol"] = v / m2
        out["element"] = element
        out["count"] = cnt
        out["mol_element"] = v / m2 * cnt
        res = v / m2 * cnt * NA
    else:
        raise ValueError(f"unknown conversion {kind!r}; expected one of {CONVERSIONS}")
    out["result"] = res
    return out


# ---------------------------------------------------------------------------
# Feature 3: percent composition
# ---------------------------------------------------------------------------
@ti_math
def percent_composition(formula: str) -> dict:
    info = parse(formula)
    m2 = info["M2"]
    rows = [{"element": e, "count": n, "mass": mass, "part": part,
             "percent": part / m2 * 100} for e, n, mass, part in info["lines"]]
    return {"formula": info["formula"], "M_exact": info["M_exact"], "M2": m2, "rows": rows,
            "percents": {r["element"]: r["percent"] for r in rows}}


@ti_math
def percent_water(formula: str) -> dict:
    info = parse(formula)
    if len(info["parts"]) < 2:
        raise ValueError(f"{formula!r} has no hydrate part ('*')")
    m2, a2 = info["M2"], info["anhydrous2"]
    return {"formula": info["formula"], "M2": m2, "anhydrous2": a2,
            "water_mass": m2 - a2, "percent": (m2 - a2) / m2 * 100}


# ---------------------------------------------------------------------------
# Feature 4: empirical and molecular formula
# ---------------------------------------------------------------------------
def _formula_str(syms, subs) -> str:
    return "".join(s + (str(n) if n != 1 else "") for s, n in zip(syms, subs))


def _is_whole(rs) -> bool:
    return all(abs(r - round_places(r, 0)) <= WHOLE_TOL for r in rs)


@ti_math
def empirical(pairs, molar_mass=None, mode: str = "percent") -> dict:
    """pairs: up to 4 (symbol, value); value = percent (100 g basis) or grams."""
    if not 1 <= len(pairs) <= 4:
        raise ValueError("need 1 to 4 elements")
    syms = [p[0] for p in pairs]
    vals = [D(p[1]) for p in pairs]
    for s, v in zip(syms, vals):
        if s not in MASS:
            raise ValueError(f"unknown element {s!r}")
        if v <= 0:
            raise ValueError(f"value for {s} must be > 0")
    moles = [v / MASS[s] for s, v in zip(syms, vals)]
    mn = min(moles)
    ratios = [m / mn for m in moles]
    tried, mult = [], None
    for m in (1, 2, 3, 4, 5):
        scaled = [r * m for r in ratios]
        ok = _is_whole(scaled)
        tried.append({"multiplier": m, "scaled": scaled, "whole": ok})
        if ok:
            mult = m
            break
    flagged = mult is None
    if flagged:
        mult = 1
    scaled = [r * mult for r in ratios]
    subs = [round_int(x) for x in scaled]
    out = {"mode": mode, "symbols": syms, "values": vals, "moles": moles, "min_moles": mn,
           "ratios": ratios, "tried": tried, "multiplier": mult, "flagged": flagged,
           "scaled": scaled, "subscripts": subs, "empirical": _formula_str(syms, subs)}
    em_exact = sum((n * MASS[s] for s, n in zip(syms, subs)), Decimal(0))
    out["EM_exact"] = em_exact
    out["EM"] = round2(em_exact)
    if molar_mass is not None:
        mm = D(molar_mass)
        n_raw = mm / out["EM"]
        n = max(1, round_int(n_raw))
        msubs = [k * n for k in subs]
        out.update({"molar_mass": mm, "n_raw": n_raw, "n": n,
                    "molecular_subscripts": msubs, "molecular": _formula_str(syms, msubs)})
    return out


# ---------------------------------------------------------------------------
# Feature 5: hydrate formula from heating data
# ---------------------------------------------------------------------------
@ti_math
def hydrate_from_heating(before, after, anhydrous: str) -> dict:
    b, a = D(before), D(after)
    water = b - a
    info = parse(anhydrous)
    m_anh = info["M2"]
    m_w = round2(2 * MASS["H"] + MASS["O"])
    mol_anh = a / m_anh
    mol_w = water / m_w
    ratio = mol_w / mol_anh
    x = round_int(ratio)
    formula = info["formula"] + "*" + (str(x) if x > 1 else "") + "H2O"
    return {"before": b, "after": a, "water_mass": water, "M2_anhydrous": m_anh,
            "M2_water": m_w, "mol_anhydrous": mol_anh, "mol_water": mol_w,
            "ratio": ratio, "x": x, "formula": formula}


# ---------------------------------------------------------------------------
# Feature 6: same number of moles, A -> B
# ---------------------------------------------------------------------------
@ti_math
def same_moles(amount, unit_a: str, formula_a: str | None, unit_b: str,
               formula_b: str | None = None) -> dict:
    v = D(amount)
    out = {"amount": v, "unit_a": unit_a, "unit_b": unit_b}
    if unit_a == "g":
        out["M2_A"] = parse(formula_a)["M2"]
        mol = v / out["M2_A"]
    elif unit_a == "particles":
        mol = v / NA
    else:
        raise ValueError("unit_a must be 'g' or 'particles'")
    if unit_b == "g":
        out["M2_B"] = parse(formula_b)["M2"]
        res = mol * out["M2_B"]
    elif unit_b == "particles":
        res = mol * NA
    else:
        raise ValueError("unit_b must be 'g' or 'particles'")
    out["mol"] = mol
    out["result"] = res
    return out


# ---------------------------------------------------------------------------
# Number formatting and sig-fig counting
# ---------------------------------------------------------------------------
def fmt(x, S: int, T: int) -> str:
    """TI-style formatting.  T=0: S sig figs (trailing zeros kept);
    T=1: up to S sig figs, trailing zeros stripped; T=2: S decimal places.
    A negative value gets a leading '⁻' (unless it rounds to zero)."""
    x = D(x)
    S, T = int(S), int(T)
    neg = x < 0
    ax = abs(x)
    if T == 2:
        if S < 0:
            raise ValueError("S must be >= 0 for T=2")
        K = int(ax.scaleb(S).quantize(Decimal(1), rounding=ROUND_HALF_UP, context=_WIDE))
        digits = str(K).rjust(S + 1, "0")
        body = digits if S == 0 else digits[:-S] + "." + digits[-S:]
        return (NEG if neg and K else "") + body
    if T not in (0, 1):
        raise ValueError("T must be 0, 1 or 2")
    if S < 1:
        raise ValueError("S must be >= 1 for T=0/1")
    if ax == 0:
        E, K = 0, 0
    else:
        E = ax.adjusted()                       # floor(log10|x|), exact
        K = int(ax.scaleb(S - 1 - E).quantize(Decimal(1), rounding=ROUND_HALF_UP, context=_WIDE))
        if K >= 10 ** S:
            K //= 10
            E += 1
    Dg = str(K).rjust(S, "0")
    if T == 1:
        Dg = Dg.rstrip("0") or "0"
    n = len(Dg)
    if T == 1:
        normal = -3 <= E <= 9
    else:
        normal = E >= -3 and (E < n - 1 or (E == n - 1 and (Dg[-1] != "0" or K == 0)))
    if normal:
        if E >= n - 1:
            body = Dg + "0" * (E - n + 1)
        elif E >= 0:
            body = Dg[:E + 1] + "." + Dg[E + 1:]
        else:
            body = "0." + "0" * (-E - 1) + Dg
    else:
        body = Dg[0] + ("." + Dg[1:] if n > 1 else "") + EXP + (NEG if E < 0 else "") + str(abs(E))
    return (NEG if neg and K else "") + body


def sigfigs(text) -> int:
    """Sig figs of a typed number string (clamped to 1..9)."""
    s = str(text).strip()
    for e in (EXP, "E", "e"):
        if e in s:
            s = s.split(e, 1)[0]
            break
    s = s.replace(NEG, "").replace("-", "").replace("+", "")
    has_dot = "." in s
    digits = "".join(ch for ch in s if ch in _DIG).lstrip("0")
    if not has_dot:
        digits = digits.rstrip("0")
    return max(1, min(9, len(digits)))


def show(x) -> str:
    """Unrounded display: up to 10 sig figs, TI Float style."""
    return fmt(x, 10, 1)


def _answer(x, typed: str) -> dict:
    s = sigfigs(typed)
    return {"value": x, "display": show(x), "sig_figs": s, "rounded": fmt(x, s, 0)}


# ---------------------------------------------------------------------------
# Named acceptance cases
# ---------------------------------------------------------------------------
def case_practice_h2o():
    r = convert("g->mol", "36.0", "H2O")
    info = parse("H2O")
    with localcontext(TI_CTX):
        alt = D("36.0") / info["M_exact"]
    return {"input": "36.0 g H2O -> mol", "M_exact": info["M_exact"], "M2": r["M2"],
            "mol": _answer(r["result"], "36.0"),
            "note": "spec rule uses M2=18.02; with M_exact=18.016 the value would be "
                    + show(alt) + " (same 3-sf answer)", "mol_if_M_exact": alt}


def case_practice_co2():
    r = convert("mol->particles", "0.500", "CO2")
    return {"input": "0.500 mol CO2 -> molecules", "M2": r["M2"],
            "particles": _answer(r["result"], "0.500")}


def case_practice_cuso4_hydrate():
    return {"input": "CuSO4 hydrate 5.00 g -> 3.20 g",
            **hydrate_from_heating("5.00", "3.20", "CuSO4")}


def case_practice_ch2():
    return {"input": "85.6% C, 14.4% H", **empirical([("C", "85.6"), ("H", "14.4")])}


def case_formb_1():
    r = convert("mol->g", "4.87", "Sn(C2H3O2)2")
    info = parse("Sn(C2H3O2)2")
    return {"input": "4.87 mol Sn(C2H3O2)2 -> g", "lines": info["lines"],
            "M_exact": info["M_exact"], "M2": r["M2"], "grams": _answer(r["result"], "4.87")}


def case_formb_2():
    r = convert("g->atoms", "5.0", "Na", "Na")
    return {"input": "5.0 g Na -> atoms", "M2": r["M2"], "mol": r["mol"],
            "atoms": _answer(r["result"], "5.0")}


def case_formb_3():
    r = convert("g->atoms", "550", "Al2(SO4)3", "Al")
    info = parse("Al2(SO4)3")
    return {"input": "550 g Al2(SO4)3 -> Al ions", "lines": info["lines"], "M2": r["M2"],
            "count_Al": r["count"], "mol": r["mol"], "mol_Al": r["mol_element"],
            "ions": _answer(r["result"], "550")}


def case_formb_4():
    return {"input": "60.0% C, 4.48% H, 35.5% O; MM 540",
            **empirical([("C", "60.0"), ("H", "4.48"), ("O", "35.5")], molar_mass="540")}


def case_formb_5():
    return {"input": "19.06 g -> 15.07 g CaSO4", **hydrate_from_heating("19.06", "15.07", "CaSO4")}


def case_formb_6():
    r = same_moles("2.40", "g", "CO2", "particles", "H2O")
    return {"input": "2.40 g CO2 -> molecules H2O (same moles)", "M2_A": r["M2_A"],
            "mol": r["mol"], "molecules": _answer(r["result"], "2.40")}


def case_pct_co2():
    return percent_composition("CO2")


def case_pct_h2o():
    return percent_composition("H2O")


def case_pct_water_cuso4_5h2o():
    r = percent_water("CuSO4*5H2O")
    r["percent_display"] = show(r["percent"])
    return r


def _caps_case(text, choices):
    f, log = resolve_caps_detailed(text, choices)
    return {"input": text, "choices": choices, "formula": f, "ambiguities": log,
            "M2": parse(f)["M2"]}


def case_caps_al2so43():
    return _caps_case("AL2(SO4)3", [])


def case_caps_nacl():
    return _caps_case("NACL", [])


def case_caps_caco3():
    return _caps_case("CACO3", [2])


def case_caps_sn_acetate():
    return _caps_case("SN(C2H3O2)2", [1])


FMT_EXAMPLES = [
    ((18.016, 2, 2), "18.02"), ((32, 2, 2), "32.00"), ((0.5, 2, 2), "0.50"),
    (("1153.17", 3, 0), "1.15ᴇ3"), (("1153.17", 4, 0), "1153"), (("1150", 4, 0), "1.150ᴇ3"),
    (("1.99822", 3, 0), "2.00"), (("0.054533", 3, 0), "0.0545"), (("3.2840e22", 3, 0), "3.28ᴇ22"),
    (("342.17", 10, 1), "342.17"), (("192", 10, 1), "192"),
    (("0.2174858634", 10, 1), "0.2174858634"), (("1.3097e23", 10, 1), "1.3097ᴇ23"),
    (("16", 4, 0), "16.00"), ((0, 5, 1), "0"),
]
SIGFIG_EXAMPLES = [("5.0", 2), ("36.0", 3), ("550", 2), ("4.87", 3), ("0.500", 3),
                   ("6.022ᴇ23", 4), ("100.", 3), ("105", 3), ("0.00500", 3)]


def case_fmt_examples():
    return {f"fmt({a[0]},{a[1]},{a[2]})": fmt(*a) for a, _ in FMT_EXAMPLES}


def case_sigfig_examples():
    return {s: sigfigs(s) for s, _ in SIGFIG_EXAMPLES}


CASES = {name[5:]: fn for name, fn in globals().items()
         if name.startswith("case_") and callable(fn)}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _jsonable(o):
    if isinstance(o, Decimal):
        return str(o)
    if isinstance(o, dict):
        return {str(k): _jsonable(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_jsonable(v) for v in o]
    return o


def _dump(obj) -> str:
    return json.dumps(_jsonable(obj), ensure_ascii=False, indent=2)


def _flatten(obj, prefix=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from _flatten(v, f"{prefix}.{k}" if prefix else str(k))
    elif isinstance(obj, (list, tuple)) and any(isinstance(v, (dict, list, tuple)) for v in obj):
        for i, v in enumerate(obj):
            yield from _flatten(v, f"{prefix}[{i}]")
    else:
        yield prefix, obj


def _fmt_value(v):
    if isinstance(v, Decimal):
        return f"{v}   (~{show(v)})"
    if isinstance(v, (list, tuple)):
        return "[" + ", ".join(str(x) for x in v) + "]"
    return str(v)


def main(argv: list[str]) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    if not argv or argv[0] in ("-h", "--help", "help"):
        print(__doc__)
        return 0
    cmd, args = argv[0], argv[1:]
    if cmd == "list":
        print("\n".join(CASES))
    elif cmd == "case":
        if len(args) != 1 or args[0] not in CASES:
            print("usage: oracle.py case NAME   (names: " + ", ".join(CASES) + ")", file=sys.stderr)
            return 2
        for k, v in _flatten(CASES[args[0]]()):
            print(f"{k}: {_fmt_value(v)}")
    elif cmd == "all":
        print(_dump({name: fn() for name, fn in CASES.items()}))
    elif cmd == "parse" and len(args) == 1:
        print(_dump(parse(args[0])))
    elif cmd == "caps" and args:
        f, log = resolve_caps_detailed(args[0], args[1:])
        print(_dump({"formula": f, "ambiguities": log}))
    elif cmd == "fmt" and len(args) == 3:
        print(fmt(args[0], int(args[1]), int(args[2])))
    elif cmd == "sigfigs" and len(args) == 1:
        print(sigfigs(args[0]))
    else:
        print(__doc__, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except ValueError as exc:      # includes AmbiguityError
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(3)
