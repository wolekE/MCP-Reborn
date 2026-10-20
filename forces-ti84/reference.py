#!/usr/bin/env python3
"""Reference (Python) version of every solver in the FORCES TI-BASIC program.

The math, sign conventions, validation rules and the words shown on screen
match the calculator program line for line, so this file doubles as a
readable spec and as the oracle the TI-BASIC simulator tests compare against.

    python3 reference.py          # run the test suite (required + extra cases)
    python3 reference.py -v       # verbose test output

All angles are in degrees.  Every function takes g (default 9.8 m/s^2).
"""

import math
import sys
import unittest

G = 9.8


class Impossible(ValueError):
    """Raised for setups the calculator rejects with a message."""


def _sin(deg):
    return math.sin(math.radians(deg))


def _cos(deg):
    return math.cos(math.radians(deg))


def _tan(deg):
    return math.tan(math.radians(deg))


def _sign(x):
    return (x > 0) - (x < 0)


def _clean(x):
    """Round away binary-float noise (the TI uses 14-digit decimal math,
    so e.g. (490 - 50*9.8)/50 is exactly 0 there)."""
    return round(x, 10) + 0.0


def _require(cond, msg):
    if not cond:
        raise Impossible(msg)


def accel_word(a, pos="UP", neg="DOWN"):
    """'ACCEL: UP' / 'ACCEL: DOWN' / 'ACCEL: NONE' as shown on screen."""
    if a > 0:
        return "ACCEL: " + pos
    if a < 0:
        return "ACCEL: " + neg
    return "ACCEL: NONE"


# ---------------------------------------------------------------- 1 ELEVATOR
def accel_from_motion(a_size, moving, change):
    """Signed a_y (up +) from the motion description.

    moving: 'UP', 'DOWN' or 'REST';  change: 'SPEEDING', 'SLOWING', 'CONSTANT'.
    Speeding up -> a along v; slowing down -> a opposite v;
    at rest or constant velocity -> a = 0.
    """
    if moving == "REST" or change == "CONSTANT":
        return 0.0
    v = 1 if moving == "UP" else -1
    return a_size * v if change == "SPEEDING" else -a_size * v


def elevator_scale(m, a_size, direction=None, moving=None, change=None, g=G):
    """1A FIND SCALE N.  N = m(g + a_y)."""
    _require(m > 0, "MUST BE >0")
    _require(a_size >= 0, "MUST BE >=0")
    if direction is not None:
        ay = {"UP": a_size, "DOWN": -a_size, "ZERO": 0.0}[direction]
    else:
        ay = accel_from_motion(a_size, moving, change)
    n = _clean(m * (g + ay))
    if ay > 0:
        feel = "HEAVIER (N>MG)"
    elif ay < 0:
        feel = "LIGHTER (N<MG)"
    else:
        feel = "NORMAL (N=MG)"
    if n == 0:
        feel = "WEIGHTLESS (N=0)"
    return {"ay": ay, "N": n, "mg": m * g, "accel": accel_word(ay),
            "feel": feel, "lifts_off": n < 0}


def elevator_accel(m, n, velocity="UNKNOWN", g=G):
    """1B FIND ACCEL FROM SCALE.  a_y = (N - mg)/m, then speeding/slowing."""
    _require(m > 0, "MUST BE >0")
    _require(n >= 0, "MUST BE >=0")
    ay = _clean((n - m * g) / m)
    s = _sign(ay)
    v = {"UP": 1, "DOWN": -1, "UNKNOWN": 0}[velocity]
    if s == 0:
        motion = ["CONSTANT V (OR AT REST)"]
    elif v == 0:
        motion = (["UP+SPEEDING", "DOWN+SLOWING"] if s > 0
                  else ["DOWN+SPEEDING", "UP+SLOWING"])
    elif s == v:
        motion = ["SPEEDING UP"]
    else:
        motion = ["SLOWING DOWN"]
    return {"ay": ay, "mg": m * g, "accel": accel_word(ay), "motion": motion}


def elevator_free_fall(g=G):
    """1C FREE FALL."""
    return {"N": 0.0, "ay": -g, "accel": "ACCEL: DOWN", "feel": "WEIGHTLESS"}


def elevator_mass(n, ay, g=G):
    """1D FIND MASS.  m = N/(g + a_y)."""
    _require(n > 0, "MUST BE >0")
    _require(g + ay > 0, "IMPOSSIBLE: N>0 NEEDS AY>-G")
    m = n / (g + ay)
    return {"m": m, "mg": m * g, "accel": accel_word(ay)}


# ------------------------------------------------------------------ 2 ATWOOD
def atwood(m1, m2, g=G):
    """2A two hanging masses.  + = heavy side down / light side up."""
    _require(m1 > 0 and m2 > 0, "MUST BE >0")
    heavy, light = max(m1, m2), min(m1, m2)
    a = (heavy - light) * g / (heavy + light)
    t = light * (g + a)
    out = {"a": a, "T": t, "light_wt": light * g, "heavy_wt": heavy * g,
           "equilibrium": m1 == m2}
    if m1 != m2:
        hn, ln = ("M1", "M2") if m1 > m2 else ("M2", "M1")
        out.update(heavy_name=hn, light_name=ln,
                   down=hn + " (HEAVY): DOWN", up=ln + " (LIGHT): UP",
                   eq_heavy=hn + "G-T=" + hn + "A",
                   eq_light="T-" + ln + "G=" + ln + "A",
                   check_ok=light * g < t < heavy * g)
    return out


def atwood_other_mass(a, known, known_is_heavy, g=G):
    """2B given a and one mass, find the other (a = (M-m)g/(M+m))."""
    _require(a >= 0, "MUST BE >=0")
    _require(known > 0, "MUST BE >0")
    _require(a < g, "IMPOSSIBLE: ATWOOD NEEDS A<G")
    if known_is_heavy:
        heavy, light = known, known * (g - a) / (g + a)
        other = light
    else:
        light, heavy = known, known * (g + a) / (g - a)
        other = heavy
    return {"other": other, "heavy": heavy, "light": light,
            "T": light * (g + a)}


# ------------------------------------------------------- 3 TABLE + HANGER
def table_hanger(M, m, muk=0.0, mus=None, g=G):
    """3 table mass M pulled horizontally by a rope to hanging mass m.

    + = toward the pulley (table) / down (hanger).  If mus is None the
    static check uses muk.  Static friction must satisfy mus >= muk.
    """
    _require(M > 0 and m > 0, "MUST BE >0")
    _require(muk >= 0, "MUST BE >=0")
    if mus is None:
        mus = muk
    _require(mus >= muk, "NEED MUS>=MUK")
    n = M * g
    moves = muk == 0 or m * g > mus * M * g
    if moves:
        a = _clean((m * g - muk * M * g) / (M + m))
        t = m * (g - a)
        return {"moves": True, "a": a, "T": t, "N": n, "fk": muk * n}
    return {"moves": False, "a": 0.0, "T": m * g, "N": n, "fs": m * g,
            "fs_max": mus * n}


# ------------------------------------------------------ 4 FLAT SURFACE PULL
def flat_pull(m, F, theta, mode, value=None, g=G):
    """4 pull F at theta above horizontal on a level floor (a_y = 0).

    mode: 'FRICTION' (value = friction force), 'MUK' (value = muk),
          'CONSTANT' (constant velocity), 'ACCEL' (value = a_x).
    """
    _require(m > 0, "MUST BE >0")
    _require(F >= 0, "MUST BE >=0")
    _require(-90 <= theta <= 90, "USE -90 TO 90")
    fx, fy = F * _cos(theta), F * _sin(theta)
    n = _clean(m * g - fy)
    out = {"Fx": fx, "Fy": fy, "N": n, "mg": m * g, "lifts_off": n < 0}
    if n < 0:
        return out
    if mode == "FRICTION":
        _require(value >= 0, "MUST BE >=0")
        f = value
        a = _clean((fx - f) / m)
    elif mode == "MUK":
        _require(value >= 0, "MUST BE >=0")
        f = value * n
        a = _clean((fx - f) / m)
    elif mode == "CONSTANT":
        a = 0.0
        f = fx - m * a
    elif mode == "ACCEL":
        a = value
        f = _clean(fx - m * a)
    else:
        raise ValueError(mode)
    out.update(f=f, ax=a, accel=accel_word(a, "RIGHT", "LEFT"),
               friction_impossible=mode == "ACCEL" and f < 0,
               stays_put_if_at_rest=mode in ("FRICTION", "MUK") and a < 0)
    if mode == "CONSTANT" and n > 0:
        out["mu_needed"] = f / n
    return out


# ---------------------------------------------------------------- 5 INCLINE
def _incline_parts(m, theta, g):
    _require(m > 0, "MUST BE >0")
    _require(0 <= theta < 90, "USE 0<=THETA<90")
    return m * g * _sin(theta), m * g * _cos(theta)


def incline_rest(m, theta, mus=None, g=G):
    """5A at rest: N = mg cos, fs = mg sin (uphill); optional mus check."""
    down, into = _incline_parts(m, theta, g)
    out = {"mg_sin": down, "mg_cos": into, "N": into, "fs": down,
           "mus_min": _tan(theta)}
    if mus is not None:
        _require(mus >= 0, "MUST BE >=0")
        out["fs_max"] = mus * into
        out["holds"] = down <= mus * into
        out["verdict"] = "YES: STAYS PUT" if out["holds"] else "NO: WILL SLIDE"
    return out


def incline_slide(m, theta, muk, g=G):
    """5B sliding down with muk: a = g(sin - muk cos), + = downhill."""
    down, into = _incline_parts(m, theta, g)
    _require(muk >= 0, "MUST BE >=0")
    a = _clean(g * (_sin(theta) - muk * _cos(theta)))
    return {"mg_sin": down, "mg_cos": into, "N": into, "fk": muk * into,
            "a": a, "slowing": a < 0}


def incline_frictionless(m, theta, g=G):
    """5C frictionless: a = g sin, downhill."""
    down, into = _incline_parts(m, theta, g)
    return {"mg_sin": down, "mg_cos": into, "N": into, "a": g * _sin(theta)}


def incline_min_mus(m, theta, g=G):
    """5D minimum mus to hold at rest: tan(theta) (mass cancels)."""
    down, into = _incline_parts(m, theta, g)
    return {"mus_min": _tan(theta), "mg_sin": down, "mg_cos": into}


# ---------------------------------------------------------------- 6 3RD LAW
def third_law(mA, mB, F=None):
    """6 equal and opposite forces; + = direction of the force on B."""
    _require(mA > 0 and mB > 0, "MUST BE >0")
    out = {"ratio": mB / mA}          # |aA| / |aB|
    if F is not None:
        F = abs(F)
        out.update(F=F, aB=F / mB, aA=-F / mA)
    return out


# ----------------------------------------------------------- 7 SIMPLE CASES
def hanging_rest(m, g=G):
    _require(m > 0, "MUST BE >0")
    return {"T": m * g}


def terminal_velocity(m, g=G):
    _require(m > 0, "MUST BE >0")
    return {"F_air": m * g, "a": 0.0}


def hanging_accel(m, ay, g=G):
    _require(m > 0, "MUST BE >0")
    t = _clean(m * (g + ay))
    return {"T": t, "mg": m * g, "slack": t < 0, "accel": accel_word(ay)}


def net_force(forces, m):
    """Generic sum F = ma with up to 4 signed forces."""
    _require(m > 0, "MUST BE >0")
    _require(len(forces) <= 4, "UP TO 4 FORCES")
    f = _clean(sum(forces))
    word = "NET F: + DIR" if f > 0 else "NET F: - DIR" if f < 0 else "NET F: ZERO"
    return {"Fnet": f, "a": f / m, "net": word, "equilibrium": f == 0}


# ---------------------------------------------------------- 7 CONCEPT CHECK
OPPOSITE = {"UP": "DOWN", "DOWN": "UP", "RIGHT": "LEFT", "LEFT": "RIGHT"}


def concept_check(moving, change=None):
    """moving: UP/DOWN/RIGHT/LEFT, 'REST' (staying at rest) or 'INSTANT'
    (v = 0 for one instant); change: SPEEDING/SLOWING/CONSTANT."""
    if moving == "INSTANT":
        return {"accel": "G DOWN", "net": "MG DOWN", "equilibrium": False,
                "note": "NOT GUARANTEED (TOP OF A TOSS)"}
    if moving == "REST" or change == "CONSTANT":
        return {"accel": "ZERO", "net": "ZERO", "equilibrium": True}
    d = moving if change == "SPEEDING" else OPPOSITE[moving]
    return {"accel": d, "net": d, "equilibrium": False}


# ------------------------------------------------------------------- TESTS
TOL = 0.01


class RequiredCases(unittest.TestCase):
    """The 12 cases from the assignment (g = 9.8, tolerance 0.01)."""

    def test_01_incline_at_rest(self):
        r = incline_rest(5.0, 30)
        self.assertAlmostEqual(r["N"], 42.44, delta=TOL)
        self.assertAlmostEqual(r["fs"], 24.5, delta=TOL)

    def test_02_elevator_down_slowing(self):
        r = elevator_scale(60, 1.5, moving="DOWN", change="SLOWING")
        self.assertAlmostEqual(r["N"], 678, delta=TOL)
        self.assertEqual(r["accel"], "ACCEL: UP")

    def test_03_elevator_scale_390(self):
        r = elevator_accel(50, 390)
        self.assertAlmostEqual(r["ay"], -2.0, delta=TOL)
        self.assertEqual(r["accel"], "ACCEL: DOWN")
        self.assertEqual(r["motion"], ["DOWN+SPEEDING", "UP+SLOWING"])

    def test_04_table_hanger_3_2(self):
        r = table_hanger(3, 2)
        self.assertAlmostEqual(r["a"], 3.92, delta=TOL)
        self.assertAlmostEqual(r["T"], 11.76, delta=TOL)

    def test_05_atwood_6_4(self):
        r = atwood(6, 4)
        self.assertAlmostEqual(r["a"], 1.96, delta=TOL)
        self.assertAlmostEqual(r["T"], 47.04, delta=TOL)
        self.assertTrue(r["check_ok"])

    def test_06_flat_constant_velocity(self):
        r = flat_pull(5, 25, 0, "CONSTANT")
        self.assertAlmostEqual(r["f"], 25, delta=TOL)
        self.assertAlmostEqual(r["N"], 49, delta=TOL)

    def test_07_elevator_up_2(self):
        r = elevator_scale(60, 2.0, direction="UP")
        self.assertAlmostEqual(r["N"], 708, delta=TOL)

    def test_08_elevator_415_moving_up(self):
        r = elevator_accel(50, 415, velocity="UP")
        self.assertAlmostEqual(r["ay"], -1.5, delta=TOL)
        self.assertEqual(r["motion"], ["SLOWING DOWN"])

    def test_09_atwood_3_5(self):
        r = atwood(3, 5)
        self.assertAlmostEqual(r["a"], 2.45, delta=TOL)
        self.assertAlmostEqual(r["T"], 36.75, delta=TOL)
        self.assertEqual(r["down"], "M2 (HEAVY): DOWN")   # the 5 kg mass

    def test_10_table_hanger_4_1(self):
        r = table_hanger(4, 1)
        self.assertAlmostEqual(r["a"], 1.96, delta=TOL)
        self.assertAlmostEqual(r["T"], 7.84, delta=TOL)

    def test_11_third_law_double_mass(self):
        r = third_law(1.0, 2.0, F=10)
        self.assertAlmostEqual(abs(r["aA"]), 2 * abs(r["aB"]), delta=TOL)
        self.assertAlmostEqual(third_law(3, 6)["ratio"], 2, delta=TOL)

    def test_12_flat_angled_pull(self):
        r = flat_pull(5, 20, 30, "FRICTION", 12)
        self.assertAlmostEqual(r["N"], 39.0, delta=TOL)
        self.assertAlmostEqual(r["ax"], 1.064, delta=TOL)


class ExtraCases(unittest.TestCase):
    """Edge cases and impossible setups the program handles."""

    def test_elevator_motion_table(self):
        # study-guide table: motion -> acceleration direction
        cases = {("UP", "SPEEDING"): 1, ("UP", "SLOWING"): -1,
                 ("DOWN", "SPEEDING"): -1, ("DOWN", "SLOWING"): 1,
                 ("UP", "CONSTANT"): 0, ("REST", None): 0}
        for (mv, ch), s in cases.items():
            self.assertEqual(_sign(accel_from_motion(2, mv, ch)), s, (mv, ch))

    def test_elevator_lifts_off_and_weightless(self):
        self.assertTrue(elevator_scale(50, 12, direction="DOWN")["lifts_off"])
        r = elevator_scale(50, 9.8, direction="DOWN")
        self.assertEqual(r["feel"], "WEIGHTLESS (N=0)")
        self.assertAlmostEqual(elevator_free_fall()["ay"], -9.8)

    def test_elevator_accel_zero_and_speeding(self):
        self.assertEqual(elevator_accel(50, 490)["motion"],
                         ["CONSTANT V (OR AT REST)"])
        self.assertEqual(elevator_accel(50, 390, "DOWN")["motion"],
                         ["SPEEDING UP"])

    def test_elevator_mass(self):
        self.assertAlmostEqual(elevator_mass(708, 2.0)["m"], 60, delta=TOL)
        with self.assertRaises(Impossible):
            elevator_mass(100, -9.8)

    def test_atwood_equal_and_other_mass(self):
        r = atwood(4, 4)
        self.assertTrue(r["equilibrium"])
        self.assertAlmostEqual(r["T"], 39.2, delta=TOL)
        self.assertAlmostEqual(atwood_other_mass(1.96, 6, True)["other"], 4,
                               delta=TOL)
        self.assertAlmostEqual(atwood_other_mass(2.45, 3, False)["other"], 5,
                               delta=TOL)
        with self.assertRaises(Impossible):
            atwood_other_mass(9.8, 3, True)

    def test_table_friction(self):
        r = table_hanger(3, 2, muk=0.2)
        self.assertAlmostEqual(r["a"], (19.6 - 0.2 * 29.4) / 5, delta=TOL)
        self.assertAlmostEqual(r["T"], 2 * (9.8 - r["a"]), delta=TOL)
        r = table_hanger(5, 1, muk=0.1, mus=0.3)        # 9.8 < 14.7: stuck
        self.assertFalse(r["moves"])
        self.assertAlmostEqual(r["T"], 9.8, delta=TOL)
        self.assertAlmostEqual(r["fs"], 9.8, delta=TOL)
        with self.assertRaises(Impossible):
            table_hanger(5, 1, muk=0.3, mus=0.1)

    def test_flat_pull_modes(self):
        self.assertTrue(flat_pull(1, 50, 90, "CONSTANT")["lifts_off"])
        r = flat_pull(5, 20, 30, "MUK", 0.2)
        self.assertAlmostEqual(r["f"], 7.8, delta=TOL)
        r = flat_pull(5, 20, 0, "ACCEL", 2)
        self.assertAlmostEqual(r["f"], 10, delta=TOL)
        self.assertTrue(flat_pull(5, 20, 0, "ACCEL", 5)["friction_impossible"])
        self.assertTrue(flat_pull(5, 5, 0, "MUK", 0.5)["stays_put_if_at_rest"])
        r = flat_pull(5, 20, -30, "CONSTANT")      # pushing down: bigger N
        self.assertAlmostEqual(r["N"], 59, delta=TOL)

    def test_incline_variants(self):
        # tan 30 = 0.577: mus 0.6 holds the block, mus 0.5 does not
        r = incline_rest(5, 30, mus=0.6)
        self.assertEqual(r["verdict"], "YES: STAYS PUT")
        self.assertEqual(incline_rest(5, 30, mus=0.5)["verdict"], "NO: WILL SLIDE")
        self.assertAlmostEqual(incline_slide(2, 30, 0.2)["a"],
                               9.8 * (0.5 - 0.2 * _cos(30)), delta=TOL)
        self.assertAlmostEqual(incline_frictionless(2, 30)["a"], 4.9, delta=TOL)
        self.assertAlmostEqual(incline_min_mus(1, 30)["mus_min"], 0.577,
                               delta=TOL)

    def test_simple_cases(self):
        self.assertAlmostEqual(hanging_rest(2)["T"], 19.6, delta=TOL)
        self.assertAlmostEqual(terminal_velocity(70)["F_air"], 686, delta=TOL)
        self.assertAlmostEqual(hanging_accel(2, -1)["T"], 17.6, delta=TOL)
        self.assertTrue(hanging_accel(2, -12)["slack"])
        r = net_force([10, -4, 6], 2)
        self.assertAlmostEqual(r["a"], 6, delta=TOL)
        self.assertFalse(r["equilibrium"])
        self.assertTrue(net_force([5, -5], 3)["equilibrium"])

    def test_concept_check(self):
        self.assertEqual(concept_check("DOWN", "SLOWING")["accel"], "UP")
        self.assertTrue(concept_check("UP", "CONSTANT")["equilibrium"])
        self.assertFalse(concept_check("INSTANT")["equilibrium"])
        self.assertEqual(concept_check("LEFT", "SPEEDING")["net"], "LEFT")

    def test_g_setting(self):
        self.assertAlmostEqual(elevator_scale(60, 2, "UP", g=10)["N"], 720)
        self.assertAlmostEqual(atwood(6, 4, g=9.81)["a"], 1.962, delta=TOL)


if __name__ == "__main__":
    unittest.main(argv=[sys.argv[0]] + sys.argv[1:])
