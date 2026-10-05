#!/usr/bin/env python3
"""
merge.py - combine the module sources into ONE TI-Basic program, PHYSICS.

The modules (modules/*.txt: the solver menu, the solvers, the helpers and the reference) are
kept as separate files because they are easier to read, test and review. For the calculator
they are merged into a single program so the student only sends and runs one file.

How one program replaces many:
  * TI-Basic has no subroutines inside a program, but a program may call itself. Every former
    `prgmZFMT` (etc.) becomes two lines:  `⁻1ᴇ⁻99→U`  (a marker no real value ever has) and
    `prgmPHYSICS`. The top of PHYSICS checks U against each marker and jumps to that routine;
    the routine starts with `0→U` (so the marker never lingers) and ends with `Return`, which
    returns to the line after the call exactly as the separate programs did.
  * Labels are renamed so every label in the merged program is unique (each module keeps its
    own logic; only the 1-2 character names change).
  * The main menu gains a top level: SOLVERS / FORMULA REFERENCE / QUIT.

Usage:  python3 tools/merge.py [MODULE_DIR] [OUT_FILE]
        (defaults: modules/ -> src/PHYSICS.txt)
"""

import re
import sys
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NAME = "PHYSICS"

# routine -> marker stored in U before `prgmPHYSICS` (all far below any real measurement)
ROUTINES = ["ZFMT", "ZLINE", "ZQUAD", "ZVOVF", "ZFREE", "ZPROJ", "ZCHASE", "ZRIVER", "ZTOOLS", "PHYSREF"]
MARKER_TEXT = {r: f"⁻{m}ᴇ⁻99" for r, m in zip(ROUTINES, ["1", "2", "3", "4", "5", "6", "7", "8", "9", "11"])}
MARKER_VALUE = {r: Decimal(t.replace("⁻", "-").replace("ᴇ", "E")) for r, t in MARKER_TEXT.items()}

SAVED = list("ABCDEFGHIJKLMNPQSUVWZ")

LABEL_CHARS = "ABCDEFGHIJKLMNOPQSUVWZ0123456789"     # no R, T, X, Y, θ


def split_args(s):
    args, depth, cur, ins = [], 0, "", False
    for ch in s:
        if ch == '"':
            ins = not ins
        if not ins and ch in "({":
            depth += 1
        if not ins and ch in ")}":
            depth -= 1
        if ch == "," and depth == 0 and not ins:
            args.append(cur)
            cur = ""
        else:
            cur += ch
    args.append(cur)
    return args


def main_section():
    """The top-level code (formerly PHYSOLVE) with labels in its own namespace."""
    L = ["{" + ",".join(SAVED) + "}→ʟPSAV",
         "Lbl M0",
         'Menu("PHYSICS  KINEMATICS","SOLVERS",M1,"FORMULA REFERENCE",RF,"QUIT",Q)',
         "Lbl M1",
         'Menu("PHYSOLVE 1/2  KINEMATICS","VOVFSTA SOLVER",A,"FREE FALL",B,"HORIZONTAL LAUNCH",C,'
         '"ANGLED LAUNCH",D,"THROW LAB (BACKWARD)",E,"MORE >",M2,"QUIT TO MAIN MENU",M0)',
         "Lbl M2",
         'Menu("PHYSOLVE 2/2  KINEMATICS","RIVER CROSSING",F,"CHASE PROBLEM",G,"VECTOR COMPONENTS",H,'
         '"AVG SPEED/VELOCITY",I,"FACTOR OF CHANGE",J,"LAB TOOLS",K,"BACK",M1)']
    calls = [("A", "1", "ZVOVF", "M1"), ("B", None, "ZFREE", "M1"), ("C", "1", "ZPROJ", "M1"),
             ("D", "2", "ZPROJ", "M1"), ("E", "3", "ZPROJ", "M1"), ("F", None, "ZRIVER", "M2"),
             ("G", None, "ZCHASE", "M2"), ("H", "1", "ZTOOLS", "M2"), ("I", "2", "ZTOOLS", "M2"),
             ("J", "3", "ZTOOLS", "M2"), ("K", "4", "ZTOOLS", "M2"), ("RF", None, "PHYSREF", "M0")]
    for lab, k, prog, back in calls:
        L.append(f"Lbl {lab}")
        if k:
            L.append(f"{k}→K")
        L.append(f"prgm{prog}")
        L.append(f"Goto {back}")
    L.append("Lbl Q")
    for i, v in enumerate(SAVED, 1):
        L.append(f"ʟPSAV({i})→{v}")
    L += ["DelVar ʟPSAV", "ClrHome", "Return"]
    return L


def _plain(label):
    """True if tivars tokenizes `label` as separate one-character tokens (e.g. not 'FV')."""
    from tivars.tokenizer import tokenize
    return len(tokenize(label, mode="max")) == len(label)


class LabelMap:
    def __init__(self):
        self.used = set()
        self.gen = (a + b for a in LABEL_CHARS[:22] for b in LABEL_CHARS if _plain(a + b))

    def fresh(self):
        lab = next(self.gen)
        self.used.add(lab)
        return lab


def transform(module, lines, labels, entry=None):
    """Rename labels, turn prgm calls into marker + self-call, keep everything else verbatim."""
    own = {}
    for ln in lines:
        m = re.match(r"^Lbl (.+)$", ln)
        if m:
            if m.group(1) in own:
                raise ValueError(f"{module}: duplicate label {m.group(1)}")
            own[m.group(1)] = labels.fresh()

    def lab(x):
        if x not in own:
            raise ValueError(f"{module}: jump to unknown label {x!r}")
        return own[x]

    out = []
    if entry:
        out += [f"Lbl {entry}", "0→U"]
    for i, ln in enumerate(lines):
        m = re.match(r"^(Lbl|Goto) (.+)$", ln)
        if m:
            out.append(f"{m.group(1)} {lab(m.group(2))}")
            continue
        if ln.startswith("Menu("):
            inner = ln[len("Menu("):]
            closed = inner.endswith(")")
            if closed:
                inner = inner[:-1]
            args = split_args(inner)
            for j in range(2, len(args), 2):
                args[j] = lab(args[j])
            if module == "PHYSREF":
                args = [('"QUIT TO MAIN MENU"' if a == '"QUIT"' else a) for a in args]
            out.append("Menu(" + ",".join(args) + (")" if closed else ""))
            continue
        m = re.match(r"^prgm([A-Z0-9θ]+)$", ln)
        if m:
            callee = m.group(1)
            if callee not in MARKER_TEXT:
                raise ValueError(f"{module}: calls unknown program {callee}")
            prev = lines[i - 1] if i else ""
            if prev.startswith("If "):
                raise ValueError(f"{module}:{i + 1}: prgm call is the body of a one-line If; "
                                 "wrap it in Then/End in the module first")
            out += [f"{MARKER_TEXT[callee]}→U", f"prgm{NAME}"]
            continue
        if ln == "Stop":
            out.append("Return")
            continue
        out.append(ln)
    if entry:
        out.append("Return")
    return out


def merge(module_dir):
    module_dir = Path(module_dir)
    labels = LabelMap()
    entries = {r: labels.fresh() for r in ROUTINES}
    head = ["Degree"]
    for r in ROUTINES:
        head += [f"If U={MARKER_TEXT[r]}", f"Goto {entries[r]}"]
    body = transform("MAIN", main_section(), labels)
    for r in ROUTINES:                       # helpers first: their labels are found fastest
        text = (module_dir / f"{r}.txt").read_text(encoding="utf-8")
        if text.endswith("\n"):
            text = text[:-1]
        body += transform(r, text.split("\n"), labels, entry=entries[r])
    return "\n".join(head + body) + "\n"


def main(argv):
    module_dir = Path(argv[0]) if argv else ROOT / "modules"
    out = Path(argv[1]) if len(argv) > 1 else ROOT / "src" / f"{NAME}.txt"
    text = merge(module_dir)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    print(f"wrote {out}: {text.count(chr(10))} lines")
    return 0


# ----------------------------------------------------------------------------- test support

def single_sim(sim_cls):
    from tisim import ScriptEnd

    """A simulator subclass that runs the old entry points (PHYSOLVE, PHYSREF, ZFMT, ...) on the
    merged PHYSICS program, so the module test-suites run unchanged against the single program."""

    class SingleSim(sim_cls):
        def __init__(self, *a, **kw):
            super().__init__(*a, **kw)
            by_value = {v: r for r, v in MARKER_VALUE.items()}
            self.call_alias = lambda name, vars_: by_value.get(vars_.get("U"), name)

        def run(self, name, script=(), **kw):
            if name not in ("PHYSOLVE", "PHYSREF") and name not in MARKER_VALUE:
                return super().run(name, script, **kw)
            first = [1 if name == "PHYSOLVE" else 2]
            inner = kw.pop("responder", None)
            keys = list(script)

            def responder(kind, info):
                # the new top menu: enter SOLVERS / FORMULA REFERENCE once, afterwards QUIT
                if kind == "menu" and info[0] == "PHYSICS  KINEMATICS":
                    return first.pop() if first else 3
                if inner is not None:
                    return inner(kind, info)
                if not keys:
                    raise ScriptEnd()
                return keys.pop(0)

            if name in MARKER_VALUE and name != "PHYSREF":     # helpers/solvers: enter as a self-call
                iv = dict(kw.pop("init_vars", None) or {})
                iv["U"] = MARKER_VALUE[name]
                kw["init_vars"] = iv
            res = super().run(NAME, responder=responder, **kw)
            # hide the new top menu so event lists look like the separate programs' runs
            res.events = [e for e in res.events if not (e[0] == "menu" and e[1] == "PHYSICS  KINEMATICS")]
            res.calls = [name] + res.calls[1:]      # self-calls are reported by routine name
            return res

    return SingleSim


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
