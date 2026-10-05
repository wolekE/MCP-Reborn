"""
Test helpers: run PHYSOLVE/PHYSREF in the TI-Basic simulator with scripted keypresses and
read the numbers off the simulated screens.

By default programs are loaded from src/*.txt (tokenized exactly like build.py does), so tests
can run while sources are being edited. Set TISIM_FROM=8xp to execute the built .8xp files
(the final verification does this).
"""
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "reference"))

from tisim import TISim, COLS, ROWS  # noqa: E402
from common import fmt3  # noqa: E402

_SIM = None


def sim():
    """TISIM_FROM=8xp runs the built .8xp files. TISIM_SINGLE=1 runs every old entry point
    (PHYSOLVE, PHYSREF, ZFMT, ...) on the merged one-program build PHYSICS, found under
    TISIM_ROOT (default: this directory)."""
    global _SIM
    if _SIM is None:
        use_src = os.environ.get("TISIM_FROM", "src") != "8xp"
        root = Path(os.environ.get("TISIM_ROOT", ROOT))
        if os.environ.get("TISIM_SINGLE"):
            from merge import single_sim
            single = single_sim(TISim)
            base = TISim.load(use_src=use_src, root=root)
            _SIM = single({k: v for k, v in base.programs.items() if k == "PHYSICS"})
        else:
            _SIM = TISim.load(use_src=use_src, root=root)
        errs = _SIM.syntax_errors()
        if errs:
            raise AssertionError("syntax errors:\n" + "\n".join(errs))
    return _SIM


def run(script, program="PHYSOLVE", **kw):
    return sim().run(program, list(script), **kw)


def assert_clean(res, allow_waiting=False, context=""):
    """No runtime error, no leak/scroll/truncation problems, program ended (or is waiting)."""
    msg = f"{context}\n{res.text()}"
    assert res.error is None, f"runtime error {res.error} at {res.error_at}{msg}"
    assert not res.problems, f"problems: {res.problems}{msg}"
    if not allow_waiting:
        assert res.finished, f"program did not finish (waiting={res.waiting}){msg}"


LINE_RE = re.compile(r"^\s*([A-Z0-9θ()/ ,.'+\-]+?)\s*=\s*(-?[0-9][0-9.]*(?:E-?[0-9]+)?)\s*(.*)$")


def screen_values(screen):
    """Parse 'NAME = VALUE UNIT' lines of one screen into a list of (name, value_str, unit)."""
    out = []
    for row in screen:
        m = LINE_RE.match(row)
        if m:
            out.append((m.group(1).strip(), m.group(2), m.group(3).strip()))
    return out


def all_values(res):
    """{name: [value_str, ...]} over every Pause screen, in order."""
    vals = {}
    for scr in res.screens:
        for name, v, unit in screen_values(scr):
            vals.setdefault(name, []).append(v)
    return vals


def last_screen_values(res, index=-1):
    """{name: value_str} for one screen (default: the last Pause screen = summary)."""
    return {n: v for n, v, u in screen_values(res.screens[index])}


def find_screen(res, needle):
    """Return the last screen that contains `needle` on some row."""
    for scr in reversed(res.screens):
        if any(needle in row for row in scr):
            return scr
    raise AssertionError(f"no screen contains {needle!r}\n{res.text()}")


def expect(actual, expected, label):
    """Compare a displayed value with an expected number at 3 significant figures."""
    want = fmt3(expected) if not isinstance(expected, str) else expected
    assert actual == want, f"{label}: screen shows {actual!r}, expected {want!r}"


class Checker:
    """Collects pass/fail results so one run reports every failure."""

    def __init__(self, name):
        self.name = name
        self.passed = 0
        self.failed = []

    def check(self, label, fn):
        try:
            fn()
            self.passed += 1
            print(f"  ok   {label}")
        except AssertionError as e:
            self.failed.append((label, str(e)))
            print(f"  FAIL {label}\n       " + str(e).replace("\n", "\n       ")[:3000])
        except Exception as e:  # a bug in the test or the simulator
            self.failed.append((label, repr(e)))
            print(f"  ERROR {label}: {e!r}")

    def done(self):
        print(f"{self.name}: {self.passed} passed, {len(self.failed)} failed")
        return 0 if not self.failed else 1
