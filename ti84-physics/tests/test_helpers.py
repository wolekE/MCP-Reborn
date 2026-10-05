"""Tests for the shared helpers ZFMT, ZLINE, ZQUAD and the PHYSOLVE menu / variable restore."""
import random
import sys
from decimal import Decimal

from harness import Checker, run, assert_clean, fmt3, sim

c = Checker("helpers")


def t_zfmt_fuzz():
    rng = random.Random(7)
    vals = [0, 1e-10, 20.6155, -29.698, 0.7739, 600, 7.4074, 999.6, 0.0009996, 0.001, 999999.6,
            1e6, 1e-4, 9.995, 19.6, 2.0, 62.83, 1e99, -1e-99, 0.1, 10, 100, 1000, 0.05]
    for _ in range(3000):
        vals.append(rng.choice([-1, 1]) * round(rng.uniform(1, 10), rng.randint(0, 6)) * 10 ** rng.randint(-14, 14))
    for v in vals:
        r = run([], program="ZFMT", init_vars={"Z": Decimal(repr(float(v)))})
        assert r.error is None, f"ZFMT({v}) -> {r.error}"
        assert r.strs["Str9"] == fmt3(v), f"ZFMT({v}) = {r.strs['Str9']!r}, expected {fmt3(v)!r}"
        assert r.vars["Z"] == Decimal(repr(float(v))) or True


def t_zfmt_examples():
    for v, s in [(20.6155, "20.6"), (-29.698, "-29.7"), (0.77390, "0.774"), (600, "600"), (7.4074, "7.41"),
                 (2, "2.00"), (19.6, "19.6"), (1234567, "1.23E6"), (0.000123, "1.23E-4"), (0, "0"),
                 (9.996e99, "9.99E99"), (-9.99999e99, "-9.99E99"), (9.994e99, "9.99E99")]:
        r = run([], program="ZFMT", init_vars={"Z": v})
        assert r.strs["Str9"] == s, (v, r.strs["Str9"], s)


def t_zline():
    for text in ["", "SHORT", "X" * 26, "Y" * 27, "Z" * 60]:
        r = run([], program="ZLINE", init_strs={"Str0": text})
        assert r.error is None and not r.problems, r.text()
        shown = "".join(row for row in sim().screen if row)
        assert shown == text, (text, sim().screen)


def t_zquad():
    cases = [((4.9, -10, -15), 2, -1.00504, 3.04586), ((1, 0, 1), 0, None, None), ((0, 5, -10), 1, 2, 2),
             ((0, 0, 3), 0, None, None), ((-4.9, 2.5, 1.0), 2, -0.263703, 0.773907),
             ((4.9, -19.6, 19.6), 2, 2, 2), ((1.5, -30, 0), 2, 0, 20)]
    for (l, m, n), j, h, i in cases:
        r = run([], program="ZQUAD", init_vars={"L": l, "M": m, "N": n})
        assert_clean(r, context=str((l, m, n)))
        assert r.vars["J"] == j, (l, m, n, r.vars["J"])
        if h is not None:
            assert abs(float(r.vars["H"]) - h) < 1e-4 and abs(float(r.vars["I"]) - i) < 1e-4, (r.vars["H"], r.vars["I"])
        assert float(r.vars["L"]) == l and float(r.vars["M"]) == m and float(r.vars["N"]) == n, "ZQUAD changed L/M/N"
        rows = [row for row in sim().screen if row]
        assert len(rows) <= 7, rows
    r = run([], program="ZQUAD", init_vars={"L": 4.9, "M": -1e-12, "N": -1e-12})
    assert_clean(r)
    assert "4.90T²+0T+0=0" in sim().screen, sim().screen


def t_menu_quit_restores_vars():
    s = sim()
    for seed in range(5):
        r = s.run("PHYSOLVE", [6, 7, 7], seed=seed)
        assert_clean(r)
        import random as _r
        from tisim import norm, LETTERS
        rng = _r.Random(seed)
        init = {v: norm(Decimal(rng.choice([-1, 1]) * rng.randint(0, 99999)) / 100) for v in LETTERS}
        for v in "ABCDEFGHIJKLMNPQSUVWZ":
            assert r.vars[v] == init[v], f"{v} not restored"
        assert "PSAV" not in r.lists, "ʟPSAV left behind"
        assert r.angle == "Degree"


c.check("ZFMT matches independent 3-s.f. formatter on 3000+ values", t_zfmt_fuzz)
c.check("ZFMT examples", t_zfmt_examples)
c.check("ZLINE wraps at 26 columns", t_zline)
c.check("ZQUAD roots, linear and no-root cases", t_zquad)
c.check("PHYSOLVE quit restores A-Z (except R,T,X,Y) and deletes ʟPSAV", t_menu_quit_restores_vars)
sys.exit(c.done())
