#!/usr/bin/env python3
"""
tisim.py -- simulator for a SUBSET of TI-84 Plus / TI-84 Plus CE TI-BASIC.

A test harness: runs a TI-BASIC program written as UTF-8 text (one TI-BASIC
line per text line, tivars_lib_py token names such as →, ᴇ, ⁻, θ, ʟNAME,
Str1, L₁, ≠, ≤, " and ") against a scripted session and reports what the user
would see, plus warnings for calculator pitfalls.  Programs are tokenized with
tivars (smart mode, TI_84P / TI_84PCE token tables) exactly like a .8xp build,
so e.g. "Pause" without its trailing space becomes the letters P,a,u,s,e here
too (and is reported).

Python API
    from tisim import run_program, run_text, lint_program
    res = run_program("MOLES.txt", model="84p", script=["menu:1", "H2O"])
    res.error            None or "ERR:CODE at line L[ in prgmX]: <source> -- detail"
                         ("SIM:..." = harness problem: SCRIPT MISMATCH, GETKEY
                         STARVATION, MAX STEPS, UNSUPPORTED, TOKENIZE, INTERNAL)
    res.stopped          "end" | "script exhausted" | "error"
    res.warnings         lint ("lint: ...") + runtime warnings, in order
    res.transcript       events: disp/pause/output/input/menu/key/clrhome/call/
                         end/exhausted/error/snapshot (each with "line")
    res.screens          snapshots (H rows of W chars) at every blocking point
    res.vars             A-Z, θ (Decimal), Str0-9 (display text), lists, Ans, window
    res.unused_script_items, res.steps, res.leak_count, res.lint,
    res.warning_counts, res.stats, res.displayed(), res.text(snapshots=True)
    run_text(src, programs={"SUB": "..."}) runs source text from a temp dir.

Script items: "menu:N" (Menu( choice, 1-based), "key:N" (returned by getKey),
anything else is text typed at Input/Prompt ("text:..." forces text,
"tok:..." tokenizes the typed text in smart mode instead of char by char).

Semantics (TI-84 behaviour; [*] = assumption where unverified):
  * 14-digit decimal arithmetic (ROUND_HALF_UP), |x| < 1ᴇ100 else ERR:OVERFLOW.
  * precedence: postfix ² ³ ⁻¹ ! > ^ (left to right) > negation ⁻ > * / and
    implicit multiplication (same level) > + - > relations > and > or/xor.
    So ⁻2^2 = ⁻4.  "and"/"or" evaluate both sides.  '-' used as negation is
    ERR:SYNTAX.  ')' '}' '"' may be omitted at end of statement or before →.
  * a string literal ends at '"', at '→' or at end of line; ':' inside is text.
  * strings are token sequences (length( counts tokens).
  * If/Then/Else/End, For(, While, Repeat, Lbl/Goto, Menu(, prgm (recursion
    OK), Return, Stop are simulated dynamically with a per-call block stack;
    a Goto/Menu( jump with open blocks is a leak (warning, stale entries stay
    on the stack like on the calculator; ERR:MEMORY after block_limit).
    [*] End with no open block and a stray Then are ERR:SYNTAX.
  * Disp/Pause/Input/Output( on a W x H home screen (84p 16x8, ce 26x10),
    starting with "prgmNAME" on row 1 and ending with "Done".  Lines are "seen"
    at blocking points (Input, Pause, Menu(, scripted getKey, program end).
    Menu( covers/clears the home screen (unseen text there is reported).
    Disp text wider than W is truncated with "…" and reported.
  * [*] non-integer sub(/list index/round( digits -> ERR:DOMAIN; DelVar of a
    real var leaves 0; log(0) ERR:DOMAIN, log(<0) ERR:NONREAL ANS.

CLI
    python3 tisim.py run PROGRAM.txt --model 84p|ce --script script.json
                     [--snapshots] [--max-steps N] [--json] [--no-start-line]
    python3 tisim.py lint PROGRAM.txt --model 84p|ce
    (--script also accepts an inline JSON list)
"""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys
import tempfile
from collections import Counter
from dataclasses import dataclass, field
from decimal import (Context, Decimal, DivisionByZero, InvalidOperation,
                     Overflow, ROUND_DOWN, ROUND_FLOOR, ROUND_HALF_UP,
                     localcontext)

from tivars.models import TI_84P, TI_84PCE
from tivars.tokenizer import decode as _tv_decode
from tivars.tokenizer import encode as _tv_encode

__all__ = ["run_program", "run_text", "lint_program", "RunResult", "TIError",
           "SimError", "fmt_num", "MODELS"]

# --------------------------------------------------------------------------
# Models
# --------------------------------------------------------------------------

MODELS = {
    # name: (tivars model, screen width, screen height, ΔX divisor, ΔY divisor)
    "84p": (TI_84P, 16, 8, 94, 62),
    "ce": (TI_84PCE, 26, 10, 264, 164),
}

# --------------------------------------------------------------------------
# Numbers: 14 significant digit decimal floating point, exponent range ±99
# --------------------------------------------------------------------------

CTX = Context(prec=14, rounding=ROUND_HALF_UP, Emax=999999, Emin=-999999,
              traps=[InvalidOperation, DivisionByZero, Overflow])
ZERO = Decimal(0)
ONE = Decimal(1)
TEN = Decimal(10)


class TIError(Exception):
    """A calculator error (ERR:<code>)."""
    prefix = "ERR:"

    def __init__(self, code, detail=""):
        super().__init__(code, detail)
        self.code = code
        self.detail = detail


class SimError(TIError):
    """A simulator/harness problem (SIM:<code>), not a calculator error."""
    prefix = "SIM:"


class ScriptExhausted(Exception):
    def __init__(self, what):
        super().__init__(what)
        self.what = what


class StopRun(Exception):
    pass


def fix(x):
    """Normalise a Decimal result to the TI range (overflow / underflow)."""
    if not x:
        return ZERO
    a = x.adjusted()
    if a > 99:
        raise TIError("OVERFLOW")
    if a < -99:
        return ZERO
    return x


def _div(a, b):
    if not b:
        raise TIError("DIVIDE BY 0")
    return fix(CTX.divide(a, b))


def _is_int(x):
    return x == x.to_integral_value()


def _pow(a, b):
    if not a:
        if not b:
            raise TIError("DOMAIN", "0^0")
        if b < 0:
            raise TIError("DIVIDE BY 0")
        return ZERO
    if a < 0 and not _is_int(b):
        raise TIError("NONREAL ANS")
    try:
        r = CTX.power(a, b)
    except Overflow:
        raise TIError("OVERFLOW")
    except InvalidOperation:
        raise TIError("DOMAIN")
    return fix(r)


def _cmp(f):
    return lambda a, b: ONE if f(a, b) else ZERO


SCALAR_OPS = {
    "+": lambda a, b: fix(CTX.add(a, b)),
    "-": lambda a, b: fix(CTX.subtract(a, b)),
    "*": lambda a, b: fix(CTX.multiply(a, b)),
    "/": _div,
    "^": _pow,
    "=": _cmp(lambda a, b: a == b),
    "≠": _cmp(lambda a, b: a != b),
    "<": _cmp(lambda a, b: a < b),
    ">": _cmp(lambda a, b: a > b),
    "≤": _cmp(lambda a, b: a <= b),
    "≥": _cmp(lambda a, b: a >= b),
    " and ": _cmp(lambda a, b: bool(a) and bool(b)),
    " or ": _cmp(lambda a, b: bool(a) or bool(b)),
    " xor ": _cmp(lambda a, b: bool(a) != bool(b)),
}


def to_dec(s):
    """Round a literal to 14 significant digits."""
    return fix(CTX.plus(Decimal(s)))


def _plain(d):
    s = format(d, "f")
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return s


def fmt_num(x, digits=10):
    """Format a real like the TI home screen in Normal/Float mode."""
    if not x:
        return "0"
    neg = x < 0
    a = -x if neg else x
    with localcontext(Context(prec=digits, rounding=ROUND_HALF_UP,
                              Emax=999999, Emin=-999999)) as c:
        r = c.plus(a)
    e = r.adjusted()
    if e >= 10 or e < -3:
        m = r.scaleb(-e)
        s = _plain(m) + "ᴇ" + ("⁻" if e < 0 else "") + str(abs(e))
    else:
        s = _plain(r)
        if s.startswith("0."):
            s = s[1:]
    return ("⁻" if neg else "") + s


# --------------------------------------------------------------------------
# Tokens
# --------------------------------------------------------------------------

B_QUOTE = b"\x2a"     # "
B_STORE = b"\x04"     # →
B_COLON = b"\x3e"     # :
B_NEWLINE = b"\x3f"   # newline


class Tok:
    __slots__ = ("bits", "disp", "key")

    def __init__(self, bits, disp):
        self.bits = bits
        self.disp = disp
        self.key = _tok_key(bits, disp)

    def __repr__(self):
        return f"Tok({self.disp!r})"


def _tok_key(bits, disp):
    # Characters that only make sense inside strings (lowercase letters,
    # accented letters, greek letters, punctuation glyphs...).
    if len(bits) == 2 and bits[0] == 0xBB and bits[1] >= 0x6E:
        return "§" + disp
    if len(bits) == 2 and bits[0] == 0x62:      # statistics variables
        return "stat:" + disp
    if bits == b"\xef\x73":
        return "§."
    return disp


class TStr(tuple):
    """A TI string: a tuple of token byte strings."""
    __slots__ = ()


class Tokenizer:
    """Per-model tivars tokenizer with a bits -> Tok cache."""

    def __init__(self, model):
        self.model = model
        self.trie = model.tokens.tries[None]
        self.table = model.tokens.bytes
        self.cache = {}
        # every token name known to the CE (superset) for lint hints
        self.all_names = set()
        for t in TI_84PCE.tokens.bytes.values():
            self.all_names.update(t.names())
            self.all_names.add(t.display)

    def tok(self, bits, disp=None):
        t = self.cache.get(bits)
        if t is None:
            if disp is None:
                tt = self.table.get(bits)
                disp = tt.display if tt is not None else "\\x" + bits.hex()
            t = Tok(bits, disp)
            self.cache[bits] = t
        return t

    def tokenize(self, text, mode="smart"):
        data, _ = _tv_encode(text, trie=self.trie, mode=mode)
        toks, _ = _tv_decode(data, tokens=self.model.tokens)
        return [self.tok(t.bits, t.display) for t in toks]

    def disp(self, s):
        return "".join(self.tok(b).disp for b in s)


# --------------------------------------------------------------------------
# Token classes used by the parser
# --------------------------------------------------------------------------

LETTERS = set("ABCDEFGHIJKLMNOPQRSTUVWXYZθ")
DIGITS = set("0123456789")
NAMECHARS = LETTERS | DIGITS
STRVARS = {f"Str{i}" for i in range(10)}
SYSLISTS = {"L₁", "L₂", "L₃", "L₄", "L₅", "L₆"}
WINVARS = {"Xmin", "Xmax", "Ymin", "Ymax", "Xscl", "Yscl", "ΔX", "ΔY"}
FUNCS = {
    "abs(", "int(", "iPart(", "fPart(", "round(", "log(", "ln(", "₁₀^(",
    "𝑒^(", "√(", "not(", "min(", "max(", "sum(", "prod(", "mean(", "dim(",
    "length(", "sub(", "inString(", "expr(", "seq(", "gcd(", "lcm(",
    "remainder(", "augment(", "cumSum(", "ΔList(", "randInt(", "toString(",
}
CONSTS = {"π", "𝑒"}
POSTFIX = {"²", "³", "⁻¹", "!"}
RELOPS = {"=", "≠", "<", ">", "≤", "≥"}
OPERAND_START = (DIGITS | {".", "ᴇ"} | LETTERS | {"Ans"} | STRVARS | SYSLISTS
                 | {"ʟ", "(", "{", '"', "getKey", "rand", "⁻"} | FUNCS | CONSTS
                 | WINVARS)

BLOCK_OPENERS = {"Then", "For(", "While ", "Repeat "}
SIMPLE_KINDS = {"Then", "Else", "End", "Return", "Stop", "ClrHome", "Float",
                "Normal", "Full"}
CMD_KINDS = SIMPLE_KINDS | {
    "If ", "For(", "While ", "Repeat ", "Lbl ", "Goto ", "Menu(", "Disp ",
    "Input ", "Prompt ", "Pause ", "prgm", "DelVar ", "Output(", "IS>(",
    "DS<(", "SortA(", "SortD(", "Fill(", "ClrList "}
# commands whose arguments never legitimately contain a store
NO_STORE_KINDS = {"Disp ", "Output(", "Menu(", "Input ", "Pause ", "Prompt ",
                  "If ", "While ", "Repeat ", "For(", "Text("}
STRUCTURAL = {")", "}", ",", "→", "+", "-", "*", "/", "^", " and ", " or ",
              " xor ", " ", ":", "\n"} | RELOPS | CMD_KINDS


# --------------------------------------------------------------------------
# Program representation
# --------------------------------------------------------------------------

class Stmt:
    __slots__ = ("prog", "idx", "line", "toks", "kind", "ast", "err")

    def __init__(self, prog, idx, line, toks):
        self.prog = prog
        self.idx = idx
        self.line = line
        self.toks = toks
        if not toks:
            self.kind = "nop"
        elif toks[0].key in CMD_KINDS:
            self.kind = toks[0].key
        else:
            self.kind = "expr"
        self.ast = None
        self.err = None
        if self.kind in SIMPLE_KINDS and len(toks) > 1:
            self.err = TIError("SYNTAX", f"unexpected {toks[1].disp!r} after {self.kind}")

    @property
    def src(self):
        return self.prog.lines[self.line - 1]


def split_statements(toks):
    """Split one source line into statements (':' outside string literals).

    A string literal ends at a closing quote, at '→' or at end of line, like
    on the calculator. Returns a list of (tokens, arrow_closed_string_flag).
    """
    out = []
    cur = []
    arrow = False
    in_str = False
    for t in toks:
        b = t.bits
        if in_str:
            cur.append(t)
            if b == B_QUOTE:
                in_str = False
            elif b == B_STORE:
                in_str = False
                arrow = True
        elif b == B_COLON:
            out.append((cur, arrow))
            cur, arrow = [], False
        else:
            cur.append(t)
            if b == B_QUOTE:
                in_str = True
    out.append((cur, arrow))
    return out


def outside_string_tokens(toks):
    """Yield (index, token) for tokens outside string literals."""
    in_str = False
    for i, t in enumerate(toks):
        if in_str:
            if t.bits in (B_QUOTE, B_STORE):
                in_str = False
            continue
        if t.bits == B_QUOTE:
            in_str = True
            continue
        yield i, t


class Program:
    def __init__(self, name, path, tokenizer, W):
        self.name = name
        self.path = path
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        if text.startswith("﻿"):
            text = text[1:]
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        lines = text.split("\n")
        if len(lines) > 1 and lines[-1] == "":
            lines.pop()
        self.lines = lines
        self.stmts = []
        self.lint = []
        self.labels = {}
        arrow_lines = []
        self.size = max(0, len(lines) - 1)        # token bytes incl. newlines
        for ln, line in enumerate(lines, 1):
            try:
                toks = tokenizer.tokenize(line)
            except ValueError as e:
                raise SimError("TOKENIZE", f"{os.path.basename(path)} line {ln}: "
                                           f"{line!r}: {e}")
            self.size += sum(len(t.bits) for t in toks)
            for seg, arrow in split_statements(toks):
                st = Stmt(self, len(self.stmts), ln, seg)
                self.stmts.append(st)
                if arrow:
                    arrow_lines.append(st)
        _lint_program(self, tokenizer, W, arrow_lines)
        if tokenizer.model is TI_84P and self.size > 20000:
            self.lint.append(f"lint: program is {self.size} bytes; the TI-84 Plus has ~24 KB of "
                             f"user RAM, so it may not fit/run alongside its variables")

    def find_label(self, name):
        return self.labels.get(name)


# --------------------------------------------------------------------------
# Parser
# --------------------------------------------------------------------------

class Parser:
    def __init__(self, toks):
        self.t = toks
        self.i = 0
        self.n = len(toks)

    # -- helpers ----------------------------------------------------------
    def peek(self):
        return self.t[self.i].key if self.i < self.n else None

    def peek_tok(self):
        return self.t[self.i] if self.i < self.n else None

    def take(self):
        t = self.t[self.i]
        self.i += 1
        return t

    def expect(self, key):
        if self.peek() != key:
            self.unexpected(f"expected {key!r}")
        self.i += 1

    def close(self, key):
        """Closing ')' / '}' may be omitted at end of statement or before →."""
        k = self.peek()
        if k == key:
            self.i += 1
        elif k is None or k == "→":
            return
        else:
            self.unexpected(f"expected {key!r}")

    def end(self):
        if self.i < self.n:
            self.unexpected("extra tokens at end of statement")

    def unexpected(self, why=""):
        t = self.peek_tok()
        if t is None:
            raise TIError("SYNTAX", f"unexpected end of statement ({why})" if why
                          else "unexpected end of statement")
        k = t.key
        if k == " ":
            raise TIError("SYNTAX", "space token outside a string")
        if k.startswith("§"):
            raise TIError("SYNTAX", f"lowercase/char token {t.disp!r} outside a string")
        if k == "-" and why == "operand":
            raise TIError("SYNTAX", "'-' (subtract) used as negation; use '⁻'")
        if k in STRUCTURAL or k in OPERAND_START or k.startswith("stat:"):
            raise TIError("SYNTAX", f"unexpected {t.disp!r}" + (f" ({why})" if why else ""))
        raise SimError("UNSUPPORTED", f"token {t.disp!r} is not supported by the simulator")

    # -- expressions -----------------------------------------------------
    def parse_full_expr(self):
        if self.n == 0:
            raise TIError("SYNTAX", "empty expression")
        e = self.parse_expr()
        self.end()
        return e

    def parse_expr(self):
        left = self.parse_and()
        while True:
            k = self.peek()
            if k == " or " or k == " xor ":
                self.i += 1
                left = ("bin", k, left, self.parse_and())
            else:
                return left

    def parse_and(self):
        left = self.parse_rel()
        while self.peek() == " and ":
            self.i += 1
            left = ("bin", " and ", left, self.parse_rel())
        return left

    def parse_rel(self):
        left = self.parse_add()
        while True:
            k = self.peek()
            if k in RELOPS:
                self.i += 1
                left = ("bin", k, left, self.parse_add())
            else:
                return left

    def parse_add(self):
        left = self.parse_mul()
        while True:
            k = self.peek()
            if k == "+" or k == "-":
                self.i += 1
                left = ("bin", k, left, self.parse_mul())
            else:
                return left

    def parse_mul(self):
        left = self.parse_neg()
        while True:
            k = self.peek()
            if k == "*" or k == "/":
                self.i += 1
                left = ("bin", k, left, self.parse_neg())
            elif k in OPERAND_START:          # implicit multiplication
                left = ("bin", "*", left, self.parse_neg())
            else:
                return left

    def parse_neg(self):
        k = self.peek()
        if k == "⁻":
            self.i += 1
            return ("neg", self.parse_neg())
        return self.parse_pow()

    def parse_pow(self):
        left = self.parse_postfix()
        while self.peek() == "^":
            self.i += 1
            if self.peek() == "⁻":
                self.i += 1
                right = ("neg", self.parse_postfix())
            else:
                right = self.parse_postfix()
            left = ("bin", "^", left, right)
        return left

    def parse_postfix(self):
        node = self.parse_primary()
        while self.peek() in POSTFIX:
            node = ("post", self.take().key, node)
        return node

    def parse_number(self):
        s = ""
        while self.i < self.n and (self.t[self.i].key in DIGITS or self.t[self.i].key == "."):
            s += self.take().key
        if s.count(".") > 1:
            raise TIError("SYNTAX", f"bad number {s!r}")
        if self.peek() == "ᴇ":
            self.i += 1
            neg = False
            if self.peek() == "⁻":
                neg = True
                self.i += 1
            e = ""
            while self.peek() in DIGITS:
                e += self.take().key
            if not e or len(e) > 2:
                raise TIError("SYNTAX", "bad exponent after ᴇ")
            mant = s or "1"
            if mant == ".":
                raise TIError("SYNTAX", "bad number '.'")
            return ("num", to_dec(mant + "E" + ("-" if neg else "") + e))
        if s == ".":
            raise TIError("SYNTAX", "bad number '.'")
        return ("num", to_dec(s))

    def parse_listname(self):
        k = self.peek()
        if k in SYSLISTS:
            self.i += 1
            return k
        if k != "ʟ":
            self.unexpected("expected a list name")
        self.i += 1
        name = ""
        while len(name) < 5 and self.peek() in NAMECHARS:
            if not name and self.peek() in DIGITS:
                break
            name += self.take().key
        if not name:
            raise TIError("SYNTAX", "ʟ without a list name")
        return "ʟ" + name

    def parse_string(self):
        self.i += 1  # opening quote
        bits = []
        while self.i < self.n:
            t = self.t[self.i]
            if t.bits == B_QUOTE:
                self.i += 1
                break
            if t.bits == B_STORE:
                break
            bits.append(t.bits)
            self.i += 1
        return ("str", TStr(bits))

    def parse_args(self):
        args = [self.parse_expr()]
        while self.peek() == ",":
            self.i += 1
            args.append(self.parse_expr())
        self.close(")")
        return args

    def parse_primary(self):
        k = self.peek()
        if k is None:
            self.unexpected("operand")
        if k in DIGITS or k == "." or k == "ᴇ":
            return self.parse_number()
        if k in LETTERS:
            self.i += 1
            return ("var", k)
        if k == '"':
            return self.parse_string()
        if k == "(":
            self.i += 1
            e = self.parse_expr()
            self.close(")")
            return e
        if k == "Ans":
            self.i += 1
            return ("ans",)
        if k in STRVARS:
            self.i += 1
            return ("strv", k)
        if k == "ʟ" or k in SYSLISTS:
            name = self.parse_listname()
            if self.peek() == "(":
                self.i += 1
                idx = self.parse_expr()
                self.close(")")
                return ("lel", name, idx)
            return ("lst", name)
        if k == "{":
            self.i += 1
            if self.peek() == "}":
                raise TIError("SYNTAX", "empty list literal {}")
            items = [self.parse_expr()]
            while self.peek() == ",":
                self.i += 1
                items.append(self.parse_expr())
            self.close("}")
            return ("llit", items)
        if k == "seq(":
            self.i += 1
            expr = self.parse_expr()
            self.expect(",")
            if self.peek() not in LETTERS:
                self.unexpected("seq( variable must be A-Z or θ")
            var = self.take().key
            self.expect(",")
            start = self.parse_expr()
            self.expect(",")
            stop = self.parse_expr()
            step = None
            if self.peek() == ",":
                self.i += 1
                step = self.parse_expr()
            self.close(")")
            return ("seq", expr, var, start, stop, step)
        if k in FUNCS:
            self.i += 1
            return ("fn", k, self.parse_args())
        if k == "getKey":
            self.i += 1
            return ("getkey",)
        if k == "rand":
            self.i += 1
            return ("rand",)
        if k in CONSTS:
            self.i += 1
            return ("const", k)
        if k in WINVARS:
            self.i += 1
            return ("win", k)
        self.unexpected("operand")

    # -- targets ---------------------------------------------------------
    def parse_target(self, allow_elem=True, allow_dim=True):
        k = self.peek()
        if k in LETTERS:
            self.i += 1
            return ("var", k)
        if k in STRVARS:
            self.i += 1
            return ("strv", k)
        if k == "ʟ" or k in SYSLISTS:
            name = self.parse_listname()
            if self.peek() == "(" and allow_elem:
                self.i += 1
                idx = self.parse_expr()
                self.close(")")
                return ("lel", name, idx)
            return ("lst", name)
        if k == "dim(" and allow_dim:
            self.i += 1
            name = self.parse_listname()
            self.close(")")
            return ("dim", name)
        if k in WINVARS:
            self.i += 1
            return ("win", k)
        self.unexpected("invalid store/input target")

    def parse_label(self):
        name = ""
        while self.peek() in NAMECHARS:
            name += self.take().key
            if len(name) > 2:
                raise TIError("SYNTAX", "label name longer than 2 characters")
        if not name:
            self.unexpected("expected a label name")
        return name


def parse_stmt(st):
    """Parse a statement into an AST (cached on the statement)."""
    toks = st.toks
    kind = st.kind
    p = Parser(toks)
    if kind == "nop":
        return None
    if kind == "expr":
        e = p.parse_expr()
        target = None
        if p.peek() == "→":
            p.i += 1
            target = p.parse_target()
        p.end()
        return (e, target)
    p.i = 1
    if kind in SIMPLE_KINDS:
        p.end()
        return None
    if kind in ("If ", "While ", "Repeat "):
        return _full(p)
    if kind == "For(":
        if p.peek() not in LETTERS:
            p.unexpected("For( variable must be A-Z or θ")
        var = p.take().key
        p.expect(",")
        a = p.parse_expr()
        p.expect(",")
        b = p.parse_expr()
        step = None
        if p.peek() == ",":
            p.i += 1
            step = p.parse_expr()
        p.close(")")
        p.end()
        return (var, a, b, step)
    if kind in ("Lbl ", "Goto "):
        name = p.parse_label()
        p.end()
        return name
    if kind == "Disp ":
        args = []
        if p.peek() is not None:
            args.append(p.parse_expr())
            while p.peek() == ",":
                p.i += 1
                args.append(p.parse_expr())
        p.end()
        return args
    if kind == "Pause ":
        if p.peek() is None:
            return None
        return _full(p)
    if kind == "Output(":
        r = p.parse_expr()
        p.expect(",")
        c = p.parse_expr()
        p.expect(",")
        v = p.parse_expr()
        p.close(")")
        p.end()
        return (r, c, v)
    if kind == "Input ":
        if p.peek() is None:
            raise SimError("UNSUPPORTED", "Input without arguments (graph cursor)")
        start = p.i
        first = p.parse_expr()
        if p.peek() == ",":
            p.i += 1
            target = p.parse_target(allow_elem=False, allow_dim=False)
            p.end()
            return (first, target)
        p.i = start
        target = p.parse_target(allow_elem=False, allow_dim=False)
        p.end()
        return (None, target)
    if kind == "Prompt ":
        targets = [p.parse_target(allow_elem=False, allow_dim=False)]
        while p.peek() == ",":
            p.i += 1
            targets.append(p.parse_target(allow_elem=False, allow_dim=False))
        p.end()
        return targets
    if kind == "Menu(":
        title = p.parse_expr()
        items = []
        while p.peek() == ",":
            p.i += 1
            item = p.parse_expr()
            if p.peek() != ",":
                raise TIError("ARGUMENT", "Menu( item without a label")
            p.i += 1
            items.append((item, p.parse_label()))
        p.close(")")
        p.end()
        return (title, items)
    if kind == "prgm":
        name = ""
        while p.peek() in NAMECHARS and len(name) < 8:
            name += p.take().key
        if not name or name[0] in DIGITS:
            raise TIError("SYNTAX", "bad program name")
        p.end()
        return name
    if kind == "DelVar ":
        target = p.parse_target(allow_elem=False, allow_dim=False)
        rest = None
        if p.i < p.n:
            rest = Stmt(st.prog, st.idx, st.line, toks[p.i:])
        return (target, rest)
    if kind in ("IS>(", "DS<("):
        if p.peek() not in LETTERS:
            p.unexpected("expected a variable")
        var = p.take().key
        p.expect(",")
        v = p.parse_expr()
        p.close(")")
        p.end()
        return (var, v)
    if kind in ("SortA(", "SortD("):
        names = [p.parse_listname()]
        while p.peek() == ",":
            p.i += 1
            names.append(p.parse_listname())
        p.close(")")
        p.end()
        return names
    if kind == "Fill(":
        v = p.parse_expr()
        p.expect(",")
        name = p.parse_listname()
        p.close(")")
        p.end()
        return (v, name)
    if kind == "ClrList ":
        names = [p.parse_listname()]
        while p.peek() == ",":
            p.i += 1
            names.append(p.parse_listname())
        p.end()
        return names
    raise SimError("UNSUPPORTED", f"statement {kind!r}")


def _full(p):
    if p.peek() is None:
        raise TIError("SYNTAX", "missing argument")
    e = p.parse_expr()
    p.end()
    return e


def get_ast(st):
    if st.err is not None:
        raise st.err
    if st.ast is None and st.kind not in SIMPLE_KINDS and st.kind != "nop":
        try:
            st.ast = parse_stmt(st)
        except TIError as e:
            st.err = e
            raise
    return st.ast


# --------------------------------------------------------------------------
# Lint (static checks done when a program is loaded)
# --------------------------------------------------------------------------

def _lint_program(prog, tz, W, arrow_stmts):
    L = prog.lint
    seen_lines = set()

    def add(msg):
        L.append("lint: " + msg)

    # store arrow ending a string literal
    for st in arrow_stmts:
        later_quote = False
        in_str = False
        closed_by_arrow = False
        for t in st.toks:
            if in_str:
                if t.bits == B_QUOTE:
                    in_str = False
                elif t.bits == B_STORE:
                    in_str = False
                    closed_by_arrow = True
            elif t.bits == B_QUOTE:
                in_str = True
                if closed_by_arrow:
                    later_quote = True
        if later_quote or st.kind in NO_STORE_KINDS:
            add(f"store arrow inside string literal at line {st.line} "
                f"(a '→' always ends a string): {st.src}")

    openers = ends = 0
    for st in prog.stmts:
        toks = st.toks
        if st.kind in BLOCK_OPENERS:
            openers += 1
        elif st.kind == "End":
            ends += 1
        # tokens outside strings
        outside = list(outside_string_tokens(toks))
        if any(t.key == " " for _, t in outside) and (st.line, "sp") not in seen_lines:
            seen_lines.add((st.line, "sp"))
            add(f"space token outside a string at line {st.line} "
                f"(ERR:SYNTAX on the calculator): {st.src!r}")
        # runs of lowercase / char tokens outside strings
        j = 0
        while j < len(outside):
            i, t = outside[j]
            if t.key.startswith("§") or t.key.startswith("stat:"):
                run_start = i
                k = j
                while k + 1 < len(outside) and outside[k + 1][0] == outside[k][0] + 1 and \
                        (outside[k + 1][1].key.startswith("§") or outside[k + 1][1].key.startswith("stat:")):
                    k += 1
                run_end = outside[k][0] + 1
                hint = _lowercase_hint(toks, run_start, run_end, tz)
                word = "".join(x.disp for x in toks[max(0, run_start - 1):run_end])
                add(f"lowercase/char tokens outside a string at line {st.line} "
                    f"({word!r}){hint}: {st.src}")
                j = k + 1
            else:
                j += 1
        # letter E used like the EE key, and "10^(" glued to a preceding number
        for j2 in range(len(outside) - 2):
            (i0, a), (i1, b), (i2, c) = outside[j2], outside[j2 + 1], outside[j2 + 2]
            if i1 == i0 + 1 and i2 == i1 + 1:
                if (a.key in DIGITS or a.key == ".") and b.key == "E" and \
                        (c.key in DIGITS or c.key == "⁻"):
                    add(f"letter E used like an exponent at line {st.line} (e.g. 6.022E23 means "
                        f"6.022*E*23); use the ᴇ token: {st.src}")
                    break
        for j2 in range(len(outside) - 3):
            seq4 = outside[j2:j2 + 4]
            if [t.key for _, t in seq4[1:]] == ["1", "0", "^"] and \
                    (seq4[0][1].key in DIGITS or seq4[0][1].key == ".") and \
                    seq4[3][0] == seq4[0][0] + 3:
                add(f"digits run into '10^(' at line {st.line} (e.g. 310^(2) is 310², not "
                    f"3*10²); use '₁₀^(' or an explicit '*': {st.src}")
                break
        # custom list names longer than 5 characters
        for j2, (i, t) in enumerate(outside):
            if t.key == "ʟ":
                n = 0
                while i + 1 + n < len(toks) and toks[i + 1 + n].key in NAMECHARS:
                    n += 1
                if n > 5:
                    add(f"list name longer than 5 characters at line {st.line} "
                        f"(only the first 5 are used): {st.src}")
        # parse check
        try:
            get_ast(st)
            if st.kind == "DelVar " and st.ast[1] is not None:
                get_ast(st.ast[1])
        except TIError as e:
            add(f"{e.prefix}{e.code} at line {st.line}: {st.src}"
                + (f" -- {e.detail}" if e.detail else ""))
            continue
        # labels
        if st.kind == "Lbl ":
            name = st.ast
            if name in prog.labels:
                add(f"duplicate label {name} at line {st.line} (first at line "
                    f"{prog.stmts[prog.labels[name]].line}; Goto uses the first)")
            else:
                prog.labels[name] = st.idx
        # static text lengths
        if st.kind == "Disp ":
            for a in st.ast:
                if a[0] == "str":
                    n = len(tz.disp(a[1]))
                    if n > W:
                        add(f"Disp string literal longer than {W} chars ({n}) at line "
                            f"{st.line}: {st.src}")
        if st.kind == "Menu(":
            title, items = st.ast
            if title[0] == "str" and len(tz.disp(title[1])) > W:
                add(f"Menu( title longer than {W} chars at line {st.line}")
            if not 1 <= len(items) <= 7:
                add(f"Menu( has {len(items)} items (1..7 allowed) at line {st.line}")
            for it, _ in items:
                if it[0] == "str" and len(tz.disp(it[1])) > W - 2:
                    add(f"Menu( item {tz.disp(it[1])!r} longer than {W - 2} chars "
                        f"at line {st.line}")
    # label references
    for st in prog.stmts:
        if st.err is not None or st.ast is None:
            continue
        refs = []
        if st.kind == "Goto ":
            refs = [st.ast]
        elif st.kind == "Menu(":
            refs = [lbl for _, lbl in st.ast[1]]
        for r in refs:
            if r not in prog.labels:
                add(f"undefined label {r} referenced at line {st.line} "
                    f"(ERR:LABEL when reached): {st.src}")
    if openers != ends:
        add(f"block openers (Then/For(/While/Repeat: {openers}) and End statements "
            f"({ends}) do not balance (ok only with conditional-End idioms)")


def _lowercase_hint(toks, s, e, tz):
    end2 = e + 1 if e < len(toks) and toks[e].key == "(" else e
    for start in range(max(0, s - 4), s + 1):
        word = "".join(t.disp for t in toks[start:end2])
        word0 = "".join(t.disp for t in toks[start:e])
        for cand in (word0 + " ", word0 + "(", word, word0):
            if cand in tz.all_names and len(cand) > 1:
                if cand.endswith(" ") and end2 == e:
                    return (f" -- probably the {cand!r} token: tivars only matches it WITH "
                            f"its trailing space, so write {cand!r} (keep the space even at "
                            f"end of line)")
                return (f" -- {cand!r} is a token on some model but was not tokenized "
                        f"as one for this model")
    return ""


# --------------------------------------------------------------------------
# Screen model
# --------------------------------------------------------------------------

class Screen:
    """Home screen: H rows of W chars, each row [text, seen, src_line]."""

    def __init__(self, sim, W, H):
        self.sim = sim
        self.W = W
        self.H = H
        self.rows = [self._blank() for _ in range(H)]
        self.cur = 0
        self.tt = None
        self.wraps = 0

    def _blank(self):
        return [" " * self.W, True, 0]

    def _scroll(self):
        top = self.rows.pop(0)
        if top[0].strip() and not top[1]:
            self.sim.warn(f"unseen line scrolled off: {top[0].strip()} "
                          f"[shown at line {top[2]}]", kind="unseen")
        self.rows.append(self._blank())
        self.cur -= 1

    def _next_row(self):
        if self.cur >= self.H:
            self._scroll()
        r = self.cur
        self.cur += 1
        return r

    def put(self, text, right=False, src=0, seen=False):
        r = self._next_row()
        s = text.rjust(self.W) if right else text.ljust(self.W)
        self.rows[r] = [s[:self.W], seen, src]

    def tt_start(self, src):
        r = self._next_row()
        self.rows[r] = [" " * self.W, False, src]
        self.tt = [r, 0, src]

    def tt_write(self, text):
        for ch in text:
            r, c, src = self.tt
            if c >= self.W:
                r = self._next_row()
                self.rows[r] = [" " * self.W, False, src]
                c = 0
                self.wraps += 1
            row = self.rows[r]
            row[0] = row[0][:c] + ch + row[0][c + 1:]
            self.tt = [r, c + 1, src]

    def output(self, r, c, text, src):
        r -= 1
        c -= 1
        for ch in text:
            if c >= self.W:
                r += 1
                c = 0
            if r >= self.H:
                break
            row = self.rows[r]
            row[0] = row[0][:c] + ch + row[0][c + 1:]
            row[1] = False
            row[2] = src
            c += 1

    def clear(self, by=""):
        for row in self.rows:
            if row[0].strip() and not row[1]:
                self.sim.warn(f"unseen line cleared{by}: {row[0].strip()} "
                              f"[shown at line {row[2]}]", kind="unseen")
        self.rows = [self._blank() for _ in range(self.H)]
        self.cur = 0

    def mark_seen(self):
        for row in self.rows:
            row[1] = True

    def snapshot(self):
        return [row[0] for row in self.rows]


# --------------------------------------------------------------------------
# Result
# --------------------------------------------------------------------------

@dataclass
class RunResult:
    transcript: list
    screens: list
    warnings: list
    error: str | None
    vars: dict
    unused_script_items: int
    steps: int
    stopped: str = "end"
    leak_count: int = 0
    lint: list = field(default_factory=list)
    warning_counts: dict = field(default_factory=dict)
    stats: dict = field(default_factory=dict)

    def __getitem__(self, k):
        return getattr(self, k)

    def get(self, k, default=None):
        return getattr(self, k, default)

    def displayed(self):
        """All text lines shown by Disp/Pause/Output, in order."""
        return [e["text"] for e in self.transcript if e["type"] in ("disp", "pause", "output")
                and e.get("text") is not None]

    def to_json(self):
        d = {k: getattr(self, k) for k in ("transcript", "screens", "warnings", "error",
                                           "unused_script_items", "steps", "stopped",
                                           "leak_count", "lint", "warning_counts", "stats")}
        d["vars"] = {k: _jsonable(v) for k, v in self.vars.items()}
        return d

    def text(self, snapshots=False):
        return format_transcript(self, snapshots)


def _jsonable(v):
    if isinstance(v, Decimal):
        return str(v)
    if isinstance(v, list):
        return [_jsonable(x) for x in v]
    return v


# --------------------------------------------------------------------------
# The interpreter
# --------------------------------------------------------------------------

class Block:
    __slots__ = ("kind", "stmt", "end", "step")

    def __init__(self, kind, stmt, end=None, step=None):
        self.kind = kind
        self.stmt = stmt
        self.end = end
        self.step = step


class Frame:
    __slots__ = ("prog", "pc", "blocks")

    def __init__(self, prog):
        self.prog = prog
        self.pc = 0
        self.blocks = []


class Sim:
    def __init__(self, path, model="84p", script=(), max_steps=2_000_000,
                 start_line=True, block_limit=500, max_call_depth=100,
                 getkey_limit=10000, seed=0, max_warnings=2000):
        if model not in MODELS:
            raise ValueError(f"model must be one of {sorted(MODELS)}")
        self.model_name = model
        tvmodel, self.W, self.H, self.dx_div, self.dy_div = MODELS[model]
        self.tz = Tokenizer(tvmodel)
        self.path = os.path.abspath(path)
        self.dir = os.path.dirname(self.path)
        self.main_name = os.path.splitext(os.path.basename(path))[0].upper()
        self.script = [str(x) for x in script]
        self.sp = 0
        self.max_steps = max_steps
        self.block_limit = block_limit
        self.max_call_depth = max_call_depth
        self.getkey_limit = getkey_limit
        self.rng = random.Random(seed)
        self.max_warnings = max_warnings
        self.start_line_enabled = start_line

        self.reals = {c: ZERO for c in LETTERS}
        self.strs = {}
        self.lists = {n: [] for n in SYSLISTS}
        self.win = {"Xmin": Decimal(-10), "Xmax": Decimal(10), "Ymin": Decimal(-10),
                    "Ymax": Decimal(10), "Xscl": ONE, "Yscl": ONE}
        self.ans = ZERO
        self.programs = {}
        self.frames = []
        self.cur = None
        self.steps = 0
        self.getkey_zero = 0
        self.last_was_expr = False

        self.warnings = []
        self.warning_counts = Counter()
        self.lint = []
        self.transcript = []
        self.screens = []
        self.leak_count = 0
        self.stats = Counter()
        self.scr = Screen(self, self.W, self.H)

        self._ev = {
            "num": lambda n: n[1],
            "str": lambda n: n[1],
            "var": lambda n: self.reals[n[1]],
            "ans": lambda n: self.ans,
            "strv": self._e_strv,
            "lst": self._e_lst,
            "lel": self._e_lel,
            "llit": self._e_llit,
            "neg": self._e_neg,
            "bin": self._e_bin,
            "post": self._e_post,
            "fn": self._e_fn,
            "seq": self._e_seq,
            "getkey": self._e_getkey,
            "rand": lambda n: to_dec(self.rng.random()),
            "const": self._e_const,
            "win": self._e_win,
        }
        self._exec = {
            "nop": self.x_nop, "expr": self.x_expr, "If ": self.x_if,
            "Then": self.x_then, "Else": self.x_else, "End": self.x_end,
            "For(": self.x_for, "While ": self.x_while, "Repeat ": self.x_repeat,
            "Lbl ": self.x_nop, "Goto ": self.x_goto, "Menu(": self.x_menu,
            "Disp ": self.x_disp, "Input ": self.x_input, "Prompt ": self.x_prompt,
            "Pause ": self.x_pause, "prgm": self.x_prgm, "Return": self.x_return,
            "Stop": self.x_stop, "ClrHome": self.x_clrhome, "DelVar ": self.x_delvar,
            "Output(": self.x_output, "Float": self.x_nop, "Normal": self.x_nop,
            "Full": self.x_nop, "IS>(": self.x_isds, "DS<(": self.x_isds,
            "SortA(": self.x_sort, "SortD(": self.x_sort, "Fill(": self.x_fill,
            "ClrList ": self.x_clrlist,
        }

    # -- bookkeeping -----------------------------------------------------
    def warn(self, msg, kind="other"):
        self.warning_counts[msg] += 1
        self.stats["warn_" + kind] += 1
        if len(self.warnings) < self.max_warnings:
            self.warnings.append(msg)

    def line(self):
        return self.cur.line if self.cur is not None else 0

    def event(self, **kw):
        kw.setdefault("line", self.line())
        if self.cur is not None and self.cur.prog.name != self.main_name:
            kw.setdefault("prgm", self.cur.prog.name)
        self.transcript.append(kw)

    def snapshot(self, reason, rows=None):
        snap = {"reason": reason, "line": self.line(),
                "rows": rows if rows is not None else self.scr.snapshot()}
        if self.cur is not None and self.cur.prog.name != self.main_name:
            snap["prgm"] = self.cur.prog.name
        self.screens.append(snap)
        self.transcript.append({"type": "snapshot", **snap})

    def blocking(self):
        self.scr.mark_seen()

    def load_program(self, name):
        if name in self.programs:
            return self.programs[name]
        path = None
        for fn in os.listdir(self.dir):
            base, ext = os.path.splitext(fn)
            if base.upper() == name and ext.lower() == ".txt":
                path = os.path.join(self.dir, fn)
                break
        if path is None:
            raise TIError("UNDEFINED", f"program {name} not found ({name}.txt in {self.dir})")
        prog = Program(name, path, self.tz, self.W)
        self.programs[name] = prog
        files = {os.path.splitext(fn)[0].upper() for fn in os.listdir(self.dir)
                 if fn.lower().endswith(".txt")}
        for st in prog.stmts:
            if st.kind == "prgm" and st.err is None and st.ast not in files:
                prog.lint.append(f"lint: prgm{st.ast} at line {st.line}: no {st.ast}.txt next to "
                                 f"the program (ERR:UNDEFINED when reached)")
        for w in prog.lint:
            msg = w if name == self.main_name else w.replace("lint: ", f"lint: prgm{name}: ", 1)
            self.lint.append(msg)
            self.warn(msg, kind="lint")
        return prog

    # -- script ----------------------------------------------------------
    def next_item(self, kind):
        if self.sp >= len(self.script):
            raise ScriptExhausted(kind)
        item = self.script[self.sp]
        if kind == "text":
            if item.startswith(("menu:", "key:")):
                raise SimError("SCRIPT MISMATCH",
                               f"Input expects typed text but next script item is {item!r}")
            self.sp += 1
            self.getkey_zero = 0
            return item[5:] if item.startswith("text:") else item
        if kind == "menu":
            m = re.fullmatch(r"menu:(\d+)", item.strip())
            if not m:
                raise SimError("SCRIPT MISMATCH",
                               f"Menu( expects 'menu:N' but next script item is {item!r}")
            self.sp += 1
            self.getkey_zero = 0
            return int(m.group(1))
        raise AssertionError(kind)

    # -- run -------------------------------------------------------------
    def run(self):
        error = None
        stopped = "end"
        try:
            main = self.load_program(self.main_name)
            if self.start_line_enabled:
                self.scr.put("prgm" + self.main_name, src=0, seen=True)
            self.frames.append(Frame(main))
            self._loop()
            self._finish_display()
        except StopRun:
            self._finish_display()
        except ScriptExhausted as e:
            stopped = "script exhausted"
            self.event(type="exhausted", waiting_for=e.what)
            self.snapshot("script exhausted")
        except TIError as e:
            stopped = "error"
            error = self._format_error(e)
            self.event(type="error", error=error)
            self.snapshot("error")
        except RecursionError:
            stopped = "error"
            error = self._format_error(SimError("RECURSION", "expression nested too deeply"))
            self.event(type="error", error=error)
        except Exception as e:  # a simulator bug: report it instead of crashing the harness
            import traceback
            stopped = "error"
            tb = traceback.extract_tb(e.__traceback__)[-1]
            error = self._format_error(SimError(
                "INTERNAL", f"{type(e).__name__}: {e} (tisim.py:{tb.lineno}) -- please report"))
            self.event(type="error", error=error)
        return RunResult(
            transcript=self.transcript, screens=self.screens, warnings=self.warnings,
            error=error, vars=self._vars(),
            unused_script_items=len(self.script) - self.sp, steps=self.steps,
            stopped=stopped, leak_count=self.leak_count, lint=self.lint,
            warning_counts=dict(self.warning_counts),
            stats={"model": self.model_name, "input_wrapped_lines": self.scr.wraps,
                   "program_bytes": {n: p.size for n, p in self.programs.items()},
                   **dict(self.stats)})

    def _format_error(self, e):
        st = self.cur
        where = ""
        if st is not None:
            where = f" at line {st.line}"
            if st.prog.name != self.main_name:
                where += f" in prgm{st.prog.name}"
            where += f": {st.src}"
        return f"{e.prefix}{e.code}{where}" + (f" -- {e.detail}" if e.detail else "")

    def _finish_display(self):
        if self.last_was_expr:
            self._disp_value(self.ans, "end")
        else:
            self.scr.put("Done", right=True)
        self.event(type="end", text="Done" if not self.last_was_expr else None)
        self.blocking()
        self.snapshot("end")

    def _loop(self):
        frames = self.frames
        ex = self._exec
        while frames:
            f = frames[-1]
            stmts = f.prog.stmts
            if f.pc >= len(stmts):
                frames.pop()
                continue
            st = stmts[f.pc]
            self.cur = st
            self.steps += 1
            if self.steps > self.max_steps:
                raise SimError("MAX STEPS", f"exceeded {self.max_steps} steps (infinite loop?)")
            f.pc += 1
            self.last_was_expr = False
            if st.err is not None:
                raise st.err
            ex[st.kind](f, st)

    def _vars(self):
        v = {}
        for k, x in self.reals.items():
            v[k] = x
        for k, s in self.strs.items():
            v[k] = self.tz.disp(s)
        for k, l in self.lists.items():
            v[k] = list(l)
        a = self.ans
        v["Ans"] = self.tz.disp(a) if type(a) is TStr else (list(a) if type(a) is list else a)
        for k, x in self.win.items():
            v[k] = x
        return v

    # -- values ----------------------------------------------------------
    def ev(self, n):
        return self._ev[n[0]](n)

    def real(self, v, what="value"):
        if type(v) is not Decimal:
            raise TIError("DATA TYPE", f"{what} must be a real number")
        return v

    def int_arg(self, v, what="argument"):
        v = self.real(v, what)
        if not _is_int(v):
            raise TIError("DOMAIN", f"{what} must be an integer")
        return int(v)

    def sdisp(self, s):
        return self.tz.disp(s)

    def _e_strv(self, n):
        s = self.strs.get(n[1])
        if s is None:
            raise TIError("UNDEFINED", f"{n[1]} is not defined")
        return s

    def get_list(self, name):
        l = self.lists.get(name)
        if l is None:
            raise TIError("UNDEFINED", f"list {name} is not defined")
        return l

    def _e_lst(self, n):
        return self.get_list(n[1])

    def _e_lel(self, n):
        l = self.get_list(n[1])
        i = self.ev(n[2])
        i = self.int_arg(i, "list index")
        if not 1 <= i <= len(l):
            raise TIError("INVALID DIM", f"{n[1]}({i}) but dim is {len(l)}")
        return l[i - 1]

    def _e_llit(self, n):
        out = []
        for e in n[1]:
            v = self.ev(e)
            if type(v) is not Decimal:
                raise TIError("DATA TYPE", "list elements must be real")
            out.append(v)
        return out

    def _e_neg(self, n):
        v = self.ev(n[1])
        if type(v) is Decimal:
            return fix(CTX.minus(v))
        if type(v) is list:
            return [fix(CTX.minus(x)) for x in v]
        raise TIError("DATA TYPE", "negation of a string")

    def _e_bin(self, n):
        a = self.ev(n[2])
        b = self.ev(n[3])
        if type(a) is Decimal and type(b) is Decimal:
            return SCALAR_OPS[n[1]](a, b)
        return self.binop(n[1], a, b)

    def binop(self, op, a, b):
        ta, tb = type(a), type(b)
        if ta is TStr or tb is TStr:
            if ta is TStr and tb is TStr:
                if op == "+":
                    return TStr(a + b)
                if op == "=":
                    return ONE if a == b else ZERO
                if op == "≠":
                    return ZERO if a == b else ONE
            raise TIError("DATA TYPE", f"operator {op.strip()!r} with a string operand")
        f = SCALAR_OPS[op]
        if ta is list and tb is list:
            if len(a) != len(b):
                raise TIError("DIM MISMATCH", f"lists of dim {len(a)} and {len(b)}")
            return [f(x, y) for x, y in zip(a, b)]
        if ta is list and tb is Decimal:
            return [f(x, b) for x in a]
        if ta is Decimal and tb is list:
            return [f(a, y) for y in b]
        raise TIError("DATA TYPE")

    def _e_post(self, n):
        op = n[1]
        v = self.ev(n[2])

        def f(x):
            if op == "²":
                return fix(CTX.multiply(x, x))
            if op == "³":
                return fix(CTX.multiply(CTX.multiply(x, x), x))
            if op == "⁻¹":
                return _div(ONE, x)
            if not _is_int(x) or x < 0 or x > 69:
                raise TIError("DOMAIN", "factorial")
            r = ONE
            for k in range(2, int(x) + 1):
                r = CTX.multiply(r, Decimal(k))
            return fix(r)
        return self.ew(f, v)

    def ew(self, f, v):
        if type(v) is Decimal:
            return f(v)
        if type(v) is list:
            return [f(x) for x in v]
        raise TIError("DATA TYPE", "string where a number was expected")

    def ew2(self, f, a, b):
        ta, tb = type(a), type(b)
        if ta is Decimal and tb is Decimal:
            return f(a, b)
        if ta is list and tb is list:
            if len(a) != len(b):
                raise TIError("DIM MISMATCH")
            return [f(x, y) for x, y in zip(a, b)]
        if ta is list and tb is Decimal:
            return [f(x, b) for x in a]
        if ta is Decimal and tb is list:
            return [f(a, y) for y in b]
        raise TIError("DATA TYPE")

    def _e_const(self, n):
        if n[1] == "π":
            return Decimal("3.1415926535898")
        return Decimal("2.718281828459")

    def _e_win(self, n):
        k = n[1]
        if k == "ΔX":
            return _div(CTX.subtract(self.win["Xmax"], self.win["Xmin"]), Decimal(self.dx_div))
        if k == "ΔY":
            return _div(CTX.subtract(self.win["Ymax"], self.win["Ymin"]), Decimal(self.dy_div))
        return self.win[k]

    def _e_getkey(self, n):
        if self.sp < len(self.script) and self.script[self.sp].startswith("key:"):
            item = self.script[self.sp]
            try:
                code = int(item[4:])
            except ValueError:
                raise SimError("SCRIPT", f"bad key item {item!r}")
            self.sp += 1
            self.getkey_zero = 0
            self.blocking()
            self.event(type="key", code=code)
            self.snapshot("getKey")
            return Decimal(code)
        self.getkey_zero += 1
        if self.getkey_zero > self.getkey_limit:
            if self.sp >= len(self.script):
                raise ScriptExhausted("getKey")
            raise SimError("GETKEY STARVATION",
                           f"getKey polled {self.getkey_limit} times but next script item is "
                           f"{self.script[self.sp]!r}, not 'key:N'")
        return ZERO

    def _e_seq(self, n):
        _, expr, var, s, e, st = n
        s = self.real(self.ev(s), "seq( start")
        e = self.real(self.ev(e), "seq( end")
        step = self.real(self.ev(st), "seq( step") if st is not None else ONE
        if not step:
            raise TIError("DOMAIN", "seq( step 0")
        saved = self.reals[var]
        out = []
        v = s
        try:
            while (step > 0 and v <= e) or (step < 0 and v >= e):
                self.reals[var] = v
                x = self.ev(expr)
                if type(x) is not Decimal:
                    raise TIError("DATA TYPE", "seq( expression must be real")
                out.append(x)
                if len(out) > 999:
                    raise TIError("INVALID DIM", "seq( longer than 999")
                v = fix(CTX.add(v, step))
                self.steps += 1
                if self.steps > self.max_steps:
                    raise SimError("MAX STEPS", f"exceeded {self.max_steps} steps")
        finally:
            self.reals[var] = saved
        return out

    # -- functions -------------------------------------------------------
    def _e_fn(self, n):
        name = n[1]
        argn = n[2]
        if name == "expr(":
            if len(argn) != 1:
                raise TIError("ARGUMENT")
            s = self.ev(argn[0])
            if type(s) is not TStr:
                raise TIError("DATA TYPE", "expr( needs a string")
            return self.eval_tstr(s)
        args = [self.ev(a) for a in argn]
        f = FUNC_IMPL.get(name)
        if f is None:
            raise SimError("UNSUPPORTED", f"function {name}")
        return f(self, args)

    def eval_tstr(self, s):
        toks = [self.tz.tok(b) for b in s]
        if not toks:
            raise TIError("SYNTAX", "empty string in expr(/Input")
        if any(t.bits == B_STORE for t in toks):
            raise TIError("SYNTAX", "→ inside expr(")
        node = Parser(toks).parse_full_expr()
        return self.ev(node)

    # -- store -----------------------------------------------------------
    def store(self, target, v):
        kind = target[0]
        if kind == "var":
            if type(v) is not Decimal:
                raise TIError("DATA TYPE", f"cannot store a {_tname(v)} in {target[1]}")
            self.reals[target[1]] = v
        elif kind == "strv":
            if type(v) is not TStr:
                raise TIError("DATA TYPE", f"cannot store a {_tname(v)} in {target[1]}")
            self.strs[target[1]] = v
        elif kind == "lst":
            if type(v) is not list:
                raise TIError("DATA TYPE", f"cannot store a {_tname(v)} in {target[1]}")
            if len(v) > 999:
                raise TIError("INVALID DIM")
            self.lists[target[1]] = list(v)
        elif kind == "lel":
            l = self.lists.get(target[1])
            if l is None:
                raise TIError("UNDEFINED", f"store to element of undefined list {target[1]}")
            i = self.int_arg(self.ev(target[2]), "list index")
            if type(v) is not Decimal:
                raise TIError("DATA TYPE", "list elements must be real")
            if 1 <= i <= len(l):
                l[i - 1] = v
            elif i == len(l) + 1 and i <= 999:
                l.append(v)
            else:
                raise TIError("INVALID DIM", f"{target[1]}({i}) with dim {len(l)}")
        elif kind == "dim":
            n = self.real(v, "dim")
            if not _is_int(n) or n < 0:
                raise TIError("DOMAIN", "dim( must be a non-negative integer")
            n = int(n)
            if n > 999:
                raise TIError("INVALID DIM", "dim > 999")
            l = self.lists.get(target[1])
            if l is None:
                self.lists[target[1]] = [ZERO] * n
            elif n <= len(l):
                del l[n:]
            else:
                l.extend([ZERO] * (n - len(l)))
        elif kind == "win":
            v = self.real(v)
            k = target[1]
            if k == "ΔX":
                self.win["Xmax"] = fix(CTX.add(self.win["Xmin"], CTX.multiply(v, Decimal(self.dx_div))))
            elif k == "ΔY":
                self.win["Ymax"] = fix(CTX.add(self.win["Ymin"], CTX.multiply(v, Decimal(self.dy_div))))
            else:
                self.win[k] = v
        else:
            raise TIError("SYNTAX", "bad store target")

    def cond(self, node):
        v = self.ev(node)
        if type(v) is not Decimal:
            raise TIError("DATA TYPE", "condition must be a real number")
        return bool(v)

    # -- control flow helpers --------------------------------------------
    def scan(self, prog, start, want_else):
        depth = 0
        stmts = prog.stmts
        for j in range(start, len(stmts)):
            k = stmts[j].kind
            if k in BLOCK_OPENERS:
                depth += 1
            elif k == "End":
                if depth == 0:
                    return j, "End"
                depth -= 1
            elif k == "Else" and depth == 0 and want_else:
                return j, "Else"
        self.warn(f"block skip from line {self.line()} ran off the end of the program "
                  f"(missing End?)", kind="block")
        return len(stmts), None

    def push_block(self, f, b):
        f.blocks.append(b)
        total = sum(len(fr.blocks) for fr in self.frames)
        if total > self.block_limit:
            raise TIError("MEMORY", f"{total} open control blocks (leaked by Goto/Menu( "
                                    f"jumps out of blocks?)")

    def jump(self, f, label, via=""):
        idx = f.prog.find_label(label)
        if idx is None:
            raise TIError("LABEL", f"label {label} not found")
        n = len(f.blocks)
        if n:
            self.leak_count += 1
            self.warn(f"goto out of {n} open blocks at line {self.line()}{via}", kind="leak")
        f.pc = idx

    # -- statements ------------------------------------------------------
    def x_nop(self, f, st):
        pass

    def x_expr(self, f, st):
        e, target = get_ast(st)
        v = self.ev(e)
        if target is not None:
            self.store(target, v)
        self.ans = list(v) if type(v) is list else v
        self.last_was_expr = True

    def x_if(self, f, st):
        c = self.cond(get_ast(st))
        stmts = f.prog.stmts
        nxt = st.idx + 1
        if nxt < len(stmts) and stmts[nxt].kind == "Then":
            if c:
                self.push_block(f, Block("if", st))
                f.pc = nxt + 1
            else:
                j, k = self.scan(f.prog, nxt + 1, True)
                if k == "Else":
                    self.push_block(f, Block("if", st))
                f.pc = j + 1
        elif not c:
            f.pc = nxt + 1

    def x_then(self, f, st):
        raise TIError("SYNTAX", "Then without a preceding If")

    def x_else(self, f, st):
        if f.blocks and f.blocks[-1].kind == "if":
            f.blocks.pop()
        else:
            self.warn(f"Else at line {st.line} reached without an open If-Then block",
                      kind="block")
        j, _ = self.scan(f.prog, st.idx + 1, False)
        f.pc = j + 1

    def x_end(self, f, st):
        if not f.blocks:
            raise TIError("SYNTAX", "End without an open block")
        b = f.blocks[-1]
        if b.kind == "if":
            f.blocks.pop()
        elif b.kind == "while":
            f.blocks.pop()
            f.pc = b.stmt.idx
        elif b.kind == "repeat":
            if self.cond(get_ast(b.stmt)):
                f.blocks.pop()
            else:
                f.pc = b.stmt.idx + 1
        else:  # for
            var = get_ast(b.stmt)[0]
            v = fix(CTX.add(self.reals[var], b.step))
            self.reals[var] = v
            if (b.step > 0 and v > b.end) or (b.step < 0 and v < b.end):
                f.blocks.pop()
            else:
                f.pc = b.stmt.idx + 1

    def x_for(self, f, st):
        var, a, b, s = get_ast(st)
        start = self.real(self.ev(a), "For( start")
        end = self.real(self.ev(b), "For( end")
        step = self.real(self.ev(s), "For( step") if s is not None else ONE
        self.reals[var] = start
        if (step > 0 and start > end) or (step < 0 and start < end):
            j, _ = self.scan(f.prog, st.idx + 1, False)
            f.pc = j + 1
        else:
            self.push_block(f, Block("for", st, end, step))

    def x_while(self, f, st):
        if self.cond(get_ast(st)):
            self.push_block(f, Block("while", st))
        else:
            j, _ = self.scan(f.prog, st.idx + 1, False)
            f.pc = j + 1

    def x_repeat(self, f, st):
        get_ast(st)  # syntax check now
        self.push_block(f, Block("repeat", st))

    def x_goto(self, f, st):
        self.jump(f, get_ast(st))

    def x_prgm(self, f, st):
        name = get_ast(st)
        prog = self.load_program(name)
        if len(self.frames) >= self.max_call_depth:
            raise TIError("MEMORY", f"program call depth > {self.max_call_depth}")
        self.event(type="call", prgm_called=name)
        self.frames.append(Frame(prog))

    def x_return(self, f, st):
        self.frames.pop()

    def x_stop(self, f, st):
        raise StopRun()

    def x_clrhome(self, f, st):
        self.scr.clear()
        self.event(type="clrhome")

    def x_delvar(self, f, st):
        target, rest = get_ast(st)
        k = target[0]
        if k == "var":
            self.reals[target[1]] = ZERO
        elif k == "strv":
            self.strs.pop(target[1], None)
        elif k == "lst":
            if target[1] in SYSLISTS:
                self.lists[target[1]] = []
            else:
                self.lists.pop(target[1], None)
        else:
            raise TIError("SYNTAX", "DelVar target")
        if rest is not None:
            self.cur = rest
            self._exec[rest.kind](f, rest)
            self.cur = st

    def _disp_value(self, v, cmd):
        W = self.W
        if type(v) is TStr:
            text = self.sdisp(v)
            full = text
            if len(text) > W:
                self.warn(f"{cmd} line too long ({len(text)}>{W}): {text} [line {self.line()}]",
                          kind="toolong")
                text = text[:W - 1] + "…"
            self.scr.put(text, right=False, src=self.line())
            kind = "str"
        elif type(v) is Decimal:
            text = full = fmt_num(v)
            self.scr.put(text, right=True, src=self.line())
            kind = "num"
        else:
            text = full = "{" + " ".join(fmt_num(x) for x in v) + "}"
            if len(text) > W:
                self.warn(f"{cmd} line too long ({len(text)}>{W}): {text} [line {self.line()}]",
                          kind="toolong")
                text = text[:W - 1] + "…"
                self.scr.put(text, right=False, src=self.line())
            else:
                self.scr.put(text, right=True, src=self.line())
            kind = "list"
        return text, full, kind

    def x_disp(self, f, st):
        for a in get_ast(st):
            v = self.ev(a)
            text, full, kind = self._disp_value(v, "Disp")
            self.event(type="disp", text=text, value_kind=kind,
                       **({"full": full} if full != text else {}))

    def x_pause(self, f, st):
        a = get_ast(st)
        if a is not None:
            v = self.ev(a)
            text, full, kind = self._disp_value(v, "Pause")
            self.event(type="pause", text=text, value_kind=kind)
        else:
            self.event(type="pause", text=None)
        self.blocking()
        self.snapshot("Pause")

    def x_output(self, f, st):
        r, c, v = get_ast(st)
        r = self.int_arg(self.ev(r), "Output( row")
        c = self.int_arg(self.ev(c), "Output( column")
        if not (1 <= r <= self.H and 1 <= c <= self.W):
            raise TIError("DOMAIN", f"Output({r},{c}) outside {self.H}x{self.W} screen")
        v = self.ev(v)
        if type(v) is TStr:
            text = self.sdisp(v)
        elif type(v) is Decimal:
            text = fmt_num(v)
        else:
            text = "{" + " ".join(fmt_num(x) for x in v) + "}"
        room = (self.H - r) * self.W + (self.W - c + 1)
        if len(text) > room:
            self.warn(f"Output( text runs off the screen at line {self.line()}: {text}",
                      kind="toolong")
        self.scr.output(r, c, text, self.line())
        self.event(type="output", row=r, col=c, text=text)

    def _typed_tokens(self, text):
        mode = "string"
        if text.startswith("tok:"):
            text, mode = text[4:], "smart"
        try:
            return self.tz.tokenize(text, mode=mode)
        except ValueError as e:
            raise SimError("SCRIPT", f"cannot tokenize typed text {text!r}: {e}")

    def do_input(self, prompt, target):
        if len(prompt) > self.W:
            self.warn(f"Input prompt longer than the screen ({len(prompt)}>{self.W}): {prompt} "
                      f"[line {self.line()}]", kind="toolong")
        self.scr.tt_start(self.line())
        self.scr.tt_write(prompt)
        self.blocking()
        text = self.next_item("text")
        toks = self._typed_tokens(text)
        typed = "".join(t.disp for t in toks)
        before = self.scr.wraps
        self.scr.tt_write(typed)
        self.blocking()
        self.event(type="input", prompt=prompt, typed=typed, var=_target_name(target),
                   wrapped_lines=self.scr.wraps - before)
        self.snapshot("Input")
        if target[0] == "strv":
            v = TStr(t.bits for t in toks)
        else:
            if not toks:
                raise TIError("SYNTAX", "empty input for a numeric variable")
            if re.search(r"[0-9.]E", typed):
                self.warn(f"typed text {typed!r} uses the letter E (a variable), not ᴇ "
                          f"[line {self.line()}]", kind="script")
            v = self.eval_tstr(TStr(t.bits for t in toks))
            if target[0] == "var" and type(v) is not Decimal:
                raise TIError("DATA TYPE", f"typed {typed!r} is not a real number")
        self.store(target, v)

    def x_input(self, f, st):
        pnode, target = get_ast(st)
        if pnode is None:
            prompt = "?"
        else:
            pv = self.ev(pnode)
            if type(pv) is TStr:
                prompt = self.sdisp(pv)
            else:
                raise TIError("SYNTAX", "Input prompt must be a string")
        self.do_input(prompt, target)

    def x_prompt(self, f, st):
        for target in get_ast(st):
            self.do_input(_target_name(target) + "=?", target)

    def x_menu(self, f, st):
        title_n, items = get_ast(st)
        title = self.ev(title_n)
        if type(title) is not TStr:
            raise TIError("DATA TYPE", "Menu( title must be a string")
        title = self.sdisp(title)
        if not 1 <= len(items) <= 7:
            raise TIError("ARGUMENT", f"Menu( with {len(items)} items (1..7 allowed)")
        texts = []
        for it, _ in items:
            v = self.ev(it)
            if type(v) is not TStr:
                raise TIError("DATA TYPE", "Menu( item must be a string")
            texts.append(self.sdisp(v))
        W = self.W
        if len(title) > W:
            self.warn(f"Menu title too long ({len(title)}>{W}): {title} [line {st.line}]",
                      kind="toolong")
        for t in texts:
            if len(t) > W - 2:
                self.warn(f"Menu item too long ({len(t)}>{W - 2}): {t} [line {st.line}]",
                          kind="toolong")
        # the menu covers the home screen: unseen home-screen text is lost
        self.scr.clear(by=" by Menu(")
        rows = [title[:W].ljust(W)] + [f"{i}:{t}"[:W].ljust(W) for i, t in enumerate(texts, 1)]
        rows += [" " * W] * (self.H - len(rows))
        try:
            choice = self.next_item("menu")
        except ScriptExhausted:
            self.event(type="menu", title=title, items=texts, chosen=None)
            self.snapshot("Menu(", rows)
            raise ScriptExhausted("menu") from None
        if not 1 <= choice <= len(items):
            raise SimError("SCRIPT", f"menu:{choice} but the menu has {len(items)} items")
        label = items[choice - 1][1]
        self.event(type="menu", title=title, items=texts, chosen=choice, label=label)
        self.snapshot("Menu(", rows)
        self.jump(f, label, via=" (Menu()")

    def x_isds(self, f, st):
        var, vn = get_ast(st)
        v = self.real(self.ev(vn))
        x = self.reals[var]
        if st.kind == "IS>(":
            x = fix(CTX.add(x, ONE))
            skip = x > v
        else:
            x = fix(CTX.subtract(x, ONE))
            skip = x < v
        self.reals[var] = x
        if skip:
            f.pc = st.idx + 2

    def x_sort(self, f, st):
        names = get_ast(st)
        lists = [self.get_list(n) for n in names]
        if any(len(l) != len(lists[0]) for l in lists):
            raise TIError("DIM MISMATCH")
        order = sorted(range(len(lists[0])), key=lambda i: lists[0][i],
                       reverse=(st.kind == "SortD("))
        for n, l in zip(names, lists):
            self.lists[n] = [l[i] for i in order]

    def x_fill(self, f, st):
        vn, name = get_ast(st)
        v = self.real(self.ev(vn))
        l = self.get_list(name)
        for i in range(len(l)):
            l[i] = v

    def x_clrlist(self, f, st):
        for name in get_ast(st):
            self.lists[name] = []


def _target_name(t):
    if t[0] == "dim":
        return f"dim({t[1]})"
    return t[1]


def _tname(v):
    if type(v) is TStr:
        return "string"
    if type(v) is list:
        return "list"
    return "real"


# --------------------------------------------------------------------------
# Built-in function implementations: f(sim, args) -> value
# --------------------------------------------------------------------------

def _nargs(args, lo, hi, name):
    if not lo <= len(args) <= hi:
        raise TIError("ARGUMENT", f"{name} takes {lo}..{hi} arguments")


def _unary(fn, name):
    def impl(sim, args):
        _nargs(args, 1, 1, name)
        return sim.ew(fn, args[0])
    return impl


def _floor(x):
    return fix(x.to_integral_value(rounding=ROUND_FLOOR))


def _ipart(x):
    return fix(x.to_integral_value(rounding=ROUND_DOWN))


def _fpart(x):
    return fix(CTX.subtract(x, x.to_integral_value(rounding=ROUND_DOWN)))


def _round(x, n=9):
    exp = x.as_tuple().exponent
    if not isinstance(exp, int) or -exp <= n:
        return x
    with localcontext(Context(prec=60, rounding=ROUND_HALF_UP)):
        r = x.quantize(Decimal(1).scaleb(-n))
    return fix(CTX.plus(r))


def _log(x):
    if x < 0:
        raise TIError("NONREAL ANS", "log of a negative number")
    if not x:
        raise TIError("DOMAIN", "log(0)")
    return fix(CTX.log10(x))


def _ln(x):
    if x < 0:
        raise TIError("NONREAL ANS", "ln of a negative number")
    if not x:
        raise TIError("DOMAIN", "ln(0)")
    return fix(CTX.ln(x))


def _sqrt(x):
    if x < 0:
        raise TIError("NONREAL ANS", "√ of a negative number")
    return fix(CTX.sqrt(x))


def _exp(x):
    try:
        return fix(CTX.exp(x))
    except Overflow:
        raise TIError("OVERFLOW")


def f_round(sim, args):
    _nargs(args, 1, 2, "round(")
    n = 9
    if len(args) == 2:
        n = sim.int_arg(args[1], "round( digits")
        if not 0 <= n <= 9:
            raise TIError("DOMAIN", "round( digits must be 0..9")
    return sim.ew(lambda x: _round(x, n), args[0])


def _minmax(pick):
    def impl(sim, args):
        _nargs(args, 1, 2, "min(/max(")
        if len(args) == 1:
            l = args[0]
            if type(l) is not list:
                raise TIError("DATA TYPE", "min(/max( of one argument needs a list")
            if not l:
                raise TIError("INVALID DIM", "empty list")
            return pick(l)
        return sim.ew2(lambda a, b: pick((a, b)), args[0], args[1])
    return impl


def _need_list(v, name):
    if type(v) is not list:
        raise TIError("DATA TYPE", f"{name} needs a list")
    return v


def f_sum(sim, args):
    _nargs(args, 1, 3, "sum(")
    l = _need_list(args[0], "sum(")
    if len(args) > 1:
        a = sim.int_arg(args[1], "sum( start")
        b = sim.int_arg(args[2], "sum( end") if len(args) > 2 else len(l)
        if not (1 <= a <= len(l) and 1 <= b <= len(l)):
            raise TIError("INVALID DIM")
        l = l[a - 1:b]
    r = ZERO
    for x in l:
        r = fix(CTX.add(r, x))
    return r


def f_prod(sim, args):
    _nargs(args, 1, 1, "prod(")
    r = ONE
    for x in _need_list(args[0], "prod("):
        r = fix(CTX.multiply(r, x))
    return r


def f_mean(sim, args):
    _nargs(args, 1, 1, "mean(")
    l = _need_list(args[0], "mean(")
    if not l:
        raise TIError("INVALID DIM")
    return _div(f_sum(sim, [l]), Decimal(len(l)))


def f_dim(sim, args):
    _nargs(args, 1, 1, "dim(")
    return Decimal(len(_need_list(args[0], "dim(")))


def _need_str(v, name):
    if type(v) is not TStr:
        raise TIError("DATA TYPE", f"{name} needs a string")
    return v


def f_length(sim, args):
    _nargs(args, 1, 1, "length(")
    return Decimal(len(_need_str(args[0], "length(")))


def f_sub(sim, args):
    _nargs(args, 3, 3, "sub(")
    s = _need_str(args[0], "sub(")
    a = sim.int_arg(args[1], "sub( start")
    n = sim.int_arg(args[2], "sub( length")
    if a < 1 or n < 1 or a + n - 1 > len(s):
        raise TIError("DOMAIN", f"sub(<string of length {len(s)}>,{a},{n})")
    return TStr(s[a - 1:a - 1 + n])


def f_instring(sim, args):
    _nargs(args, 2, 3, "inString(")
    s = _need_str(args[0], "inString(")
    t = _need_str(args[1], "inString(")
    start = sim.int_arg(args[2], "inString( start") if len(args) == 3 else 1
    if start < 1:
        raise TIError("DOMAIN", "inString( start < 1")
    if not t:
        return Decimal(start)
    m = len(t)
    for i in range(start - 1, len(s) - m + 1):
        if s[i:i + m] == t:
            return Decimal(i + 1)
    return ZERO


def _intpair(f, name):
    def impl(sim, args):
        _nargs(args, 2, 2, name)

        def g(a, b):
            if not (_is_int(a) and _is_int(b)):
                raise TIError("DOMAIN", f"{name} needs integers")
            return Decimal(f(int(a), int(b)))
        return sim.ew2(g, args[0], args[1])
    return impl


def _gcd(a, b):
    import math
    return math.gcd(a, b)


def _lcm(a, b):
    import math
    return abs(a * b) // math.gcd(a, b) if a and b else 0


def _rem(a, b):
    if b == 0:
        raise TIError("DIVIDE BY 0")
    return (abs(a) % abs(b)) * (1 if a >= 0 else -1)


def f_augment(sim, args):
    _nargs(args, 2, 2, "augment(")
    a, b = args
    if type(a) is list and type(b) is list:
        if len(a) + len(b) > 999:
            raise TIError("INVALID DIM")
        return a + b
    raise TIError("DATA TYPE", "augment( needs two lists")


def f_cumsum(sim, args):
    _nargs(args, 1, 1, "cumSum(")
    out, r = [], ZERO
    for x in _need_list(args[0], "cumSum("):
        r = fix(CTX.add(r, x))
        out.append(r)
    return out


def f_dlist(sim, args):
    _nargs(args, 1, 1, "ΔList(")
    l = _need_list(args[0], "ΔList(")
    if len(l) < 2:
        raise TIError("INVALID DIM")
    return [fix(CTX.subtract(l[i + 1], l[i])) for i in range(len(l) - 1)]


def f_randint(sim, args):
    _nargs(args, 2, 3, "randInt(")
    lo = sim.int_arg(args[0])
    hi = sim.int_arg(args[1])
    if lo > hi:
        lo, hi = hi, lo
    if len(args) == 3:
        return [Decimal(sim.rng.randint(lo, hi)) for _ in range(sim.int_arg(args[2]))]
    return Decimal(sim.rng.randint(lo, hi))


def f_tostring(sim, args):
    if sim.model_name != "ce":
        raise TIError("SYNTAX", "toString( exists only on the TI-84 Plus CE (OS 5.2+)")
    _nargs(args, 1, 1, "toString(")
    v = args[0]
    if type(v) is TStr:
        return v
    if type(v) is Decimal:
        text = fmt_num(v)
    else:
        text = "{" + ",".join(fmt_num(x) for x in v) + "}"
    return TStr(t.bits for t in sim.tz.tokenize(text, mode="string"))


def f_not(sim, args):
    _nargs(args, 1, 1, "not(")
    return sim.ew(lambda x: ZERO if x else ONE, args[0])


def _tenpow(x):
    return _pow(TEN, x)


FUNC_IMPL = {
    "abs(": _unary(lambda x: fix(abs(x)), "abs("),
    "int(": _unary(_floor, "int("),
    "iPart(": _unary(_ipart, "iPart("),
    "fPart(": _unary(_fpart, "fPart("),
    "round(": f_round,
    "log(": _unary(_log, "log("),
    "ln(": _unary(_ln, "ln("),
    "₁₀^(": _unary(_tenpow, "₁₀^("),
    "𝑒^(": _unary(_exp, "𝑒^("),
    "√(": _unary(_sqrt, "√("),
    "not(": f_not,
    "min(": _minmax(min),
    "max(": _minmax(max),
    "sum(": f_sum,
    "prod(": f_prod,
    "mean(": f_mean,
    "dim(": f_dim,
    "length(": f_length,
    "sub(": f_sub,
    "inString(": f_instring,
    "gcd(": _intpair(_gcd, "gcd("),
    "lcm(": _intpair(_lcm, "lcm("),
    "remainder(": _intpair(_rem, "remainder("),
    "augment(": f_augment,
    "cumSum(": f_cumsum,
    "ΔList(": f_dlist,
    "randInt(": f_randint,
    "toString(": f_tostring,
}


# --------------------------------------------------------------------------
# Public API
# --------------------------------------------------------------------------

def run_program(path, model="84p", script=(), max_steps=2_000_000, *,
                start_line=True, block_limit=500, max_call_depth=100,
                getkey_limit=10000, seed=0):
    """Run PROGRAM.txt (other programs are loaded from NAME.txt in the same dir).

    script: list of items consumed in order --
        'menu:N'  choose item N (1-based) at a Menu(
        'key:N'   value returned by the next getKey that polls while it is next
        any other string: text typed at an Input/Prompt ('text:...' forces text,
        'tok:...' tokenizes the typed text in smart mode instead of letter-by-letter)
    """
    sim = Sim(path, model=model, script=script, max_steps=max_steps,
              start_line=start_line, block_limit=block_limit,
              max_call_depth=max_call_depth, getkey_limit=getkey_limit, seed=seed)
    return sim.run()


def run_text(text, model="84p", script=(), name="TEST", programs=None, **kw):
    """Convenience: run TI-BASIC source text (plus optional {NAME: source} subprograms)."""
    with tempfile.TemporaryDirectory() as d:
        for n, src in {name: text, **(programs or {})}.items():
            with open(os.path.join(d, n.upper() + ".txt"), "w", encoding="utf-8") as fh:
                fh.write(src)
        return run_program(os.path.join(d, name.upper() + ".txt"), model=model,
                           script=script, **kw)


def lint_program(path, model="84p"):
    tvmodel, W, H, _, _ = MODELS[model]
    tz = Tokenizer(tvmodel)
    name = os.path.splitext(os.path.basename(path))[0].upper()
    return Program(name, path, tz, W).lint


# --------------------------------------------------------------------------
# Text rendering of results
# --------------------------------------------------------------------------

def format_transcript(res, snapshots=False):
    out = []
    for e in res.transcript:
        t = e["type"]
        loc = f"L{e.get('line', 0)}" + (f"@{e['prgm']}" if e.get("prgm") else "")
        if t == "snapshot":
            if snapshots:
                rows = e["rows"]
                w = len(rows[0]) if rows else 0
                where = f"line {e['line']}" + (f" in prgm{e['prgm']}" if e.get("prgm") else "")
                out.append(f"{'':10} screen at {e['reason']} ({where})")
                out.append(f"{'':10} +{'-' * w}+")
                out.extend(f"{'':10} |{r}|" for r in rows)
                out.append(f"{'':10} +{'-' * w}+")
            continue
        if t == "disp":
            out.append(f"{loc:10} DISP   {e['text']}")
        elif t == "pause":
            out.append(f"{loc:10} PAUSE  {e['text'] if e.get('text') is not None else ''}")
        elif t == "output":
            out.append(f"{loc:10} OUTPUT ({e['row']},{e['col']}) {e['text']}")
        elif t == "input":
            out.append(f"{loc:10} INPUT  {e['prompt']}{e['typed']}   -> {e['var']}")
        elif t == "menu":
            items = " ".join(f"{i}:{x}" for i, x in enumerate(e["items"], 1))
            ch = e.get("chosen")
            out.append(f"{loc:10} MENU   [{e['title']}] {items}  => "
                       + (f"{ch} (Lbl {e['label']})" if ch else "(waiting)"))
        elif t == "key":
            out.append(f"{loc:10} KEY    {e['code']}")
        elif t == "clrhome":
            out.append(f"{loc:10} CLRHOME")
        elif t == "call":
            out.append(f"{loc:10} CALL   prgm{e['prgm_called']}")
        elif t == "end":
            out.append(f"{loc:10} END")
        elif t == "exhausted":
            out.append(f"{loc:10} SCRIPT EXHAUSTED (waiting for {e['waiting_for']})")
        elif t == "error":
            out.append(f"{loc:10} ERROR  {e['error']}")
    out.append("")
    out.append(f"stopped: {res.stopped}   steps: {res.steps}   unused script items: "
               f"{res.unused_script_items}   goto leaks: {res.leak_count}   "
               f"input wrapped lines: {res.stats.get('input_wrapped_lines', 0)}")
    if res.error:
        out.append(f"error: {res.error}")
    if res.warning_counts:
        out.append(f"warnings ({sum(res.warning_counts.values())} total, "
                   f"{len(res.warning_counts)} distinct):")
        for w, c in res.warning_counts.items():
            out.append(f"  {w}" + (f"   (x{c})" if c > 1 else ""))
    return "\n".join(out)


def _load_script(arg):
    if arg is None:
        return []
    if arg.lstrip().startswith("["):
        return json.loads(arg)
    with open(arg, encoding="utf-8") as fh:
        return json.load(fh)


def main(argv=None):
    ap = argparse.ArgumentParser(description="TI-84 Plus / CE TI-BASIC subset simulator")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="run a program with a scripted session")
    r.add_argument("program")
    r.add_argument("--model", default="84p", choices=sorted(MODELS))
    r.add_argument("--script", help="JSON file (or inline JSON list) of script items")
    r.add_argument("--snapshots", action="store_true", help="print screen snapshots")
    r.add_argument("--max-steps", type=int, default=2_000_000)
    r.add_argument("--no-start-line", action="store_true",
                   help="do not put 'prgmNAME' on the first screen row")
    r.add_argument("--json", action="store_true", help="dump the full result as JSON")
    li = sub.add_parser("lint", help="static checks only")
    li.add_argument("program")
    li.add_argument("--model", default="84p", choices=sorted(MODELS))
    a = ap.parse_args(argv)
    if a.cmd == "lint":
        try:
            ws = lint_program(a.program, a.model)
        except TIError as e:
            print(f"{e.prefix}{e.code}: {e.detail}")
            return 1
        print("\n".join(ws) if ws else "no lint warnings")
        return 1 if ws else 0
    res = run_program(a.program, model=a.model, script=_load_script(a.script),
                      max_steps=a.max_steps, start_line=not a.no_start_line)
    if a.json:
        print(json.dumps(res.to_json(), ensure_ascii=False, indent=1))
    else:
        print(format_transcript(res, a.snapshots))
    return 1 if res.error else 0


if __name__ == "__main__":
    sys.exit(main())
