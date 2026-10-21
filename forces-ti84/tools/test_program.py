#!/usr/bin/env python3
"""Trace tests: run the real FORCES.8xp files in the TI-BASIC simulator.

    python3 tools/test_program.py        (after python3 tools/build.py)

Every test runs both builds (TI-84 Plus mono with both number display
styles, and TI-84 Plus CE) and fails on any simulator violation: memory
leak, text scrolled/cleared/hidden before it was seen, text past the screen
edge, text overwritten, pause indicator overlap, or a calculator error.
The required cases and path tests check the key answers and words; the
fuzz test checks EVERY answer row of every solver against reference.py.
The run ends with a line-coverage check: every line of both programs must
execute at least once.
"""

import collections
import math
import os
import random
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path[:0] = [HERE, ROOT]

from tivars.types import TIProgram  # noqa: E402

import reference as ref  # noqa: E402
from tisim import Machine, values  # noqa: E402

SRC = {p: TIProgram.open(os.path.join(ROOT, f, "FORCES.8xp")).string()
       for p, f in (("mono", "TI-84_Plus"), ("ce", "TI-84_Plus_CE"))}
# (profile, number style): mono shows .5 on classic OS, 0.5 on MathPrint OS
TARGETS = [("mono", "classic"), ("mono", "mathprint"), ("ce", "mathprint")]
COVER = {p: set() for p in SRC}
TOL = 0.01          # assignment tolerance
ROUND_TOL = 0.0011  # TI shows round(x,3); reference.py is unrounded
# prompts where any number (including the test's "bad" ⁻1) is legal
OPEN_PROMPTS = ("AY", "AX", "F (N)=", "FORCE F", "F1", "F2", "F3", "F4")


def calc_keys(profile, keys):
    """The CE's FLAT SURFACE PULL opens a submenu first: "FLAT" means the
    pull-F-known solver on both calculators, "FLAT>F" the CE's FIND PULL F."""
    out = []
    for k in keys:
        if k == "FLAT":
            out += ["FLAT"] + (["PULL F KNOWN"] if profile == "ce" else [])
        elif k == "FLAT>F":
            out += ["FLAT", "FIND PULL F"]
        else:
            out.append(k)
    return out


def run(profile, keys, style="classic", init=None, quit=True, blank="empty"):
    state = {"G": 9.8}
    state.update(init or {})
    keys = calc_keys(profile, keys)
    m = Machine(SRC[profile], profile, keys + (["MORE", "QUIT"] if quit else []),
                init=state, style=style, blank=blank).run()
    COVER[profile] |= m.hit
    return m


def check_clean(tc, m, finished=True):
    tc.assertEqual(m.violations, [], f"violations on {m.profile}/{m.style}")
    if finished:
        tc.assertEqual(m.status, "stopped", m.status)
        tc.assertEqual(m.stack, [], "block stack not empty at QUIT")


def value(m, *labels):
    for label, v, unit in values(m.pauses):
        if label in labels:
            return v, unit
    raise AssertionError(f"no row labelled {labels} in {m.pauses}")


def shows(m, text):
    return any(text in row for page in m.pauses for row in page)


def num(x):
    """Format a test input the way it is typed on the calculator."""
    s = f"{x:g}"
    return s.replace("-", "⁻")


class Base(unittest.TestCase):
    def each(self):
        return TARGETS

    @staticmethod
    def tol(m, label, unit, want, base=ROUND_TOL):
        """Allowed difference for a displayed value.  On the mono screen a
        long label (MGSINθ, FS MAX, OTHER, ...) with a value of 1000 or more
        is shown as a whole number so its unit still fits."""
        if m.profile == "mono" and len(label) + len(unit) > 6 and abs(want) >= 999.5:
            return 0.5 + 1e-9
        return base + abs(want) * 1e-9

    def expect(self, m, labels, unit, want, tol=TOL):
        got, u = value(m, *labels)
        self.assertAlmostEqual(got, want, delta=max(tol, self.tol(m, labels[0], unit, want)),
                               msg=f"{labels} on {m.profile}/{m.style}: {m.pauses}")
        self.assertEqual(u, unit, f"unit for {labels}")
        return got


# --------------------------------------------------------- required cases
class RequiredCases(Base):
    """The 12 assignment cases, traced through the TI-BASIC on both calcs.

    Each value is checked against the assignment's number (tolerance 0.01)
    and against reference.py (to the 3 displayed decimals).
    """

    def both(self, m, labels, unit, assignment, python):
        got = self.expect(m, labels, unit, assignment)
        self.assertAlmostEqual(got, python, delta=ROUND_TOL)

    def test_01_incline_at_rest(self):
        r = ref.incline_rest(5.0, 30)
        for p, st in self.each():
            m = run(p, ["INCLINE", "AT REST", "5.0", "30", ""], st)
            check_clean(self, m)
            self.both(m, ("N",), "N", 42.44, r["N"])
            self.both(m, ("FS", "FS NEEDED"), "N", 24.5, r["fs"])
            self.assertTrue(shows(m, "FS POINTS UPHILL"))

    def test_02_elevator_down_slowing(self):
        r = ref.elevator_scale(60, 1.5, moving="DOWN", change="SLOWING")
        for p, st in self.each():
            m = run(p, ["ELEVATOR", "FIND SCALE", "60", "1.5", "MOTION",
                        "MOVING DOWN", "SLOWING"], st)
            check_clean(self, m)
            self.both(m, ("N", "SCALE N"), "N", 678, r["N"])
            self.assertTrue(shows(m, "ACCEL: UP") and shows(m, "HEAVIER"))

    def test_03_elevator_scale_390(self):
        r = ref.elevator_accel(50, 390)
        for p, st in self.each():
            m = run(p, ["ELEVATOR", "ACCEL FROM", "50", "390", "UNKNOWN"], st)
            check_clean(self, m)
            self.both(m, ("AY", "ACCEL AY"), "M/S²", -2.0, r["ay"])
            self.assertTrue(shows(m, "ACCEL: DOWN"))
            for words in r["motion"]:
                self.assertTrue(shows(m, words), words)

    def test_04_table_hanger_3_2(self):
        r = ref.table_hanger(3, 2)
        for p, st in self.each():
            m = run(p, ["TABLE", "3", "2", "0"], st)
            check_clean(self, m)
            self.both(m, ("A",), "M/S²", 3.92, r["a"])
            self.both(m, ("T",), "N", 11.76, r["T"])
            self.assertTrue(shows(m, "HANGER MOVES") and shows(m, "TO PULLEY"))
            self.assertTrue(shows(m, "+=TO PULLEY"))

    def test_05_atwood_6_4(self):
        r = ref.atwood(6, 4)
        for p, st in self.each():
            m = run(p, ["ATWOOD", "FIND A AND T", "6", "4"], st)
            check_clean(self, m)
            self.both(m, ("A",), "M/S²", 1.96, r["a"])
            self.both(m, ("T",), "N", 47.04, r["T"])
            self.assertTrue(shows(m, "M2G<T<M1G") and shows(m, "CHECK OK"))
            self.assertTrue(shows(m, "M1G-T=M1A") and shows(m, "T-M2G=M2A"))

    def test_06_flat_constant_velocity(self):
        r = ref.flat_pull(5, 25, 0, "CONSTANT")
        for p, st in self.each():
            m = run(p, ["FLAT", "5", "25", "0", "CONSTANT"], st)
            check_clean(self, m)
            self.both(m, ("FRIC",), "N", 25, r["f"])
            self.both(m, ("N",), "N", 49, r["N"])

    def test_07_elevator_up_2(self):
        r = ref.elevator_scale(60, 2.0, direction="UP")
        for p, st in self.each():
            m = run(p, ["ELEVATOR", "FIND SCALE", "60", "2.0", "#1"], st)
            check_clean(self, m)
            self.both(m, ("N", "SCALE N"), "N", 708, r["N"])

    def test_08_elevator_415_moving_up(self):
        r = ref.elevator_accel(50, 415, velocity="UP")
        for p, st in self.each():
            m = run(p, ["ELEVATOR", "ACCEL FROM", "50", "415", "#1"], st)
            check_clean(self, m)
            self.both(m, ("AY", "ACCEL AY"), "M/S²", -1.5, r["ay"])
            self.assertTrue(shows(m, "SLOWING DOWN"))

    def test_09_atwood_3_5(self):
        r = ref.atwood(3, 5)
        for p, st in self.each():
            m = run(p, ["ATWOOD", "FIND A AND T", "3", "5"], st)
            check_clean(self, m)
            self.both(m, ("A",), "M/S²", 2.45, r["a"])
            self.both(m, ("T",), "N", 36.75, r["T"])
            self.assertTrue(shows(m, "M2 (HEAVY): DOWN"))   # 5 kg goes down
            self.assertTrue(shows(m, "M1 (LIGHT): UP"))

    def test_10_table_hanger_4_1(self):
        r = ref.table_hanger(4, 1)
        for p, st in self.each():
            m = run(p, ["TABLE", "4", "1", "0"], st)
            check_clean(self, m)
            self.both(m, ("A",), "M/S²", 1.96, r["a"])
            self.both(m, ("T",), "N", 7.84, r["T"])

    def test_11_third_law_double_mass(self):
        for p, st in self.each():
            m = run(p, ["3RD LAW", "1", "2", ""], st)          # F left blank
            check_clean(self, m)
            ratio, _ = value(m, "RATIO")
            self.assertAlmostEqual(ratio, 2, delta=TOL)
            m = run(p, ["3RD LAW", "1", "2", "10"], st)
            check_clean(self, m)
            aa, _ = value(m, "AA", "AA=-F/MA")
            ab, _ = value(m, "AB", "AB=F/MB")
            self.assertAlmostEqual(abs(aa), 2 * abs(ab), delta=TOL)
            self.assertLess(aa * ab, 0)                      # opposite directions

    def test_12_flat_angled_pull(self):
        r = ref.flat_pull(5, 20, 30, "FRICTION", 12)
        for p, st in self.each():
            m = run(p, ["FLAT", "5", "20", "30", "FRICTION", "12"], st)
            check_clean(self, m)
            self.both(m, ("N",), "N", 39.0, r["N"])
            self.both(m, ("AX",), "M/S²", 1.064, r["ax"])
            self.assertTrue(shows(m, "ACCEL: RIGHT"))


# ---------------------------------------------------- worksheet problems
CE_STYLES = [("ce", "mathprint")]
MOTION = ["MORE", "MOTION"]


class WorksheetCases(Base):
    """Both 'Non-Equilibrium Problems' worksheets, keyed into the CE program.
    Each answer is checked against the sheet (1%) and against reference.py."""

    def sheet(self, m, labels, unit, sheet, python, rel=0.01):
        got = self.expect(m, labels, unit, python, ROUND_TOL)
        self.assertAlmostEqual(got, sheet, delta=max(0.011, abs(sheet) * rel))
        return got

    def ce(self, keys):
        m = run("ce", keys, "mathprint")
        check_clean(self, m)
        return m

    # ---- Fnet = ma in the VERTICAL direction
    def test_v1_helicopter_lift(self):
        m = self.ce(["MORE", "SIMPLE", "UP FORCE", "4500", "2"])
        self.sheet(m, ("T",), "N", 53100, ref.hanging_accel(4500, 2)["T"])
        self.assertTrue(shows(m, "LIFT"))

    def test_v2_grocery_bag(self):
        m = self.ce(["MORE", "ROPE", "WILL IT HOLD", "15", "230", "7"])
        self.sheet(m, ("T NEEDED",), "N", 252, ref.rope_hold(15, 230, 7)["T"])
        self.assertTrue(shows(m, "BREAKS: T NEEDED > TMAX"))

    def test_v3_v4_v5_max_acceleration(self):
        for mass, tmax, want in (("10", "100", 0.2), ("42", "450", 0.914),
                                 ("2.0ᴇ⁻4", "2.0ᴇ⁻3", 0.20)):
            m = self.ce(["MORE", "ROPE", "MAX A, LIFTING", mass, tmax])
            r = ref.rope_max_lift(float(mass.replace("ᴇ⁻", "e-")),
                                  float(tmax.replace("ᴇ⁻", "e-")))
            self.sheet(m, ("AMAX UP",), "M/S²", want, r["a_max"])
        self.assertTrue(shows(m, "TMAX=0.002 N") and shows(m, "MG=0.00196 N"))

    def test_v6_rocket(self):
        m = self.ce(MOTION + ["VERTICAL, MOVING UP", "M/S", "V0, V, D", "25", "45",
                              "100", "70"])
        r = ref.kinematics("VVD", 25, v=45, d=100)
        self.sheet(m, ("A",), "M/S²", 7, r["a"])
        self.sheet(m, ("F UP",), "N", 1176, ref.motion_force(70, 7, "UP")["F_up"])

    def test_v8_backpack(self):
        m = self.ce(MOTION + ["HORIZONTAL", "M/S", "V0, V, T", "0", "2", "16", ""])
        self.sheet(m, ("A",), "M/S²", 0.125, 0.125)
        m = self.ce(["FLAT>F", "2", "30", "0.125", "NONE"])
        self.sheet(m, ("F",), "N", 0.289, ref.pull_force(2, 30, 0.125)["F"])

    # ---- Fnet = ma in the HORIZONTAL direction
    def test_h1_stop_car(self):
        m = self.ce(MOTION + ["HORIZONTAL", "KM/H", "V0, V, T", "90", "0", "8", "1100"])
        self.sheet(m, ("FNET",), "N", -3437.5, -3437.5)
        self.assertTrue(shows(m, "OPPOSITE THE MOTION") and shows(m, "V0=25 M/S"))

    def test_h2_towrope(self):
        m = self.ce(["MORE", "ROPE", "TOWING", "700", "1500", "25"])
        self.sheet(m, ("AMAX",), "M/S²", 2.1, ref.tow_max(700, 1500, 25)["a_max"])
        m = self.ce(MOTION + ["HORIZONTAL", "KM/H", "V0, V, A", "0", "30", "2.1", ""])
        self.sheet(m, ("T",), "S", 3.97, ref.kinematics("VVA", 0, v=30 * ref.KMH, a=2.1)["t"])

    def test_h3_dragster(self):
        m = self.ce(MOTION + ["HORIZONTAL", "M/S", "V0, V, T", "0", "26.3", "0.59", "875"])
        a = ref.kinematics("VVT", 0, v=26.3, t=0.59)["a"]
        self.sheet(m, ("FNET",), "N", 3.9e4, 875 * a, rel=0.01)
        m = self.ce(["MORE", "SIMPLE", "SAME A", "875", "68", ""])
        self.sheet(m, ("F1/F2",), "", 13, 875 / 68, rel=0.04)

    def test_h4_dogs(self):
        m = self.ce(["MORE", "SIMPLE", "SUM", "42", "⁻35", "", "", "2.5"])
        self.sheet(m, ("A",), "M/S²", 2.8, 2.8)

    def test_h5_baseball(self):
        m = self.ce(MOTION + ["HORIZONTAL", "M/S", "V0, V, T", "30", "0", "0.005", "0.145"])
        self.sheet(m, ("FNET",), "N", -870, -870)
        self.assertTrue(shows(m, "OPPOSITE THE MOTION"))

    def test_h6_truck(self):
        m = self.ce(MOTION + ["HORIZONTAL", "M/S", "V0, V, D", "12", "0", "15", "2000"])
        self.sheet(m, ("FNET",), "N", -9600, -9600)

    def test_h7_box_45(self):
        m = self.ce(["FLAT", "20", "50", "45", "FRICTION", "0"])
        a = ref.flat_pull(20, 50, 45, "FRICTION", 0)["ax"]
        self.sheet(m, ("AX",), "M/S²", 1.77, a)
        m = self.ce(MOTION + ["HORIZONTAL", "M/S", "V0, A, T", "0", "1.768", "2", ""])
        self.sheet(m, ("V",), "M/S", 3.54, 3.536)


class CEPaths(Base):
    """Every branch of the CE-only solvers."""

    def each(self):
        return CE_STYLES

    def test_find_pull_branches(self):
        for p, st in self.each():
            r = ref.pull_force(5, 30, 1, "FORCE", 4)
            m = run(p, ["FLAT>F", "5", "30", "1", "FRICTION FORCE", "4"], st)
            check_clean(self, m)
            self.expect(m, ("F",), "N", r["F"], ROUND_TOL)
            r = ref.pull_force(5, -20, 0, "MUK", 0.3)
            m = run(p, ["FLAT>F", "5", "⁻20", "0", "MUK", "0.3"], st)
            check_clean(self, m)
            self.expect(m, ("F",), "N", r["F"], ROUND_TOL)
            self.expect(m, ("FRIC",), "N", r["f"], ROUND_TOL)
            self.assertTrue(shows(m, "CONSTANT V"))
            m = run(p, ["FLAT>F", "5", "0", "⁻1", "NONE"], st)
            check_clean(self, m)
            self.assertTrue(shows(m, "F<0: NOT POSSIBLE."))
            m = run(p, ["FLAT>F", "5", "0", "⁻1", "MUK", "0.5"], st)
            check_clean(self, m)
            self.assertTrue(shows(m, "SLOWING") and shows(m, "BACKWARD"))
            m = run(p, ["FLAT>F", "5", "⁻80", "1", "MUK", "1"], st)
            check_clean(self, m)
            self.assertTrue(shows(m, "NO F IS ENOUGH."))
            m = run(p, ["FLAT>F", "1", "80", "50", "NONE"], st)
            check_clean(self, m)
            self.assertTrue(shows(m, "LIFTS OFF"))
            m = run(p, ["FLAT>F", "2", "90", "30", "0.125", "NONE"], st)
            check_clean(self, m)                    # 90 is refused, asked again
            self.assertEqual(sum(1 for pr, _ in m.inputs if "θ" in pr), 2)

    def test_motion_branches(self):
        cases = [  # keys after the case pick, expected rows
            (["V0, A, D", "10", "⁻2", "9"], "VAD", dict(v0=10, a=-2, d=9)),
            (["V0, A, D", "4", "0", "8"], "VAD", dict(v0=4, a=0, d=8)),
            (["V0, T, D", "2", "4", "20"], "VTD", dict(v0=2, t=4, d=20)),
            (["V0, A, T", "5", "⁻2", "4"], "VAT", dict(v0=5, a=-2, t=4)),
            (["V0, V, A", "3", "3.5", "0.5"], "VVA", dict(v0=3, v=3.5, a=0.5)),
        ]
        for p, st in self.each():
            for keys, known, kw in cases:
                r = ref.kinematics(known, **kw)
                m = run(p, MOTION + ["HORIZONTAL", "M/S"] + keys + [""], st)
                check_clean(self, m)
                for lab, unit in (("A", "M/S²"), ("V", "M/S"), ("T", "S"), ("D", "M")):
                    self.expect(m, (lab,), unit, r[lab.lower()], ROUND_TOL)
            self.assertTrue(shows(m, "SPEEDING UP"))
            m = run(p, MOTION + ["HORIZONTAL", "M/S", "V0, A, T", "5", "⁻2", "4", ""], st)
            self.assertTrue(shows(m, "TURNED AROUND"))
            for keys, word in ((["V0, V, D", "0", "0", "5"], "YET IT MOVED"),
                               (["V0, A, D", "4", "⁻1", "20"], "STOPS BEFORE"),
                               (["V0, A, D", "0", "0", "5"], "NEVER MOVES"),
                               (["V0, V, A", "3", "5", "0"], "NEVER"),
                               (["V0, V, A", "3", "5", "⁻1"], "NEVER REACHES")):
                m = run(p, MOTION + ["HORIZONTAL", "M/S"] + keys, st)
                check_clean(self, m)
                self.assertTrue(shows(m, "CANNOT SOLVE:") and shows(m, word), keys)
            m = run(p, MOTION + ["VERTICAL, MOVING DOWN", "M/S", "V0, V, T", "2", "8",
                                 "2", "60"], st)
            check_clean(self, m)
            self.expect(m, ("F UP",), "N", 60 * (9.8 - 3), ROUND_TOL)
            m = run(p, MOTION + ["VERTICAL, MOVING DOWN", "M/S", "V0, V, T", "0", "30",
                                 "2", "1"], st)
            check_clean(self, m)
            self.assertTrue(shows(m, "PUSH DOWN"))
            m = run(p, MOTION + ["VERTICAL, MOVING UP", "M/S", "V0, V, T", "30", "0",
                                 "1", "1"], st)
            check_clean(self, m)
            self.assertTrue(shows(m, "PUSH DOWN"))
            m = run(p, MOTION + ["HORIZONTAL", "M/S", "V0, V, T", "5", "5", "2", "3"], st)
            check_clean(self, m)
            self.assertTrue(shows(m, "ZERO (EQUILIBRIUM)") and shows(m, "CONSTANT V"))

    def test_rope_branches(self):
        for p, st in self.each():
            m = run(p, ["MORE", "ROPE", "MAX A, LIFTING", "20", "100"], st)
            check_clean(self, m)
            self.assertTrue(shows(m, "BREAKS EVEN"))
            m = run(p, ["MORE", "ROPE", "WILL IT HOLD", "15", "230", "2"], st)
            check_clean(self, m)
            self.assertTrue(shows(m, "HOLDS: T NEEDED"))
            m = run(p, ["MORE", "ROPE", "WILL IT HOLD", "15", "230", "⁻12"], st)
            check_clean(self, m)
            self.assertTrue(shows(m, "NOT POSSIBLE"))
            m = run(p, ["MORE", "ROPE", "TOWING", "700", "100", "150"], st)
            check_clean(self, m)
            self.assertTrue(shows(m, "NO SPEEDUP"))
            m = run(p, ["MORE", "ROPE", "TOWING", "700", "1500", ""], st)
            check_clean(self, m)
            self.expect(m, ("AMAX",), "M/S²", 1500 / 700, ROUND_TOL)

    def test_same_a_with_acceleration(self):
        for p, st in self.each():
            m = run(p, ["MORE", "SIMPLE", "SAME A", "875", "68", "44.576"], st)
            check_clean(self, m)
            self.expect(m, ("F1",), "N", 875 * 44.576, ROUND_TOL)
            self.expect(m, ("F2",), "N", 68 * 44.576, ROUND_TOL)

    def test_ce_validation_messages(self):
        bad = {"θ (DEG)=": "95"}
        good = {"θ": "30", "MUS=": "0.5", "MUK": "0.2", "SCALE": "100"}
        paths = [["FLAT>F", "#3"], ["FLAT>F", "#2"], MOTION + ["#1", "#1", "#1"],
                 MOTION + ["#1", "#1", "#2"], MOTION + ["#1", "#1", "#4"],
                 ["MORE", "ROPE", "#1"], ["MORE", "ROPE", "#3"],
                 ["MORE", "SIMPLE", "SAME A"]]
        for p, st in self.each():
            for path in paths:
                menus = calc_keys(p, path) + ["MORE", "QUIT"]
                seen = set()

                def answer(kind, info):
                    if kind == "menu":
                        return menus.pop(0) if menus else None
                    if info not in seen:
                        seen.add(info)
                        return bad.get(info, "⁻1")
                    return next((v for k, v in good.items() if k in info), "2")

                m = Machine(SRC[p], p, answer, init={"G": 9.8}, style=st).run()
                COVER[p] |= m.hit
                check_clean(self, m)
                asked = collections.Counter(pr for pr, _ in m.inputs)
                for prompt in seen:
                    if not any(k in prompt for k in OPEN_PROMPTS + ("A (M/S²)=", "A (+")):
                        self.assertGreaterEqual(asked[prompt], 2,
                                                f"{prompt!r} accepted a bad value")


# ------------------------------------------------------- every other path
class Paths(Base):
    """Impossible setups, messages, validation loops, settings, modes."""

    def test_validation_reprompts(self):
        for p, st in self.each():
            m = run(p, ["ELEVATOR", "FIND SCALE", "⁻5", "0", "60", "⁻1", "2",
                        "#1"], st)
            check_clean(self, m)
            self.assertEqual(sum(1 for pr, _ in m.inputs if pr.startswith("M")), 3)
            self.expect(m, ("N", "SCALE N"), "N", 708)

    def test_elevator_paths(self):
        for p, st in self.each():
            for keys, word in [
                    (["#2"], "LIGHTER"), (["#3"], "NORMAL"),
                    (["MOTION", "MOVING UP", "SPEEDING"], "HEAVIER"),
                    (["MOTION", "MOVING UP", "CONSTANT"], "NORMAL"),
                    (["MOTION", "AT REST"], "NORMAL")]:
                m = run(p, ["ELEVATOR", "FIND SCALE", "60", "1.5"] + keys, st)
                check_clean(self, m)
                self.assertTrue(shows(m, word), (keys, word))
            m = run(p, ["ELEVATOR", "FIND SCALE", "50", "9.8", "#2"], st)
            check_clean(self, m)
            self.assertTrue(shows(m, "WEIGHTLESS (N=0)"))
            m = run(p, ["ELEVATOR", "FIND SCALE", "50", "12", "#2"], st)
            check_clean(self, m)
            self.assertTrue(shows(m, "N<0: LIFTS OFF"))

    def test_elevator_accel_velocity_cases(self):
        for p, st in self.each():
            for n, vel, words in [("390", "#2", ["SPEEDING UP"]),
                                  ("590", "#1", ["SPEEDING UP"]),
                                  ("590", "#2", ["SLOWING DOWN"]),
                                  ("590", "#3", ["UP+SPEEDING", "DOWN+SLOWING"]),
                                  ("490", "#3", ["CONSTANT", "(OR AT REST)"])]:
                m = run(p, ["ELEVATOR", "ACCEL FROM", "50", n, vel], st)
                check_clean(self, m)
                for w in words:
                    self.assertTrue(shows(m, w), (n, vel, w))

    def test_free_fall_and_mass(self):
        for p, st in self.each():
            m = run(p, ["ELEVATOR", "FREE FALL"], st)
            check_clean(self, m)
            self.expect(m, ("AY", "ACCEL AY"), "M/S²", -9.8)
            self.assertTrue(shows(m, "WEIGHTLESS"))
            m = run(p, ["ELEVATOR", "FIND MASS", "708", "2"], st)
            check_clean(self, m)
            self.expect(m, ("M", "MASS M"), "KG", 60)
            m = run(p, ["ELEVATOR", "FIND MASS", "100", "⁻9.8"], st)
            check_clean(self, m)
            self.assertTrue(shows(m, "IMPOSSIBLE:"))

    def test_atwood_paths(self):
        for p, st in self.each():
            m = run(p, ["ATWOOD", "FIND A AND T", "4", "4"], st)
            check_clean(self, m)
            self.assertTrue(shows(m, "EQUILIBRIUM"))
            self.expect(m, ("T",), "N", 39.2)
            m = run(p, ["ATWOOD", "OTHER" if p == "ce" else "2ND", "1.96", "6",
                        "HEAVIER"], st)
            check_clean(self, m)
            self.expect(m, ("OTHER", "OTHER MASS"), "KG", 4)
            m = run(p, ["ATWOOD", "#2", "2.45", "3", "LIGHTER"], st)
            check_clean(self, m)
            self.expect(m, ("OTHER", "OTHER MASS"), "KG", 5)
            self.expect(m, ("T",), "N", 36.75)
            m = run(p, ["ATWOOD", "#2", "9.8", "3", "LIGHTER"], st)
            check_clean(self, m)
            self.assertTrue(shows(m, "IMPOSSIBLE:"))

    def test_table_friction_paths(self):
        for p, st in self.each():
            r = ref.table_hanger(3, 2, muk=0.2)
            m = run(p, ["TABLE", "3", "2", "0.2", ""], st)       # mus blank
            check_clean(self, m)
            self.expect(m, ("A",), "M/S²", r["a"], ROUND_TOL)
            self.expect(m, ("FK", "FK (KINETIC)"), "N", r["fk"], ROUND_TOL)
            m = run(p, ["TABLE", "5", "1", "0.1", "0.05", "0.3"], st)  # 0.05<muk
            check_clean(self, m)
            self.assertTrue(any(pr == "MUS=" for pr, _ in m.inputs))
            self.assertTrue(shows(m, "BLOCK STAYS PUT"))
            self.expect(m, ("FS", "FS (STATIC)"), "N", 9.8)
            self.expect(m, ("FSMAX", "FS MAX = MUS*N"), "N", 14.7)

    def test_flat_paths(self):
        for p, st in self.each():
            m = run(p, ["FLAT", "1", "50", "90", "CONSTANT"], st)
            check_clean(self, m)
            self.assertTrue(shows(m, "N<0: LIFTS OFF"))
            r = ref.flat_pull(5, 20, 30, "MUK", 0.2)
            m = run(p, ["FLAT", "5", "20", "30", "MUK", "0.2"], st)
            check_clean(self, m)
            self.expect(m, ("FRIC",), "N", r["f"], ROUND_TOL)
            m = run(p, ["FLAT", "5", "20", "0", "ACCEL", "5"], st)
            check_clean(self, m)
            self.assertTrue(shows(m, "IMPOSSIBLE.") and shows(m, "RIGHT (!)"))
            m = run(p, ["FLAT", "1", "5", "90", "CONSTANT"], st)
            check_clean(self, m)
            self.assertTrue(shows(m, "NO FRICTION"))
            m = run(p, ["FLAT", "5", "5", "0", "MUK", "0.5"], st)
            check_clean(self, m)
            self.assertTrue(shows(m, "STAYS PUT"))
            m = run(p, ["FLAT", "5", "20", "⁻30", "CONSTANT"], st)
            check_clean(self, m)
            self.expect(m, ("N",), "N", 59)
            self.expect(m, ("MU", "MU NEEDED"), "",
                        17.3205 / 59, ROUND_TOL)

    def test_incline_paths(self):
        for p, st in self.each():
            m = run(p, ["INCLINE", "AT REST", "5", "30", "0.6"], st)
            check_clean(self, m)
            self.assertTrue(shows(m, "YES:") and shows(m, "STAYS PUT"))
            m = run(p, ["INCLINE", "AT REST", "5", "30", "0.5"], st)
            check_clean(self, m)
            self.assertTrue(shows(m, "NO: WILL SLIDE"))
            r = ref.incline_slide(2, 30, 0.2)
            m = run(p, ["INCLINE", "SLIDING", "2", "30", "0.2"], st)
            check_clean(self, m)
            self.expect(m, ("A",), "M/S²", r["a"], ROUND_TOL)
            m = run(p, ["INCLINE", "SLIDING", "2", "10", "0.5"], st)
            check_clean(self, m)
            self.assertTrue(shows(m, "SLOWS DOWN"))
            m = run(p, ["INCLINE", "FRICTIONLESS", "2", "30"], st)
            check_clean(self, m)
            self.expect(m, ("A",), "M/S²", 4.9)
            m = run(p, ["INCLINE", "MIN MUS", "1", "30"], st)
            check_clean(self, m)
            self.expect(m, ("MIN MUS",), "", ref.incline_min_mus(1, 30)["mus_min"],
                        ROUND_TOL)
            m = run(p, ["INCLINE", "AT REST", "5", "95", "90", "0", "30", ""], st)
            check_clean(self, m)
            self.assertEqual(sum(1 for pr, _ in m.inputs if "θ" in pr), 4)
            self.expect(m, ("FS", "FS NEEDED"), "N", 24.5)
            self.assertTrue(shows(m, "DOWNHILL") and shows(m, "INTO SLOPE"))

    def test_incline_push_and_hanger(self):
        for p, st in self.each():
            r = ref.incline_push(5, 30, 40, 0.2)
            m = run(p, ["INCLINE", "PUSHED", "5", "30", "40", "0.2"], st)
            check_clean(self, m)
            self.expect(m, ("A",), "M/S²", r["a"], ROUND_TOL)
            self.expect(m, ("F NEED", "F NEEDED"), "N", r["F_const"], ROUND_TOL)
            self.assertTrue(shows(m, "F-MGSINθ-FK=MA") and shows(m, "UP"))
            m = run(p, ["INCLINE", "PUSHED", "5", "30", "10", "0.2"], st)
            check_clean(self, m)
            self.assertTrue(shows(m, "SLOW") and shows(m, "NOT START UP")
                            or shows(m, "START UP THE SLOPE."))
            m = run(p, ["INCLINE", "PUSHED", "2", "30", "9.8", "0"], st)
            check_clean(self, m)
            self.expect(m, ("A",), "M/S²", 0)
            self.assertTrue(shows(m, "CONST"))

            r = ref.incline_hanger(4, 3, 30, 0.2)
            m = run(p, ["INCLINE", "HANGER", "4", "30", "3", "0.2", ""], st)
            check_clean(self, m)
            self.expect(m, ("A",), "M/S²", r["a"], ROUND_TOL)
            self.expect(m, ("T",), "N", r["T"], ROUND_TOL)
            self.assertTrue(shows(m, "BLOCK MOVES UP") and shows(m, "T-MGSINθ-FK=MA")
                            and shows(m, "MG-T=MA"))
            r = ref.incline_hanger(10, 2, 40)
            m = run(p, ["INCLINE", "HANGER", "10", "40", "2", "0"], st)
            check_clean(self, m)
            self.expect(m, ("A",), "M/S²", r["a"], ROUND_TOL)
            self.assertTrue(shows(m, "BLOCK MOVES DOWN") and shows(m, "HANGER MOVES UP")
                            and shows(m, "MGSINθ-T-FK=MA"))
            for keys, word, fs in ((["4", "30", "2.5", "0.2", "0.4"], "DOWNHILL", 4.9),
                                   (["4", "30", "1.5", "0.2", "0.4"], "UPHILL", 4.9),
                                   (["2", "30", "1", "0"], "NONE NEEDED", 0)):
                m = run(p, ["INCLINE", "HANGER"] + keys, st)
                check_clean(self, m)
                self.assertTrue(shows(m, "BLOCK STAYS PUT") and shows(m, word), keys)
                self.expect(m, ("FS",), "N", fs)

    def test_simple_cases(self):
        for p, st in self.each():
            m = run(p, ["MORE", "SIMPLE", "HANGING", "2"], st)
            check_clean(self, m)
            self.expect(m, ("T",), "N", 19.6)
            m = run(p, ["MORE", "SIMPLE", "TERMINAL", "70"], st)
            check_clean(self, m)
            self.expect(m, ("FAIR",), "N", 686)
            m = run(p, ["MORE", "SIMPLE", "#3", "2", "⁻1"], st)
            check_clean(self, m)
            self.expect(m, ("T",), "N", 17.6)
            self.assertTrue(shows(m, "T<MG"))
            m = run(p, ["MORE", "SIMPLE", "#3", "2", "⁻12"], st)
            check_clean(self, m)
            self.assertTrue(shows(m, "ROPE SLACK"))
            m = run(p, ["MORE", "SIMPLE", "SUM", "10", "⁻4", "6", "", "2"], st)
            check_clean(self, m)
            self.expect(m, ("A",), "M/S²", 6)
            self.assertTrue(shows(m, "EQUILIBRIUM: NO"))
            m = run(p, ["MORE", "SIMPLE", "SUM", "5", "⁻5", "", "", "3"], st)
            check_clean(self, m)
            self.assertTrue(shows(m, "EQUILIBRIUM: YES"))

    def test_concept_check(self):
        cases = [("MOVING UP", "SPEEDING", "ACCEL: UP", "EQUILIBRIUM: NO"),
                 ("MOVING DOWN", "SLOWING", "ACCEL: UP", "EQUILIBRIUM: NO"),
                 ("MOVING RIGHT", "CONSTANT", "ACCEL: ZERO", "EQUILIBRIUM: YES"),
                 ("MOVING LEFT", "SLOWING", "NET F: RIGHT", "EQUILIBRIUM: NO"),
                 ("MOVING LEFT", "SPEEDING", "NET F: LEFT", "EQUILIBRIUM: NO")]
        for p, st in self.each():
            for move, change, want, eq in cases:
                m = run(p, ["MORE", "CONCEPT", move, change], st)
                check_clean(self, m)
                self.assertTrue(shows(m, want) and shows(m, eq), (move, change))
            m = run(p, ["MORE", "CONCEPT", "AT REST"], st)
            check_clean(self, m)
            self.assertTrue(shows(m, "EQUILIBRIUM: YES"))
            m = run(p, ["MORE", "CONCEPT", "V=0"], st)
            check_clean(self, m)
            self.assertTrue(shows(m, "NOT") and shows(m, "ACCEL: G DOWN"))

    def test_settings_and_g(self):
        for p, st in self.each():
            m = run(p, ["MORE", "SETTINGS", "10", "ELEVATOR", "FIND SCALE",
                        "60", "2", "#1"], st)
            check_clean(self, m)
            self.assertEqual(float(m.reals["G"]), 10)
            self.expect(m, ("N", "SCALE N"), "N", 720)
            m = run(p, ["MORE", "SETTINGS", "KEEP"], st, init={"G": 9.81})
            check_clean(self, m)
            self.assertTrue(shows(m, "NOTE:"))            # start-up reminder
            self.assertEqual(float(m.reals["G"]), 9.81)
            m = run(p, ["MORE", "SETTINGS", "9.8"], st, init={"G": 3})
            check_clean(self, m)
            self.assertFalse(shows(m, "NOTE:"))
            self.assertEqual(float(m.reals["G"]), 9.8)
            m = run(p, ["MORE", "SETTINGS", "9.81"], st)
            check_clean(self, m)
            self.assertEqual(float(m.reals["G"]), 9.81)

    def test_angle_mode_restored(self):
        for p, st in self.each():
            for start in ("radian", "degree"):
                m = run(p, ["INCLINE", "FRICTIONLESS", "2", "30"], st,
                        init={"angle": start})
                check_clean(self, m)
                self.expect(m, ("A",), "M/S²", 4.9)       # computed in degrees
                self.assertEqual(m.angle, start)

    def test_back_options_and_long_session(self):
        keys = []
        for menu in ("ELEVATOR", "ATWOOD", "INCLINE"):
            keys += [menu, "BACK"]
        keys += ["MORE", "SIMPLE", "BACK", "MORE", "BACK"]
        for i in range(30):                       # 30 problems in one run
            keys += ["ATWOOD", "FIND A AND T", str(i + 1), "2",
                     "TABLE", "3", "2", "0", "MORE", "CONCEPT", "#1", "#1"]
        for p, st in self.each():
            m = run(p, keys, st)
            check_clean(self, m)
            self.assertLessEqual(m.max_depth, 3)

    def test_more_simple_branches(self):
        for p, st in self.each():
            m = run(p, ["MORE", "SIMPLE", "#3", "2", "1"], st)
            check_clean(self, m)
            self.expect(m, ("T",), "N", 21.6)
            self.assertTrue(shows(m, "T>MG") and shows(m, "ACCEL: UP"))
            m = run(p, ["MORE", "SIMPLE", "SUM", "1", "⁻2", "⁻3", "⁻4.5", "2"], st)
            check_clean(self, m)
            self.expect(m, ("FNET",), "N", -8.5)
            self.expect(m, ("A",), "M/S²", -4.25)
            self.assertTrue(shows(m, "- DIR"))

    def test_blank_entries_either_calculator_behavior(self):
        """ENTER alone at an optional prompt must mean 'skip' whether the OS
        stores an empty string or leaves the string variable unchanged."""
        for p, st in self.each():
            for blank in ("empty", "unchanged"):
                for old in ("7", "", "ABC"):
                    init = {"Str8": old}
                    m = run(p, ["3RD LAW", "1", "2", ""], st, init, blank=blank)
                    check_clean(self, m)
                    self.assertAlmostEqual(value(m, "RATIO")[0], 2)
                    self.assertFalse(shows(m, "F (EACH)") or any(
                        lab == "F" for lab, _, _ in values(m.pauses)))
                    m = run(p, ["TABLE", "5", "1", "0.3", ""], st, init, blank=blank)
                    check_clean(self, m)
                    self.expect(m, ("FSMAX", "FS MAX = MUS*N"), "N", 14.7)
                    m = run(p, ["INCLINE", "AT REST", "5", "30", ""], st, init,
                            blank=blank)
                    check_clean(self, m)
                    self.assertTrue(shows(m, "TANθ"))
                    m = run(p, ["MORE", "SIMPLE", "SUM", "", "", "3", "4.5", "2"],
                            st, init, blank=blank)
                    check_clean(self, m)
                    self.expect(m, ("FNET",), "N", 7.5)
            m = run(p, ["3RD LAW", "1", "2", "0"], st)       # 0 also means skip
            check_clean(self, m)
            self.assertAlmostEqual(value(m, "RATIO")[0], 2)

    def test_review_fixes(self):
        """Branches added after the independent review."""
        for p, st in self.each():
            m = run(p, ["ELEVATOR", "ACCEL FROM", "50", "490", "#1"], st)
            check_clean(self, m)                       # a=0, V known
            self.assertTrue(shows(m, "CONSTANT") and not shows(m, "(OR AT REST)"))
            m = run(p, ["ATWOOD", "#2", "0", "5", "HEAVIER"], st)
            check_clean(self, m)
            self.assertTrue(shows(m, "EQUILIBRIUM") and not shows(m, "HEAVY GOES"))
            m = run(p, ["ELEVATOR", "FIND SCALE", "60", "2", "MOTION", "AT REST"], st)
            check_clean(self, m)
            self.assertTrue(shows(m, "IGNORED"))
            m = run(p, ["TABLE", "5", "1", "0.1", "0.3"], st)
            check_clean(self, m)
            self.assertTrue(shows(m, "HANG: MG-T=0") and shows(m, "TABLE: T-FS=0"))
            m = run(p, ["INCLINE", "AT REST", "5", "30", "0.5"], st)
            check_clean(self, m)
            self.assertTrue(shows(m, "SLIDING"))
            # long labels with 4-digit values keep their unit (mono rounds)
            for keys in (["INCLINE", "AT REST", "301.75", "33.3", "0.9"],
                         ["INCLINE", "SLIDING", "301.75", "33.3", "0.1"],
                         ["INCLINE", "FRICTIONLESS", "301.75", "33.3"],
                         ["INCLINE", "MIN MUS", "301.75", "33.3"],
                         ["ATWOOD", "#2", "1.5", "1234.567", "HEAVIER"],
                         ["ATWOOD", "#2", "1.5", "1234.567", "LIGHTER"],
                         ["TABLE", "999.99", "100.07", "0.5", "0.6"]):
                m = run(p, keys, st)
                check_clean(self, m)
                for label, v, unit in values(m.pauses):
                    if label in ("MGSINθ", "MGCOSθ", "FSMAX", "OTHER", "HEAVY", "LIGHT"):
                        self.assertTrue(unit in ("N", "KG"), (label, v, unit, m.pauses))

    def test_numeric_blank_keeps_old_value(self):
        """If a blank ENTER at a numeric Input leaves the variable unchanged,
        every validated prompt asks again instead of using a stale value."""
        for p, st in self.each():
            m = run(p, ["ATWOOD", "FIND A AND T", "", "6", "", "4"], st,
                    init={"P": 99, "Q": 99}, blank="unchanged")
            check_clean(self, m)
            self.expect(m, ("A",), "M/S²", 1.96)
            m = run(p, ["MORE", "SIMPLE", "#3", "2", ""], st, init={"Y": 50},
                    blank="unchanged")
            check_clean(self, m)
            self.expect(m, ("T",), "N", 19.6)          # AY blank means 0

    def test_every_validation_message(self):
        """Answer every numeric prompt wrongly once; the program must
        re-ask (never crash, never accept) and then finish normally."""
        bad = {"θ (DEG)=": "200"}               # flat pull accepts negatives
        good = {"θ": "30", "MUS=": "0.5", "MUK": "0.2", "SCALE": "100"}
        paths = [["ELEVATOR", "FIND SCALE", "#1"], ["ELEVATOR", "ACCEL FROM", "#1"],
                 ["ELEVATOR", "FIND MASS"], ["ATWOOD", "#1"],
                 ["ATWOOD", "#2", "#1"], ["TABLE"], ["FLAT", "#1"], ["FLAT", "#2"],
                 ["INCLINE", "#1"], ["INCLINE", "#2"], ["INCLINE", "#5"],
                 ["INCLINE", "#6"], ["3RD LAW"],
                 ["MORE", "SIMPLE", "#1"], ["MORE", "SIMPLE", "#2"],
                 ["MORE", "SIMPLE", "#3"], ["MORE", "SIMPLE", "#4"]]
        for p, st in self.each():
            for path in paths:
                menus = calc_keys(p, path) + ["MORE", "QUIT"]
                seen = set()

                def answer(kind, info):
                    if kind == "menu":
                        return menus.pop(0) if menus else None
                    if info not in seen:
                        seen.add(info)
                        return bad.get(info, "⁻1")
                    return next((v for k, v in good.items() if k in info), "2")

                m = Machine(SRC[p], p, answer, init={"G": 9.8}, style=st).run()
                COVER[p] |= m.hit
                check_clean(self, m)
                self.assertTrue(m.pauses, path)
                asked = collections.Counter(pr for pr, _ in m.inputs)
                for prompt in seen:
                    if not any(k in prompt for k in OPEN_PROMPTS):
                        self.assertGreaterEqual(asked[prompt], 2,
                                                f"{prompt!r} accepted a bad value")

    def test_only_allowed_variables(self):
        allowed = set("ABCDEFGHIJKLMNOPQRSTUVWXYZθ") | {f"Str{i}" for i in range(1, 10)}
        for p, st in self.each():
            m = run(p, ["ATWOOD", "FIND A AND T", "6", "4"], st)
            self.assertLessEqual(m.written, allowed)


# --------------------------------------------------------------- fuzzing
class Fuzz(Base):
    """Random inputs on every solver vs reference.py.  Strict: EVERY answer
    row on every screen must be one the test expects, with the right value
    and unit (so no displayed number goes unchecked)."""

    N = 60

    def rnd(self, rng, lo, hi, nd=2):
        return round(rng.uniform(lo, hi), nd)

    def mass(self, rng):
        # mostly classroom sizes, sometimes cars/elevators (4-digit forces)
        return self.rnd(rng, 0.5, 120) if rng.random() < 0.8 else self.rnd(rng, 300, 2500)

    def compare(self, m, rows):
        """rows: list of (labels, unit, value).  Every value row on screen
        must match one of them; every one of them must appear."""
        check_clean(self, m)
        used = set()
        for label, v, unit in values(m.pauses):
            hit = [i for i, (labels, _, _) in enumerate(rows) if label in labels]
            self.assertTrue(hit, f"unexpected answer row {label}={v} on {m.profile}: "
                                 f"{m.pauses}")
            labels, want_unit, want = rows[hit[0]]
            self.assertEqual(unit, want_unit, f"unit of {label}")
            self.assertAlmostEqual(v, want, delta=self.tol(m, label, unit, want),
                                   msg=f"{label} on {m.profile}/{m.style}: {m.pauses}")
            used.update(hit)
        missing = [rows[i][0] for i in range(len(rows)) if i not in used]
        self.assertEqual(missing, [], f"rows not shown on {m.profile}: {m.pauses}")

    def test_fuzz(self):
        rng = random.Random(84)
        AY, MG = ("AY", "ACCEL AY"), ("MG", "TRUE WEIGHT MG")
        for p, st in self.each():
            for _ in range(self.N):
                mass = self.mass(rng)
                a = self.rnd(rng, 0, 9)
                d = rng.choice(["UP", "DOWN"])
                r = ref.elevator_scale(mass, a, direction=d)
                m = run(p, ["ELEVATOR", "FIND SCALE", num(mass), num(a),
                            "#1" if d == "UP" else "#2"], st)
                self.compare(m, [(AY, "M/S²", r["ay"]), (("N", "SCALE N"), "N", r["N"]),
                                 (MG, "N", r["mg"])])
                n = self.rnd(rng, 0, 1500, 1)
                r = ref.elevator_accel(mass, n)
                m = run(p, ["ELEVATOR", "ACCEL FROM", num(mass), num(n), "#3"], st)
                self.compare(m, [(AY, "M/S²", r["ay"]), (MG, "N", r["mg"])])
                ay = self.rnd(rng, -9, 9)
                r = ref.elevator_mass(n + 1, ay)
                m = run(p, ["ELEVATOR", "FIND MASS", num(n + 1), num(ay)], st)
                self.compare(m, [(("M", "MASS M"), "KG", r["m"]), (MG, "N", r["mg"])])

                m1, m2 = self.rnd(rng, 0.1, 50), self.rnd(rng, 0.1, 50)
                if m1 != m2:
                    r = ref.atwood(m1, m2)
                    m = run(p, ["ATWOOD", "FIND A AND T", num(m1), num(m2)], st)
                    self.compare(m, [(("A",), "M/S²", r["a"]), (("T",), "N", r["T"]),
                                     (("M1G",), "N", m1 * 9.8), (("M2G",), "N", m2 * 9.8)])
                    self.assertTrue(shows(m, "CHECK OK"))
                acc, known = self.rnd(rng, 0, 9.7), self.mass(rng)
                heavy = rng.random() < 0.5
                r = ref.atwood_other_mass(acc, known, heavy)
                m = run(p, ["ATWOOD", "#2", num(acc), num(known),
                            "HEAVIER" if heavy else "LIGHTER"], st)
                self.compare(m, [(("OTHER", "OTHER MASS"), "KG", r["other"]),
                                 (("T",), "N", r["T"]),
                                 (("HEAVY", "HEAVY MASS"), "KG", r["heavy"]),
                                 (("LIGHT", "LIGHT MASS"), "KG", r["light"])])

                big, small = self.mass(rng), self.mass(rng)
                muk = rng.choice([0, self.rnd(rng, 0, 0.8)])
                r = ref.table_hanger(big, small, muk)
                keys = ["TABLE", num(big), num(small), num(muk)] + ([""] if muk else [])
                m = run(p, keys, st)
                if r["moves"]:
                    self.compare(m, [(("A",), "M/S²", r["a"]), (("T",), "N", r["T"]),
                                     (("N", "N ON TABLE"), "N", r["N"]),
                                     (("FK", "FK (KINETIC)"), "N", r["fk"])])
                else:
                    self.compare(m, [(("A",), "M/S²", 0), (("T",), "N", r["T"]),
                                     (("FS", "FS (STATIC)"), "N", r["fs"]),
                                     (("FSMAX", "FS MAX = MUS*N"), "N", r["fs_max"])])

                F, th = self.rnd(rng, 0, 200), self.rnd(rng, -60, 60, 1)
                mode = rng.choice(["FRICTION", "MUK", "CONSTANT", "ACCEL"])
                val = {"FRICTION": self.rnd(rng, 0, 30), "MUK": self.rnd(rng, 0, 0.9),
                       "CONSTANT": None, "ACCEL": self.rnd(rng, -3, 6)}[mode]
                r = ref.flat_pull(mass, F, th, mode, val)
                keys = ["FLAT", num(mass), num(F), num(th), mode]
                keys += [] if val is None else [num(val)]
                m = run(p, keys, st)
                if r["lifts_off"]:
                    self.compare(m, [(("FY",), "N", r["Fy"]), (("MG",), "N", r["mg"])])
                    self.assertTrue(shows(m, "LIFTS OFF"))
                else:
                    rows = [(("N",), "N", r["N"]), (("AX",), "M/S²", r["ax"]),
                            (("FX",), "N", r["Fx"]), (("FY",), "N", r["Fy"]),
                            (("FRIC",), "N", r["f"])]
                    if "mu_needed" in r:
                        rows.append((("MU", "MU NEEDED"), "", r["mu_needed"]))
                    self.compare(m, rows)

                th = self.rnd(rng, 0.1, 89, 1)
                k = rng.choice([0, self.rnd(rng, 0.01, 1)])
                parts = [(("MGSINθ",), "N", mass * 9.8 * math.sin(math.radians(th))),
                         (("MGCOSθ",), "N", mass * 9.8 * math.cos(math.radians(th)))]
                r = ref.incline_slide(mass, th, k)
                m = run(p, ["INCLINE", "SLIDING", num(mass), num(th), num(k)], st)
                self.compare(m, parts + [(("A",), "M/S²", r["a"]), (("N",), "N", r["N"]),
                                         (("FK",), "N", r["fk"])])
                r = ref.incline_rest(mass, th, k or None)
                m = run(p, ["INCLINE", "AT REST", num(mass), num(th), num(k)], st)
                rows = parts + [(("N",), "N", r["N"]), (("FS", "FS NEEDED"), "N", r["fs"]),
                                (("MIN MUS", "MIN MUS = TANθ"), "", r["mus_min"])]
                if k:
                    rows.append((("MUS*N", "FS MAX = MUS*N"), "N", r["fs_max"]))
                    self.assertTrue(shows(m, r["verdict"].split(":")[0] + ":"))
                self.compare(m, rows)
                r = ref.incline_frictionless(mass, th)
                m = run(p, ["INCLINE", "FRICTIONLESS", num(mass), num(th)], st)
                self.compare(m, parts + [(("A",), "M/S²", r["a"]), (("N",), "N", r["N"])])
                F2 = self.rnd(rng, 0, 3) * mass * 9.8
                r = ref.incline_push(mass, th, F2, k)
                m = run(p, ["INCLINE", "PUSHED", num(mass), num(th), num(F2), num(k)], st)
                self.compare(m, parts + [(("A",), "M/S²", r["a"]), (("N",), "N", r["N"]),
                                         (("FK",), "N", r["fk"]),
                                         (("F NEED", "F NEEDED"), "N", r["F_const"])])
                hang = self.mass(rng)
                ks = rng.choice([0, self.rnd(rng, 0.01, 0.6)])
                us = rng.choice([0, round(ks + self.rnd(rng, 0, 0.4), 2)]) if ks else 0
                r = ref.incline_hanger(mass, hang, th, ks, us or None)
                keys = ["INCLINE", "HANGER", num(mass), num(th), num(hang), num(ks)]
                keys += [num(us)] if ks else []
                m = run(p, keys, st)
                if r["moves"]:
                    self.compare(m, parts + [(("A",), "M/S²", r["a"]), (("T",), "N", r["T"]),
                                             (("N",), "N", r["N"]), (("FK",), "N", r["fk"])])
                    self.assertTrue(shows(m, "BLOCK MOVES " + r["block"]))
                else:
                    self.compare(m, parts + [(("A",), "M/S²", 0), (("T",), "N", r["T"]),
                                             (("FS",), "N", r["fs"]),
                                             (("FSMAX", "FS MAX = MUS*N"), "N", r["fs_max"])])
                r = ref.incline_min_mus(mass, th)
                m = run(p, ["INCLINE", "MIN MUS", num(mass), num(th)], st)
                self.compare(m, parts + [(("MIN MUS",), "", r["mus_min"])])

                ma, mb = self.rnd(rng, 0.1, 9), self.rnd(rng, 0.1, 9)
                f = rng.choice([0, self.rnd(rng, 0.1, 99)])
                r = ref.third_law(ma, mb, f or None)
                m = run(p, ["3RD LAW", num(ma), num(mb), num(f)], st)
                rows = [(("RATIO",), "", r["ratio"])]
                if f:
                    rows += [(("F", "F (EACH)"), "N", r["F"]),
                             (("AA", "AA=-F/MA"), "M/S²", r["aA"]),
                             (("AB", "AB=F/MB"), "M/S²", r["aB"])]
                self.compare(m, rows)

                ay = self.rnd(rng, -9.7, 9)
                r = ref.hanging_accel(mass, ay)
                m = run(p, ["MORE", "SIMPLE", "#3", num(mass), num(ay)], st)
                self.compare(m, [(("T",), "N", r["T"]), (("MG",), "N", r["mg"]),
                                 (("AY",), "M/S²", ay)])
                forces = [self.rnd(rng, -50, 50) for _ in range(rng.randint(1, 4))]
                r = ref.net_force(forces, mass)
                keys = [num(x) for x in forces] + [""] * (4 - len(forces))
                m = run(p, ["MORE", "SIMPLE", "SUM"] + keys + [num(mass)], st)
                self.compare(m, [(("FNET",), "N", r["Fnet"]), (("A",), "M/S²", r["a"])])
                m = run(p, ["MORE", "SIMPLE", "#1", num(mass)], st)
                self.compare(m, [(("T",), "N", mass * 9.8)])
                m = run(p, ["MORE", "SIMPLE", "#2", num(mass)], st)
                self.compare(m, [(("FAIR",), "N", mass * 9.8), (("A",), "M/S²", 0)])


class FuzzCE(Fuzz):
    """Random problems for the CE-only solvers, every row checked."""

    def test_fuzz(self):
        rng = random.Random(1984)
        p, st = "ce", "mathprint"
        names = {"VVT": "V0, V, T", "VVD": "V0, V, D", "VAT": "V0, A, T",
                 "VAD": "V0, A, D", "VTD": "V0, T, D", "VVA": "V0, V, A"}
        motions = {"HORIZONTAL": "HORIZONTAL", "UP": "VERTICAL, MOVING UP",
                   "DOWN": "VERTICAL, MOVING DOWN"}
        done = 0
        while done < 120:
            known = rng.choice(list(names))
            kmh = rng.random() < 0.3
            unit = ref.KMH if kmh else 1
            v0, v = self.rnd(rng, 0, 40), self.rnd(rng, 0, 40)
            a, t, d = self.rnd(rng, -6, 6), self.rnd(rng, 0.2, 20), self.rnd(rng, 1, 200)
            ins = {"VVT": [v0, v, t], "VVD": [v0, v, d], "VAT": [v0, a, t],
                   "VAD": [v0, a, d], "VTD": [v0, t, d], "VVA": [v0, v, a]}[known]
            kw = {"VVT": dict(v=v * unit, t=t), "VVD": dict(v=v * unit, d=d),
                  "VAT": dict(a=a, t=t), "VAD": dict(a=a, d=d), "VTD": dict(t=t, d=d),
                  "VVA": dict(v=v * unit, a=a)}[known]
            try:
                r = ref.kinematics(known, v0 * unit, **kw)
            except ref.Impossible:
                continue
            done += 1
            mass = rng.choice([0, self.mass(rng)])
            motion = rng.choice(list(motions))
            m = run(p, MOTION + [motions[motion], "KM/H" if kmh else "#1", names[known]]
                    + [num(x) for x in ins] + [num(mass) if mass else ""], st)
            rows = [(("V0",), "M/S", r["v0"]), (("V",), "M/S", r["v"]),
                    (("A",), "M/S²", r["a"]), (("T",), "S", r["t"]), (("D",), "M", r["d"])]
            if mass:
                f = ref.motion_force(mass, r["a"], motion)
                rows += [(("FNET",), "N", f["Fnet"])]
                if motion == "HORIZONTAL":
                    rows += [(("M",), "KG", mass)]
                else:
                    rows += [(("F UP",), "N", f["F_up"]), (("MG",), "N", f["mg"])]
            self.compare(m, rows)

            mass, th = self.mass(rng), self.rnd(rng, -60, 60, 1)
            acc = self.rnd(rng, 0, 5)
            mode = rng.choice(["NONE", "FORCE", "MUK"])
            val = {"NONE": 0, "FORCE": self.rnd(rng, 0, 40), "MUK": self.rnd(rng, 0, 0.8)}[mode]
            try:
                r = ref.pull_force(mass, th, acc, mode, val)
            except ref.Impossible:
                r = None
            keys = ["FLAT>F", num(mass), num(th), num(acc),
                    {"NONE": "NONE", "FORCE": "FRICTION FORCE", "MUK": "MUK"}[mode]]
            keys += [] if mode == "NONE" else [num(val)]
            m = run(p, keys, st)
            if r is None:
                check_clean(self, m)
                self.assertTrue(shows(m, "CANNOT") or shows(m, "NOT POSSIBLE")
                                or shows(m, "LIFTS OFF"))
            else:
                self.compare(m, [(("F",), "N", r["F"]), (("FX",), "N", r["Fx"]),
                                 (("FY",), "N", r["Fy"]), (("N",), "N", r["N"]),
                                 (("FRIC",), "N", r["f"]), (("AX",), "M/S²", acc)])

            tmax, acc = self.rnd(rng, 1, 3000), self.rnd(rng, -9, 9)
            r = ref.rope_max_lift(mass, tmax)
            m = run(p, ["MORE", "ROPE", "MAX A, LIFTING", num(mass), num(tmax)], st)
            self.compare(m, [(("AMAX UP",), "M/S²", r["a_max"]), (("MG",), "N", r["mg"]),
                             (("TMAX",), "N", tmax)])
            r = ref.rope_hold(mass, tmax, acc)
            m = run(p, ["MORE", "ROPE", "WILL IT HOLD", num(mass), num(tmax), num(acc)], st)
            self.compare(m, [(("T NEEDED",), "N", r["T"]), (("TMAX",), "N", tmax),
                             (("AMAX UP",), "M/S²", r["a_max"])])
            self.assertTrue(shows(m, "HOLDS:" if r["holds"] else "BREAKS:"))
            opp = rng.choice([0, self.rnd(rng, 0, 500)])
            r = ref.tow_max(mass, tmax, opp)
            m = run(p, ["MORE", "ROPE", "TOWING", num(mass), num(tmax), num(opp) if opp else ""], st)
            self.compare(m, [(("AMAX",), "M/S²", r["a_max"]), (("TMAX",), "N", tmax),
                             (("F OPP",), "N", opp)])
            m1, m2 = self.mass(rng), self.mass(rng)
            r = ref.force_ratio(m1, m2, acc or None)
            m = run(p, ["MORE", "SIMPLE", "SAME A", num(m1), num(m2), num(acc)], st)
            rows = [(("F1/F2",), "", r["ratio"])]
            if acc:
                rows += [(("A",), "M/S²", acc), (("F1",), "N", r["F1"]), (("F2",), "N", r["F2"])]
            self.compare(m, rows)


# -------------------------------------------------------------- coverage
class ZCoverage(unittest.TestCase):
    """Runs last: every line of both programs was executed by some test."""

    def test_every_line_executed(self):
        for p, src in SRC.items():
            lines = src.split("\n")
            missed = [f"{i + 1}: {lines[i]}" for i in range(len(lines))
                      if i not in COVER[p]]
            self.assertEqual(missed, [], f"{p}: lines never executed")


if __name__ == "__main__":
    unittest.main(verbosity=2)
