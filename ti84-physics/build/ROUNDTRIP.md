# Round-trip report

Each `.8xp` was re-opened from disk, detokenized with tivars_lib_py, and diffed
against its source text (`src/<NAME>.txt` for the modules, `PHYSICS.txt` for the merged
program). `identical` means the diff is empty. The detokenized text is in `build/roundtrip/`.

**`PHYSICS.8xp` is the file to send.** The module builds in `build/modules/` are what the
test-suites exercise one by one.

| Program | Lines | Tokens | Program bytes | .8xp file bytes | Round-trip diff | tivars smart-mode bytes | sha256 (16) | Min OS |
|---|---|---|---|---|---|---|---|---|
| PHYSOLVE | 71 | 810 | 811 | 887 | identical | same | 4ca00a9ce22d918b | TI-83 1.010 |
| PHYSREF | 517 | 10645 | 10683 | 10759 | identical | same | 0c8a2fc3f4401ca6 | TI-83+ 1.16 |
| ZCHASE | 275 | 3678 | 3729 | 3805 | identical | differs | 69e8fcb22e7a3985 | TI-83 0.01013 |
| ZFMT | 40 | 449 | 487 | 563 | identical | differs | da828288219aff4b | TI-83 0.01013 |
| ZFREE | 439 | 5607 | 5680 | 5756 | identical | differs | b6c0ce2cd1ce661b | TI-83+ 1.16 |
| ZLINE | 6 | 41 | 47 | 123 | identical | same | 1d1f11ba78bc9ebb | TI-83 0.01013 |
| ZPROJ | 657 | 8345 | 8541 | 8617 | identical | differs | 7863af6ccaf0193e | TI-83+ 1.16 |
| ZQUAD | 72 | 524 | 541 | 617 | identical | differs | f76ab24464dc60ae | TI-83+ 1.16 |
| ZRIVER | 250 | 3493 | 3540 | 3616 | identical | differs | b7096436b243f628 | TI-83+ 1.16 |
| ZTOOLS | 991 | 12484 | 12844 | 12920 | identical | differs | be29f9e2ba301c56 | TI-83+ 1.16 |
| ZVOVF | 964 | 9843 | 10138 | 10214 | identical | differs | 17d1f10ef6d0a113 | TI-83+ 1.16 |
| PHYSICS | 4706 | 60686 | 61808 | 61884 | identical | differs | d992fed99c0e4f0c | TI-83+ 1.16 |

`tivars smart-mode bytes` compares against `TIProgram.load_string(text)` with the default
"smart" mode. Where it says `differs`, smart mode turned a `"..."→StrN` store into the letters
S,t,r,N (a tokenizer quirk), which is why build.py tokenizes code and strings separately.
