#!/usr/bin/env python3
"""
Independently verify every .8xp in TRANSFER/ against src/.

For each file:
1. Parse the raw bytes by hand (no tivars) with the documented TI-83 Plus /
   TI-84 Plus variable-file layout: signature, lengths, checksum, type 05
   (program, not protected), name = file name, stored in RAM (not archived).
2. Split the program's bytes into tokens by hand (one- and two-byte tokens)
   and decode them with the inverse of the token tables; the result must be
   the source file line for line.  Each command line must start with its
   command byte (Pause = D8, never the letters P,a,u,s,e).
3. Re-open the file with tivars and detokenize it: again the source, line for line.
4. Every prgm call names a program that is in the folder; nothing is missing
   or extra compared to src/.

Usage:  python3 verify.py [DIR]
"""

import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from tokens import ALL, CODE, STRING  # noqa: E402

SRC = HERE.parent / "src"
DIR = HERE.parent / "TRANSFER"
TWO_BYTE = {0x5C, 0x5D, 0x5E, 0x60, 0x61, 0x62, 0x63, 0x7E, 0xAA, 0xBB, 0xEF}
COMMANDS = {"Disp ": 0xDE, "Input ": 0xDC, "Output(": 0xE0, "ClrHome": 0xE1, "Pause": 0xD8,
            "Lbl ": 0xD6, "Goto ": 0xD7, "If ": 0xCE, "Then": 0xCF, "Else": 0xD0, "End": 0xD4,
            "Stop": 0xD9, "For(": 0xD3, "While ": 0xD1, "Repeat ": 0xD2, "Return": 0xD5,
            "prgm": 0x5F, "DelVar ": (0xBB, 0x54), "SortA(": 0xE3, "SetUpEditor": (0xBB, 0x4A),
            "Float": 0x69, "Normal": 0x66, "Func": 0x76}


class Fail(Exception):
    pass


def check(cond, msg):
    if not cond:
        raise Fail(msg)


def split(tokens):
    out, i = [], 0
    while i < len(tokens):
        if tokens[i] in TWO_BYTE:
            out.append(bytes(tokens[i:i + 2]))
            i += 2
        else:
            out.append(bytes(tokens[i:i + 1]))
            i += 1
    return out


def decode_by_hand(tokens):
    code_inv = {v: k for k, v in CODE.items() if k not in ("SetUpEditor ",)}
    str_inv = {v: k for k, v in STRING.items()}
    lines, cur, in_str = [], [], False
    for t in split(tokens):
        if t == b"\x3F":
            lines.append(cur)
            cur, in_str = [], False
            continue
        if t == b"\x2A":
            cur.append(('"', t))
            in_str = not in_str
            continue
        table = str_inv if in_str else code_inv
        if t not in table:
            raise Fail(f"token {t.hex()} is not on the allowed {'string' if in_str else 'code'} list")
        cur.append((table[t], t))
    lines.append(cur)
    return lines


def join(toks, line):
    """Rebuild the source text; SetUpEditor with arguments has a space after it."""
    s = ""
    for k, (name, _) in enumerate(toks):
        s += name
        if name == "SetUpEditor" and k + 1 < len(toks):
            s += " "
    return s


def verify(path, src_lines, programs):
    raw = path.read_bytes()
    check(raw[0:8] == b"**TI83F*" and raw[8:10] == b"\x1A\x0A", "signature **TI83F* 1A 0A")
    check(raw[10] in (0x00, 0x0A), f"product id 0x{raw[10]:02X}")
    dlen = struct.unpack_from("<H", raw, 53)[0]
    check(len(raw) == 55 + dlen + 2, "file length = 55 + data + checksum")
    data = raw[55:55 + dlen]
    check(struct.unpack_from("<H", raw, 55 + dlen)[0] == sum(data) & 0xFFFF, "checksum")
    meta, vlen, typ = struct.unpack_from("<HHB", data, 0)
    check(meta == 0x0D, "entry meta length 0x0D")
    check(typ == 0x05, "type 05 (program)")
    name = data[5:13].rstrip(b"\x00").decode("ascii")
    check(name == path.stem, f"variable name {name!r} = file name")
    check(data[14] == 0x00, "stored in RAM, not archived")
    check(struct.unpack_from("<H", data, 15)[0] == vlen and len(data) == 17 + vlen, "variable length")
    body = data[17:17 + vlen]
    check(struct.unpack_from("<H", body, 0)[0] == vlen - 2, "token length")
    tokens = body[2:]

    lines = decode_by_hand(tokens)
    check(len(lines) == len(src_lines), f"{len(lines)} lines decoded, source has {len(src_lines)}")
    for n, (toks, line) in enumerate(zip(lines, src_lines), 1):
        got = join(toks, line)
        check(got == line, f"line {n} decodes as {got!r}, source {line!r}")
        for cmd, b in COMMANDS.items():
            if line.startswith(cmd):
                want = bytes([b]) if isinstance(b, int) else bytes(b)
                check(toks and toks[0][1] == want, f"line {n} starts with command byte {want.hex()}")
                break
        for k, (nm, _) in enumerate(toks):
            if nm == "prgm":
                target = "".join(t[0] for t in toks[k + 1:])
                check(target in programs, f"line {n} calls prgm{target}, which is not in the folder")

    from tivars.types import TIProgram
    from tivars.var import TIVarFile
    entry = TIVarFile.open(str(path)).entries[0]
    check(isinstance(entry, TIProgram) and entry.name == path.stem, "tivars opens it as the program")
    back = [l.rstrip(" ") for l in entry.string().split("\n")]
    check(back == src_lines, "tivars detokenizes it to the source, line for line")
    return vlen


def main():
    d = Path(sys.argv[1]) if len(sys.argv) > 1 else DIR
    srcs = {p.stem: p.read_text(encoding="utf-8").rstrip("\n").split("\n") for p in SRC.glob("*.txt")}
    files = {p.stem: p for p in d.glob("*.8xp")}
    bad = 0
    if set(files) != set(srcs):
        print("FAIL: folder and src/ differ:", sorted(set(files) ^ set(srcs)))
        bad += 1
    total = 0
    for name in sorted(files):
        if name not in srcs:
            continue
        try:
            total += verify(files[name], srcs[name], set(files))
            print(f"ok   {name}.8xp")
        except Fail as e:
            bad += 1
            print(f"FAIL {name}.8xp: {e}")
    print(f"{len(files)} files, {total} bytes of programs in RAM: "
          + ("ALL CHECKS PASSED" if not bad else f"{bad} FAILED"))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
