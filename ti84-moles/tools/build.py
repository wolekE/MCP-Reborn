"""Build .8xp files from the TI-BASIC token-name sources and lint them for TI-84 Plus pitfalls.

Usage:  python3 tools/build.py            (builds MOLES and FORMBKEY next to their .txt sources)
"""

import pathlib
import sys

from tivars.models import TI_84P
from tivars.types import TIProgram

ROOT = pathlib.Path(__file__).resolve().parent.parent
PROGRAMS = ["MOLES", "FORMBKEY"]

# The oldest monochrome OS we want to support: TI-84 Plus 2.43 (no CE-only tokens such as toString( or eval().
MAX_OS = TI_84P.OS("2.43")

MONO_WIDTH = 16


def token_lines(prog):
    """Split the token stream into source lines (newline token 0x3F) of display names."""
    lines, cur = [], []
    for tok in prog.tokens():
        if tok.bits == b"\x3f":
            lines.append(cur)
            cur = []
        else:
            cur.append(tok)
    lines.append(cur)
    return lines


def name(tok):
    return tok.langs["en"].display


def split_statements(line):
    """Split a token line on ':' outside string literals. Returns lists of tokens."""
    stmts, cur, in_str = [], [], False
    for tok in line:
        n = name(tok)
        if n == '"':
            in_str = not in_str
        elif n == "→" and in_str:
            in_str = False  # the calculator closes a string at the store arrow
        if n == ":" and not in_str:
            stmts.append(cur)
            cur = []
        else:
            cur.append(tok)
    stmts.append(cur)
    return [s for s in stmts if s]


def string_literals(stmt):
    """Yield the token-name lists of every string literal in a statement."""
    i, names = 0, [name(t) for t in stmt]
    while i < len(names):
        if names[i] == '"':
            j = i + 1
            while j < len(names) and names[j] not in ('"', "→"):
                j += 1
            yield names[i + 1:j]
            i = j + 1 if j < len(names) and names[j] == '"' else j
        else:
            i += 1


def split_args(names):
    """Split a token-name list on top-level commas (outside strings and brackets)."""
    args, cur, depth, in_str = [], [], 0, False
    for n in names:
        if n == '"':
            in_str = not in_str
        if not in_str:
            if n.endswith("(") or n in ("{", "["):
                depth += 1
            elif n in (")", "}", "]"):
                depth -= 1
            elif n == "," and depth == 0:
                args.append(cur)
                cur = []
                continue
        cur.append(n)
    args.append(cur)
    return args


def lint(prog_name, lines):
    errors, warnings = [], []
    labels, gotos = {}, []
    depth_stack = []
    for lineno, line in enumerate(lines, 1):
        stmts = split_statements(line)
        prev_was_if = False
        for stmt in stmts:
            names = [name(t) for t in stmt]
            first = names[0]
            # → inside a string literal silently ends the string on the calculator
            raw, in_str = names, False
            for k, n in enumerate(raw):
                if n == '"':
                    in_str = not in_str
                elif n == "→" and in_str and k + 1 < len(raw) and raw[k + 1] != '"':
                    if any(x == '"' for x in raw[k + 1:]):
                        errors.append(f"{prog_name}:{lineno}: store arrow inside a string literal")
                    in_str = False
            if first == "Lbl ":
                lbl = "".join(names[1:])
                if lbl in labels:
                    errors.append(f"{prog_name}:{lineno}: duplicate label {lbl}")
                labels[lbl] = lineno
            elif first == "Goto ":
                gotos.append((lineno, "".join(names[1:])))
            elif first == "Menu(":
                args = split_args(names[1:])
                if args and args[-1] and args[-1][-1] == ")":
                    args[-1] = args[-1][:-1]
                title, rest = args[0], args[1:]
                if len(rest) % 2 or not 1 <= len(rest) // 2 <= 7:
                    errors.append(f"{prog_name}:{lineno}: Menu( needs 1-7 text/label pairs")
                ttl = [n for n in title if n != '"']
                if len(ttl) > 16:
                    errors.append(f"{prog_name}:{lineno}: Menu title longer than 16")
                for k in range(0, len(rest), 2):
                    txt = [n for n in rest[k] if n != '"']
                    if len(txt) > 14:
                        warnings.append(f"{prog_name}:{lineno}: Menu item '{''.join(txt)}' longer than 14")
                    gotos.append((lineno, "".join(rest[k + 1])))
            elif first in ("Disp ", "Pause "):
                for lit in string_literals(stmt):
                    if len(lit) > MONO_WIDTH:
                        errors.append(f"{prog_name}:{lineno}: {first.strip()} literal wider than {MONO_WIDTH}: {''.join(lit)}")
            elif first == "Input ":
                for lit in string_literals(stmt):
                    if len(lit) > 12:
                        warnings.append(f"{prog_name}:{lineno}: Input prompt '{''.join(lit)}' leaves < 4 columns on a TI-84 Plus")
            # block structure
            if first in ("For(", "While ", "Repeat "):
                depth_stack.append((first, lineno))
            elif first == "Then":
                if not prev_was_if:
                    errors.append(f"{prog_name}:{lineno}: Then without If")
                depth_stack.append(("Then", lineno))
            elif first == "Else":
                if not depth_stack or depth_stack[-1][0] != "Then":
                    errors.append(f"{prog_name}:{lineno}: Else outside If-Then")
            elif first == "End":
                if not depth_stack:
                    errors.append(f"{prog_name}:{lineno}: End without block")
                else:
                    depth_stack.pop()
            elif first in ("Lbl ",) and depth_stack:
                warnings.append(f"{prog_name}:{lineno}: label inside an open block")
            prev_was_if = first == "If "
            # A single-line If swallows the next statement; a Then must follow an If directly.
    for opener, lineno in depth_stack:
        errors.append(f"{prog_name}:{lineno}: {opener.strip()} never closed")
    for lineno, lbl in gotos:
        if lbl not in labels:
            errors.append(f"{prog_name}:{lineno}: jump to missing label {lbl}")
    return errors, warnings


def build(prog_name):
    src_path = ROOT / f"{prog_name}.txt"
    text = src_path.read_text(encoding="utf-8").rstrip("\n")
    prog = TIProgram(name=prog_name)
    prog.load_string(text, model=TI_84P)

    min_os = prog.get_min_os()
    errors, warnings = lint(prog_name, token_lines(prog))
    if not min_os <= MAX_OS:
        errors.append(f"{prog_name}: needs OS {min_os}, newer than {MAX_OS}")

    # Round trip: the decoded text must match the source exactly (catches mis-tokenised names).
    if prog.string(model=TI_84P) != text:
        a, b = prog.string(model=TI_84P).splitlines(), text.splitlines()
        for i, (x, y) in enumerate(zip(a, b), 1):
            if x != y:
                errors.append(f"{prog_name}:{i}: round-trip mismatch\n  src: {y}\n  got: {x}")
                break

    out = ROOT / f"{prog_name}.8xp"
    prog.save(str(out), model=TI_84P)
    size = len(prog.data)
    print(f"{prog_name}: {len(text.splitlines())} lines, {size} bytes of tokens, min OS {min_os} -> {out.name}")
    for w in warnings:
        print("  warning:", w)
    for e in errors:
        print("  ERROR:", e)
    return not errors


if __name__ == "__main__":
    names = sys.argv[1:] or PROGRAMS
    ok = all([build(n) for n in names if (ROOT / f"{n}.txt").exists()])
    sys.exit(0 if ok else 1)
