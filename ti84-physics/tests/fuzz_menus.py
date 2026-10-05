"""
Random-walk fuzzer: drives PHYSOLVE and PHYSREF through random menu choices and adversarial
inputs (0, negatives, 999, huge/tiny values, angles, ...) and reports any calculator error,
memory leak, scrolling, truncation or infinite loop, with the key sequence to reproduce it.
Also reports which statements were never executed (coverage).

    python3 tests/fuzz_menus.py [walks=4000] [seed=1]
"""
import os
import random
import sys
from collections import Counter

from harness import sim
from tisim import ScriptEnd

POOL = [0, 1, -1, 2, 3, 4, 5, 10, 20, 45, 90, 120, 999, -999, 0.5, 0.001, 1e-5, 1e5, 1e9, -9.8, 9.8,
        30, 60, -30, 180, 270, 360, 1.0936, 2.4, 6, 3, 25, 0.85, 19.6, -45, -0.5, 7, 100, 2.5, 1e-12]
WEIGHTED = POOL + [999] * 6 + [0] * 3 + [10, 20, 5, 2, 1, -1, 3, 45, 30] * 2


def walk(s, program, rng, max_interactions):
    keys = []
    count = [0]

    def responder(kind, info):
        count[0] += 1
        if count[0] > max_interactions:
            raise ScriptEnd()
        if kind == "menu":
            title, items = info
            weights = [0.25 if any(w in t for w in ("QUIT", "BACK")) else 1.0 for t in items]
            choice = rng.choices(range(1, len(items) + 1), weights)[0]
            keys.append(choice)
            return choice
        v = rng.choice(WEIGHTED)
        if rng.random() < 0.15:
            v = round(rng.uniform(-50, 150), rng.randint(0, 3))
        keys.append(v)
        return v

    res = s.run(program, responder=responder, seed=rng.randint(0, 10 ** 9), max_steps=300000)
    return res, keys


def main():
    walks = int(sys.argv[1]) if len(sys.argv) > 1 else 4000
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    s = sim()
    rng = random.Random(seed)
    bad = []
    kinds = Counter()
    for i in range(walks):
        program = "PHYSREF" if (i % 10 == 9 and "PHYSREF" in s.programs) else "PHYSOLVE"
        res, keys = walk(s, program, rng, rng.choice([8, 15, 30, 60]))
        issues = []
        if res.error is not None:
            issues.append(f"{res.error} at {res.error_at}")
        issues += res.problems
        for iss in issues:
            key = iss.split(" at ")[0][:90] if res.error else iss[:120]
            kinds[key] += 1
            if kinds[key] <= 3:
                bad.append((program, keys, iss))
    print(f"{walks} random walks")
    total = sum(kinds.values())
    if total:
        print(f"{total} issue(s) in {len(kinds)} kind(s):")
        for k, n in kinds.most_common():
            print(f"  {n:5}x {k}")
        print("\nreproduce (first examples of each kind):")
        for program, keys, iss in bad[:40]:
            print(f"  {program} {keys}\n     -> {iss}")
    # coverage
    uncovered = []
    for name, prog in s.programs.items():
        if name not in [c[0] for c in s.coverage]:
            uncovered.append(f"{name}: never run")
            continue
        missing = [st for i, st in enumerate(prog.stmts) if (name, i) not in s.coverage and st.kind not in ("Lbl",)]
        if missing:
            uncovered.append(f"{name}: {len(missing)}/{len(prog.stmts)} statements never executed, e.g. "
                             + "; ".join(f"L{st.line} {st.text[:40]}" for st in missing[:6]))
    print("\ncoverage gaps:" if uncovered else "\nevery statement executed at least once")
    for u in uncovered:
        print("  " + u)
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
