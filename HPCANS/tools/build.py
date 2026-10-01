#!/usr/bin/env python3
"""
Build one .8xp per program: src/NAME.txt -> TRANSFER/NAME.8xp.

Every line is tokenized from the explicit tables in tokens.py (longest match
first; quoted text from the smaller string table).  Before anything is
written, every table entry is decoded with the TI-Toolkit token sheet that
ships with tivars (https://github.com/TI-Toolkit/tivars_lib_py) and must come
back as its own name, and every built line must decode back to the source
line exactly.  So no command can be spelled out as letters (the HPC2HELP
"Pause" lesson) and no name can silently become a different token.

Needs tivars (pip install tivars).  Usage:  python3 build.py [OUTDIR]
"""

import sys
from pathlib import Path

from tivars.models import TI_84P
from tivars.tokenizer import decode
from tivars.types import TIProgram
from tivars.var import TIHeader

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from tokens import CODE, SHEET_ALIAS, STRING, to_bytes, tokenize  # noqa: E402

SRC = HERE.parent / "src"
OUT = HERE.parent / "TRANSFER"
NEWLINE = b"\x3F"


def shown(data):
    return "".join(t.langs["en"].display for t in decode(data)[0])


def check_tables():
    for table in (CODE, STRING):
        for name, tok in table.items():
            toks = decode(tok)[0]
            s = shown(tok)
            s = SHEET_ALIAS.get(s, s)
            if len(toks) != 1 or s.rstrip(" ") != name.rstrip(" "):
                raise AssertionError(f"token {name!r} = {tok.hex()} decodes as {s!r}")


def program_bytes(path):
    lines = path.read_text(encoding="utf-8").rstrip("\n").split("\n")
    chunks = []
    for n, line in enumerate(lines, 1):
        where = f"{path.name}:{n}"
        if not line or line != line.strip():
            raise ValueError(f"{where}: empty line or stray whitespace")
        data = to_bytes(tokenize(line))
        if NEWLINE in data:
            raise ValueError(f"{where}: newline token inside a statement")
        back = shown(data).rstrip(" ")  # the sheet shows Pause / SetUpEditor with a trailing space
        if back != line:
            raise ValueError(f"{where}: round trip\n  source : {line!r}\n  decoded: {back!r}")
        chunks.append(data)
    return NEWLINE.join(chunks), len(lines)


def main():
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else OUT
    out.mkdir(parents=True, exist_ok=True)
    check_tables()
    total = 0
    for path in sorted(SRC.glob("*.txt")):
        name = path.stem
        data, n = program_bytes(path)
        prog = TIProgram(name=name)
        prog.data = data
        # TI-84 Plus header (product id 0x0A); TI Connect CE sends it to the CE as is.
        prog.save(str(out / f"{name}.8xp"), header=TIHeader(model=TI_84P), model=TI_84P)
        total += len(data)
        print(f"  {name:9s} {n:4d} lines {len(data):6d} bytes")
    print(f"built {len(list(SRC.glob('*.txt')))} programs into {out} ({total} token bytes)")


if __name__ == "__main__":
    main()
