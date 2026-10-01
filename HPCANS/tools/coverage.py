#!/usr/bin/env python3
"""
Write COVERAGE.md: every item of the study guide and cram sheet
(audit/inventory_raw.json) with its solver path, what the student enters,
what the calculator shows (taken from the real test run on the simulator)
and the test ids.  Solver paths come from audit/coverage/*.json.

Exit code 1 if any practice problem (Sections 1-7) or Section 9 answer has no
passing test: "THE PROGRAM IS NOT FINISHED IF A PRACTICE PROBLEM HAS NO SOLVER PATH."
"""

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from harness import run_case  # noqa: E402
from run_tests import load  # noqa: E402

ROOT = HERE.parent
OUT = ROOT / "COVERAGE.md"
MENU = {"1": "F+G OR F/G", "2": "F(G(X))", "3": "F⁻¹", "4": "A*F(BX+C)+K", "5": "ABS BARS",
        "6": "KX^P / ROOTS", "7": "DECOMPOSE"}


def esc(s):
    return " ".join(str(s or "").replace("|", "\\|").split())


def short(lines, n=8):
    lines = [l for l in lines if l.strip() and not l.startswith("ANSWER:")]
    s = " / ".join(lines[:n])
    return s + (" / …" if len(lines) > n else "")


def main():
    inv = json.loads((ROOT / "audit" / "inventory_raw.json").read_text(encoding="utf-8"))
    items, seen = [], set()
    for it in inv["items"] + inv.get("critic_items", []):
        if it["kind"] == "ican" and it["section"][:2] in ("1 ", "2 ", "3 ", "4 ", "5 ", "6 ", "7 "):
            continue  # the same text as the S#-ICAN rule items; their ids collide with the 0.4 list
        key = (it["id"], it["statement"][:60])
        if key in seen:
            continue
        seen.add(key)
        items.append(it)

    rows = {}
    for p in sorted((ROOT / "audit" / "coverage").glob("*.json")):
        for r in json.loads(p.read_text(encoding="utf-8")):
            rows.setdefault(r["item_id"], []).append(r)

    results = {}
    for group, case in load():
        r = run_case(case)
        results[case["id"]] = (case, r)

    def tests_cell(ids):
        out = []
        for t in ids:
            if t in results:
                out.append(f"{t} {'PASS' if results[t][1]['ok'] else 'FAIL'}")
            else:
                out.append(f"{t} (no test)")
        return ", ".join(out) or "—"

    def shows(row):
        for t in row.get("test_ids") or []:
            if t in results and results[t][1]["answers"]:
                return "ANSWER: " + short([l for a in results[t][1]["answers"] for l in a])
        return row.get("calculator_shows") or ""

    def passing(ids):
        return any(t in results and results[t][1]["ok"] for t in ids)

    missing = []
    md = ["# COVERAGE", "",
          "Every item in the study guide and the cram sheet, and how HPCANS handles it.",
          "The student starts `HPCANS`, presses the main-menu number that matches the problem's",
          "shape, then the \"WHAT DO THEY WANT?\" number, and types the numbers on the paper.",
          "**Calculator shows** is copied from the scripted run on the simulator (see TESTS.md).",
          "Main menu: " + "  ".join(f"{k}:{v}" for k, v in MENU.items()) + ".", ""]

    def table(title, pred, kind_cols=True):
        sel = [it for it in items if pred(it)]
        if not sel:
            return
        md.extend([f"## {title}", ""])
        if kind_cols:
            md.append("| ITEM | QUESTION GIVES | EXPECTED ANSWER | SOLVER PATH | STUDENT ENTERS | CALCULATOR SHOWS | TESTS |")
            md.append("|---|---|---|---|---|---|---|")
        else:
            md.append("| ITEM | WHAT IT SAYS | HOW HPCANS HANDLES IT | TESTS |")
            md.append("|---|---|---|---|")
        for it in sel:
            rs = rows.get(it["id"], [])
            ids = [t for r in rs for t in (r.get("test_ids") or [])]
            ids = list(dict.fromkeys(ids))
            if kind_cols:
                r = rs[0] if rs else {}
                gives = r.get("what_question_gives") or it.get("given") or it["statement"]
                exp = it.get("official_answer") or r.get("expected_answer") or ""
                path = "; ".join(dict.fromkeys(x.get("solver_path", "") for x in rs)) or "**NO SOLVER PATH**"
                ent = "; ".join(dict.fromkeys(x.get("student_enters", "") for x in rs if x.get("student_enters")))
                sh = " ‖ ".join(dict.fromkeys(shows(x) for x in rs if shows(x)))
                md.append("| " + " | ".join(esc(x) for x in [f"**{it['id']}** {it['statement'][:160]}", gives[:200],
                                                             exp, path, ent, sh, tests_cell(ids)]) + " |")
                if it["kind"] in ("practice", "solution") and not passing(ids):
                    missing.append(it["id"])
            else:
                how = " ".join(dict.fromkeys(
                    " ".join(x for x in (r.get("solver_path"), r.get("student_enters"), r.get("calculator_shows")) if x)
                    for r in rs)) or "**NOT MAPPED**"
                if not rs:
                    missing.append(it["id"])
                md.append("| " + " | ".join(esc(x) for x in [f"**{it['id']}**", it["statement"][:220], how,
                                                             tests_cell(ids)]) + " |")
        md.append("")

    sec = lambda it, n: it["section"].startswith(n) or f"Practice {n.strip()}" in it["section"]
    table("I Can list", lambda it: it["kind"] == "ican" or it["id"].endswith("-ICAN") and it["kind"] == "rule",
          kind_cols=False)
    for n, name in (("1", "Operations & domain"), ("2", "Composition"), ("3", "Decomposition"), ("4", "Inverses"),
                    ("5", "Transformations"), ("6", "Absolute value"), ("7", "Power functions")):
        table(f"Section {n} {name}: examples and practice",
              lambda it, n=n: it["kind"] in ("intro_example", "test_example", "practice")
              and (it["section"].startswith(n + " ") or it["id"].startswith(f"PR-{n}.")))
    table("Section 9 answers", lambda it: it["kind"] == "solution")
    table("Cram sheet examples", lambda it: it["kind"] == "cram_example")
    table("Cram sheet problem types (\"when you see this, try this\")", lambda it: it["kind"] == "cram_problem_type")
    table("Section 8 corrections to the answer keys", lambda it: it["kind"] == "correction")
    table("Common mistakes (study guide and cram sheet)", lambda it: it["kind"] == "mistake", kind_cols=False)

    n_pr = sum(1 for it in items if it["kind"] == "practice")
    head = [f"**{n_pr} practice problems; " + (f"{len(missing)} without a passing test or mapping: {', '.join(missing)}**"
                                               if missing else "every one has a solver path and a passing test.**"), ""]
    md[7:7] = head
    OUT.write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"wrote {OUT}; {len(missing)} unmapped/failing: {missing}")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
