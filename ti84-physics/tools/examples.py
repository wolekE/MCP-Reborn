#!/usr/bin/env python3
"""Run one example per solver on PHYSICS.8xp in the simulator and write build/EXAMPLES.md
(every screen) plus a compact version (inputs + final screen) for the README."""
import os
import sys
from pathlib import Path

os.environ["TISIM_SINGLE"] = "1"
os.environ["TISIM_FROM"] = "8xp"
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tests"))
from harness import run, assert_clean  # noqa: E402

EXAMPLES = [
    ("A. VOVFSTA solver", "v0 = 8.0 m/s, a = 1.5 m/s², s = 120 m; vf and t unknown (999)", [1, 8, 999, 120, 999, 1.5, 7]),
    ("B. Free fall", "thrown up at 10 m/s from a 15 m roof (FREE FALL > 4 THROWN UP (HEIGHT H))", [2, 4, 15, 10, 6, 7]),
    ("C. Horizontal launch", "H = 20 m, speed 15 m/s (HORIZONTAL LAUNCH > 1 GIVEN H AND SPEED V)", [3, 1, 20, 15, 7]),
    ("D. Angled launch", "25.0 m/s at 50°, level ground (height 0)", [4, 25, 50, 0, 7]),
    ("E. Throw lab (work backward)", "H = 2.0 m, t = 2.4 s, range 50 yd (THROW LAB > 2 RANGE IN YARDS)", [5, 2, 2, 2.4, 50, 7]),
    ("F. River crossing", "boat 6.00 m/s, river 3.00 m/s, width 120 m (MORE > 1)", [6, 1, 6, 3, 120, 7, 7]),
    ("G. Chase problem", "car 30 m/s, no head start, police 3.0 m/s² from rest, no delay (MORE > 2)", [6, 2, 30, 0, 3, 0, 7, 7]),
    ("H. Vector components", "20 m at 30° to X and Y (MORE > 3 > 1 MAG+ANGLE > 1 DISPLACEMENT)", [6, 3, 1, 1, 20, 30, 3, 7, 7]),
    ("I. Averages", "2 legs: 100 m forward in 10 s, 50 m back in 5 s (MORE > 4)", [6, 4, 2, 100, 1, 10, 50, -1, 5, 7, 7]),
    ("J. Factor of change", "stopping distance 20 m, speed x3 (MORE > 5 > 1 S PROP TO V²)", [6, 5, 1, 20, 3, 6, 7, 7]),
    ("K. Lab tools", "ramp slope 0.40 (MORE > 6 > 1 RAMP)", [6, 6, 1, 0.40, 6, 7, 7]),
    ("K. Lab tools", "percent difference of 2.10 and 1.95 (MORE > 6 > 2)", [6, 6, 2, 2.10, 1.95, 6, 7, 7]),
]


def box(rows):
    out = ["+" + "-" * 26 + "+"]
    for r in rows:
        out.append("|" + r.ljust(26) + "|")
    out.append("+" + "-" * 26 + "+")
    return out


def last_result_screen(res):
    for scr in reversed(res.screens):
        if any(" = " in r for r in scr):
            return [r for r in scr if r.strip()]
    return [r for r in res.screens[-1] if r.strip()]


def main():
    full, compact = ["# Example runs (simulated on PHYSICS.8xp)", ""], []
    for title, what, keys in EXAMPLES:
        res = run(keys)
        assert_clean(res, context=title)
        typed = [f"{p.strip()} {v}" for k, p, v in [e for e in res.events if e[0] == "input"]]
        menus = [f"{e[2][e[3] - 1]}" for e in res.events if e[0] == "menu"]
        full += [f"## {title}: {what}", "", "Menu choices: " + " > ".join(menus), "",
                 "Typed: " + "; ".join(typed), "", "```"]
        for scr in res.screens:
            full += box([r for r in scr])
        full += ["```", ""]
        compact += [f"**{title}** ({what})", "", "Typed: `" + "`, `".join(typed) + "`", "", "```"]
        summaries = [[r for r in scr if r.strip()] for scr in res.screens if scr[0].startswith("SUMMARY")]
        for scr in (summaries or [last_result_screen(res)]):
            compact += box(scr)
        compact += ["```", ""]
    (ROOT / "build").mkdir(exist_ok=True)
    (ROOT / "build" / "EXAMPLES.md").write_text("\n".join(full), encoding="utf-8")
    (ROOT / "build" / "examples_compact.md").write_text("\n".join(compact), encoding="utf-8")
    print("\n".join(compact))


if __name__ == "__main__":
    main()
