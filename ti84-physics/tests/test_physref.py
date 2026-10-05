"""Tests for PHYSREF (the formula / explanation reference screens).

PHYSREF is run directly from the PRGM menu (it is not called by PHYSOLVE). It has two menu pages:
  page 1  1 SCALARS VS VECTORS  2 THE 5 EQUATIONS  3 FREE FALL  4 GRAPHS X-T V-T A-T
          5 FACTOR OF CHANGE    6 MORE >           7 QUIT
  page 2  1 CHASE PROBLEMS  2 HORIZONTAL LAUNCH  3 ANGLED LAUNCH  4 RIVER CROSSING  5 LABS
          6 BACK            7 QUIT
Each topic is a fixed sequence of screens (ClrHome, <= 10 Disp rows, Pause) and then returns to the
menu page it was chosen from. PHYSREF uses no variables at all.

Checks: lint + source structure (only Degree/Lbl/Goto/Menu(/ClrHome/Disp "..."/Pause, no variables),
every menu path in the simulator (assert_clean: no error/leak/scroll/truncation, program finished),
screens per topic and their "k/N" headers, return-to-page, 26x10 limits, every required bullet's key
phrases in the right topic, and every worked-example number recomputed here in Python (fmt3).
"""
import math
import re
import sys
from decimal import Decimal

from harness import Checker, run, assert_clean, fmt3, sim, ROOT, COLS, ROWS

c = Checker("PHYSREF")

SRC = ROOT / "src" / "PHYSREF.txt"
P1 = "PHYSREF 1/2  FORMULAS"
P2 = "PHYSREF 2/2  FORMULAS"

# (page, option number, menu text, number of screens, header prefix of its screens)
TOPICS = [
    (1, 1, "SCALARS VS VECTORS", 3, "SCALARS VS VECTORS"),
    (1, 2, "THE 5 EQUATIONS", 4, "THE 5 EQUATIONS"),
    (1, 3, "FREE FALL", 4, "FREE FALL"),
    (1, 4, "GRAPHS X-T V-T A-T", 6, "GRAPHS"),
    (1, 5, "FACTOR OF CHANGE", 3, "FACTOR OF CHANGE"),
    (2, 1, "CHASE PROBLEMS", 3, "CHASE PROBLEMS"),
    (2, 2, "HORIZONTAL LAUNCH", 3, "HORIZONTAL LAUNCH"),
    (2, 3, "ANGLED LAUNCH", 4, "ANGLED LAUNCH"),
    (2, 4, "RIVER CROSSING", 5, "RIVER CROSSING"),
    (2, 5, "LABS", 6, "LABS"),
]
ALLOWED_CHARS = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 =+-*/().,²√°<>≤≥≠?!%|⁻")


def topic_script(page, opt, via_back=False):
    """Keys that open one topic and then leave PHYSREF (QUIT, or page-2 BACK then page-1 QUIT)."""
    if page == 1:
        return [opt, 7]
    return [6, opt, 6, 7] if via_back else [6, opt, 7]


def topic_screens(res, page, opt):
    """Screens shown between choosing (page, opt) and the next menu."""
    title = P1 if page == 1 else P2
    out, cur = [], None
    for e in res.events:
        if e[0] == "menu":
            cur = None
            if e[1] == title and e[3] == opt:
                cur = []
                out.append(cur)
        elif e[0] == "screen" and cur is not None:
            cur.append([r for r in e[1]])
    assert len(out) == 1, f"topic {page}/{opt} opened {len(out)} times\n{res.text()}"
    return out[0]


def text_of(screens):
    return "\n".join(r for scr in screens for r in scr)


_CACHE = {}


def topic_text(menu_text):
    """All rows (joined with newlines) of one topic, run through the real menus."""
    if menu_text not in _CACHE:
        page, opt = next((p, o) for p, o, t, n, h in TOPICS if t == menu_text)
        res = run(topic_script(page, opt), program="PHYSREF")
        assert_clean(res, context=menu_text)
        _CACHE[menu_text] = text_of(topic_screens(res, page, opt))
    return _CACHE[menu_text]


def has(menu_text, *phrases):
    txt = topic_text(menu_text)
    missing = [p for p in phrases if p not in txt]
    assert not missing, f"{menu_text}: missing {missing}\n{txt}"


def row_has(menu_text, *parts):
    """Some single row of the topic contains every part (e.g. an equation and its '(NO X)')."""
    rows = topic_text(menu_text).split("\n")
    assert any(all(p in r for p in parts) for r in rows), f"{menu_text}: no row with {parts}"


# ------------------------------------------------------------------------- source / lint
def t_lint():
    sys.path.insert(0, str(ROOT / "tools"))
    import build
    report, failures, warns = build.build(write=False, only={"PHYSREF"})
    assert report and report[0][0] == "PHYSREF", report
    assert not failures, "\n".join(failures)
    assert not warns, "\n".join(warns)


def t_source_structure():
    raw = SRC.read_text(encoding="utf-8")
    assert raw.endswith("\n") and not raw.endswith("\n\n"), "file must end with exactly one newline"
    lines = raw[:-1].split("\n")
    assert lines[0] == "Degree", "first line must be Degree"
    labels = set()
    i, n_screens = 1, 0
    while i < len(lines):
        ln = lines[i]
        if m := re.fullmatch(r"Lbl ([A-Z0-9]{1,2})", ln):
            assert not set(m.group(1)) & set("RTXY"), ln
            assert m.group(1) not in labels, f"duplicate label {ln}"
            labels.add(m.group(1))
            i += 1
        elif re.fullmatch(r"Goto [A-Z0-9]{1,2}", ln) or ln.startswith("Menu("):
            i += 1
        elif ln == "ClrHome":
            j = i + 1
            while j < len(lines) and lines[j].startswith('Disp "'):
                assert re.fullmatch(r'Disp "[^"→]{1,26}"', lines[j]), f"line {j + 1}: {lines[j]!r}"
                j += 1
            rows = j - i - 1
            if j == len(lines):          # the QUIT ClrHome is the very last statement
                assert rows == 0 and lines[j - 2] == "Lbl Q", "program must end with Lbl Q, ClrHome"
                break
            assert 1 <= rows <= ROWS, f"line {i + 1}: screen with {rows} Disp rows"
            assert lines[j] == "Pause ", f"line {j + 1}: screen must end with 'Pause ' (found {lines[j]!r})"
            n_screens += 1
            i = j + 1
        else:
            raise AssertionError(f"line {i + 1}: statement not allowed in PHYSREF: {ln!r}")
    assert n_screens == sum(t[3] for t in TOPICS), f"{n_screens} screens in source"
    # no variables at all: no store arrow, no Input/Prompt/Str/lists anywhere
    for k, ln in enumerate(lines, 1):
        assert "→" not in ln and "ʟ" not in ln and "Str" not in ln, f"line {k} uses a variable: {ln!r}"
        assert not ln.startswith(("Input", "Prompt", "Stop", "Return", "prgm", "If", "While", "For(")), ln
    # menus: <= 7 options, title <= 24, option text <= 22, BACK/QUIT present
    menus = [ln for ln in lines if ln.startswith("Menu(")]
    assert len(menus) == 2, menus
    for ln in menus:
        parts = re.findall(r'"([^"]*)"', ln)
        title, opts = parts[0], parts[1:]
        assert len(title) <= 24, title
        assert 2 <= len(opts) <= 7, opts
        assert all(len(o) <= 22 for o in opts), opts
        assert "QUIT" in opts or "BACK" in opts, opts


def t_strings_charset():
    for k, ln in enumerate(SRC.read_text(encoding="utf-8").split("\n"), 1):
        for s in re.findall(r'"([^"]*)"', ln):
            bad = set(s) - ALLOWED_CHARS
            assert not bad, f"line {k}: characters {bad} in {s!r}"
            assert "..." not in s and ":" not in s, f"line {k}: {s!r}"
            for m in re.finditer("⁻", s):
                assert s[m.start():m.start() + 3] == "⁻1(", f"line {k}: '⁻' only as inverse trig ⁻1(: {s!r}"


# ------------------------------------------------------------------------- menu paths
def t_quit_paths():
    for keys in ([7], [6, 7], [6, 6, 7], [6, 6, 6, 6, 6, 7]):
        res = run(keys, program="PHYSREF")
        assert_clean(res, context=str(keys))
        assert res.screens == [], f"{keys}: unexpected screens"
        menus = [e for e in res.events if e[0] == "menu"]
        assert [m[3] for m in menus] == keys, (keys, menus)
        # MORE > goes to page 2, BACK goes to page 1
        for a, b in zip(menus, menus[1:]):
            want = P2 if (a[1] == P1 and a[3] == 6) else P1
            assert b[1] == want, f"{keys}: after {a[1]} option {a[3]} expected {want}, got {b[1]}"


def t_every_topic():
    for page, opt, text, n, head in TOPICS:
        for via_back in ((False, True) if page == 2 else (False,)):
            keys = topic_script(page, opt, via_back)
            res = run(keys, program="PHYSREF")
            assert_clean(res, context=f"{text} {keys}")
            menus = [e for e in res.events if e[0] == "menu"]
            title = P1 if page == 1 else P2
            # the chosen menu option text matches, and the topic returns to its own page
            chosen = next(i for i, m in enumerate(menus) if m[1] == title and m[3] == opt)
            assert menus[chosen][2][opt - 1] == text, (menus[chosen][2], text)
            assert menus[chosen + 1][1] == title, f"{text} returned to {menus[chosen + 1][1]}"
            scrs = topic_screens(res, page, opt)
            assert len(scrs) == n, f"{text}: {len(scrs)} screens, expected {n}"
            for k, scr in enumerate(scrs, 1):
                assert len(scr) == ROWS
                assert all(len(r) <= COLS for r in scr), scr
                assert sum(1 for r in scr if r) <= ROWS
                # first row is the topic header with page k/N (proves ClrHome ran and nothing scrolled)
                assert scr[0].startswith(head) and f"{k}/{n}" in scr[0], f"{text} screen {k}: {scr[0]!r}"
                assert all(r == r.rstrip() for r in scr), f"{text} screen {k}: trailing spaces"
                assert not any(r.startswith("ERR") for r in scr)
            # every screen is different
            assert len({tuple(s) for s in scrs}) == n, f"{text}: repeated screen"


def t_all_topics_one_run():
    keys = [1, 2, 3, 4, 5, 6, 1, 2, 3, 4, 5, 6, 6, 1, 2, 3, 4, 5, 6, 7]
    res = run(keys, program="PHYSREF")
    assert_clean(res, context="all topics")
    assert len(res.screens) == sum(t[3] for t in TOPICS) + sum(t[3] for t in TOPICS if t[0] == 2)


def t_no_variables_touched():
    s = sim()
    for seed in (0, 1, 2):
        res = s.run("PHYSREF", [1, 2, 6, 5, 7], seed=seed, angle="Radian")
        assert_clean(res)
        import random as _r
        from tisim import norm, LETTERS
        rng = _r.Random(seed)
        init = {v: norm(Decimal(rng.choice([-1, 1]) * rng.randint(0, 99999)) / 100) for v in LETTERS}
        assert res.vars == init, "PHYSREF changed a variable"
        assert res.strs == {} and res.lists == {}, (res.strs, res.lists)
        assert res.angle == "Degree", "PHYSREF must set Degree mode"
        assert res.calls == ["PHYSREF"], res.calls


def t_menus_fit():
    res = run([6, 7], program="PHYSREF")
    for e in res.events:
        if e[0] == "menu":
            assert len(e[1]) <= 24 and len(e[2]) <= 7, e
            assert all(len(t) <= 22 for t in e[2]), e
            assert e[2][-1] in ("QUIT", "BACK") and ("BACK" in e[2] or "QUIT" in e[2]), e


# ------------------------------------------------------------------------- required content
def t_scalars_vectors():
    T = "SCALARS VS VECTORS"
    has(T, "SCALAR = SIZE ONLY", "VECTOR = SIZE + DIRECTION",
        "DISTANCE (SCALAR)", "PATH LENGTH", "DISPLACEMENT S (VECTOR)", "CHANGE IN X",
        "SPEED (SCALAR)", "VELOCITY (VECTOR)",
        "AVG SPEED = DISTANCE / T", "AVG VELOCITY = S / T",
        "ACCELERATION A (VECTOR)", "A = (VF - V0)/T",
        "SPEEDING UP WHEN V AND A\n HAVE THE SAME SIGN",
        "SLOWING DOWN WHEN V AND A\n HAVE OPPOSITE SIGNS")
    # worked examples: 5 m right then 2 m left; 400 m lap in 80 s
    has(T, "DISTANCE 7 M, S = +3 M", f"= {fmt3(400 / 80)} M/S", "AVG VELOCITY = 0 (S = 0)")
    row_has(T, "V = -5", "A = -2")      # same signs -> speeding up
    has(T, "SAME SIGNS, SPEEDING UP")


def t_five_equations():
    T = "THE 5 EQUATIONS"
    row_has(T, "VF=V0+AT", "(NO S)")
    row_has(T, "S=V0T+(1/2)AT²", "(NO VF)")
    row_has(T, "S=VFT-(1/2)AT²", "(NO V0)")
    row_has(T, "VF²=V0²+2AS", "(NO T)")
    row_has(T, "S=(1/2)(V0+VF)T", "(NO A)")
    has(T, "CONSTANT", "V0 VF S T A", "3 KNOWNS", "1 UNKNOWN", "PICK AN EQUATION",
        "FROM REST       V0 = 0", "COMES TO A STOP VF = 0", "FREE FALL       A = -9.8", "UP IS +")
    # worked example: 20 m/s, brakes at 4 m/s^2 to a stop: 0 = 20^2 + 2(-4)S
    v0, a = 20, -4
    has(T, f"0 = {v0 * v0} - {2 * -a}S", f"S = {fmt3(-v0 * v0 / (2 * a))} M")


def t_free_fall():
    T = "FREE FALL"
    has(T, "A = -9.8 M/S²", "AT THE TOP V = 0", "A IS STILL -9.8", "SYMMETRY",
        "TIME UP = TIME DOWN", "SAME\n SPEED AT SAME HEIGHT", "1,3,5", "1,4,9",
        "SUCCESSIVE EQUAL TIMES", "S = -4.9T²")
    g = 9.8
    rows = topic_text(T).split("\n")
    # ratio row: in-that-second distances go 1,3,5 and totals 1,4,9 (k^2)
    ratio = next(r for r in rows if r.startswith("RATIO")).split()
    that = [round((k * k - (k - 1) ** 2)) for k in (1, 2, 3)]
    total = [k * k for k in (1, 2, 3)]
    assert ratio == ["RATIO", ",".join(map(str, that)), ",".join(map(str, total))], ratio
    row_has(T, " 1,3,5  TOTALS 1,4,9 (T²)")
    for k, name in ((1, "1ST SEC"), (2, "2ND SEC"), (3, "3RD SEC")):
        d_that = 0.5 * g * (k * k - (k - 1) ** 2)
        d_total = 0.5 * g * k * k
        row = next(r for r in rows if r.startswith(name))
        nums = re.findall(r"[0-9.]+ M", row)
        assert nums == [f"{d_that:.1f} M", f"{d_total:.1f} M"], (row, d_that, d_total)
    assert [f"{0.5 * g * k * k:.1f}" for k in (1, 2, 3)] == ["4.9", "19.6", "44.1"]
    assert [f"{0.5 * g * (2 * k - 1):.1f}" for k in (1, 2, 3)] == ["4.9", "14.7", "24.5"]
    # symmetry example: thrown up at 14.7 m/s
    v0 = 14.7
    has(T, f"T = {fmt3(v0 / g)} S (TOP", f"S = {fmt3(v0 * v0 / (2 * g))} M (MAX HEIGHT)",
        f"BACK AT {fmt3(2 * v0 / g)} S, {fmt3(-v0)} M/S", "0 = 14.7² + 2(-9.8)S")
    # drop from 20 m
    h = 20
    has(T, f"T = √({2 * h}/9.8) = {fmt3(math.sqrt(2 * h / g))} S",
        f"VF = -√({fmt3(2 * g * h)}) = {fmt3(-math.sqrt(2 * g * h))} M/S", "T = √(2H/9.8)")


def t_graphs():
    T = "GRAPHS X-T V-T A-T"
    has(T, "SLOPE GOES DOWN THE STACK", "AREA GOES UP THE STACK",
        "SLOPE OF X-T = V", "SLOPE OF V-T = A",
        "AREA UNDER V-T = S", "CHANGE IN X", "AREA UNDER A-T", "CHANGE IN V",
        # x-t shapes
        "X-T SHAPES", "FLAT = AT REST", "STRAIGHT LINE = CONSTANT V", "PARABOLA", "ACCELERATING",
        # v-t shapes
        "V-T SHAPES", "FLAT = CONSTANT V (A = 0)", "SLOPED LINE = CONSTANT A",
        "AWAY FROM AXIS SPEEDS UP", "TOWARD AXIS SLOWS DOWN",
        # a-t shapes
        "A-T SHAPES", "FLAT = CONSTANT A", "A IS 0", "AT -9.8 M/S²",
        # one-motion table
        "AT REST FLAT     AT 0 AT 0", "CONST V LINE     FLAT AT 0", "CONST A PARABOLA LINE FLAT")
    has(T, f"S = {fmt3(0.5 * 4 * 8)} M")


def t_factor_of_change():
    T = "FACTOR OF CHANGE"
    has(T, "STOPPING", "S PROP TO V0²", "2X SPEED GIVES 4X S", "3X SPEED GIVES 9X S",
        "FROM REST", "S PROP TO T²", "2X TIME GIVES 4X S", "3X TIME GIVES 9X S",
        "DROPPED", "T PROP TO √(H)", "4X HEIGHT GIVES 2X TIME", "9X HEIGHT GIVES 3X TIME")
    # ratio examples use exact whole numbers (they are rules of thumb, not 3-s.f. results)
    has(T, f"{fmt3(math.sqrt(2))}X T",                                # 2x height -> 1.41x time
        f"40 M/S STOPS IN {30 * (40 // 20) ** 2} M",                  # s prop to v^2
        f"5 M IN THE FIRST 1 S,\n {5 * 2 ** 2} M IN 2 S, {5 * 3 ** 2} M IN 3 S",  # s prop to t^2
        f"4.9 M TAKES {fmt3(math.sqrt(2 * 4.9 / 9.8))} S",
        f"19.6 M TAKES {fmt3(math.sqrt(2 * 19.6 / 9.8))} S")
    assert 30 * (40 // 20) ** 2 == 120 and 5 * 2 ** 2 == 20 and 5 * 3 ** 2 == 45


def t_chase():
    T = "CHASE PROBLEMS"
    has(T, "POSITIONS ARE EQUAL", "FROM REST", "CONSTANT V", "TWICE", "(1/2)AT² = VT", "T = 2V/A",
        "= 2V")
    v, a = 15, 3
    t = 2 * v / a
    assert abs(0.5 * a * t * t - v * t) < 1e-9          # both positions really are equal
    has(T, f"T = 2(15)/3 = {fmt3(t)} S", f"X = 15(10) = {fmt3(v * t)} M",
        f"COP VF = 3(10) = {fmt3(a * t)} M/S", "TWICE 15 M/S")
    assert a * t == 2 * v


def t_horizontal():
    T = "HORIZONTAL LAUNCH"
    has(T, "VX = V0", "V0Y = 0", "SAME T IN BOTH DIRECTIONS", "T = √(2H/G)", "AY = -9.8")
    g, h, vx = 9.8, 20, 5
    t = math.sqrt(2 * h / g)
    vy = -g * t
    has(T, f"T = {fmt3(t)} S", f"RANGE = {fmt3(vx * t)} M", f"VY = {fmt3(vy)} M/S (DOWN)",
        f"= {fmt3(math.hypot(vx, vy))} M/S", f"= {fmt3(math.degrees(math.atan(-vy / vx)))}° BELOW",
        "TAN⁻1(|VY|/VX)")
    assert fmt3(t) == "2.02"


def t_angled():
    T = "ANGLED LAUNCH"
    has(T, "VX = V0COS(ANGLE)", "V0Y = V0SIN(ANGLE)", "THE Y MOTION DECIDES T", "RANGE = VX*T",
        "MAX RANGE AT 45°", "COMPLEMENTARY ANGLES", "GIVE EQUAL", "RANGES, EX 30° AND 60°",
        "LEVEL GROUND", "AT THE TOP VY = 0")
    g, v0, th = 9.8, 20, math.radians(30)
    vx, vy = v0 * math.cos(th), v0 * math.sin(th)
    t = 2 * vy / g
    has(T, f"VX = 20COS(30) = {fmt3(vx)} M/S", f"V0Y = 20SIN(30) = {fmt3(vy)} M/S",
        f"T = {fmt3(t)} S", f"= {fmt3(vx * t)} M", f"= {fmt3(vy * vy / (2 * g))} M",
        f"20 M/S AT 60° ALSO {fmt3(v0 * v0 * math.sin(math.radians(120)) / g)} M")
    # the rounded intermediate shown (17.3 x 2.04) gives the same 3-s.f. range
    assert fmt3(17.3 * 2.04) == fmt3(vx * t) == "35.3"


def t_river():
    T = "RIVER CROSSING"
    has(T, "INDEPENDENT", "T = W / BOAT SPEED ACROSS", "DRIFT = VR*T", "√(VB² + VR²)",
        "TAN⁻1(VR/VB)", "HEADING", "DIFFERENT FROM PATH", "LAND DIRECTLY ACROSS", "AIM UPSTREAM",
        "SIN⁻1(VR/VB)", "VB > VR")
    vb, vr, w = 4, 3, 100
    t = w / vb
    has(T, f"T = 100/4 = {fmt3(t)} S", f"DRIFT = 3(25) = {fmt3(vr * t)} M",
        f"= {fmt3(math.hypot(vb, vr))} M/S", f"= {fmt3(math.degrees(math.atan(vr / vb)))}° DOWNSTREAM")
    vb = 5
    across = math.sqrt(vb * vb - vr * vr)
    has(T, f"= {fmt3(math.degrees(math.asin(vr / vb)))}° UPSTREAM", f"= {fmt3(across)} M/S",
        f"T = 100/4 = {fmt3(w / across)} S", "DRIFT = 0 M")


def t_labs():
    T = "LABS"
    has(T, "RAMP", "S (Y AXIS) VS T²", "SLOPE = A/2", "A = 2*SLOPE",
        "100 M DASH", "AVG VELOCITY PER INTERVAL", "MIDDLE TIME", "(T1+T2)/2",
        "% DIFF = |A - B|", "/ AVERAGE * 100", "AVERAGE = (A + B)/2",
        "1 M = 1.0936 YD", "LAUNCH FROM H", "-H = V0Y*T - (1/2)GT²", "QUADRATIC FORMULA",
        "POSITIVE ROOT")
    has(T, f"A = 2(0.75) = {fmt3(2 * 0.75)} M/S²",
        f"V = 10/1.6\n = {fmt3(10 / 1.6)} M/S AT T = {fmt3((2.0 + 3.6) / 2)} S",
        f"0.2/9.7 * 100 = {fmt3(abs(9.6 - 9.8) / ((9.6 + 9.8) / 2) * 100)} %",
        f"1 YD = {round(1 / 1.0936, 4)} M",
        f"100/1.0936\n = {fmt3(100 / 1.0936)} M", f"100(1.0936)\n = {fmt3(100 * 1.0936)} YD")
    # launch-from-height example: up at 10 m/s from 15 m -> 4.9T^2 - 10T - 15 = 0
    a, b, cc = 4.9, -10, -15
    disc = b * b - 4 * a * cc
    t1, t2 = sorted(((-b - math.sqrt(disc)) / (2 * a), (-b + math.sqrt(disc)) / (2 * a)))
    has(T, f"B²-4AC = 100 + {fmt3(-4 * a * cc)} = {fmt3(disc)}", f"T = {fmt3(t2)} S (OTHER ROOT",
        f"{fmt3(t1)} S IS BEFORE LAUNCH", "4.9T² - 10T - 15 = 0", "4.9T² - V0Y*T - H = 0")


def t_transcript():
    keys = [1, 2, 3, 4, 5, 6, 1, 2, 3, 4, 5, 7]
    res = run(keys, program="PHYSREF")
    assert_clean(res)
    print("\n----- full PHYSREF transcript (keys " + str(keys) + ") -----")
    print(res.text())
    print("----- end of transcript -----")


c.check("lint: build.py --check --only PHYSREF is clean", t_lint)
c.check("source: only Degree/Lbl/Goto/Menu(/ClrHome/Disp/Pause, no variables, 1-10 rows per screen", t_source_structure)
c.check("strings: allowed characters only, no ':' or '...', '⁻' only in ⁻1(", t_strings_charset)
c.check("QUIT from page 1 and 2, MORE > / BACK ping-pong", t_quit_paths)
c.check("every topic: clean run, screen count, k/N headers, returns to its own page (page 2 via QUIT and BACK)", t_every_topic)
c.check("all topics in one run", t_all_topics_one_run)
c.check("no variables/strings/lists touched, Degree mode set", t_no_variables_touched)
c.check("menus: <= 7 options, title <= 24, options <= 22, BACK/QUIT last", t_menus_fit)
c.check("scalars vs vectors content", t_scalars_vectors)
c.check("5 equations with missing variable + how to pick", t_five_equations)
c.check("free fall: a = -9.8 always, top, symmetry, 1,3,5 and 1,4,9 numbers", t_free_fall)
c.check("graph stacks: slope down, area up, x-t/v-t/a-t shapes", t_graphs)
c.check("factor-of-change rules and examples", t_factor_of_change)
c.check("chase: positions equal, twice the speed, example", t_chase)
c.check("horizontal launch: vx const, v0y = 0, same t, 20 m example", t_horizontal)
c.check("angled launch: components, y decides t, 45°, complementary angles, example", t_angled)
c.check("river crossing: independent, t, drift, resultant, angles, aim upstream", t_river)
c.check("labs: ramp, 100 m dash, percent difference, yards, launch from height", t_labs)
c.check("print full transcript", t_transcript)
sys.exit(c.done())
