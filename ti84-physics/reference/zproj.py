"""
Reference implementation of prgmZPROJ (PHYSOLVE items C, D, E: projectile motion), mirroring
src/ZPROJ.txt label by label: the same input checks in the same order, the same equations, the
same branches and the same screen text. Class conventions: g = 9.8 m/s^2, up is +, so the
vertical acceleration is A = -9.8 m/s^2 and the horizontal acceleration is 0; no air resistance.

PHYSOLVE calls ZPROJ with K = 1 (C, horizontal launch), K = 2 (D, angled launch) or
K = 3 (E, throw lab worked backward). Any other K is treated as 1.

TI variables (the same letters are used below):
  C  horizontal:  P = mode (1 given V, 2 given range)  Q = H   V = vx   E = range
                  S = -H   D = t   F = vy at impact     B = impact speed   C = impact angle
  D  angled:      V = v0   E = angle (deg)   Q = h (launch height above the landing point)
                  B = vx   C = v0y   P = time to top   S = RISE (top above the launch point)
                  A = MAX H (top above the landing point, = Q+S)
                  L, M, N -> prgmZQUAD (4.9, -v0y, -h); J, H, I, G <- prgmZQUAD
                  D = flight time (= I, the later root)   L = range   F = vy at impact
                  M = impact speed (HIT SPEED)   N = impact angle below horizontal (-1 = none)
  E  throw lab:   P = units (1 m, 2 yd)   Q = H   D = t   N = range as typed   E = range (m)
                  B = vx   C = v0y   V = launch speed   A = launch angle (+ above horizontal)

run(k, *keys) feeds the same keys the calculator would get after PHYSOLVE's menu choice (menu
option numbers and typed numbers, in order) and returns a Result:
  .screens  one Screen per Pause, each a list of lines; a line is a template with "{}" slots
            and the numbers that go in them (shown through ZFMT = common.fmt3).
            Screen.rows() renders the 26-column rows exactly like the calculator.
  .menus    [(title, option chosen)] for ZPROJ's own menus
  .message  label of the message screen shown (M1..M9 or "D5"), or None
  .inputs   (rows shown above the prompts, prompts) of the input screen ZPROJ showed, or None
  .summary  {name: number} from the SUMMARY screen ("NAME = {} UNIT" lines)
  .quad     (J, H, I, G) from the prgmZQUAD call (angled launch), or None
"""
import math
import re

from common import G as GRAV, fmt3      # g = 9.8 m/s^2; fmt3 = what prgmZFMT prints

LO, HI = 1e-6, 1e6                       # allowed sizes of typed numbers (besides 0)
YD_PER_M = 1.0936                        # 1 m = 1.0936 yd, so yards -> meters is /1.0936
COLS = 26

MENU_C = ("HORIZONTAL LAUNCH", ("GIVEN H AND SPEED V", "GIVEN H AND RANGE", "BACK"))
MENU_E = ("THROW LAB (BACKWARD)", ("RANGE IN METERS", "RANGE IN YARDS", "BACK"))

NEG_HINT = "NEGATIVE = (-) KEY"           # SPEC 7b: on every input screen that takes a negative
KEEPS = "(CALC KEEPS ALL DIGITS)"        # the substituted numbers are rounded; the math is not

# Input screens: (rows Disp'ed after ClrHome, Input prompts). The prompts follow on the next rows.
INPUT_C1 = (("HORIZONTAL LAUNCH",            # Lbl C1 (H and V are never negative: no hint)
             "LAUNCHED LEVEL (ANGLE 0)",
             "FROM HEIGHT H ABOVE THE",
             "LANDING POINT. UP IS +.",
             "ENTER H AS A POSITIVE",
             "NUMBER AND THE LAUNCH",
             "SPEED V."),
            ("HEIGHT H (M)=", "SPEED V (M/S)="))
INPUT_C2 = (("HORIZONTAL LAUNCH",            # Lbl C2
             "LAUNCHED LEVEL (ANGLE 0)",
             "FROM HEIGHT H ABOVE THE",
             "LANDING POINT. UP IS +.",
             "ENTER H AS A POSITIVE",
             "NUMBER AND THE RANGE (HOW",
             "FAR IT WENT SIDEWAYS)."),
            ("HEIGHT H (M)=", "RANGE (M)="))
INPUT_D = (("ANGLED LAUNCH (UP IS +)",       # Lbl D0 (angle and H may be negative)
            "ANGLE- DEGREES ABOVE THE",
            "HORIZONTAL, - IF DOWNWARD.",
            "H- LAUNCH HEIGHT ABOVE THE",
            "LANDING POINT (0 IF LEVEL,",
            "- IF IT LANDS HIGHER).",
            NEG_HINT),
           ("SPEED V0 (M/S)=", "ANGLE (DEG)=", "HEIGHT H (M)="))
INPUT_E_ROWS = ("THROW LAB- WORK BACKWARD",    # Lbl E3 (H may be negative)
                "H- LAUNCH HEIGHT ABOVE THE",
                "LANDING POINT (0 IF LEVEL,",
                "- IF IT LANDS HIGHER).",
                "T- TIME IN THE AIR.",
                "RANGE- HOW FAR SIDEWAYS.",
                NEG_HINT)
INPUT_E = {1: (INPUT_E_ROWS, ("HEIGHT H (M)=", "TIME T (S)=", "RANGE (M)=")),
           2: (INPUT_E_ROWS, ("HEIGHT H (M)=", "TIME T (S)=", "RANGE (YD)="))}

# Extra M2 rows when M2 comes from the angled launch (If K=2): the direction is in the angle.
M2_ANGLED = ("FOR A DOWNWARD THROW, USE",
             "A NEGATIVE ANGLE.")

# Message screens (label -> rows). D5 is shown under prgmZQUAD's rows (no ClrHome).
MESSAGES = {
    "M1": ("H MUST BE MORE THAN 0.",            # horizontal launch with H <= 0
           "H IS THE HEIGHT OF THE",
           "LAUNCH ABOVE THE LANDING",
           "POINT. WITH H AT 0 IT IS",
           "ALREADY ON THE GROUND."),
    "M2": ("THE SPEED CANNOT BE",               # negative launch speed (C or D)
           "NEGATIVE. ENTER IT AS A",
           "POSITIVE NUMBER (OR 0).",
           "(SPEED HAS NO DIRECTION-",
           "THE PROGRAM HANDLES THE",
           "SIGNS FOR YOU.)"),
    "M3": ("THE RANGE CANNOT BE",               # negative range (C given range, or E)
           "NEGATIVE. ENTER HOW FAR IT",
           "WENT SIDEWAYS AS A",
           "POSITIVE NUMBER (OR 0)."),
    "M4": ("THE ANGLE MUST BE FROM",            # |angle| > 90
           "-90 TO 90 DEGREES",
           "(+ IS ABOVE HORIZONTAL,",
           "- IS BELOW HORIZONTAL)."),
    "M5": ("H IS 0 AND V0Y IS NOT",             # level ground and not launched upward
           "UPWARD (ANGLE ≤ 0 OR V0",
           "IS 0), SO IT IS ON THE",
           "GROUND RIGHT AWAY- THERE",
           "IS NO FLIGHT TO SOLVE."),
    "M6": ("THE LANDING POINT IS",              # landing higher (h < 0) and not launched upward
           "HIGHER (H<0), BUT V0Y IS",
           "NOT UPWARD (ANGLE ≤ 0 OR",
           "V0 IS 0), SO IT CAN NEVER",
           "GET UP THERE."),
    "M7": ("THE TIME T MUST BE MORE",           # throw lab with t <= 0
           "THAN 0 (HOW LONG IT WAS",
           "IN THE AIR)."),
    "M9": ("THAT NUMBER IS TOO LARGE",          # a typed size above 1E6 or below 1E-6 (not 0)
           "OR TOO SMALL. KEEP SIZES",
           "FROM 1E-6 TO 1E6 (0 IS OK",
           "WHERE IT IS ALLOWED)."),
    "D5": ("IT NEVER GETS AS HIGH AS",          # B^2-4AC < 0: never reaches the landing height
           "THE LANDING POINT. CHECK",
           "V0, THE ANGLE AND H."),
}

_VALUE_TMPL = re.compile(r"^(.+?) = \{\}(.*)$")


class Screen:
    """One Pause screen: lines of ('disp' | 'zline', template, numbers)."""

    def __init__(self):
        self.lines = []

    def disp(self, tmpl, *nums):
        self.lines.append(("disp", tmpl, nums))

    def zline(self, tmpl, *nums):        # prgmZLINE: wrapped into 26-character rows
        self.lines.append(("zline", tmpl, nums))

    def rows(self, fmt=fmt3):
        out = []
        for kind, tmpl, nums in self.lines:
            text = tmpl.format(*[fmt(x) for x in nums])
            if kind == "zline":
                out += [text[i:i + COLS] for i in range(0, len(text), COLS)]
            else:
                out.append(text)
        return out

    @property
    def title(self):
        return self.lines[0][1] if self.lines else ""

    def numbers(self):
        """{name: number} for every 'NAME = {} UNIT' line of this screen."""
        out = {}
        for kind, tmpl, nums in self.lines:
            m = _VALUE_TMPL.match(tmpl)
            if kind == "disp" and m and len(nums) == 1:
                out[m.group(1)] = nums[0]
        return out


class Result:
    def __init__(self):
        self.screens = []
        self.menus = []
        self.message = None
        self.quad = None
        self.inputs = None

    def new_screen(self):                # ClrHome
        s = Screen()
        self.screens.append(s)
        return s

    @property
    def summary(self):
        last = self.screens[-1] if self.screens else None
        if last is None or not last.title.startswith("SUMMARY"):
            return {}
        return last.numbers()


class _Keys:
    def __init__(self, keys):
        self.keys = list(keys)

    def __call__(self):
        if not self.keys:
            raise ValueError("ZPROJ asked for more keys than were given")
        return self.keys.pop(0)


def _size_bad(x, zero_ok=True):
    """abs(x)>1E6 or (x≠0 and abs(x)<1E-6) -- the M9 check."""
    return abs(x) > HI or ((x != 0 or not zero_ok) and abs(x) < LO)


def _msg(r, label, scr=None, extra=()):
    """Message screen: ClrHome (unless shown under ZQUAD's rows), rows, Pause, Return."""
    scr = scr if scr is not None else r.new_screen()
    for row in MESSAGES[label] + tuple(extra):
        scr.disp(row)
    r.message = label
    return r


def _dir(x, up=" (UP)", down=" (DOWN)"):
    return up if x > 0 else down if x < 0 else ""


def zquad(scr, l, m, n):
    """Mirror of prgmZQUAD for L*T^2 + M*T + N = 0 (L is never 0 here). Returns (J, H, I, G)."""
    scr.disp("SOLVE QUADRATIC FOR T")
    scr.zline("{}T²" + ("+" if (m >= 0 or abs(m) < 1e-9) else "") + "{}T" + ("+" if (n >= 0 or abs(n) < 1e-9) else "") + "{}=0", l, m, n)
    g = m * m - 4 * l * n
    if abs(g) < 1e-10 * (m * m + abs(4 * l * n)):
        g = 0.0
    scr.disp("T=(-B+/-√(B²-4AC))/(2A)")
    scr.disp("B²-4AC = {}", g)
    if g < 0:
        scr.disp("B²-4AC<0 SO NO REAL ROOT")
        return 0, None, None, g
    # stable form (no cancellation): q = -(M + sign(M)*sqrt(G))/2, roots q/L and N/q
    q = (-m - math.sqrt(g)) / 2 if m >= 0 else (-m + math.sqrt(g)) / 2
    if q == 0:
        h = i = 0.0
    else:
        h = q / l
        i = n / q
    if h > i:
        h, i = i, h
    scr.disp("T1 = {} S", h)
    scr.disp("T2 = {} S", i)
    return 2, h, i, g


def _sin(deg):
    return math.sin(math.radians(deg))


def _cos(deg):
    return math.cos(math.radians(deg))


def _angle(x, y):
    """R►Pθ(x,y) in Degree mode."""
    return math.degrees(math.atan2(y, x))


# ----------------------------------------------------------------------------- dispatch
def run(k, *keys):
    r = Result()
    key = _Keys(keys)
    if k == 2:                                        # If K=2 / Goto D0
        return _angled(r, key)
    if k == 3:                                        # If K=3 / Goto E0
        return _throw_lab(r, key)
    return _horizontal(r, key)                        # Lbl C0 (any other K)


# ----------------------------------------------------------------------------- C: horizontal
def _horizontal(r, key):
    choice = key()                                    # Menu("HORIZONTAL LAUNCH",...)
    r.menus.append((MENU_C[0], choice))
    if choice == 3:                                   # BACK -> Lbl Q0 / Return
        return r
    if choice == 1:                                   # Lbl C1
        p = 1
        r.inputs = INPUT_C1
        q = key()                                     # Input "HEIGHT H (M)=",Q
        v = key()                                     # Input "SPEED V (M/S)=",V
        e = None
    else:                                             # Lbl C2
        p = 2
        r.inputs = INPUT_C2
        q = key()                                     # Input "HEIGHT H (M)=",Q
        e = key()                                     # Input "RANGE (M)=",E
        v = None
    # Lbl C3
    if q <= 0:
        return _msg(r, "M1")
    if q < LO or q > HI:
        return _msg(r, "M9")
    if p != 2:
        if v < 0:
            return _msg(r, "M2")
        if v > HI or (v > 0 and v < LO):
            return _msg(r, "M9")
    else:                                             # Lbl C4
        if e < 0:
            return _msg(r, "M3")
        if e > HI or (e > 0 and e < LO):
            return _msg(r, "M9")
    # Lbl C5
    s = -q
    d = math.sqrt(2 * q / GRAV)
    scr = r.new_screen()
    scr.disp("STEP 1  TIME TO FALL")
    scr.disp("VERTICAL- V0Y IS 0 AND A")
    scr.disp("IS -9.8 M/S². IT ENDS H")
    scr.disp("BELOW THE START, SO")
    scr.disp("S = {} M", s)
    scr.disp("USE S=V0YT+(1/2)AT²")
    scr.disp("{}=0+(1/2)(-9.8)T²", s)
    scr.disp("T=√(2H/9.8)")
    scr.disp("T=√(2({})/9.8)", q)
    scr.disp("T FLIGHT = {} S", d)
    if p != 2:
        e = v * d                                     # VD->E
        scr = r.new_screen()
        scr.disp("STEP 2  RANGE")
        scr.disp("HORIZONTAL- A IS 0, SO VX")
        scr.disp("STAYS V THE WHOLE TIME.")
        scr.disp("X AND Y SHARE THE SAME T.")
        scr.disp("RANGE=VX*T")
        scr.zline("RANGE=({})({})", v, d)
        scr.disp("RANGE = {} M", e)
        scr.disp(KEEPS)
    else:                                             # Lbl C6
        v = e / d
        scr = r.new_screen()
        scr.disp("STEP 2  LAUNCH SPEED")
        scr.disp("HORIZONTAL- A IS 0, SO VX")
        scr.disp("STAYS THE SAME THE WHOLE")
        scr.disp("TIME. X AND Y SHARE T.")
        scr.disp("RANGE=VX*T, SO VX=RANGE/T")
        scr.disp("VX={}/{}", e, d)
        scr.disp("VX = {} M/S", v)
        scr.disp(KEEPS)
    # Lbl C7
    f = -GRAV * d
    scr = r.new_screen()
    scr.disp("STEP 3  FINAL VX AND VY")
    scr.disp("HORIZONTAL- VX NEVER")
    scr.disp("CHANGES (A IS 0), SO")
    scr.disp("VFX = {} M/S", v)
    scr.disp("VERTICAL- USE VF=V0+AT")
    scr.disp("VFY=0+(-9.8)({})", d)
    scr.disp("VFY = {} M/S (DOWN)", f)
    b = math.sqrt(v * v + f * f)
    c = _angle(v, abs(f))                             # R►Pθ(V,abs(F)) (F<0 always)
    scr = r.new_screen()
    scr.disp("STEP 4  IMPACT SPEED/ANGLE")
    scr.disp("SPEED=√(VFX²+VFY²)")
    scr.zline("SPEED=√({}²+{}²)", v, abs(f))
    scr.disp("HIT SPEED = {} M/S", b)
    scr.disp("ANGLE BELOW HORIZONTAL-")
    if v != 0:
        scr.disp("ANGLE=TAN⁻1(|VFY|/VFX)")
        scr.zline("ANGLE=TAN⁻1({}/{})", abs(f), v)
    else:                                             # Lbl C8
        scr.disp("VFX IS 0, SO IT FALLS")
        scr.disp("STRAIGHT DOWN-")
    # Lbl C9
    scr.disp("ANGLE = {}° BELOW", c)
    scr = r.new_screen()
    scr.disp("SUMMARY (HORIZONTAL)")
    scr.disp("H = {} M", q)
    scr.disp("T FLIGHT = {} S", d)
    scr.disp("VX = {} M/S", v)
    scr.disp("RANGE = {} M", e)
    scr.disp("VFX = {} M/S", v)
    scr.disp("VFY = {} M/S (DOWN)", f)
    scr.disp("HIT SPEED = {} M/S", b)
    scr.disp("ANGLE = {}° BELOW", c)
    return r                                          # Return


# ----------------------------------------------------------------------------- D: angled
def _angled(r, key):
    # Lbl D0: instructions, then the three inputs
    r.inputs = INPUT_D
    v = key()                                         # Input "SPEED V0 (M/S)=",V
    e = key()                                         # Input "ANGLE (DEG)=",E
    q = key()                                         # Input "HEIGHT H (M)=",Q
    if v < 0:
        return _msg(r, "M2", extra=M2_ANGLED)             # If K=2 rows of Lbl M2
    if v > HI or (v > 0 and v < LO):
        return _msg(r, "M9")
    if abs(e) > 90:
        return _msg(r, "M4")
    if _size_bad(q):
        return _msg(r, "M9")
    b = v * _cos(e)
    c = v * _sin(e)
    if abs(b) < 1e-12 * v:                            # cos(90°) / sin(0°) round-off -> exactly 0
        b = 0.0
    if abs(c) < 1e-12 * v:
        c = 0.0
    if q == 0 and c <= 0:
        return _msg(r, "M5")
    if q < 0 and c <= 0:
        return _msg(r, "M6")
    scr = r.new_screen()
    scr.disp("STEP 1  COMPONENTS OF V0")
    scr.disp("VX=V0COS(ANGLE)")
    scr.zline("VX=({})COS({}°)", v, e)
    scr.disp("VX = {} M/S", b)
    scr.disp("V0Y=V0SIN(ANGLE)")
    scr.zline("V0Y=({})SIN({}°)", v, e)
    scr.disp("V0Y = {} M/S" + _dir(c), c)
    scr.disp(KEEPS)
    p = 0.0
    s = 0.0
    if c > 0:
        p = c / GRAV                                  # time to the top
        s = c * c / (2 * GRAV)                        # max height above the launch point
    a = q + s                                         # max height above the landing point
    scr = r.new_screen()
    scr.disp("STEP 2  TIME TO TOP, MAX H")
    if c <= 0:
        scr.disp("V0Y IS NOT UPWARD, SO IT")
        scr.disp("STARTS GOING DOWN (OR")
        scr.disp("LEVEL). ITS HIGHEST POINT")
        scr.disp("IS THE LAUNCH POINT-")
        scr.disp("T TOP = 0 S (AT LAUNCH)")
    else:                                             # Lbl D2
        scr.disp("AT TOP VY IS 0- VF=V0+AT")
        scr.disp("0={}+(-9.8)T", c)
        scr.disp("T TOP = {} S", p)
        scr.disp("RISE ABOVE THE LAUNCH-")
        scr.disp("USE VF²=V0²+2AS")
        scr.disp("0=({})²+2(-9.8)S", c)
    # Lbl D3: RISE is above the launch point, MAX H above the landing point (like H)
    scr.disp("RISE = {} M", s)
    scr.disp("H+RISE={}+{}", q, s)
    scr.disp("MAX H = {} M", a)
    scr = r.new_screen()
    scr.disp("STEP 3  FLIGHT TIME")
    scr.disp("VERTICAL- IT LANDS H BELOW")
    scr.disp("THE LAUNCH, SO S IS -H-")
    scr.disp("S = {} M", -q)
    scr.disp("USE S=V0YT+(1/2)AT²")
    scr.disp("(1/2)A IS -4.9, SO")
    scr.zline("{}={}T-4.9T²", -q, c)
    scr.disp("4.9T²-V0YT-H=0 (QUADRATIC)")
    scr.disp("SOLVE IT FOR T (NEXT).")
    # 4.9T² - V0Y*T - H = 0  ->  L = 4.9, M = -V0Y, N = -H
    scr = r.new_screen()
    j, h, i, g = zquad(scr, 4.9, -c, -q)
    r.quad = (j, h, i, g)
    if j == 0:                                        # Lbl D5 (rows under ZQUAD's)
        return _msg(r, "D5", scr)
    d = i                                             # the later root is the landing
    if q > 0:
        scr.disp("T1<0 IS BEFORE THE LAUNCH,")
        scr.disp("SO IT LANDS AT T2-")
    if q == 0:
        scr.disp("T1 IS 0 (THE LAUNCH), SO")
        scr.disp("IT LANDS AT T2-")
    if q < 0 and g > 0:
        scr.disp("T1 PASSES THAT LEVEL GOING")
        scr.disp("UP, T2 LANDS COMING DOWN-")
    if q < 0 and g == 0:                              # double root: reaches that level at the top
        scr.disp("ONE ROOT- IT JUST REACHES")
        scr.disp("THAT LEVEL AT ITS TOP-")
    scr.disp("T FLIGHT = {} S", d)
    rng = b * d                                       # BD->L
    scr = r.new_screen()
    scr.disp("STEP 4  RANGE (HORIZONTAL)")
    scr.disp("HORIZONTAL- A IS 0, SO VX")
    scr.disp("NEVER CHANGES (VFX IS VX).")
    scr.disp("VX = {} M/S", b)
    scr.disp("RANGE=VX*T")
    scr.zline("RANGE=({})({})", b, d)
    scr.disp("RANGE = {} M", rng)
    if q == 0:
        scr.disp("LEVEL GROUND- T=2V0Y/9.8")
        scr.disp("AND MAX RANGE IS AT 45°.")
    f = c - GRAV * d                                  # VF = V0 + AT (vertical)
    if abs(f) < 1e-10 * abs(c):                       # lands exactly at the top: VFY is 0
        f = 0.0
    scr = r.new_screen()
    scr.disp("STEP 5  VFY AT IMPACT")
    scr.disp("VERTICAL- USE VF=V0+AT")
    scr.zline("VFY={}+(-9.8)({})", c, d)
    scr.disp("VFY = {} M/S" + (" (DOWN)" if f < 0 else ""), f)
    if f < 0:
        scr.disp("(- MEANS MOVING DOWNWARD)")
    m = math.sqrt(b * b + f * f)                      # impact speed
    if b == 0 and f == 0:
        n = -1.0                                      # no impact angle (speed 0)
    else:
        n = _angle(b, abs(f))                         # R►Pθ(B,abs(F)): degrees below horizontal
    scr = r.new_screen()
    scr.disp("STEP 6  IMPACT SPEED/ANGLE")
    scr.disp("SPEED=√(VFX²+VFY²)")
    scr.zline("SPEED=√({}²+{}²)", b, abs(f))
    scr.disp("HIT SPEED = {} M/S", m)
    if n < 0:                                         # Lbl D6
        scr.disp("IT LANDS RIGHT AT THE TOP")
        scr.disp("WITH SPEED 0, SO THERE IS")
        scr.disp("NO IMPACT ANGLE.")
    else:
        scr.disp("ANGLE BELOW HORIZONTAL-")
        if b != 0:
            scr.disp("ANGLE=TAN⁻1(|VFY|/VFX)")
            scr.zline("ANGLE=TAN⁻1({}/{})", abs(f), b)
        else:                                         # Lbl D7
            scr.disp("VFX IS 0, SO IT IS MOVING")
            scr.disp("STRAIGHT DOWN-")
        # Lbl D8
        scr.disp("ANGLE = {}° BELOW", n)
    # Lbl D9
    scr = r.new_screen()
    scr.disp("SUMMARY (ANGLED LAUNCH)")
    scr.disp("VX = {} M/S", b)
    scr.disp("V0Y = {} M/S" + _dir(c), c)
    if c <= 0:
        scr.disp("T TOP = 0 S (AT LAUNCH)")
    if c > 0:
        scr.disp("T TOP = {} S", p)
    if q != 0:
        scr.disp("RISE = {} M", s)
    scr.disp("MAX H = {} M", a)
    scr.disp("T FLIGHT = {} S", d)
    scr.disp("RANGE = {} M", rng)
    scr.disp("HIT SPEED = {} M/S", m)
    if n >= 0:
        scr.disp("ANGLE = {}° BELOW", n)
    else:
        scr.disp("ANGLE- NONE (SPEED IS 0)")
    return r                                          # Return


# ----------------------------------------------------------------------------- E: throw lab
def _throw_lab(r, key):
    choice = key()                                    # Menu("THROW LAB (BACKWARD)",...)
    r.menus.append((MENU_E[0], choice))
    if choice == 3:                                   # BACK
        return r
    p = 1 if choice == 1 else 2                       # Lbl E1 / Lbl E2
    # Lbl E3: instructions, then the inputs
    r.inputs = INPUT_E[p]
    q = key()                                         # Input "HEIGHT H (M)=",Q
    d = key()                                         # Input "TIME T (S)=",D
    n = key()                                         # Input "RANGE (M)=",N  or "RANGE (YD)=",N
    if _size_bad(q):
        return _msg(r, "M9")
    if d <= 0:
        return _msg(r, "M7")
    if d > HI or d < LO:
        return _msg(r, "M9")
    if n < 0:
        return _msg(r, "M3")
    if n > HI or (n > 0 and n < LO):
        return _msg(r, "M9")
    e = n
    if p == 2:
        e = n / YD_PER_M                              # yards -> meters
    b = e / d                                         # VX = RANGE/T
    c = (4.9 * d * d - q) / d                         # from -H = V0Y*T - 4.9T^2
    v = math.sqrt(b * b + c * c)                      # launch speed
    a = 0.0
    if v != 0:
        a = _angle(b, c)                              # R►Pθ(B,C): + above, - below horizontal
    scr = r.new_screen()
    scr.disp("STEP 1  VX (HORIZONTAL)")
    if p != 1:
        scr.disp("YARDS TO METERS- DIVIDE")
        scr.disp("BY 1.0936 (1 M=1.0936 YD)")
        scr.disp("RANGE={}/1.0936", n)
    # Lbl E4
    scr.disp("RANGE = {} M", e)
    scr.disp("HORIZONTAL- A IS 0, SO")
    scr.disp("VX=RANGE/T")
    scr.disp("VX={}/{}", e, d)
    scr.disp("VX = {} M/S", b)
    scr.disp(KEEPS)
    scr = r.new_screen()
    scr.disp("STEP 2  V0Y (VERTICAL)")
    scr.disp("IT ENDS H BELOW THE START,")
    scr.disp("SO S IS -H. A IS -9.8.")
    scr.disp("S = {} M", -q)
    scr.disp("USE S=V0YT+(1/2)AT²")
    scr.disp("(1/2)A IS -4.9, SO")
    scr.disp("V0Y=(S+4.9T²)/T")
    scr.zline("=({}+4.9({})²)/{}", -q, d, d)
    scr.disp("V0Y = {} M/S" + _dir(c), c)
    scr = r.new_screen()
    scr.disp("STEP 3  LAUNCH SPEED/ANGLE")
    scr.disp("V0=√(VX²+V0Y²)")
    scr.zline("V0=√({}²+{}²)", b, abs(c))
    scr.disp("V0 = {} M/S", v)
    if v != 0:
        scr.disp("ANGLE FROM HORIZONTAL-")
        scr.disp("ANGLE=TAN⁻1(V0Y/VX)")
        if b != 0:
            scr.zline("ANGLE=TAN⁻1({}/{})", c, b)
        else:                                         # Lbl E6
            scr.disp("VX IS 0, SO IT IS THROWN")
            scr.disp("STRAIGHT UP OR DOWN-")
        # Lbl E7
        scr.disp("ANGLE = {}°" + _dir(a, " (ABOVE)", " (BELOW)"), a)
    else:                                             # Lbl E5
        scr.disp("V0 IS 0- IT WAS DROPPED")
        scr.disp("FROM REST, SO THERE IS NO")
        scr.disp("LAUNCH ANGLE.")
    # Lbl E8
    scr = r.new_screen()
    scr.disp("SUMMARY (THROW LAB)")
    scr.disp("H = {} M", q)
    scr.disp("T FLIGHT = {} S", d)
    scr.disp("RANGE = {} M", e)
    if p == 2:
        scr.disp("(FROM {} YD)", n)
    scr.disp("VX = {} M/S", b)
    scr.disp("V0Y = {} M/S" + _dir(c), c)
    scr.disp("V0 = {} M/S", v)
    if v == 0:
        scr.disp("ANGLE- NONE (V0 IS 0)")
    else:
        scr.disp("ANGLE = {}°" + _dir(a, " (ABOVE)", " (BELOW)"), a)
    return r                                          # Return


if __name__ == "__main__":                           # python3 reference/zproj.py 2 25 50 0
    import sys
    res = run(int(sys.argv[1]), *[float(x) for x in sys.argv[2:]])
    for scr in res.screens:
        print("+" + "-" * COLS + "+")
        for row in scr.rows():
            print("|" + row.ljust(COLS) + "|")
    print("+" + "-" * COLS + "+")
    print("message:", res.message, " summary:", res.summary)
