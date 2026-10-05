"""Tests for prgmZCHASE (PHYSOLVE page 2, option 2: CHASE PROBLEM), driven through PHYSOLVE's real
menus.

Every run starts at PHYSOLVE page 1, picks 6 (MORE >) and 2 (CHASE PROBLEM), types V1, D0, A, TD,
and leaves with page 2 option 7 (BACK) + page 1 option 7 (QUIT), so assert_clean() can check that
the program ended without errors, leaks, scrolling, truncated lines or empty strings. Every Pause
screen (including the prgmZQUAD screen) is compared with reference/zchase.py row by row, every
"NAME = VALUE UNIT" value is compared with fmt3(reference), and the required/typical cases are also
compared with hand-computed values at 3 significant figures.
"""
import math
import random
import re
import sys

from harness import Checker, run, assert_clean, fmt3, sim

import zchase as ref  # noqa: E402  (reference/ is on sys.path via harness)
import zriver  # noqa: E402

c = Checker("ZCHASE")

P1 = "PHYSOLVE 1/2  KINEMATICS"
P2 = "PHYSOLVE 2/2  KINEMATICS"
NUM = r"-?[0-9]+(?:\.[0-9]+)?(?:E-?[0-9]+)?"
VAL_RE = re.compile(r"^(.+?) = (" + NUM + r")(.*)$")
NUM_RE = re.compile(NUM)
QUAD = "SOLVE QUADRATIC FOR T"
SUM = "SUMMARY (CHASE)"


# ------------------------------------------------------------------------------ helpers
def script(v1, d0, a, td):
    """PHYSOLVE -> 6 MORE -> 2 CHASE PROBLEM -> V1, D0, A, TD -> 7 BACK -> 7 QUIT."""
    return [6, 2, v1, d0, a, td, 7, 7]


def rows_of(screen):
    return [row.rstrip() for row in screen if row.strip()]


def values_of(screen):
    out = []
    for row in rows_of(screen):
        m = VAL_RE.match(row)
        if m:
            out.append((m.group(1).strip(), m.group(2), m.group(3).strip()))
    return out


def screen_dict(screen):
    return {n: v for n, v, u in values_of(screen)}


def segments(res, option=2):
    segs, cur = [], None
    for e in res.events:
        if e[0] == "menu":
            cur = None
            if e[1] == P2 and e[3] == option:
                cur = []
                segs.append(cur)
        elif e[0] == "screen" and cur is not None:
            cur.append(e[1])
    return segs


def close3(shown, x):
    if isinstance(x, str):
        return shown == x
    if shown == fmt3(x):
        return True
    return any(shown == fmt3(x * f) for f in (1 + 1e-10, 1 - 1e-10))


def numbers_close(a, b):
    if NUM_RE.sub("#", a) != NUM_RE.sub("#", b):
        return False
    for x, y in zip(NUM_RE.findall(a), NUM_RE.findall(b)):
        fx, fy = float(x), float(y)
        if fx != fy and abs(fx - fy) > 0.0101 * max(abs(fx), abs(fy)):
            return False
    return True


def t1_ill_conditioned(rr):
    """ZQUAD's smaller root (V1-sqrt(G))/A cancels when the lead is 0 or tiny next to V1^2/A; then the
    14-digit calculator and binary floats can show different leftovers of size ~1E-13*T2."""
    t1, t2 = rr.results.get("T1"), rr.results.get("T2")
    return t1 is not None and abs(t1) < 1e-6 * abs(t2)


def compare_screens(screens, rr, ctx, exact=True):
    got_titles = [rows_of(s)[0] if rows_of(s) else "" for s in screens]
    want_titles = [s.title for s in rr.screens]
    assert got_titles == want_titles, f"{ctx}: screen titles {got_titles}\n  expected {want_titles}"
    skip_t1 = t1_ill_conditioned(rr)
    for scr, want in zip(screens, rr.screens):
        got_rows = rows_of(scr)
        assert len(got_rows) == len(want.rows), \
            f"{ctx}: screen {want.title!r} has {len(got_rows)} rows, reference {len(want.rows)}\n  " + \
            "\n  ".join(got_rows) + "\n  ---\n  " + "\n  ".join(want.rows)
        for g, w in zip(got_rows, want.rows):
            if skip_t1 and g.startswith("T1 = ") and w.startswith("T1 = "):
                continue
            if exact:
                assert g == w, f"{ctx}: screen {want.title!r}\n  row   {g!r}\n  wants {w!r}"
            else:
                assert g == w or numbers_close(g, w), f"{ctx}: screen {want.title!r}\n  row   {g!r}\n  wants {w!r}"
        got_vals = values_of(scr)
        assert [(n, u) for n, v, u in got_vals] == [(n, u) for n, v, u in want.values], \
            f"{ctx}: value rows {got_vals}\n  reference {want.values}"
        for (n, v, u), (_, x, _) in zip(got_vals, want.values):
            if skip_t1 and n == "T1":
                continue
            ok = (v == (x if isinstance(x, str) else fmt3(x))) if exact else close3(v, x)
            assert ok, f"{ctx}: {want.title!r} {n} shows {v!r}, reference {x!r} -> {fmt3(x) if not isinstance(x, str) else x!r}"


def one_calc(v1, d0, a, td, ctx=None, exact=True, **kw):
    ctx = ctx or f"V1={v1} D0={d0} A={a} TD={td}"
    res = run(script(v1, d0, a, td), **kw)
    assert_clean(res, context=ctx)
    menus = [(e[1], e[3]) for e in res.events if e[0] == "menu"]
    assert menus == [(P1, 6), (P2, 2), (P2, 7), (P1, 7)], f"{ctx}: menu path {menus}"
    prompts = [e[1] for e in res.events if e[0] == "input"]
    assert prompts == list(ref.PROMPTS), f"{ctx}: prompts {prompts}"
    segs = segments(res)
    assert len(segs) == 1, segs
    rr = ref.run(v1, d0, a, td)
    compare_screens(segs[0], rr, ctx, exact=exact)
    return res, rr, segs[0]


def by_title(screens, title):
    for s in screens:
        if rows_of(s) and rows_of(s)[0] == title:
            return s
    raise AssertionError(f"no screen titled {title!r}: {[rows_of(s)[0] for s in screens]}")


def expect_values(got, want, ctx):
    for k, v in want.items():
        assert k in got, f"{ctx}: no {k!r} on the screen: {got}"
        assert got[k] == v, f"{ctx}: {k} shows {got[k]!r}, hand-computed {v!r}"


def hand(v1, d0, a, td):
    """Independent solution: positions equal. Car 1 lead when car 2 starts = d0 + v1*td;
    (1/2)a u^2 = lead + v1 u  ->  u = (v1 + sqrt(v1^2 + 2 a lead)) / a."""
    lead = d0 + v1 * td
    u = (v1 + math.sqrt(v1 * v1 + 2 * a * lead)) / a
    s = 0.5 * a * u * u
    assert abs(s - (d0 + v1 * (u + td))) <= 1e-9 * max(1, s)     # both cars at the same place
    return dict(lead=lead, u=u, t=u + td, s=s, v2=a * u, ratio=(a * u / v1) if v1 else None,
                t1=(v1 - math.sqrt(v1 * v1 + 2 * a * lead)) / a, disc=v1 * v1 + 2 * a * lead)


# ------------------------------------------------------------------------------ setup
def t_syntax():
    mine = ("ZCHASE", "PHYSOLVE", "ZFMT", "ZLINE", "ZQUAD")
    try:
        sim()
    except AssertionError as e:
        lines = str(e).splitlines()[1:]
        bad = [ln for ln in lines if ln.split(":")[0] in mine]
        others = [ln for ln in lines if ln not in bad]
        if others:
            print("       NOTE: syntax errors in programs ZCHASE does not use:\n         "
                  + "\n         ".join(others[:5]))
        assert not bad, "\n".join(bad)


def t_info_and_input_screens():
    """An explanation screen (Pause), then an input screen naming V1, D0, A, TD before asking."""
    seen = {}
    keys = script(30, 0, 3, 0)

    def responder(kind, info):
        if kind == "input" and "screen" not in seen:
            seen["screen"] = [r for r in sim().screen if r.strip()]
        return keys.pop(0)

    res = run([], responder=responder)
    assert_clean(res)
    assert seen["screen"] == list(ref.INPUT_ROWS), seen["screen"]
    assert len(ref.INPUT_ROWS) + len(ref.PROMPTS) <= 10
    assert rows_of(segments(res)[0][0]) == list(ref.INFO_ROWS)


# ------------------------------------------------------------------------------ required case
def t_required_police():
    """Car at 30 m/s, police from rest at 3.0 m/s^2: t = 20 s, s = 600 m, police speed 60 m/s (2x)."""
    res, rr, scr = one_calc(30, 0, 3.0, 0)
    s = screen_dict(by_title(scr, SUM))
    expect_values(s, {"T": "20.0", "S": "600", "V2": "60.0", "V2/V1": "2.00"}, "required")
    assert set(s) == {"T", "S", "V2", "V2/V1"}, s
    h = hand(30, 0, 3, 0)
    assert (fmt3(h["u"]), fmt3(h["s"]), fmt3(h["v2"]), fmt3(h["ratio"])) == ("20.0", "600", "60.0", "2.00")
    assert rr.summary == {"T": 20.0, "S": 600.0, "V2": 60.0, "V2/V1": 2.0}, rr.summary
    rows = rows_of(by_title(scr, SUM))
    for row in ("T = 20.0 S", "(CATCH-UP TIME)", "S = 600 M", "V2 = 60.0 M/S", "V2/V1 = 2.00"):
        assert row in rows, (row, rows)
    q = by_title(scr, QUAD)
    qrows = rows_of(q)
    assert "1.50T²-30.0T+0=0" in qrows, qrows
    expect_values(screen_dict(q), {"B²-4AC": "900", "T1": "0", "T2": "20.0", "SO U": "20.0"}, "quadratic")
    assert "T1 IS 0, THE START (SIDE" in qrows and len(qrows) <= 10
    step5 = rows_of(by_title(scr, "STEP 5  CAR 2 SPEED"))
    assert "RULE- FROM REST, SIDE BY" in step5 and "SIDE, IT CATCHES UP AT 2X" in step5, step5


def t_required_steps_show_work():
    res, rr, scr = one_calc(30, 0, 3, 0)
    titles = [rows_of(s)[0] for s in scr]
    assert titles == ["CHASE PROBLEM", "STEP 1  SET X1=X2", "STEP 2  PUT IN NUMBERS", QUAD,
                      "STEP 3  CATCH-UP TIME", "STEP 4  DISTANCE", "STEP 5  CAR 2 SPEED", SUM], titles
    want = {
        "STEP 1  SET X1=X2": ["CAR 1- X1=D0+V1*T", "CAR 2- X2=(1/2)A(T-TD)²", "X1=X2 GIVES",
                              "(1/2)AU²-V1*U-(D0+V1*TD)=0"],
        "STEP 2  PUT IN NUMBERS": ["LEAD=0+(30.0)(0)", "LEAD = 0 M", "(1/2)(3.00)U²-30.0U-0=0",
                                   "ON THE NEXT SCREEN T IS U"],
        "STEP 3  CATCH-UP TIME": ["TD IS 0, SO CAR 2 STARTS", "T = 20.0 S"],
        "STEP 4  DISTANCE": ["S=(1/2)AU²", "S=(1/2)(3.00)(20.0)²", "S = 600 M", "X1 = 600 M"],
        "STEP 5  CAR 2 SPEED": ["VF=V0+AT WITH V0 IS 0,", "SO V2=AU", "V2=(3.00)(20.0)", "V2 = 60.0 M/S",
                                "V2/V1=60.0/30.0", "V2/V1 = 2.00"],
    }
    for s in scr:
        rows = rows_of(s)
        for row in want.get(rows[0], []):
            assert row in rows, f"{rows[0]!r} lacks {row!r}:\n" + "\n".join(rows)


# ------------------------------------------------------------------------------ more hand-computed cases
def t_head_start():
    """V1 = 30, D0 = 100, A = 3: u = (30+sqrt(900+600))/3 = 22.91 s."""
    res, rr, scr = one_calc(30, 100, 3, 0)
    h = hand(30, 100, 3, 0)
    assert abs(h["u"] - 22.9099) < 1e-3
    s = screen_dict(by_title(scr, SUM))
    expect_values(s, {"T": "22.9", "S": "787", "V2": "68.7", "V2/V1": "2.29"}, "head start")
    expect_values(s, {"T": fmt3(h["u"]), "S": fmt3(h["s"]), "V2": fmt3(h["v2"]), "V2/V1": fmt3(h["ratio"])}, "hand")
    q = by_title(scr, QUAD)
    expect_values(screen_dict(q), {"B²-4AC": "1500", "T1": "-2.91", "T2": "22.9", "SO U": "22.9"}, "quad")
    assert "1.50T²-30.0T-100=0" in rows_of(q) and "T1<0 IS BEFORE CAR 2" in rows_of(q)
    assert "THE 2X RULE IS ONLY FOR A" in rows_of(by_title(scr, "STEP 5  CAR 2 SPEED"))


def t_delay():
    """V1 = 30, TD = 2, A = 3: lead 60 m, u = (30+sqrt(1260))/3 = 21.83 s, t = 23.83 s."""
    res, rr, scr = one_calc(30, 0, 3, 2)
    h = hand(30, 0, 3, 2)
    s = screen_dict(by_title(scr, SUM))
    expect_values(s, {"U": "21.8", "T": "23.8", "S": "715", "V2": "65.5", "V2/V1": "2.18"}, "delay")
    expect_values(s, {"U": fmt3(h["u"]), "T": fmt3(h["t"]), "S": fmt3(h["s"]), "V2": fmt3(h["v2"]),
                      "V2/V1": fmt3(h["ratio"])}, "hand")
    rows = rows_of(by_title(scr, SUM))
    assert rows[1:5] == ["U = 21.8 S", "(AFTER CAR 2 STARTS)", "T = 23.8 S", "(AFTER TIME 0)"], rows
    st3 = rows_of(by_title(scr, "STEP 3  CATCH-UP TIME"))
    assert "T=21.8+2.00" in st3 and "T = 23.8 S" in st3 and "U = 21.8 S" in st3, st3
    st2 = rows_of(by_title(scr, "STEP 2  PUT IN NUMBERS"))
    assert "LEAD=0+(30.0)(2.00)" in st2 and "LEAD = 60.0 M" in st2 and "(1/2)(3.00)U²-30.0U-60.0=0" in st2, st2
    expect_values(screen_dict(by_title(scr, QUAD)), {"B²-4AC": "1260", "T1": "-1.83", "T2": "21.8"}, "quad")
    expect_values(screen_dict(by_title(scr, "STEP 4  DISTANCE")), {"S": "715", "X1": "715"}, "check")


def t_head_start_and_delay():
    res, rr, scr = one_calc(30, 100, 3, 2)
    h = hand(30, 100, 3, 2)
    # lead 160 m; disc 1860; u = (30+43.128)/3 = 24.376; t = 26.376; s = 891.3; v2 = 73.13; ratio 2.438
    s = screen_dict(by_title(scr, SUM))
    expect_values(s, {"U": "24.4", "T": "26.4", "S": "891", "V2": "73.1", "V2/V1": "2.44"}, "both")
    expect_values(s, {"U": fmt3(h["u"]), "T": fmt3(h["t"]), "S": fmt3(h["s"]), "V2": fmt3(h["v2"]),
                      "V2/V1": fmt3(h["ratio"])}, "hand")
    expect_values(screen_dict(by_title(scr, QUAD)), {"B²-4AC": "1860", "T1": "-4.38", "T2": "24.4"}, "quad")


def t_parked_car():
    """V1 = 0: car 2 reaches a parked car D0 ahead at u = sqrt(2 D0/A); no speed ratio."""
    res, rr, scr = one_calc(0, 50, 4, 0)
    s = screen_dict(by_title(scr, SUM))
    expect_values(s, {"T": fmt3(math.sqrt(2 * 50 / 4)), "S": "50.0", "V2": "20.0"}, "parked")
    assert s["T"] == "5.00" and "V2/V1" not in s, s
    q = by_title(scr, QUAD)
    assert "2.00T²+0T-50.0=0" in rows_of(q), rows_of(q)
    expect_values(screen_dict(q), {"B²-4AC": "400", "T1": "-5.00", "T2": "5.00"}, "quad")
    st5 = rows_of(by_title(scr, "STEP 5  CAR 2 SPEED"))
    assert "CAR 1 IS PARKED (V1 IS 0)" in st5 and not any(r.startswith("V2/V1") for r in st5), st5
    # parked with a delay: car 2 drives the same 5.00 s, caught at t = 8.00 s after time 0
    res, rr, scr = one_calc(0, 50, 4, 3)
    expect_values(screen_dict(by_title(scr, SUM)), {"U": "5.00", "T": "8.00", "S": "50.0", "V2": "20.0"}, "parked+delay")
    # another: 12.5 m at 2.5 m/s^2 -> sqrt(10) = 3.162 s, v2 = 7.906
    res, rr, scr = one_calc(0, 12.5, 2.5, 0)
    expect_values(screen_dict(by_title(scr, SUM)), {"T": "3.16", "S": "12.5", "V2": "7.91"}, "parked 2")


def t_more_hand_values():
    for v1, d0, a, td in [(25, 0, 5, 0), (20, 50, 2, 0), (15, 0, 2.5, 4), (12, 30, 1.5, 1.5), (40, 0, 8, 0.5),
                          (8.5, 10, 0.75, 3)]:
        res, rr, scr = one_calc(v1, d0, a, td)
        h = hand(v1, d0, a, td)
        s = screen_dict(by_title(scr, SUM))
        want = {"S": fmt3(h["s"]), "V2": fmt3(h["v2"]), "V2/V1": fmt3(h["ratio"])}
        if td > 0:
            want.update({"U": fmt3(h["u"]), "T": fmt3(h["t"])})
        else:
            want["T"] = fmt3(h["u"])
        expect_values(s, want, (v1, d0, a, td))
        expect_values(screen_dict(by_title(scr, QUAD)), {"B²-4AC": fmt3(h["disc"]), "T2": fmt3(h["u"])}, "quad")
        if d0 or td:
            assert h["ratio"] > 2 and float(s["V2/V1"]) >= 2.0


def t_twice_rule_property():
    """Side-by-side start (D0 = 0, TD = 0): u = 2 V1/A, S = 2 V1^2/A and V2/V1 = 2.00 always."""
    rng = random.Random(5)
    for _ in range(40):
        v1 = round(rng.uniform(0.5, 60), rng.choice([0, 1, 2]))
        a = round(rng.uniform(0.2, 12), rng.choice([1, 2]))
        res, rr, scr = one_calc(v1, 0, a, 0)
        s = screen_dict(by_title(scr, SUM))
        assert s["V2/V1"] == "2.00", (v1, a, s)
        assert close3(s["T"], 2 * v1 / a) and close3(s["S"], 2 * v1 * v1 / a) and close3(s["V2"], 2 * v1), (v1, a, s)


# ------------------------------------------------------------------------------ menu paths
def t_menu_path_and_back():
    res = run([6, 2, 30, 0, 3, 0, 2, 30, 100, 3, 0, 7, 7])
    assert_clean(res)
    menus = [(e[1], e[3]) for e in res.events if e[0] == "menu"]
    assert menus == [(P1, 6), (P2, 2), (P2, 2), (P2, 7), (P1, 7)], menus
    segs = segments(res)
    compare_screens(segs[0], ref.run(30, 0, 3, 0), "first")
    compare_screens(segs[1], ref.run(30, 100, 3, 0), "second")
    assert res.angle == "Degree"


def t_river_then_chase_session():
    """Page 2 option 1 then option 2 in one session: each program is independent of the other."""
    res = run([6, 1, 6, 3, 120, 2, 30, 0, 3, 2, 1, 3, 5, 90, 7, 7])
    assert_clean(res)
    menus = [(e[1], e[3]) for e in res.events if e[0] == "menu"]
    assert menus == [(P1, 6), (P2, 1), (P2, 2), (P2, 1), (P2, 7), (P1, 7)], menus
    compare_screens(segments(res, 2)[0], ref.run(30, 0, 3, 2), "chase")
    river = segments(res, 1)
    assert [rows_of(s)[0] for s in river[0]] == [s.title for s in zriver.run(6, 3, 120).screens]
    assert [rows_of(s)[0] for s in river[1]] == [s.title for s in zriver.run(3, 5, 90).screens]


def t_session_with_messages():
    res = run([6, 2, 30, 0, 0, 0, 2, 30, 0, 3, 0, 2, 0, 0, 3, 0, 7, 7])
    assert_clean(res)
    segs = segments(res)
    assert len(segs) == 3
    compare_screens(segs[0], ref.run(30, 0, 0, 0), "A=0")
    compare_screens(segs[1], ref.run(30, 0, 3, 0), "ok")
    compare_screens(segs[2], ref.run(0, 0, 3, 0), "together")


def t_seeds():
    for seed in range(6):
        res = run(script(30, 100, 3, 2), seed=seed)
        assert_clean(res)
        compare_screens(segments(res)[0], ref.run(30, 100, 3, 2), f"seed {seed}")


# ------------------------------------------------------------------------------ impossible / edge inputs
EDGE = [
    ((-30, 0, 3, 0), "E1"), ((-1, -1, -1, -1), "E1"), ((-1e99, 0, 3, 0), "E1"),
    ((30, -5, 3, 0), "E2"), ((0, -1, 3, 0), "E2"),
    ((30, 0, 3, -2), "E3"), ((30, 0, 0, -2), "E3"),
    ((2e9, 0, 3, 0), "E4"), ((30, 2e9, 3, 0), "E4"), ((30, 0, 2e9, 0), "E4"), ((30, 0, 3, 2e9), "E4"),
    ((9.99e99, 9.99e99, 9.99e99, 9.99e99), "E4"),
    ((0, 0, 3, 0), "E6"), ((0, 0, 3, 5), "E6"), ((0, 0, -3, 0), "E6"), ((0, 0, 0, 0), "E6"),
    ((30, 0, 0, 0), "E7"), ((30, 0, -3, 0), "E7"), ((0, 10, 0, 0), "E7"), ((30, 100, -1e99, 2), "E7"),
    ((1e-10, 0, 3, 0), "E5"), ((30, 1e-12, 3, 0), "E5"), ((30, 0, 1e-10, 0), "E5"), ((30, 0, 3, 1e-12), "E5"),
    ((0, 1e-99, 3, 0), "E5"), ((30, 0, 1e-99, 0), "E5"), ((9.99e-7, 0, 3, 0), "E5"), ((30, 0, 9.99e-7, 0), "E5"),
    ((30, 5e-7, 3, 1), "E5"), ((30, 1, 3, 5e-7), "E5"),
]


def t_edge_inputs():
    for inp, label in EDGE:
        ctx = f"inputs {inp}"
        res, rr, scr = one_calc(*inp, ctx=ctx)
        assert rr.messages == [label], f"{ctx}: reference messages {rr.messages}, expected {label}"
        assert len(scr) == 2 and rows_of(scr[1]) == list(ref.MESSAGES[label]), f"{ctx}: {scr}"
        for row in rows_of(scr[1]):
            assert not VAL_RE.match(row), f"message row looks like a value: {row!r}"


def t_boundaries():
    """Largest/smallest accepted inputs: no overflow, no error, values equal the reference."""
    big, tiny = 1e9, 1e-6
    for inp in [(big, big, big, big), (big, big, tiny, big), (tiny, big, big, 0), (big, 0, tiny, 0),
                (tiny, 0, big, 0), (0, tiny, tiny, 0), (0, tiny, big, big), (tiny, tiny, tiny, tiny),
                (big, 0, big, tiny), (0, big, tiny, big), (tiny, 0, tiny, 0), (big, tiny, tiny, 0),
                (392190925.66108, 0, tiny, 0), (33726.130987342, 0, 0.001, 0), (0.001, 0.001, 0.001, 0.001),
                (1, 1e-6, 1e9, 0), (1e9, 1e-6, 1e-6, 1e-6)]:
        one_calc(*inp, exact=False)


def t_wide_values():
    """Worst-case 9-character numbers everywhere: nothing truncated, nothing scrolls."""
    for inp in [(30, 0, 3, 0), (30, 100, 3, 2), (0, 50, 4, 0), (0, 50, 4, 3), (30, 100, 3, 0)]:
        res = run(script(*inp), wide=True)
        assert_clean(res, context=f"wide {inp}")


def t_message_wording():
    for label, rows in ref.MESSAGES.items():
        assert len(rows) <= 9, label
        for row in rows:
            assert len(row) <= 26 and not VAL_RE.match(row), (label, row)


# ------------------------------------------------------------------------------ fuzz
def t_fuzz_realistic():
    rng = random.Random(1234)
    for _ in range(150):
        v1 = round(rng.uniform(0, 60), rng.choice([0, 1, 2])) if rng.random() > 0.1 else 0
        d0 = round(rng.uniform(0, 500), rng.choice([0, 1])) if rng.random() > 0.4 else 0
        a = round(rng.uniform(0.1, 15), rng.choice([1, 2])) or 1.0
        td = round(rng.uniform(0, 10), rng.choice([0, 1])) if rng.random() > 0.5 else 0
        if v1 == 0 and d0 == 0:
            d0 = 25
        one_calc(v1, d0, a, td, exact=False)


def t_fuzz_wide():
    rng = random.Random(4321)

    def val():
        r = rng.random()
        if r < 0.15:
            return 0
        mag = 10 ** rng.uniform(-12, 11)
        return float(f"{rng.choice([-1, 1, 1, 1, 1]) * mag:.4g}")

    for _ in range(300):
        one_calc(val(), val(), val(), val(), exact=False, seed=rng.randint(0, 10 ** 6))


def t_fuzz_valid_all_magnitudes():
    """Valid inputs spread over every accepted magnitude (1E-6 ... 1E9, or 0 where allowed): the full
    solution runs (no message), no error/overflow, and every screen matches the reference."""
    rng = random.Random(777)

    def mag(allow0):
        if allow0 and rng.random() < 0.25:
            return 0
        return float(f"{10 ** rng.uniform(-6, 9):.4g}")

    n = 0
    for _ in range(250):
        v1, d0, a, td = mag(True), mag(True), mag(False), mag(True)
        if v1 == 0 and d0 == 0:
            d0 = 1.0
        res, rr, scr = one_calc(v1, d0, a, td, exact=False, seed=rng.randint(0, 10 ** 6))
        assert rr.messages == [], (v1, d0, a, td, rr.messages)
        h = hand(v1, d0, a, td)
        s = screen_dict(by_title(scr, SUM))
        assert close3(s["S"], h["s"]) and close3(s["V2"], h["v2"]), (v1, d0, a, td, s, h)
        n += 1
    assert n == 250


for name, fn in list(globals().items()):
    if name.startswith("t_") and callable(fn):
        c.check(name[2:].replace("_", " "), fn)
sys.exit(c.done())
