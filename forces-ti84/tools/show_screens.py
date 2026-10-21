#!/usr/bin/env python3
"""Print every result screen of FORCES for a tour of example problems.

    python3 tools/show_screens.py > SCREENS.md

Runs the real .8xp files in the simulator (tools/tisim.py) and draws each
Pause screen in a 16x8 (TI-84 Plus) or 26x10 (TI-84 Plus CE) box.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from test_program import SRC, calc_keys  # noqa: E402
from tisim import Machine  # noqa: E402

TOUR = [
    ("Elevator: 60 kg moving down, slowing at 1.5 (find N)",
     ["ELEVATOR", "FIND SCALE", "60", "1.5", "MOTION", "MOVING DOWN", "SLOWING"]),
    ("Elevator: 60 kg, a = 2.0 up (find N)",
     ["ELEVATOR", "FIND SCALE", "60", "2.0", "#1"]),
    ("Elevator: 50 kg, scale 390 N, velocity unknown",
     ["ELEVATOR", "ACCEL FROM", "50", "390", "UNKNOWN"]),
    ("Elevator: 50 kg, scale 415 N, moving up",
     ["ELEVATOR", "ACCEL FROM", "50", "415", "#1"]),
    ("Elevator: free fall", ["ELEVATOR", "FREE FALL"]),
    ("Elevator: find mass, N = 708, a = 2.0",
     ["ELEVATOR", "FIND MASS", "708", "2"]),
    ("Atwood: 6 kg and 4 kg", ["ATWOOD", "FIND A AND T", "6", "4"]),
    ("Atwood: 3 kg and 5 kg", ["ATWOOD", "FIND A AND T", "3", "5"]),
    ("Atwood: a = 1.96, heavier mass 6 kg (find the other)",
     ["ATWOOD", "#2", "1.96", "6", "HEAVIER"]),
    ("Table + hanger: M = 3, m = 2, frictionless", ["TABLE", "3", "2", "0"]),
    ("Table + hanger: M = 5, m = 1, muk 0.1, mus 0.3 (stays put)",
     ["TABLE", "5", "1", "0.1", "0.3"]),
    ("Flat pull: 5 kg, 25 N horizontal, constant velocity",
     ["FLAT", "5", "25", "0", "CONSTANT"]),
    ("Flat pull: 5 kg, 20 N at 30 deg, friction 12 N",
     ["FLAT", "5", "20", "30", "FRICTION", "12"]),
    ("Incline at rest: 5 kg, 30 deg, mus 0.5", ["INCLINE", "AT REST", "5", "30", "0.5"]),
    ("Incline sliding: 2 kg, 30 deg, muk 0.2", ["INCLINE", "SLIDING", "2", "30", "0.2"]),
    ("Incline frictionless: 2 kg, 30 deg", ["INCLINE", "FRICTIONLESS", "2", "30"]),
    ("Incline min mus: 30 deg", ["INCLINE", "MIN MUS", "1", "30"]),
    ("Pushed up a slope: 5 kg, 30 deg, F = 40 N, muk 0.2",
     ["INCLINE", "PUSHED", "5", "30", "40", "0.2"]),
    ("Slope + hanger: 4 kg block, 30 deg, 3 kg hanger, muk 0.2",
     ["INCLINE", "HANGER", "4", "30", "3", "0.2", ""]),
    ("Slope + hanger: 10 kg block, 40 deg, 2 kg hanger, frictionless",
     ["INCLINE", "HANGER", "10", "40", "2", "0"]),
    ("Slope + hanger: 4 kg block, 30 deg, 2.5 kg hanger, muk 0.2, mus 0.4 (held)",
     ["INCLINE", "HANGER", "4", "30", "2.5", "0.2", "0.4"]),
    ("3rd law: mA = 1, mB = 2, F = 10 N", ["3RD LAW", "1", "2", "10"]),
    ("Hanging mass accelerating: 2 kg, a = -1", ["MORE", "SIMPLE", "#3", "2", "⁻1"]),
    ("Sum F = ma: 10, -4, 6 N on 2 kg", ["MORE", "SIMPLE", "SUM", "10", "⁻4", "6", "", "2"]),
    ("Concept check: moving down, slowing down", ["MORE", "CONCEPT", "MOVING DOWN", "SLOWING"]),
    ("Concept check: v = 0 for one instant", ["MORE", "CONCEPT", "V=0"]),
]


MOTION = ["MORE", "MOTION"]
CE_TOUR = [   # the 'Non-Equilibrium Problems' worksheets (CE only)
    ("Vertical 1: 4500 kg helicopter, a = 2 up (lift)", ["MORE", "SIMPLE", "UP FORCE", "4500", "2"]),
    ("Vertical 2: 15 kg groceries, bag max 230 N, a = 7 up", ["MORE", "ROPE", "WILL IT HOLD", "15", "230", "7"]),
    ("Vertical 3: 10 kg, string max 100 N", ["MORE", "ROPE", "MAX A, LIFTING", "10", "100"]),
    ("Vertical 4: 42 kg bucket, rope max 450 N", ["MORE", "ROPE", "MAX A, LIFTING", "42", "450"]),
    ("Vertical 5: 2.0E-4 kg spider, strand max 2.0E-3 N", ["MORE", "ROPE", "MAX A, LIFTING", "2.0ᴇ⁻4", "2.0ᴇ⁻3"]),
    ("Vertical 6: 70 kg rocket, 25 to 45 m/s in 100 m", MOTION + ["VERTICAL, MOVING UP", "M/S", "V0, V, D", "25", "45", "100", "70"]),
    ("Vertical 8a: backpack, a from the graph (0 to 2 m/s in 16 s)", MOTION + ["HORIZONTAL", "M/S", "V0, V, T", "0", "2", "16", ""]),
    ("Vertical 8b: backpack, 2 kg pulled at 30 deg, a = 0.125, ice", ["FLAT>F", "2", "30", "0.125", "NONE"]),
    ("Horizontal 1: stop an 1100 kg car from 90 km/h in 8.0 s", MOTION + ["HORIZONTAL", "KM/H", "V0, V, T", "90", "0", "8", "1100"]),
    ("Horizontal 2a: 700 kg car, towrope max 1500 N, wind 25 N", ["MORE", "ROPE", "TOWING", "700", "1500", "25"]),
    ("Horizontal 2b: 0 to 30 km/h at 2.1 m/s^2", MOTION + ["HORIZONTAL", "KM/H", "V0, V, A", "0", "30", "2.1", ""]),
    ("Horizontal 3a: 875 kg car, 0 to 26.3 m/s in 0.59 s", MOTION + ["HORIZONTAL", "M/S", "V0, V, T", "0", "26.3", "0.59", "875"]),
    ("Horizontal 3b: car 875 kg vs driver 68 kg", ["MORE", "SIMPLE", "SAME A", "875", "68", ""]),
    ("Horizontal 4: dogs, 42 N right, 35 N left, 2.5 kg bone", ["MORE", "SIMPLE", "SUM", "42", "⁻35", "", "", "2.5"]),
    ("Horizontal 5: 0.145 kg baseball, 30 to 0 m/s in 0.005 s", MOTION + ["HORIZONTAL", "M/S", "V0, V, T", "30", "0", "0.005", "0.145"]),
    ("Horizontal 6: 2000 kg truck, 12 m/s to stop in 15 m", MOTION + ["HORIZONTAL", "M/S", "V0, V, D", "12", "0", "15", "2000"]),
    ("Horizontal 7a: 20 kg box, 50 N at 45 deg, frictionless", ["FLAT", "20", "50", "45", "FRICTION", "0"]),
    ("Horizontal 7b: velocity after 2.0 s at a = 1.768", MOTION + ["HORIZONTAL", "M/S", "V0, A, T", "0", "1.768", "2", ""]),
]


def box(page, cols):
    edge = "+" + "-" * cols + "+"
    return "\n".join([edge] + ["|" + row.ljust(cols) + "|" for row in page] + [edge])


def main():
    for profile, name, cols in (("mono", "TI-84 Plus (16x8)", 16),
                                ("ce", "TI-84 Plus CE (26x10)", 26)):
        print(f"# {name}\n")
        for title, keys in TOUR + (CE_TOUR if profile == "ce" else []):
            m = Machine(SRC[profile], profile, calc_keys(profile, keys) + ["MORE", "QUIT"],
                        init={"G": 9.8}).run()
            assert not m.violations and m.status == "stopped", (title, m.violations)
            print(f"## {title}\n")
            print("Keys: " + " > ".join(k or "ENTER" for k in calc_keys(profile, keys)) + "\n")
            print("```")
            print("\n\n".join(box(p, cols) for p in m.pauses))
            print("```\n")


if __name__ == "__main__":
    main()
