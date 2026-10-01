#!/usr/bin/env python3
"""Run every scripted test in tools/tests/ and write TESTS.md (or just print with --quiet / a filter)."""
import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from harness import describe_failure, run_case  # noqa: E402

OUT = HERE.parent / "TESTS.md"


def load(only=None):
    cases = []
    for p in sorted((HERE / "tests").glob("test_*.py")):
        if only and p.stem[5:] not in only.split(","):
            continue
        spec = importlib.util.spec_from_file_location(p.stem, p)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        for c in mod.CASES:
            cases.append((p.stem[5:], c))
    return cases


def esc(s):
    return str(s).replace("|", "\\|").replace("\n", " ")


def main():
    only = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("-") else None
    write = "--write" in sys.argv
    cases = load(only)
    rows, fails = [], 0
    for group, c in cases:
        r = run_case(c)
        if not r["ok"]:
            fails += 1
            print(describe_failure(r))
        actual = " / ".join(" | ".join(a) for a in r["answers"]) or "(no answer screen)"
        rows.append((group, c, r, actual))
    print(f"{len(cases)} cases, {len(cases) - fails} passed, {fails} failed")
    if write:
        lines = ["# TESTS", "",
                 "Every row is a scripted session on the simulator (`tools/run_tests.py --write`):",
                 "the keys a student presses from the main menu, the numbers they type, and the",
                 "ANSWER screen(s) the program shows, compared with the study guide's answer.",
                 "Inputs: `k1` = press 1, `t:x` = type x and ENTER (`t:` = just ENTER), `⁻` = the (-) key.", "",
                 f"**{len(cases)} cases: {len(cases) - fails} PASS, {fails} FAIL.**", "",
                 "| PROBLEM | SOLVER PATH | INPUTS | EXPECTED | ACTUAL | PASS/FAIL |",
                 "|---|---|---|---|---|---|"]
        for group, c, r, actual in rows:
            lines.append("| " + " | ".join([
                esc(c["id"] + ": " + c["source"]), esc(c.get("path", "")),
                esc(" ".join(a for a in c["actions"])), esc(c["official"]),
                esc(actual), "PASS" if r["ok"] else "**FAIL**"]) + " |")
        OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"wrote {OUT}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
