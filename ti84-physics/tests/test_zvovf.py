"""Tests for prgmZVOVF: the VOVFSTA solver (A, PHYSOLVE option 1) and its free-fall mode
(B, K=2: A = -9.8 filled in automatically).

Every run is checked three ways:
  * clean: no calculator error, no LEAK / SCROLL / TRUNCATED, program finished,
  * reference: the final screen (SUMMARY or message) is exactly what reference/zvovf.py
    says, row for row, and every summary value equals fmt3(reference value),
  * hand values: the expected numbers worked out by hand (3 significant figures).
"""
import math
import random
import sys
from pathlib import Path

from harness import (Checker, run, assert_clean, fmt3, find_screen, screen_values,
                     last_screen_values, all_values, expect, ROOT)
import zvovf as ref
from common import UNKNOWN

U = UNKNOWN
c = Checker("zvovf")

# the five variables in input order, and their names on screen
VARS = ["V0", "VF", "S", "T", "A"]


# ------------------------------------------------------------------ running
def run_a(v0, vf, s, t, a, **kw):
    """Section A through the real menus: PHYSOLVE 1 VOVFSTA SOLVER, 5 inputs, 7 QUIT."""
    return run([1, v0, vf, s, t, a, 7], **kw)


def run_b(v0, vf, s, t, **kw):
    """Section B: ZVOVF called the way ZFREE calls it (2→K), inputs V0, VF, S, T only."""
    return run([v0, vf, s, t], program="ZVOVF", init_vars={"K": 2}, **kw)


def rows(screen):
    return [r for r in screen if r]


def check_run(res, r, context=""):
    """Clean run, final screen identical to the reference, summary values = fmt3(ref)."""
    assert_clean(res, context=context)
    final = rows(res.screens[-1])
    assert final == r["lines"], (f"{context}\nfinal screen differs from reference:\n"
                                 f"  screen: {final}\n  ref:    {r['lines']}\n{res.text()}")
    if r["kind"] == "summary":
        vals = {n: (v, u) for n, v, u in screen_values(res.screens[-1])}
        assert set(vals) == set(r["summary"]), (context, set(vals), set(r["summary"]))
        for name, (x, unit) in r["summary"].items():
            assert vals[name][0] == fmt3(x), f"{context} {name}: {vals[name][0]} vs ref {fmt3(x)}"
            assert vals[name][1] == unit, f"{context} {name} unit: {vals[name][1]!r} vs {unit!r}"
        # every step result shown on a step screen matches the reference
        av = all_values(res)
        for name, x in r["steps"]:
            assert fmt3(x) in av.get(name, []), f"{context} step {name}={fmt3(x)} not shown: {av.get(name)}"
    else:
        # message screens must not contain anything that parses as NAME = VALUE
        assert screen_values(res.screens[-1]) == [], f"{context} message looks like a value line"
    # cases 2/5: the STEP 1 explanation rows and the root explanation under ZQUAD's output
    if r.get("step1_rows") is not None:
        s1 = rows(find_screen(res, "STEP 1 - FIND T"))
        n = len(r["step1_rows"])
        assert s1[-n:] == r["step1_rows"], f"{context} step 1 rows: {s1} vs ref {r['step1_rows']}"
    if r.get("quad_rows") is not None:
        q = rows(find_screen(res, "SOLVE QUADRATIC FOR T"))
        n = len(r["quad_rows"])
        assert q[-n:] == r["quad_rows"], f"{context} quadratic rows: {q} vs ref {r['quad_rows']}"
    return res


def summary(res):
    return last_screen_values(res)


def kinematics_ok(v0, vf, s, t, a, label):
    """The five VOVFSTA equations hold for a solution (independent physics check)."""
    v0, vf, s, t, a = (float(x) for x in (v0, vf, s, t, a))
    eqs = [(vf, v0 + a * t, "VF=V0+AT"),
           (s, v0 * t + 0.5 * a * t * t, "S=V0T+(1/2)AT²"),
           (s, vf * t - 0.5 * a * t * t, "S=VFT-(1/2)AT²"),
           (vf * vf, v0 * v0 + 2 * a * s, "VF²=V0²+2AS"),
           (s, 0.5 * (v0 + vf) * t, "S=(1/2)(V0+VF)T")]
    for lhs, rhs, name in eqs:
        scale = abs(lhs) + abs(rhs) + abs(v0 * t) + abs(a * t * t) + abs(v0 * v0) + abs(vf * vf) + 1e-12
        assert abs(lhs - rhs) <= 1e-9 * scale, f"{label}: {name} fails: {lhs} vs {rhs}"


def solutions(r):
    """All (v0, vf, s, t, a) solutions in a reference summary (1 or 2)."""
    sm = {k: v[0] for k, v in r["summary"].items()}
    if r["answers"] == 1:
        return [tuple(sm[k] for k in VARS)]
    out = []
    for n in (1, 2):
        if r["case"] == 2:
            out.append((sm["V0"], sm[f"VF(T{n})"], sm["S"], sm[f"T{n}"], sm["A"]))
        else:
            out.append((sm[f"V0(T{n})"], sm["VF"], sm["S"], sm[f"T{n}"], sm["A"]))
    return out


def solve_check(inputs, mode="A", context="", **kw):
    """Run (mode A through PHYSOLVE, or B with K=2), compare with the reference, return both."""
    if mode == "A":
        res = run_a(*inputs, **kw)
        r = ref.solve(*inputs, k=1)
    else:
        res = run_b(*inputs, **kw)
        r = ref.free_fall(*inputs)
    check_run(res, r, context=f"{mode} {inputs} {context}")
    if r["kind"] == "summary":
        for sol in solutions(r):
            kinematics_ok(*sol, label=f"{mode} {inputs}")
    return res, r


def with_unknowns(motion, pair):
    """The 5 inputs of a known motion with the two names in `pair` replaced by 999."""
    return [U if name in pair else motion[name] for name in VARS]


# ------------------------------------------------------------------ the required case
def t_required_case():
    res, r = solve_check([8.0, U, 120, U, 1.5])
    sv = summary(res)
    expect(sv["VF"], "20.6", "VF")            # hand: VF² = 64 + 2(1.5)(120) = 424 -> 20.6
    expect(sv["T"], "8.39", "T")              # hand: 0.75T²+8T-120=0 -> T = 8.39 (or -19.1)
    expect(sv["V0"], "8.00", "V0")
    expect(sv["S"], "120", "S")
    expect(sv["A"], "1.50", "A")
    q = find_screen(res, "SOLVE QUADRATIC FOR T")
    assert "0.750T²+8.00T-120=0" in q, q
    assert "T1 = -19.1 S" in q and "T2 = 8.39 S" in q, q          # both roots shown
    assert "T1<0 IS BEFORE THE START," in q and "SO T = 8.39 S" in q, q
    given = rows(find_screen(res, "GIVEN"))
    assert given == ["GIVEN", "V0 = 8.00 M/S", "S = 120 M", "A = 1.50 M/S²", "UNKNOWNS ARE T AND VF",
                     "1) T FROM S=V0T+(1/2)AT²", "   (IT HAS NO VF)", "2) VF FROM VF=V0+AT",
                     "   (NOW T IS KNOWN)"], given
    s1 = rows(find_screen(res, "STEP 1 - FIND T"))
    assert s1 == ["STEP 1 - FIND T", "USE S=V0T+(1/2)AT²", "(IT HAS NO VF)", "(120)=(8.00)T",
                  "  +(1/2)(1.50)T²", "T IS SQUARED, SO WRITE", "(1/2)AT²+V0T-S=0 AND USE",
                  "THE QUADRATIC FORMULA WITH", "A,B,C AS (1/2)A, V0, -S"], s1
    s2 = rows(find_screen(res, "STEP 2 - FIND VF"))
    assert s2 == ["STEP 2 - FIND VF", "USE VF=V0+AT", "(NOW T IS KNOWN)", "VF=(8.00)+(1.50)(8.39)",
                  "VF = 20.6 M/S"], s2
    assert rows(res.screens[-1])[-2:] == ["T FROM S=V0T+(1/2)AT²", "VF FROM VF=V0+AT"]
    assert res.calls.count("ZQUAD") == 1


# ------------------------------------------------------------------ all 10 unknown pairs
# Two motions worked out by hand (VF = V0+AT, S = V0T+(1/2)AT²):
#   M1: V0=12, A=-3, T=2  -> VF = 12-6 = 6,      S = 24-6 = 18
#   M2: V0=8,  A=1.5, T=4 -> VF = 8+6 = 14,      S = 32+12 = 44
M1 = {"V0": 12, "VF": 6, "S": 18, "T": 2, "A": -3}
M2 = {"V0": 8, "VF": 14, "S": 44, "T": 4, "A": 1.5}
PAIRS = {1: ("VF", "S"), 2: ("VF", "T"), 3: ("VF", "A"), 4: ("V0", "S"), 5: ("V0", "T"),
         6: ("V0", "A"), 7: ("S", "T"), 8: ("S", "A"), 9: ("T", "A"), 10: ("V0", "VF")}
# Hand-worked second answers where the quadratic has two positive roots:
#   M1 case 2: -1.5T²+12T-18=0 -> T²-8T+12=0 -> T = 2 or 6; VF(6) = 12-3(6) = -6
#   M2 case 5: -0.75T²+14T-44=0 -> T = 4 or 44/3 = 14.67; V0(44/3) = 14-1.5(44/3) = -8
TWO = {("M1", 2): {"T1": "2.00", "VF(T1)": "6.00", "T2": "6.00", "VF(T2)": "-6.00"},
       ("M2", 5): {"T1": "4.00", "V0(T1)": "8.00", "T2": "14.7", "V0(T2)": "-8.00"}}


def t_all_pairs():
    for mname, motion in (("M1", M1), ("M2", M2)):
        for case, pair in PAIRS.items():
            inputs = with_unknowns(motion, pair)
            res, r = solve_check(inputs, context=f"{mname} case {case}")
            assert r["case"] == case, (r["case"], case)
            sv = summary(res)
            u1, eq1, u2, eq2 = ref.CASES[case]
            if (mname, case) in TWO:
                assert r["answers"] == 2 and rows(res.screens[-1])[0] == "SUMMARY (2 ANSWERS)"
                for name, want in TWO[(mname, case)].items():
                    expect(sv[name], want, f"{mname} case {case} {name}")
            else:
                assert r["answers"] == 1, (mname, case)
                for name in VARS:   # every value recovered at 3 s.f. (hand values)
                    expect(sv[name], float(motion[name]), f"{mname} case {case} {name}")
            # the right equations are named on the GIVEN, step and SUMMARY screens
            given = rows(find_screen(res, "GIVEN"))
            assert f"1) {u1} FROM {eq1}" in given and f"2) {u2} FROM {eq2}" in given, given
            assert f"   (IT HAS NO {u2})" in given, given
            st1 = rows(find_screen(res, f"STEP 1 - FIND {u1}"))
            assert st1[1] == f"USE {eq1}" and st1[2] == f"(IT HAS NO {u2})", st1
            st2 = rows(find_screen(res, f"STEP 2 - FIND {u2}"))
            assert st2[1] == f"USE {eq2}", st2
            assert f"{u1} FROM {eq1}" in rows(res.screens[-1])


def t_case_table_matches_task():
    """The equation for the first unknown must not contain the second unknown."""
    letters = {"V0": "V0", "VF": "VF", "S": "S", "T": "T", "A": "A"}
    for case, (u1, eq1, u2, eq2) in ref.CASES.items():
        bare = eq1.replace("V0", "").replace("VF", "").replace("(1/2)", "")
        if u2 in ("V0", "VF"):
            assert u2 not in eq1, (case, eq1, u2)
        else:
            assert letters[u2] not in bare, (case, eq1, u2)
        assert set(PAIRS[case]) == {u1, u2}, case


# ------------------------------------------------------------------ quadratic root choice
def t_both_roots_positive():
    # v0 = 10 up, a = -9.8, s = 4 m up: 4.9T²-10T+4=0, B²-4AC = 100-78.4 = 21.6
    #   T = (10 -/+ 4.648)/9.8 = 0.546 s (going up) and 1.49 s (coming down), VF = +/-4.65 m/s.
    # (The task text says 0.583 s and 1.46 s; those do not satisfy S=4: see the check below.)
    t1 = (10 - math.sqrt(21.6)) / 9.8
    t2 = (10 + math.sqrt(21.6)) / 9.8
    assert abs(10 * t1 - 4.9 * t1 * t1 - 4) < 1e-12 and abs(10 * t2 - 4.9 * t2 * t2 - 4) < 1e-12
    assert abs(10 * 0.583 - 4.9 * 0.583 ** 2 - 4) > 0.15   # task's 0.583 s gives S = 4.17 m
    for mode, inputs in (("A", [10, U, 4, U, -9.8]), ("B", [10, U, 4, U])):
        res, r = solve_check(inputs, mode)
        sv = summary(res)
        expect(sv["T1"], "0.546", "T1")
        expect(sv["T2"], "1.49", "T2")
        expect(sv["VF(T1)"], "4.65", "VF(T1)")
        expect(sv["VF(T2)"], "-4.65", "VF(T2)")
        q = find_screen(res, "SOLVE QUADRATIC FOR T")
        assert "T1 = 0.546 S" in q and "T2 = 1.49 S" in q, q
        assert "T1 AND T2 ARE BOTH > 0," in q and "TWICE (EX. UP, THEN DOWN)." in q, q
        st2 = rows(find_screen(res, "STEP 2 - FIND VF"))
        assert "VF(T1) = 4.65 M/S" in st2 and "VF(T2) = -4.65 M/S" in st2, st2
        if mode == "B":
            last = rows(res.screens[-1])
            assert "VF(T1) = 4.65 M/S (UP)" in last and "VF(T2) = -4.65 M/S (DOWN)" in last, last


def t_two_answers_case5_free_fall():
    # ends moving down at 4.65 m/s, 1 m below the start: thrown up OR down at 1.42 m/s
    res, r = solve_check([U, -4.65, -1, U], "B")
    sv = summary(res)
    expect(sv["T1"], "0.329", "T1")
    expect(sv["T2"], "0.620", "T2")
    expect(sv["V0(T1)"], "-1.42", "V0(T1)")
    expect(sv["V0(T2)"], "1.42", "V0(T2)")
    assert "V0(T1) = -1.42 M/S (DOWN)" in rows(res.screens[-1])
    q = find_screen(res, "SOLVE QUADRATIC FOR T")
    assert "2 POSSIBLE STARTS (V0)." in q, q


def t_impossible_discriminant():
    # thrown up at 10 m/s never gets 10 m high: B²-4AC = 100 - 4(4.9)(10) = -96 < 0
    for mode, inputs in (("A", [10, U, 10, U, -9.8]), ("B", [10, U, 10, U])):
        res, r = solve_check(inputs, mode)
        assert r["code"] == "E5", r["code"]
        q = find_screen(res, "SOLVE QUADRATIC FOR T")
        assert "B²-4AC = -96.0" in q and "B²-4AC<0 SO NO REAL ROOT" in q, q
        assert rows(res.screens[-1])[0] == "IMPOSSIBLE"
        assert "IT NEVER GETS TO THAT S." in rows(res.screens[-1])
    # case 5: at the top (VF=0) but 5 m BELOW the start: V0² = VF²-2AS = -98 < 0
    for mode, inputs in (("A", [U, 0, -5, U, -9.8]), ("B", [U, 0, -5, U])):
        res, r = solve_check(inputs, mode)
        assert r["code"] == "E5" and "NO START VELOCITY CAN END" in rows(res.screens[-1])


def t_quadratic_edges():
    # S=0: thrown up at 10, back at the start: T1 = 0 is the start, T = 20/9.8 = 2.04 s, VF = -10
    res, r = solve_check([10, U, 0, U, -9.8])
    expect(summary(res)["T"], "2.04", "T")
    expect(summary(res)["VF"], "-10.0", "VF")
    assert "T1 IS 0 (THE START)," in find_screen(res, "SOLVE QUADRATIC FOR T")
    # S=0 but moving away (thrown down): only at the start -> message
    for inputs in ([-10, U, 0, U, -9.8], [0, U, 0, U, -9.8]):
        res, r = solve_check(inputs)
        assert r["code"] == "E6" and "S IS 0 ONLY AT THE START" in rows(res.screens[-1])
    # both roots negative: speeding up forward, never gets 5 m behind
    res, r = solve_check([20, U, -5, U, 9.8])
    assert r["code"] == "E6" and "NO ROOT IS AFTER THE START" in rows(res.screens[-1])
    # double root (B²-4AC = 0): thrown up at 19.6 just reaches 19.6 m
    # (regression ZVOVF-7: the double-root branch also says which T it uses)
    for mode, inputs in (("B", [19.6, U, 19.6, U]), ("A", [19.6, U, 19.6, U, -9.8])):
        res, r = solve_check(inputs, mode)
        expect(summary(res)["T"], "2.00", "T")
        expect(summary(res)["VF"], "0", "VF")
        q = rows(find_screen(res, "SOLVE QUADRATIC FOR T"))
        assert q[-3:] == ["ONE ROOT (B²-4AC IS 0).", "IT JUST REACHES S, VF IS 0", "SO T = 2.00 S"], q
    res, r = solve_check([U, -19.6, -19.6, U], "B")      # case 5 double root: started at rest
    expect(summary(res)["T"], "2.00", "T")
    expect(summary(res)["V0"], "0", "V0")
    q = rows(find_screen(res, "SOLVE QUADRATIC FOR T"))
    assert q[-3:] == ["ONE ROOT (B²-4AC IS 0).", "IT STARTED AT REST.", "SO T = 2.00 S"], q


# ------------------------------------------------------------------ bad inputs
def t_wrong_count():
    full = [8, 20.6, 120, 8.39, 1.5]
    for n in (0, 1, 3, 4, 5):
        inputs = [U if i < n else x for i, x in enumerate(full)]
        res, r = solve_check(inputs, context=f"{n} unknowns")
        assert r["code"] == "E1" and rows(res.screens[-1])[2] == f"FOR {n} OF THE 5 VALUES.", rows(res.screens[-1])
    fb = [0, -29.7, -45, 3.03]
    for n in (0, 1, 3, 4):
        inputs = [U if i < n else x for i, x in enumerate(fb)]
        res, r = solve_check(inputs, "B", context=f"{n} unknowns")
        assert r["code"] == "E1" and "EXACTLY 2 OF V0,VF,S,T" in rows(res.screens[-1])


def t_time_not_positive():
    for inputs in ([5, U, U, 0, 2], [5, U, 10, 0, U], [U, U, 10, -2, 3], [5, 6, U, -1, U],
                   [U, 6, 10, 0, U]):
        res, r = solve_check(inputs)
        assert r["code"] == "E3" and rows(res.screens[-1])[0] == "CHECK T"
    res, r = solve_check([0, U, U, 0], "B")
    assert r["code"] == "E3"


def t_out_of_range():
    for inputs in ([1e10, U, 5, U, 1], [1e-10, U, 5, U, 1], [5, U, U, 2, -2e9], [5, U, U, 3e-12, 1],
                   [U, 6, -1.5e9, U, 2]):
        res, r = solve_check(inputs)
        assert r["code"] == "E2"
    res, r = solve_check([1e9, U, U, 1e-9, -1e9])    # the limits themselves are allowed
    assert r["kind"] == "summary"
    # extreme ratio: 0.05T² + 1E5 T - 1E-4 = 0. The plain quadratic formula loses the small root
    # (B²-4AC = 1E10+2E-5 rounds to 1E10, so T2 comes out as 0); ZVOVF recomputes it from
    # T1*T2 = C/A as N/(L*T1) = -1E-4/(0.05(-2E6)) = 1.00E-9 s.
    res, r = solve_check([1e5, U, 1e-4, U, 0.1])
    expect(summary(res)["T"], "1.00E-9", "T")
    expect(summary(res)["VF"], "100000", "VF")
    q = find_screen(res, "SOLVE QUADRATIC FOR T")
    assert "SO T = 1.00E-9 S" in q, q


def t_a_zero():
    res, r = solve_check([5, U, U, 3, 0])             # case 1: VF=5, S=15
    expect(summary(res)["VF"], "5.00", "VF")
    expect(summary(res)["S"], "15.0", "S")
    res, r = solve_check([5, U, 20, U, 0])            # case 2 linear: T=20/5=4, VF=5
    expect(summary(res)["T"], "4.00", "T")
    expect(summary(res)["VF"], "5.00", "VF")
    q = find_screen(res, "SOLVE QUADRATIC FOR T")
    assert "NO T² TERM, SO LINEAR" in q and "T = 4.00 S" in q, q
    # (regression ZVOVF-6: step 1 must not promise the quadratic formula when A is 0)
    s1 = rows(find_screen(res, "STEP 1 - FIND T"))
    assert s1[-2:] == ["A IS 0, SO NO T² TERM.", "SOLVE THE LINEAR EQUATION."], s1
    assert not any("QUADRATIC FORMULA" in x or "T IS SQUARED" in x for x in s1), s1
    res, r = solve_check([U, 5, 20, U, 0])            # case 5 linear
    expect(summary(res)["T"], "4.00", "T")
    expect(summary(res)["V0"], "5.00", "V0")
    s1 = rows(find_screen(res, "STEP 1 - FIND T"))
    assert s1[-2:] == ["A IS 0, SO NO T² TERM.", "SOLVE THE LINEAR EQUATION."], s1
    res, r = solve_check([U, 5, U, 3, 0])             # case 4
    expect(summary(res)["V0"], "5.00", "V0")
    expect(summary(res)["S"], "15.0", "S")
    res, r = solve_check([U, U, 15, 3, 0])            # case 10
    expect(summary(res)["V0"], "5.00", "V0")
    expect(summary(res)["VF"], "5.00", "VF")
    res, r = solve_check([5, U, 15, 3, U])            # case 3 gives A = 0
    expect(summary(res)["A"], "0", "A")
    expect(summary(res)["VF"], "5.00", "VF")
    for inputs, code in (([5, U, -20, U, 0], "E6"), ([5, U, 0, U, 0], "E6"),
                         ([0, U, 20, U, 0], "EF"), ([0, U, 0, U, 0], "EF"),
                         ([U, 0, 20, U, 0], "EF"), ([U, 0, 0, U, 0], "EF"),
                         ([5, 5, U, U, 0], "E7"), ([5, 8, U, U, 0], "E8")):
        res, r = solve_check(inputs)
        assert r["code"] == code, (inputs, r["code"], code)
    assert rows(run_a(0, U, 0, U, 0).screens[-1])[0] == "NOT ENOUGH INFORMATION"
    assert rows(run_a(0, U, 20, U, 0).screens[-1])[0] == "IMPOSSIBLE"


def t_case7_and_case9_guards():
    for inputs, code in (([10, 20, U, U, -9.8], "EA"), ([10, 10, U, U, -9.8], "E9"),
                         ([10, -10, 0, U, U], "EB"), ([10, -10, 5, U, U], "EC"),
                         ([10, 5, 0, U, U], "ED"), ([10, 5, -5, U, U], "EE"),
                         ([0, 0, 0, U, U], "EB")):
        res, r = solve_check(inputs)
        assert r["code"] == code, (inputs, r["code"], code)
    res, r = solve_check([8, 14, 44, U, U])           # case 9 normal: T = 88/22 = 4, A = 1.5
    expect(summary(res)["T"], "4.00", "T")
    expect(summary(res)["A"], "1.50", "A")
    res, r = solve_check([10, -10, U, U, -9.8])       # case 7, VF=-V0: T = 2.04, S = 0
    expect(summary(res)["T"], "2.04", "T")
    expect(summary(res)["S"], "0", "S")
    res, r = solve_check([0, -29.7, U, U], "B")       # case 7 free fall
    expect(summary(res)["T"], "3.03", "T")
    expect(summary(res)["S"], "-45.0", "S")


# ------------------------------------------------------------------ free fall (B)
def t_free_fall():
    # dropped from rest, lands 45 m below: -45 = -4.9T² -> T = 3.03 s, VF = -9.8(3.03) = -29.7 m/s
    res, r = solve_check([0, U, -45, U], "B")
    sv = summary(res)
    expect(sv["T"], "3.03", "T")
    expect(sv["VF"], "-29.7", "VF")
    expect(sv["A"], "-9.80", "A")
    last = rows(res.screens[-1])
    assert last[0] == "SUMMARY (FREE FALL)" and "VF = -29.7 M/S (DOWN)" in last and "S = -45.0 M (DOWN)" in last
    given = rows(find_screen(res, "GIVEN"))
    assert "A = -9.80 M/S² (AUTO)" in given, given
    assert res.vars["K"] == 2 and res.angle == "Degree"
    # thrown up at 19.6 m/s to the top (VF=0): T = 19.6/9.8 = 2.00 s, S = 19.6²/19.6 = 19.6 m
    res, r = solve_check([19.6, 0, U, U], "B")
    sv = summary(res)
    expect(sv["T"], "2.00", "T")
    expect(sv["S"], "19.6", "S")
    assert "S = 19.6 M (UP)" in rows(res.screens[-1]) and "V0 = 19.6 M/S (UP)" in rows(res.screens[-1])
    assert all(p[0] != "A (M/S²)=" for p in [e[1:] for e in res.events if e[0] == "input"]), "B asked for A"
    # every free-fall pair from one motion: V0=5 up, T=2 -> VF = 5-19.6 = -14.6, S = 10-19.6 = -9.6
    fm = {"V0": 5, "VF": -14.6, "S": -9.6, "T": 2, "A": -9.8}
    for pair in (("VF", "S"), ("VF", "T"), ("V0", "S"), ("V0", "T"), ("S", "T"), ("V0", "VF")):
        inputs = with_unknowns(fm, pair)[:4]
        res, r = solve_check(inputs, "B", context=str(pair))
        sv = summary(res)
        if pair == ("V0", "T"):
            # V0² = VF²-2AS = 213.16-188.16 = 25, so V0 = -5 (thrown down, T = 9.6/9.8 = 0.980 s)
            # or V0 = +5 (thrown up, T = 2.00 s): both are physical.
            for name, want in (("T1", "0.980"), ("V0(T1)", "-5.00"), ("T2", "2.00"), ("V0(T2)", "5.00")):
                expect(sv[name], want, f"free fall {pair} {name}")
            continue
        for name in VARS:
            expect(sv[name], float(fm[name]), f"free fall {pair} {name}")


def t_free_fall_through_zfree():
    zfree = (ROOT / "src" / "ZFREE.txt").read_text(encoding="utf-8")
    if "VOVFSTA" not in zfree:
        print("       (skipped: ZFREE has no VOVFSTA option yet)")
        return
    res = run([2, "VOVFSTA", 0, U, -45, U, "BACK", 7])
    r = ref.free_fall(0, U, -45, U)
    check_run(res, r, "PHYSOLVE > FREE FALL > VOVFSTA")
    expect(summary(res)["T"], "3.03", "T")
    expect(summary(res)["VF"], "-29.7", "VF")
    # (regression ZVOVF-5) thrown up at 19.6 m/s, time to the top and max height, VF = 0:
    # T = 19.6/9.8 = 2.00 s, S = 19.6²/(2(9.8)) = 19.6 m
    res = run([2, "VOVFSTA", 19.6, 0, U, U, "BACK", 7])
    r = ref.free_fall(19.6, 0, U, U)
    check_run(res, r, "PHYSOLVE > FREE FALL > VOVFSTA thrown up")
    sv = summary(res)
    expect(sv["T"], "2.00", "T")
    expect(sv["S"], "19.6", "S")
    expect(sv["V0"], "19.6", "V0")
    expect(sv["VF"], "0", "VF")
    assert "S = 19.6 M (UP)" in rows(res.screens[-1]), rows(res.screens[-1])
    # (regression ZVOVF-1/5) dropped ball with VF typed +29.7: the free-fall EA screen blames
    # the signs (VF must be less than V0), not A (which is the automatic -9.8)
    res = run([2, "VOVFSTA", 0, 29.7, U, U, "BACK", 7])
    r = ref.free_fall(0, 29.7, U, U)
    check_run(res, r, "PHYSOLVE > FREE FALL > VOVFSTA dropped, VF +29.7")
    last = rows(res.screens[-1])
    assert r["code"] == "EA", r["code"]
    assert "A = -9.80 M/S² (AUTO)" in rows(find_screen(res, "GIVEN"))
    assert not any("A HAS THE WRONG SIGN" in x for x in last), last
    assert last[1] == "THE SIGNS DO NOT FIT." and "A IS -9.8, SO VF MUST BE" in last, last
    assert "LESS THAN V0." in last and "(UP IS +, FALLING IS -.)" in last, last
    assert "(UP/FORWARD IS +.)" not in last, last
    # the corrected input (VF = -29.7) solves: T = 29.7/9.8 = 3.03 s, S = -29.7²/19.6 = -45.0 m
    res = run([2, "VOVFSTA", 0, -29.7, U, U, "BACK", 7])
    check_run(res, ref.free_fall(0, -29.7, U, U), "dropped, VF -29.7")
    expect(summary(res)["T"], "3.03", "T")
    expect(summary(res)["S"], "-45.0", "S")


def t_ea_wording():
    """(regression ZVOVF-1) EA never says A has the wrong sign; it may be VF that is wrong."""
    # mode A: V0=0, VF=29.7, A=-9.8 - A is right here, VF has the wrong sign
    res, r = solve_check([0, 29.7, U, U, -9.8])
    last = rows(res.screens[-1])
    assert r["code"] == "EA" and last == ["NO PHYSICAL SOLUTION", "THE SIGNS DO NOT FIT.",
                                          "T IS (VF-V0)/A, WHICH IS", "NEGATIVE HERE. VF-V0 AND A",
                                          "MUST HAVE THE SAME SIGN.", "(UP/FORWARD IS +.)",
                                          "CHECK THE SIGNS."], last
    # free fall (K=2): the extra row says VF must be less than V0
    res, r = solve_check([0, 29.7, U, U], "B")
    last = rows(res.screens[-1])
    assert r["code"] == "EA" and "A IS -9.8, SO VF MUST BE" in last, last
    assert not any("WRONG SIGN" in x for x in last), last
    res, r = solve_check([-5, 10, U, U], "B")          # thrown down at 5, VF typed as +10
    assert r["code"] == "EA" and "LESS THAN V0." in rows(res.screens[-1])


def t_e5_farthest():
    """(regression ZVOVF-2) the case-2 'never gets there' screen shows the turning point."""
    # thrown up at 10 m/s: farthest S = 10²/(2(9.8)) = 5.10 m (the example on the screen)
    for mode, inputs in (("A", [10, U, 10, U, -9.8]), ("B", [10, U, 10, U])):
        res, r = solve_check(inputs, mode)
        last = rows(res.screens[-1])
        assert r["code"] == "E5" and "FARTHEST S IS 5.10 M" in last, last
        assert "(EX. A BALL THROWN UP AT" in last and "IF S WAS ROUNDED, ENTER" not in last, last
    # backward: V0 = -10, A = +2 turns round at S = -100/4 = -25.0 m, so S = -30 is never reached
    res, r = solve_check([-10, U, -30, U, 2])
    assert r["code"] == "E5" and "FARTHEST S IS -25.0 M" in rows(res.screens[-1])
    # the program's own rounded max height: V0=15 to the top gives S = 225/19.6 = 11.48 -> 11.5
    res = run([2, "VOVFSTA", 15, 0, U, U, "BACK", 7])
    check_run(res, ref.free_fall(15, 0, U, U), "V0=15 to the top")
    expect(summary(res)["S"], "11.5", "S")
    expect(summary(res)["T"], "1.53", "T")
    # typing that 11.5 back: B²-4AC = 225-4(4.9)(11.5) = -0.4 < 0 (just past the top) -> hint
    res = run([2, "VOVFSTA", 15, U, 11.5, U, "BACK", 7])
    r = ref.free_fall(15, U, 11.5, U)
    check_run(res, r, "V0=15, S=11.5 (rounded top)")
    last = rows(res.screens[-1])
    assert r["code"] == "E5" and last[4:8] == ["IT NEVER GETS TO THAT S.", "FARTHEST S IS 11.5 M",
                                               "IF S WAS ROUNDED, ENTER",
                                               "VF AS 0 AND 999 FOR S."], last
    assert "B²-4AC = -0.400" in find_screen(res, "SOLVE QUADRATIC FOR T")
    res, r = solve_check([15, U, 11.5, U, -9.8])      # same in mode A
    assert "IF S WAS ROUNDED, ENTER" in rows(res.screens[-1])
    # the case-5 E5 screen is unchanged (no farthest-S row: it has no room and no V0)
    res, r = solve_check([U, 0, -5, U], "B")
    assert not any("FARTHEST" in x for x in rows(res.screens[-1]))


def t_e6_case5_wording():
    """(regression ZVOVF-3) case 5 with S=0: back at the start needs VF and A of the same sign."""
    res = run([2, "VOVFSTA", U, 10, 0, U, "BACK", 7])     # caught at the same height, VF typed +10
    r = ref.free_fall(U, 10, 0, U)
    check_run(res, r, "case 5 S=0 VF=+10")
    last = rows(res.screens[-1])
    assert r["code"] == "E6" and last[1:6] == ["TO END BACK AT THE START,", "VF AND A MUST HAVE THE",
                                               "SAME SIGN. (A BALL CAUGHT", "AT THE SAME HEIGHT IS",
                                               "MOVING DOWN, SO VF<0.)"], last
    assert not any("NEVER COMES" in x for x in last), last
    # with VF = -10 it solves: T = 2(10)/9.8 = 2.04 s, V0 = -10+9.8(2.04) = +10.0 m/s (up)
    res = run([2, "VOVFSTA", U, -10, 0, U, "BACK", 7])
    check_run(res, ref.free_fall(U, -10, 0, U), "case 5 S=0 VF=-10")
    expect(summary(res)["T"], "2.04", "T")
    expect(summary(res)["V0"], "10.0", "V0")
    assert "V0 = 10.0 M/S (UP)" in rows(res.screens[-1])
    # case 5, S=0, VF=0 (A not 0): same new wording
    res, r = solve_check([U, 0, 0, U, -9.8])
    assert r["code"] == "E6" and "TO END BACK AT THE START," in rows(res.screens[-1])
    # case 5 with A=0 (steady velocity) and case 2 keep the 'never comes back' wording
    for inputs in ([U, 5, 0, U, 0], [-10, U, 0, U, -9.8]):
        res, r = solve_check(inputs)
        assert r["code"] == "E6" and "S IS 0 ONLY AT THE START" in rows(res.screens[-1]), inputs


def t_intro_hints():
    """(regression ZVOVF-4) the intro says how to enter 'at the top' (VF = 0)."""
    res = run([2, "VOVFSTA", 19.6, U, U, U, "BACK", 7])   # only V0 known: E1
    assert_clean(res)
    intro = rows(find_screen(res, "FREE FALL (VOVFSTA)"))
    assert "AT THE TOP, VF IS 0." in intro and "DROPPED MEANS V0 IS 0." in intro, intro
    assert len(intro) == 10, intro
    assert rows(res.screens[-1])[0] == "WRONG NUMBER OF UNKNOWNS"
    res = run_a(U, U, U, U, U)
    assert_clean(res)
    intro = rows(find_screen(res, "VOVFSTA SOLVER"))
    assert "FROM REST MEANS V0 IS 0." in intro and "STOPS/AT TOP MEANS VF IS 0" in intro, intro


def t_k_not_1_or_2():
    for k in (1, 0, 7, 1.5, -2):
        res = run([8, U, 120, U, 1.5], program="ZVOVF", init_vars={"K": k})
        check_run(res, ref.solve(8, U, 120, U, 1.5, k=k), f"K={k}")
        assert float(res.vars["K"]) == k, "ZVOVF changed K"
        assert res.angle == "Degree"
        expect(summary(res)["T"], "8.39", "T")


# ------------------------------------------------------------------ random fuzz
def t_fuzz_consistency():
    """Random motions: pick v0, a, t, compute vf and s, hide 2, check the solver recovers them."""
    rng = random.Random(2024)
    n_two = 0
    for i in range(260):
        mode = "A" if i % 3 else "B"
        v0 = rng.uniform(-40, 40)
        a = -9.8 if mode == "B" else rng.choice([-1, 1]) * rng.uniform(0.3, 15)
        t = rng.uniform(0.1, 12)
        motion = {"V0": v0, "VF": v0 + a * t, "S": v0 * t + 0.5 * a * t * t, "T": t, "A": a}
        pairs = list(PAIRS.values()) if mode == "A" else [p for p in PAIRS.values() if "A" not in p]
        pair = rng.choice(pairs)
        inputs = with_unknowns(motion, pair)
        if mode == "B":
            inputs = inputs[:4]
        if any(x != U and x != 0 and abs(x) < 1e-6 for x in inputs):
            continue
        res, r = solve_check(inputs, mode, context=f"fuzz #{i} {pair}")
        assert r["kind"] == "summary", (i, inputs, r["code"])
        sv = summary(res)
        if r["answers"] == 1:
            for name in VARS:
                got, want = sv[name], fmt3(motion[name])
                assert got == want or abs(float(got) - motion[name]) <= 0.006 * abs(motion[name]) + 1e-9, \
                    f"fuzz #{i} {pair} {name}: {got} vs true {want}"
        else:   # two physical answers: the motion we started from is one of them
            n_two += 1
            u2 = "VF" if r["case"] == 2 else "V0"
            pairs_shown = {(sv[f"T{n}"], sv[f"{u2}(T{n})"]) for n in (1, 2)}
            assert (fmt3(t), fmt3(motion[u2])) in pairs_shown, (i, pairs_shown, t, motion[u2])
    assert n_two > 3, "fuzz never produced the two-answer case"


def t_fuzz_robust():
    """Any numeric input: never an error, always a SUMMARY or a message equal to the reference."""
    rng = random.Random(77)
    pool = [0, 0, 1, -1, 2, -2, 5, -5, 9.8, -9.8, 10, -10, 19.6, 0.5, -0.5, 100, -100, 1e9, -1e9,
            1e-9, -1e-9, 3e9, -3e9, 2e-10, 1e-5, 123456, -0.001, 1e99, -1e99]
    for i in range(320):
        mode = "A" if i % 4 else "B"
        n = 5 if mode == "A" else 4
        vals = [rng.choice(pool) if rng.random() < 0.4 else round(rng.uniform(-50, 50), rng.randint(0, 3))
                for _ in range(n)]
        k = rng.choice([2, 2, 2, 1, 3]) if rng.random() < 0.15 else 2   # mostly exactly 2 unknowns
        idx = rng.sample(range(n), min(k, n))
        for j in idx:
            vals[j] = U
        solve_check(vals, mode, context=f"robust #{i}", seed=1000 + i)   # different start-up garbage


# Scripts that together reach every screen of ZVOVF (used for the wide-value run).
WIDE_SCRIPTS = [("A", [8, U, 120, U, 1.5])] + \
    [("A", with_unknowns(m, p)) for m in (M1, M2) for p in PAIRS.values()] + \
    [("A", x) for x in ([10, U, 10, U, -9.8], [U, 0, -5, U, -9.8], [10, U, 0, U, -9.8],
                        [-10, U, 0, U, -9.8], [20, U, -5, U, 9.8], [5, U, 20, U, 0], [U, 5, 20, U, 0],
                        [0, U, 20, U, 0], [U, 0, 0, U, 0], [5, 5, U, U, 0], [5, 8, U, U, 0],
                        [10, 20, U, U, -9.8], [10, 10, U, U, -9.8], [10, -10, 0, U, U],
                        [10, -10, 5, U, U], [10, 5, 0, U, U], [10, 5, -5, U, U], [U, U, U, U, U],
                        [1e10, U, 5, U, 1], [5, U, U, 0, 2], [5, U, -20, U, 0],
                        [15, U, 11.5, U, -9.8], [-10, U, -30, U, 2], [U, 10, 0, U, -9.8],
                        [U, 5, 0, U, 0], [0, 29.7, U, U, -9.8], [19.6, U, 19.6, U, -9.8])] + \
    [("B", x) for x in ([0, U, -45, U], [19.6, 0, U, U], [10, U, 4, U], [U, -4.65, -1, U],
                        [19.6, U, 19.6, U], [U, -19.6, -19.6, U], [10, U, 10, U], [U, U, U, U],
                        [5, U, U, 2], [U, U, -9.6, 2], [0, 29.7, U, U], [15, U, 11.5, U],
                        [U, 10, 0, U], [U, 0, -5, U])]


def t_wide_values():
    """Every screen still fits 26x10 when every number is shown 9 characters wide (-8.88E-88)."""
    for mode, inputs in WIDE_SCRIPTS:
        if mode == "A":
            res = run([1] + list(inputs) + [7], wide=True)
        else:
            res = run(inputs, program="ZVOVF", init_vars={"K": 2}, wide=True)
        assert_clean(res, context=f"wide {mode} {inputs}")


def t_coverage():
    """Every statement of ZVOVF ran in this test file (every menu path and message)."""
    from harness import sim
    s = sim()
    prog = s.programs["ZVOVF"]
    missing = [(st.line, st.text) for i, st in enumerate(prog.stmts)
               if ("ZVOVF", i) not in s.coverage and st.kind not in ("Lbl", "Then")]
    assert not missing, f"{len(missing)} statements never executed: {missing[:20]}"


c.check("required case v0=8, a=1.5, s=120 -> VF=20.6, T=8.39 (both roots shown)", t_required_case)
c.check("case table: first equation never contains the second unknown", t_case_table_matches_task)
c.check("all 10 unknown pairs, two hand-worked motions (incl. 2-answer cases)", t_all_pairs)
c.check("both roots > 0 (v0=10, a=-9.8, s=4 -> T=0.546 s and 1.49 s)", t_both_roots_positive)
c.check("two answers in case 5 (free fall), direction words", t_two_answers_case5_free_fall)
c.check("impossible discriminant (v0=10, a=-9.8, s=10) and case-5 version", t_impossible_discriminant)
c.check("quadratic edges: S=0, both roots < 0, double root", t_quadratic_edges)
c.check("wrong number of unknowns (0,1,3,4,5 in A; 0,1,3,4 in B)", t_wrong_count)
c.check("T known and <= 0", t_time_not_positive)
c.check("inputs out of range (overflow guard)", t_out_of_range)
c.check("A = 0 in every case it can appear", t_a_zero)
c.check("case 7 / case 9 guards (wrong sign, V0+VF=0, S=0)", t_case7_and_case9_guards)
c.check("free fall K=2: dropped s=-45 -> T=3.03, VF=-29.7; thrown up 19.6 -> T=2.00, S=19.6", t_free_fall)
c.check("free fall through PHYSOLVE > FREE FALL > VOVFSTA (ZFREE)", t_free_fall_through_zfree)
c.check("EA wording: signs do not fit; free fall says VF must be < V0 (ZVOVF-1)", t_ea_wording)
c.check("E5 case 2 shows the farthest S and the rounding hint (ZVOVF-2)", t_e5_farthest)
c.check("E6 case 5 with S=0 explains VF and A signs (ZVOVF-3)", t_e6_case5_wording)
c.check("intro hints: V0 is 0 from rest, VF is 0 at the top (ZVOVF-4)", t_intro_hints)
c.check("K not 1 or 2 behaves as K=1 and K is not changed", t_k_not_1_or_2)
c.check("fuzz: random motions, solver recovers the hidden values", t_fuzz_consistency)
c.check("fuzz: random inputs never error and match the reference", t_fuzz_robust)
c.check("every screen fits with 9-character values (wide mode)", t_wide_values)
c.check("statement coverage of ZVOVF is 100%", t_coverage)
sys.exit(c.done())
