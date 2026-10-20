"""A small TI-84 TI-BASIC interpreter used to test FORCES off-calculator.

It runs the text that tivars detokenizes from the .8xp, with scripted key
presses, and models what matters for this program:

* TI number semantics: 14-digit decimal math, 10-digit Float display,
  degree/radian trig, round(, int(, fPart(, log(, expr(, toString(.
* The home screen (16x8 monochrome or 26x10 CE) for Disp, Input, Output(,
  ClrHome, Pause and Menu(.  Every character written is tracked until the
  user has had a chance to read it (a Pause, Input or Menu( wait); anything
  scrolled off, cleared or hidden by a menu before that is a violation.
* Control flow with a block stack, so a Goto or Menu( executed inside an
  If-Then / For / While / Repeat block is reported as a memory leak.

Only the TI-BASIC subset used by FORCES is supported; anything else raises.
"""

import math
import re
from decimal import Decimal, ROUND_DOWN, ROUND_FLOOR, ROUND_HALF_UP, localcontext

PREC = 14


class TIError(Exception):
    """A calculator runtime error (ERR:DOMAIN, ERR:UNDEFINED, ...)."""


class ScriptEnd(Exception):
    """The test script ran out of key presses at a menu."""


def D(x):
    with localcontext() as c:
        c.prec = PREC
        return +Decimal(x)


def _from_float(f):
    if abs(f) < 1e-12:
        return Decimal(0)
    return D(format(f, ".14g"))


# ------------------------------------------------------------ number display
def ti_format(d, style="classic"):
    """Format a number the way the home screen shows it in Normal Float mode.

    style 'classic' drops the leading zero (.5); 'mathprint' keeps it (0.5).
    """
    if d == 0:
        return "0"
    neg = d < 0
    x = abs(d)
    exp = x.adjusted()
    with localcontext() as c:
        c.prec = 10
        c.rounding = ROUND_HALF_UP
        x = +x                                 # 10 significant digits
    exp = x.adjusted()
    if -3 <= exp < 10:
        s = format(x, "f")
        if "." in s:
            s = s.rstrip("0").rstrip(".")
        if style == "classic" and s.startswith("0."):
            s = s[1:]
    else:
        m = x.scaleb(-exp)
        ms = format(m, "f")
        if "." in ms:
            ms = ms.rstrip("0").rstrip(".")
        s = f"{ms}ᴇ{'⁻' if exp < 0 else ''}{abs(exp)}"
    return ("⁻" if neg else "") + s


# ------------------------------------------------------------------- lexer
FUNCS = ["toString(", "length(", "fPart(", "iPart(", "round(", "expr(",
         "abs(", "sin(", "cos(", "tan(", "max(", "min(", "int(", "log(",
         "not(", "sub("]
OPS = [" and ", " or ", " xor ", "→", "+", "-", "*", "/", "^", "²", "=", "≠",
       "<", ">", "≤", "≥", "⁻", "(", ")", ","]
TOKEN_RE = re.compile(
    r'(?P<str>"[^"]*"?)|(?P<num>\d+\.?\d*|\.\d+)|(?P<strvar>Str\d)|'
    r'(?P<func>' + "|".join(re.escape(f) for f in FUNCS) + r')|'
    r'(?P<var>[A-Zθ])|(?P<op>' + "|".join(re.escape(o) for o in OPS) + r')')


def lex(text):
    toks, i = [], 0
    while i < len(text):
        m = TOKEN_RE.match(text, i)
        if not m:
            raise TIError(f"ERR:SYNTAX (cannot lex {text[i:]!r})")
        kind = m.lastgroup
        val = m.group()
        if kind == "str":
            val = val[1:-1] if val.endswith('"') and len(val) > 1 else val[1:]
        toks.append((kind, val))
        i = m.end()
    return toks


# ------------------------------------------------------------------ parser
class Parser:
    def __init__(self, toks):
        self.t, self.i = toks, 0

    def peek(self, k=0):
        j = self.i + k
        return self.t[j] if j < len(self.t) else (None, None)

    def take(self, val=None):
        tok = self.peek()
        if val is not None and tok[1] != val:
            raise TIError(f"ERR:SYNTAX (expected {val!r}, got {tok[1]!r})")
        self.i += 1
        return tok

    def parse(self):
        node = self.orexpr()
        if self.i != len(self.t):
            raise TIError(f"ERR:SYNTAX (trailing {self.t[self.i:]})")
        return node

    def orexpr(self):
        node = self.andexpr()
        while self.peek()[1] in (" or ", " xor "):
            op = self.take()[1].strip()
            node = (op, node, self.andexpr())
        return node

    def andexpr(self):
        node = self.relexpr()
        while self.peek()[1] == " and ":
            self.take()
            node = ("and", node, self.relexpr())
        return node

    def relexpr(self):
        node = self.addexpr()
        while self.peek()[1] in ("=", "≠", "<", ">", "≤", "≥"):
            op = self.take()[1]
            node = (op, node, self.addexpr())
        return node

    def addexpr(self):
        node = self.mulexpr()
        while self.peek()[1] in ("+", "-"):
            op = self.take()[1]
            node = (op, node, self.mulexpr())
        return node

    def starts_operand(self):
        kind, val = self.peek()
        return kind in ("num", "var", "strvar", "func") or val == "("

    def mulexpr(self):
        node = self.negexpr()
        while True:
            if self.peek()[1] in ("*", "/"):
                op = self.take()[1]
                node = (op, node, self.negexpr())
            elif self.starts_operand():
                node = ("*", node, self.negexpr())       # implied multiplication
            else:
                return node

    def negexpr(self):
        if self.peek()[1] == "⁻":
            self.take()
            return ("neg", self.negexpr())
        return self.powexpr()

    def powexpr(self):
        node = self.postfix()
        while self.peek()[1] == "^":
            self.take()
            node = ("^", node, self.negexpr())
        return node

    def postfix(self):
        node = self.primary()
        while self.peek()[1] == "²":
            self.take()
            node = ("^", node, ("num", Decimal(2)))
        return node

    def primary(self):
        kind, val = self.take()
        if kind == "num":
            return ("num", D(val))
        if kind == "str":
            return ("str", val)
        if kind in ("var", "strvar"):
            return ("var", val)
        if kind == "func":
            args = [self.orexpr()]
            while self.peek()[1] == ",":
                self.take()
                args.append(self.orexpr())
            if self.peek()[1] == ")":
                self.take()
            return ("call", val, args)
        if val == "(":
            node = self.orexpr()
            if self.peek()[1] == ")":
                self.take()
            return node
        raise TIError(f"ERR:SYNTAX (unexpected {val!r})")


def parse_expr(text):
    return Parser(lex(text)).parse()


def split_args(text):
    """Split on commas that are outside strings and parentheses."""
    out, depth, cur, in_str = [], 0, "", False
    for ch in text:
        if ch == '"':
            in_str = not in_str
        elif not in_str and ch == "(":
            depth += 1
        elif not in_str and ch == ")":
            depth -= 1
        if ch == "," and depth == 0 and not in_str:
            out.append(cur)
            cur = ""
        else:
            cur += ch
    out.append(cur)
    return out


def split_store(text):
    in_str = False
    for i in range(len(text) - 1, -1, -1):
        ch = text[i]
        if ch == '"':
            in_str = not in_str
        if ch == "→" and text[:i].count('"') % 2 == 0:
            return text[:i], text[i + 1:]
    return text, None


# ------------------------------------------------------------------ screen
class Screen:
    def __init__(self, rows, cols, mono, style, violations):
        self.rows, self.cols, self.mono, self.style = rows, cols, mono, style
        self.v = violations
        self.clear(check=False)

    def clear(self, check=True):
        if check:
            self._discard(range(self.rows), "cleared before it was seen")
        self.grid = [[" "] * self.cols for _ in range(self.rows)]
        self.unseen = [[False] * self.cols for _ in range(self.rows)]
        self.cursor = 0

    def _discard(self, rows, why):
        for r in rows:
            if any(u and ch != " " for u, ch in zip(self.unseen[r], self.grid[r])):
                self.v.append(f"text {why}: {''.join(self.grid[r]).rstrip()!r}")

    def _scroll(self):
        self._discard([0], "scrolled away before it was seen")
        self.grid = self.grid[1:] + [[" "] * self.cols]
        self.unseen = self.unseen[1:] + [[False] * self.cols]
        self.cursor = self.rows - 2

    def put(self, r, c, text):
        """Write text at 0-based (r, c); report wrapping."""
        for ch in text:
            if c >= self.cols:
                self.v.append(f"text wraps past column {self.cols}: {text!r}")
                r, c = r + 1, 0
            if r >= self.rows:
                self.v.append(f"text runs off the bottom: {text!r}")
                return
            if self.unseen[r][c] and self.grid[r][c] not in (" ", ch):
                self.v.append(f"overwrote unseen text at row {r + 1}: {text!r} "
                              f"over {''.join(self.grid[r]).rstrip()!r}")
            self.grid[r][c] = ch
            self.unseen[r][c] = True
            c += 1

    def line(self, text, right=False):
        """A Disp line at the cursor.  Like the TI, Disp never writes on the
        last row: it scrolls first, so only rows-1 Disp lines fit."""
        if self.cursor >= self.rows - 1:
            self._scroll()
        if len(text) > self.cols:
            self.v.append(f"Disp/Input line wider than {self.cols}: {text!r}")
        if right:
            text = text.rjust(self.cols)[-self.cols:]
        self.grid[self.cursor] = [" "] * self.cols
        self.put(self.cursor, 0, text[:self.cols])
        extra = text[self.cols:]
        self.cursor += 1
        while extra:
            if self.cursor >= self.rows - 1:
                self._scroll()
            self.put(self.cursor, 0, extra[:self.cols])
            extra = extra[self.cols:]
            self.cursor += 1

    def seen(self):
        self.unseen = [[False] * self.cols for _ in range(self.rows)]

    def text(self):
        return ["".join(r).rstrip() for r in self.grid]


# ---------------------------------------------------------------- machine
PROFILES = {
    "mono": dict(rows=8, cols=16, mono=True, menu_title=16, menu_opt=14),
    "ce": dict(rows=10, cols=26, mono=False, menu_title=26, menu_opt=24),
}


class Machine:
    def __init__(self, source, profile, script, init=None, style="classic",
                 max_steps=200000, blank="empty"):
        self.lines = source.split("\n")
        self.p = PROFILES[profile]
        self.profile = profile
        self.style = style
        self.blank = blank      # what a blank ENTER at Input "...",StrN does:
                                # "empty" stores "", "unchanged" keeps StrN
        self.answer = script if callable(script) else None
        self.script = [] if callable(script) else list(script)
        self.violations = []
        self.screen = Screen(self.p["rows"], self.p["cols"], self.p["mono"],
                             style, self.violations)
        self.reals = {}
        self.strs = {}
        self.angle = "degree"
        for k, v in (init or {}).items():
            if k == "angle":
                self.angle = v
            elif k.startswith("Str"):
                self.strs[k] = v
            else:
                self.reals[k] = D(v)
        self.stack = []
        self.max_depth = 0
        self.pc = 0
        self.steps = 0
        self.max_steps = max_steps
        self.pauses = []        # screen snapshots at every Pause
        self.menus = []         # (title, options, choice)
        self.inputs = []        # (prompt, typed)
        self.status = None
        self.written = set()
        self.labels = {}
        for i, line in enumerate(self.lines):
            if line.startswith("Lbl ") and line[4:] not in self.labels:
                self.labels[line[4:]] = i
        self._cache = {}
        self.hit = set()        # line numbers executed (coverage)

    # ---- values
    def get(self, name):
        if name.startswith("Str"):
            if name not in self.strs:
                raise TIError(f"ERR:UNDEFINED ({name})")
            return self.strs[name]
        return self.reals.get(name, Decimal(0))

    def set(self, name, val):
        self.written.add(name)
        if name.startswith("Str"):
            if not isinstance(val, str):
                raise TIError("ERR:DATA TYPE")
            self.strs[name] = val
        else:
            if isinstance(val, str):
                raise TIError("ERR:DATA TYPE")
            self.reals[name] = val

    def ev(self, node):
        with localcontext() as c:
            c.prec = PREC
            return self._ev(node)

    def _num(self, node):
        v = self._ev(node)
        if isinstance(v, str):
            raise TIError("ERR:DATA TYPE")
        return v

    def _ev(self, node):
        kind = node[0]
        if kind == "num":
            return node[1]
        if kind == "str":
            return node[1]
        if kind == "var":
            return self.get(node[1])
        if kind == "neg":
            return -self._num(node[1])
        if kind == "call":
            return self.call(node[1], node[2])
        a, b = self._ev(node[1]), self._ev(node[2])
        if kind == "+" and isinstance(a, str) and isinstance(b, str):
            return a + b
        if isinstance(a, str) or isinstance(b, str):
            raise TIError("ERR:DATA TYPE")
        if kind == "+":
            return a + b
        if kind == "-":
            return a - b
        if kind == "*":
            return a * b
        if kind == "/":
            if b == 0:
                raise TIError("ERR:DIVIDE BY 0")
            return a / b
        if kind == "^":
            return a ** b
        truth = {"=": a == b, "≠": a != b, "<": a < b, ">": a > b,
                 "≤": a <= b, "≥": a >= b, "and": a != 0 and b != 0,
                 "or": a != 0 or b != 0, "xor": (a != 0) != (b != 0)}
        return Decimal(1) if truth[kind] else Decimal(0)

    def _trig(self, fn, x):
        rad = math.radians(float(x)) if self.angle == "degree" else float(x)
        if fn is math.tan and abs(math.cos(rad)) < 1e-15:
            raise TIError("ERR:DOMAIN (tan)")
        return _from_float(fn(rad))

    def call(self, name, args):
        if name == "toString(":
            if len(args) != 2 or self._num(args[1]) != 1:
                raise TIError("use toString(X,1): format 0 can return fractions")
            return ti_format(self._num(args[0]), "mathprint")
        if name == "length(":
            s = self._ev(args[0])
            if not isinstance(s, str):
                raise TIError("ERR:DATA TYPE")
            return Decimal(len(s))
        if name == "expr(":
            s = self._ev(args[0])
            if not isinstance(s, str):
                raise TIError("ERR:DATA TYPE")
            if not s:
                raise TIError("ERR:SYNTAX (expr of empty string)")
            return self._ev(parse_expr(s))
        if name == "sub(":
            s = self._ev(args[0])
            start, n = int(self._num(args[1])), int(self._num(args[2]))
            if not isinstance(s, str) or start < 1 or n < 1 or start + n - 1 > len(s):
                raise TIError("ERR:DOMAIN (sub)")
            return s[start - 1:start - 1 + n]
        vals = [self._num(a) for a in args]
        x = vals[0]
        if name == "abs(":
            return abs(x)
        if name == "round(":
            n = int(vals[1]) if len(vals) > 1 else 9
            return D(x.quantize(Decimal(1).scaleb(-n), rounding=ROUND_HALF_UP))
        if name == "int(":
            return x.to_integral_value(rounding=ROUND_FLOOR)
        if name == "iPart(":
            return x.to_integral_value(rounding=ROUND_DOWN)
        if name == "fPart(":
            return x - x.to_integral_value(rounding=ROUND_DOWN)
        if name == "log(":
            if x <= 0:
                raise TIError("ERR:NONREAL ANS (log)")
            return D(x.log10())
        if name == "max(":
            return max(vals)
        if name == "min(":
            return min(vals)
        if name == "not(":
            return Decimal(1) if x == 0 else Decimal(0)
        if name == "sin(":
            return self._trig(math.sin, x)
        if name == "cos(":
            return self._trig(math.cos, x)
        if name == "tan(":
            return self._trig(math.tan, x)
        raise TIError(f"unsupported function {name}")

    def expr(self, text):
        if text not in self._cache:
            self._cache[text] = parse_expr(text)
        return self.ev(self._cache[text])

    def fmt(self, v):
        return v if isinstance(v, str) else ti_format(v, self.style)

    # ---- control flow helpers
    def block_end(self, start, stop_at_else):
        depth = 0
        for i in range(start, len(self.lines)):
            ln = self.lines[i]
            if ln == "Then" or ln.startswith(("While ", "Repeat ", "For(")):
                depth += 1
            elif ln == "End":
                if depth == 0:
                    return i, "End"
                depth -= 1
            elif ln == "Else" and depth == 0 and stop_at_else:
                return i, "Else"
        raise TIError("ERR:SYNTAX (missing End)")

    def jump(self, label, how):
        if self.stack:
            self.violations.append(
                f"memory leak: {how} {label} executed inside "
                f"{[f[0] for f in self.stack]} block(s)")
        if label not in self.labels:
            raise TIError(f"ERR:LABEL ({label})")
        self.hit.add(self.labels[label])
        self.pc = self.labels[label] + 1

    def wait(self):
        self.screen.seen()

    def next_key(self, what, kind=None, info=None):
        if self.answer is not None:
            key = self.answer(kind, info)
            if key is None:
                raise ScriptEnd(what)
            return key
        if not self.script:
            raise ScriptEnd(what)
        return self.script.pop(0)

    # ---- statements
    def step(self):
        line = self.lines[self.pc]
        s = self.screen
        if line.startswith("Lbl "):
            self.pc += 1
        elif line.startswith("Goto "):
            self.jump(line[5:], "Goto")
        elif line.startswith("If "):
            cond = self.expr(line[3:]) != 0
            nxt = self.lines[self.pc + 1] if self.pc + 1 < len(self.lines) else ""
            if nxt == "Then":
                self.hit.add(self.pc + 1)
                if cond:
                    self.stack.append(("If",))
                    self.pc += 2
                else:
                    j, kind = self.block_end(self.pc + 2, True)
                    self.hit.add(j)
                    if kind == "Else":
                        self.stack.append(("If",))
                    self.pc = j + 1
            else:
                self.pc += 1 if cond else 2
        elif line == "Else":
            j, _ = self.block_end(self.pc + 1, False)
            self.hit.add(j)
            self.stack.pop()
            self.pc = j + 1
        elif line == "End":
            if not self.stack:
                raise TIError("ERR:SYNTAX (End without block)")
            frame = self.stack.pop()
            if frame[0] == "Repeat" and self.expr(frame[2]) == 0:
                self.stack.append(frame)
                self.pc = frame[1]
            elif frame[0] == "While":
                self.pc = frame[1]
            else:
                self.pc += 1
        elif line.startswith("Repeat "):
            self.stack.append(("Repeat", self.pc + 1, line[7:]))
            self.pc += 1
        elif line.startswith("While "):
            if self.expr(line[6:]) != 0:
                self.stack.append(("While", self.pc))
                self.pc += 1
            else:
                self.pc = self.block_end(self.pc + 1, False)[0] + 1
        elif line == "ClrHome":
            s.clear()
            self.pc += 1
        elif line.startswith("Disp "):
            for arg in split_args(line[5:]):
                v = self.expr(arg)
                s.line(self.fmt(v), right=not isinstance(v, str))
            self.pc += 1
        elif line.startswith("Input "):
            prompt_src, var = split_args(line[6:])
            prompt = self.expr(prompt_src)
            if len(prompt) > s.cols - 3:
                self.violations.append(f"Input prompt leaves no room: {prompt!r}")
            if s.cursor >= s.rows - 1:
                s._scroll()
            s.put(s.cursor, 0, prompt)
            self.wait()
            typed = self.next_key(f"Input {prompt!r}", "input", prompt)
            self.inputs.append((prompt, typed))
            text = prompt + typed           # typed text wraps like on the TI
            s.put(s.cursor, 0, text[:s.cols])
            s.cursor += 1
            for k in range(s.cols, len(text), s.cols):
                if s.cursor >= s.rows - 1:
                    s._scroll()
                s.put(s.cursor, 0, text[k:k + s.cols])
                s.cursor += 1
            s.seen()
            if var.startswith("Str"):
                if typed or self.blank == "empty":
                    self.set(var, typed)
            else:
                if typed == "":
                    raise TIError("ERR:SYNTAX (blank numeric Input)")
                v = self.ev(parse_expr(typed))
                self.set(var, v)
            self.pc += 1
        elif line.startswith("Output("):
            r, c, val = split_args(line[7:-1])
            r, c = int(self.expr(r)), int(self.expr(c))
            if not (1 <= r <= s.rows and 1 <= c <= s.cols):
                raise TIError(f"ERR:DOMAIN (Output({r},{c}))")
            text = self.fmt(self.expr(val))
            if not text:
                raise TIError("ERR:INVALID (empty Output)")
            s.put(r - 1, c - 1, text)
            self.pc += 1
        elif line.startswith("Pause"):
            if self.p["mono"] and s.grid[0][s.cols - 1] != " ":
                self.violations.append(
                    f"row 1 column {s.cols} is hidden by the pause indicator: "
                    f"{''.join(s.grid[0])!r}")
            self.wait()
            self.pauses.append(s.text())
            self.pc += 1
        elif line.startswith("Menu("):
            parts = split_args(line[5:-1])
            title = self.expr(parts[0])
            opts = [self.expr(o) for o in parts[1::2]]
            labels = parts[2::2]
            if len(opts) > 7:
                self.violations.append(f"Menu( with {len(opts)} options")
            if len(title) > self.p["menu_title"]:
                self.violations.append(f"menu title too long: {title!r}")
            for o in opts:
                if len(o) > self.p["menu_opt"]:
                    self.violations.append(f"menu option too long: {o!r}")
            s._discard(range(s.rows), "hidden by a Menu( before it was seen")
            self.wait()
            key = self.next_key(f"Menu {title!r} {opts}", "menu", (title, opts))
            if key.startswith("#"):
                idx = int(key[1:]) - 1
            else:
                hits = [i for i, o in enumerate(opts) if key.upper() in o.upper()]
                if not hits:
                    raise AssertionError(f"menu {title!r} has no option {key!r}: {opts}")
                idx = hits[0]
            self.menus.append((title, opts, opts[idx]))
            s.clear(check=False)        # the home screen after a menu is unknown
            self.jump(labels[idx], "Menu(")
        elif line == "Degree":
            self.angle = "degree"
            self.pc += 1
        elif line == "Radian":
            self.angle = "radian"
            self.pc += 1
        elif line in ("Float", "Normal", "Full"):
            self.pc += 1
        elif line == "Stop":
            self.status = "stopped"
        else:
            expr, target = split_store(line)
            v = self.expr(expr)
            if target is not None:
                self.set(target, v)
            self.pc += 1
        self.max_depth = max(self.max_depth, len(self.stack))

    def run(self):
        try:
            while self.status is None:
                if self.pc >= len(self.lines):
                    self.status = "ended"
                    break
                self.steps += 1
                self.hit.add(self.pc)
                if self.steps > self.max_steps:
                    raise TIError("too many steps (infinite loop?)")
                self.step()
        except ScriptEnd as e:
            self.status = f"waiting: {e}"
        return self


def values(pages):
    """Parse 'LABEL=number UNIT' rows from screen snapshots -> list of tuples."""
    out = []
    num = r"(⁻?(?:\d+\.?\d*|\.\d+)(?:ᴇ⁻?\d+)?)"
    for page in pages:
        for row in page:
            m = re.match(r"^(.*)=" + num + r"(?:\s*(\S.*))?$", row)
            if m:
                v = float(m.group(2).replace("⁻", "-").replace("ᴇ", "e"))
                out.append((m.group(1), v, m.group(3) or ""))
    return out
