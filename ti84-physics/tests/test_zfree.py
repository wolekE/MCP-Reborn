"""Tests for prgmZFREE (menu B, FREE FALL), driven through PHYSOLVE's real menus.

Every run starts at PHYSOLVE page 1, picks 2 (FREE FALL), then a ZFREE option, types the inputs,
and leaves with ZFREE 6 (BACK) + PHYSOLVE 7 (QUIT), so assert_clean() can check that the program
ended without errors, leaks, scrolling or truncated lines. Each Pause screen of ZFREE is compared
with reference/zfree.py (title row, every "NAME = VALUE UNIT" row via fmt3, message rows), and
the required cases are also compared with hand-computed values at 3 significant figures.
"""
import math
import random
import re
import sys

from harness import Checker, run, assert_clean, fmt3, sim, ROOT

sys.path.insert(0, str(ROOT / "tools"))
from tisim import ScriptEnd  # noqa: E402

import zfree as ref  # noqa: E402  (reference/ is on sys.path via harness)

c = Checker("ZFREE")

ZMENU = ref.MENU_TITLE
NUM = r"-?[0-9]+(?:\.[0-9]+)?(?:E-?[0-9]+)?"
VAL_RE = re.compile(r"^(.+?) = (" + NUM + r")(?: (.*))?$")
IS_RE = re.compile(r"^(.+?) IS (" + NUM + r")$")


# ------------------------------------------------------------------------------ helpers
def script(option, *inputs):
    """PHYSOLVE -> 2 FREE FALL -> option -> inputs -> 6 BACK -> 7 QUIT."""
    return [2, option, *inputs, 6, 7]


def rows_of(screen):
    return [row.rstrip() for row in screen if row.strip()]


def values_of(screen):
    """[(name, value_str, unit)] for every 'NAME = VALUE UNIT' row and 'NAME IS VALUE' row."""
    out = []
    for row in rows_of(screen):
        m = VAL_RE.match(row)
        if m:
            out.append((m.group(1).strip(), m.group(2), (m.group(3) or "").strip()))
            continue
        m = IS_RE.match(row)
        if m:
            out.append((m.group(1).strip() + " IS", m.group(2), ""))
    return out


def segments(res):
    """Split a run into ZFREE visits: [(option chosen, [screens after that choice])]."""
    segs, cur = [], None
    for e in res.events:
        if e[0] == "menu" and e[1] == ZMENU:
            cur = (e[3], [])
            segs.append(cur)
        elif e[0] == "menu":
            cur = None
        elif e[0] == "screen" and cur is not None:
            cur[1].append(e[1])
    return segs


def shown(x):
    return x if isinstance(x, str) else fmt3(x)


def compare_with_ref(screens, rr, ctx=""):
    """Screen-by-screen comparison of the simulator output with the reference Result."""
    compare_screens(screens, rr.screens, ctx)


def compare_screens(screens, ref_screens, ctx=""):
    titles = [rows_of(s)[0] if rows_of(s) else "" for s in screens]
    want_titles = [s.title for s in ref_screens]
    assert titles == want_titles, f"{ctx}: screen titles {titles}\n  expected {want_titles}"
    for scr, want in zip(screens, ref_screens):
        got = values_of(scr)
        exp = [(n, shown(v), u) for n, v, u in want.values]
        assert got == exp, f"{ctx}: screen {want.title!r}\n  shows    {got}\n  expected {exp}\n  " + \
            "\n  ".join(rows_of(scr))
        if want.rows:
            tail = rows_of(scr)[-len(want.rows):]
            assert tail == list(want.rows), f"{ctx}: message rows {tail}, expected {list(want.rows)}"


def one_calc(option, *inputs, ctx=None, **kw):
    """Run one ZFREE calculation through PHYSOLVE; check clean + return to the ZFREE menu +
    match with the reference. Returns (sim result, reference result)."""
    ctx = ctx or f"option {option} inputs {inputs}"
    res = run(script(option, *inputs), **kw)
    assert_clean(res, context=ctx)
    segs = segments(res)
    assert len(segs) == 2 and segs[0][0] == option and segs[1][0] == 6, \
        f"{ctx}: expected the ZFREE menu again after the calculation, got {[(s[0], len(s[1])) for s in segs]}"
    assert segs[1][1] == [], f"{ctx}: screens after BACK"
    rr = ref.run(option, *inputs)
    compare_with_ref(segs[0][1], rr, ctx)
    return res, rr


def summary(res):
    return {n: v for n, v, u in values_of(res.screens[-1])}


def expect_values(got, want, ctx):
    for k, v in want.items():
        assert k in got, f"{ctx}: summary has no {k!r}: {got}"
        assert got[k] == v, f"{ctx}: {k} shows {got[k]!r}, hand-computed {v!r}"


# ------------------------------------------------------------------------------ setup
OWN_DEPS = ("ZFREE", "PHYSOLVE", "ZFMT", "ZLINE", "ZQUAD")


def t_syntax():
    """harness.sim() refuses to load if ANY program has a syntax error. A program ZFREE only calls
    from option 5 (ZVOVF, written by someone else) must not fail ZFREE's tests: note it instead."""
    try:
        sim()
    except AssertionError as e:
        lines = str(e).splitlines()[1:]
        mine = [ln for ln in lines if ln.split(":")[0] in OWN_DEPS]
        others = [ln for ln in lines if ln not in mine]
        if others:
            print("       NOTE: syntax errors in programs ZFREE does not own:\n         "
                  + "\n         ".join(others[:5]))
        assert not mine, "\n".join(mine)


# ------------------------------------------------------------------------------ required cases
def t_thrown_up_19_6():
    res, rr = one_calc(2, 19.6)
    s = summary(res)
    # T_top = 19.6/9.8 = 2 s; H_max = 19.6^2/19.6 = 19.6 m; total 2*2 = 4 s; VF = -19.6 m/s
    expect_values(s, {"V0": "19.6", "T TO TOP": "2.00", "MAX HEIGHT": "19.6", "T TOTAL": "4.00",
                      "VF": "-19.6"}, "thrown up 19.6")
    assert rows_of(res.screens[-1])[0] == "SUMMARY (UP, SAME LEVEL)"
    assert "VF = -19.6 M/S (DOWN)" in rows_of(res.screens[-1])
    assert "T TO TOP = 2.00 S" in rows_of(res.screens[-1])
    assert "MAX HEIGHT = 19.6 M" in rows_of(res.screens[-1])
    assert "T TOTAL = 4.00 S" in rows_of(res.screens[-1])


def t_dropped_45():
    res, rr = one_calc(1, 45)
    s = summary(res)
    # T = sqrt(2*45/9.8) = 3.0305 s; VF = -sqrt(2*9.8*45) = -29.698 m/s
    expect_values(s, {"V0": "0", "T TO TOP": "0", "MAX HEIGHT": "45.0", "T TOTAL": "3.03",
                      "VF": "-29.7"}, "dropped 45")
    assert "VF = -29.7 M/S (DOWN)" in rows_of(res.screens[-1])
    step2 = res.screens[-2]
    assert "VF² IS 882" in rows_of(step2) and "VF=-√(882)" in rows_of(step2), rows_of(step2)


def t_thrown_up_roof():
    res, rr = one_calc(4, 15, 10)
    s = summary(res)
    # T_top = 10/9.8 = 1.0204; rise = 100/19.6 = 5.102; above ground 20.102;
    # 4.9T^2 - 10T - 15 = 0 -> T = (10 + sqrt(394))/9.8 = 3.0459; VF = -sqrt(394) = -19.849;
    # top -> ground sqrt(2*20.102/9.8) = 2.0255
    expect_values(s, {"V0": "10.0", "T TO TOP": "1.02", "ABOVE LAUNCH": "5.10", "ABOVE GROUND": "20.1",
                      "T TOP TO GND": "2.03", "T TOTAL": "3.05", "VF": "-19.8"}, "up from roof")
    quad = [scr for scr in res.screens if rows_of(scr)[0] == "SOLVE QUADRATIC FOR T"][0]
    q = {n: v for n, v, u in values_of(quad)}
    # roots of 4.9T^2 - 10T - 15 = 0: (10 -/+ sqrt(394))/9.8 = -1.0050, 3.0459
    expect_values(q, {"T1": "-1.01", "T2": "3.05", "B²-4AC": "394", "T TOTAL": "3.05"}, "roof quadratic")
    assert "4.90T²-10.0T-15.0=0" in rows_of(quad), rows_of(quad)
    assert "T1<0 IS BEFORE THE THROW," in rows_of(quad)


def t_thrown_down():
    res, rr = one_calc(3, 20, 5)
    s = summary(res)
    # V0 = -5; 4.9T^2 + 5T - 20 = 0 -> T = (-5 + sqrt(417))/9.8 = 1.5737; VF = -sqrt(417) = -20.421
    expect_values(s, {"V0": "-5.00", "MAX HEIGHT": "20.0", "T TOTAL": "1.57", "VF": "-20.4"}, "thrown down")
    quad = [scr for scr in res.screens if rows_of(scr)[0] == "SOLVE QUADRATIC FOR T"][0]
    q = {n: v for n, v, u in values_of(quad)}
    expect_values(q, {"T1": "-2.59", "T2": "1.57", "B²-4AC": "417"}, "thrown down quadratic")
    assert "4.90T²+5.00T-20.0=0" in rows_of(quad), rows_of(quad)
    assert any("NO TIME TO TOP" in row for row in rows_of(res.screens[0]))
    assert any("T TO TOP- NONE" in row for row in rows_of(res.screens[-1]))


def t_more_hand_values():
    # dropped 20 m: T = sqrt(40/9.8) = 2.0203, VF = -sqrt(392) = -19.799
    res, _ = one_calc(1, 20)
    expect_values(summary(res), {"T TOTAL": "2.02", "VF": "-19.8", "MAX HEIGHT": "20.0"}, "dropped 20")
    # thrown up 10 m/s, same level: 1.02 s, 5.10 m, 2.04 s, -10.0 m/s
    res, _ = one_calc(2, 10)
    expect_values(summary(res), {"T TO TOP": "1.02", "MAX HEIGHT": "5.10", "T TOTAL": "2.04", "VF": "-10.0"},
                  "up 10")
    # thrown down 10 m/s from 50 m: 4.9T^2+10T-50=0 -> T=(-10+sqrt(1080))/9.8 = 2.3330; VF=-sqrt(1080)=-32.863
    res, _ = one_calc(3, 50, 10)
    expect_values(summary(res), {"V0": "-10.0", "T TOTAL": "2.33", "VF": "-32.9"}, "down 10 from 50")
    # thrown up 20 m/s from a 30 m cliff: T_top 2.0408, rise 20.408, above ground 50.408,
    # total (20+sqrt(988))/9.8 = 5.2482, VF=-sqrt(988)=-31.432, top->ground sqrt(2*50.408/9.8)=3.2074
    res, _ = one_calc(4, 30, 20)
    expect_values(summary(res), {"T TO TOP": "2.04", "ABOVE LAUNCH": "20.4", "ABOVE GROUND": "50.4",
                                 "T TOTAL": "5.25", "VF": "-31.4", "T TOP TO GND": "3.21"}, "up 20 from 30")


# ------------------------------------------------------------------------------ menu paths
def t_back():
    res = run([2, 6, 7])
    assert_clean(res)
    menus = [(e[1], e[3]) for e in res.events if e[0] == "menu"]
    assert menus == [("PHYSOLVE 1/2  KINEMATICS", 2), (ZMENU, 6), ("PHYSOLVE 1/2  KINEMATICS", 7)], menus
    assert res.screens == [], "BACK should not show any screen"


def t_menu_shape():
    res = run([2, 6, 7])
    items = [e[2] for e in res.events if e[0] == "menu" and e[1] == ZMENU][0]
    assert len(items) <= 7 and len(ZMENU) <= 24, items
    assert all(len(t) <= 22 for t in items), items
    assert items[-1] == "BACK", items
    assert items[4] == "VOVFSTA (A=-9.8)", items


def t_all_options_in_one_session():
    """Several calculations in a row (state from one must not leak into the next)."""
    plan = [(1, 45), (2, 19.6), (3, 20, 5), (4, 15, 10), (1, 7.5), (4, 2.5, 3.3), (3, 100, 0.5), (2, 0.4)]
    keys = [2]
    for opt, *inp in plan:
        keys += [opt, *inp]
    keys += [6, 7]
    res = run(keys)
    assert_clean(res)
    segs = segments(res)
    assert [s[0] for s in segs] == [p[0] for p in plan] + [6], [s[0] for s in segs]
    for (opt, *inp), (_, screens) in zip(plan, segs):
        compare_with_ref(screens, ref.run(opt, *inp), f"session {opt} {inp}")


def t_option5_calls_zvovf():
    """Option 5 does 2->K and prgmZVOVF, then shows the ZFREE menu again. ZVOVF's own screens and
    inputs are not checked (another program); its menus are left through BACK/QUIT."""
    src = (ROOT / "src" / "ZFREE.txt").read_text(encoding="utf-8").split("\n")
    i = src.index("prgmZVOVF")
    assert src[i - 1] == "2→K" and src[i + 1] == "Goto M", src[i - 2:i + 2]
    st = {"z": 0, "p": 0, "k": None, "back": False, "n_in": 0}

    def responder(kind, info):
        s = sim()
        inside = "ZVOVF" in s.res.calls and not st["back"]
        if inside and st["k"] is None:
            st["k"] = s.vars.get("K")
        if kind == "menu":
            title, items = info
            if title == ZMENU:
                st["z"] += 1
                if st["z"] == 1:
                    return 5
                st["back"] = True
                return 6
            if title.startswith("PHYSOLVE"):
                st["p"] += 1
                return 2 if st["p"] == 1 else len(items)
            for j, t in enumerate(items, 1):           # a ZVOVF menu: leave it
                if re.search(r"BACK|QUIT|EXIT", t):
                    return j
            return len(items)
        st["n_in"] += 1                                 # a ZVOVF input: a valid free-fall problem
        if st["n_in"] > 40:
            raise ScriptEnd()
        p = str(info).upper()
        if p.startswith("V0"):
            return 0
        if p.startswith("T"):
            return 2
        if p.startswith("A"):
            return -9.8
        return 999

    res = run([], responder=responder)
    assert "ZVOVF" in res.calls, res.calls
    if (res.error is not None and res.error_at and res.error_at[0] == "ZVOVF") or (res.waiting and not st["back"]):
        k = st["k"] if st["k"] is not None else res.vars.get("K")
        assert float(k) == 2, f"K at the ZVOVF call was {k}"
        print(f"       NOTE: ZVOVF (not ZFREE) stopped: {res.error or 'still asking for input'} at {res.error_at}")
        return
    assert st["k"] is not None and float(st["k"]) == 2, f"K at the ZVOVF call was {st['k']}"
    assert_clean(res)
    assert st["z"] == 2, "the ZFREE menu was not shown again after ZVOVF returned"
    menus = [(e[1], e[3]) for e in res.events if e[0] == "menu" and e[1] in (ZMENU,)]
    assert menus == [(ZMENU, 5), (ZMENU, 6)], menus


def t_option5_direct():
    """Run ZFREE by itself: 5 -> ZVOVF (stopped at its first question, or returns) -> 6 BACK."""
    st = {"z": 0, "k": None}

    def responder(kind, info):
        s = sim()
        if kind == "menu" and info[0] == ZMENU:
            st["z"] += 1
            if st["z"] == 2:
                st["k"] = s.vars.get("K")
            return 5 if st["z"] == 1 else 6
        st["k"] = s.vars.get("K")       # ZVOVF asked something: stop here
        raise ScriptEnd()

    res = run([], program="ZFREE", responder=responder)
    assert "ZVOVF" in res.calls
    if res.error is not None and res.error_at and res.error_at[0] == "ZVOVF":
        assert float(res.vars["K"]) == 2, res.vars["K"]
        print(f"       NOTE: error inside ZVOVF (not ZFREE): {res.error} at {res.error_at}")
        return
    assert res.error is None and not [p for p in res.problems if "ZVOVF" not in p], res.text()
    assert float(st["k"]) == 2, st


# ------------------------------------------------------------------------------ impossible / edge inputs
EDGE = [
    # (option, inputs, expected message labels in order)
    (1, (-5,), ["E1"]), (1, (0,), ["E2"]), (1, (2e9,), ["E9"]), (1, (-1e99,), ["E1"]), (1, (9.99e99,), ["E9"]),
    (2, (-3,), ["E4"]), (2, (0,), ["E5"]), (2, (1.5e9,), ["E9"]), (2, (-1e99,), ["E4"]),
    (3, (-1, 5), ["E1"]), (3, (0, 5), ["E2"]), (3, (20, -5), ["E3"]), (3, (20, 0), ["E6"]),
    (3, (1e10, 5), ["E9"]), (3, (20, 1e10), ["E9"]), (3, (0, 0), ["E2"]), (3, (-1, -1), ["E1"]),
    (3, (0, -5), ["E3"]), (3, (1e-6, 1e6), ["E8"]),
    (4, (-1, 5), ["E1"]), (4, (15, -10), ["E4"]), (4, (0, 19.6), ["E7"]), (4, (0, 0), ["E7", "E5"]),
    (4, (20, 0), ["E6"]), (4, (1e10, 1), ["E9"]), (4, (1, 1e10), ["E9"]), (4, (0, -2), ["E4"]),
]


def t_edge_inputs():
    for opt, inp, msgs in EDGE:
        ctx = f"option {opt} inputs {inp}"
        res, rr = one_calc(opt, *inp, ctx=ctx)
        assert rr.messages == msgs, f"{ctx}: reference messages {rr.messages}, expected {msgs}"
        firsts = [ref.MESSAGES[m][0] for m in msgs]
        shown_rows = [r for scr in res.screens for r in rows_of(scr)]
        for f in firsts:
            assert f in shown_rows, f"{ctx}: message {f!r} not shown"


def t_redirects_compute_right_values():
    # thrown down / up from 20 m with speed 0 -> solved as dropped from 20 m
    for opt in (3, 4):
        res, _ = one_calc(opt, 20, 0)
        expect_values(summary(res), {"V0": "0", "T TOTAL": "2.02", "VF": "-19.8", "MAX HEIGHT": "20.0"},
                      f"option {opt} speed 0")
        assert rows_of(res.screens[-1])[0] == "SUMMARY (DROPPED)"
    # thrown up from H = 0 -> solved as thrown up, same level
    res, _ = one_calc(4, 0, 19.6)
    expect_values(summary(res), {"T TO TOP": "2.00", "MAX HEIGHT": "19.6", "T TOTAL": "4.00", "VF": "-19.6"},
                  "up from H=0")


def t_boundaries():
    # the largest accepted inputs and tiny ones must not overflow / error
    for opt, inp in [(1, (1e9,)), (2, (1e9,)), (3, (1e9, 1e9)), (4, (1e9, 1e9)), (3, (1e-99, 1e-99)),
                     (4, (1e-99, 1e-99)), (1, (1e-99,)), (2, (1e-99,)), (3, (1e9, 1e-9)), (4, (1e-9, 1e9)),
                     (1, (0.001,)), (4, (0.001, 0.001)), (3, (0.001, 0.001))]:
        res = run(script(opt, *inp))
        assert_clean(res, context=f"option {opt} {inp}")
        segs = segments(res)
        assert [s[0] for s in segs] == [opt, 6], segs


# ------------------------------------------------------------------------------ fuzz
def rnd_val(rng, lo, hi):
    return round(rng.uniform(lo, hi), rng.choice([0, 1, 2, 3]))


def t_fuzz_realistic():
    """Typical test-problem numbers: every screen value equals the reference."""
    rng = random.Random(2024)
    n = 0
    for _ in range(160):
        opt = rng.choice([1, 2, 3, 4])
        h = rnd_val(rng, 0.1, 500)
        s = rnd_val(rng, 0.1, 80)
        h = h or 1.0
        s = s or 1.0
        inp = {1: (h,), 2: (s,), 3: (h, s), 4: (h, s)}[opt]
        one_calc(opt, *inp)
        n += 1
    assert n == 160


def t_fuzz_wide():
    """Any numbers (negative, zero, tiny, huge): never an error/leak/scroll/truncation, always back to the
    ZFREE menu, the same screens (titles) as the reference, and values equal to the reference whenever
    the problem is not numerically ill-conditioned."""
    rng = random.Random(77)
    for k in range(220):
        opt = rng.choice([1, 2, 3, 4])

        def val():
            r = rng.random()
            if r < 0.08:
                return 0
            mag = 10 ** rng.uniform(-12, 10.5)
            return float(f"{rng.choice([-1, 1, 1, 1]) * mag:.4g}")

        inp = {1: (val(),), 2: (val(),), 3: (val(), val()), 4: (val(), val())}[opt]
        ctx = f"wide #{k} option {opt} {inp}"
        res = run(script(opt, *inp))
        assert_clean(res, context=ctx)
        segs = segments(res)
        assert [s[0] for s in segs] == [opt, 6], f"{ctx}: {[(s[0]) for s in segs]}"
        rr = ref.run(opt, *inp)
        screens = segs[0][1]
        ill = (opt in (3, 4) and 0 < inp[0] <= 1e9 and 0 < inp[1] <= 1e9
               and inp[1] ** 2 / inp[0] >= 1e8)           # cancellation in a quadratic root
        if not ill:
            compare_with_ref(screens, rr, ctx)
        else:
            # TI's 14-digit decimals and Python floats may differ in the cancelling root: compare the
            # screens before the quadratic; afterwards it must end in a summary or the E8 message.
            k = [s.title for s in rr.screens].index("SOLVE QUADRATIC FOR T")
            compare_screens(screens[:k], rr.screens[:k], ctx)
            assert rows_of(screens[-1])[0] in (
                "SUMMARY (THROWN DOWN)", "SUMMARY (UP FROM HEIGHT)", "SOLVE QUADRATIC FOR T"), ctx


def t_reference_physics():
    """The reference itself agrees with closed-form kinematics (independent of the TI code)."""
    rng = random.Random(5)
    g = 9.8
    for _ in range(500):
        h = rng.uniform(0.01, 1000)
        v = rng.uniform(0.01, 100)
        d = ref.run(1, h).summary
        assert math.isclose(d["T TOTAL"], math.sqrt(2 * h / g)) and math.isclose(d["VF"], -g * d["T TOTAL"])
        u = ref.run(2, v).summary
        assert math.isclose(u["T TO TOP"], v / g) and math.isclose(u["MAX HEIGHT"], v * v / (2 * g))
        assert math.isclose(u["T TOTAL"], 2 * v / g) and math.isclose(u["VF"], -v)
        dn = ref.run(3, h, v).summary
        t = dn["T TOTAL"]
        assert t > 0 and math.isclose(-v * t - 0.5 * g * t * t, -h, rel_tol=1e-9)
        assert math.isclose(dn["VF"], -v - g * t, rel_tol=1e-9)        # VF = V0 + AT
        up = ref.run(4, h, v).summary
        t = up["T TOTAL"]
        assert t > 0 and math.isclose(v * t - 0.5 * g * t * t, -h, rel_tol=1e-9, abs_tol=1e-9)
        assert math.isclose(up["VF"], v - g * t, rel_tol=1e-9)
        assert math.isclose(up["T TO TOP"] + up["T TOP TO GND"], t, rel_tol=1e-9)
        assert math.isclose(up["ABOVE GROUND"], h + v * v / (2 * g))


def t_screens_fit():
    """Every screen of the required cases: <= 10 rows, <= 26 columns, no 'X = word' prose rows."""
    for opt, inp in [(1, (45,)), (2, (19.6,)), (3, (20, 5)), (4, (15, 10)), (3, (1e-4, 9.9e-5)),
                     (4, (1.23e-4, 1.23e-4)), (3, (987654321, 987654321)), (4, (987654321, 987654321))]:
        res = run(script(opt, *inp))
        assert_clean(res, context=str((opt, inp)))
        for scr in res.screens:
            assert len(scr) <= 10 and all(len(r) <= 26 for r in scr)
            for row in rows_of(scr):
                if " = " in row:
                    assert VAL_RE.match(row), f"row {row!r} has ' = ' but is not NAME = VALUE UNIT"


c.check("ZFREE and its helpers have no syntax errors", t_syntax)
c.check("required: thrown up 19.6 m/s -> 2.00 s, 19.6 m, 4.00 s, -19.6 m/s", t_thrown_up_19_6)
c.check("required: dropped from 45 m -> 3.03 s, -29.7 m/s", t_dropped_45)
c.check("required: up 10 m/s from 15 m roof -> 5.10 m, -19.8 m/s, 3.05 s", t_thrown_up_roof)
c.check("thrown down 5 m/s from 20 m -> 1.57 s, -20.4 m/s", t_thrown_down)
c.check("more hand-computed cases (all four options)", t_more_hand_values)
c.check("BACK returns to PHYSOLVE page 1", t_back)
c.check("ZFREE menu: <=7 options, text lengths, BACK, option 5", t_menu_shape)
c.check("all options in one session match the reference", t_all_options_in_one_session)
c.check("option 5: 2->K, prgmZVOVF, back to the ZFREE menu (via PHYSOLVE)", t_option5_calls_zvovf)
c.check("option 5: K=2 when ZVOVF starts (ZFREE run directly)", t_option5_direct)
c.check("impossible/edge inputs give message screens, never errors", t_edge_inputs)
c.check("speed 0 -> dropped, H=0 -> same level: right values", t_redirects_compute_right_values)
c.check("largest/smallest accepted inputs: no overflow or error", t_boundaries)
c.check("fuzz (realistic numbers): every screen value = reference", t_fuzz_realistic)
c.check("fuzz (any numbers): clean, back to menu, matches reference", t_fuzz_wide)
c.check("reference agrees with closed-form kinematics", t_reference_physics)
c.check("screens fit 26x10, value rows parseable", t_screens_fit)
sys.exit(c.done())
