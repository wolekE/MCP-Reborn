#!/usr/bin/env python3
"""Trace tests: run the real FORCES.8xp files in the TI-BASIC simulator.

    python3 tools/test_program.py        (after python3 tools/build.py)

Every test runs both builds (TI-84 Plus mono with both number display
styles, and TI-84 Plus CE), checks the answers on screen against
reference.py, and fails on any simulator violation: memory leak, text
scrolled/cleared/hidden before it was seen, text past the screen edge,
pause indicator overlap, or a calculator error.  The run ends with a line
coverage report: every line of both programs must execute at least once.
"""

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


def run(profile, keys, style="classic", init=None, quit=True, blank="empty"):
    state = {"G": 9.8}
    state.update(init or {})
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

    def expect(self, m, labels, unit, want, tol=TOL):
        got, u = value(m, *labels)
        self.assertAlmostEqual(got, want, delta=tol,
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
            self.both(m, ("FS",), "N", 24.5, r["fs"])
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
            self.assertTrue(shows(m, "HANGER: DOWN") and shows(m, "PULLEY"))

    def test_05_atwood_6_4(self):
        r = ref.atwood(6, 4)
        for p, st in self.each():
            m = run(p, ["ATWOOD", "FIND A AND T", "6", "4"], st)
            check_clean(self, m)
            self.both(m, ("A",), "M/S²", 1.96, r["a"])
            self.both(m, ("T",), "N", 47.04, r["T"])
            self.assertTrue(shows(m, "M2G<T<M1G: OK"))
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
            self.expect(m, ("FS MAX", "FS MAX = MUS*N"), "N", 14.7)

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
            self.assertTrue(shows(m, "NOT") and shows(m, "POSSIBLE"))
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
            m = run(p, ["INCLINE", "AT REST", "5", "95", "90", "0", ""], st)
            check_clean(self, m)
            self.assertEqual(sum(1 for pr, _ in m.inputs if "θ" in pr), 3)
            self.expect(m, ("FS",), "N", 0)

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
                    self.expect(m, ("FS MAX", "FS MAX = MUS*N"), "N", 14.7)
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

    def test_every_validation_message(self):
        """Answer every numeric prompt wrongly once; the program must
        re-ask (never crash, never accept) and then finish normally."""
        bad = {"θ (DEG)=": "200"}               # flat pull accepts negatives
        good = {"θ": "30", "MUS=": "0.5", "MUK": "0.2", "SCALE": "100"}
        paths = [["ELEVATOR", "FIND SCALE", "#1"], ["ELEVATOR", "ACCEL FROM", "#1"],
                 ["ELEVATOR", "FIND MASS"], ["ATWOOD", "#1"],
                 ["ATWOOD", "#2", "#1"], ["TABLE"], ["FLAT", "#1"], ["FLAT", "#2"],
                 ["INCLINE", "#1"], ["INCLINE", "#2"], ["3RD LAW"],
                 ["MORE", "SIMPLE", "#1"], ["MORE", "SIMPLE", "#2"],
                 ["MORE", "SIMPLE", "#3"], ["MORE", "SIMPLE", "#4"]]
        for p, st in self.each():
            for path in paths:
                menus = path + ["MORE", "QUIT"]
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

    def test_only_allowed_variables(self):
        allowed = set("ABCDEFGHIJKLMNOPQRSTUVWXYZθ") | {f"Str{i}" for i in range(1, 10)}
        for p, st in self.each():
            m = run(p, ["ATWOOD", "FIND A AND T", "6", "4"], st)
            self.assertLessEqual(m.written, allowed)


# --------------------------------------------------------------- fuzzing
class Fuzz(Base):
    """Random inputs on every numeric solver vs reference.py."""

    N = 40

    def rnd(self, rng, lo, hi, nd=2):
        return round(rng.uniform(lo, hi), nd)

    def compare(self, m, pairs):
        check_clean(self, m)
        for labels, unit, want in pairs:
            self.expect(m, labels, unit, want, ROUND_TOL + abs(want) * 1e-9)

    def test_fuzz(self):
        rng = random.Random(84)
        for p, st in self.each():
            for _ in range(self.N):
                mass = self.rnd(rng, 0.5, 120)
                a = self.rnd(rng, 0, 9)
                d = rng.choice(["UP", "DOWN"])
                r = ref.elevator_scale(mass, a, direction=d)
                if not r["lifts_off"]:
                    m = run(p, ["ELEVATOR", "FIND SCALE", num(mass), num(a),
                                "#1" if d == "UP" else "#2"], st)
                    self.compare(m, [(("N", "SCALE N"), "N", r["N"]),
                                     (("AY", "ACCEL AY"), "M/S²", r["ay"])])
                n = self.rnd(rng, 0, 1500, 1)
                r = ref.elevator_accel(mass, n)
                m = run(p, ["ELEVATOR", "ACCEL FROM", num(mass), num(n), "#3"], st)
                self.compare(m, [(("AY", "ACCEL AY"), "M/S²", r["ay"]),
                                 (("MG", "TRUE WEIGHT MG"), "N", r["mg"])])
                m1, m2 = self.rnd(rng, 0.1, 50), self.rnd(rng, 0.1, 50)
                if m1 != m2:
                    r = ref.atwood(m1, m2)
                    m = run(p, ["ATWOOD", "FIND A AND T", num(m1), num(m2)], st)
                    self.compare(m, [(("A",), "M/S²", r["a"]), (("T",), "N", r["T"]),
                                     (("M1G",), "N", m1 * 9.8), (("M2G",), "N", m2 * 9.8)])
                    self.assertTrue(shows(m, ": OK"))
                big, small = self.rnd(rng, 0.5, 40), self.rnd(rng, 0.5, 40)
                muk = rng.choice([0, self.rnd(rng, 0, 0.8)])
                r = ref.table_hanger(big, small, muk)
                keys = ["TABLE", num(big), num(small), num(muk)] + ([""] if muk else [])
                m = run(p, keys, st)
                if r["moves"]:
                    self.compare(m, [(("A",), "M/S²", r["a"]), (("T",), "N", r["T"])])
                else:
                    self.compare(m, [(("FS", "FS (STATIC)"), "N", r["fs"])])
                F, th = self.rnd(rng, 0, 200), self.rnd(rng, -60, 60, 1)
                fr = self.rnd(rng, 0, 30)
                r = ref.flat_pull(mass, F, th, "FRICTION", fr)
                m = run(p, ["FLAT", num(mass), num(F), num(th), "FRICTION",
                            num(fr)], st)
                if r["lifts_off"]:
                    check_clean(self, m)
                    self.assertTrue(shows(m, "LIFTS OFF"))
                else:
                    self.compare(m, [(("N",), "N", r["N"]), (("AX",), "M/S²", r["ax"]),
                                     (("FX",), "N", r["Fx"]), (("FY",), "N", r["Fy"])])
                th = self.rnd(rng, 0, 89, 1)
                k = self.rnd(rng, 0, 1)
                r = ref.incline_slide(mass, th, k)
                m = run(p, ["INCLINE", "SLIDING", num(mass), num(th), num(k)], st)
                self.compare(m, [(("A",), "M/S²", r["a"]),
                                 (("MGSINθ",), "N", r["mg_sin"]),
                                 (("MGCOSθ",), "N", r["mg_cos"])])
                r = ref.incline_rest(mass, th, k)
                m = run(p, ["INCLINE", "AT REST", num(mass), num(th), num(k)], st)
                self.compare(m, [(("FS",), "N", r["fs"]), (("N",), "N", r["N"])])
                self.assertTrue(shows(m, r["verdict"].split(":")[0] + ":"))
                ma, mb, f = self.rnd(rng, 0.1, 9), self.rnd(rng, 0.1, 9), self.rnd(rng, 0, 99)
                r = ref.third_law(ma, mb, f)
                m = run(p, ["3RD LAW", num(ma), num(mb), num(f)], st)
                self.compare(m, [(("AA", "AA=-F/MA"), "M/S²", r["aA"]),
                                 (("AB", "AB=F/MB"), "M/S²", r["aB"]),
                                 (("RATIO",), "", r["ratio"])])


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
