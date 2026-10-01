"""
Run scripted student sessions on the simulator and check the ANSWER screens.

A test case is a dict:
    id        e.g. "PR-1.2a" (study-guide id) or "REG-1" (regression)
    source    what the study guide asks, in words
    path      the keys/inputs a student uses, in words (for TESTS.md)
    actions   list of actions from the main menu: "k1".."k9", "ENTER", "CLEAR",
              "t:TEXT" (type TEXT at an Input prompt and press ENTER)
    expect    list of text lines that must each appear as a whole line on the
              answer page(s) (after stripping spaces), in any order
    official  the study guide's answer, verbatim (for TESTS.md)
    lists     optional {list name: [numbers]} already saved on the calculator
    graph     optional note "graph values typed from the figure"

The run starts at HPCANS (splash, then main menu).  After the actions the
harness presses CLEAR until the program stops.
"""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from tibasic import D, Machine, TIError, load_programs  # noqa: E402

SRC = HERE.parent / "src"
_PROGS = None


def programs():
    global _PROGS
    if _PROGS is None:
        _PROGS = load_programs(SRC)
    return _PROGS


def answer_pages(events):
    """Each answer = the screens from the first one whose top line is ANSWER: (or WHY:)
    through any ENTER=MORE pages, up to the footer key press."""
    answers, cur = [], None
    for kind, detail, lines in events:
        if cur is None and lines and (lines[0].startswith("ANSWER:") or lines[0].startswith("WHY:")):
            cur = []
        if cur is not None:
            if not cur or cur[-1] != lines:
                cur.append(lines)
            if kind == "key" and detail != "ENTER":
                answers.append(cur)
                cur = None
    if cur:
        answers.append(cur)
    return [[l for p in pages for l in p if l.strip()] for pages in answers]


def run_case(case, programs_override=None):
    progs = programs_override or programs()
    lists = {k: [D(str(x)) for x in v] for k, v in (case.get("lists") or {}).items()}
    m = Machine(progs, persistent_lists=lists)
    actions = list(case["actions"]) + ["CLEAR"] * 6
    err = None
    try:
        res = m.run(actions)
    except TIError as e:
        res, err = ("error", None), str(e)
    answers = answer_pages(m.events)
    got = [l.strip() for a in answers for l in a]
    missing = [e for e in case["expect"] if e.strip() not in got]
    ok = (err is None and res[0] == "stop" and not missing and not m.problems)
    return {
        "id": case["id"], "ok": ok, "error": err, "end": res, "missing": missing,
        "answers": answers, "problems": list(m.problems), "machine": m,
    }


def describe_failure(r):
    lines = [f"FAIL {r['id']}: end={r['end']} error={r['error']}"]
    if r["missing"]:
        lines.append(f"   missing lines: {r['missing']}")
    if r["problems"]:
        lines.append(f"   screen problems: {r['problems'][:5]}")
    for a in r["answers"][-3:]:
        lines.append("   answer: " + " | ".join(a))
    m = r["machine"]
    if r["end"][0] != "stop":
        lines.append("   last screen: " + " | ".join(l for l in m.lines() if l.strip()))
    return "\n".join(lines)
