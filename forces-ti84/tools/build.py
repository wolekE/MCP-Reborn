#!/usr/bin/env python3
"""Build FORCES for the TI-84 Plus (monochrome) and the TI-84 Plus CE.

    python3 tools/build.py

For each calculator this script
  1. expands tools/forces.tpl into plain TI-BASIC (screen layout, inputs),
  2. lints it for the TI-BASIC pitfalls listed in README.md,
  3. tokenizes it with tivars_lib_py (pip install tivars) into FORCES.8xp,
  4. reloads the .8xp, detokenizes it and checks it matches FORCES.txt exactly,
  5. audits every token (no stray lowercase-letter tokens, OS version limits).
Any problem stops the build with a message.
"""

import os
import re
import sys

from tivars.models import TI_84P, TI_84PCE
from tivars.tokenizer import decode, encode
from tivars.types import TIProgram

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TEMPLATE = os.path.join(HERE, "forces.tpl")

PROFILES = {
    # label: longest answer label + unit that still leaves room for a
    # num-character number, e.g. "MGSINθ=1234.56 N" on the 16-column screen
    "mono": dict(folder="TI-84_Plus", model=TI_84P, cols=16, rows=8,
                 row1=15, menu_opt=14, label=7, num=7),
    "ce": dict(folder="TI-84_Plus_CE", model=TI_84PCE, cols=26, rows=10,
               row1=26, menu_opt=24, label=15, num=9),
}

# Characters allowed inside string literals (uppercase only, keypad glyphs).
STRING_CHARS = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 +-*/=<>(),.?!:≤≥≠θ²⁻")
ALLOWED_VARS = set("ABCDEFGHIJKLMNOPQRSTUVWXYZθ") | {f"Str{i}" for i in range(1, 10)}
LABEL_RE = re.compile(r"^[A-Z0-9θ]{1,2}$")


# Mono only: upper bound on the printed length of X (minus one), stored once
# in Str9 so each answer row can place its unit right after the number with
# Output(row,col+expr(Str9),"UNIT").  The string holds function tokens, so this
# one line is tokenized with maximal munch.
UNIT_COL = ("2+(X<0)+int(log(max(1,abs(X))))-(0<abs(X) and abs(X)<1)"
            "+(fPart(X)≠0)(2+(fPart(10X)≠0)+(fPart(100X)≠0))")
UNIT_COL_LINE = f'"{UNIT_COL}"→Str9'


class BuildError(Exception):
    pass


# ------------------------------------------------------------------ expand
def resolve_alternatives(line, profile):
    pick = 0 if profile == "mono" else 1
    return re.sub(r"\{([^{}|]*)\|([^{}]*)\}",
                  lambda m: m.group(1 + pick), line)


def split_fields(body, n):
    parts = body.split(";")
    if len(parts) != n:
        raise BuildError(f"expected {n} ';' fields: {body!r}")
    return [p.strip() for p in parts]


def expand_input(body):
    """Validated Input.  The variable is first set to a failing value (field 5,
    default ⁻1) so a blank ENTER that leaves it unchanged is asked again."""
    fields = body.split(";")
    if len(fields) == 4:
        fields.append("⁻1")
    var, prompt, cond, err, bad = split_fields(";".join(fields), 5)
    out = [f"{bad}→{var}", f"Repeat {cond}", f'Input "{prompt}",{var}']
    if err:
        out += [f"If not({cond})", f'Disp "{err}"']
    return out + ["End"]


def expand_optional(body):
    var, prompt, cond, err = split_fields(body, 4)
    ask = ['"0"→Str8', f'Input "{prompt}",Str8', "If not(length(Str8))",
           '"0"→Str8', f"expr(Str8)→{var}"]
    if cond == "1":
        return ask
    out = [f"Repeat {cond}"] + ask
    if err:
        out += [f"If not({cond})", f'Disp "{err}"']
    return out + ["End"]


def value_lines(row, label, unit, expr, p, profile):
    """Lines that show LABEL=round(expr,3) UNIT on one row."""
    budget = p["label"] - len(unit)
    if len(label) > budget:
        raise BuildError(f"label {label!r} too long for unit {unit!r} "
                         f"(max {budget} so a {p['num']}-character number fits)")
    if profile == "ce":
        tail = f'+" {unit}"' if unit else ""
        return [f'Output({row},1,"{label}="+toString(round({expr},3),1){tail})']
    col = len(label) + 2                  # first column of the number
    out = [f"round({expr},3)→X", f'Output({row},1,"{label}=")']
    if unit:
        width = p["row1"] if row == 1 else p["cols"]   # pause indicator
        last = width + 1 - len(unit)
        if len(label) + len(unit) > 6:
            # long label: a value of 1000 or more with decimals would push
            # the unit off the row, so show it as a whole number instead
            out += [f"If {col}+expr(Str9)>{last}", "round(X,0)→X"]
        # unit first: a number too long for the row overwrites the unit,
        # never the other way round
        out.append(f'Output({row},min({last},{col}+expr(Str9)),"{unit}")')
    return out + [f"Output({row},{col},X)"]


def layout_screen(items, p, profile):
    pages, page = [], []
    for kind, arg in items:
        if kind == "BR":
            if page:
                pages.append(page)
                page = []
            continue
        if len(page) == p["rows"]:
            pages.append(page)
            page = []
        page.append((kind, arg))
    if page:
        pages.append(page)
    out = []
    for page in pages:
        if p["row1"] < p["cols"] and page[0][0] == "V":
            raise BuildError("a mono page must not start with a value row "
                             "(the pause indicator covers row 1, column 16)")
        out.append("ClrHome")
        for row, (kind, arg) in enumerate(page, start=1):
            if kind == "T":
                out.append(f'Output({row},1,"{arg}")')
            elif kind == "S":
                out.append(f"Output({row},1,{arg})")
            else:
                label, unit, expr = split_fields(arg, 3)
                out += value_lines(row, label, unit, expr, p, profile)
        out.append("Pause ")
    return out


def expand(profile):
    p = PROFILES[profile]
    out, screen = [], None
    with open(TEMPLATE, encoding="utf-8") as fh:
        raw = fh.read().splitlines()
    for n, line in enumerate(raw, start=1):
        line = line.rstrip()
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        line = resolve_alternatives(line, profile)
        for tag in ("@MONO ", "@CE "):
            if line.startswith(tag):
                if (tag == "@MONO ") != (profile == "mono"):
                    line = None
                else:
                    line = line[len(tag):]
                break
        if line is None:
            continue
        try:
            if screen is not None:
                if line == "@END":
                    out += layout_screen(screen, p, profile)
                    screen = None
                elif line in ("@BR", "@MBR", "@CBR"):
                    if line == "@BR" or (line == "@MBR") == (profile == "mono"):
                        screen.append(("BR", None))
                elif line[:3] in ("@T ", "@S ", "@V "):
                    screen.append((line[1], line[3:]))
                else:
                    raise BuildError("unknown screen item")
            elif line == "@SCREEN":
                screen = []
            elif line == "@UNITCOL":
                if profile == "mono":
                    out.append(UNIT_COL_LINE)
            elif line.startswith("@IN "):
                out += expand_input(line[4:])
            elif line.startswith("@OPT "):
                out += expand_optional(line[5:])
            elif line.startswith("@"):
                raise BuildError("unknown directive")
            else:
                out.append(line)
        except BuildError as e:
            raise BuildError(f"forces.tpl:{n}: {e}: {line!r}") from None
    if screen is not None:
        raise BuildError("unterminated @SCREEN")
    return out


# -------------------------------------------------------------------- lint
def strings_in(line):
    return re.findall(r'"([^"]*)"', line)


def outside_strings(line):
    return re.sub(r'"[^"]*"', '""', line)


def lint(lines, profile):
    p = PROFILES[profile]
    errors = []

    def err(i, msg):
        errors.append(f"{profile} line {i + 1}: {msg}: {lines[i]!r}")

    labels, targets = {}, []
    depth, prev_single_if = 0, False
    for i, line in enumerate(lines):
        code = outside_strings(line)
        if line.count('"') % 2:
            err(i, "unbalanced quote")
        if code.count("(") != code.count(")"):
            err(i, "unbalanced parentheses")
        if ":" in code:
            err(i, "colon-chained statements (keep one per line)")
        if "{" in code or "[" in code or "⌊" in code or "L₁" in code:
            err(i, "list/matrix syntax is not allowed")
        for s in strings_in(line if line != UNIT_COL_LINE else ""):
            bad = set(s) - STRING_CHARS
            if bad:
                err(i, f"string has disallowed characters {sorted(bad)}")
        # variables: every capital letter / Str / θ outside strings and keywords
        names = re.sub(r"(Lbl|Goto) \S+", "", code)
        names = re.sub(r"Menu\(.*", "", names)
        for kw in ("ClrHome", "Disp ", "Input ", "Output(", "If ", "Then", "Else",
                   "End", "Repeat ", "While ", "For(", "Pause ", "Degree",
                   "Radian", "Float", "Normal", "Full", "Stop"):
            names = names.replace(kw, " ")
        for v in re.findall(r"Str\d|[A-Zθ]", names):
            if v not in ALLOWED_VARS:
                err(i, f"variable {v} not allowed")
        # structure
        is_single_if_body = prev_single_if
        prev_single_if = False
        if line.startswith("If "):
            nxt = lines[i + 1] if i + 1 < len(lines) else ""
            if nxt != "Then":
                prev_single_if = True
                if nxt.startswith(("Goto", "Menu(", "Lbl", "End", "Else",
                                   "Repeat", "While", "For(", "If ")):
                    err(i + 1, "single-line If body must be a plain statement")
        if line == "Then":
            if i == 0 or not lines[i - 1].startswith("If "):
                err(i, "Then without If")
            depth += 1
        elif line.startswith(("Repeat ", "While ", "For(")):
            depth += 1
        elif line == "End":
            depth -= 1
            if depth < 0:
                err(i, "End without block")
                depth = 0
        if line.startswith(("Goto ", "Menu(", "Lbl ")):
            if depth:
                err(i, "Lbl/Goto/Menu( inside a block (memory leak risk)")
            if is_single_if_body:
                err(i, "conditional jump")
        if line.startswith("Lbl "):
            name = line[4:]
            if not LABEL_RE.match(name):
                err(i, "bad label name")
            if name in labels:
                err(i, "duplicate label")
            labels[name] = i
        elif line.startswith("Goto "):
            targets.append((i, line[5:]))
        elif line.startswith("Menu("):
            parts = [a.strip('"') for a in
                     re.findall(r'"[^"]*"|[^,]+', line[5:-1])]
            title, rest = parts[0], parts[1:]
            if len(rest) % 2 or not rest:
                err(i, "Menu( arguments must be text,label pairs")
            opts = rest[0::2]
            if len(opts) > 7:
                err(i, "Menu( has more than 7 options")
            if len(title) > p["cols"]:
                err(i, f"menu title longer than {p['cols']}")
            for o in opts:
                if len(o) > p["menu_opt"]:
                    err(i, f"menu option {o!r} longer than {p['menu_opt']}")
            targets += [(i, t) for t in rest[1::2]]
        elif line.startswith("Disp "):
            first_row = i > 0 and lines[i - 1] == "ClrHome"
            width = p["row1"] if first_row else p["cols"]
            for s in strings_in(line):
                if len(s) > width:
                    err(i, f"Disp text longer than {width}"
                           + (" (row 1: pause indicator)" if first_row else ""))
        elif line.startswith("Input "):
            prompt = strings_in(line)[0]
            if len(prompt) > p["cols"] - 3:
                err(i, f"Input prompt leaves no room (>{p['cols'] - 3})")
        elif line.startswith("Output("):
            m = re.match(r'Output\((\d+),(\d+),"([^"]*)"\)$', line)
            if m:
                row, col, text = int(m[1]), int(m[2]), m[3]
                width = p["row1"] if row == 1 else p["cols"]
                if col + len(text) - 1 > width:
                    err(i, f"Output text runs past column {width}")
    if depth:
        errors.append(f"{profile}: {depth} block(s) never closed")
    for i, t in targets:
        if t not in labels:
            err(i, f"jump to missing label {t}")
    used = {t for _, t in targets}
    for name, i in labels.items():
        if name not in used:
            err(i, "label is never used")
    return errors


# ---------------------------------------------------------------- tokenize
LOWERCASE_TOKENS = {bytes([0xBB, b]) for b in range(0xB0, 0xCB)} | \
                   {bytes([0xBB, b]) for b in range(0xCB, 0xD5)}


def tokenize_and_check(source, profile):
    p = PROFILES[profile]
    trie = p["model"].tokens.tries[None]
    data = b"\x3f".join(
        encode(line, trie=trie, mode="max" if line == UNIT_COL_LINE else "smart")[0]
        for line in source.split("\n"))
    prog = TIProgram(name="FORCES")
    prog.load_tokens(decode(data)[0])
    folder = os.path.join(ROOT, p["folder"])
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, "FORCES.8xp")
    prog.export(model=p["model"]).save(path)

    back = TIProgram.open(path)
    if back.string() != source:
        raise BuildError(f"{profile}: .8xp does not detokenize to the source")
    if back.name != "FORCES":
        raise BuildError(f"{profile}: program name is {back.name!r}")
    tokens = decode(back.data)[0]
    used = {}
    for t in tokens:
        if t.bits in LOWERCASE_TOKENS:
            raise BuildError(f"{profile}: lowercase-letter token {t.bits.hex()} "
                             "(a command was misspelled and tokenized as letters)")
        used[t.bits] = t.langs["en"].display
    min_os = back.get_min_os()
    if profile == "mono" and min_os.model.startswith("TI-84+CE"):
        raise BuildError(f"{profile}: needs {min_os}, not a monochrome TI-84 Plus")
    return path, len(back.data), min_os, used


def main():
    report = []
    for profile, p in PROFILES.items():
        lines = expand(profile)
        problems = lint(lines, profile)
        if problems:
            print("\n".join(problems))
            raise SystemExit(f"lint failed for {profile}")
        source = "\n".join(lines)
        path, size, min_os, used = tokenize_and_check(source, profile)
        txt = os.path.join(ROOT, p["folder"], "FORCES.txt")
        with open(txt, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(source + "\n")
        with open(txt, encoding="utf-8") as fh:
            if fh.read().rstrip("\n") != TIProgram.open(path).string():
                raise BuildError(f"{profile}: FORCES.txt does not match .8xp")
        report.append(f"{p['folder']}: {len(lines)} lines, {size} bytes, "
                      f"{len(used)} distinct tokens, needs {min_os.model} "
                      f"OS {min_os.version}+ -> {os.path.relpath(path, ROOT)}")
    print("\n".join(report))


if __name__ == "__main__":
    try:
        main()
    except BuildError as e:
        sys.exit(f"BUILD FAILED: {e}")
