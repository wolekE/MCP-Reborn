#!/usr/bin/env python3
"""
Build HPC2HELP.8xp from HPC2HELP.txt with tivars (TI-Toolkit's tivars_lib_py,
https://github.com/TI-Toolkit/tivars_lib_py, `pip install tivars`).

The source file has one TI-BASIC statement per line, written with the token
names the calculator / TI Connect CE display (Disp, ClrHome, →, ►Frac, ≠ ...).

Code (outside quotes) is tokenized by tivars.  Text inside quotes is tokenized
here one character at a time from a whitelist of characters a student can type
on the keypad, so tivars' ASCII shortcuts ("->", ">=", "L1", "[A]" ...) can
never turn display text into a different token.  Every line is then decoded
again and must read back exactly as written, or the build fails.

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


def tokenize_line(line: str, where: str) -> bytes:
    """Tokenize one statement: code via tivars, quoted text via the whitelist."""
    out = b""
    rest = line
    while rest:
        q = rest.find('"')
        if q < 0:
            code, rest = rest, ""
            out += encode(code, mode="smart")[0] if code else b""
            break
        code = rest[:q]
        if code:
            out += encode(code, mode="smart")[0]
        rest = rest[q + 1:]
        end = rest.find('"')
        if end < 0:
            raise ValueError(f"{where}: unterminated string (every string must be closed)")
        body, rest = rest[:end], rest[end + 1:]
        out += b"\x2A" + tokenize_string_body(body, where) + b"\x2A"
    return out


def display(data: bytes) -> str:
    return "".join(tok.langs["en"].display for tok in decode(data)[0])


def build(src: Path, out: Path) -> bytes:
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
