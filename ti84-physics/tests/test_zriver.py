"""Tests for prgmZRIVER (PHYSOLVE page 2, option 1: RIVER CROSSING), driven through PHYSOLVE's real
menus.

Every run starts at PHYSOLVE page 1, picks 6 (MORE >) and 1 (RIVER CROSSING), types VB, VR, W, and
leaves with page 2 option 7 (BACK) + page 1 option 7 (QUIT), so assert_clean() can check that the
program ended without errors, leaks, scrolling, truncated lines or empty strings. Every Pause screen
of ZRIVER is compared with reference/zriver.py row by row (the reference rebuilds every row,
formatting numbers with fmt3), every "NAME = VALUE UNIT" value is compared with fmt3(reference),
and the required/typical cases are also compared with hand-computed values at 3 significant figures.
"""
import math
import random
import re
import sys

from harness import Checker, run, assert_clean, fmt3, sim

import zriver as ref  # noqa: E402  (reference/ is on sys.path via harness)

c = Checker("ZRIVER")

P1 = "PHYSOLVE 1/2  KINEMATICS"
P2 = "PHYSOLVE 2/2  KINEMATICS"
NUM = r"-?[0-9]+(?:\.[0-9]+)?(?:E-?[0-9]+)?"
VAL_RE = re.compile(r"^(.+?) = (" + NUM + r")(.*)$")
NUM_RE = re.compile(NUM)


# ------------------------------------------------------------------------------ helpers
def script(vb, vr, w):
    """PHYSOLVE -> 6 MORE -> 1 RIVER CROSSING -> VB, VR, W -> 7 BACK -> 7 QUIT."""
    return [6, 1, vb, vr, w, 7, 7]


def rows_of(screen):
    return [row.rstrip() for row in screen if row.strip()]


def values_of(screen):
    """[(name, value_str, unit)] for every 'NAME = VALUE UNIT' row ('°' directly after the value)."""
    out = []
    for row in rows_of(screen):
        m = VAL_RE.match(row)
        if m:
            out.append((m.group(1).strip(), m.group(2), m.group(3).strip()))
    return out


def screen_dict(screen):
    return {n: v for n, v, u in values_of(screen)}


def segments(res):
    """Screens shown by each ZRIVER visit: the screens between choosing page 2 option 1 and the next menu."""
    segs, cur = [], None
    for e in res.events:
        if e[0] == "menu":
            cur = None
            if e[1] == P2 and e[3] == 1:
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
    return any(shown == fmt3(x * f) for f in (1 + 1e-10, 1 - 1e-10))


def numbers_close(a, b):
    """Two rows that differ only in numbers that are equal to ~3 significant figures (fuzz only)."""
    if NUM_RE.sub("#", a) != NUM_RE.sub("#", b):
        return False
    for x, y in zip(NUM_RE.findall(a), NUM_RE.findall(b)):
        fx, fy = float(x), float(y)
        if fx != fy and abs(fx - fy) > 0.0101 * max(abs(fx), abs(fy)):
            return False
    return True


def compare_screens(screens, rr, ctx, exact=True):
    """Simulator screens vs reference Result: same number of screens, same rows (exactly, or for
    fuzz up to rounding-edge digits), and every value equal to fmt3(reference value)."""
    got_titles = [rows_of(s)[0] if rows_of(s) else "" for s in screens]
    want_titles = [s.title for s in rr.screens]
    assert got_titles == want_titles, f"{ctx}: screen titles {got_titles}\n  expected {want_titles}"
    for scr, want in zip(screens, rr.screens):
        got_rows = rows_of(scr)
        assert len(got_rows) == len(want.rows), \
            f"{ctx}: screen {want.title!r} has {len(got_rows)} rows, reference {len(want.rows)}\n  " + \
            "\n  ".join(got_rows) + "\n  ---\n  " + "\n  ".join(want.rows)
        for g, w in zip(got_rows, want.rows):
            if exact:
                assert g == w, f"{ctx}: screen {want.title!r}\n  row   {g!r}\n  wants {w!r}"
            else:
                assert g == w or numbers_close(g, w), f"{ctx}: screen {want.title!r}\n  row   {g!r}\n  wants {w!r}"
        got_vals = values_of(scr)
        assert [(n, u) for n, v, u in got_vals] == [(n, u) for n, v, u in want.values], \
            f"{ctx}: value rows {got_vals}\n  reference {want.values}"
        for (n, v, u), (_, x, _) in zip(got_vals, want.values):
            ok = (v == (x if isinstance(x, str) else fmt3(x))) if exact else close3(v, x)
            assert ok, f"{ctx}: {want.title!r} {n} shows {v!r}, reference {x!r} -> {x if isinstance(x, str) else fmt3(x)!r}"


def one_calc(vb, vr, w, ctx=None, exact=True, **kw):
    """Run ZRIVER once through PHYSOLVE; check clean, the menu path, and every screen vs the reference."""
    ctx = ctx or f"VB={vb} VR={vr} W={w}"
    res = run(script(vb, vr, w), **kw)
    assert_clean(res, context=ctx)
    menus = [(e[1], e[3]) for e in res.events if e[0] == "menu"]
    assert menus == [(P1, 6), (P2, 1), (P2, 7), (P1, 7)], f"{ctx}: menu path {menus}"
    prompts = [e[1] for e in res.events if e[0] == "input"]
    assert prompts == list(ref.PROMPTS), f"{ctx}: prompts {prompts}"
    segs = segments(res)
    assert len(segs) == 1, segs
    rr = ref.run(vb, vr, w)
    compare_screens(segs[0], rr, ctx, exact=exact)
    return res, rr, segs[0]


def by_title(screens, title):
    for s in screens:
        if rows_of(s) and rows_of(s)[0] == title:
            return s
    raise AssertionError(f"no screen titled {title!r}")


def expect_values(got, want, ctx):
    for k, v in want.items():
        assert k in got, f"{ctx}: no {k!r} on the screen: {got}"
        assert got[k] == v, f"{ctx}: {k} shows {got[k]!r}, hand-computed {v!r}"


S1 = "SUMMARY 1/2 (AIMED ACROSS)"
S2 = "SUMMARY 2/2 (LAND ACROSS)"
VAR_END = re.compile(r"(VR|VB|TD|D0|V1|ANGLE)$")


def dash_reads_as_minus(screens):
    """Rows ending in '-' (used as a colon) where the dash reads as a minus sign: the text before it
    is a formula ('THE BANK IT IS 90-ANGLE-'), or a variable directly above a formula row ('=' with
    no spaces), e.g. 'MUST CANCEL VR-' / 'VB SIN(ANGLE)=VR'."""
    bad = []
    for scr in screens:
        rows = rows_of(scr) + [""]
        for a, b in zip(rows, rows[1:]):
            if not a.endswith("-"):
                continue
            last = a[:-1].split(" ")[-1]
            formula_below = "=" in b and " = " not in b
            if re.search(r"[0-9=+*/-]", last) or (VAR_END.search(last) and formula_below):
                bad.append((a, b))
    return bad


# ------------------------------------------------------------------------------ setup
def t_syntax():
    """harness.sim() refuses to load if ANY program has a syntax error; ZRIVER and its helpers must be clean."""
    mine = ("ZRIVER", "PHYSOLVE", "ZFMT", "ZLINE")
    try:
        sim()
    except AssertionError as e:
        lines = str(e).splitlines()[1:]
        bad = [ln for ln in lines if ln.split(":")[0] in mine]
        others = [ln for ln in lines if ln not in bad]
        if others:
            print("       NOTE: syntax errors in programs ZRIVER does not use:\n         "
                  + "\n         ".join(others[:5]))
        assert not bad, "\n".join(bad)


def t_input_screen():
    """The input screen explains VB, VR, W before asking, fits 10 rows, and asks in that order."""
    seen = {}
    keys = script(6, 3, 120)

    def responder(kind, info):
        if kind == "input" and "screen" not in seen:
            seen["screen"] = [r for r in sim().screen if r.strip()]
        return keys.pop(0)

    res = run([], responder=responder)
    assert_clean(res)
    assert seen["screen"] == list(ref.INPUT_ROWS), seen["screen"]
    assert len(ref.INPUT_ROWS) + len(ref.PROMPTS) <= 10


# ------------------------------------------------------------------------------ required case
def t_required_6_3_120():
    res, rr, scr = one_calc(6, 3, 120)
    # t = 120/6 = 20 s; drift = 3*20 = 60 m; resultant sqrt(36+9) = 6.708 m/s;
    # path tan^-1(3/6) = 26.565 deg from straight across (63.435 from the bank);
    # land across: sin^-1(3/6) = 30.0 deg upstream, across speed sqrt(36-9) = 5.196 m/s, 120/5.196 = 23.094 s
    s1 = screen_dict(by_title(scr, S1))
    expect_values(s1, {"T": "20.0", "DRIFT": "60.0", "V RESULT": "6.71", "FROM ACROSS": "26.6",
                       "FROM BANK": "63.4"}, "summary 1")
    s2 = screen_dict(by_title(scr, S2))
    expect_values(s2, {"FROM ACROSS": "30.0", "FROM BANK": "60.0", "V ACROSS": "5.20", "T": "23.1",
                       "DRIFT": "0"}, "summary 2")
    # the same values from the reference (fmt3) and from independent hand formulas
    hand = {"T": 120 / 6, "DRIFT": 3 * 120 / 6, "V RESULT": math.hypot(6, 3),
            "FROM ACROSS": math.degrees(math.atan2(3, 6)), "FROM BANK": 90 - math.degrees(math.atan2(3, 6))}
    for k, x in hand.items():
        assert s1[k] == fmt3(x), (k, s1[k], fmt3(x))
    assert s2["V ACROSS"] == fmt3(math.sqrt(27)) and s2["T"] == fmt3(120 / math.sqrt(27))
    assert s2["FROM ACROSS"] == fmt3(math.degrees(math.asin(0.5)))
    assert rr.summary["1:T"] == 20 and abs(rr.summary["2:T"] - 23.0940107676) < 1e-9
    # units and labels on the summary screens
    rows1, rows2 = rows_of(by_title(scr, S1)), rows_of(by_title(scr, S2))
    for row in ("T = 20.0 S", "DRIFT = 60.0 M", "V RESULT = 6.71 M/S", "PATH ANGLE (DOWNSTREAM)-",
                "FROM ACROSS = 26.6°", "FROM BANK = 63.4°", "HEADING- STRAIGHT ACROSS,"):
        assert row in rows1, (row, rows1)
    for row in ("HEADING (UPSTREAM)-", "FROM ACROSS = 30.0°", "FROM BANK = 60.0°", "V ACROSS = 5.20 M/S",
                "T = 23.1 S", "DRIFT = 0 M"):
        assert row in rows2, (row, rows2)


def t_land_across_heading_vs_path():
    """Aimed upstream: the summary says the path is straight across (not along the heading) and that
    V ACROSS is the speed seen from shore (the usual 'speed relative to shore' follow-up)."""
    res, rr, scr = one_calc(6, 3, 120)
    rows2 = rows_of(by_title(scr, S2))
    assert rows2 == ["SUMMARY 2/2 (LAND ACROSS)", "HEADING (UPSTREAM)-", "FROM ACROSS = 30.0°",
                     "FROM BANK = 60.0°", "PATH- STRAIGHT ACROSS,", "NOT ALONG THE HEADING.",
                     "V ACROSS = 5.20 M/S", "(SPEED SEEN FROM SHORE)", "T = 23.1 S", "DRIFT = 0 M"], rows2
    # the speed seen from shore when aimed upstream: sqrt(VB^2 - VR^2), the resultant of the
    # heading velocity and the current
    vx, vy = 6 * math.cos(math.radians(30)), -6 * math.sin(math.radians(30)) + 3
    assert abs(vy) < 1e-12 and fmt3(math.hypot(vx, vy)) == "5.20"
    # the aimed-across summary keeps its own heading-vs-path rows
    rows1 = rows_of(by_title(scr, S1))
    assert rows1[-2:] == ["HEADING- STRAIGHT ACROSS,", "NOT ALONG THE PATH."], rows1


def t_dash_not_read_as_minus():
    """RC-3: no row ends with a formula/variable and a '-' right above a formula row."""
    for inp in [(6, 3, 120), (5, 0, 100), (4, 4, 50), (3, 5, 90)]:
        res, rr, scr = one_calc(*inp)
        assert dash_reads_as_minus(scr) == [], (inp, dash_reads_as_minus(scr))
    res, rr, scr = one_calc(6, 3, 120)
    assert "MUST CANCEL VR, SO" in rows_of(by_title(scr, "STEP 5  HEADING UPSTREAM"))
    assert "THE BANK IT IS 90-ANGLE." in rows_of(by_title(scr, "STEP 4  PATH ANGLE"))


def t_required_steps_show_work():
    """Each step names its equation and shows the numbers substituted."""
    res, rr, scr = one_calc(6, 3, 120)
    titles = [rows_of(s)[0] for s in scr]
    assert titles == ["STEP 1  CROSSING TIME", "STEP 2  DRIFT", "STEP 3  RESULTANT SPEED", "STEP 4  PATH ANGLE",
                      "STEP 5  HEADING UPSTREAM", "STEP 6  NEW CROSSING TIME", S1, S2], titles
    want = {
        "STEP 1  CROSSING TIME": ["T=W/VB", "T=120/6.00", "T = 20.0 S"],
        "STEP 2  DRIFT": ["DRIFT=VR*T", "DRIFT=(3.00)(20.0)", "DRIFT = 60.0 M"],
        "STEP 3  RESULTANT SPEED": ["V=√(VB²+VR²)", "V=√(6.00²+3.00²)", "V RESULT = 6.71 M/S"],
        "STEP 4  PATH ANGLE": ["TAN(ANGLE)=VR/VB", "ANGLE=TAN⁻1(3.00/6.00)", "FROM ACROSS = 26.6°",
                               "(TOWARD DOWNSTREAM). FROM", "FROM BANK = 63.4°", "HEADING IS STRAIGHT ACROSS",
                               "BUT THE PATH IS SLANTED."],
        "STEP 5  HEADING UPSTREAM": ["MUST CANCEL VR, SO", "VB SIN(ANGLE)=VR", "ANGLE=SIN⁻1(3.00/6.00)",
                                     "FROM ACROSS = 30.0°",
                                     "FROM BANK = 60.0°", "(AIM UPSTREAM)"],
        "STEP 6  NEW CROSSING TIME": ["V ACROSS=VB COS(ANGLE)", "=√(VB²-VR²)", "=√(6.00²-3.00²)",
                                      "V ACROSS = 5.20 M/S", "T=W/V ACROSS", "T=120/5.20", "T = 23.1 S"],
    }
    for s in scr:
        rows = rows_of(s)
        for row in want.get(rows[0], []):
            assert row in rows, f"{rows[0]!r} lacks {row!r}:\n" + "\n".join(rows)


# ------------------------------------------------------------------------------ more hand-computed cases
def t_typical_4_25_80():
    res, rr, scr = one_calc(4, 2.5, 80)
    # t = 20; drift 50; V = sqrt(22.25) = 4.717; path atan(0.625) = 32.005 (bank 57.995);
    # heading asin(0.625) = 38.682 (bank 51.318); across sqrt(9.75) = 3.1225; 80/3.1225 = 25.62
    expect_values(screen_dict(by_title(scr, S1)), {"T": "20.0", "DRIFT": "50.0", "V RESULT": "4.72",
                                                   "FROM ACROSS": "32.0", "FROM BANK": "58.0"}, "4/2.5/80 s1")
    expect_values(screen_dict(by_title(scr, S2)), {"FROM ACROSS": "38.7", "FROM BANK": "51.3",
                                                   "V ACROSS": "3.12", "T": "25.6"}, "4/2.5/80 s2")


def t_still_water_vr0():
    res, rr, scr = one_calc(5, 0, 100)
    # no current: t = 20, no drift, V = VB, path straight across (0 deg, 90 from the bank),
    # aim 0 deg upstream, across speed = VB, same time
    expect_values(screen_dict(by_title(scr, S1)), {"T": "20.0", "DRIFT": "0", "V RESULT": "5.00",
                                                   "FROM ACROSS": "0", "FROM BANK": "90.0"}, "VR=0 s1")
    expect_values(screen_dict(by_title(scr, S2)), {"FROM ACROSS": "0", "FROM BANK": "90.0",
                                                   "V ACROSS": "5.00", "T": "20.0"}, "VR=0 s2")
    assert "(NO CURRENT- AIM ACROSS)" in rows_of(by_title(scr, "STEP 5  HEADING UPSTREAM"))
    assert "(AIM UPSTREAM)" not in rows_of(by_title(scr, "STEP 5  HEADING UPSTREAM"))


def t_still_water_wording():
    """RIV-1: with VR = 0 the path is straight across, along the heading. No row may call the path
    slanted/downstream, say the heading is not along the path, or call a 0 degree heading upstream."""
    res, rr, scr = one_calc(5, 0, 100)
    st4 = rows_of(by_title(scr, "STEP 4  PATH ANGLE"))
    assert st4[3:] == ["FROM ACROSS = 0°", "(STRAIGHT ACROSS). FROM", "THE BANK IT IS 90-ANGLE.",
                       "FROM BANK = 90.0°", "HEADING IS STRAIGHT ACROSS", "NO CURRENT- SO IS THE PATH"], st4
    rows1 = rows_of(by_title(scr, S1))
    assert rows1 == ["SUMMARY 1/2 (AIMED ACROSS)", "T = 20.0 S", "DRIFT = 0 M", "V RESULT = 5.00 M/S",
                     "PATH ANGLE (NO CURRENT)-", "FROM ACROSS = 0°", "FROM BANK = 90.0°",
                     "HEADING- STRAIGHT ACROSS,", "SAME AS THE PATH."], rows1
    rows2 = rows_of(by_title(scr, S2))
    assert rows2 == ["SUMMARY 2/2 (LAND ACROSS)", "HEADING (NO CURRENT)-", "FROM ACROSS = 0°",
                     "FROM BANK = 90.0°", "PATH- STRAIGHT ACROSS,", "SAME AS THE HEADING.",
                     "V ACROSS = 5.00 M/S", "(SPEED SEEN FROM SHORE)", "T = 20.0 S", "DRIFT = 0 M"], rows2
    for title in ("STEP 4  PATH ANGLE", S1, S2):
        text = " ".join(rows_of(by_title(scr, title)))
        for phrase in ("SLANTED", "DOWNSTREAM", "UPSTREAM", "NOT ALONG"):
            assert phrase not in text, (title, phrase, text)
    # any current at all (even tiny) keeps the slanted/upstream wording
    for vr in (3, 0.001):
        res, rr, scr = one_calc(6, vr, 120)
        assert "BUT THE PATH IS SLANTED." in rows_of(by_title(scr, "STEP 4  PATH ANGLE"))
        assert "(TOWARD DOWNSTREAM). FROM" in rows_of(by_title(scr, "STEP 4  PATH ANGLE"))
        assert "NOT ALONG THE PATH." in rows_of(by_title(scr, S1))
        assert "HEADING (UPSTREAM)-" in rows_of(by_title(scr, S2))
        assert "NOT ALONG THE HEADING." in rows_of(by_title(scr, S2))
    # VR >= VB (cannot land across): the aimed-across summary still says the path is slanted
    res, rr, scr = one_calc(3, 5, 90)
    assert "NOT ALONG THE PATH." in rows_of(by_title(scr, S1))


def t_vr_equals_vb():
    res, rr, scr = one_calc(4, 4, 50)
    # t = 12.5; drift 50; V = sqrt(32) = 5.657; path 45 / 45; landing across impossible
    assert rr.messages == ["N1"], rr.messages
    expect_values(screen_dict(by_title(scr, S1)), {"T": "12.5", "DRIFT": "50.0", "V RESULT": "5.66",
                                                   "FROM ACROSS": "45.0", "FROM BANK": "45.0"}, "VR=VB s1")
    msg = [s for s in scr if rows_of(s)[0] == "TO LAND DIRECTLY ACROSS"]
    assert len(msg) == 1 and rows_of(msg[0]) == list(ref.MESSAGES["N1"]), msg
    rows2 = rows_of(by_title(scr, S2))
    assert "IMPOSSIBLE- THE RIVER IS" in rows2 and values_of(by_title(scr, S2)) == [], rows2
    assert not any(rows_of(s)[0].startswith(("STEP 5", "STEP 6")) for s in scr)


def t_vr_faster_than_vb():
    res, rr, scr = one_calc(3, 5, 90)
    # t = 30; drift 150; V = sqrt(34) = 5.831; path atan(5/3) = 59.036 (bank 30.964); impossible
    assert rr.messages == ["N1"], rr.messages
    expect_values(screen_dict(by_title(scr, S1)), {"T": "30.0", "DRIFT": "150", "V RESULT": "5.83",
                                                   "FROM ACROSS": "59.0", "FROM BANK": "31.0"}, "VR>VB s1")
    assert "IMPOSSIBLE- THE RIVER IS" in rows_of(by_title(scr, S2))


def t_more_hand_values():
    cases = [  # (vb, vr, w) -> T, drift, V, path, head, v across, t land
        ((2, 1.5, 40), dict(T=20, DRIFT=30, V=2.5, PATH=36.8699, HEAD=48.5904, VA=1.32288, TL=30.2372)),
        ((10, 6, 250), dict(T=25, DRIFT=150, V=11.6619, PATH=30.9638, HEAD=36.8699, VA=8, TL=31.25)),
        ((1.2, 0.5, 15), dict(T=12.5, DRIFT=6.25, V=1.3, PATH=22.6199, HEAD=24.6243, VA=1.09087, TL=13.7505)),
    ]
    for (vb, vr, w), h in cases:
        res, rr, scr = one_calc(vb, vr, w)
        s1, s2 = screen_dict(by_title(scr, S1)), screen_dict(by_title(scr, S2))
        expect_values(s1, {"T": fmt3(h["T"]), "DRIFT": fmt3(h["DRIFT"]), "V RESULT": fmt3(h["V"]),
                           "FROM ACROSS": fmt3(h["PATH"]), "FROM BANK": fmt3(90 - h["PATH"])}, (vb, vr, w))
        expect_values(s2, {"FROM ACROSS": fmt3(h["HEAD"]), "FROM BANK": fmt3(90 - h["HEAD"]),
                           "V ACROSS": fmt3(h["VA"]), "T": fmt3(h["TL"])}, (vb, vr, w))


# ------------------------------------------------------------------------------ menu paths
def t_menu_path_and_back():
    """Page 2 option 1 runs ZRIVER and comes back to page 2; BACK/QUIT leave cleanly."""
    res = run([6, 1, 6, 3, 120, 1, 4, 4, 50, 7, 7])
    assert_clean(res)
    menus = [(e[1], e[3]) for e in res.events if e[0] == "menu"]
    assert menus == [(P1, 6), (P2, 1), (P2, 1), (P2, 7), (P1, 7)], menus
    segs = segments(res)
    assert len(segs) == 2
    compare_screens(segs[0], ref.run(6, 3, 120), "session 1")
    compare_screens(segs[1], ref.run(4, 4, 50), "session 2")
    assert res.angle == "Degree"


def t_session_with_messages():
    """A bad input, then a good run, in one session (no state leaks from the message path)."""
    res = run([6, 1, 0, 3, 120, 1, 6, 3, 120, 1, 6, -1, 5, 7, 7])
    assert_clean(res)
    segs = segments(res)
    assert len(segs) == 3
    compare_screens(segs[0], ref.run(0, 3, 120), "E1")
    compare_screens(segs[1], ref.run(6, 3, 120), "ok")
    compare_screens(segs[2], ref.run(6, -1, 5), "E2")


def t_seeds():
    """Garbage in the variables at start must not matter."""
    for seed in range(6):
        res = run(script(6, 3, 120), seed=seed)
        assert_clean(res)
        compare_screens(segments(res)[0], ref.run(6, 3, 120), f"seed {seed}")


# ------------------------------------------------------------------------------ impossible / edge inputs
EDGE = [
    ((0, 3, 120), "E1"), ((-6, 3, 120), "E1"), ((-1e99, -1e99, -1e99), "E1"), ((0, 0, 0), "E1"),
    ((6, -3, 120), "E2"), ((6, -1e-99, 120), "E2"),
    ((6, 3, 0), "E3"), ((6, 3, -5), "E3"), ((6, 0, -1e99), "E3"),
    ((2e9, 1, 1), "E4"), ((6, 2e9, 1), "E4"), ((6, 3, 1e10), "E4"), ((9.99e99, 9.99e99, 9.99e99), "E4"),
    ((1e-10, 0, 1), "E5"), ((1e-99, 0, 1), "E5"), ((9.99e-10, 5, 5), "E5"),
]


def t_edge_inputs():
    for inp, label in EDGE:
        ctx = f"inputs {inp}"
        res, rr, scr = one_calc(*inp, ctx=ctx)
        assert rr.messages == [label], f"{ctx}: reference messages {rr.messages}, expected {label}"
        assert len(scr) == 1 and rows_of(scr[0]) == list(ref.MESSAGES[label]), f"{ctx}: {scr}"
        for row in rows_of(scr[0]):
            assert not VAL_RE.match(row), f"message row looks like a value: {row!r}"


def t_boundaries():
    """Largest/smallest accepted inputs: no overflow, no error, values equal the reference."""
    for inp in [(1e9, 1e9, 1e9), (1e-9, 0, 1e9), (1e-9, 1e9, 1e9), (1e9, 1e-99, 1e-99), (1e9, 0, 1e-99),
                (1e-9, 9.999e-10, 1e9), (1e9, 999999999, 1e9), (1, 0.9999999999, 1e9), (1e-9, 1e-99, 1e-9),
                (0.001, 0.001, 0.001), (1e9, 1e9 - 1, 1), (1e-9, 1e-9, 1e-9)]:
        one_calc(*inp, exact=False)


def t_wide_values():
    """Worst-case 9-character numbers everywhere: nothing truncated, nothing scrolls."""
    for inp in [(6, 3, 120), (4, 4, 50), (3, 5, 90), (5, 0, 100), (6, 0.001, 120), (0, 3, 120), (6, -3, 120),
                (6, 3, 0), (2e9, 1, 1), (1e-10, 0, 1)]:
        res = run(script(*inp), wide=True)
        assert_clean(res, context=f"wide {inp}")


def t_message_wording():
    """Message rows are prose (no 'NAME = VALUE' look-alikes) and fit 26 columns."""
    for label, rows in ref.MESSAGES.items():
        assert len(rows) <= 9, label
        for row in rows:
            assert len(row) <= 26 and not VAL_RE.match(row), (label, row)


# ------------------------------------------------------------------------------ fuzz
def t_fuzz_realistic():
    """Typical test-problem numbers: every row equals the reference."""
    rng = random.Random(2026)
    for _ in range(150):
        vb = round(rng.uniform(0.3, 25), rng.choice([0, 1, 2]))
        vr = round(rng.uniform(0, 20), rng.choice([0, 1, 2]))
        w = round(rng.uniform(5, 2000), rng.choice([0, 1]))
        vb = vb or 1.0
        w = w or 10.0
        one_calc(vb, vr, w, exact=False)


def t_fuzz_wide():
    """Any numbers (negative, zero, tiny, huge): never an error/leak/scroll/truncation, always back to
    page 2, and the same screens/values as the reference."""
    rng = random.Random(99)

    def val():
        r = rng.random()
        if r < 0.1:
            return 0
        mag = 10 ** rng.uniform(-12, 11)
        return float(f"{rng.choice([-1, 1, 1, 1, 1]) * mag:.4g}")

    for _ in range(250):
        one_calc(val(), val(), val(), exact=False, seed=rng.randint(0, 10 ** 6))


def t_fuzz_valid_all_magnitudes():
    """Valid inputs spread over every accepted magnitude (VB 1E-9 ... 1E9, VR 0 ... 1E9, W up to 1E9):
    the full solution runs, no error/overflow, and every screen matches the reference and hand formulas."""
    rng = random.Random(555)

    def mag(lo):
        return float(f"{10 ** rng.uniform(lo, 9):.4g}")

    for _ in range(250):
        vb = mag(-9)
        vr = 0 if rng.random() < 0.15 else (vb * rng.uniform(0, 1.5) if rng.random() < 0.5 else mag(-12))
        vr = float(f"{min(vr, 1e9):.4g}")
        w = mag(-12)
        res, rr, scr = one_calc(vb, vr, w, exact=False, seed=rng.randint(0, 10 ** 6))
        assert rr.messages in ([], ["N1"]), (vb, vr, w, rr.messages)
        s1 = screen_dict(by_title(scr, S1))
        assert close3(s1["T"], w / vb) and close3(s1["V RESULT"], math.hypot(vb, vr)), (vb, vr, w, s1)
        if vr < vb:
            s2 = screen_dict(by_title(scr, S2))
            assert close3(s2["V ACROSS"], math.sqrt((vb - vr) * (vb + vr))), (vb, vr, w, s2)


for name, fn in list(globals().items()):
    if name.startswith("t_") and callable(fn):
        c.check(name[2:].replace("_", " "), fn)
sys.exit(c.done())
