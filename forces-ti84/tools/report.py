#!/usr/bin/env python3
"""Write TEST_RESULTS.md: the 12 required cases (both calculators) and the
Non-Equilibrium worksheet problems (CE), Python vs. the programs.

    python3 tools/report.py > TEST_RESULTS.md

For each case it shows the assignment's answer, reference.py's answer, and
the number the TI-BASIC program puts on screen (simulated run of the real
.8xp) on the TI-84 Plus and the TI-84 Plus CE.
"""

import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path[:0] = [HERE, ROOT]

import reference as ref  # noqa: E402
from test_program import SRC, calc_keys  # noqa: E402
from tisim import Machine, values  # noqa: E402

CASES = [
    ("Incline at rest, 5.0 kg, 30°", "INCLINE > AT REST > 5.0 > 30 > ENTER",
     ["INCLINE", "AT REST", "5.0", "30", ""], [
         ("N", ("N",), 42.44, ref.incline_rest(5, 30)["N"]),
         ("fs", ("FS", "FS NEEDED"), 24.5, ref.incline_rest(5, 30)["fs"])]),
    ("Elevator, 60 kg, moving down, slowing at 1.5", "ELEVATOR > FIND SCALE N > 60 > 1.5 > FROM MOTION > MOVING DOWN > SLOWING DOWN",
     ["ELEVATOR", "FIND SCALE", "60", "1.5", "MOTION", "MOVING DOWN", "SLOWING"], [
         ("N", ("N", "SCALE N"), 678,
          ref.elevator_scale(60, 1.5, moving="DOWN", change="SLOWING")["N"])]),
    ("Elevator, 50 kg, scale 390", "ELEVATOR > ACCEL FROM N > 50 > 390 > UNKNOWN",
     ["ELEVATOR", "ACCEL FROM", "50", "390", "UNKNOWN"], [
         ("aᵧ", ("AY", "ACCEL AY"), -2.0, ref.elevator_accel(50, 390)["ay"])]),
    ("Table + hanger, M = 3, m = 2, frictionless", "TABLE + HANGER > 3 > 2 > 0",
     ["TABLE", "3", "2", "0"], [
         ("a", ("A",), 3.92, ref.table_hanger(3, 2)["a"]),
         ("T", ("T",), 11.76, ref.table_hanger(3, 2)["T"])]),
    ("Atwood 6 and 4", "ATWOOD > FIND A AND T > 6 > 4",
     ["ATWOOD", "FIND A AND T", "6", "4"], [
         ("a", ("A",), 1.96, ref.atwood(6, 4)["a"]),
         ("T", ("T",), 47.04, ref.atwood(6, 4)["T"])]),
    ("Flat pull, 5 kg, 25 N horizontal, constant v", "FLAT SURF PULL > 5 > 25 > 0 > CONSTANT V",
     ["FLAT", "5", "25", "0", "CONSTANT"], [
         ("f", ("FRIC",), 25, ref.flat_pull(5, 25, 0, "CONSTANT")["f"]),
         ("N", ("N",), 49, ref.flat_pull(5, 25, 0, "CONSTANT")["N"])]),
    ("Elevator, 60 kg, a = 2.0 up", "ELEVATOR > FIND SCALE N > 60 > 2.0 > UP",
     ["ELEVATOR", "FIND SCALE", "60", "2.0", "#1"], [
         ("N", ("N", "SCALE N"), 708, ref.elevator_scale(60, 2.0, "UP")["N"])]),
    ("Elevator, 50 kg, scale 415, moving up", "ELEVATOR > ACCEL FROM N > 50 > 415 > UP",
     ["ELEVATOR", "ACCEL FROM", "50", "415", "#1"], [
         ("aᵧ", ("AY", "ACCEL AY"), -1.5, ref.elevator_accel(50, 415, "UP")["ay"])]),
    ("Atwood 3 and 5", "ATWOOD > FIND A AND T > 3 > 5",
     ["ATWOOD", "FIND A AND T", "3", "5"], [
         ("a", ("A",), 2.45, ref.atwood(3, 5)["a"]),
         ("T", ("T",), 36.75, ref.atwood(3, 5)["T"])]),
    ("Table + hanger, M = 4, m = 1, frictionless", "TABLE + HANGER > 4 > 1 > 0",
     ["TABLE", "4", "1", "0"], [
         ("a", ("A",), 1.96, ref.table_hanger(4, 1)["a"]),
         ("T", ("T",), 7.84, ref.table_hanger(4, 1)["T"])]),
    ("3rd law, mB = 2·mA (mA = 1, mB = 2, F blank)", "3RD LAW > 1 > 2 > ENTER",
     ["3RD LAW", "1", "2", ""], [
         ("size ratio aA/aB", ("RATIO",), 2, ref.third_law(1, 2)["ratio"])]),
    ("Flat pull, 5 kg, 20 N at 30°, f = 12", "FLAT SURF PULL > 5 > 20 > 30 > FRICTION (N) > 12",
     ["FLAT", "5", "20", "30", "FRICTION", "12"], [
         ("N", ("N",), 39.0, ref.flat_pull(5, 20, 30, "FRICTION", 12)["N"]),
         ("aₓ", ("AX",), 1.064, ref.flat_pull(5, 20, 30, "FRICTION", 12)["ax"])]),
]

WORDS = {
    "Elevator, 60 kg, moving down, slowing at 1.5": ["ACCEL: UP", "HEAVIER (N>MG)"],
    "Elevator, 50 kg, scale 390": ["ACCEL: DOWN", "DOWN+SPEEDING", "UP+SLOWING"],
    "Elevator, 50 kg, scale 415, moving up": ["SLOWING DOWN"],
    "Atwood 3 and 5": ["M2 (HEAVY): DOWN", "M1 (LIGHT): UP"],
    "Atwood 6 and 4": ["M2G<T<M1G", "CHECK OK"],
}


def shown(profile, keys, labels):
    m = Machine(SRC[profile], profile, calc_keys(profile, keys) + ["MORE", "QUIT"],
                init={"G": 9.8}).run()
    assert not m.violations and m.status == "stopped"
    for label, v, unit in values(m.pauses):
        if label in labels:
            row = next(r for p in m.pauses for r in p
                       if r.startswith(label + "=") and values([[r]]))
            return row, m, v
    raise AssertionError(labels)


MOTION = ["MORE", "MOTION"]
KMH = ref.KMH
WORKSHEET = [  # (problem, keys, label(s), sheet answer, reference.py)
    ("V1 helicopter lift", ["MORE", "SIMPLE", "UP FORCE", "4500", "2"],
     ("T",), 53100, ref.hanging_accel(4500, 2)["T"]),
    ("V2 grocery bag (holds?)", ["MORE", "ROPE", "WILL IT HOLD", "15", "230", "7"],
     ("T NEEDED",), 252, ref.rope_hold(15, 230, 7)["T"]),
    ("V3 string max a", ["MORE", "ROPE", "MAX A, LIFTING", "10", "100"],
     ("AMAX UP",), 0.2, ref.rope_max_lift(10, 100)["a_max"]),
    ("V4 bucket max a", ["MORE", "ROPE", "MAX A, LIFTING", "42", "450"],
     ("AMAX UP",), 0.914, ref.rope_max_lift(42, 450)["a_max"]),
    ("V5 spider max a", ["MORE", "ROPE", "MAX A, LIFTING", "2.0ᴇ⁻4", "2.0ᴇ⁻3"],
     ("AMAX UP",), 0.20, ref.rope_max_lift(2e-4, 2e-3)["a_max"]),
    ("V6a rocket a", MOTION + ["VERTICAL, MOVING UP", "M/S", "V0, V, D", "25", "45", "100", "70"],
     ("A",), 7, ref.kinematics("VVD", 25, v=45, d=100)["a"]),
    ("V6c rocket engine force", MOTION + ["VERTICAL, MOVING UP", "M/S", "V0, V, D", "25", "45", "100", "70"],
     ("F UP",), 1176, ref.motion_force(70, 7, "UP")["F_up"]),
    ("V8 backpack a (graph)", MOTION + ["HORIZONTAL", "M/S", "V0, V, T", "0", "2", "16", ""],
     ("A",), 0.125, ref.kinematics("VVT", 0, v=2, t=16)["a"]),
    ("V8 backpack pull F", ["FLAT>F", "2", "30", "0.125", "NONE"],
     ("F",), 0.289, ref.pull_force(2, 30, 0.125)["F"]),
    ("H1 stop the car", MOTION + ["HORIZONTAL", "KM/H", "V0, V, T", "90", "0", "8", "1100"],
     ("FNET",), -3.44e3, 1100 * ref.kinematics("VVT", 90 * KMH, v=0, t=8)["a"]),
    ("H2a towrope max a", ["MORE", "ROPE", "TOWING", "700", "1500", "25"],
     ("AMAX",), 2.1, ref.tow_max(700, 1500, 25)["a_max"]),
    ("H2b time to 30 km/h", MOTION + ["HORIZONTAL", "KM/H", "V0, V, A", "0", "30", "2.1", ""],
     ("T",), 3.97, ref.kinematics("VVA", 0, v=30 * KMH, a=2.1)["t"]),
    ("H3a dragster net force", MOTION + ["HORIZONTAL", "M/S", "V0, V, T", "0", "26.3", "0.59", "875"],
     ("FNET",), 3.9e4, 875 * ref.kinematics("VVT", 0, v=26.3, t=0.59)["a"]),
    ("H3b car vs driver force", ["MORE", "SIMPLE", "SAME A", "875", "68", ""],
     ("F1/F2",), 13, ref.force_ratio(875, 68)["ratio"]),
    ("H4 dogs and bone", ["MORE", "SIMPLE", "SUM", "42", "⁻35", "", "", "2.5"],
     ("A",), 2.8, ref.net_force([42, -35], 2.5)["a"]),
    ("H5 baseball", MOTION + ["HORIZONTAL", "M/S", "V0, V, T", "30", "0", "0.005", "0.145"],
     ("FNET",), -870, 0.145 * ref.kinematics("VVT", 30, v=0, t=0.005)["a"]),
    ("H6 truck", MOTION + ["HORIZONTAL", "M/S", "V0, V, D", "12", "0", "15", "2000"],
     ("FNET",), -9600, 2000 * ref.kinematics("VVD", 12, v=0, d=15)["a"]),
    ("H7 box a", ["FLAT", "20", "50", "45", "FRICTION", "0"],
     ("AX",), 1.77, ref.flat_pull(20, 50, 45, "FRICTION", 0)["ax"]),
    ("H7 box v after 2.0 s", MOTION + ["HORIZONTAL", "M/S", "V0, A, T", "0", "1.768", "2", ""],
     ("V",), 3.54, ref.kinematics("VAT", 0, a=1.768, t=2)["v"]),
]


def worksheet():
    print("\n## Non-Equilibrium Problems worksheets (TI-84 Plus CE)\n")
    print("Keyed into the CE program; the answer column is what the worksheet "
          "prints (it rounds, so a 1-4% match counts).\n")
    print("| Problem | Keys | Worksheet | reference.py | TI-84 Plus CE shows | Pass |")
    print("|---------|------|----------:|-------------:|---------------------|:----:|")
    for name, keys, labels, sheet, py in WORKSHEET:
        row, m, v = shown("ce", keys, labels)
        tol = 0.04 if "driver" in name else 0.01
        ok = abs(v - py) <= 0.0011 + abs(py) * 1e-9 and \
            abs(abs(v) - abs(sheet)) <= max(0.011, abs(sheet) * tol)
        shown_keys = calc_keys("ce", keys)
        print(f"| {name} | `{' > '.join(k or 'ENTER' for k in shown_keys)}` | {sheet:g} | "
              f"{py:.4g} | `{row}` | {'✅' if ok else '❌'} |")


def main():
    print("# Test results\n")
    print("Generated by `python3 tools/report.py`. g = 9.8, tolerance 0.01. The TI "
          "columns are the exact rows each program prints when the real `.8xp` "
          "is run in the simulator (`tools/tisim.py`) with the keys shown "
          "(⁻ is the calculator's negative sign).\n")
    print("| # | Case | Quantity | Assignment | reference.py | TI-84 Plus | TI-84 Plus CE | Pass |")
    print("|---|------|----------|-----------:|-------------:|------------|---------------|:----:|")
    for i, (name, keys_text, keys, checks) in enumerate(CASES, start=1):
        for qty, labels, want, py in checks:
            mono, mm, vm = shown("mono", keys, labels)
            ce, mc, vc = shown("ce", keys, labels)
            ok = abs(py - want) <= 0.01 and all(abs(v - py) <= 0.0011 for v in (vm, vc))
            print(f"| {i} | {name} | {qty} | {want:g} | {py:.4f} | `{mono}` | `{ce}` | "
                  f"{'✅' if ok else '❌'} |")
        for w in WORDS.get(name, []):
            found = all(any(w in row for p in m.pauses for row in p) for m in (mm, mc))
            print(f"| {i} | {name} | shows “{w}” | | | {'yes' if found else 'NO'} | "
                  f"{'yes' if found else 'NO'} | {'✅' if found else '❌'} |")
    print("\nKey presses for each case:\n")
    for i, (name, keys_text, _, _) in enumerate(CASES, start=1):
        print(f"{i}. {name}: `{keys_text}`")
    worksheet()
    print("\n## Test suites\n")
    for cmd in (["python3", "reference.py"], ["python3", "tools/test_program.py"]):
        r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
        tail = [ln for ln in (r.stdout + r.stderr).splitlines() if ln.strip()][-2:]
        print(f"- `{' '.join(cmd)}`: " + " / ".join(tail))


if __name__ == "__main__":
    main()
