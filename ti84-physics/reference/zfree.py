"""
Reference implementation of prgmZFREE (menu item B, FREE FALL), mirroring src/ZFREE.txt
label by label: same input checks in the same order, same equations, same branches, same
messages. Class conventions: g = 9.8 m/s^2, up is +, so a = -9.8 m/s^2; H is the height of the
launch point above the ground (typed as a positive number); speeds are typed as positive numbers.

TI variables used by ZFREE (the same letters are used below):
    Q = H (height typed)        V = v0 (signed; typed as a speed)    A = -9.8
    P = path (1 dropped, 2 up same level, 3 thrown down, 4 up from height)
    B = time to top             C = rise above launch (max height above launch)
    E = max height above ground D = total time                       F = vf (impact)
    S = displacement            N = VF^2                             G = time from top to ground
    L, M, N -> prgmZQUAD inputs; J, H, I, G <- prgmZQUAD outputs

run(option, *inputs) returns a Result whose .screens list has one entry per Pause screen:
    Screen(title, values, rows)
      title  = first row of the screen
      values = [(name, value, unit)] for each "NAME = VALUE UNIT" row (and ("VF² IS", N, "")
               for the "VF² IS 882" row), in screen order; value is a number (the tests format
               it with fmt3, like prgmZFMT) or a literal string the program prints as text
      rows   = for message screens: the exact message rows (they end the screen)
"""
import math

from common import G as GRAV   # 9.8 m/s^2

BIG = 1e9                       # inputs above this are rejected (keeps every step far from overflow)
MENU_TITLE = "FREE FALL (A=-9.8)"

# Message screens (label -> rows), exactly as the TI program displays them.
MESSAGES = {
    "E1": ("H CANNOT BE NEGATIVE.",          # negative height
           "ENTER H AS A POSITIVE",
           "NUMBER- THE HEIGHT OF THE",
           "START ABOVE THE GROUND.",
           "THE PROGRAM MAKES S",
           "NEGATIVE FOR YOU."),
    "E2": ("H IS 0, SO IT STARTS ON",        # H = 0 for dropped / thrown down
           "THE GROUND AND HAS NO",
           "ROOM TO FALL. ENTER A",
           "HEIGHT ABOVE 0."),
    "E3": ("ENTER THE SPEED AS A",           # negative speed for thrown down
           "POSITIVE NUMBER. THE",
           "PROGRAM MAKES V0 NEGATIVE",
           "FOR YOU (DOWN IS -)."),
    "E4": ("ENTER V0 AS A POSITIVE",         # negative v0 for thrown up
           "NUMBER (THE SPEED UP).",
           "FOR A THROW DOWNWARD USE",
           "THROWN DOWN (OPTION 3)."),
    "E5": ("V0 IS 0, SO IT NEVER",           # thrown up (same level) with v0 = 0
           "LEAVES THE HAND- NOTHING",
           "TO SOLVE. TO DROP FROM A",
           "HEIGHT USE OPTION 1."),
    "E6": ("THE SPEED IS 0, SO IT IS",       # thrown down/up from height with speed 0 -> dropped
           "JUST DROPPED FROM REST.",
           "SOLVING IT AS DROPPED."),
    "E7": ("H IS 0, SO IT LANDS BACK",       # thrown up from height with H = 0 -> option 2
           "AT LAUNCH LEVEL. SOLVING",
           "IT AS THROWN UP (SAME",
           "LEVEL)."),
    "E8": ("NO POSITIVE TIME FOUND.",        # quadratic gave no positive root (shown under ZQUAD's rows)
           "CHECK H AND THE SPEED."),
    "E9": ("THAT NUMBER IS TOO LARGE.",      # an input above 1E9
           "KEEP H AND SPEEDS AT OR",
           "BELOW 1E9 (1 BILLION)."),
}


class Screen:
    def __init__(self, title, values=(), rows=()):
        self.title = title
        self.values = list(values)
        self.rows = list(rows)

    def __repr__(self):
        return f"Screen({self.title!r}, {self.values!r}, {self.rows!r})"


class Result:
    def __init__(self):
        self.screens = []
        self.messages = []        # message labels shown, in order (E1..E9)
        self.calls = []           # programs called (other than ZFMT/ZLINE)
        self.k_at_call = None     # K when prgmZVOVF is called (option 5)

    def add(self, title, values=(), rows=()):
        self.screens.append(Screen(title, values, rows))

    @property
    def summary(self):
        """{name: value} of the last screen (the SUMMARY screen of a calculation)."""
        return {n: v for n, v, u in self.screens[-1].values}


class Vars:
    """The TI variables ZFREE uses (start as None = 'garbage')."""
    def __init__(self):
        for k in "ABCDEFGHIJLMNPQSV":
            setattr(self, k, None)


def zquad(l, m, n):
    """Mirror of prgmZQUAD for L*T^2 + M*T + N = 0. Returns (J, H, I, G, values-on-screen)."""
    if l == 0:
        if m == 0:
            return 0, None, None, None, []
        h = -n / m
        return 1, h, h, None, [("T", h, "S")]
    g = m ** 2 - 4 * l * n
    if abs(g) < 1e-10 * (m ** 2 + abs(4 * l * n)):
        g = 0.0
    vals = [("B²-4AC", g, "")]
    if g < 0:
        return 0, None, None, g, vals
    h = (-m - math.sqrt(g)) / (2 * l)
    i = (-m + math.sqrt(g)) / (2 * l)
    if h > i:
        h, i = i, h
    vals += [("T1", h, "S"), ("T2", i, "S")]
    return 2, h, i, g, vals


def run(option, *inputs):
    """option: ZFREE menu choice 1-6; inputs: the numbers typed (H and/or speed)."""
    r = Result()
    v = Vars()
    if option == 1:            # Lbl D1   Input "HEIGHT H (M)=",Q
        (v.Q,) = inputs
        _d1(r, v)
    elif option == 2:          # Lbl U1   Input "V0 UP (M/S)=",V
        (v.V,) = inputs
        _u2(r, v)
    elif option == 3:          # Lbl N1   Input "HEIGHT H (M)=",Q   Input "SPEED DOWN (M/S)=",V
        v.Q, v.V = inputs
        _n1(r, v)
    elif option == 4:          # Lbl H1   Input "HEIGHT H (M)=",Q   Input "V0 UP (M/S)=",V
        v.Q, v.V = inputs
        _h1(r, v)
    elif option == 5:          # Lbl V5   2->K, prgmZVOVF, back to the ZFREE menu
        r.k_at_call = 2
        r.calls.append("ZVOVF")
    elif option == 6:          # Lbl Q    BACK: Return to PHYSOLVE
        pass
    else:
        raise ValueError(option)
    return r


def _msg(r, label):
    r.messages.append(label)
    rows = MESSAGES[label]
    r.add(rows[0], rows=rows)
    return r


# ---------------------------------------------------------------- 1: dropped from height H
def _d1(r, v):
    if v.Q < 0:
        return _msg(r, "E1")
    if v.Q > BIG:
        return _msg(r, "E9")
    if v.Q == 0:
        return _msg(r, "E2")
    return _d2(r, v)


def _d2(r, v):
    v.P = 1
    v.V = 0
    v.A = -GRAV
    v.S = -v.Q
    v.D = math.sqrt(2 * v.S / v.A)            # S = V0T + (1/2)AT^2 with V0 = 0  ->  T = sqrt(2S/A)
    r.add("STEP 1  TIME TO GROUND", [("S", v.S, "M"), ("T", v.D, "S")])
    return _f1(r, v)


# ---------------------------------------------------------------- 2: thrown up, same level
def _u2(r, v):
    if v.V < 0:
        return _msg(r, "E4")
    if v.V > BIG:
        return _msg(r, "E9")
    if v.V == 0:
        return _msg(r, "E5")
    v.P = 2
    return _u3(r, v)


def _u3(r, v):                                 # shared by paths 2 and 4
    v.A = -GRAV
    v.B = -v.V / v.A                           # VF = V0 + AT with VF = 0 at the top
    v.C = -v.V ** 2 / (2 * v.A)                # VF^2 = V0^2 + 2AS with VF = 0 at the top
    r.add("STEP 1  TIME TO THE TOP", [("T TO TOP", v.B, "S")])
    if v.P == 2:
        r.add("STEP 2  MAX HEIGHT", [("MAX HEIGHT", v.C, "M")])
    else:
        v.E = v.Q + v.C                        # max height above the ground = H + rise
        r.add("STEP 2  MAX HEIGHT", [("ABOVE LAUNCH", v.C, "M"), ("ABOVE GROUND", v.E, "M")])
    if v.P == 4:
        return _q1(r, v)
    v.D = 2 * v.B                              # S = 0 at the end: T = 0 or T = 2V0/9.8
    v.F = -v.V                                 # VF = V0 + A(2V0/9.8) = -V0
    r.add("STEP 3  TOTAL TIME", [("T TOTAL", v.D, "S")])
    r.add("STEP 4  IMPACT VELOCITY", [("VF", v.F, "M/S (DOWN)")])
    r.add("SUMMARY (UP, SAME LEVEL)", [("V0", v.V, "M/S (UP)"), ("T TO TOP", v.B, "S"),
                                       ("MAX HEIGHT", v.C, "M"), ("T TOTAL", v.D, "S"),
                                       ("VF", v.F, "M/S (DOWN)")])
    return r


# ---------------------------------------------------------------- 3: thrown down from height H
def _n1(r, v):
    if v.Q < 0:
        return _msg(r, "E1")
    if v.Q > BIG:
        return _msg(r, "E9")
    if v.V < 0:
        return _msg(r, "E3")
    if v.V > BIG:
        return _msg(r, "E9")
    if v.Q == 0:
        return _msg(r, "E2")
    if v.V == 0:
        _msg(r, "E6")
        return _d2(r, v)
    v.P = 3
    v.V = -v.V                                 # down is negative
    v.A = -GRAV
    r.add("STEP 1  SIGN OF V0", [("V0", v.V, "M/S"), ("A", "-9.8", "M/S² (GRAVITY)")])
    return _q1(r, v)


# ---------------------------------------------------------------- 4: thrown up from height H
def _h1(r, v):
    if v.Q < 0:
        return _msg(r, "E1")
    if v.Q > BIG:
        return _msg(r, "E9")
    if v.V < 0:
        return _msg(r, "E4")
    if v.V > BIG:
        return _msg(r, "E9")
    if v.Q == 0:
        _msg(r, "E7")
        return _u2(r, v)
    if v.V == 0:
        _msg(r, "E6")
        return _d2(r, v)
    v.P = 4
    return _u3(r, v)


# ---------------------------------------------------------------- shared: total time by quadratic
def _q1(r, v):                                 # paths 3 and 4
    v.A = -GRAV
    v.S = -v.Q
    step = "STEP 2"
    if v.P == 4:
        step = "STEP 3"
    r.add(step + "  TIME TO GROUND", [("S", v.S, "M")])
    # S = V0T + (1/2)AT^2  ->  4.9T^2 - V0T + S = 0
    v.L = 4.9
    v.M = -v.V
    v.N = v.S
    v.I = 0
    v.J, v.H, v.I, v.G, qvals = zquad(v.L, v.M, v.N)
    if v.I is None:
        v.I = 0
    if v.J < 2 or v.I <= 0:
        r.messages.append("E8")
        r.add("SOLVE QUADRATIC FOR T", qvals, rows=MESSAGES["E8"])
        return r
    v.D = v.I                                  # T1 < 0 is before the throw: use T2
    r.add("SOLVE QUADRATIC FOR T", qvals + [("T TOTAL", v.D, "S")])
    if v.P == 3:
        return _f1(r, v)
    v.G = math.sqrt(2 * v.E / 9.8)             # from the top: falls E from rest, T = sqrt(2S/A)
    r.add("STEP 4  TOP TO GROUND", [("ABOVE GROUND", v.E, "M"), ("T TOP TO GND", v.G, "S")])
    return _f1(r, v)


# ---------------------------------------------------------------- shared: impact velocity
def _f1(r, v):                                 # paths 1, 3 and 4
    v.N = v.V ** 2 + 2 * v.A * v.S             # VF^2 = V0^2 + 2AS
    v.F = -math.sqrt(v.N)                      # moving down: negative root
    step = "STEP 2"
    if v.P == 3:
        step = "STEP 3"
    if v.P == 4:
        step = "STEP 5"
    r.add(step + "  IMPACT VELOCITY", [("VF² IS", v.N, ""), ("VF", v.F, "M/S (DOWN)")])
    if v.P == 1:
        r.add("SUMMARY (DROPPED)", [("V0", 0, "M/S"), ("T TO TOP", 0, "S"), ("MAX HEIGHT", v.Q, "M"),
                                    ("T TOTAL", v.D, "S"), ("VF", v.F, "M/S (DOWN)")])
        return r
    if v.P == 3:
        r.add("SUMMARY (THROWN DOWN)", [("V0", v.V, "M/S (DOWN)"), ("MAX HEIGHT", v.Q, "M"),
                                        ("T TOTAL", v.D, "S"), ("VF", v.F, "M/S (DOWN)")])
        return r
    r.add("SUMMARY (UP FROM HEIGHT)", [("V0", v.V, "M/S (UP)"), ("T TO TOP", v.B, "S"),
                                       ("ABOVE LAUNCH", v.C, "M"), ("ABOVE GROUND", v.E, "M"),
                                       ("T TOP TO GND", v.G, "S"), ("T TOTAL", v.D, "S"),
                                       ("VF", v.F, "M/S (DOWN)")])
    return r


if __name__ == "__main__":
    from common import fmt3
    for args in [(2, 19.6), (1, 45), (4, 15, 10), (3, 20, 5)]:
        res = run(*args)
        print(args, {k: (fmt3(x) if not isinstance(x, str) else x) for k, x in res.summary.items()})
