#!/usr/bin/env python3
"""
Build HPC2HELP.8xp from HPC2HELP.txt with tivars (TI-Toolkit's tivars_lib_py,
https://github.com/TI-Toolkit/tivars_lib_py, `pip install tivars`).

The source file has one TI-BASIC statement per line, written with the token
names the calculator / TI Connect CE display (Disp, ClrHome, →, ►Frac, ≠ ...).

Both code and quoted text are tokenized here from explicit whitelists
(longest match first), so every byte in the program comes from a table that
is listed below and cross-checked against the TI-Toolkit token sheet that
ships with tivars.  Nothing is left to a general-purpose tokenizer: tivars'
ASCII shortcuts ("->", ">=", "L1", "[A]" ...) can never turn display text into
a different token, and a command can never be silently spelled out as letters
(e.g. "Pause" as P,a,u,s,e, which displays the same but is ERR:SYNTAX).
Every line is then decoded by tivars and must read back exactly as written.

Usage:  python build_8xp.py [source.txt] [output.8xp]
"""

import sys
from pathlib import Path

from tivars.tokenizer import decode, encode
from tivars.models import TI_84P
from tivars.types import TIProgram
from tivars.var import TIHeader

HERE = Path(__file__).resolve().parent
DEFAULT_SRC = HERE.parent / "HPC2HELP.txt"
DEFAULT_OUT = HERE.parent / "HPC2HELP.8xp"
PROGRAM_NAME = "HPC2HELP"

# Multi-character glyphs that are a single token on the calculator.
STRING_MULTI = {
    "³√(": b"\xBD",  # MATH 4
    "√(": b"\xBC",   # 2nd x²
    "⁻¹": b"\x0C",   # x⁻¹ key
}

# Single characters allowed inside strings (all typeable on a TI-84 keypad).
STRING_SINGLE = {}
for ch in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
    STRING_SINGLE[ch] = bytes([ord(ch)])
for ch in "0123456789":
    STRING_SINGLE[ch] = bytes([ord(ch)])
STRING_SINGLE.update({
    " ": b"\x29", "(": b"\x10", ")": b"\x11", ",": b"\x2B", ".": b"\x3A",
    "+": b"\x70", "-": b"\x71", "*": b"\x82", "/": b"\x83", "^": b"\xF0",
    "=": b"\x6A", "<": b"\x6B", ">": b"\x6C", "≤": b"\x6D", "≥": b"\x6E",
    "≠": b"\x6F", "?": b"\xAF", "[": b"\x06", "]": b"\x07",
    "²": b"\x0D", "³": b"\x0F",
})


def tokenize_string_body(body: str, where: str) -> bytes:
    out = b""
    i = 0
    while i < len(body):
        for glyph, tok in STRING_MULTI.items():
            if body.startswith(glyph, i):
                out += tok
                i += len(glyph)
                break
        else:
            ch = body[i]
            if ch not in STRING_SINGLE:
                raise ValueError(f"{where}: character {ch!r} is not allowed inside a string")
            out += STRING_SINGLE[ch]
            i += 1
    return out


# Every token allowed outside quotes, with its byte value.
CODE_TOKENS = {
    # commands
    "Disp ": b"\xDE", "Input ": b"\xDC", "Output(": b"\xE0", "ClrHome": b"\xE1",
    "Pause": b"\xD8", "Lbl ": b"\xD6", "Goto ": b"\xD7", "Menu(": b"\xE6",
    "If ": b"\xCE", "Then": b"\xCF", "Else": b"\xD0", "End": b"\xD4", "Stop": b"\xD9",
    "Float": b"\x69", "Normal": b"\x66",
    # functions
    "abs(": b"\xB2", "fPart(": b"\xBA", "gcd(": b"\xBB\x09", "min(": b"\x1A",
    "max(": b"\x19", "not(": b"\xB8",
    # operators and punctuation
    " and ": b"\x40", " or ": b"\x3C", " xor ": b"\x3D", "►Frac": b"\x03", "→": b"\x04",
    "⁻": b"\xB0", "+": b"\x70", "-": b"\x71", "*": b"\x82", "/": b"\x83",
    "=": b"\x6A", "<": b"\x6B", ">": b"\x6C", "≤": b"\x6D", "≥": b"\x6E", "≠": b"\x6F",
    "(": b"\x10", ")": b"\x11", ",": b"\x2B", ".": b"\x3A", "ᴇ": b"\x3B",
}
for _ch in "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ":
    CODE_TOKENS[_ch] = bytes([ord(_ch)])
# tivars shows the Pause token as "Pause " (trailing space); lines never end in a space.
DISPLAY_ALIAS = {"Pause ": "Pause"}


def _check_tables():
    """Every table entry must decode, per the TI-Toolkit token sheet, to its own name."""
    for table in (CODE_TOKENS, STRING_MULTI, STRING_SINGLE):
        for name, tok in table.items():
            toks = decode(tok)[0]
            shown = "".join(t.langs["en"].display for t in toks)
            if len(toks) != 1 or DISPLAY_ALIAS.get(shown, shown) != name:
                raise AssertionError(f"token table entry {name!r} -> {tok.hex()} decodes as {shown!r}")


def tokenize_code(code: str, where: str) -> bytes:
    out = b""
    i = 0
    names = sorted(CODE_TOKENS, key=len, reverse=True)
    while i < len(code):
        for name in names:
            if code.startswith(name, i):
                out += CODE_TOKENS[name]
                i += len(name)
                break
        else:
            raise ValueError(f"{where}: cannot tokenize {code[i:]!r} (not in the allowed token list)")
    return out


def tokenize_line(line: str, where: str) -> bytes:
    """Tokenize one statement: code and quoted text each from their whitelist."""
    out = b""
    rest = line
    while rest:
        q = rest.find('"')
        if q < 0:
            out += tokenize_code(rest, where)
            break
        out += tokenize_code(rest[:q], where)
        rest = rest[q + 1:]
        end = rest.find('"')
        if end < 0:
            raise ValueError(f"{where}: unterminated string (every string must be closed)")
        body, rest = rest[:end], rest[end + 1:]
        out += b"\x2A" + tokenize_string_body(body, where) + b"\x2A"
    return out


def display(data: bytes) -> str:
    shown = "".join(tok.langs["en"].display for tok in decode(data)[0])
    return DISPLAY_ALIAS.get(shown, shown)


def build(src: Path, out: Path) -> bytes:
    _check_tables()
    lines = src.read_text(encoding="utf-8").split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    chunks = []
    for n, line in enumerate(lines, 1):
        where = f"{src.name}:{n}"
        if line != line.strip():
            raise ValueError(f"{where}: leading/trailing whitespace is not allowed")
        if not line:
            raise ValueError(f"{where}: empty line")
        data = tokenize_line(line, where)
        if b"\x3F" in data or b"\x3E" in data:
            raise ValueError(f"{where}: statement contains a newline/colon token")
        back = display(data)
        if back != line:
            raise ValueError(f"{where}: round-trip mismatch\n  source : {line!r}\n  decoded: {back!r}")
        chunks.append(data)
    tokens = b"\x3F".join(chunks)

    prog = TIProgram(name=PROGRAM_NAME)
    prog.data = tokens
    # TI-84 Plus header (product id 0x0A): the same file works on the TI-84 Plus,
    # 84 Plus SE and 84 Plus CE through TI Connect CE.
    prog.save(str(out), header=TIHeader(model=TI_84P), model=TI_84P)
    return tokens


def main():
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_SRC
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_OUT
    tokens = build(src, out)
    n_lines = tokens.count(b"\x3F") + 1
    print(f"Built {out} : {len(tokens)} token bytes, {n_lines} lines")


if __name__ == "__main__":
    main()
