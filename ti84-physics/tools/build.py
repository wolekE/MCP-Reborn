#!/usr/bin/env python3
"""
Build the TI-84 Plus CE program PHYSICS.8xp (the file to send) from the TI-Basic module sources in
../src/*.txt: each module is built on its own into build/modules/ (for testing), then all modules
are merged by tools/merge.py into PHYSICS.txt and built into PHYSICS.8xp.

Tokenizer: TI-Toolkit tivars_lib_py (https://github.com/TI-Toolkit/tivars_lib_py),
installed with `pip install tivars` or from a clone of the GitHub repo.

Each source line is split into code and string-literal segments. Code is
tokenized by tivars in "max" (maximal munch) mode and string contents in "min"
mode, which is what tivars' own "smart" mode intends; doing the split here
avoids a smart-mode quirk where `"0"→Str9` on a later line can come out as the
letters S,t,r,9 instead of the Str9 token. The token stream is then linted
(no lowercase-letter tokens in code, only one-glyph tokens in strings, only
commands the simulator in tisim.py implements, screen-width limits, ...).

After saving, every .8xp is re-opened from disk, detokenized with tivars, and
diffed against its source text. The build fails on any difference.

Usage:  python3 tools/build.py                 (build + lint + round-trip, writes 8xp/)
        python3 tools/build.py --check         (lint + in-memory round-trip, writes nothing)
        python3 tools/build.py --check --only ZVOVF,ZFMT   (just these programs)
"""

import difflib
import hashlib
import re
import sys
from pathlib import Path

from tivars.models import TI_84PCE
from tivars.tokenizer import tokenize
from tivars.types import TIProgram

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
OUT = ROOT / "build" / "modules"          # each module as its own .8xp (used by the tests)
SINGLE = "PHYSICS"                         # the one program the student sends
SINGLE_TXT = ROOT / f"{SINGLE}.txt"
SINGLE_8XP = ROOT / f"{SINGLE}.8xp"
MAX_PROGRAM_BYTES = 65000                  # a TI-84 Plus CE program can hold just under 64 KB
RT = ROOT / "build" / "roundtrip"
REPORT = ROOT / "build" / "ROUNDTRIP.md"

SCREEN_W = 26      # TI-84 Plus CE home screen: 26 columns x 10 rows
MENU_MAX = 7       # Menu( limit on the TI-84 Plus; also safe on the CE
MENU_ITEM_W = 24   # "1:" prefix + 24 characters
PROMPT_W = 18      # leave room to type a number after an Input prompt

TOKENS = TI_84PCE.tokens
NEWLINE = TOKENS.bytes[b"\x3f"]
QUOTE = TOKENS.bytes[b"\x2a"]
STO = TOKENS.bytes[b"\x04"]

# Every token allowed outside string literals. tisim.py implements exactly these.
CODE_TOKENS = {
    # statements / control flow
    "ClrHome", "Disp ", "Output(", "Pause ", "Input ", "Prompt ", "Menu(", "Lbl ", "Goto ",
    "If ", "Then", "Else", "End", "While ", "Repeat ", "For(", "Return", "Stop", "prgm",
    "DelVar ", "Degree", "Radian", "Float", "Normal", "Fix ",
    # punctuation / operators
    "→", '"', ",", "(", ")", "{", "}", "+", "-", "*", "/", "^", "⁻", "²", "⁻¹", "°",
    "=", "≠", "<", ">", "≤", "≥", " and ", " or ", " xor ", "not(", ".", "ᴇ", " ", "!",
    # values / variables
    "π", "Ans", "ʟ",
    "Str0", "Str1", "Str2", "Str3", "Str4", "Str5", "Str6", "Str7", "Str8", "Str9",
    # functions
    "abs(", "int(", "iPart(", "fPart(", "round(", "log(", "ln(", "₁₀^(", "𝑒^(", "√(",
    "sin(", "cos(", "tan(", "sin⁻¹(", "cos⁻¹(", "tan⁻¹(", "R►Pr(", "R►Pθ(", "P►Rx(", "P►Ry(",
    "min(", "max(", "sub(", "length(", "dim(", "sum(",
}
CODE_TOKENS |= set("ABCDEFGHIJKLMNOPQRSTUVWXYZθ0123456789")

FORBIDDEN_VARS = set("RTXYθ")   # clobbered by graphing/solver/table; never used as variables
NAME_RE = re.compile(r"^[A-Zθ][A-Z0-9θ]{0,7}$")
LABEL_RE = re.compile(r"^[A-Z0-9θ]{1,2}$")


class BuildError(Exception):
    pass


def disp(tok):
    return tok.langs["en"].display


def lex_line(line):
    """Split one source line into [(kind, text)] with kind in {'code','quote','str','sto'}."""
    segs, i, n = [], 0, len(line)
    code = ""
    while i < n:
        ch = line[i]
        if ch == '"':
            if code:
                segs.append(("code", code))
                code = ""
            segs.append(("quote", '"'))
            j = i + 1
            content = ""
            while j < n and line[j] not in '"→':
                content += line[j]
                j += 1
            if content:
                segs.append(("str", content))
            if j < n and line[j] == '"':
                segs.append(("quote", '"'))
                j += 1
            i = j          # a '→' that ended the string is handled as code
        else:
            code += ch
            i += 1
    if code:
        segs.append(("code", code))
    return segs


def tokenize_line(line, where):
    out = []        # list of (token, in_string)
    for kind, text in lex_line(line):
        try:
            if kind == "quote":
                out.append((QUOTE, False))
            elif kind == "str":
                out.extend((t, True) for t in tokenize(text, mode="min"))
            else:
                out.extend((t, False) for t in tokenize(text, mode="max"))
        except ValueError as e:
            raise BuildError(f"{where}: cannot tokenize {text!r}: {e}")
    return out


def tokenize_program(text, name):
    lines = text.split("\n")
    toks, per_line = [], []
    for k, line in enumerate(lines, 1):
        lt = tokenize_line(line, f"{name}:{k}")
        per_line.append(lt)
        toks.extend(t for t, _ in lt)
        if k < len(lines):
            toks.append(NEWLINE)
    return toks, per_line


def string_literals(line_toks):
    """Yield the text of each string literal on a line (as displayed)."""
    cur, inside = None, False
    for t, in_str in line_toks:
        if t is QUOTE or t.bits == b"\x2a":
            if inside:
                yield cur
                inside, cur = False, None
            else:
                inside, cur = True, ""
        elif t.bits == b"\x04" and inside:
            yield cur
            inside, cur = False, None
        elif inside:
            cur += disp(t)
    if inside:
        yield cur


def split_args(s):
    """Split the inside of Menu(...) on top-level commas, respecting strings/parens."""
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


def lint(name, text, per_line, all_names):
    errs, warns = [], []
    lines = text.split("\n")
    labels = {}
    if lines[0] != "Degree":
        errs.append(f"{name}:1: first line must be 'Degree' (each program sets Degree mode)")
    for k, (line, lt) in enumerate(zip(lines, per_line), 1):
        at = f"{name}:{k}"
        if line != line.rstrip(" ") and not (line.endswith("Pause ") or line.endswith('"')):
            # "Pause " legitimately ends in a space (that is the token's name)
            if not re.search(r"(Pause |Disp |Input |Prompt |Lbl |Goto |If |While |Repeat |DelVar |Fix ) *$", line):
                warns.append(f"{at}: trailing space")
        if line.strip() == "":
            errs.append(f"{at}: blank line (on the calculator it is an empty statement that a false If skips)")
        if ":" in line:
            errs.append(f"{at}: ':' is not allowed (one statement per line; no colons in strings)")
        if "\t" in line:
            errs.append(f"{at}: tab character")
        for t, in_str in lt:
            d = disp(t)
            if type(t).__name__ == "IllegalToken":
                errs.append(f"{at}: illegal token {t.bits.hex()}")
                continue
            if in_str:
                if len(d) != 1 or d in ':"→…':
                    errs.append(f"{at}: string contains multi-glyph or reserved token {d!r} ({t.bits.hex()})")
                if d.isalpha() and d.islower():
                    errs.append(f"{at}: lowercase letter {d!r} in string (use uppercase)")
            else:
                if d not in CODE_TOKENS:
                    errs.append(f"{at}: token {d!r} ({t.bits.hex()}) is not in the supported command set")
        # variable use (code only): R,T,X,Y,θ may appear only inside program/list names
        if not line.startswith(("Lbl ", "Goto ", "Menu(")):
            skip = 0
            for t, s in lt:
                d = disp(t)
                if s:
                    continue
                if d in ("prgm",):
                    skip = 8
                    continue
                if d == "ʟ":
                    skip = 5
                    continue
                if skip and (d.isupper() or d.isdigit() or d == "θ") and len(d) == 1:
                    skip -= 1
                    continue
                skip = 0
                if d in FORBIDDEN_VARS:
                    errs.append(f"{at}: uses variable {d} (R,T,X,Y,θ are reserved; never use them)")
        if line.startswith(("Lbl ", "Goto ")) and any(c in FORBIDDEN_VARS for c in line.split(" ", 1)[1]):
            errs.append(f"{at}: label names must not contain R,T,X,Y,θ")
        # labels
        m = re.match(r"^Lbl (.*)$", line)
        if m:
            lab = m.group(1)
            if not LABEL_RE.match(lab):
                errs.append(f"{at}: bad label name {lab!r}")
            if lab in labels:
                errs.append(f"{at}: duplicate label {lab!r} (first at line {labels[lab]})")
            labels.setdefault(lab, k)
        m = re.match(r"^Goto (.*)$", line)
        if m and not LABEL_RE.match(m.group(1)):
            errs.append(f"{at}: bad Goto target {m.group(1)!r}")
        for m in re.finditer(r"prgm([A-Z0-9θ]*)", line):
            pn = m.group(1)
            if not NAME_RE.match(pn):
                errs.append(f"{at}: bad program name after prgm: {pn!r}")
            elif pn not in all_names:
                errs.append(f"{at}: calls prgm{pn}, which has no source file")
        if name.startswith("Z") and line == "Stop":
            errs.append(f"{at}: Stop is not allowed in a subprogram (use Return)")
        # screen widths
        lits = list(string_literals(lt))
        if "" in lits and line != 'Disp ""':
            errs.append(f"{at}: empty string literal (only 'Disp \"\"' for a blank row is allowed)")
        if line.startswith("Disp "):
            for s in lits:
                if len(s) > SCREEN_W:
                    errs.append(f"{at}: Disp string is {len(s)} chars (> {SCREEN_W}): {s!r}")
        if line.startswith("Input ") and lits:
            if len(lits[0]) > PROMPT_W:
                errs.append(f"{at}: Input prompt is {len(lits[0])} chars (> {PROMPT_W}): {lits[0]!r}")
        if line.startswith("Menu("):
            inner = line[len("Menu("):]
            if inner.endswith(")"):
                inner = inner[:-1]
            args = split_args(inner)
            if len(args) % 2 != 1:
                errs.append(f"{at}: Menu( needs a title plus text,label pairs")
            else:
                title = args[0].strip('"')
                opts = [(args[i].strip('"'), args[i + 1]) for i in range(1, len(args), 2)]
                if len(title) > SCREEN_W:
                    errs.append(f"{at}: Menu title is {len(title)} chars (> {SCREEN_W})")
                if len(opts) > MENU_MAX:
                    errs.append(f"{at}: Menu has {len(opts)} options (> {MENU_MAX})")
                for txt, lab in opts:
                    if len(txt) > MENU_ITEM_W:
                        errs.append(f"{at}: Menu item {txt!r} is {len(txt)} chars (> {MENU_ITEM_W})")
                    if not LABEL_RE.match(lab):
                        errs.append(f"{at}: bad Menu label {lab!r}")
                if not any(re.search(r"BACK|QUIT|EXIT", t) for t, _ in opts):
                    errs.append(f"{at}: Menu has no BACK/QUIT option")
    # every Goto / Menu label must exist
    for k, line in enumerate(lines, 1):
        targets = []
        m = re.match(r"^Goto (.*)$", line)
        if m:
            targets.append(m.group(1))
        if line.startswith("Menu("):
            inner = line[len("Menu("):].rstrip(")")
            args = split_args(inner)
            targets += [args[i + 1] for i in range(1, len(args) - 1, 2)]
        for tg in targets:
            if tg not in labels:
                errs.append(f"{name}:{k}: jump to missing label {tg!r}")
    return errs, warns


def build_program(name, raw, all_names, target, src_label, write):
    """Tokenize, lint, save, re-open, detokenize and diff one program. Returns (row, errors, warnings)."""
    failures = []
    if "\r" in raw:
        return None, [f"{src_label}: CRLF line endings"], []
    if not raw.endswith("\n") or raw.endswith("\n\n"):
        return None, [f"{src_label}: file must end with exactly one newline"], []
    text = raw[:-1]
    try:
        toks, per_line = tokenize_program(text, name)
    except BuildError as e:
        return None, [str(e)], []
    errs, warns = lint(name, text, per_line, all_names)
    failures += errs
    prog = TIProgram(name=name)
    prog.load_tokens(toks)
    if write:
        target.parent.mkdir(parents=True, exist_ok=True)
        prog.save(str(target))
        reopened = TIProgram.open(str(target))
    else:
        reopened = prog
    # round trip: detokenize what is on disk and diff with the source text
    back = reopened.string()
    if write:
        RT.mkdir(parents=True, exist_ok=True)
        (RT / f"{name}.txt").write_text(back + "\n", encoding="utf-8")
    diff = list(difflib.unified_diff(text.split("\n"), back.split("\n"),
                                     src_label, f"detokenized {target.name}", lineterm=""))
    if diff:
        failures.append(f"{name}: ROUND-TRIP MISMATCH\n" + "\n".join(diff[:40]))
    # re-tokenizing the detokenized text must give identical bytes
    toks2, _ = tokenize_program(back, name)
    if b"".join(t.bits for t in toks2) != reopened.data:
        failures.append(f"{name}: re-tokenizing the detokenized text gives different bytes")
    if reopened.name != name:
        failures.append(f"{name}: var name in file is {reopened.name!r}")
    if len(reopened.data) > MAX_PROGRAM_BYTES:
        failures.append(f"{name}: {len(reopened.data)} bytes is over the {MAX_PROGRAM_BYTES}-byte program limit")
    # informational: compare with tivars' default "smart" tokenization of the same text
    smart = TIProgram(name=name)
    try:
        smart.load_string(text)
        smart_same = smart.data == reopened.data
    except Exception:
        smart_same = False
    sha = hashlib.sha256(target.read_bytes()).hexdigest()[:16] if write else "-"
    n_lines = text.count("\n") + 1
    mos = reopened.get_min_os()
    row = (name, n_lines, len(toks), len(reopened.data), target.stat().st_size if write else 0,
           "identical" if not diff else "DIFF", "same" if smart_same else "differs", sha,
           f"{mos.model} {mos.version}")
    return row, failures, warns


def build(write=True, only=None):
    srcs = sorted(SRC.glob("*.txt"))
    if not srcs:
        raise BuildError(f"no sources in {SRC}")
    all_names = {p.stem for p in srcs}
    if only:
        srcs = [p for p in srcs if p.stem in only]
    report, failures, all_warns = [], [], []
    for path in srcs:
        name = path.stem
        if not NAME_RE.match(name):
            failures.append(f"{path.name}: program name must be 1-8 chars, A-Z/0-9, starting with a letter")
            continue
        row, errs, warns = build_program(name, path.read_text(encoding="utf-8"), all_names,
                                         OUT / f"{name}.8xp", f"src/{name}.txt", write)
        failures += errs
        all_warns += warns
        if row:
            report.append(row)

    # the deliverable: every module merged into the single program PHYSICS
    if not only or SINGLE in only:
        from merge import merge
        text = merge(SRC)
        if write:
            SINGLE_TXT.write_text(text, encoding="utf-8")
        row, errs, warns = build_program(SINGLE, text, {SINGLE}, SINGLE_8XP, f"{SINGLE}.txt", write)
        failures += errs
        all_warns += warns
        if row:
            report.append(row)

    lines = ["# Round-trip report", "",
             "Each `.8xp` was re-opened from disk, detokenized with tivars_lib_py, and diffed",
             "against its source text (`src/<NAME>.txt` for the modules, `PHYSICS.txt` for the merged",
             "program). `identical` means the diff is empty. The detokenized text is in `build/roundtrip/`.",
             "", "**`PHYSICS.8xp` is the file to send.** The module builds in `build/modules/` are what the",
             "test-suites exercise one by one.", "",
             "| Program | Lines | Tokens | Program bytes | .8xp file bytes | Round-trip diff | tivars smart-mode bytes | sha256 (16) | Min OS |",
             "|---|---|---|---|---|---|---|---|---|"]
    for r in report:
        lines.append("| " + " | ".join(str(x) for x in r) + " |")
    lines += ["", "`tivars smart-mode bytes` compares against `TIProgram.load_string(text)` with the default",
              "\"smart\" mode. Where it says `differs`, smart mode turned a `\"...\"→StrN` store into the letters",
              "S,t,r,N (a tokenizer quirk), which is why build.py tokenizes code and strings separately.", ""]
    if write and not only:
        REPORT.write_text("\n".join(lines), encoding="utf-8")
    return report, failures, all_warns


def main():
    write = "--check" not in sys.argv
    only = None
    if "--only" in sys.argv:
        only = set(sys.argv[sys.argv.index("--only") + 1].split(","))
    try:
        report, failures, warns = build(write, only)
    except BuildError as e:
        print("BUILD ERROR:", e)
        return 1
    for w in warns:
        print("warning:", w)
    for r in report:
        print(f"{r[0]:9} lines={r[1]:4} tokens={r[2]:5} bytes={r[3]:6} file={r[4]:6} roundtrip={r[5]} smart={r[6]}")
    if failures:
        print(f"\n{len(failures)} PROBLEM(S):")
        for f in failures:
            print(" -", f)
        return 1
    print(f"\nOK: {len(report)} programs built, linted, and round-tripped with no differences.")
    if not only:
        print(f"Send this one file to the calculator: {SINGLE_8XP.relative_to(ROOT.parent)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
