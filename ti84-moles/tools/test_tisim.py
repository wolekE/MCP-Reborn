#!/usr/bin/env python3
"""Self-tests for tisim.py.

Run:  python3 -I tools/test_tisim.py        (plain runner, no deps)
  or: python3 -m pytest tools/test_tisim.py  (if pytest is installed)
"""

import os
import sys
import tempfile
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tisim import fmt_num, lint_program, run_text  # noqa: E402

D = Decimal


def run(src, script=(), **kw):
    kw.setdefault("start_line", False)
    return run_text(src, script=script, **kw)


def ok(res):
    assert res.error is None, res.error
    return res


def has_warning(res, text):
    return any(text in w for w in res.warnings)


# ---------------------------------------------------------------- arithmetic

def test_precedence_and_implicit_multiplication():
    r = ok(run("2+3*4→A\n⁻2^2→B\n3→X\n2X→C\n37→K\n10int(K/10)→D\n"
               "{5,6,7}→ʟMRC\n2→Y\n4→Z\nZʟMRC(Y)→E\n(X)(Y)→F\n1/2X→G\n2^3^2→H\n"
               "2⁻3→I\n1<2<3→J\n3+4=7→L\nXint(2.5)→M\n2(3+4)→N\n5-2-1→O\n12/2/3→P\n"
               "2ʟMRC→ʟQ\nX²+1→Q\n"))
    v = r.vars
    assert v["A"] == 14
    assert v["B"] == -4                 # negation binds looser than ^
    assert v["C"] == 6
    assert v["D"] == 30
    assert v["E"] == 24                 # Z * ʟMRC(Y)
    assert v["F"] == 6
    assert v["G"] == D("1.5")           # (1/2)*X: implicit mult same level as /
    assert v["H"] == 64                 # left to right
    assert v["I"] == -6
    assert v["J"] == 1
    assert v["L"] == 1                  # relational below +
    assert v["M"] == 6
    assert v["N"] == 14
    assert v["O"] == 2
    assert v["P"] == 2
    assert v["ʟQ"] == [10, 12, 14]
    assert v["Q"] == 10


def test_binary_minus_as_negation_is_syntax_error():
    r = run("-5→A\n")
    assert r.error.startswith("ERR:SYNTAX at line 1: -5→A"), r.error


def test_and_or_do_not_short_circuit():
    r = run("0→A\nIf A and ʟZZ(5)\nDisp 1\n")
    assert r.error.startswith("ERR:UNDEFINED at line 2"), r.error
    r = run('1→A\nIf A or sub("AB",3,1)="X"\nDisp 1\n')
    assert r.error.startswith("ERR:DOMAIN at line 2"), r.error
    r = ok(run("0 and 1→A\n2 or 0→B\n1 xor 1→C\n"))
    assert (r.vars["A"], r.vars["B"], r.vars["C"]) == (0, 1, 0)


def test_precision_and_rounding():
    r = ok(run("1/3*3→A\nround(2.25,1)→B\nint(⁻2.5)→C\nlog(1000)→D\niPart(⁻2.5)→E\n"
               "fPart(⁻2.5)→F\nround(⁻2.5,0)→G\n10^(3)→H\n1/3→I\n2/3→J\nround(1/3)→K\n"
               ".1+.2-.3→L\n"))
    v = r.vars
    assert v["A"] == D("0.99999999999999")   # 14 digit arithmetic
    assert fmt_num(v["A"]) == "1"            # ...but displays as 1
    assert v["B"] == D("2.3")                 # half away from zero
    assert v["C"] == -3
    assert v["D"] == 3 and str(v["D"]) == "3"
    assert v["E"] == -2
    assert v["F"] == D("-0.5")
    assert v["G"] == -3
    assert v["H"] == 1000
    assert fmt_num(v["I"]) == ".3333333333"
    assert fmt_num(v["J"]) == ".6666666667"
    assert v["K"] == D("0.333333333")
    assert v["L"] == 0


def test_number_formatting():
    assert fmt_num(D("6.022E23")) == "6.022ᴇ23"
    assert fmt_num(D("3.011E23")) == "3.011ᴇ23"
    assert fmt_num(D("-0.5")) == "⁻.5"
    assert fmt_num(D("0.001")) == ".001"
    assert fmt_num(D("0.00099")) == "9.9ᴇ⁻4"
    assert fmt_num(D("12345678901")) == "1.23456789ᴇ10"
    assert fmt_num(D("1234567890")) == "1234567890"
    assert fmt_num(D("2.00")) == "2"
    assert fmt_num(D("1.9984")) == "1.9984"


def test_overflow_and_domain_errors():
    assert run("10^(99)*10→A\n").error.startswith("ERR:OVERFLOW")
    assert run("1/0→A\n").error.startswith("ERR:DIVIDE BY 0")
    assert run("log(0)→A\n").error.startswith("ERR:DOMAIN")
    assert run('"A"+1→A\n').error.startswith("ERR:DATA TYPE")


def test_expr_on_typed_number():
    r = ok(run('Input "N?",Str1\nexpr(Str1)→A\nInput "X?",B\n', ["6.022ᴇ23", "0.500*6.022ᴇ23"]))
    assert r.vars["A"] == D("6.022E23")
    assert r.vars["B"] == D("3.011E23")
    assert fmt_num(r.vars["B"]) == "3.011ᴇ23"
    # letter E is a variable, not the EE key -> warning
    r = ok(run("Input X\n", ["3.01E23"]))
    assert has_warning(r, "uses the letter E")
    assert run('"→Str1\nexpr(Str1)\n').error.startswith("ERR:SYNTAX")
    assert run('""→Str1\nexpr(Str1)\n').error.startswith("ERR:SYNTAX")
    assert run("Input A\n", [""]).error.startswith("ERR:SYNTAX at line 1")


# ---------------------------------------------------------------- control flow

def test_for_skip_when_start_past_end():
    r = ok(run('0→C\nFor(I,5,1)\nC+1→C\nDisp "NO"\nEnd\n'
               "For(J,1,3)\nC+1→C\nEnd\n"
               "For(K,3,1,⁻1)\nEnd\n"
               "For(L,1,0)\nFor(M,1,2)\nEnd\nC+100→C\nEnd\n"))
    assert r.vars["C"] == 3
    assert r.vars["I"] == 5          # stored start, body skipped
    assert r.vars["J"] == 4          # first value past end
    assert r.vars["K"] == 0
    assert "NO" not in r.displayed()


def test_repeat_runs_at_least_once_and_while_tests_at_top():
    r = ok(run("0→A\nRepeat 1\nA+1→A\nEnd\n0→B\nWhile 0\nB+1→B\nEnd\n"
               "0→C\nRepeat C≥3\nC+1→C\nEnd\n0→D\nWhile D<5\nD+1→D\nEnd\n"))
    assert (r.vars["A"], r.vars["B"], r.vars["C"], r.vars["D"]) == (1, 0, 3, 5)


def test_nested_if_then_else_skipping():
    src = """0→A
If 0
Then
If 1
Then
Disp "BAD1"
Else
Disp "BAD2"
End
For(I,1,3)
Disp "BAD3"
End
While 1
End
Repeat 0
End
Disp "BAD4"
Else
1→A
If 0:Then
Disp "BAD5"
Else
A+10→A
End
End
If 0
Disp "BAD6"
If 1:A+100→A
If 0:Then:Disp "BAD7":End
Disp "OK"
"""
    r = ok(run(src))
    assert r.vars["A"] == 111
    assert r.displayed() == ["OK"]


def test_single_line_if_skips_exactly_one_statement():
    r = ok(run("0→A\nIf 0:A+1→A:A+10→A\nIf 0\nDelVar BA+5→A\n"))
    assert r.vars["A"] == 10          # DelVar chain is one statement


def test_goto_out_of_block_leak_warning():
    src = """0→A
Lbl S
A+1→A
If A<4
Then
For(I,1,5)
If I=2
Goto S
End
End
Disp A
"""
    r = ok(run(src))
    assert r.vars["A"] == 4
    assert r.leak_count == 3
    assert has_warning(r, "goto out of 2 open blocks at line 8")
    assert has_warning(r, "goto out of 6 open blocks at line 8")   # leak accumulates


def test_goto_leak_eventually_err_memory():
    r = run("Lbl A\nWhile 1\nGoto A\nEnd\n", block_limit=50)
    assert r.error.startswith("ERR:MEMORY"), r.error


def test_goto_missing_label():
    r = run("Goto ZZ\n")
    assert r.error.startswith("ERR:LABEL at line 1: Goto ZZ"), r.error
    assert any("undefined label ZZ" in w for w in r.lint)


def test_end_without_block_is_error():
    assert run("Disp 1\nEnd\n").error.startswith("ERR:SYNTAX at line 2")


def test_stop_and_return_at_top_level():
    r = ok(run('Disp "A"\nReturn\nDisp "B"\n'))
    assert r.displayed() == ["A"]
    r = ok(run('Disp "A"\nStop\nDisp "B"\n'))
    assert r.displayed() == ["A"]


def test_self_recursive_program_with_dispatch_variable():
    src = """If θ=⁻1:Then
A+1→A
If A<5:prgmREC
Return
End
0→A
⁻1→θ
prgmREC
0→θ
Disp A
"""
    r = ok(run(src, name="REC"))
    assert r.vars["A"] == 5
    assert r.leak_count == 0                     # Return discards open blocks silently
    assert r.displayed() == ["5"]


def test_subprogram_call_and_implicit_return():
    r = ok(run('Disp "MAIN"\nprgmSUB\nDisp "BACK",A\n', programs={
        "SUB": 'For(I,1,3)\nIf I=2:Then\n7→A\nReturn\nEnd\nEnd\n'}))
    assert r.displayed() == ["MAIN", "BACK", "7"]


def test_subprogram_missing():
    assert run("prgmNOPE\n").error.startswith("ERR:UNDEFINED at line 1")


def test_menu_jumping_and_menu_errors():
    # NB: "Pause " needs its trailing space (see test_keyword_without_trailing_space...)
    src = "\n".join(['Lbl M', 'Menu("MAIN","ONE",A,"TWO",B,"QUIT",Q', 'Lbl A',
                     'Disp "GOT ONE"', 'Pause ', 'Goto M', 'Lbl B', 'Disp "GOT TWO"',
                     'Pause ', 'Goto M', 'Lbl Q']) + "\n"
    r = ok(run(src, ["menu:2", "menu:1", "menu:3"]))
    assert r.displayed() == ["GOT TWO", "GOT ONE"]
    menus = [e for e in r.transcript if e["type"] == "menu"]
    assert [m["chosen"] for m in menus] == [2, 1, 3]
    assert menus[0]["items"] == ["ONE", "TWO", "QUIT"]
    assert r.unused_script_items == 0
    snap = [s for s in r.screens if s["reason"] == "Menu("][0]["rows"]
    assert snap[0].startswith("MAIN") and snap[2].startswith("2:TWO")
    # script mismatch and exhaustion
    r = run(src, ["Na"])
    assert r.error.startswith("SIM:SCRIPT MISMATCH"), r.error
    r = run(src, ["menu:1"])
    assert r.error is None and r.stopped == "script exhausted"
    # long text warnings and too many items
    r = run('Menu("A VERY LONG MENU TITLE","SHORT",A,"AN ITEM THAT IS LONG",A\nLbl A\n',
            ["menu:1"])
    assert has_warning(r, "Menu title too long") and has_warning(r, "Menu item too long")
    r = run('Menu("T","1",A,"2",A,"3",A,"4",A,"5",A,"6",A,"7",A,"8",A\nLbl A\n', ["menu:1"])
    assert r.error.startswith("ERR:ARGUMENT")


def test_menu_hides_unseen_result():
    src = 'Lbl M\nMenu("M","GO",A,"QUIT",Q\nLbl A\nDisp "ANSWER 42"\nGoto M\nLbl Q\n'
    r = ok(run(src, ["menu:1", "menu:2"]))
    assert has_warning(r, "unseen line cleared by Menu(: ANSWER 42")


def test_menu_jump_out_of_block_counts_as_leak():
    src = 'Lbl M\nWhile 1\nMenu("M","A",M,"Q",Q\nEnd\nLbl Q\n'
    r = ok(run(src, ["menu:1", "menu:2"]))
    assert r.leak_count == 2
    assert has_warning(r, "goto out of 1 open blocks at line 3 (Menu()")


# ---------------------------------------------------------------- strings

def test_string_operations():
    src = '''"AL2(SO4)3→Str1
length(Str1)→A
sub(Str1,3,1)→Str2
inString(Str1,"SO")→B
inString(Str1,"Z")→C
inString(Str1,"O",6)→D
""→Str3
length(Str3)→E
Str3+"X"+Str3→Str4
(Str2≠"2")→F
(Str2="2")→G
inString("ABC","")→H
sub(Str1,1,2)+"!"→Str5
'''
    r = ok(run(src))
    v = r.vars
    assert v["A"] == 9 and v["Str2"] == "2" and v["B"] == 5 and v["C"] == 0
    assert v["D"] == 6            # search starts at position 6, which is the O
    assert v["E"] == 0 and v["Str4"] == "X"
    assert v["F"] == 0 and v["G"] == 1 and v["H"] == 1
    assert v["Str5"] == "AL!"
    assert run('sub("ABC",3,2)\n').error.startswith("ERR:DOMAIN")
    assert run('sub("ABC",0,1)\n').error.startswith("ERR:DOMAIN")
    assert run("Str7\n").error.startswith("ERR:UNDEFINED")
    assert run('"A"<"B"\n').error.startswith("ERR:DATA TYPE")


def test_instring_start_position():
    r = ok(run('inString("ABCABC","B",3)→A\ninString("ABCABC","B",6)→B\n'))
    assert r.vars["A"] == 5 and r.vars["B"] == 0
    assert run('inString("AB","B",0)\n').error.startswith("ERR:DOMAIN")


def test_typed_strings_count_tokens_not_chars():
    r = ok(run('Input "F?",Str1\nlength(Str1)→A\nsub(Str1,2,1)→Str2\n', ["CaSO4*2H2O"]))
    assert r.vars["A"] == 10 and r.vars["Str2"] == "a"
    assert r.vars["Str1"] == "CaSO4*2H2O"


def test_store_arrow_inside_string_literal():
    r = run('Disp "MOL→GRAMS"\n')
    assert any("store arrow inside string literal" in w for w in r.lint)
    assert r.error.startswith("ERR:SYNTAX at line 1"), r.error
    # an arrow silently ends the string: "X→Y" stores "X" in Y -> DATA TYPE
    r = run('"G→MOL"→Str1\n')
    assert any("store arrow inside string literal" in w for w in r.lint)
    assert r.error is not None
    # legitimate omitted closing quote: no warning
    r = ok(run('"ABC→Str1\nDisp Str1\n'))
    assert not any("store arrow" in w for w in r.warnings)
    assert r.vars["Str1"] == "ABC"


def test_colon_inside_string_is_text():
    r = ok(run('Disp "A:B":Disp "C"\n'))
    assert r.displayed() == ["A:B", "C"]


def test_omitted_closing_parens_and_quotes():
    r = ok(run('round(1.2345,2→A\nsub("ABCD",2,2→Str1\n{1,2,3→ʟA\nDisp "HI\n'))
    assert r.vars["A"] == D("1.23") and r.vars["Str1"] == "BC" and r.vars["ʟA"] == [1, 2, 3]
    assert r.displayed() == ["HI"]


# ---------------------------------------------------------------- lists

def test_lists():
    src = """{1,2,3}→ʟA
4→ʟA(4)
dim(ʟA)→A
5→dim(ʟB)
dim(ʟB)→B
2→dim(ʟA)
ʟA=2→ʟC
sum(seq(X²,X,1,4))→C
{1.98,3.01,2}→ʟD
max(abs(ʟD-round(ʟD,0)))→D
sum(ʟA)→E
min(ʟD)→F
max(3,7)→G
DelVar ʟB
DelVar ʟB
{1,2}+{10,20}→ʟE
"""
    r = ok(run(src))
    v = r.vars
    assert v["A"] == 4 and v["B"] == 5
    assert v["ʟA"] == [1, 2]
    assert v["ʟC"] == [0, 1]
    assert v["C"] == 30
    assert v["D"] == D("0.02")
    assert v["E"] == 3 and v["F"] == D("1.98") and v["G"] == 7
    assert "ʟB" not in v
    assert v["ʟE"] == [11, 22]
    assert v["X"] == 0                       # seq( restores its variable
    assert run("{1,2}→ʟA\n9→ʟA(4)\n").error.startswith("ERR:INVALID DIM")
    assert run("{1,2}→ʟA\nʟA(3)\n").error.startswith("ERR:INVALID DIM")
    assert run("ʟNO(1)\n").error.startswith("ERR:UNDEFINED")
    assert run("5→ʟNO(1)\n").error.startswith("ERR:UNDEFINED")
    assert run("{1,2}+{1,2,3}\n").error.startswith("ERR:DIM MISMATCH")


def test_list_name_greedy_five_chars():
    r = ok(run("{7,8}→ʟABCDE\n2→F\nʟABCDEF→ʟX\n"))
    assert r.vars["ʟX"] == [14, 16]          # ʟABCDE * F
    assert any("list name longer than 5" in w for w in r.lint)


# ---------------------------------------------------------------- screen

def test_disp_truncation_warning():
    r = ok(run('ClrHome\nDisp "THIS LINE IS TOO LONG"\n'))
    assert has_warning(r, "Disp line too long (21>16)")
    assert r.screens[-1]["rows"][0] == "THIS LINE IS TO…"
    r = ok(run('ClrHome\nDisp "THIS LINE IS TOO LONG"\n', model="ce"))
    assert not has_warning(r, "too long")


def test_input_wrapping():
    r = ok(run('ClrHome\nInput "ENTER FORMULA:",Str1\n', ["Sn(C2H3O2)2"]))
    inp = [e for e in r.transcript if e["type"] == "input"][0]
    assert inp["wrapped_lines"] == 1
    assert r.stats["input_wrapped_lines"] == 1
    rows = [s for s in r.screens if s["reason"] == "Input"][0]["rows"]
    assert rows[0] == "ENTER FORMULA:Sn"
    assert rows[1].startswith("(C2H3O2)2")
    r = ok(run('Input "A PROMPT THAT IS WAY TOO LONG",A\n', ["1"]))
    assert has_warning(r, "Input prompt longer than the screen")


def test_unseen_line_scroll_warning():
    src = 'ClrHome\nFor(I,1,9)\nDisp I\nEnd\nPause \n'
    r = ok(run(src))
    assert has_warning(r, "unseen line scrolled off: 1 [shown at line 3]")
    assert not has_warning(r, "scrolled off: 2 ")
    # with a Pause after 8 lines, nothing is lost
    r = ok(run('ClrHome\nFor(I,1,8)\nDisp I\nEnd\nPause \nDisp 9\nPause \n'))
    assert not any("unseen" in w for w in r.warnings)
    # CE has 10 rows
    r = ok(run(src, model="ce"))
    assert not any("unseen" in w for w in r.warnings)


def test_clrhome_of_unseen_text_warns():
    r = ok(run('Disp "RESULT"\nClrHome\nDisp "NEXT"\n'))
    assert has_warning(r, "unseen line cleared: RESULT")


def test_start_line_and_done():
    r = ok(run_text('Disp "HI"\n'))
    rows = r.screens[-1]["rows"]
    assert rows[0].startswith("prgmTEST") and rows[1].startswith("HI")
    assert rows[2].rstrip().endswith("Done")


def test_output_and_snapshot_width():
    r = ok(run('ClrHome\nOutput(2,5,"HELLO")\nOutput(3,15,"ABCD")\nOutput(1,1,12.5)\nPause \n'))
    rows = [s for s in r.screens if s["reason"] == "Pause"][0]["rows"]
    assert rows[0].startswith("12.5")
    assert rows[1] == "    HELLO       "
    assert rows[2].endswith("AB") and rows[3].startswith("CD")
    assert all(len(x) == 16 for x in rows) and len(rows) == 8
    assert run("Output(9,1,1)\n").error.startswith("ERR:DOMAIN")


def test_getkey_scripted():
    src = "0→K\nRepeat K\ngetKey→K\nEnd\nDisp K\nRepeat getKey:End\n"
    r = ok(run(src, ["key:105", "key:45"]))
    assert r.vars["K"] == 105
    assert [e["code"] for e in r.transcript if e["type"] == "key"] == [105, 45]
    r = run(src, ["key:105", "menu:1"])
    assert r.error.startswith("SIM:GETKEY STARVATION"), r.error
    r = run(src, ["key:105"])
    assert r.error is None and r.stopped == "script exhausted"


def test_pause_does_not_consume_script():
    r = ok(run('Pause "HELLO"\nInput A\n', ["5"]))
    assert r.vars["A"] == 5 and r.unused_script_items == 0
    assert [s["reason"] for s in r.screens][:2] == ["Pause", "Input"]


def test_window_vars_per_model():
    r84 = ok(run("ΔX→A\n"))
    rce = ok(run("ΔX→A\n", model="ce"))
    assert r84.vars["A"] == D(20) / D(94) or abs(r84.vars["A"] - D("0.21276595744681")) < D("1E-13")
    assert abs(rce.vars["A"] - D("0.075757575757576")) < D("1E-13")


# ---------------------------------------------------------------- lint / tokens

def test_keyword_without_trailing_space_is_letters():
    r = run('Disp "A"\nPause\n')
    assert any("'Pause '" in w for w in r.lint), r.lint
    assert r.error.startswith("ERR:SYNTAX at line 2: Pause")
    r = ok(run('Disp "A"\nPause \n'))


def test_space_outside_string():
    r = run("1 + 2→A\n")
    assert any("space token outside a string" in w for w in r.lint)
    assert r.error.startswith("ERR:SYNTAX")


def test_tostring_only_on_ce():
    r = ok(run('toString(3.5)+"G"→Str1\n', model="ce"))
    assert r.vars["Str1"] == "3.5G"
    r = run('toString(3.5)→Str1\n', model="84p")   # tokenizes as letters on the 84+
    assert r.error.startswith("ERR:SYNTAX") and r.lint


def test_error_message_has_line_and_source():
    r = run('Disp "OK"\n\n1→A:B/0→C\n')
    assert r.error == "ERR:DIVIDE BY 0 at line 3: 1→A:B/0→C", r.error
    r = run('prgmSUB\n', programs={"SUB": "Disp 1\nsub(\"A\",2,1)\n"})
    assert r.error.startswith('ERR:DOMAIN at line 2 in prgmSUB: sub("A",2,1)'), r.error


def test_max_steps():
    r = run("Lbl A\nGoto A\n", max_steps=1000)
    assert r.error.startswith("SIM:MAX STEPS")


def test_lint_program_api_and_cli():
    import subprocess
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "LINTME.txt")
        with open(p, "w", encoding="utf-8") as fh:
            fh.write('Goto Q\nLbl A\nLbl A\nDisp "→"\n')
        ws = lint_program(p)
        assert any("undefined label Q" in w for w in ws)
        assert any("duplicate label A" in w for w in ws)
        s = os.path.join(d, "s.json")
        with open(s, "w") as fh:
            fh.write('["menu:1"]')
        tool = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tisim.py")
        out = subprocess.run([sys.executable, "-I", tool, "run", p, "--script", s,
                              "--snapshots"], capture_output=True, text=True)
        assert out.returncode == 1 and "ERR:LABEL" in out.stdout, out.stdout + out.stderr


# ---------------------------------------------------------------- integration

MINI_MM = r'''"H C N O S Cu→Str9
{1.008,12.01,14.01,16.00,32.07,63.55→ʟAM
Input "FORMULA?",Str1
length(Str1)→N
0→M
1→I
While I≤N
sub(Str1,I,1)→Str2
I+1→I
If I≤N
Then
If inString("abcdefghijklmnopqrstuvwxyz",sub(Str1,I,1))
Then
Str2+sub(Str1,I,1)→Str2
I+1→I
End
End
If length(Str2)=1
Str2+" "→Str2
0→C
1→F
While F
0→F
If I≤N
Then
inString("0123456789",sub(Str1,I,1))→D
If D
Then
10C+D-1→C
I+1→I
1→F
End
End
End
If C=0:1→C
inString(Str9,Str2)→J
M+CʟAM((J+1)/2)→M
End
Disp M
Input "GRAMS?",G
G/M→X
Disp X
Disp round(X,2)
'''


def test_integration_mini_molar_mass_parser():
    # practice cases (not test answers): 36.0 g H2O -> 2.00 mol
    r = ok(run(MINI_MM, ["H2O", "36.0"]))
    assert r.vars["M"] == D("18.016")
    assert r.displayed()[-1] == "2"
    assert abs(r.vars["X"] - D("1.998223801")) < D("1E-9")
    r = ok(run(MINI_MM, ["CO2", "22.005"]))
    assert r.vars["M"] == D("44.01")
    assert r.vars["X"] == D("0.5")
    r = ok(run(MINI_MM, ["CuSO4", "1"]))
    assert r.vars["M"] == D("159.62")


EMPIRICAL = r'''{85.6,14.4}→ʟP
{12.01,1.008}→ʟAM
ʟP/ʟAM→ʟR
ʟR/min(ʟR)→ʟR
1→M
While max(abs(MʟR-round(MʟR,0)))≥.1 and M<5
M+1→M
End
round(MʟR,0)→ʟN
Input "BEFORE?",B
Input "AFTER?",A
(B-A)/18.016→W
A/159.62→C
round(W/C,0)→X
'''


def test_integration_empirical_and_hydrate_practice_cases():
    # practice cases (not test answers): 85.6% C, 14.4% H -> CH2;
    # CuSO4 hydrate 5.00 g -> 3.20 g -> x = 5
    r = ok(run(EMPIRICAL, ["5.00", "3.20"]))
    assert r.vars["ʟN"] == [1, 2] and r.vars["M"] == 1
    assert r.vars["X"] == 5


# ---------------------------------------------------------------- runner

def _main():
    tests = [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_") and callable(f)]
    failed = 0
    for n, f in tests:
        try:
            f()
            print(f"PASS {n}")
        except Exception as e:  # noqa: BLE001
            failed += 1
            import traceback
            print(f"FAIL {n}: {e!r}")
            traceback.print_exc()
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(_main())
