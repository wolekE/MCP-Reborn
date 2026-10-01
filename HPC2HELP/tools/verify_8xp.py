#!/usr/bin/env python3
"""
Independently verify HPC2HELP.8xp.

1. Parse the raw bytes by hand (no tivars) using the documented TI-83+/84+
   variable-file layout and check the signature, lengths, type, name, the
   archived flag and the checksum.
2. Re-open the file with tivars, detokenize it, and check that it reads back
   line for line as HPC2HELP.txt.
3. Re-tokenize HPC2HELP.txt and check the program bytes are identical.

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

    # ---- 2. tivars re-open and detokenize ------------------------------
    var = TIVarFile.open(str(f8))
    entry = var.entries[0]
    check(isinstance(entry, TIProgram) and entry.name == "HPC2HELP", "tivars opens it as program HPC2HELP")
    text = entry.string()
    src_lines = src.read_text(encoding="utf-8").rstrip("\n").split("\n")
    check(text.split("\n") == src_lines, f"detokenized program matches {src.name} line for line ({len(src_lines)} lines)")

    # ---- 3. re-tokenize the source -------------------------------------
    rebuilt = b"\x3F".join(tokenize_line(l, f"{src.name}:{i+1}") for i, l in enumerate(src_lines))
    check(rebuilt == tokens, "re-tokenized source is byte-identical to the program in the .8xp")
    print("ALL CHECKS PASSED")


if __name__ == "__main__":
    main()
