#!/usr/bin/env python3
"""Acceptance tests for the MOLES oracle.  Run: python3 tools/test_oracle.py"""
import json
import os
import subprocess
import sys
import unittest
from decimal import Decimal

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import oracle as o  # noqa: E402

E, N = o.EXP, o.NEG


class Close:
    def assertClose(self, got, want, rel=Decimal("1e-9")):
        got, want = Decimal(got), Decimal(want)
        self.assertLessEqual(abs(got - want), abs(want) * rel, f"{got} != {want}")


class TestTable(unittest.TestCase):
    def test_table(self):
        self.assertEqual(len(o.SYMBOLS), 59)
        self.assertEqual(o.SYMBOLS[:3], ["H", "He", "Li"])
        self.assertEqual(o.SYMBOLS[-3:], ["Au", "Hg", "Pb"])
        self.assertEqual(o.element_index("Ba"), 56)
        self.assertEqual(o.element_index("Sn"), 50)
        self.assertEqual(o.MASS["H"], Decimal("1.008"))
        self.assertEqual(o.MASS["Tc"], Decimal("98"))
        self.assertEqual(o.MASS["Pb"], Decimal("207.2"))
        self.assertEqual(o.NA, Decimal("6.022E23"))


class TestFmt(unittest.TestCase):
    def test_examples(self):
        for args, want in o.FMT_EXAMPLES:
            with self.subTest(args=args):
                self.assertEqual(o.fmt(*args), want)

    def test_more(self):
        self.assertEqual(o.fmt("0.000123", 3, 0), f"1.23{E}{N}4")
        self.assertEqual(o.fmt("0.001", 3, 1), "0.001")
        self.assertEqual(o.fmt("0.0001", 3, 1), f"1{E}{N}4")
        self.assertEqual(o.fmt("1E10", 10, 1), f"1{E}10")
        self.assertEqual(o.fmt("1500000000", 10, 1), "1500000000")
        self.assertEqual(o.fmt("100", 3, 0), f"1.00{E}2")
        self.assertEqual(o.fmt("9.996", 3, 0), "10.0")
        self.assertEqual(o.fmt("99.96", 3, 0), f"1.00{E}2")
        self.assertEqual(o.fmt("0", 3, 0), "0.00")
        self.assertEqual(o.fmt("0", 1, 0), "0")
        self.assertEqual(o.fmt("-2.5", 2, 0), f"{N}2.5")
        self.assertEqual(o.fmt("2.345", 0, 2), "2")
        self.assertEqual(o.fmt("0.005", 2, 2), "0.01")
        self.assertEqual(o.fmt(f"3.011{E}23", 3, 0), f"3.01{E}23")


class TestSigfigs(unittest.TestCase):
    def test_examples(self):
        for s, want in o.SIGFIG_EXAMPLES:
            with self.subTest(s=s):
                self.assertEqual(o.sigfigs(s), want)

    def test_more(self):
        self.assertEqual(o.sigfigs("0"), 1)
        self.assertEqual(o.sigfigs(f"{N}0.0250"), 3)
        self.assertEqual(o.sigfigs("2.40"), 3)
        self.assertEqual(o.sigfigs("1.234567890123"), 9)
        self.assertEqual(o.sigfigs("6.022E23"), 4)


class TestParse(unittest.TestCase, Close):
    def test_al2so43(self):
        p = o.parse("Al2(SO4)3")
        self.assertEqual(p["elements"], [("Al", 2), ("S", 3), ("O", 12)])
        self.assertEqual(p["M2"], Decimal("342.17"))

    def test_tin_acetate(self):
        p = o.parse("Sn(C2H3O2)2")
        self.assertEqual(p["elements"], [("Sn", 1), ("C", 4), ("H", 6), ("O", 4)])
        self.assertEqual(p["M_exact"], Decimal("236.788"))
        self.assertEqual(p["M2"], Decimal("236.79"))

    def test_hydrates(self):
        p = o.parse("CaSO4*2H2O")
        self.assertEqual(p["elements"], [("Ca", 1), ("S", 1), ("O", 6), ("H", 4)])
        self.assertEqual(p["M_exact"], Decimal("172.182"))
        self.assertEqual(p["M2"], Decimal("172.18"))
        self.assertEqual(p["anhydrous2"], Decimal("136.15"))
        q = o.parse("CuSO4.5H2O")
        self.assertEqual(q["formula"], "CuSO4*5H2O")
        self.assertEqual(q["M2"], Decimal("249.70"))
        self.assertEqual(q["anhydrous2"], Decimal("159.62"))
        self.assertEqual(o.parse("CaSO4*H2O")["counts"]["H"], 2)

    def test_nested_and_simple(self):
        p = o.parse("K4(Fe(CN)6)")
        self.assertEqual(p["elements"], [("K", 4), ("Fe", 1), ("C", 6), ("N", 6)])
        self.assertEqual(p["M2"], Decimal("368.37"))
        self.assertEqual(o.parse("H2O")["M2"], Decimal("18.02"))
        self.assertEqual(o.parse("CO2")["M2"], Decimal("44.01"))
        self.assertEqual(o.parse("Ca3(PO4)2")["M2"], Decimal("310.18"))
        self.assertEqual(o.parse("C12H22O11")["M2"], Decimal("342.30"))

    def test_errors(self):
        for bad in ["", "Xx2", "Al2(SO4", "Al2SO4)3", "so4", "2H2O", "CaSO4*", "H0", "()2"]:
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                o.parse(bad)


class TestResolver(unittest.TestCase):
    def test_cases(self):
        self.assertEqual(o.resolve_caps("AL2(SO4)3"), "Al2(SO4)3")
        self.assertEqual(o.resolve_caps("NACL"), "NaCl")
        self.assertEqual(o.resolve_caps("CACO3", [2]), "CaCO3")
        self.assertEqual(o.resolve_caps("SN(C2H3O2)2", [1]), "Sn(C2H3O2)2")
        f, log = o.resolve_caps_detailed("CACO3", [2])
        self.assertEqual([a["pair"] for a in log], ["CO"])
        f, log = o.resolve_caps_detailed("SN(C2H3O2)2", [1])
        self.assertEqual([a["pair"] for a in log], ["SN"])

    def test_more(self):
        self.assertEqual(o.resolve_caps("CO2", [2]), "CO2")
        self.assertEqual(o.resolve_caps("CO", [1]), "Co")
        self.assertEqual(o.resolve_caps("CUSO4.5H2O"), "CuSO4*5H2O")
        self.assertEqual(o.resolve_caps("CaSO4"), "CaSO4")      # mixed case passes through
        self.assertEqual(o.resolve_caps("MGCL2"), "MgCl2")
        self.assertEqual(o.resolve_caps("HF"), "HF")             # Hf not in table

    def test_errors(self):
        with self.assertRaises(o.AmbiguityError):
            o.resolve_caps("CACO3")
        with self.assertRaises(ValueError):
            o.resolve_caps("QZ")
        with self.assertRaises(ValueError):
            o.resolve_caps("CO", [3])


class TestPractice(unittest.TestCase, Close):
    def test_h2o(self):
        r = o.convert("g->mol", "36.0", "H2O")
        self.assertEqual(r["M2"], Decimal("18.02"))
        self.assertClose(r["result"], "1.997780244173")       # spec rule: g / M2
        self.assertEqual(o.fmt(r["result"], o.sigfigs("36.0"), 0), "2.00")
        c = o.CASES["practice_h2o"]()
        self.assertClose(c["mol_if_M_exact"], "1.998223801066")  # 36.0 / 18.016
        self.assertEqual(o.fmt(c["mol_if_M_exact"], 3, 0), "2.00")

    def test_co2(self):
        r = o.convert("mol->particles", "0.500", "CO2")
        self.assertEqual(r["result"], Decimal("3.011E23"))
        self.assertEqual(o.fmt(r["result"], o.sigfigs("0.500"), 0), f"3.01{E}23")

    def test_cuso4_hydrate(self):
        r = o.hydrate_from_heating("5.00", "3.20", "CuSO4")
        self.assertEqual(r["water_mass"], Decimal("1.80"))
        self.assertClose(r["ratio"], "4.982588790233")
        self.assertEqual(r["x"], 5)
        self.assertEqual(r["formula"], "CuSO4*5H2O")

    def test_ch2(self):
        r = o.empirical([("C", "85.6"), ("H", "14.4")])
        self.assertEqual(r["multiplier"], 1)
        self.assertEqual(r["empirical"], "CH2")


class TestFormB(unittest.TestCase, Close):
    def test_1(self):
        r = o.convert("mol->g", "4.87", "Sn(C2H3O2)2")
        self.assertEqual(r["M2"], Decimal("236.79"))
        self.assertEqual(r["result"], Decimal("1153.1673"))
        self.assertEqual(o.fmt(r["result"], o.sigfigs("4.87"), 0), f"1.15{E}3")

    def test_2(self):
        r = o.convert("g->atoms", "5.0", "Na", "Na")
        self.assertClose(r["result"], "1.309699870e23")
        self.assertEqual(o.fmt(r["result"], o.sigfigs("5.0"), 0), f"1.3{E}23")
        self.assertEqual(o.convert("g->particles", "5.0", "Na")["result"], r["result"])

    def test_3(self):
        r = o.convert("g->atoms", "550", "Al2(SO4)3", "Al")
        self.assertEqual(r["M2"], Decimal("342.17"))
        self.assertEqual(r["count"], 2)
        self.assertClose(r["result"], "1.935938276e24")
        self.assertEqual(o.fmt(r["result"], o.sigfigs("550"), 0), f"1.9{E}24")

    def test_4(self):
        r = o.empirical([("C", "60.0"), ("H", "4.48"), ("O", "35.5")], molar_mass="540")
        self.assertClose(r["ratios"][0], "2.251644756")
        self.assertClose(r["ratios"][1], "2.003129890")
        self.assertEqual(r["ratios"][2], 1)
        self.assertEqual([t["whole"] for t in r["tried"]], [False, False, False, True])
        self.assertEqual(r["multiplier"], 4)
        self.assertFalse(r["flagged"])
        self.assertEqual(r["empirical"], "C9H8O4")
        self.assertEqual(r["EM"], Decimal("180.15"))
        self.assertClose(r["n_raw"], "2.997502082")
        self.assertEqual(r["n"], 3)
        self.assertEqual(r["molecular"], "C27H24O12")

    def test_5(self):
        r = o.hydrate_from_heating("19.06", "15.07", "CaSO4")
        self.assertEqual(r["water_mass"], Decimal("3.99"))
        self.assertEqual(r["M2_anhydrous"], Decimal("136.15"))
        self.assertClose(r["ratio"], "2.000426055")
        self.assertEqual(r["x"], 2)
        self.assertEqual(r["formula"], "CaSO4*2H2O")

    def test_6(self):
        r = o.same_moles("2.40", "g", "CO2", "particles", "H2O")
        self.assertClose(r["mol"], "0.05453306067")
        self.assertClose(r["result"], "3.283980913e22")
        self.assertEqual(o.fmt(r["result"], o.sigfigs("2.40"), 0), f"3.28{E}22")


class TestOtherFeatures(unittest.TestCase, Close):
    def test_percent_comp(self):
        p = o.percent_composition("CO2")["percents"]
        self.assertClose(p["C"], "27.28925244")
        self.assertClose(p["O"], "72.71074756")
        p = o.percent_composition("H2O")["percents"]
        self.assertClose(p["H"], "11.18756937")
        self.assertClose(p["O"], "88.79023307")

    def test_percent_water(self):
        r = o.percent_water("CuSO4*5H2O")
        self.assertEqual(r["M2"], Decimal("249.70"))
        self.assertEqual(r["anhydrous2"], Decimal("159.62"))
        self.assertClose(r["percent"], "36.07529035")
        self.assertEqual(o.fmt(r["percent"], 4, 0), "36.08")
        with self.assertRaises(ValueError):
            o.percent_water("CuSO4")

    def test_conversions(self):
        self.assertEqual(o.convert("particles->mol", "6.022E23")["result"], 1)
        self.assertClose(o.convert("particles->g", "3.011E23", "H2O")["result"], "9.01")
        self.assertClose(o.convert("g->particles", "18.02", "H2O")["result"], "6.022e23")
        with self.assertRaises(ValueError):
            o.convert("g->atoms", "1", "H2O", "Na")

    def test_same_moles_grams(self):
        r = o.same_moles("6.022E23", "particles", None, "g", "CO2")
        self.assertEqual(r["result"], Decimal("44.01"))

    def test_empirical_flag_and_grams(self):
        r = o.empirical([("C", "12.01"), ("O", "21.92")])   # ratio 1.37: no m <= 5 is whole
        self.assertTrue(r["flagged"])
        self.assertEqual(r["multiplier"], 1)
        r = o.empirical([("Fe", "2.0"), ("O", "0.859")], mode="grams")
        self.assertEqual(r["empirical"], "Fe2O3")


class TestCLI(unittest.TestCase):
    def run_cli(self, *args):
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONIOENCODING="utf-8")
        return subprocess.run([sys.executable, os.path.join(HERE, "oracle.py"), *args],
                              capture_output=True, text=True, encoding="utf-8", env=env, check=True)

    def test_all(self):
        data = json.loads(self.run_cli("all").stdout)
        self.assertEqual(set(data), set(o.CASES))
        self.assertEqual(data["formb_4"]["molecular"], "C27H24O12")
        self.assertEqual(data["formb_6"]["molecules"]["rounded"], f"3.28{E}22")

    def test_case(self):
        out = self.run_cli("case", "formb_1").stdout
        self.assertIn(f"grams.rounded: 1.15{E}3", out)
        self.assertIn("M2: 236.79", out)


if __name__ == "__main__":
    unittest.main(verbosity=1)
