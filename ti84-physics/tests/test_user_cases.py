"""
The student's 12 required test cases, checked three ways:

  1. Python reference implementation (reference/*.py, mirrors the TI-Basic line for line)
  2. TI-Basic trace: the simulator executing PHYSICS.8xp (the file that is sent to the calculator)
  3. The expected values from the assignment

A case passes when the TI screen shows exactly the reference value at 3 significant figures and
the expected value agrees at the precision it was given (3 s.f., or fewer if it was written with
fewer, e.g. "t = 20 s", "7.4%"). Writes build/TEST_REPORT.md.
"""
import os
import re
import sys
from decimal import Decimal
from pathlib import Path

os.environ["TISIM_SINGLE"] = "1"          # always test the one-program build
os.environ["TISIM_FROM"] = "8xp"          # ...from the .8xp file itself

from harness import ROOT, run, assert_clean, fmt3  # noqa: E402
import zvovf, zfree, zproj, zriver, zchase, ztools  # noqa: E402,E401


def summ(r):
    return r.summary() if callable(r.summary) else r.summary


def val(v):
    return v[0] if isinstance(v, tuple) else v


def sig(s):
    """Significant figures in a number written as text ('20' -> 1, '2.0' -> 2, '0.80' -> 2)."""
    digits = s.replace("-", "").replace(".", "").lstrip("0")
    if "." not in s:
        digits = digits.rstrip("0") or "0"
    return max(1, len(digits))


def round_sig(x, n):
    x = Decimal(str(x))
    if x == 0:
        return Decimal(0)
    q = Decimal(1).scaleb(x.adjusted() - n + 1)
    return x.quantize(q, rounding="ROUND_HALF_UP")


def screen_value(res, label, title=None):
    pat = re.compile(rf"^\s*{re.escape(label)} = (-?[0-9.]+(?:E-?[0-9]+)?)\b")
    screens = res.screens
    if title:
        screens = [s for s in screens if s[0].strip().startswith(title)]
    for scr in reversed(screens):
        for row in scr:
            m = pat.match(row)
            if m:
                return m.group(1)
    raise AssertionError(f"no '{label} = ...' row" + (f" on a '{title}' screen" if title else ""))


# (case, keys after choosing SOLVERS, reference values, [(quantity, screen label, screen title, ref key, expected)])
CASES = [
    ("v0 = 8.0, a = 1.5, s = 120 (VOVFSTA)", [1, 8, 999, 120, 999, 1.5, 7],
     {k: val(v) for k, v in zvovf.solve(8, 999, 120, 999, 1.5)["summary"].items()},
     [("vf", "VF", None, "VF", "20.6"), ("t", "T", None, "T", "8.39")]),
    ("Chase: car 30 m/s, police from rest 3.0 m/s²", [6, 2, 30, 0, 3, 0, 7, 7],
     summ(zchase.run(30, 0, 3, 0)),
     [("t", "T", "SUMMARY", "T", "20"), ("s", "S", "SUMMARY", "S", "600"),
      ("police speed", "V2", "SUMMARY", "V2", "60")]),
    ("Thrown up at 19.6 m/s", [2, 2, 19.6, 6, 7], summ(zfree.run(2, 19.6)),
     [("time to top", "T TO TOP", None, "T TO TOP", "2.0"), ("max height", "MAX HEIGHT", None, "MAX HEIGHT", "19.6")]),
    ("Dropped from 45 m", [2, 1, 45, 6, 7], summ(zfree.run(1, 45)),
     [("t", "T TOTAL", None, "T TOTAL", "3.03"), ("vf", "VF", None, "VF", "-29.7")]),
    ("Thrown up at 10 m/s from a 15 m roof", [2, 4, 15, 10, 6, 7], summ(zfree.run(4, 15, 10)),
     [("max above roof", "ABOVE LAUNCH", None, "ABOVE LAUNCH", "5.10"), ("vf", "VF", None, "VF", "-19.8"),
      ("total t", "T TOTAL", None, "T TOTAL", "3.05")]),
    ("Angled, level ground: 25.0 m/s at 50°", [4, 25, 50, 0, 7], summ(zproj.run(2, 25, 50, 0)),
     [("vx", "VX", None, "VX", "16.07"), ("v0y", "V0Y", None, "V0Y", "19.15"), ("T", "T FLIGHT", None, "T FLIGHT", "3.91"),
      ("R", "RANGE", None, "RANGE", "62.8"), ("hmax", "MAX H", None, "MAX H", "18.7")]),
    ("Angled from a height: 5.0 m/s at 30° from 1.0 m", [4, 5, 30, 1, 7], summ(zproj.run(2, 5, 30, 1)),
     [("t", "T FLIGHT", None, "T FLIGHT", "0.774"), ("x", "RANGE", None, "RANGE", "3.35")]),
    ("Angled from a height: 4.9 m/s at 20° from 0.85 m", [4, 4.9, 20, 0.85, 7], summ(zproj.run(2, 4.9, 20, 0.85)),
     [("T", "T FLIGHT", None, "T FLIGHT", "0.621"), ("R", "RANGE", None, "RANGE", "2.86")]),
    ("Throw lab: H = 2.0 m, t = 2.4 s, range 50 yd", [5, 2, 2, 2.4, 50, 7], summ(zproj.run(3, 2, 2, 2.4, 50)),
     [("range", "RANGE", None, "RANGE", "45.7"), ("vx", "VX", None, "VX", "19.05"), ("v0y", "V0Y", None, "V0Y", "10.93"),
      ("speed", "V0", None, "V0", "21.96"), ("angle", "ANGLE", None, "ANGLE", "29.8")]),
    ("River: boat 6.00 m/s, river 3.00 m/s (width 120 m)", [6, 1, 6, 3, 120, 7, 7], summ(zriver.run(6, 3, 120)),
     [("resultant", "V RESULT", "SUMMARY 1/2", "1:V RESULT", "6.71"),
      ("path angle from straight across", "FROM ACROSS", "SUMMARY 1/2", "1:FROM ACROSS", "26.6")]),
    ("Ramp: slope 0.40", [6, 6, 1, 0.40, 6, 7, 7], ztools.ramp(0.40).results,
     [("a", "A", "SUMMARY", "A", "0.80")]),
    ("Percent difference of 2.10 and 1.95", [6, 6, 2, 2.10, 1.95, 6, 7, 7], ztools.pct_diff(2.10, 1.95).results,
     [("percent difference", "PERCENT DIFF", "SUMMARY", "PCT", "7.4")]),
]


def main():
    rows, failures = [], []
    for case, keys, ref, checks in CASES:
        res = run(keys)           # PHYSOLVE keys; the harness enters SOLVERS first and QUITs at the end
        try:
            assert_clean(res, context=case)
        except AssertionError as e:
            failures.append(f"{case}: {str(e)[:300]}")
        for qty, label, title, ref_key, expected in checks:
            try:
                ti = screen_value(res, label, title)
            except AssertionError as e:
                ti = f"(missing: {e})"
            ref_s = fmt3(val(ref[ref_key]))
            n = min(3, sig(expected))
            ok_ref = ti == ref_s
            ok_exp = (not ti.startswith("(")) and round_sig(ti, n) == round_sig(expected, n)
            ok = ok_ref and ok_exp
            rows.append((case, qty, expected, ref_s, ti, "PASS" if ok else "FAIL"))
            if not ok:
                failures.append(f"{case} / {qty}: expected {expected}, reference {ref_s}, TI screen {ti}")
    out = ["# Required test cases", "",
           "Each case was run three ways: the Python reference implementation (`reference/*.py`), the",
           "TI-Basic itself (the simulator executing **`PHYSICS.8xp`**, the file sent to the calculator,",
           "through its real menus), and the expected value from the assignment. PASS means the TI screen",
           "shows exactly the reference value at 3 significant figures and agrees with the expected value",
           "at the precision it was given.", "",
           "| Case | Quantity | Expected | Python reference (3 s.f.) | TI-Basic screen | Result |",
           "|---|---|---|---|---|---|"]
    out += ["| " + " | ".join(r) + " |" for r in rows]
    out += ["", f"**{sum(r[5] == 'PASS' for r in rows)} of {len(rows)} values match.**", ""]
    (ROOT / "build").mkdir(exist_ok=True)
    (ROOT / "build" / "TEST_REPORT.md").write_text("\n".join(out), encoding="utf-8")
    for r in rows:
        print(f"  {r[5]}  {r[0][:44]:44} {r[1][:22]:22} expected {r[2]:>6}  ref {r[3]:>6}  TI {r[4]:>6}")
    for f in failures:
        print("  FAILURE:", f)
    print(f"user cases: {sum(r[5] == 'PASS' for r in rows)} of {len(rows)} values match, {len(failures)} failure(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
