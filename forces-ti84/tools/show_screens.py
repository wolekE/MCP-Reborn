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

from test_program import SRC  # noqa: E402
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
    ("3rd law: mA = 1, mB = 2, F = 10 N", ["3RD LAW", "1", "2", "10"]),
    ("Hanging mass accelerating: 2 kg, a = -1", ["MORE", "SIMPLE", "#3", "2", "⁻1"]),
    ("Sum F = ma: 10, -4, 6 N on 2 kg", ["MORE", "SIMPLE", "SUM", "10", "⁻4", "6", "", "2"]),
    ("Concept check: moving down, slowing down", ["MORE", "CONCEPT", "MOVING DOWN", "SLOWING"]),
    ("Concept check: v = 0 for one instant", ["MORE", "CONCEPT", "V=0"]),
]


def box(page, cols):
    edge = "+" + "-" * cols + "+"
    return "\n".join([edge] + ["|" + row.ljust(cols) + "|" for row in page] + [edge])


def main():
    for profile, name, cols in (("mono", "TI-84 Plus (16x8)", 16),
                                ("ce", "TI-84 Plus CE (26x10)", 26)):
        print(f"# {name}\n")
        for title, keys in TOUR:
            m = Machine(SRC[profile], profile, keys + ["MORE", "QUIT"],
                        init={"G": 9.8}).run()
            assert not m.violations and m.status == "stopped", (title, m.violations)
            print(f"## {title}\n")
            print("Keys: " + " > ".join(keys) + "\n")
            print("```")
            print("\n\n".join(box(p, cols) for p in m.pauses))
            print("```\n")


if __name__ == "__main__":
    main()
