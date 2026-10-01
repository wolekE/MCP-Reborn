#!/usr/bin/env python3
"""
Static checks over every program in src/:

* every line tokenizes from the allowed token lists and parses as a statement
* program names: 1-8 chars, letter first; every prgm call targets a program in src/
* labels: unique per program, every Goto target exists
* blocks: Then follows If; Else/End balance; no Goto, Lbl or Return inside a
  block (a jump out of a block leaks memory on a real TI-84); a single-line If
  is followed by an ordinary statement
* string literals shown with Disp/Output fit the 26-column screen; Output( rows
  and columns given as numbers are on the 10 x 26 screen
* variable layers (see DESIGN.md): a program stores only to its own layer's
  variables or lower ones, and only HAANS/HAOUT touch W
* every program is reachable from HPCANS
"""

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from tibasic import TIError, parse_statement  # noqa: E402
from tokens import TokenError, tokenize, width  # noqa: E402

SRC = HERE.parent / "src"

LOW = {"HADIG", "HAFRAC", "HANUM", "HAKEY", "HAANS", "HAPAGE", "HAOUT", "HAEND", "HAROOT"}
MID = {"HAPOLY", "HAPMUL", "HADOM", "HAIVL"}
HIGH = {"HAFUNC", "HAGRAPH", "HAFSTR", "HAFEVAL", "HAFDOM", "HAFZERO", "HAWORDS", "HAABCK", "HAPTS", "HAEQN", "HAPTXT"}
LAYER_VARS = {
    "low": set("WXYZ") | {"θ", "Str8", "Str9"},
    "mid": set("STUV") | {"Str6", "Str7"},
    "high": set("NOPQR") | {"Str4", "Str5"},
    "solver": set("ABCDEFGHIJKLM") | {"Str0", "Str1", "Str2", "Str3", "L₁", "L₂", "L₃", "L₄", "L₅"},
}
ORDER = ["low", "mid", "high", "solver"]


def layer(name):
    return "low" if name in LOW else "mid" if name in MID else "high" if name in HIGH else "solver"


def allowed(name):
    lay = layer(name)
    ok = set()
    for l in ORDER[: ORDER.index(lay) + 1]:
        ok |= LAYER_VARS[l]
    if name not in ("HAANS", "HAPAGE", "HAOUT"):
        ok.discard("W")
    return ok


def targets(st):
    """Variables a statement stores to."""
    k = st[0]
    if k == "Store":
        t = st[2]
        return [t[1]]
    if k == "Input":
        return [st[2][1]]
    if k == "For":
        return [st[1]]
    return []


def main():
    probs = []
    progs = {p.stem: p.read_text(encoding="utf-8").rstrip("\n").split("\n") for p in sorted(SRC.glob("*.txt"))}
    calls = {}
    for name, lines in progs.items():
        if not re.fullmatch(r"[A-Z][A-Z0-9]{0,7}", name):
            probs.append(f"{name}: bad program name")
        labels, gotos, depth = {}, [], 0
        calls[name] = set()
        ok = allowed(name)
        parsed = []
        for n, line in enumerate(lines, 1):
            where = f"{name}:{n}"
            if line != line.strip() or not line:
                probs.append(f"{where}: blank line or stray whitespace")
                parsed.append(None)
                continue
            try:
                toks = tokenize(line)
                st = parse_statement(toks, where)
            except (TokenError, TIError) as e:
                probs.append(f"{where}: {e}")
                parsed.append(None)
                continue
            parsed.append(st)
            k = st[0]
            if k == "Then" and (n < 2 or parsed[n - 2] is None or parsed[n - 2][0] != "If"):
                probs.append(f"{where}: Then not right after If")
            if k in ("Then", "For", "While", "Repeat"):
                depth += 1
            elif k == "End":
                depth -= 1
                if depth < 0:
                    probs.append(f"{where}: End without a block")
                    depth = 0
            elif k in ("Goto", "Lbl", "Return") and depth > 0:
                probs.append(f"{where}: {k} inside a block")
            if k == "Lbl":
                if st[1] in labels:
                    probs.append(f"{where}: duplicate label {st[1]}")
                labels[st[1]] = n
            if k == "Goto":
                gotos.append((st[1], where))
            if k == "prgm":
                calls[name].add(st[1])
            for v in targets(st):
                vv = v if not v.startswith("ʟ") else None
                if vv is not None and vv not in ok:
                    probs.append(f"{where}: stores to {v} (not allowed in layer {layer(name)})")
            if k in ("Disp", "Output"):
                vals = st[1] if k == "Disp" else [st[3]]
                for a in vals:
                    if a[0] == "str" and sum(width(t) for t in a[1]) > 26:
                        probs.append(f"{where}: text wider than 26: {''.join(a[1])}")
                if k == "Output" and st[1][0] == "num" and st[2][0] == "num":
                    r, c = int(st[1][1]), int(st[2][1])
                    if not (1 <= r <= 10 and 1 <= c <= 26):
                        probs.append(f"{where}: Output({r},{c}) off screen")
                    if st[3][0] == "str" and c - 1 + sum(width(t) for t in st[3][1]) > 26:
                        probs.append(f"{where}: Output text runs past column 26")
        if depth != 0:
            probs.append(f"{name}: {depth} block(s) never closed")
        for k, (st, nxt) in enumerate(zip(parsed, parsed[1:] + [None]), 1):
            if st and st[0] == "If" and (nxt is None or nxt[0] in ("Else", "End", "Lbl")):
                probs.append(f"{name}:{k}: single-line If followed by {nxt and nxt[0]}")
        for lab, where in gotos:
            if lab not in labels:
                probs.append(f"{where}: Goto {lab} has no Lbl")
    for name, cs in calls.items():
        for c in cs:
            if c not in progs:
                probs.append(f"{name}: calls prgm{c} which does not exist")
    if "HPCANS" in progs:
        seen, todo = {"HPCANS"}, ["HPCANS"]
        while todo:
            for c in calls.get(todo.pop(), ()):
                if c in progs and c not in seen:
                    seen.add(c)
                    todo.append(c)
        for name in progs:
            if name not in seen:
                probs.append(f"{name}: not reachable from HPCANS")
    only = [a for a in sys.argv[1:] if not a.startswith("-")]
    if only:
        probs = [p for p in probs if any(p.startswith(o + ":") or p.startswith(o + " ") for o in only)
                 and "not reachable" not in p]
    for p in probs:
        print("  -", p)
    print(f"{len(progs)} programs, {sum(len(l) for l in progs.values())} lines: "
          + ("ALL STATIC CHECKS PASSED" if not probs else f"{len(probs)} problem(s)"))
    return 1 if probs else 0


if __name__ == "__main__":
    sys.exit(main())
