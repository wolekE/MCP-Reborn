#!/usr/bin/env python3
"""
Clobber check: after every helper call returns to a caller in a HIGHER layer, give every
variable the helper may change (its layer and the lower ones, see HELPERS.md) except its
documented outputs a junk value.  A caller that kept something there across the call then
shows a wrong answer or an error, so the scripted tests (or a fuzzer) fail.

    python3 poison.py              run every scripted test with poisoning
    python3 poison.py fuzz/fuzz_ops.py 300 5     run a fuzzer with poisoning
"""
import runpy
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import tibasic  # noqa: E402
from check_static import HIGH, LOW, MID, layer  # noqa: E402

RANK = {"low": 0, "mid": 1, "high": 2, "solver": 3}
REALS = {"low": "XYZθ", "mid": "STUV", "high": "NOPQR"}
STRS = {"low": ("Str8", "Str9"), "mid": ("Str6", "Str7"), "high": ("Str4", "Str5")}
OUT = {  # documented results (HELPERS.md); W is never poisoned (only the screen helpers own it)
    "HADIG": {"Str8"}, "HAFRAC": {"Str9", "X", "Y", "Z"}, "HANUM": {"θ", "Z"}, "HAKEY": {"θ"},
    "HAANS": set(), "HAPAGE": set(), "HAOUT": set(), "HAEND": {"θ"}, "HAROOT": {"θ"},
    "HAPOLY": {"Str7"}, "HAPMUL": set(), "HADOM": {"Str6"}, "HAIVL": {"S", "T", "U", "V"},
    "HAPTS": set(), "HAABCK": {"N", "O", "P", "Q"}, "HAEQN": {"Str4", "Str5", "Str9"},
    "HAPTXT": {"Str5"}, "HAFUNC": {"θ", "N"}, "HAFSTR": {"Str5"}, "HAFEVAL": {"P", "Q"},
    "HAFDOM": {"θ"}, "HAFZERO": {"R", "θ"},
}
SKIP = {"HAGRAPH", "HAWORDS"}  # internal to the function helpers
JUNK_R = tibasic.D("7777.123")
JUNK_S = tibasic.TIStr(("Q", "Q", "Q"))
stats = {"poisoned_returns": 0}


class PoisonMachine(tibasic.Machine):
    def after_return(self, name):
        if name in SKIP or not self.frames or name not in OUT:
            return
        caller = self.frames[-1].name
        lc, lh = layer(caller), layer(name)
        if RANK[lc] <= RANK[lh]:
            return
        stats["poisoned_returns"] += 1
        for lay in ("low", "mid", "high")[: RANK[lh] + 1]:
            for v in REALS[lay]:
                if v not in OUT[name]:
                    self.reals[v] = JUNK_R
            for v in STRS[lay]:
                if v not in OUT[name]:
                    self.strs[v] = JUNK_S


def actual_writes():
    """Variables each program (with everything it calls) really stores to."""
    from check_static import targets
    from tokens import tokenize
    src = HERE.parent / "src"
    own, calls = {}, {}
    for path in src.glob("*.txt"):
        w, c = set(), set()
        for n, line in enumerate(path.read_text(encoding="utf-8").rstrip("\n").split("\n"), 1):
            st = tibasic.parse_statement(tokenize(line), f"{path.stem}:{n}")
            w |= set(targets(st))
            if st[0] == "prgm":
                c.add(st[1])
        own[path.stem], calls[path.stem] = w, c
    full = {}
    for name in own:
        seen, todo, w = {name}, [name], set()
        while todo:
            x = todo.pop()
            w |= own.get(x, set())
            for y in calls.get(x, ()):
                if y not in seen:
                    seen.add(y)
                    todo.append(y)
        full[name] = w
    return full


WRITES = actual_writes() if "--contract" not in sys.argv else None
if "--contract" in sys.argv:
    sys.argv.remove("--contract")


class ActualPoison(PoisonMachine):
    def after_return(self, name):
        if WRITES is None:
            return PoisonMachine.after_return(self, name)
        if name in SKIP or not self.frames or name not in OUT:
            return
        caller = self.frames[-1].name
        if RANK[layer(caller)] <= RANK[layer(name)]:
            return
        stats["poisoned_returns"] += 1
        for v in WRITES[name] - OUT[name] - {"W"}:
            if v in self.strs or v.startswith("Str"):
                self.strs[v] = JUNK_S
            elif len(v) == 1 or v == "θ":
                self.reals[v] = JUNK_R


tibasic.Machine = ActualPoison

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1].endswith(".py"):
        target = sys.argv[1]
        sys.argv = sys.argv[1:]
        runpy.run_path(target, run_name="__main__")
    else:
        sys.argv = [sys.argv[0]] + sys.argv[1:]
        import run_tests  # noqa: E402
        rc = run_tests.main()
        print("poisoned returns:", stats["poisoned_returns"])
        sys.exit(rc)
