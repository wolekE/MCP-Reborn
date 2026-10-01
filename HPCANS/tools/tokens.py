"""
TI-84 token tables shared by the builder, the verifier and the simulator.

Source files hold one statement per line, written with the token names the
calculator / TI Connect CE display.  Every token the programs may use is listed
here with its byte value; build.py cross-checks every entry against the
TI-Toolkit token sheet (tivars) so a name can never silently become a
different token (the HPC2HELP "Pause" lesson).

tokenize(line) -> list of token names (display strings), longest match first,
with string literals tokenized from the (smaller) string whitelist.
"""

# ---- tokens allowed outside quotes ------------------------------------------
CODE = {
    # program control / I/O
    "Disp ": b"\xDE", "Input ": b"\xDC", "Output(": b"\xE0", "ClrHome": b"\xE1",
    "Pause": b"\xD8", "Lbl ": b"\xD6", "Goto ": b"\xD7", "Menu(": b"\xE6",
    "If ": b"\xCE", "Then": b"\xCF", "Else": b"\xD0", "End": b"\xD4", "Stop": b"\xD9",
    "For(": b"\xD3", "While ": b"\xD1", "Repeat ": b"\xD2", "Return": b"\xD5",
    "prgm": b"\x5F", "getKey": b"\xAD", "DelVar ": b"\xBB\x54",
    "Float": b"\x69", "Normal": b"\x66", "Func": b"\x76", "SortA(": b"\xE3", "SetUpEditor ": b"\xBB\x4A", "SetUpEditor": b"\xBB\x4A",
    # functions
    "abs(": b"\xB2", "fPart(": b"\xBA", "iPart(": b"\xB9", "int(": b"\xB1",
    "round(": b"\x12", "gcd(": b"\xBB\x09", "lcm(": b"\xBB\x08", "min(": b"\x1A",
    "max(": b"\x19", "not(": b"\xB8", "√(": b"\xBC", "³√(": b"\xBD",
    "sub(": b"\xBB\x0C", "length(": b"\xBB\x2B", "inString(": b"\xBB\x0F",
    "expr(": b"\xBB\x2A", "dim(": b"\xB5", "augment(": b"\x14", "seq(": b"\x23",
    "sum(": b"\xB6",
    # operators and punctuation
    " and ": b"\x40", " or ": b"\x3C", " xor ": b"\x3D", "→": b"\x04", "⁻": b"\xB0",
    "+": b"\x70", "-": b"\x71", "*": b"\x82", "/": b"\x83", "^": b"\xF0",
    "²": b"\x0D", "³": b"\x0F", "⁻¹": b"\x0C",
    "=": b"\x6A", "<": b"\x6B", ">": b"\x6C", "≤": b"\x6D", "≥": b"\x6E", "≠": b"\x6F",
    "(": b"\x10", ")": b"\x11", "{": b"\x08", "}": b"\x09", ",": b"\x2B", ".": b"\x3A",
    "ᴇ": b"\x3B", '"': b"\x2A", "θ": b"\x5B", "ʟ": b"\xEB",
    # variables
    "L₁": b"\x5D\x00", "L₂": b"\x5D\x01", "L₃": b"\x5D\x02", "L₄": b"\x5D\x03",
    "L₅": b"\x5D\x04", "L₆": b"\x5D\x05",
}
for _i in range(10):
    CODE[f"Str{_i}"] = b"\xAA" + bytes([(_i - 1) % 10])  # Str1=AA00 ... Str9=AA08, Str0=AA09
for _ch in "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ":
    CODE[_ch] = bytes([ord(_ch)])

# ---- tokens allowed inside quotes (all display cleanly on the CE) -------------
STRING = {
    " ": b"\x29", "(": b"\x10", ")": b"\x11", ",": b"\x2B", ".": b"\x3A",
    "+": b"\x70", "-": b"\x71", "*": b"\x82", "/": b"\x83", "^": b"\xF0",
    "=": b"\x6A", "<": b"\x6B", ">": b"\x6C", "≤": b"\x6D", "≥": b"\x6E", "≠": b"\x6F",
    "?": b"\xAF", "[": b"\x06", "]": b"\x07", "²": b"\x0D", "³": b"\x0F",
    "⁻¹": b"\x0C", "⁻": b"\xB0", "√(": b"\xBC", "³√(": b"\xBD", "|": b"\xBB\xD8",
    "𝑒^(": b"\xBF", "θ": b"\x5B", ":": b"\x3E", "𝑖": b"\x2C", "abs(": b"\xB2",
}
for _ch in "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ":
    STRING[_ch] = bytes([ord(_ch)])

# Display width of a token on the home screen (characters).
def width(tok):
    if tok == "⁻¹":
        return 1
    return len(tok)


ALL = dict(CODE)
ALL.update(STRING)
_CODE_NAMES = sorted(CODE, key=len, reverse=True)
_STR_NAMES = sorted(STRING, key=len, reverse=True)
# The tivars token sheet shows the Pause token as "Pause " (trailing space) etc.
SHEET_ALIAS = {"Pause ": "Pause"}


class TokenError(ValueError):
    pass


def _munch(text, i, names, table_name):
    for name in names:
        if text.startswith(name, i):
            return name
    raise TokenError(f"cannot tokenize {text[i:i + 12]!r} ({table_name})")


def tokenize(line):
    """Return the token names of one source line.  Quotes are tokens; text
    between quotes uses the string whitelist; a string ends at the next quote
    (every string in the sources must be closed)."""
    toks, i, in_str = [], 0, False
    while i < len(line):
        if line[i] == '"':
            toks.append('"')
            in_str = not in_str
            i += 1
            continue
        name = _munch(line, i, _STR_NAMES if in_str else _CODE_NAMES,
                      "string text" if in_str else "code")
        toks.append(name)
        i += len(name)
    if in_str:
        raise TokenError("unterminated string")
    return toks


def tokenize_text(text):
    """Tokenize text the student would type at an Input prompt (string mode
    plus the code tokens a student can key in, e.g. X from [X,T,θ,n])."""
    names = sorted(set(_STR_NAMES) | set(_CODE_NAMES) - {'"', "→"}, key=len, reverse=True)
    toks, i = [], 0
    while i < len(text):
        name = _munch(text, i, names, "typed text")
        toks.append(name)
        i += len(name)
    return toks


def to_bytes(toks):
    return b"".join(ALL[t] for t in toks)
