#!/usr/bin/env python3
"""
Independently verify HPC2HELP.8xp.

1. Parse the raw bytes by hand (no tivars) using the documented TI-83+/84+
   variable-file layout and check the signature, lengths, type, name, the
   archived flag and the checksum.
2. Walk the program's token bytes by hand (no tivars) and check every token
   against a hand-written list of TI-83 Plus token values: each line starts
   with the right command byte (e.g. Pause = D8, not the letters P,a,u,s,e),
   code uses only the allowed tokens, quoted text only keypad characters,
   and no lowercase-letter (BB B0..) tokens appear anywhere.
3. Re-open the file with tivars, detokenize it, and check that it reads back
   line for line as HPC2HELP.txt.
4. Re-tokenize HPC2HELP.txt and check the program bytes are identical.

Usage:  python verify_8xp.py [file.8xp] [source.txt]
"""

import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from build_8xp import tokenize_line  # noqa: E402
from tivars.types import TIProgram  # noqa: E402
from tivars.var import TIVarFile  # noqa: E402

DEFAULT_8XP = HERE.parent / "HPC2HELP.8xp"
DEFAULT_SRC = HERE.parent / "HPC2HELP.txt"


def check(cond, msg):
    if not cond:
        raise SystemExit("FAIL: " + msg)
    print("ok  ", msg)


# TI-83 Plus / TI-84 Plus token values (TI-83 Plus SDK token table).
TWO_BYTE_PREFIXES = {0x5C, 0x5D, 0x5E, 0x60, 0x61, 0x62, 0x63, 0x7E, 0xAA, 0xBB, 0xEF}
COMMAND_BYTES = {  # first token of a line, by how the source line starts
    "Disp ": 0xDE, "Input ": 0xDC, "Output(": 0xE0, "ClrHome": 0xE1, "Pause": 0xD8,
    "Lbl ": 0xD6, "Goto ": 0xD7, "Menu(": 0xE6, "If ": 0xCE, "Then": 0xCF, "Else": 0xD0,
    "End": 0xD4, "Stop": 0xD9, "Float": 0x69, "Normal": 0x66,
}
CODE_OK = set(COMMAND_BYTES.values()) | {
    0xB2, 0xBA, 0x1A, 0x19, 0xB8, (0xBB, 0x09),          # abs( fPart( min( max( not( gcd(
    0x40, 0x3C, 0x3D, 0x03, 0x04, 0xB0,                  # and or xor ►Frac → ⁻
    0x70, 0x71, 0x82, 0x83, 0x6A, 0x6B, 0x6C, 0x6D, 0x6E, 0x6F,  # + - * / = < > ≤ ≥ ≠
    0x10, 0x11, 0x2B, 0x3A, 0x3B,                        # ( ) , . ᴇ
} | set(range(0x30, 0x3A)) | set(range(0x41, 0x5B))      # 0-9 A-Z
STRING_OK = {0x29, 0x10, 0x11, 0x2B, 0x3A, 0x70, 0x71, 0x82, 0x83, 0xF0, 0x6A, 0x6B, 0x6C,
             0x6D, 0x6E, 0x6F, 0xAF, 0x06, 0x07, 0x0D, 0x0F, 0x0C, 0xBC, 0xBD, 0xB0} \
    | set(range(0x30, 0x3A)) | set(range(0x41, 0x5B))


def split_tokens(tokens):
    toks, i = [], 0
    while i < len(tokens):
        if tokens[i] in TWO_BYTE_PREFIXES:
            toks.append((tokens[i], tokens[i + 1]))
            i += 2
        else:
            toks.append(tokens[i])
            i += 1
    return toks


def check_token_bytes(tokens, src_lines):
    toks = split_tokens(tokens)
    lines, cur = [], []
    for t in toks:
        if t == 0x3F:
            lines.append(cur)
            cur = []
        else:
            cur.append(t)
    lines.append(cur)
    check(len(lines) == len(src_lines), f"{len(lines)} lines of tokens for {len(src_lines)} source lines")
    bad = []
    for n, (lt, sl) in enumerate(zip(lines, src_lines), 1):
        want = next((b for name, b in COMMAND_BYTES.items() if sl.startswith(name)), None)
        if want is None and "→" not in sl:
            bad.append(f"line {n}: unknown statement {sl!r}")
        if want is not None and (not lt or lt[0] != want):
            bad.append(f"line {n}: {sl!r} does not start with command token {want:02X}")
        if sl in COMMAND_BYTES and lt != [COMMAND_BYTES[sl]]:
            bad.append(f"line {n}: {sl!r} must be the single token {COMMAND_BYTES[sl]:02X}")
        in_str = False
        for t in lt:
            if t == 0x2A:
                in_str = not in_str
                continue
            if isinstance(t, tuple) and t[0] == 0xBB and t[1] >= 0xB0:
                bad.append(f"line {n}: lowercase/special-character token BB {t[1]:02X}")
            if t not in (STRING_OK if in_str else CODE_OK):
                tt = " ".join(f"{x:02X}" for x in (t if isinstance(t, tuple) else (t,)))
                bad.append(f"line {n}: token {tt} not allowed {'in a string' if in_str else 'in code'}")
        if in_str:
            bad.append(f"line {n}: string not closed")
    for b in bad[:20]:
        print("     ", b)
    check(not bad, "every token is on the allowed list; every line starts with its command token")
    n_pause = sum(1 for l in src_lines if l == "Pause")
    check(toks.count(0xD8) == n_pause, f"{n_pause} Pause commands are the real Pause token (D8)")


def main():
    f8 = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_8XP
    src = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_SRC
    raw = f8.read_bytes()

    # ---- 1. raw layout -------------------------------------------------
    check(raw[0:8] == b"**TI83F*", "signature is **TI83F* (TI-83 Plus / TI-84 Plus family)")
    check(raw[8:10] == b"\x1A\x0A", "signature tail 1A 0A")
    check(raw[10] in (0x00, 0x0A), f"product id byte 0x{raw[10]:02X} (00 = generic, 0A = TI-84 Plus)")
    data_len = struct.unpack_from("<H", raw, 53)[0]
    check(len(raw) == 55 + data_len + 2, f"file length = 55 + data section ({data_len}) + 2-byte checksum")
    data = raw[55:55 + data_len]
    checksum = struct.unpack_from("<H", raw, 55 + data_len)[0]
    check(checksum == sum(data) & 0xFFFF, f"checksum 0x{checksum:04X} matches the data section")

    meta_len, var_len, type_id = struct.unpack_from("<HHB", data, 0)
    check(meta_len == 0x0D, "entry meta length is 0x0D (TI-83+/84+ format with version + archive flag)")
    check(type_id == 0x05, "type id 0x05 = unprotected BASIC program")
    name = data[5:13].rstrip(b"\x00").decode("ascii")
    check(name == "HPC2HELP", f"variable name is {name!r} (8 chars max, starts with a letter)")
    version, flag = data[13], data[14]
    check(flag == 0x00, "stored to RAM (not archived), so it can run on a TI-84 Plus right away")
    var_len2 = struct.unpack_from("<H", data, 15)[0]
    check(var_len == var_len2, "both copies of the variable length agree")
    body = data[17:17 + var_len]
    check(len(data) == 17 + var_len, "entry fills the data section exactly")
    tok_len = struct.unpack_from("<H", body, 0)[0]
    check(tok_len == var_len - 2, f"program token length {tok_len} = variable length - 2")
    tokens = body[2:]
    check(version <= 0x01, f"version byte 0x{version:02X}: needs only TI-83 Plus OS 1.00+ tokens (no CE-only tokens)")
    print(f"     program size {var_len} bytes")

    # ---- 2. hand-written byte-level token check ------------------------
    src_lines = src.read_text(encoding="utf-8").rstrip("\n").split("\n")
    check_token_bytes(tokens, src_lines)

    # ---- 3. tivars re-open and detokenize ------------------------------
    var = TIVarFile.open(str(f8))
    entry = var.entries[0]
    check(isinstance(entry, TIProgram) and entry.name == "HPC2HELP", "tivars opens it as program HPC2HELP")
    text = entry.string()
    shown = [("Pause" if l == "Pause " else l) for l in text.split("\n")]  # tivars names it "Pause "
    check(shown == src_lines, f"detokenized program matches {src.name} line for line ({len(src_lines)} lines)")

    # ---- 4. re-tokenize the source -------------------------------------
    rebuilt = b"\x3F".join(tokenize_line(l, f"{src.name}:{i+1}") for i, l in enumerate(src_lines))
    check(rebuilt == tokens, "re-tokenized source is byte-identical to the program in the .8xp")
    print("ALL CHECKS PASSED")


if __name__ == "__main__":
    main()
