"""Tests for prgmZTOOLS (PHYSOLVE page 2 options 3-6: VECTOR COMPONENTS, AVG SPEED/VELOCITY,
FACTOR OF CHANGE, LAB TOOLS), driven through PHYSOLVE's real menus.

Every run starts at PHYSOLVE page 1, picks 6 (MORE >) and the tool, walks the tool's own menus,
types the inputs, leaves the tool with its BACK option and quits PHYSOLVE (page 2 option 7 + page 1
option 7), so assert_clean() can check that the program ended without errors, leaks, scrolling,
truncated lines or empty strings. Every Pause screen of each calculation is compared with
reference/ztools.py row by row (the reference rebuilds every row, formatting numbers with fmt3),
every "NAME = VALUE" value is compared with fmt3(reference), and the required/typical cases are
also compared with values computed by hand (independently of the reference) at 3 significant
figures. The screen shown while typing (the explanation + prompts) is checked too.
"""
import os
import math
import random
import re
import sys

from harness import Checker, run, assert_clean, fmt3, sim
from tisim import ScriptEnd

import ztools as ref  # noqa: E402  (reference/ is on sys.path via harness)

c = Checker("ZTOOLS")

P1 = "PHYSOLVE 1/2  KINEMATICS"
P2 = "PHYSOLVE 2/2  KINEMATICS"
VEC, UNIT, FAC, LAB = "VECTOR COMPONENTS", "WHAT KIND OF VECTOR?", "FACTOR OF CHANGE", "LAB TOOLS"
YDM, SPD = "YARDS AND METERS", "SPEED TO M/S"
NUM = r"-?[0-9]+(?:\.[0-9]+)?(?:E-?[0-9]+)?"
VAL_RE = re.compile(r"^(.+?) = (" + NUM + r")(.*)$")
NUM_RE = re.compile(NUM)

# menu choices that start one calculation (the screens after them belong to that calculation)
STARTS = {(UNIT, k) for k in (1, 2, 3, 4)} | {(P2, 4)} | {(FAC, k) for k in (1, 2, 3, 4, 5)} | \
         {(LAB, k) for k in (1, 2, 3)} | {(YDM, 1), (YDM, 2), (SPD, 1), (SPD, 2)}


# ------------------------------------------------------------------------------ calculations
def calc(kind, *args):
    """(reference Result, keys from page 2 to the inputs, inputs typed, keys back to page 2,
    menu path inside the tool)."""
    if kind == "vec1":
        unit, m, n = args
        return (ref.vector_mag_angle(unit, m, n), [3, 1, unit], [m, n], [3],
                [(P2, 3), (VEC, 1), (UNIT, unit), (VEC, 3)])
    if kind == "vec2":
        unit, p, q = args
        return (ref.vector_xy(unit, p, q), [3, 2, unit], [p, q], [3],
                [(P2, 3), (VEC, 2), (UNIT, unit), (VEC, 3)])
    if kind == "avg":
        n, legs = args
        flat = [n] + [x for leg in legs for x in leg]
        return ref.averages(n, legs), [4], flat, [], [(P2, 4)]
    if kind == "fac":
        rel, old, k = args
        return ref.factor(rel, old, k), [5, rel], [old, k], [6], [(P2, 5), (FAC, rel), (FAC, 6)]
    lab = {"ramp": (ref.ramp, [1], []), "pdiff": (ref.pct_diff, [2], []), "perr": (ref.pct_error, [3], []),
           "yd2m": (ref.yd_to_m, [4, 1], [YDM]), "m2yd": (ref.m_to_yd, [4, 2], [YDM]),
           "kmh": (ref.kmh_to_ms, [5, 1], [SPD]), "mph": (ref.mph_to_ms, [5, 2], [SPD])}
    fn, keys, sub = lab[kind]
    path = [(P2, 6), (LAB, keys[0])] + ([(sub[0], keys[1])] if sub else []) + [(LAB, 6)]
    return fn(*args), [6] + keys, list(args), [6], path


def script_for(kind, *args):
    rr, menu_keys, inputs, back, path = calc(kind, *args)
    keys = [6] + menu_keys + inputs[:len(rr.prompts)] + back + [7, 7]
    return keys, rr, [(P1, 6)] + path + [(P2, 7), (P1, 7)]


def drive(keys, **kw):
    """Run PHYSOLVE with `keys`; also record the screen shown at each Input prompt."""
    keys = list(keys)
    shots = []

    def responder(kind, info):
        if kind == "input":
            shots.append((info, [r for r in sim().screen if r.strip()]))
        if not keys:
            raise ScriptEnd()
        return keys.pop(0)

    res = run([], responder=responder, **kw)
    return res, shots


def rows_of(screen):
    return [row.rstrip() for row in screen if row.strip()]


def values_of(screen):
    """[(name, value_str, tail)] for every 'NAME = VALUE...' row."""
    out = []
    for row in rows_of(screen):
        m = VAL_RE.match(row)
        if m:
            out.append((m.group(1).strip(), m.group(2), m.group(3)))
    return out


def screen_dict(screen):
    return {n: v for n, v, t in values_of(screen)}


def segments(res):
    """Screens of each calculation: between a STARTS menu choice and the next menu."""
    segs, cur = [], None
    for e in res.events:
        if e[0] == "menu":
            cur = None
            if (e[1], e[3]) in STARTS:
                cur = []
                segs.append(cur)
        elif e[0] == "screen" and cur is not None:
            cur.append(e[1])
    return segs


def close3(shown, x):
    """shown == fmt3(x), allowing a one-digit difference only when x sits on a 3-s.f. rounding edge
    (the calculator's 14-digit decimals and Python's binary floats can round such a value apart)."""
    if isinstance(x, str):
        return shown == x
    if shown == fmt3(x):
        return True
    return any(shown == fmt3(float(x) * f) for f in (1 + 1e-10, 1 - 1e-10))


def numbers_close(a, b):
    """Two rows that differ only in numbers equal to ~3 significant figures (fuzz only)."""
    if NUM_RE.sub("#", a) != NUM_RE.sub("#", b):
        return False
    for x, y in zip(NUM_RE.findall(a), NUM_RE.findall(b)):
        fx, fy = float(x), float(y)
        if fx != fy and abs(fx - fy) > 0.0101 * max(abs(fx), abs(fy)) and max(abs(fx), abs(fy)) > 2e-9:
            return False
    return True


def compare_screens(screens, rr, ctx, exact=True):
    """Simulator screens vs reference Result: same screens, same rows, values == fmt3(reference)."""
    got_titles = [rows_of(s)[0] if rows_of(s) else "" for s in screens]
    want_titles = [s.title for s in rr.screens]
    assert got_titles == want_titles, f"{ctx}: screen titles {got_titles}\n  expected {want_titles}"
    for scr, want in zip(screens, rr.screens):
        got_rows = rows_of(scr)
        assert len(got_rows) == len(want.rows), \
            f"{ctx}: screen {want.title!r} has {len(got_rows)} rows, reference {len(want.rows)}\n  " + \
            "\n  ".join(got_rows) + "\n  ---\n  " + "\n  ".join(want.rows)
        for g, w in zip(got_rows, want.rows):
            w = w.rstrip()          # a row ending in Str4=" " (no unit) shows a trailing space
            ok = (g == w) if exact else (g == w or numbers_close(g, w))
            assert ok, f"{ctx}: screen {want.title!r}\n  row   {g!r}\n  wants {w!r}"
        got_vals = [(n, v, t.rstrip()) for n, v, t in values_of(scr)]
        want_vals = [(n, x, t.rstrip()) for n, x, t in want.values]
        assert [(n, t) for n, v, t in got_vals] == [(n, t) for n, x, t in want_vals], \
            f"{ctx}: value rows {got_vals}\n  reference {want.values}"
        for (n, v, t), (_, x, _) in zip(got_vals, want_vals):
            ok = (v == (x if isinstance(x, str) else fmt3(x))) if exact else close3(v, x)
            assert ok, f"{ctx}: {want.title!r} {n} shows {v!r}, reference {x!r}"


def one_calc(kind, *args, exact=True, ctx=None, **kw):
    """Run one calculation through PHYSOLVE; check clean run, menu path, prompts, the input screens
    and every result screen against the reference."""
    ctx = ctx or f"{kind}{args}"
    keys, rr, path = script_for(kind, *args)
    res, shots = drive(keys, **kw)
    assert_clean(res, context=ctx)
    menus = [(e[1], e[3]) for e in res.events if e[0] == "menu"]
    assert menus == path, f"{ctx}: menu path {menus}\n  expected {path}"
    prompts = [p for p, _ in shots]
    assert prompts == rr.prompts, f"{ctx}: prompts {prompts}, reference {rr.prompts}"
    # the explanation screen is on show when the first prompt of each input screen appears
    first = shots[0][1]
    assert first == rr.info, f"{ctx}: input screen\n  " + "\n  ".join(first) + "\n  ---\n  " + "\n  ".join(rr.info)
    if kind == "avg":
        legs_seen = [rows for p, rows in shots if p == "DISTANCE (M)="]
        assert legs_seen == rr.leg_info[:len(legs_seen)], f"{ctx}: leg screens {legs_seen}"
    segs = segments(res)
    assert len(segs) == 1, f"{ctx}: {len(segs)} calculations"
    compare_screens(segs[0], rr, ctx, exact=exact)
    assert res.angle == "Degree"
    return res, rr, segs[0]


def by_title(screens, title):
    for s in screens:
        if rows_of(s) and rows_of(s)[0] == title:
            return s
    raise AssertionError(f"no screen titled {title!r}: {[rows_of(s)[:1] for s in screens]}")


def expect_values(got, want, ctx):
    for k, v in want.items():
        assert k in got, f"{ctx}: no {k!r} on the screen: {got}"
        assert got[k] == v, f"{ctx}: {k} shows {got[k]!r}, hand-computed {v!r}"


def expect_rows(screen, rows, ctx):
    have = rows_of(screen)
    for row in rows:
        assert row in have, f"{ctx}: missing row {row!r}:\n  " + "\n  ".join(have)


def message_only(kind, *args, label):
    """An impossible/edge input: exactly one screen, the message, then back to the tool's menu."""
    res, rr, scr = one_calc(kind, *args, ctx=f"{kind}{args} -> {label}")
    assert rr.messages == [label], f"{kind}{args}: reference messages {rr.messages}, expected {label}"
    assert len(scr) == 1, f"{kind}{args}: {len(scr)} screens"
    if label in ref.MESSAGES:
        assert rows_of(scr[0]) == list(ref.MESSAGES[label]), rows_of(scr[0])
    for row in rows_of(scr[0]):
        if label != "H9":
            assert not VAL_RE.match(row), f"message row looks like a value: {row!r}"
    return scr[0]


SUM_V1 = "SUMMARY  MAG,ANGLE TO X,Y"
SUM_V2 = "SUMMARY  X,Y TO MAG,ANGLE"


# ------------------------------------------------------------------------------ setup / static
def t_syntax():
    """harness.sim() refuses to load if ANY program has a syntax error; ZTOOLS and its helpers must be clean."""
    mine = ("ZTOOLS", "PHYSOLVE", "ZFMT", "ZLINE")
    try:
        sim()
    except AssertionError as e:
        lines = str(e).splitlines()[1:]
        bad = [ln for ln in lines if ln.split(":")[0] in mine]
        assert not bad, "\n".join(bad)


def t_static_layout():
    """Explanation rows + prompts fit the 10-row screen; message rows fit 26 columns and are prose."""
    pairs = [("MAG_ANGLE", "MAG_ANGLE"), ("XY", "XY"), ("AVG", "LEGS"), ("J1", "J1"), ("J2", "J2"),
             ("J3", "J3"), ("J4", "J4"), ("J5", "J5"), ("RAMP", "RAMP"), ("PDIFF", "PDIFF"),
             ("PERR", "PERR"), ("YD2M", "YD2M"), ("M2YD", "M2YD"), ("KMH", "KMH"), ("MPH", "MPH")]
    for info, pr in pairs:
        assert len(ref.INFO[info]) + len(ref.PROMPTS[pr]) <= 10, info
        for row in ref.INFO[info]:
            assert len(row) <= 26 and not VAL_RE.match(row), (info, row)
        for p in ref.PROMPTS[pr]:
            assert len(p) <= 18, p
    assert 1 + len(ref.INFO["LEG"]) + len(ref.PROMPTS["LEG"]) <= 10
    # SPEC 7b: every input screen whose prompts accept a negative number shows the (-) key hint
    # (J3 only takes a fall time and a factor K, both >= 0; AVG only takes the number of legs)
    for info in ("MAG_ANGLE", "XY", "LEG", "J1", "J2", "J4", "J5", "RAMP", "PDIFF", "PERR", "YD2M", "M2YD",
                 "KMH", "MPH"):
        assert "NEGATIVE = (-) KEY" in ref.INFO[info], f"{info}: no NEGATIVE = (-) KEY row"
    # "proportional to" is always written PROP TO
    for info, rows in ref.INFO.items():
        for row in rows:
            assert "PROP " not in row or "PROP TO " in row, (info, row)
    assert "S=-V0²/(2A), S PROP TO V²." in ref.INFO["J1"]
    for label, rows in ref.MESSAGES.items():
        assert len(rows) <= 9, label
        for row in rows:
            assert len(row) <= 26 and not VAL_RE.match(row), (label, row)
    for title, items in ref.MENUS.items():
        assert len(items) <= 7 and items[-1] == "BACK" and len(title) <= 24, title
        assert all(len(t) <= 22 for t in items), items


# ------------------------------------------------------------------------------ H. vectors
def t_vec_required_examples():
    # 20 at 30 deg: X = 20 cos 30 = 17.32, Y = 20 sin 30 = 10
    res, rr, scr = one_calc("vec1", 1, 20, 30)
    s = by_title(scr, SUM_V1)
    expect_values(screen_dict(s), {"MAGNITUDE": "20.0", "ANGLE": "30.0", "X": "17.3", "Y": "10.0"}, "20@30")
    expect_rows(s, ["X = 17.3 M (RIGHT)", "Y = 10.0 M (UP)", "ANGLE = 30.0°", "(COUNTERCLOCKWISE FROM +X)"], "20@30")
    expect_rows(by_title(scr, "STEP 1  X COMPONENT"), ["ANGLE IS FROM +X, SO X IS", "THE ADJACENT SIDE (COS)-",
                                                       "X=MAGNITUDE*COS(ANGLE)", "X=(20.0)COS(30.0°)",
                                                       "X = 17.3 M (RIGHT)"], "step 1")
    expect_rows(by_title(scr, "STEP 2  Y COMPONENT"), ["ANGLE IS FROM +X, SO Y IS", "THE OPPOSITE SIDE (SIN)-",
                                                       "Y=MAGNITUDE*SIN(ANGLE)", "Y=(20.0)SIN(30.0°)",
                                                       "Y = 10.0 M (UP)"], "step 2")
    # the reason row comes before the equation on both step screens
    for title, why, eq in [("STEP 1  X COMPONENT", "THE ADJACENT SIDE (COS)-", "X=MAGNITUDE*COS(ANGLE)"),
                           ("STEP 2  Y COMPONENT", "THE OPPOSITE SIDE (SIN)-", "Y=MAGNITUDE*SIN(ANGLE)")]:
        rows = rows_of(by_title(scr, title))
        assert rows.index(why) < rows.index(eq), rows
    assert screen_dict(s)["X"] == fmt3(20 * math.cos(math.radians(30)))
    # 120 deg points up and to the left: X = 10 cos 120 = -5, Y = 10 sin 120 = 8.660
    res, rr, scr = one_calc("vec1", 2, 10, 120)
    expect_rows(by_title(scr, SUM_V1), ["X = -5.00 M/S (LEFT)", "Y = 8.66 M/S (UP)", "MAGNITUDE = 10.0 M/S"], "10@120")


def t_vec_mag_angle_hand():
    cases = [  # (m, angle) -> X, Y shown, direction words
        ((15, 0), "15.0", "0", " (RIGHT)", ""), ((15, 90), "0", "15.0", "", " (UP)"),
        ((15, 180), "-15.0", "0", " (LEFT)", ""), ((15, 270), "0", "-15.0", "", " (DOWN)"),
        ((15, -90), "0", "-15.0", "", " (DOWN)"), ((12, 225), "-8.49", "-8.49", " (LEFT)", " (DOWN)"),
        ((12, 360), "12.0", "0", " (RIGHT)", ""), ((12, -360), "12.0", "0", " (RIGHT)", ""),
        ((25, 36.87), "20.0", "15.0", " (RIGHT)", " (UP)"), ((0, 45), "0", "0", "", ""),
        ((9.8, -30), "8.49", "-4.90", " (RIGHT)", " (DOWN)"), ((50, 300), "25.0", "-43.3", " (RIGHT)", " (DOWN)"),
    ]
    for (m, n), x, y, wx, wy in cases:
        res, rr, scr = one_calc("vec1", 3, m, n)
        s = by_title(scr, SUM_V1)
        expect_rows(s, [f"X = {x} M/S²{wx}", f"Y = {y} M/S²{wy}"], (m, n))
        # independent formulas
        assert screen_dict(s)["X"] == fmt3(m * math.cos(math.radians(n))) or x == "0"
        assert screen_dict(s)["Y"] == fmt3(m * math.sin(math.radians(n))) or y == "0"


def t_vec_units():
    for unit, tail in [(1, " M"), (2, " M/S"), (3, " M/S²"), (4, " ")]:
        res, rr, scr = one_calc("vec1", unit, 20, 30)
        expect_rows(by_title(scr, SUM_V1), [f"MAGNITUDE = 20.0{tail}".rstrip(), f"X = 17.3{tail.rstrip()} (RIGHT)"],
                    unit)
        res, rr, scr = one_calc("vec2", unit, 3, 4)
        expect_rows(by_title(scr, SUM_V2), [f"MAGNITUDE = 5.00{tail}".rstrip(), f"X = 3.00{tail}".rstrip()], unit)


def t_vec_no_unit_words():
    """OTHER (NO UNIT): the direction word follows the number after ONE space (Str4 is " ")."""
    cases = [((20, 120), "X = -10.0 (LEFT)", "Y = 17.3 (UP)"), ((20, 30), "X = 17.3 (RIGHT)", "Y = 10.0 (UP)"),
             ((10, -60), "X = 5.00 (RIGHT)", "Y = -8.66 (DOWN)"), ((10, 180), "X = -10.0 (LEFT)", "Y = 0"),
             ((10, 270), "X = 0", "Y = -10.0 (DOWN)")]
    for (m, n), xrow, yrow in cases:
        res, rr, scr = one_calc("vec1", 4, m, n)
        expect_rows(by_title(scr, "STEP 1  X COMPONENT"), [xrow], (m, n))
        expect_rows(by_title(scr, "STEP 2  Y COMPONENT"), [yrow], (m, n))
        expect_rows(by_title(scr, SUM_V1), [xrow, yrow], (m, n))
        for sc in scr:
            for row in rows_of(sc):
                assert "  (" not in row, f"double space in {row!r}"
    # with a unit the word still has its space: "X = -10.0 M (LEFT)"
    res, rr, scr = one_calc("vec1", 1, 20, 120)
    expect_rows(by_title(scr, SUM_V1), ["X = -10.0 M (LEFT)", "Y = 17.3 M (UP)"], "unit M")


def t_vec_xy_quadrants():
    # (x, y) -> magnitude, reference angle, angle 0..360, clockwise row, description, quadrant row, rule row
    cases = [
        ((3, 4), "5.00", "53.1", "53.1", None, "53.1° ABOVE +X", "QUADRANT I (X>0, Y>0)", "ANGLE=REF=53.1"),
        ((-3, 4), "5.00", "53.1", "127", None, "53.1° ABOVE -X", "QUADRANT II (X<0, Y>0)", "ANGLE=180-REF=180-53.1"),
        ((-3, -4), "5.00", "53.1", "233", "OR -127° (CLOCKWISE)", "53.1° BELOW -X", "QUADRANT III (X<0, Y<0)",
         "ANGLE=180+REF=180+53.1"),
        ((4, -3), "5.00", "36.9", "323", "OR -36.9° (CLOCKWISE)", "36.9° BELOW +X", "QUADRANT IV (X>0, Y<0)",
         "ANGLE=360-REF=360-36.9"),
        ((5, 0), "5.00", "0", "0", None, "ALONG +X (RIGHT)", "ON THE +X AXIS (Y IS 0)", "+X IS 0°"),
        ((-5, 0), "5.00", "0", "180", None, "ALONG -X (LEFT)", "ON THE -X AXIS (Y IS 0)", "-X IS 180°"),
        ((0, 7), "7.00", "90.0", "90.0", None, "STRAIGHT UP (ALONG +Y)", "ON THE +Y AXIS (X IS 0)", "+Y IS 90°"),
        ((0, -7), "7.00", "90.0", "270", "OR -90.0° (CLOCKWISE)", "STRAIGHT DOWN (ALONG -Y)",
         "ON THE -Y AXIS (X IS 0)", "-Y IS 270°"),
        ((12, 5), "13.0", "22.6", "22.6", None, "22.6° ABOVE +X", "QUADRANT I (X>0, Y>0)", "ANGLE=REF=22.6"),
        ((-8, 6), "10.0", "36.9", "143", None, "36.9° ABOVE -X", "QUADRANT II (X<0, Y>0)", "ANGLE=180-REF=180-36.9"),
    ]
    for (x, y), mag, refa, ang, cw, words, quad, rule in cases:
        ctx = f"({x},{y})"
        res, rr, scr = one_calc("vec2", 1, x, y)
        # independent: magnitude = hypot, angle = atan2 mapped to 0..360
        h_ang = math.degrees(math.atan2(y, x)) % 360
        h_ref = math.degrees(math.atan2(abs(y), abs(x)))
        assert mag == fmt3(math.hypot(x, y)) and ang == fmt3(h_ang) and refa == fmt3(h_ref), ctx
        s = by_title(scr, SUM_V2)
        expect_values(screen_dict(s), {"MAGNITUDE": mag, "ANGLE": ang}, ctx)
        want = [f"MAGNITUDE = {mag} M", f"ANGLE = {ang}°", "(CCW FROM +X, 0 TO 360)", words]
        expect_rows(s, want + ([cw] if cw else []), ctx)
        assert (cw is None) == (not any(r.startswith("OR ") for r in rows_of(s))), ctx
        s3 = by_title(scr, "STEP 3  ANGLE FROM +X")
        expect_rows(s3, [quad, rule, f"ANGLE = {ang}°", words] + ([cw] if cw else []), ctx)
        s2 = by_title(scr, "STEP 2  REFERENCE ANGLE")
        expect_values(screen_dict(s2), {"REF ANGLE": refa}, ctx)
        sub = "X IS 0, SO REF IS 90°" if x == 0 else f"=TAN⁻1({fmt3(abs(y))}/{fmt3(abs(x))})"
        expect_rows(s2, ["REF=TAN⁻1(|Y|/|X|)", sub], ctx)
        s1 = by_title(scr, "STEP 1  MAGNITUDE")
        expect_rows(s1, ["MAGNITUDE=√(X²+Y²)", f"=√(({fmt3(x)})²+({fmt3(y)})²)", f"MAGNITUDE = {mag} M"], ctx)


def t_vec_round_trip():
    """Components from (M, angle), then back again, give M and the angle (0..360) again."""
    rng = random.Random(5)
    for _ in range(12):
        m = round(rng.uniform(1, 80), 1)
        n = round(rng.uniform(-359, 359), 1)
        x, y = m * math.cos(math.radians(n)), m * math.sin(math.radians(n))
        res, rr, scr = one_calc("vec1", 1, m, n, exact=False)
        res2, rr2, scr2 = one_calc("vec2", 1, round(x, 9), round(y, 9), exact=False)
        d = screen_dict(by_title(scr2, SUM_V2))
        assert close3(d["MAGNITUDE"], m), (m, n, d)
        assert close3(d["ANGLE"], n % 360) or (fmt3(n % 360) in ("360", "0") and d["ANGLE"] in ("0", "360")), (m, n, d)


def t_vec_messages():
    message_only("vec1", 1, -5, 30, label="H6")
    message_only("vec1", 1, -1e-99, 0, label="H6")
    message_only("vec1", 2, 5, 361, label="H7")
    message_only("vec1", 2, 5, -400, label="H7")
    message_only("vec1", 3, 5, 9.99e99, label="H7")
    message_only("vec1", 4, -1, 1e99, label="H6")          # the magnitude is checked first
    # ZT-2: a magnitude above 1E9 gets a message (ZFMT itself fails from 9.995E99 up)
    message_only("vec1", 1, 9.995e99, 45, label="HA")
    message_only("vec1", 2, 9.999e99, 45, label="HA")
    message_only("vec1", 3, 9.9999999999999e99, 0, label="HA")
    message_only("vec1", 4, 1000000001, 30, label="HA")
    message_only("vec1", 1, 2e9, 400, label="HA")           # magnitude before angle
    message_only("vec1", 1, -2e9, 30, label="H6")           # sign before size
    message_only("vec2", 1, 2e9, 1, label="H8")
    message_only("vec2", 1, 0, -1.5e9, label="H8")
    message_only("vec2", 1, -9.99e99, 9.99e99, label="H8")
    for unit, tail in [(1, " M"), (2, " M/S"), (3, " M/S²"), (4, " ")]:
        scr = message_only("vec2", unit, 0, 0, label="H9")
        rows = rows_of(scr)
        assert rows[0] == "ZERO VECTOR" and ("MAGNITUDE = 0" + tail).rstrip() in rows and "UNDEFINED." in rows, rows


def t_vec_opposite_advice():
    """H6 tells the student how to point the opposite way; following it never gives the H7 message
    and gives exactly the vector the negative magnitude meant."""
    rows = rows_of(message_only("vec1", 1, -10, 300, label="H6"))
    assert "ANGLE (OR SUBTRACT 180 IF" in rows and "IT IS ABOVE 180) AND USE A" in rows, rows
    for n in [x / 2 for x in range(-720, 721)]:            # every typed angle -360..360 in 0.5 steps
        new = n - 180 if n > 180 else n + 180
        assert abs(new) <= 360, (n, new)
    for m, n in [(10, 300), (10, 200), (10, 181), (10, 180), (10, 90), (10, -300), (4, 360), (4, -360)]:
        new = n - 180 if n > 180 else n + 180
        res, rr, scr = one_calc("vec1", 1, m, new)
        assert rr.messages == [], (n, new, rr.messages)
        d = screen_dict(by_title(scr, SUM_V1))
        assert d["X"] == fmt3(-m * math.cos(math.radians(n))) or d["X"] == "0", (m, n, d)
        assert d["Y"] == fmt3(-m * math.sin(math.radians(n))) or d["Y"] == "0", (m, n, d)
    # the reviewer's sequence: -10 at 300 (message), then 10 at 120 (the advice) on the same visit
    res, shots = drive([6, 3, 1, 1, -10, 300, 1, 1, 10, 120, 3, 7, 7])
    assert_clean(res)
    assert not any("MUST BE FROM" in r for s in res.screens for r in rows_of(s)), res.text()
    expect_rows(res.screens[-1], ["X = -5.00 M (LEFT)", "Y = 8.66 M (UP)"], "advice followed")


def t_vec_edges():
    """Boundaries: no error, values equal the reference."""
    for args in [(1, 0, 0), (1, 1e9, 360), (1, 1e9, -360), (1, 1e-99, 45), (1, 1e9, 89.999999), (4, 1e9, -0.5),
                 (2, 1e-12, 359.9999), (4, 7, 1e-99)]:
        one_calc("vec1", *args, exact=False)
    for args in [(1, 1e9, 1e9), (1, -1e9, -1e9), (1, 1e-99, 0), (1, 0, -1e-99), (1, 1e-12, 1e-12),
                 (1, 1, -1e-13), (1, -1, 1e-13), (1, -1, -1e-13), (1, 1e9, 1e-9), (4, 0.001, -0.002)]:
        one_calc("vec2", *args, exact=False)


# ------------------------------------------------------------------------------ I. averages
S_AVG = "SUMMARY  AVERAGES"


def t_avg_required_example():
    # legs 100 m +, 10 s; 50 m -, 5 s -> distance 150, displacement 50, time 15 -> 10.0 m/s, 3.33 m/s
    res, rr, scr = one_calc("avg", 2, [(100, 1, 10), (50, -1, 5)])
    s = by_title(scr, S_AVG)
    expect_values(screen_dict(s), {"DISTANCE": "150", "DISPLACEMENT": "50.0", "TOTAL TIME": "15.0",
                                   "AVG SPEED": "10.0", "AVG VEL": "3.33"}, "example")
    expect_rows(s, ["DISTANCE = 150 M", "DISPLACEMENT = 50.0 M", "TOTAL TIME = 15.0 S", "AVG SPEED = 10.0 M/S",
                    "AVG VEL = 3.33 M/S", "(IN THE + DIRECTION)"], "example")
    assert screen_dict(s)["AVG VEL"] == fmt3(50 / 15) and screen_dict(s)["AVG SPEED"] == fmt3(150 / 15)
    expect_rows(by_title(scr, "STEP 1  TOTAL DISTANCE"), ["=100+50.0", "DISTANCE = 150 M"], "step 1")
    expect_rows(by_title(scr, "STEP 2  DISPLACEMENT"), ["S=100-50.0", "DISPLACEMENT = 50.0 M"], "step 2")
    expect_rows(by_title(scr, "STEP 3  TOTAL TIME"), ["=10.0+5.00", "TOTAL TIME = 15.0 S"], "step 3")
    expect_rows(by_title(scr, "STEP 4  AVERAGE SPEED"), ["AVG SPEED=DISTANCE/TIME", "=150/15.0",
                                                         "AVG SPEED = 10.0 M/S"], "step 4")
    expect_rows(by_title(scr, "STEP 5  AVERAGE VELOCITY"), ["AVG VEL=DISPLACEMENT/TIME", "=50.0/15.0",
                                                            "AVG VEL = 3.33 M/S"], "step 5")


def t_avg_hand_cases():
    cases = [  # legs -> distance, displacement, time, avg speed, avg vel, direction row
        ([(100, 1, 20), (100, -1, 30)], "200", "0", "50.0", "4.00", "0", "(ENDS WHERE IT STARTED)"),
        ([(30, 1, 10), (40, 1, 20), (100, -1, 30)], "170", "-30.0", "60.0", "2.83", "-0.500", "(IN THE - DIRECTION)"),
        ([(5, 1, 2), (5, 1, 2), (5, -1, 2), (10, -1, 4)], "25.0", "-5.00", "10.0", "2.50", "-0.500",
         "(IN THE - DIRECTION)"),
        ([(100, -1, 9.58)], "100", "-100", "9.58", "10.4", "-10.4", "(IN THE - DIRECTION)"),
        ([(10, 1, 0), (10, 1, 5)], "20.0", "20.0", "5.00", "4.00", "4.00", "(IN THE + DIRECTION)"),
        ([(0, 1, 3), (0, -1, 4)], "0", "0", "7.00", "0", "0", "(ENDS WHERE IT STARTED)"),
        ([(0.1, 1, 1), (0.2, 1, 1), (0.3, -1, 1)], "0.600", "0", "3.00", "0.200", "0", "(ENDS WHERE IT STARTED)"),
    ]
    for legs, dist, disp, time, spd, vel, word in cases:
        ctx = str(legs)
        res, rr, scr = one_calc("avg", len(legs), legs)
        # independent check of the hand numbers
        hd = sum(a for a, b, t in legs)
        hs = sum(a * b for a, b, t in legs)
        ht = sum(t for a, b, t in legs)
        assert (dist, disp, time, spd, vel) == (fmt3(hd), fmt3(hs), fmt3(ht), fmt3(hd / ht), fmt3(hs / ht)), ctx
        s = by_title(scr, S_AVG)
        expect_values(screen_dict(s), {"DISTANCE": dist, "DISPLACEMENT": disp, "TOTAL TIME": time,
                                       "AVG SPEED": spd, "AVG VEL": vel}, ctx)
        assert rows_of(s)[-1] == word, (ctx, rows_of(s))
        assert rows_of(by_title(scr, "STEP 5  AVERAGE VELOCITY"))[-1] == word


def t_avg_four_legs_one_row():
    """4 legs of ordinary numbers: each sum line fits ONE row (ZLINE does not cut a number in two)."""
    cases = [
        ([(50, 1, 10), (50, -1, 12.5), (25, 1, 6.5), (75, -1, 0.5)],
         "=50.0+50.0+25.0+75.0", "S=50.0-50.0+25.0-75.0", "=10.0+12.5+6.50+0.500"),
        ([(2, 1, 0.5), (2, 1, 0.5), (2, -1, 0.5), (2, 1, 0.5)],
         "=2.00+2.00+2.00+2.00", "S=2.00+2.00-2.00+2.00", "=0.500+0.500+0.500+0.500"),
        ([(0.125, -1, 0.25), (0.375, -1, 0.75), (0.5, -1, 0.125), (0.625, -1, 0.875)],
         "=0.125+0.375+0.500+0.625", "S=-0.125-0.375-0.500-0.625", "=0.250+0.750+0.125+0.875"),
        ([(1500, 1, 120), (2500, -1, 340), (999, 1, 60), (4200, -1, 300)],
         "=1500+2500+999+4200", "S=1500-2500+999-4200", "=120+340+60.0+300"),
    ]
    for legs, dist, disp, time in cases:
        res, rr, scr = one_calc("avg", 4, legs)
        for title, row in [("STEP 1  TOTAL DISTANCE", dist), ("STEP 2  DISPLACEMENT", disp),
                           ("STEP 3  TOTAL TIME", time)]:
            rows = rows_of(by_title(scr, title))
            assert len(row) <= 26 and row in rows, (title, row, rows)
            assert rows[rows.index(row) + 1].split(" = ")[0] in ("DISTANCE", "DISPLACEMENT", "TOTAL TIME"), rows


def t_avg_messages():
    for n in (0, 5, 2.5, -1, 1e99, 0.999):
        message_only("avg", n, [], label="I2")
    message_only("avg", 2, [(-5, 1, 3)], label="I3")
    message_only("avg", 2, [(5, 2, 3)], label="I4")
    message_only("avg", 2, [(5, 0, 3)], label="I4")
    message_only("avg", 1, [(5, 0.5, 3)], label="I4")
    message_only("avg", 3, [(5, -2, 3)], label="I4")
    message_only("avg", 2, [(5, 1, -3)], label="I5")
    message_only("avg", 2, [(2e9, 1, 3)], label="I6")
    message_only("avg", 2, [(5, 1, 1.5e9)], label="I6")
    message_only("avg", 1, [(10, 1, 0)], label="I7")          # zero total time
    message_only("avg", 3, [(1, 1, 0), (2, -1, 0), (3, 1, 0)], label="I7")
    message_only("avg", 1, [(10, 1, 1e-10)], label="I7")
    # an impossible leg after a good one: the message comes right after that leg is typed
    message_only("avg", 3, [(10, 1, 2), (5, 3, 1)], label="I4")
    message_only("avg", 4, [(10, 1, 2), (5, 1, 1), (-1, 1, 1)], label="I3")
    message_only("avg", 4, [(10, 1, 2), (5, 1, 1), (1, 1, 1), (1, 1, -1)], label="I5")


def t_avg_edges():
    for legs in [[(1e9, 1, 1e9)] * 4, [(1e9, -1, 1e-9)], [(1e-99, 1, 1e-9)], [(1e9, 1, 1e-9), (1e9, 1, 1e-9)],
                 [(0, 1, 1e9)], [(999999999.5, 1, 1), (999999999.5, -1, 1)]]:
        one_calc("avg", len(legs), legs, exact=False)


# ------------------------------------------------------------------------------ J. factor of change
S_FAC = "SUMMARY  FACTOR OF CHANGE"


def t_fac_required_examples():
    # stopping distance 20 m, speed x3 -> 20 * 3^2 = 180 m
    res, rr, scr = one_calc("fac", 1, 20, 3)
    s = by_title(scr, S_FAC)
    expect_values(screen_dict(s), {"OLD S": "20.0", "V FACTOR K": "3.00", "MULTIPLIER": "9.00", "NEW S": "180"}, "stop")
    expect_rows(s, ["S PROP TO V²", "NEW S = 180 M", "3.00X V GIVES 9.00X S"], "stop")
    expect_rows(by_title(scr, "STEP 1  MULTIPLIER"), ["V IS MULTIPLIED BY K, SO", "S IS MULTIPLIED BY K²",
                                                      "MULTIPLIER=K²", "=(3.00)²", "MULTIPLIER = 9.00"], "stop 1")
    expect_rows(by_title(scr, "STEP 2  NEW S"), ["NEW S=OLD S*K²", "NEW S=(20.0)(9.00)", "NEW S = 180 M"], "stop 2")
    # fall time 2.0 s, height x4 -> 2.0 * sqrt(4) = 4.00 s
    res, rr, scr = one_calc("fac", 3, 2.0, 4)
    s = by_title(scr, S_FAC)
    expect_values(screen_dict(s), {"OLD T": "2.00", "H FACTOR K": "4.00", "MULTIPLIER": "2.00", "NEW T": "4.00"}, "fall")
    expect_rows(s, ["T PROP TO √(H)", "NEW T = 4.00 S", "4.00X H GIVES 2.00X T"], "fall")
    expect_rows(by_title(scr, "STEP 1  MULTIPLIER"), ["MULTIPLIER=√(K)", "=√(4.00)"], "fall 1")


def t_fac_hand_cases():
    cases = [  # (rel, old, k) -> multiplier, new, unit, relationship row
        ((1, 30, 0.5), "0.250", "7.50", " M", "S PROP TO V²"),
        ((1, 20, 0), "0", "0", " M", "S PROP TO V²"),
        ((2, 5, 2), "4.00", "20.0", " M", "S PROP TO T²"),
        ((2, 12, 0.5), "0.250", "3.00", " M", "S PROP TO T²"),
        ((3, 3, 2), "1.41", "4.24", " S", "T PROP TO √(H)"),
        ((3, 0, 9), "3.00", "0", " S", "T PROP TO √(H)"),
        ((4, 10, 9), "3.00", "30.0", " M/S", "V PROP TO √(H)"),
        ((4, -14, 2), "1.41", "-19.8", " M/S", "V PROP TO √(H)"),
        ((5, -9.8, 3), "3.00", "-29.4", " M/S", "V PROP TO T"),
        ((5, 4, 0.25), "0.250", "1.00", " M/S", "V PROP TO T"),
    ]
    power = {1: 2, 2: 2, 3: 0.5, 4: 0.5, 5: 1}
    for (rel, old, k), mult, new, unit, rule in cases:
        ctx = (rel, old, k)
        assert mult == fmt3(k ** power[rel]) and new == fmt3(old * k ** power[rel]), ctx   # independent
        res, rr, scr = one_calc("fac", rel, old, k)
        s = by_title(scr, S_FAC)
        q = ref.RELATIONS[rel][0]
        expect_values(screen_dict(s), {"MULTIPLIER": mult, f"NEW {q}": new}, ctx)
        expect_rows(s, [rule, f"NEW {q} = {new}{unit}"], ctx)


def t_fac_negative_old_s():
    """J1/J2 accept a negative old S (a drop has S < 0, up is +); the input screen shows the (-) hint."""
    res, rr, scr = one_calc("fac", 2, -4.9, 2)          # dropped 1 s: S = -4.9 m; at 2 s: S = -19.6 m
    expect_rows(by_title(scr, S_FAC), ["OLD S = -4.90 M", "NEW S = -19.6 M"], "drop")
    assert fmt3(-4.9 * 2 ** 2) == "-19.6"
    expect_rows(by_title(scr, "STEP 2  NEW S"), ["NEW S=(-4.90)(4.00)", "NEW S = -19.6 M"], "drop 2")
    res, rr, scr = one_calc("fac", 1, -20, 3)           # stopping while moving the - way
    expect_rows(by_title(scr, S_FAC), ["NEW S = -180 M"], "stop -")
    for rel in (1, 2):
        keys, rr, path = script_for("fac", rel, -4.9, 2)
        res, shots = drive(keys)
        assert_clean(res)
        info = shots[0][1]
        assert info[-1] == "NEGATIVE = (-) KEY" and len(info) + len(rr.prompts) == 10, info
    assert "(A DROP HAS S<0, UP IS +)" in ref.INFO["J2"]


def t_negative_hint_on_screen():
    """At every prompt that accepts a negative, the (-) hint row is on the screen (SPEC 7b)."""
    runs = [("vec1", (1, 20, -30)), ("vec2", (1, -3, -4)), ("avg", (1, [(5, -1, 2)])), ("fac", (1, -20, 3)),
            ("fac", (2, -4.9, 2)), ("fac", (4, -14, 2)), ("fac", (5, -9.8, 3)), ("ramp", (-0.25,)),
            ("pdiff", (-2, -2.2)), ("perr", (-9.0, -9.8)), ("yd2m", (-50,)), ("m2yd", (-100,)), ("kmh", (-72,)),
            ("mph", (-60,))]
    no_neg = {"NUMBER OF LEGS=", "H FACTOR K=", "V FACTOR K=", "T FACTOR K="}
    for kind, args in runs:
        keys, rr, path = script_for(kind, *args)
        res, shots = drive(keys)
        assert_clean(res, context=f"{kind}{args}")
        for prompt, rows in shots:
            if prompt not in no_neg:
                assert "NEGATIVE = (-) KEY" in rows, f"{kind}: prompt {prompt!r} without the hint:\n  " + \
                    "\n  ".join(rows)


def t_fac_messages():
    for rel in (1, 2, 3, 4, 5):
        message_only("fac", rel, 10, -2, label="J6")
        message_only("fac", rel, 10, -1e-99, label="J6")
        message_only("fac", rel, 2e9, 2, label="J7")
        message_only("fac", rel, 5, 1.5e9, label="J7")
    message_only("fac", 3, -2, 4, label="J8")           # a negative fall time
    message_only("fac", 3, -2, -4, label="J8")          # (checked before K)
    message_only("fac", 1, -9.99e99, -9.99e99, label="J6")


def t_fac_edges():
    for args in [(1, 1e9, 1e9), (2, -1e9, 1e9), (3, 1e9, 1e9), (4, -1e9, 1e-99), (5, 1e-99, 1e9),
                 (3, 0, 0), (4, 0, 0), (1, -7, 1e-9)]:
        one_calc("fac", *args, exact=False)


# ------------------------------------------------------------------------------ K. lab tools
def t_lab_required_cases():
    # ramp: slope 0.40 -> a = 2 * 0.40 = 0.80 m/s^2 (shows 0.800)
    res, rr, scr = one_calc("ramp", 0.40)
    s = by_title(scr, "SUMMARY  RAMP")
    expect_values(screen_dict(s), {"SLOPE": "0.400", "A": "0.800"}, "ramp")
    expect_rows(s, ["A = 0.800 M/S²", "SLOPE = 0.400 M/S²"], "ramp")
    expect_rows(by_title(scr, "STEP 1  ACCELERATION"), ["A=2*SLOPE", "A=2(0.400)", "A = 0.800 M/S²"], "ramp step")
    # percent difference of 2.10 and 1.95: |0.15| / 2.025 * 100 = 7.407 -> 7.41 %
    res, rr, scr = one_calc("pdiff", 2.10, 1.95)
    s = by_title(scr, "SUMMARY  PERCENT DIFF")
    expect_values(screen_dict(s), {"VALUE A": "2.10", "VALUE B": "1.95", "AVG": "2.03", "PERCENT DIFF": "7.41"}, "pd")
    expect_rows(s, ["PERCENT DIFF = 7.41 %"], "pd")
    assert screen_dict(s)["PERCENT DIFF"] == fmt3(abs(2.10 - 1.95) / ((2.10 + 1.95) / 2) * 100)
    expect_rows(by_title(scr, "STEP 1  AVERAGE"), ["AVG=(A+B)/2", "AVG=(2.10+1.95)/2", "AVG = 2.03"], "pd 1")
    expect_rows(by_title(scr, "STEP 2  PERCENT DIFFERENCE"),
                ["%DIFF=|A-B|/|AVG|*100", "=|A-B|/(|A+B|/2)*100", "=|2.10-1.95|/(4.05/2)*100",
                 "=0.150/(4.05/2)*100", "PERCENT DIFF = 7.41 %", "(UNROUNDED VALUES USED)"], "pd 2")
    assert fmt3(0.150 / (4.05 / 2) * 100) == "7.41"      # the numbers on the screen give the answer shown


def t_pdiff_shown_numbers():
    """The substituted numbers on STEP 2 reproduce the PERCENT DIFF shown (when A+B has <= 3 s.f.)."""
    sub_re = re.compile(r"^=(" + NUM + r")/\((" + NUM + r")/2\)\*100$")
    # (A+B with more than 3 s.f., e.g. 9.81+9.75 = 19.56 shown as 19.6, is rounded on screen; the
    # "(UNROUNDED VALUES USED)" row covers that case)
    for a, b in [(2.10, 1.95), (10, 12), (-2, -2.2), (9.8, 9.6), (0.52, 0.48), (120, 135), (3.2, -1.1)]:
        res, rr, scr = one_calc("pdiff", a, b)
        rows = rows_of(by_title(scr, "STEP 2  PERCENT DIFFERENCE"))
        subs = [sub_re.match(r) for r in rows if sub_re.match(r)]
        assert len(subs) == 1, rows
        d, s = float(subs[0].group(1)), float(subs[0].group(2))
        shown = screen_dict(by_title(scr, "STEP 2  PERCENT DIFFERENCE"))["PERCENT DIFF"]
        assert fmt3(d / (s / 2) * 100) == shown, (a, b, rows)
        assert shown == fmt3(abs(a - b) / abs((a + b) / 2) * 100), (a, b, shown)       # independent


def t_lab_conversions():
    cases = [  # kind, input -> step value name, shown, unit; summary rows
        ("yd2m", 50, "METERS", "45.7", " M", ["YARDS = 50.0 YD", "METERS = 45.7 M"]),
        ("m2yd", 100, "YARDS", "109", " YD", ["METERS = 100 M", "YARDS = 109 YD"]),
        ("kmh", 90, "SPEED", "25.0", " M/S", ["SPEED = 90.0 KM/H", "SPEED = 25.0 M/S"]),
        ("mph", 60, "SPEED", "26.8", " M/S", ["SPEED = 60.0 MPH", "SPEED = 26.8 M/S"]),
        ("yd2m", 100, "METERS", "91.4", " M", ["METERS = 91.4 M"]),
        ("m2yd", 1, "YARDS", "1.09", " YD", ["YARDS = 1.09 YD"]),
        ("kmh", 36, "SPEED", "10.0", " M/S", ["SPEED = 10.0 M/S"]),
        ("mph", 30, "SPEED", "13.4", " M/S", ["SPEED = 13.4 M/S"]),
        ("kmh", -72, "SPEED", "-20.0", " M/S", ["SPEED = -20.0 M/S"]),
        ("yd2m", 0, "METERS", "0", " M", ["METERS = 0 M"]),
    ]
    hand = {"yd2m": lambda v: v / 1.0936, "m2yd": lambda v: v * 1.0936, "kmh": lambda v: v * 1000 / 3600,
            "mph": lambda v: v * 1609.344 / 3600}
    eqs = {"yd2m": "METERS={}/1.0936", "m2yd": "YARDS={}*1.0936", "kmh": "M/S={}/3.6", "mph": "M/S={}*0.44704"}
    for kind, v, name, shown, unit, rows in cases:
        assert fmt3(hand[kind](v)) == shown, (kind, v)
        res, rr, scr = one_calc(kind, v)
        step, summ = scr
        expect_rows(step, [eqs[kind].format(fmt3(v)), f"{name} = {shown}{unit}"], (kind, v))
        expect_rows(summ, rows, (kind, v))


def t_lab_more_hand():
    res, rr, scr = one_calc("ramp", -0.25)
    expect_values(screen_dict(scr[-1]), {"A": "-0.500"}, "ramp -0.25")
    res, rr, scr = one_calc("pdiff", 10, 12)          # 2 / 11 * 100 = 18.18
    expect_values(screen_dict(scr[-1]), {"AVG": "11.0", "PERCENT DIFF": "18.2"}, "10 vs 12")
    res, rr, scr = one_calc("pdiff", -2, -2.2)        # 0.2 / 2.1 * 100 = 9.524
    expect_values(screen_dict(scr[-1]), {"AVG": "-2.10", "PERCENT DIFF": "9.52"}, "-2 vs -2.2")
    expect_rows(by_title(scr, "STEP 1  AVERAGE"), ["AVG=(-2.00+(-2.20))/2"], "negatives in parentheses")
    res, rr, scr = one_calc("perr", 9.6, 9.8)         # 0.2 / 9.8 * 100 = 2.041
    s = by_title(scr, "SUMMARY  PERCENT ERROR")
    expect_values(screen_dict(s), {"EXPERIMENTAL": "9.60", "ACCEPTED": "9.80", "PERCENT ERROR": "2.04"}, "perr")
    expect_rows(by_title(scr, "STEP 1  PERCENT ERROR"), ["%ERROR=|ACC-EXP|/|ACC|*100", "=|9.80-9.60|/9.80*100",
                                                         "=0.200/9.80*100", "PERCENT ERROR = 2.04 %"], "perr step")
    res, rr, scr = one_calc("perr", 10.5, 10)         # 5.00 %
    expect_values(screen_dict(scr[-1]), {"PERCENT ERROR": "5.00"}, "perr 2")
    res, rr, scr = one_calc("perr", -9.0, -9.8)       # 0.8 / 9.8 = 8.16 %
    expect_values(screen_dict(scr[-1]), {"PERCENT ERROR": "8.16"}, "perr negative")
    expect_rows(scr[0], ["=|-9.80-(-9.00)|/9.80*100"], "perr negative")


def t_lab_messages():
    message_only("ramp", 2e9, label="K6")
    message_only("ramp", -9.99e99, label="K6")
    message_only("pdiff", 1.5e9, 1, label="K6")
    message_only("pdiff", 1, -2e9, label="K6")
    message_only("pdiff", 5, -5, label="K7")          # A+B = 0
    message_only("pdiff", 0, 0, label="K7")
    message_only("pdiff", 1e-99, -1e-99, label="K7")
    message_only("perr", 9.8, 0, label="K8")          # accepted value 0
    message_only("perr", 0, 0, label="K8")
    message_only("perr", 1, 1e-90, label="K8")        # percent error would overflow
    message_only("perr", 2e9, 1, label="K6")
    message_only("yd2m", 2e9, label="K6")
    message_only("m2yd", -2e9, label="K6")
    # ZT-2: km/h and mph are bounded too (ZFMT fails from 9.995E99 up; 9.9999999999999E99 overflowed)
    for kind in ("kmh", "mph"):
        for v in (9.995e99, -9.995e99, 9.999e99, -9.999e99, 9.9999999999999e99, 1.5e9, -1000000001):
            message_only(kind, v, label="K6")


def t_lab_edges():
    for kind, args in [("ramp", (1e9,)), ("ramp", (0,)), ("ramp", (1e-99,)), ("pdiff", (1e9, -999999999.99999)),
                       ("pdiff", (1e-99, 0)), ("pdiff", (3, 0)), ("perr", (0, 5)), ("perr", (1e9, 1e-70)),
                       ("perr", (-1e9, 1e9)), ("yd2m", (1e9,)), ("m2yd", (-1e9,)), ("kmh", (1e9,)),
                       ("kmh", (-1e9,)), ("mph", (-1e9,)), ("mph", (1e9,)), ("kmh", (1e-99,)), ("mph", (0,))]:
        one_calc(kind, *args, exact=False)


# ------------------------------------------------------------------------------ menus / dispatch
def t_menu_back_paths():
    """Every BACK option, and several calculations in one visit, return to the right menu."""
    keys = [6,
            3, 3,                       # VECTOR COMPONENTS -> BACK
            3, 1, 5, 2, 5, 3,           # unit menu BACK -> vector menu; again BACK via unit menu -> BACK
            5, 6,                       # FACTOR OF CHANGE -> BACK
            6, 4, 3, 5, 3, 6,           # LAB TOOLS -> YARDS menu BACK -> SPEED menu BACK -> BACK
            7, 7]
    res, shots = drive(keys)
    assert_clean(res)
    menus = [(e[1], e[3]) for e in res.events if e[0] == "menu"]
    assert menus == [(P1, 6), (P2, 3), (VEC, 3), (P2, 3), (VEC, 1), (UNIT, 5), (VEC, 2), (UNIT, 5), (VEC, 3),
                     (P2, 5), (FAC, 6), (P2, 6), (LAB, 4), (YDM, 3), (LAB, 5), (SPD, 3), (LAB, 6),
                     (P2, 7), (P1, 7)], menus
    assert res.screens == [] and shots == []


def t_session_many():
    """Several calculations (and messages) in one visit of each tool: no state leaks between them."""
    keys = [6,
            3, 1, 1, 20, 30, 2, 2, 4, -3, 2, 4, 0, 0, 1, 3, -5, 30, 3,
            4, 2, 100, 1, 10, 50, -1, 5,
            4, 2, 100, 1, 10, 50, 2, 0,
            5, 1, 20, 3, 3, 2.0, 4, 5, -9.8, -1, 6,
            6, 1, 0.40, 2, 2.10, 1.95, 2, 5, -5, 3, 9.6, 9.8, 4, 1, 50, 4, 2, 100, 5, 1, 90, 5, 2, 60, 6,
            7, 7]
    res, shots = drive(keys)
    assert_clean(res)
    want = [ref.vector_mag_angle(1, 20, 30), ref.vector_xy(2, 4, -3), ref.vector_xy(4, 0, 0),
            ref.vector_mag_angle(3, -5, 30), ref.averages(2, [(100, 1, 10), (50, -1, 5)]),
            ref.averages(2, [(100, 1, 10), (50, 2, 0)]), ref.factor(1, 20, 3), ref.factor(3, 2.0, 4),
            ref.factor(5, -9.8, -1), ref.ramp(0.40), ref.pct_diff(2.10, 1.95), ref.pct_diff(5, -5),
            ref.pct_error(9.6, 9.8), ref.yd_to_m(50), ref.m_to_yd(100), ref.kmh_to_ms(90), ref.mph_to_ms(60)]
    segs = segments(res)
    assert len(segs) == len(want), (len(segs), len(want))
    for k, (seg, rr) in enumerate(zip(segs, want)):
        compare_screens(seg, rr, f"calc {k}")
    assert [p for p, _ in shots] == [p for rr in want for p in rr.prompts]


def t_dispatch_direct():
    """ZTOOLS reads K (1..4; anything else means vectors), never changes K, sets Degree mode."""
    first = {1: VEC, 2: None, 3: FAC, 4: LAB, 0: VEC, 7: VEC, -2: VEC, 1.5: VEC, 2.5: VEC, 999: VEC}
    for k, menu in first.items():
        script = [2.5] if k == 2 else [len(ref.MENUS[menu])]       # averages: an invalid N; else BACK
        res = run(script, program="ZTOOLS", init_vars={"K": k})
        assert_clean(res, context=f"K={k}")
        menus = [e[1] for e in res.events if e[0] == "menu"]
        if menu is None:
            assert menus == [] and res.screens and rows_of(res.screens[0]) == list(ref.MESSAGES["I2"]), res.text()
        else:
            assert menus == [menu], (k, menus)
        assert float(res.vars["K"]) == k, f"K changed from {k} to {res.vars['K']}"
        assert res.angle == "Degree"


def t_seeds():
    """Garbage in the variables (and strings) at start must not matter."""
    for seed in range(5):
        for kind, args in [("vec1", (2, 10, 120)), ("vec2", (1, -3, -4)), ("avg", (2, [(100, 1, 10), (50, -1, 5)])),
                           ("fac", (4, 10, 9)), ("pdiff", (2.10, 1.95)), ("mph", (60,))]:
            one_calc(kind, *args, seed=seed)


def t_wide_values():
    """Worst-case 9-character numbers everywhere: nothing truncated, nothing scrolls."""
    cases = [("vec1", (k, 20, 30)) for k in (1, 2, 3, 4)] + [("vec1", (3, 20, -150))] + \
            [("vec2", (k, x, y)) for k in (3, 4) for x, y in [(3, 4), (-3, 4), (-3, -4), (4, -3), (5, 0),
                                                              (-5, 0), (0, 7), (0, -7), (0, 0)]] + \
            [("avg", (n, [(100, -1, 10)] * n)) for n in (1, 2, 3, 4)] + [("avg", (4, [(0, 1, 1)] * 4))] + \
            [("vec1", (4, 20, a)) for a in (120, -60, 180, 270)] + \
            [("avg", (4, [(50, 1, 10), (50, -1, 12.5), (25, 1, 6.5), (75, -1, 0.5)]))] + \
            [("fac", (rel, -20, 3)) for rel in (1, 2, 4, 5)] + [("fac", (3, 2, 4)), ("fac", (2, -4.9, 2))] + \
            [("ramp", (0.4,)), ("pdiff", (2.1, -1.95)), ("pdiff", (-2.1, 1.95)), ("perr", (-9.6, -9.8)),
             ("perr", (9.6, 9.8)), ("yd2m", (50,)), ("m2yd", (100,)), ("kmh", (90,)), ("mph", (60,)),
             ("pdiff", (2.10, 1.95)), ("kmh", (-1e9,)), ("mph", (1e9,))]
    for kind, args in cases:
        keys, rr, path = script_for(kind, *args)
        res, shots = drive(keys, wide=True)
        assert_clean(res, context=f"wide {kind}{args}")


# ------------------------------------------------------------------------------ fuzz
def _val(rng, lo=-1e3, hi=1e3):
    r = rng.random()
    if r < 0.08:
        return 0
    if r < 0.6:
        return round(rng.uniform(lo, hi), rng.choice([0, 1, 2, 3]))
    mag = 10 ** rng.uniform(-12, 11)
    return float(f"{rng.choice([-1, 1, 1]) * mag:.4g}")


def t_fuzz_vectors():
    rng = random.Random(11)
    for _ in range(120):
        unit = rng.randint(1, 4)
        m = abs(_val(rng)) if rng.random() < 0.85 else _val(rng)
        n = round(rng.uniform(-370, 370), rng.choice([0, 1, 2])) if rng.random() < 0.9 else _val(rng)
        one_calc("vec1", unit, m, n, exact=False, seed=rng.randint(0, 10 ** 6))
        p, q = _val(rng), _val(rng)
        if rng.random() < 0.15:
            p = 0
        if rng.random() < 0.15:
            q = 0
        one_calc("vec2", unit, p, q, exact=False, seed=rng.randint(0, 10 ** 6))


def t_fuzz_averages():
    rng = random.Random(12)
    for _ in range(120):
        n = rng.choice([1, 2, 3, 4, 1, 2, 3, 4, 0, 5, 2.5, -1])
        legs = []
        for _ in range(4):
            a = abs(_val(rng)) if rng.random() < 0.9 else _val(rng)
            b = rng.choice([1, -1, 1, -1, 1, -1, 0, 2, 0.5])
            t = abs(_val(rng, 0, 100)) if rng.random() < 0.9 else _val(rng)
            legs.append((a, b, t))
        one_calc("avg", n, legs, exact=False, seed=rng.randint(0, 10 ** 6))


def t_fuzz_factor():
    rng = random.Random(13)
    for _ in range(150):
        rel = rng.randint(1, 5)
        old = _val(rng)
        k = abs(_val(rng, 0, 10)) if rng.random() < 0.85 else _val(rng)
        one_calc("fac", rel, old, k, exact=False, seed=rng.randint(0, 10 ** 6))


def t_fuzz_lab():
    rng = random.Random(14)
    for _ in range(60):
        one_calc("ramp", _val(rng, -5, 5), exact=False, seed=rng.randint(0, 10 ** 6))
        a = _val(rng)
        b = -a if rng.random() < 0.1 else _val(rng)
        one_calc("pdiff", a, b, exact=False, seed=rng.randint(0, 10 ** 6))
        one_calc("perr", _val(rng), _val(rng), exact=False, seed=rng.randint(0, 10 ** 6))
        kind = rng.choice(["yd2m", "m2yd", "kmh", "mph"])
        one_calc(kind, _val(rng), exact=False, seed=rng.randint(0, 10 ** 6))


def t_coverage():
    """After all the runs above, every statement of ZTOOLS has been executed at least once."""
    if os.environ.get("TISIM_SINGLE"):
        return   # per-module coverage needs the separate module build
    prog = sim().programs["ZTOOLS"]
    missing = [st for i, st in enumerate(prog.stmts) if ("ZTOOLS", i) not in sim().coverage and st.kind != "Lbl"]
    assert not missing, "never executed: " + "; ".join(f"L{st.line} {st.text}" for st in missing[:20])


c.check("syntax (ZTOOLS, PHYSOLVE, ZFMT, ZLINE load)", t_syntax)
c.check("static layout: info rows + prompts <= 10, prompts <= 18, menus, message rows", t_static_layout)
c.check("H required: 20 at 30 deg, 10 at 120 deg (up-left)", t_vec_required_examples)
c.check("H mag+angle -> X,Y hand cases (axes, all quadrants, 360, -90)", t_vec_mag_angle_hand)
c.check("H unit menu: M, M/S, M/S², none", t_vec_units)
c.check("H no unit: one space before the direction word (ZT-8)", t_vec_no_unit_words)
c.check("H X,Y -> mag+angle: 4 quadrants + 4 axes, reference angle, clockwise form, words", t_vec_xy_quadrants)
c.check("H round trip mag/angle -> X,Y -> mag/angle", t_vec_round_trip)
c.check("H impossible inputs: negative magnitude, angle out of range, too large, zero vector", t_vec_messages)
c.check("H negative-magnitude advice never leads to the angle message (ZT-4)", t_vec_opposite_advice)
c.check("H boundary inputs", t_vec_edges)
c.check("I required: 100 m + 10 s, 50 m - 5 s -> 10.0 and 3.33 m/s", t_avg_required_example)
c.check("I hand cases: round trip, 1/3/4 legs, zero-time leg, zero distance", t_avg_hand_cases)
c.check("I 4 legs: each sum line fits one row (ZT-3)", t_avg_four_legs_one_row)
c.check("I impossible inputs: N=0/5/2.5, direction 2/0, negatives, zero total time, too large", t_avg_messages)
c.check("I boundary inputs", t_avg_edges)
c.check("J required: 20 m with speed x3 -> 180 m; 2.0 s with height x4 -> 4.00 s", t_fac_required_examples)
c.check("J hand cases for all five relationships", t_fac_hand_cases)
c.check("J1/J2 negative old S with the (-) hint (ZT-1)", t_fac_negative_old_s)
c.check("every prompt accepting negatives has the (-) hint on screen (ZT-1/ZT-7)", t_negative_hint_on_screen)
c.check("J impossible inputs: negative K (all), too large, negative fall time", t_fac_messages)
c.check("J boundary inputs", t_fac_edges)
c.check("K required: slope 0.40 -> 0.800 M/S²; 2.10 & 1.95 -> 7.41 %", t_lab_required_cases)
c.check("K percent difference: the shown numbers give the shown result (ZT-5)", t_pdiff_shown_numbers)
c.check("K conversions: 50 yd, 100 m, 90 km/h, 60 mph and more", t_lab_conversions)
c.check("K more hand cases: negative slope, % diff, % error", t_lab_more_hand)
c.check("K impossible inputs: A+B=0, accepted 0, too large", t_lab_messages)
c.check("K boundary inputs", t_lab_edges)
c.check("every BACK option returns to the right menu", t_menu_back_paths)
c.check("many calculations and messages in one session", t_session_many)
c.check("dispatch on K (other K -> vectors), K unchanged, Degree", t_dispatch_direct)
c.check("garbage start values do not matter", t_seeds)
c.check("wide (9-character) values: no truncation/scroll", t_wide_values)
c.check("fuzz vectors vs reference", t_fuzz_vectors)
c.check("fuzz averages vs reference", t_fuzz_averages)
c.check("fuzz factor of change vs reference", t_fuzz_factor)
c.check("fuzz lab tools vs reference", t_fuzz_lab)
c.check("every ZTOOLS statement executed", t_coverage)
sys.exit(c.done())
