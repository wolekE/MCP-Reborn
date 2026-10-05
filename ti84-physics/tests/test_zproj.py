"""Tests for prgmZPROJ (PHYSOLVE items C HORIZONTAL LAUNCH, D ANGLED LAUNCH, E THROW LAB),
driven through PHYSOLVE's real menus.

Every run starts at PHYSOLVE page 1, picks 3 / 4 / 5, answers ZPROJ's menu and inputs, and
finally picks 7 (QUIT) on PHYSOLVE page 1, so assert_clean() can check that the whole program
ended with no calculator error, LEAK, SCROLL or TRUNCATED line. Every Pause screen ZPROJ shows
is compared row by row with reference/zproj.py (numbers formatted with fmt3, like prgmZFMT), and
the required cases are also compared with hand-computed values at 3 significant figures.

    python3 tests/test_zproj.py
"""
import itertools
import math
import os
import random
import re
import sys
from decimal import Decimal

import harness
from harness import Checker, run, assert_clean, fmt3, ROOT

import zproj as ref  # noqa: E402  (reference/ is on sys.path via harness)

c = Checker("ZPROJ")

MAIN = "PHYSOLVE 1/2  KINEMATICS"
DEPS = ("PHYSOLVE", "ZPROJ", "ZFMT", "ZLINE", "ZQUAD")
NUM = r"-?[0-9]+(?:\.[0-9]+)?(?:E-?[0-9]+)?"
VAL_RE = re.compile(r"^(.+?) = (" + NUM + r")(?:(?: |°)(.*))?$")
ITEM = {1: 3, 2: 4, 3: 5}          # K -> PHYSOLVE page-1 option


# ------------------------------------------------------------------------------ simulator
def setup_sim():
    """harness.sim() refuses to load if ANY program has a syntax error. Programs that ZPROJ's
    menu paths never run (written by other people at the same time) must not fail these tests:
    if only they are broken, run with a simulator that loads just PHYSOLVE and ZPROJ's helpers."""
    try:
        return harness.sim()
    except AssertionError as e:
        lines = str(e).splitlines()[1:]
        mine = [ln for ln in lines if ln.split(":")[0] in DEPS]
        if mine:
            raise
        print("       NOTE: syntax errors in programs ZPROJ does not use:\n         "
              + "\n         ".join(lines[:5]))
        from tisim import TISim, Program, load_tokens_from_src, load_tokens_from_8xp
        use_src = os.environ.get("TISIM_FROM", "src") != "8xp"
        progs = {}
        for name in DEPS:
            if use_src:
                progs[name] = Program(name, load_tokens_from_src(ROOT / "src" / f"{name}.txt"))
            else:
                progs[name] = Program(name, load_tokens_from_8xp(ROOT / "8xp" / f"{name}.8xp"))
        harness._SIM = TISim(progs)
        errs = harness._SIM.syntax_errors()
        assert not errs, "\n".join(errs)
        return harness._SIM


# ------------------------------------------------------------------------------ helpers
def rows_of(screen):
    rows = list(screen)
    while rows and rows[-1] == "":
        rows.pop()
    return [r.rstrip() for r in rows]


def values_of(rows):
    """{name: value_str} for every 'NAME = VALUE UNIT' row."""
    out = {}
    for row in rows:
        m = VAL_RE.match(row)
        if m:
            out[m.group(1)] = m.group(2)
    return out


def part(res):
    """The ZPROJ part of a run: (menus [(title, choice)], screens) between the first PHYSOLVE menu
    and the next one. Also checks that the run is: PHYSOLVE -> ZPROJ -> PHYSOLVE -> QUIT."""
    mains = [i for i, e in enumerate(res.events) if e[0] == "menu" and e[1] == MAIN]
    assert len(mains) == 2, f"expected PHYSOLVE's menu twice, got {len(mains)}\n{res.text()}"
    assert res.events[mains[1]][3] == 7, "the run must end with QUIT"
    assert mains[1] == len(res.events) - 1 or all(e[0] != "screen" for e in res.events[mains[1]:]), \
        "screens after QUIT"
    seg = res.events[mains[0] + 1:mains[1]]
    menus = [(e[1], e[3]) for e in seg if e[0] == "menu"]
    screens = [rows_of(e[1]) for e in seg if e[0] == "screen"]
    return menus, screens


EPS = 1e-9


def _variants(kind, tmpl, nums, tolerant):
    if tolerant:
        lists = []
        for x in nums:
            opts = [fmt3(x)]
            for f in (1 + EPS, 1 - EPS):
                s = fmt3(x * f)
                if s not in opts:
                    opts.append(s)
            lists.append(opts)
    else:
        lists = [[fmt3(x)] for x in nums]
    for combo in itertools.product(*lists):
        text = tmpl.format(*combo)
        if kind == "zline":
            yield [text[i:i + 26] for i in range(0, len(text), 26)]
        else:
            yield [text]


def match_screen(got, want, tolerant=False):
    """Row-by-row comparison of one simulator screen with one reference Screen."""
    pos = 0
    for kind, tmpl, nums in want.lines:
        first = None
        for rows in _variants(kind, tmpl, nums, tolerant):
            first = first or rows
            if got[pos:pos + len(rows)] == rows:
                pos += len(rows)
                break
        else:
            return f"row {pos + 1}: expected {first!r}, screen shows {got[pos:pos + len(first)]!r}"
    if pos != len(got):
        return f"extra rows on screen: {got[pos:]!r}"
    return None


TOLERANT_USED = []


def compare(screens, rr, ctx):
    assert len(screens) == len(rr.screens), (
        f"{ctx}: {len(screens)} screens, reference has {len(rr.screens)}\n  shown: "
        + str([s[0] if s else "" for s in screens]) + "\n  ref:   " + str([s.title for s in rr.screens]))
    for k, (got, want) in enumerate(zip(screens, rr.screens)):
        err = match_screen(got, want)
        if err:
            err2 = match_screen(got, want, tolerant=True)
            assert err2 is None, f"{ctx}: screen {k + 1} ({want.title!r}): {err}\n  " + "\n  ".join(got)
            TOLERANT_USED.append(ctx)


def calc(k, *keys, ctx=None):
    """Run PHYSOLVE -> item C/D/E -> keys -> QUIT; check it is clean and matches the reference.
    Returns (sim result, reference result, ZPROJ screens)."""
    ctx = ctx or f"K={k} keys={keys}"
    res = run([ITEM[k], *keys, 7])
    assert_clean(res, context=ctx)
    menus, screens = part(res)
    rr = ref.run(k, *keys)
    assert menus == rr.menus, f"{ctx}: menus {menus}, reference {rr.menus}"
    compare(screens, rr, ctx)
    for scr in screens:
        assert len(scr) <= 10 and all(len(r) <= 26 for r in scr), f"{ctx}: screen too big {scr}"
        for row in scr:
            if " = " in row:
                assert VAL_RE.match(row), f"{ctx}: row {row!r} has ' = ' but is not NAME = VALUE UNIT"
    if rr.summary:
        shown = values_of(screens[-1])
        for name, x in rr.summary.items():
            assert name in shown, f"{ctx}: summary has no {name}: {screens[-1]}"
            want = fmt3(x)
            if shown[name] != want:
                assert shown[name] in (fmt3(x * (1 + EPS)), fmt3(x * (1 - EPS))), \
                    f"{ctx}: summary {name} shows {shown[name]}, reference {want}"
    return res, rr, screens


def summary(screens):
    return values_of(screens[-1])


def expect(got, want, ctx):
    """want: {name: 3-s.f. string computed by hand}."""
    for name, v in want.items():
        assert name in got, f"{ctx}: no {name!r} on the screen: {got}"
        assert got[name] == v, f"{ctx}: {name} shows {got[name]!r}, hand-computed {v!r}"


def screen_with(screens, title):
    for s in screens:
        if s and s[0] == title:
            return s
    raise AssertionError(f"no screen titled {title!r}: {[x[0] for x in screens if x]}")


def message_shown(screens, label):
    first = ref.MESSAGES[label][0]
    return any(first in s for s in screens)


# ------------------------------------------------------------------------------ setup
def t_syntax():
    setup_sim()


def t_lint_clean():
    import subprocess
    out = subprocess.run([sys.executable, str(ROOT / "tools" / "build.py"), "--check", "--only", "ZPROJ"],
                         capture_output=True, text=True)
    assert out.returncode == 0, out.stdout + out.stderr


# ------------------------------------------------------------------------------ required cases (D)
def t_angled_level_25_50():
    res, rr, scr = calc(2, 25, 50, 0)
    s = summary(scr)
    # vx = 25cos50 = 16.0697, v0y = 25sin50 = 19.1511, T = 2(19.1511)/9.8 = 3.9084,
    # R = 16.0697(3.9084) = 62.807, hmax = 19.1511^2/19.6 = 18.712, t_top = 1.9542
    expect(s, {"VX": "16.1", "V0Y": "19.2", "T TOP": "1.95", "MAX H": "18.7", "T FLIGHT": "3.91",
               "RANGE": "62.8", "HIT SPEED": "25.0", "ANGLE": "50.0"}, "25 m/s at 50 deg")
    assert "V0Y = 19.2 M/S (UP)" in scr[-1] and "ANGLE = 50.0° BELOW" in scr[-1], scr[-1]
    assert abs(rr.summary["VX"] - 16.07) < 0.005 and abs(rr.summary["V0Y"] - 19.15) < 0.005
    q = screen_with(scr, "SOLVE QUADRATIC FOR T")
    assert "4.90T²-19.2T+0=0" in q and "T1 IS 0 (THE LAUNCH), SO" in q, q
    expect(values_of(q), {"T1": "0", "T2": "3.91", "B²-4AC": "367"}, "level quadratic")
    s4 = screen_with(scr, "STEP 4  RANGE (HORIZONTAL)")
    assert "LEVEL GROUND- T=2V0Y/9.8" in s4 and "RANGE=(16.1)(3.91)" in s4, s4


def t_angled_from_1m():
    res, rr, scr = calc(2, 5.0, 30, 1.0)
    s = summary(scr)
    # vx = 4.3301, v0y = 2.5; 4.9T^2 - 2.5T - 1 = 0 -> T = (2.5 + sqrt(25.85))/9.8 = 0.77391;
    # x = 4.3301(0.77391) = 3.3511; rise = 6.25/19.6 = 0.31888; above landing 1.31888
    expect(s, {"VX": "4.33", "V0Y": "2.50", "T TOP": "0.255", "RISE": "0.319",
               "MAX H": "1.32", "T FLIGHT": "0.774", "RANGE": "3.35"}, "5.0 m/s at 30 from 1.0 m")
    q = screen_with(scr, "SOLVE QUADRATIC FOR T")
    # roots (2.5 -/+ 5.08429)/9.8 = -0.26370, 0.77391
    expect(values_of(q), {"T1": "-0.264", "T2": "0.774", "T FLIGHT": "0.774"}, "from 1 m quadratic")
    assert "4.90T²-2.50T-1.00=0" in q and "T1<0 IS BEFORE THE LAUNCH," in q, q
    # impact: vfy = 2.5 - 9.8(0.77391) = -5.0843; speed sqrt(18.75+25.85) = 6.6783; angle 49.58
    expect(s, {"HIT SPEED": "6.68", "ANGLE": "49.6"}, "from 1 m impact")


def t_angled_from_085m():
    res, rr, scr = calc(2, 4.9, 20, 0.85)
    s = summary(scr)
    # vx = 4.9cos20 = 4.6045, v0y = 4.9sin20 = 1.6759; disc = 2.8086 + 16.66 = 19.4686;
    # T = (1.6759 + 4.4123)/9.8 = 0.62125; R = 4.6045(0.62125) = 2.8606
    expect(s, {"VX": "4.60", "V0Y": "1.68", "T FLIGHT": "0.621", "RANGE": "2.86"}, "4.9 at 20 from 0.85")


# ------------------------------------------------------------------------------ required case (E)
def t_throw_lab_yards():
    res, rr, scr = calc(3, 2, 2.0, 2.4, 50)
    s = summary(scr)
    # R = 50/1.0936 = 45.721 m; vx = 45.721/2.4 = 19.050; v0y = (4.9(5.76) - 2)/2.4 = 10.927;
    # v0 = sqrt(19.050^2 + 10.927^2) = 21.961; angle = atan(10.927/19.050) = 29.84 deg
    expect(s, {"RANGE": "45.7", "VX": "19.1", "V0Y": "10.9", "V0": "22.0", "ANGLE": "29.8",
               "H": "2.00", "T FLIGHT": "2.40"}, "throw lab")
    assert abs(rr.summary["VX"] - 19.05) < 0.005 and abs(rr.summary["V0Y"] - 10.93) < 0.005
    assert abs(rr.summary["V0"] - 21.96) < 0.005
    assert "(FROM 50.0 YD)" in scr[-1] and "ANGLE = 29.8° (ABOVE)" in scr[-1], scr[-1]
    s1 = screen_with(scr, "STEP 1  VX (HORIZONTAL)")
    assert "RANGE=50.0/1.0936" in s1 and "RANGE = 45.7 M" in s1, s1


def t_throw_lab_meters():
    res, rr, scr = calc(3, 1, 0, 2, 20)
    # vx = 20/2 = 10; v0y = 4.9(4)/2 = 9.8; v0 = sqrt(100 + 96.04) = 14.0014; angle atan(0.98) = 44.42
    expect(summary(scr), {"RANGE": "20.0", "VX": "10.0", "V0Y": "9.80", "V0": "14.0", "ANGLE": "44.4"},
           "throw lab meters")
    assert not any("YD" in row for row in scr[-1]), scr[-1]
    assert "YARDS TO METERS- DIVIDE" not in scr[0]


def t_throw_lab_more():
    # thrown downward: H=10, t=1, R=5 m -> v0y = (4.9-10)/1 = -5.1, angle atan2(-5.1, 5) = -45.57
    res, rr, scr = calc(3, 1, 10, 1, 5)
    expect(summary(scr), {"VX": "5.00", "V0Y": "-5.10", "V0": "7.14", "ANGLE": "-45.6"}, "thrown down")
    assert "ANGLE = -45.6° (BELOW)" in scr[-1] and "V0Y = -5.10 M/S (DOWN)" in scr[-1], scr[-1]
    # range 0: straight up (H=0, t=2): v0y = 9.8, angle +90
    res, rr, scr = calc(3, 1, 0, 2, 0)
    expect(summary(scr), {"VX": "0", "V0Y": "9.80", "V0": "9.80", "ANGLE": "90.0"}, "straight up")
    assert "VX IS 0, SO IT IS THROWN" in scr[2], scr[2]
    # dropped from rest: H=4.9, t=1, R=0 -> v0y = 0, v0 = 0, no angle
    res, rr, scr = calc(3, 1, 4.9, 1, 0)
    expect(summary(scr), {"V0Y": "0", "V0": "0"}, "dropped")
    assert "ANGLE- NONE (V0 IS 0)" in scr[-1] and "V0 IS 0- IT WAS DROPPED" in scr[2], scr
    # landing higher (H<0): H=-2, t=2, R=10 -> v0y = (19.6+2)/2 = 10.8
    res, rr, scr = calc(3, 1, -2, 2, 10)
    expect(summary(scr), {"H": "-2.00", "VX": "5.00", "V0Y": "10.8", "V0": "11.9", "ANGLE": "65.2"}, "H<0")


# ------------------------------------------------------------------------------ horizontal launch (C)
def t_horizontal_given_speed():
    res, rr, scr = calc(1, 1, 20, 15)
    s = summary(scr)
    # t = sqrt(40/9.8) = 2.0203; R = 15(2.0203) = 30.305; vy = -9.8(2.0203) = -19.799;
    # speed = sqrt(225 + 392) = sqrt(617) = 24.839 (the task text said 24.9; 24.839 rounds to 24.8);
    # angle = atan(19.799/15) = 52.85 deg below
    expect(s, {"H": "20.0", "T FLIGHT": "2.02", "VX": "15.0", "RANGE": "30.3", "VFX": "15.0",
               "VFY": "-19.8", "HIT SPEED": "24.8", "ANGLE": "52.9"}, "H=20 v=15")
    assert "VFY = -19.8 M/S (DOWN)" in scr[-1] and "ANGLE = 52.9° BELOW" in scr[-1], scr[-1]
    s1 = scr[0]
    assert "-20.0=0+(1/2)(-9.8)T²" in s1 and "T=√(2(20.0)/9.8)" in s1, s1


def t_horizontal_given_range():
    res, rr, scr = calc(1, 2, 20, 30.3)
    s = summary(scr)
    # vx = 30.3/2.0203 = 14.998 -> 15.0; speed sqrt(224.94 + 392) = 24.838; angle atan(19.799/14.998) = 52.86
    expect(s, {"T FLIGHT": "2.02", "VX": "15.0", "RANGE": "30.3", "VFY": "-19.8", "HIT SPEED": "24.8",
               "ANGLE": "52.9"}, "H=20 R=30.3")
    assert "VX=30.3/2.02" in scr[1], scr[1]


def t_horizontal_more():
    # dropped (v = 0): falls straight down, angle 90
    res, rr, scr = calc(1, 1, 45, 0)
    # t = sqrt(90/9.8) = 3.0305; vy = -29.698
    expect(summary(scr), {"T FLIGHT": "3.03", "RANGE": "0", "VFY": "-29.7", "HIT SPEED": "29.7", "ANGLE": "90.0"},
           "dropped 45 m")
    assert "VFX IS 0, SO IT FALLS" in scr[3], scr[3]
    res, rr, scr = calc(1, 2, 45, 0)
    expect(summary(scr), {"VX": "0", "ANGLE": "90.0"}, "range 0")
    # 1.25 m table, 2 m/s: t = 0.50508, R = 1.0102, vy = -4.9497, speed 5.3385, angle 68.00
    res, rr, scr = calc(1, 1, 1.25, 2)
    expect(summary(scr), {"T FLIGHT": "0.505", "RANGE": "1.01", "VFY": "-4.95", "HIT SPEED": "5.34",
                          "ANGLE": "68.0"}, "table")


# ------------------------------------------------------------------------------ angled: special cases
def t_landing_higher():
    res, rr, scr = calc(2, 20, 60, -5)
    s = summary(scr)
    # vx = 10, v0y = 17.3205; 4.9T^2 - 17.3205T + 5 = 0: disc = 300 - 98 = 202,
    # T = (17.3205 -/+ 14.2127)/9.8 = 0.31712, 3.21762 -> later one; R = 32.176;
    # vfy = 17.3205 - 31.5327 = -14.2127; speed sqrt(100 + 202) = 17.378; angle atan(1.42127) = 54.87
    expect(s, {"VX": "10.0", "V0Y": "17.3", "T TOP": "1.77", "RISE": "15.3", "MAX H": "10.3",
               "T FLIGHT": "3.22", "RANGE": "32.2", "HIT SPEED": "17.4", "ANGLE": "54.9"}, "landing higher")
    q = screen_with(scr, "SOLVE QUADRATIC FOR T")
    expect(values_of(q), {"T1": "0.317", "T2": "3.22", "B²-4AC": "202", "T FLIGHT": "3.22"}, "both roots > 0")
    assert "T1 PASSES THAT LEVEL GOING" in q and "UP, T2 LANDS COMING DOWN-" in q, q
    assert rr.quad[1] > 0 and rr.quad[2] > 0
    s5 = screen_with(scr, "STEP 5  VFY AT IMPACT")
    assert "VFY = -14.2 M/S (DOWN)" in s5, s5


def t_unreachable():
    res, rr, scr = calc(2, 5, 30, -10)
    # v0y = 2.5: disc = 6.25 - 4(4.9)(10) = -189.75 < 0 -> never as high as the landing point
    assert rr.message == "D5" and rr.quad[0] == 0
    q = scr[-1]
    assert q[0] == "SOLVE QUADRATIC FOR T" and "B²-4AC = -190" in q and "B²-4AC<0 SO NO REAL ROOT" in q, q
    assert q[-3:] == list(ref.MESSAGES["D5"]), q
    assert not any(s[0].startswith("SUMMARY") for s in scr)
    # the max-height step already shows the top is 9.68 m below the landing point
    expect(values_of(scr[1]), {"RISE": "0.319", "MAX H": "-9.68"}, "unreachable top")


def t_theta_90():
    res, rr, scr = calc(2, 10, 90, 0)
    # straight up, level: T = 2(10)/9.8 = 2.0408, top 100/19.6 = 5.102, lands at -10 m/s, angle 90
    expect(summary(scr), {"VX": "0", "V0Y": "10.0", "T TOP": "1.02", "MAX H": "5.10", "T FLIGHT": "2.04",
                          "RANGE": "0", "HIT SPEED": "10.0", "ANGLE": "90.0"}, "theta 90")
    assert "VFX IS 0, SO IT IS MOVING" in screen_with(scr, "STEP 6  IMPACT SPEED/ANGLE")
    res, rr, scr = calc(2, 10, 90, 2)
    # 4.9T^2 - 10T - 2 = 0 -> T = (10 + sqrt(139.2))/9.8 = 2.2243; vfy = -sqrt(139.2) = -11.798
    expect(summary(scr), {"T FLIGHT": "2.22", "HIT SPEED": "11.8", "ANGLE": "90.0", "MAX H": "7.10"},
           "theta 90 from 2 m")
    res, rr, scr = calc(2, 5, -90, 10)
    # thrown straight down: 4.9T^2 + 5T - 10 = 0 -> T = (-5 + sqrt(221))/9.8 = 1.0067; vfy = -14.866
    expect(summary(scr), {"VX": "0", "V0Y": "-5.00", "T FLIGHT": "1.01", "HIT SPEED": "14.9", "ANGLE": "90.0"},
           "theta -90")


def t_theta_0_and_negative():
    res, rr, scr = calc(2, 10, 0, 5)
    # horizontal from 5 m: T = sqrt(10/9.8) = 1.0102, R = 10.102, vfy = -9.8995,
    # speed sqrt(100 + 98) = 14.071, angle atan(0.98995) = 44.71
    expect(summary(scr), {"VX": "10.0", "V0Y": "0", "T TOP": "0", "RISE": "0", "MAX H": "5.00",
                          "T FLIGHT": "1.01", "RANGE": "10.1", "HIT SPEED": "14.1", "ANGLE": "44.7"}, "theta 0")
    assert "T TOP = 0 S (AT LAUNCH)" in scr[-1], scr[-1]
    assert "V0Y IS NOT UPWARD, SO IT" in scr[1], scr[1]
    res, rr, scr = calc(2, 10, -30, 20)
    # vx = 8.6603, v0y = -5: 4.9T^2 + 5T - 20 = 0 -> T = (-5 + sqrt(417))/9.8 = 1.5735;
    # R = 13.627; vfy = -sqrt(417) = -20.421; speed sqrt(75 + 417) = 22.181; angle atan(20.421/8.6603) = 67.02
    expect(summary(scr), {"VX": "8.66", "V0Y": "-5.00", "T FLIGHT": "1.57", "RANGE": "13.6", "HIT SPEED": "22.2",
                          "ANGLE": "67.0", "MAX H": "20.0"}, "theta -30")
    assert "V0Y = -5.00 M/S (DOWN)" in scr[-1], scr[-1]
    q = screen_with(scr, "SOLVE QUADRATIC FOR T")
    assert "4.90T²+5.00T-20.0=0" in q, q


def t_v0_zero():
    res, rr, scr = calc(2, 0, 40, 5)
    # dropped from 5 m: T = 1.0102, vfy = -9.8995, straight down
    expect(summary(scr), {"VX": "0", "V0Y": "0", "T FLIGHT": "1.01", "RANGE": "0", "HIT SPEED": "9.90",
                          "ANGLE": "90.0"}, "v0 = 0")
    res, rr, scr = calc(2, 0, 40, 0)
    assert rr.message == "M5" and message_shown(scr, "M5") and len(scr) == 1, scr
    res, rr, scr = calc(2, 0, 40, -3)
    assert rr.message == "M6" and message_shown(scr, "M6") and len(scr) == 1, scr


def t_lands_at_top():
    # 9.8 m/s straight up onto a ledge 4.9 m higher: B^2-4AC = 96.04 - 96.04 = 0, T = 1.00 s,
    # it arrives with speed 0 -> no impact angle (must not error)
    res, rr, scr = calc(2, 9.8, 90, -4.9)
    expect(summary(scr), {"T FLIGHT": "1.00", "HIT SPEED": "0", "RANGE": "0"}, "touches at the top")
    assert "ANGLE- NONE (SPEED IS 0)" in scr[-1], scr[-1]
    assert "IT LANDS RIGHT AT THE TOP" in screen_with(scr, "STEP 6  IMPACT SPEED/ANGLE")
    # same with sideways speed: 19.6 m/s at 30 deg onto a 4.9 m ledge -> lands level, angle 0
    res, rr, scr = calc(2, 19.6, 30, -4.9)
    expect(summary(scr), {"T FLIGHT": "1.00", "HIT SPEED": "17.0", "ANGLE": "0"}, "touches at the top, vx>0")


def t_d_matches_c_for_theta_0():
    """An angled launch at 0 deg is a horizontal launch: same T, range, impact speed and angle."""
    for h, v in [(5, 10), (20, 15), (1.25, 2), (100, 0.5), (0.3, 40)]:
        _, _, sc = calc(1, 1, h, v)
        _, _, sd = calc(2, v, 0, h)
        a, b = summary(sc), summary(sd)
        for name in ("T FLIGHT", "RANGE", "HIT SPEED", "ANGLE", "VX"):
            assert a[name] == b[name], (h, v, name, a[name], b[name])


# ------------------------------------------------------------------------------ menus / dispatch
def t_back_paths():
    for item, k in ((3, 1), (5, 3)):
        res = run([item, 3, 7])
        assert_clean(res)
        menus = [(e[1], e[3]) for e in res.events if e[0] == "menu"]
        title = ref.MENU_C[0] if k == 1 else ref.MENU_E[0]
        assert menus == [(MAIN, item), (title, 3), (MAIN, 7)], menus
        assert res.screens == [], "BACK should not show any screen"
        assert ref.run(k, 3).screens == []


def t_menu_shapes():
    for item, (title, opts) in ((3, ref.MENU_C), (5, ref.MENU_E)):
        res = run([item, 3, 7])
        ev = [e for e in res.events if e[0] == "menu" and e[1] == title]
        assert ev and list(ev[0][2]) == list(opts), (ev, opts)
        assert len(title) <= 24 and len(opts) <= 7 and all(len(o) <= 22 for o in opts)
        assert opts[-1] == "BACK"


def t_several_in_one_session():
    """C, D, E one after another in one PHYSOLVE session (no state leaks between them)."""
    plan = [(1, (1, 20, 15)), (2, (25, 50, 0)), (3, (2, 2.0, 2.4, 50)), (2, (5, 30, -10)), (1, (3,)),
            (2, (5.0, 30, 1.0)), (3, (1, 0, 2, 20)), (1, (2, 20, 30.3))]
    keys = []
    for k, kk in plan:
        keys += [ITEM[k], *kk]
    keys.append(7)
    res = run(keys)
    assert_clean(res)
    mains = [i for i, e in enumerate(res.events) if e[0] == "menu" and e[1] == MAIN]
    assert len(mains) == len(plan) + 1
    for n, (k, kk) in enumerate(plan):
        seg = res.events[mains[n] + 1:mains[n + 1]]
        screens = [rows_of(e[1]) for e in seg if e[0] == "screen"]
        compare(screens, ref.run(k, *kk), f"session step {n} K={k} {kk}")


def t_k_dispatch_and_degree():
    """Run ZPROJ directly: any K other than 2/3 is the horizontal launch; K is not changed; the
    program sets Degree itself (the simulator starts in Radian)."""
    s = setup_sim()
    for k in (1, 0, 7, -2, 1.5):
        r = s.run("ZPROJ", [3], init_vars={"K": k}, angle="Radian")
        assert r.error is None and not r.problems, r.text()
        menus = [e[1] for e in r.events if e[0] == "menu"]
        assert menus == [ref.MENU_C[0]], (k, menus)
        assert float(r.vars["K"]) == float(k) and r.angle == "Degree"
    r = s.run("ZPROJ", [25, 50, 0], init_vars={"K": 2}, angle="Radian")
    assert r.error is None and not r.problems and r.finished, r.text()
    assert float(r.vars["K"]) == 2
    got = values_of(rows_of(r.screens[-1]))
    assert got["VX"] == "16.1" and got["RANGE"] == "62.8", got
    r = s.run("ZPROJ", [3], init_vars={"K": 3}, angle="Radian")
    assert [e[1] for e in r.events if e[0] == "menu"] == [ref.MENU_E[0]] and float(r.vars["K"]) == 3


def t_garbage_registers():
    """Results must not depend on what was in the variables before (random garbage per seed)."""
    s = setup_sim()
    want = None
    for seed in range(6):
        r = s.run("PHYSOLVE", [4, 20, 60, -5, 7], seed=seed)
        assert_clean(r)
        shown = [rows_of(e[1]) for e in r.events if e[0] == "screen"]
        if want is None:
            want = shown
        assert shown == want, f"seed {seed} gives different screens"


# ------------------------------------------------------------------------------ impossible / edge inputs
EDGE = [
    # (K, keys, message label)
    (1, (1, 0, 10), "M1"), (1, (1, -3, 10), "M1"), (1, (2, 0, 10), "M1"), (1, (1, 1e-7, 5), "M9"),
    (1, (1, 2e6, 5), "M9"), (1, (1, 10, -1), "M2"), (1, (1, 10, 1e7), "M9"), (1, (1, 10, 1e-9), "M9"),
    (1, (2, 10, -1), "M3"), (1, (2, 10, 1e7), "M9"), (1, (2, 10, 1e-8), "M9"), (1, (1, -1e99, -1e99), "M1"),
    (1, (2, 1e99, 1e99), "M9"),
    (2, (-5, 30, 0), "M2"), (2, (2e6, 30, 0), "M9"), (2, (1e-7, 30, 0), "M9"), (2, (10, 91, 0), "M4"),
    (2, (10, -90.5, 0), "M4"), (2, (10, 1e99, 0), "M4"), (2, (10, 30, 2e6), "M9"), (2, (10, 30, -1e-8), "M9"),
    (2, (10, 0, 0), "M5"), (2, (10, -20, 0), "M5"), (2, (0, 0, 0), "M5"), (2, (10, -45, -2), "M6"),
    (2, (10, 0, -2), "M6"), (2, (5, 30, -10), "D5"), (2, (-1e99, 0, 0), "M2"), (2, (1e99, 0, 0), "M9"),
    (3, (1, 2, 0, 10), "M7"), (3, (2, 2, -2.4, 50), "M7"), (3, (1, 2, 1e-7, 10), "M9"), (3, (1, 2, 2e6, 10), "M9"),
    (3, (1, 2e6, 2, 10), "M9"), (3, (1, 1e-9, 2, 10), "M9"), (3, (1, 2, 2, -5), "M3"), (3, (2, 2, 2, 1e-8), "M9"),
    (3, (2, 2, 2, 1e7), "M9"), (3, (1, -1e99, -1e99, -1e99), "M9"), (3, (2, 0, -1e99, 5), "M7"),
]


def t_edge_messages():
    for k, keys, label in EDGE:
        ctx = f"K={k} keys={keys}"
        res, rr, scr = calc(k, *keys, ctx=ctx)
        assert rr.message == label, f"{ctx}: reference shows {rr.message}, expected {label}"
        assert message_shown(scr, label), f"{ctx}: message {label} not shown\n" + "\n".join(map(str, scr))
        assert not any(s and s[0].startswith("SUMMARY") for s in scr), ctx
        msg_screen = [s for s in scr if ref.MESSAGES[label][0] in s][0]
        assert not any(" = " in row for row in msg_screen if row in ref.MESSAGES[label]), ctx


def t_boundaries():
    """Largest/smallest accepted sizes: no overflow, no error, a summary at the end."""
    cases = [(1, (1, 1e6, 1e6)), (1, (1, 1e-6, 1e-6)), (1, (2, 1e-6, 1e6)), (1, (2, 1e6, 1e-6)),
             (2, (1e6, 89.999999, 1e-6)), (2, (1e-6, 45, 1e6)), (2, (1e6, 1e-6, 1e-6)), (2, (1e6, 90, -1e6)),
             (2, (1e-6, -90, 1e-6)), (2, (1e6, -89.9, 1e6)), (2, (1e6, 0.0001, 0)), (2, (1e-6, 1e-6, 1e6)),
             (3, (1, 1e6, 1e-6, 1e6)), (3, (2, -1e6, 1e-6, 1e-6)), (3, (1, 1e-6, 1e6, 1e6)), (3, (2, 0, 1e6, 0)),
             (3, (1, -1e6, 1e6, 1e-6))]
    for k, keys in cases:
        ctx = f"K={k} keys={keys}"
        res = run([ITEM[k], *keys, 7])
        assert_clean(res, context=ctx)
        menus, screens = part(res)
        assert screens and (screens[-1][0].startswith("SUMMARY") or ref.run(k, *keys).message), ctx


# ------------------------------------------------------------------------------ fuzz
def rnd(rng, lo, hi, nd=None):
    return round(rng.uniform(lo, hi), nd if nd is not None else rng.choice([0, 1, 2, 3]))


def t_fuzz_realistic():
    """Typical test-problem numbers for every path: every screen equals the reference."""
    rng = random.Random(1234)
    for n in range(240):
        k = rng.choice([1, 2, 2, 3])
        if k == 1:
            keys = (rng.choice([1, 2]), rnd(rng, 0.2, 300) or 1.0, rnd(rng, 0, 80))
        elif k == 2:
            th = rng.choice([rnd(rng, -89, 89, 1), rnd(rng, 1, 89, 0), 0, 90, -90, 45])
            h = rng.choice([0, 0, rnd(rng, 0.1, 60, 2), -rnd(rng, 0.1, 20, 2)])
            keys = (rnd(rng, 0.5, 60), th, h)
        else:
            keys = (rng.choice([1, 2]), rng.choice([0, rnd(rng, -3, 30, 2)]), rnd(rng, 0.2, 8, 2) or 1.0,
                    rnd(rng, 0, 120, 1))
        calc(k, *keys, ctx=f"realistic #{n} K={k} {keys}")


def ill_conditioned(k, keys):
    """Inputs where TI's 14-digit decimals and Python floats legitimately differ in a displayed
    digit (catastrophic cancellation in a quadratic root or in (4.9T²-H)/T)."""
    if k == 2:
        v, th, h = keys
        if not (0 <= v <= 1e6 and abs(th) <= 90):
            return False
        vy = v * math.sin(math.radians(th))
        return h != 0 and vy != 0 and 19.6 * abs(h) / (vy * vy) < 1e-6
    if k == 3:
        _, h, t, r = keys
        if not (1e-6 <= t <= 1e6):
            return False
        return abs(4.9 * t * t - h) < 1e-7 * max(abs(h), 1e-300)
    return False


def t_fuzz_wide():
    """Any numbers (negative, zero, tiny, huge, out of range): never an error/leak/scroll/truncation,
    always back to PHYSOLVE, and the same screens as the reference (unless ill-conditioned)."""
    rng = random.Random(99)

    def val():
        r = rng.random()
        if r < 0.1:
            return 0
        mag = 10 ** rng.uniform(-9, 8)
        return float(f"{rng.choice([-1, 1, 1, 1]) * mag:.4g}")

    for n in range(300):
        k = rng.choice([1, 2, 3])
        if k == 1:
            keys = (rng.choice([1, 2]), val(), val())
        elif k == 2:
            keys = (val(), rng.choice([val(), rnd(rng, -100, 100, 2), 90, -90, 0]), val())
        else:
            keys = (rng.choice([1, 2]), val(), val(), val())
        ctx = f"wide #{n} K={k} {keys}"
        res = run([ITEM[k], *keys, 7])
        assert_clean(res, context=ctx)
        menus, screens = part(res)
        rr = ref.run(k, *keys)
        if not ill_conditioned(k, keys):
            compare(screens, rr, ctx)
        else:
            assert [s[0] for s in screens] == [s.title for s in rr.screens], ctx


def t_reference_physics():
    """The reference itself agrees with closed-form projectile formulas (independent of the TI code)."""
    rng = random.Random(5)
    g = 9.8
    for _ in range(400):
        v = rng.uniform(0.1, 60)
        th = rng.uniform(1, 89)
        rr = ref.run(2, v, th, 0)
        s = rr.summary
        assert math.isclose(s["T FLIGHT"], 2 * v * math.sin(math.radians(th)) / g, rel_tol=1e-9)
        assert math.isclose(s["RANGE"], v * v * math.sin(math.radians(2 * th)) / g, rel_tol=1e-9)
        assert math.isclose(s["HIT SPEED"], v, rel_tol=1e-9) and math.isclose(s["ANGLE"], th, rel_tol=1e-9)
        h = rng.uniform(0.01, 50)
        s = ref.run(2, v, th, h).summary
        t = s["T FLIGHT"]
        vy0 = v * math.sin(math.radians(th))
        assert math.isclose(vy0 * t - 0.5 * g * t * t, -h, abs_tol=1e-9)
        assert math.isclose(s["HIT SPEED"], math.sqrt(v * v + 2 * g * h), rel_tol=1e-9)   # energy
        hh = rng.uniform(0.1, 100)
        vx = rng.uniform(0, 40)
        s = ref.run(1, 1, hh, vx).summary
        assert math.isclose(s["T FLIGHT"], math.sqrt(2 * hh / g)) and math.isclose(s["RANGE"], vx * s["T FLIGHT"])
        assert math.isclose(s["HIT SPEED"], math.sqrt(vx * vx + 2 * g * hh), rel_tol=1e-9)
        # throw lab inverts the angled launch: launch, then work backward from (H, t, range)
        s2 = ref.run(2, v, th, h).summary
        back = ref.run(3, 1, h, s2["T FLIGHT"], s2["RANGE"]).summary
        assert math.isclose(back["V0"], v, rel_tol=1e-7) and math.isclose(back["ANGLE"], th, rel_tol=1e-7)


# ------------------------------------------------------------------------------ review fixes
def drive(keys, **kw):
    """Run PHYSOLVE with `keys`, also recording the rows on screen at each Input prompt.
    Returns (result, [(prompt, rows shown above it)])."""
    from tisim import ScriptEnd
    s = setup_sim()
    keys = list(keys)
    shots = []

    def responder(kind, info):
        if kind == "input":
            shots.append((info, [r.rstrip() for r in s.screen if r.strip()]))
        if not keys:
            raise ScriptEnd()
        return keys.pop(0)

    res = run([], responder=responder, **kw)
    return res, shots


def t_input_screens():
    """ZPROJ-1: every input screen is exactly the reference's; the ones that take a negative
    (angled launch: angle and H; throw lab: H) show the (-) key hint; rows + prompts <= 10."""
    cases = [((3, 1, 20, 15, 7), ref.INPUT_C1, False), ((3, 2, 20, 30.3, 7), ref.INPUT_C2, False),
             ((4, 25, 50, 0, 7), ref.INPUT_D, True), ((5, 1, 2, 2.4, 50, 7), ref.INPUT_E[1], True),
             ((5, 2, 2, 2.4, 50, 7), ref.INPUT_E[2], True)]
    for wide in (False, True):
        for keys, (rows, prompts), neg in cases:
            ctx = f"{keys} wide={wide}"
            res, shots = drive(keys, wide=wide)
            assert_clean(res, context=ctx)
            assert [p for p, _ in shots] == list(prompts), (ctx, shots)
            first = shots[0][1]
            assert first == list(rows), f"{ctx}: input screen {first}, reference {rows}"
            assert len(rows) + len(prompts) <= 10, ctx
            assert all(len(r) <= 26 for r in rows) and all(len(p) + 9 <= 26 for p in prompts), ctx
            assert (ref.NEG_HINT in first) == neg, f"{ctx}: (-) hint shown={ref.NEG_HINT in first}"
            # the last prompt (row 10 at most) is answered on the same screen: nothing scrolled away
            assert shots[-1][1][:len(rows)] == list(rows), (ctx, shots[-1])
    rr = ref.run(2, 25, 50, 0)
    assert rr.inputs == ref.INPUT_D and ref.run(3, 2, 2, 2.4, 50).inputs == ref.INPUT_E[2]


def t_negative_key():
    """ZPROJ-1: negatives typed with the (-) key (strings starting with '⁻') work on both input
    screens that take them, and give the same screens as numeric negatives."""
    for typed, num in [((4, 20, 60, "⁻5", 7), (4, 20, 60, -5, 7)), ((4, 10, "⁻30", 20, 7), (4, 10, -30, 20, 7)),
                       ((5, 1, "⁻2", 2, 10, 7), (5, 1, -2, 2, 10, 7)), ((4, 9.8, 90, "⁻4.9", 7), (4, 9.8, 90, -4.9, 7))]:
        a, b = run(list(typed)), run(list(num))
        assert_clean(a, context=str(typed))
        assert a.screens == b.screens, typed


WIDE_PATHS = [
    (3, 1, 20, 15), (3, 2, 20, 30.3), (3, 1, 45, 0), (3, 2, 45, 0), (3, 1, 1.25, 2),
    (4, 25, 50, 0), (4, 5, 30, 1), (4, 4.9, 20, 0.85), (4, 20, 60, -5), (4, 10, 0, 5), (4, 10, -30, 20),
    (4, 10, 90, 2), (4, 10, 90, 0), (4, 5, -90, 10), (4, 0, 40, 5), (4, 9.8, 90, -4.9), (4, 19.6, 30, -4.9),
    (4, 5, 30, -10),
    (5, 1, 2, 2.4, 50), (5, 2, 2, 2.4, 50), (5, 1, 10, 1, 5), (5, 1, 0, 2, 0), (5, 1, 4.9, 1, 0),
    (5, 1, -2, 2, 10), (5, 1, 0, 2, 20), (3, 3), (5, 3),
]


def t_wide_values():
    """ZPROJ-7: every path, every message (M1-M9, D5) and BACK with worst-case 9-character values
    (-8.88E-88) and 9-character inputs: nothing truncated, nothing scrolls, back to PHYSOLVE."""
    seen = set()
    for keys in WIDE_PATHS + [(ITEM[k], *kk) for k, kk, _ in EDGE]:
        res = run([*keys, 7], wide=True)
        assert_clean(res, context=f"wide {keys}")
        k = {3: 1, 4: 2, 5: 3}[keys[0]]
        if ref.run(k, *keys[1:]).message:
            seen.add(ref.run(k, *keys[1:]).message)
    assert seen == set(ref.MESSAGES), f"wide mode does not reach {set(ref.MESSAGES) - seen}"
    # several in one session, wide
    res = run([3, 1, 20, 15, 4, 5, 30, 1, 5, 2, 2, 2.4, 50, 4, 20, 60, -5, 7], wide=True)
    assert_clean(res, context="wide session")


def t_heights_step2():
    """ZPROJ-2/3: RISE (above the launch point), H+RISE, MAX H (above the landing point, like H)."""
    _, _, scr = calc(2, 20, 60, -5)
    s2 = screen_with(scr, "STEP 2  TIME TO TOP, MAX H")
    assert s2[-3:] == ["RISE = 15.3 M", "H+RISE=-5.00+15.3", "MAX H = 10.3 M"], s2
    assert "RISE ABOVE THE LAUNCH-" in s2 and "USE VF²=V0²+2AS" in s2, s2
    assert not any("H-" in row and "MAX" in row for row in s2), s2
    _, _, scr = calc(2, 5.0, 30, 1.0)       # required case: the cliff max height is 1.32 m
    assert summary(scr)["MAX H"] == "1.32" and summary(scr)["RISE"] == "0.319"
    _, _, scr = calc(2, 25, 50, 0)          # level ground: RISE = MAX H, the summary shows MAX H only
    s2 = screen_with(scr, "STEP 2  TIME TO TOP, MAX H")
    assert s2[-3:] == ["RISE = 18.7 M", "H+RISE=0+18.7", "MAX H = 18.7 M"], s2
    assert "RISE" not in summary(scr) and summary(scr)["MAX H"] == "18.7", scr[-1]
    _, _, scr = calc(2, 10, -30, 20)        # not launched upward: RISE 0, top is the launch point
    s2 = screen_with(scr, "STEP 2  TIME TO TOP, MAX H")
    assert s2[-4:] == ["T TOP = 0 S (AT LAUNCH)", "RISE = 0 M", "H+RISE=20.0+0", "MAX H = 20.0 M"], s2
    # ZPROJ-5: the summary's T TOP row for a launch that is not upward is the fixed text
    assert "T TOP = 0 S (AT LAUNCH)" in scr[-1], scr[-1]
    for row in scr[-1][1:]:
        assert len(row) <= 26 and VAL_RE.match(row), row


def t_range_line_and_note():
    """ZPROJ-4/6: the RANGE substitution goes through ZLINE; a note says the calculator keeps all
    digits (so redoing the math from the rounded numbers on screen can differ in the last digit)."""
    _, _, scr = calc(2, 25, 50, 0)
    assert scr[0][-1] == ref.KEEPS, scr[0]
    s4 = screen_with(scr, "STEP 4  RANGE (HORIZONTAL)")
    assert "RANGE=(16.1)(3.91)" in s4 and "RANGE = 62.8 M" in s4, s4
    _, _, scr = calc(1, 1, 20, 15)
    assert scr[1][-1] == ref.KEEPS and "RANGE=(15.0)(2.02)" in scr[1], scr[1]
    _, _, scr = calc(1, 2, 20, 30.3)
    assert scr[1][-1] == ref.KEEPS, scr[1]
    for k in (1, 2):
        _, _, scr = calc(3, k, 2.0, 2.4, 50)
        assert scr[0][-1] == ref.KEEPS and len(scr[0]) <= 10, scr[0]
    assert len(ref.KEEPS) <= 26 and not VAL_RE.match(ref.KEEPS)


def t_m2_angled_hint():
    """ZPROJ-8: a negative speed in the angled launch says to use a negative angle instead;
    the horizontal launch's M2 does not (it has no angle)."""
    _, rr, scr = calc(2, -5, 30, 10)
    assert scr[-1] == list(ref.MESSAGES["M2"] + ref.M2_ANGLED), scr[-1]
    _, rr, scr = calc(1, 1, 10, -1)
    assert scr[-1] == list(ref.MESSAGES["M2"]), scr[-1]
    for row in ref.M2_ANGLED:
        assert len(row) <= 26 and " = " not in row


def t_labels():
    """ZPROJ-9/10: the throw-lab angle heading fits up and down; the impact speed is HIT SPEED
    (not the launch speed); D step 4 shows VX (the summary's name), not VFX."""
    _, _, scr = calc(3, 1, 10, 1, 5)
    s3 = screen_with(scr, "STEP 3  LAUNCH SPEED/ANGLE")
    assert "ANGLE FROM HORIZONTAL-" in s3 and "ANGLE = -45.6° (BELOW)" in s3, s3
    assert not any("ABOVE HORIZONTAL" in r for r in s3), s3
    _, _, scr = calc(2, 25, 50, 0)
    assert "HIT SPEED = 25.0 M/S" in scr[-1] and not any(r.startswith("SPEED = ") for r in scr[-1]), scr[-1]
    s4 = screen_with(scr, "STEP 4  RANGE (HORIZONTAL)")
    assert "VX = 16.1 M/S" in s4 and not any(r.startswith("VFX = ") for r in s4), s4
    _, _, scr = calc(1, 1, 20, 15)
    assert "HIT SPEED = 24.8 M/S" in scr[-1] and "HIT SPEED = 24.8 M/S" in scr[3], scr


def t_every_statement_runs():
    """Coverage: every ZPROJ statement was executed by the tests above (so every branch, message
    and menu path has been run at least once)."""
    if os.environ.get("TISIM_SINGLE"):
        return   # per-module coverage needs the separate module build
    s = setup_sim()
    prog = s.programs["ZPROJ"]
    missing = [st for i, st in enumerate(prog.stmts) if ("ZPROJ", i) not in s.coverage and st.kind not in ("Lbl", "Then")]
    assert not missing, "never executed: " + "; ".join(f"L{st.line} {st.text}" for st in missing[:12])


c.check("ZPROJ and its helpers load without syntax errors", t_syntax)
c.check("build.py --check --only ZPROJ is clean", t_lint_clean)
c.check("required: 25.0 m/s at 50 deg, level -> 16.1, 19.2, 3.91 s, 62.8 m, 18.7 m", t_angled_level_25_50)
c.check("required: 5.0 m/s at 30 deg from 1.0 m -> 0.774 s, 3.35 m", t_angled_from_1m)
c.check("required: 4.9 m/s at 20 deg from 0.85 m -> 0.621 s, 2.86 m", t_angled_from_085m)
c.check("required: throw lab 2.0 m, 2.4 s, 50 yd -> 45.7 m, 19.1, 10.9, 22.0 m/s, 29.8 deg", t_throw_lab_yards)
c.check("throw lab in meters", t_throw_lab_meters)
c.check("throw lab: thrown down, range 0, dropped, landing higher", t_throw_lab_more)
c.check("horizontal: H=20, v=15 -> 2.02 s, 30.3 m, -19.8 m/s, 24.8 m/s, 52.9 deg", t_horizontal_given_speed)
c.check("horizontal: H=20, R=30.3 -> v=15.0", t_horizontal_given_range)
c.check("horizontal: dropped, range 0, table", t_horizontal_more)
c.check("angled: landing higher, both roots positive, later one used", t_landing_higher)
c.check("angled: unreachable landing height -> message under ZQUAD", t_unreachable)
c.check("angled: theta = 90 and -90 (vx = 0) without error", t_theta_90)
c.check("angled: theta = 0 and negative theta", t_theta_0_and_negative)
c.check("angled: v0 = 0", t_v0_zero)
c.check("angled: lands exactly at the top (speed 0, no angle)", t_lands_at_top)
c.check("angled at 0 deg = horizontal launch (same numbers)", t_d_matches_c_for_theta_0)
c.check("BACK paths return to PHYSOLVE with no screens", t_back_paths)
c.check("menus: <=7 options, text lengths, BACK last", t_menu_shapes)
c.check("C, D, E in one session match the reference", t_several_in_one_session)
c.check("K dispatch (other K -> C), K unchanged, Degree set", t_k_dispatch_and_degree)
c.check("results do not depend on old register contents", t_garbage_registers)
c.check("impossible/edge inputs give message screens, never errors", t_edge_messages)
c.check("largest/smallest accepted sizes: no overflow or error", t_boundaries)
c.check("fuzz (realistic numbers): every screen = reference", t_fuzz_realistic)
c.check("fuzz (any numbers): clean, back to PHYSOLVE, = reference", t_fuzz_wide)
c.check("reference agrees with closed-form projectile physics", t_reference_physics)
c.check("input screens = reference; (-) key hint where a negative is allowed", t_input_screens)
c.check("negatives typed with the (-) key work on every input screen", t_negative_key)
c.check("wide mode (9-char values/inputs): every path, message and BACK fits", t_wide_values)
c.check("step 2 / summary heights: RISE, H+RISE, MAX H; T TOP at launch", t_heights_step2)
c.check("RANGE substitution via ZLINE; 'calc keeps all digits' note", t_range_line_and_note)
c.check("M2 from the angled launch says to use a negative angle", t_m2_angled_hint)
c.check("labels: ANGLE FROM HORIZONTAL, HIT SPEED, VX in D step 4", t_labels)
c.check("every ZPROJ statement executed", t_every_statement_runs)
if TOLERANT_USED:
    print(f"  note: {len(TOLERANT_USED)} screen(s) matched only within 1e-9 relative (rounding ties), e.g. "
          f"{TOLERANT_USED[0]}")
sys.exit(c.done())
