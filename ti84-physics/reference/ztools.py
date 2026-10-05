"""
Reference implementation of prgmZTOOLS (PHYSOLVE page 2, options 3-6), mirroring src/ZTOOLS.txt
line for line: the same input checks in the same order, the same equations, the same branches,
and the same screens and messages (every row is rebuilt here, so the tests can compare whole
screens row by row).

PHYSOLVE sets K before calling prgmZTOOLS:
    K=1 (or anything else)  H. VECTOR COMPONENTS   -> vector_mag_angle(), vector_xy()
    K=2                     I. AVG SPEED/VELOCITY  -> averages()
    K=3                     J. FACTOR OF CHANGE    -> factor()
    K=4                     K. LAB TOOLS           -> ramp(), pct_diff(), pct_error(), yd_to_m(),
                                                      m_to_yd(), kmh_to_ms(), mph_to_ms()

Class facts used (from the student):
    * vectors: angle measured counterclockwise from +X; X = M cos(angle), Y = M sin(angle);
      M = sqrt(X^2+Y^2); reference angle = tan^-1(|Y|/|X|) (R>Ptheta( handles X = 0);
      angle from +X = R>Ptheta(X,Y), shown 0..360 (and as -180..0 "clockwise" when above 180)
    * average speed = total distance / total time; average velocity = displacement / total time
    * factor of change: s prop to v^2 when stopping, s prop to t^2 from rest, t prop to sqrt(h)
      when falling, v prop to sqrt(h) (impact speed of a drop), v prop to t from rest
    * ramp: graph s vs t^2, slope = a/2, so a = 2*slope
    * percent difference = |a-b| / |average| x 100;  percent error = |acc-exp| / |acc| x 100
    * 1 m = 1.0936 yd;  km/h / 3.6 = m/s;  mph * 0.44704 = m/s

Every function returns a Result whose .screens list has one Screen per Pause screen:
    Screen.title  = first row
    Screen.rows   = every row the program writes on that screen (exact text, ZLINE-wrapped)
    Screen.values = [(name, value, tail)] for each "NAME = VALUE..." row, in screen order; value
                    is a number (tests format it with fmt3, like prgmZFMT) or a literal string the
                    program prints as text; tail is the exact text after the number (" M/S", "°",
                    " M (RIGHT)", ...)
Result.messages lists the message labels shown (H6..HA, I2..I7, J6..J8, K6..K8),
Result.prompts the Input prompts asked, Result.info the rows on the screen while typing,
Result.results the computed numbers (unrounded).
"""
import math
from decimal import Decimal, Context, ROUND_HALF_UP, ROUND_DOWN

from common import fmt3

COLS = 26
BIG = 1e9          # "THAT NUMBER IS TOO LARGE" above this (keeps squares/sums far from overflow)
TINY = 1e-9        # ZFMT shows |x| < 1E-9 as "0"; direction words use the same threshold

# The averages, factor-of-change and lab-tool arithmetic (+ - * / and square roots of typed
# decimal numbers) is done like the calculator does it: decimal numbers with 14 significant
# digits, results below 1E-99 in size becoming 0. (The vector tool uses binary floats for its
# trig; the tests allow for 3-s.f. rounding-edge differences there.)
_TI = Context(prec=14, rounding=ROUND_HALF_UP, Emax=999, Emin=-999)
BIGD, TINYD = Decimal("1E9"), Decimal("1E-9")


def ti(x):
    """Round a Decimal result to 14 significant digits; |x| < 1E-99 becomes 0."""
    x = _TI.plus(x)
    return Decimal(0) if x != 0 and abs(x) < Decimal("1E-99") else x


def num(x):
    """A typed number as the calculator stores it."""
    return ti(Decimal(repr(x)) if isinstance(x, float) else Decimal(x))


def div(a, b):
    return ti(_TI.divide(a, b))


def tf(x):
    """A float result stored by the calculator: 14 significant digits (|x| < 1E-99 -> 0)."""
    return float(ti(Decimal(repr(float(x)))))


def trig_deg(f, x):
    """sin(/cos( in Degree mode: exact at multiples of 90 degrees (sin(180) is exactly 0 on the
    calculator), otherwise the usual value rounded to 14 digits."""
    xm = Decimal(repr(float(x))) % 360
    if xm < 0:
        xm += 360
    exact = {"sin": {0: 0, 90: 1, 180: 0, 270: -1}, "cos": {0: 1, 90: 0, 180: -1, 270: 0}}[f]
    if xm in exact:
        return float(exact[int(xm)])
    v = (math.sin if f == "sin" else math.cos)(math.radians(float(x)))
    return 0.0 if abs(v) < 1e-13 else tf(v)

# ----------------------------------------------------------------------------- message screens
MESSAGES = {
    # H. vectors (back to the VECTOR COMPONENTS menu)
    "H6": ("MAGNITUDE CANNOT BE",              # M < 0
           "NEGATIVE (IT IS A LENGTH).",
           "FOR THE OPPOSITE",
           "DIRECTION, ADD 180 TO THE",
           "ANGLE (OR SUBTRACT 180 IF",
           "IT IS ABOVE 180) AND USE A",
           "POSITIVE MAGNITUDE."),
    "H7": ("THE ANGLE MUST BE FROM",           # |angle| > 360
           "-360 TO 360 DEGREES,",
           "COUNTERCLOCKWISE FROM +X."),
    "H8": ("THAT NUMBER IS TOO LARGE.",        # |X| or |Y| > 1E9
           "KEEP X AND Y BETWEEN",
           "-1E9 AND 1E9."),
    "HA": ("THAT NUMBER IS TOO LARGE.",        # magnitude > 1E9
           "KEEP THE MAGNITUDE AT OR",
           "BELOW 1E9."),
    # H9 (zero vector) is built in vector_xy() because it shows the unit
    # I. averages (back to PHYSOLVE)
    "I2": ("THE NUMBER OF LEGS MUST",          # N not 1, 2, 3 or 4
           "BE 1, 2, 3 OR 4 (A WHOLE",
           "NUMBER)."),
    "I3": ("DISTANCE CANNOT BE",               # a distance < 0
           "NEGATIVE. ENTER HOW FAR",
           "(0 OR MORE) AND SHOW THE",
           "WAY WITH DIRECTION -1."),
    "I4": ("DIRECTION MUST BE 1 OR -1.",       # direction not 1 / -1
           "USE 1 FOR THE + WAY AND",
           "-1 FOR THE OPPOSITE WAY",
           "(PRESS (-) THEN 1)."),
    "I5": ("TIME CANNOT BE NEGATIVE.",         # a time < 0
           "ENTER HOW LONG THE LEG",
           "TOOK (0 OR MORE SECONDS)."),
    "I6": ("THAT NUMBER IS TOO LARGE.",        # a distance or time > 1E9
           "KEEP DISTANCES AND TIMES",
           "AT OR BELOW 1E9."),
    "I7": ("TOTAL TIME IS 0 (OR BELOW",        # total time < 1E-9
           "1E-9 S). THE AVERAGES",
           "DIVIDE BY THE TOTAL TIME,",
           "SO THEY CANNOT BE FOUND."),
    # J. factor of change (back to the FACTOR OF CHANGE menu)
    "J6": ("THE FACTOR K CANNOT BE",           # K < 0
           "NEGATIVE. K TELLS HOW MANY",
           "TIMES BIGGER OR SMALLER",
           "THE QUANTITY GETS- 3 FOR",
           "TRIPLED, 0.5 FOR HALVED."),
    "J7": ("THAT NUMBER IS TOO LARGE.",        # |old| > 1E9 or K > 1E9
           "KEEP THE OLD VALUE AND K",
           "BETWEEN -1E9 AND 1E9."),
    "J8": ("TIME CANNOT BE NEGATIVE.",         # T prop to sqrt(H): old T < 0
           "ENTER THE OLD FALL TIME",
           "(0 OR MORE SECONDS)."),
    # K. lab tools (back to the LAB TOOLS menu)
    "K6": ("THAT NUMBER IS TOO LARGE.",        # an input > 1E9 in size (every lab tool)
           "KEEP EACH NUMBER BETWEEN",
           "-1E9 AND 1E9."),
    "K7": ("THE AVERAGE (A+B)/2 IS 0,",        # percent difference with A+B = 0
           "SO THE PERCENT DIFFERENCE",
           "WOULD DIVIDE BY 0. IT",
           "CANNOT BE FOUND."),
    "K8": ("THE ACCEPTED VALUE IS 0",          # percent error with ACC = 0 (or |ACC-EXP| > 1E80|ACC|)
           "(OR TOO CLOSE TO 0).",
           "PERCENT ERROR DIVIDES BY",
           "IT, SO IT CANNOT BE FOUND."),
}

# ----------------------------------------------------------------------------- menus
MENU_TOP = {1: "VECTOR COMPONENTS", 2: None, 3: "FACTOR OF CHANGE", 4: "LAB TOOLS"}
MENUS = {
    "VECTOR COMPONENTS": ("MAG+ANGLE TO X,Y", "X,Y TO MAG+ANGLE", "BACK"),
    "WHAT KIND OF VECTOR?": ("DISPLACEMENT (M)", "VELOCITY (M/S)", "ACCELERATION (M/S²)",
                             "OTHER (NO UNIT)", "BACK"),
    "FACTOR OF CHANGE": ("S PROP TO V² (STOP)", "S PROP TO T² (REST)", "T PROP TO √(H) (FALL)",
                         "V PROP TO √(H) (DROP)", "V PROP TO T (REST)", "BACK"),
    "LAB TOOLS": ("RAMP A FROM SLOPE", "PERCENT DIFFERENCE", "PERCENT ERROR", "YARDS AND METERS",
                  "KM/H OR MPH TO M/S", "BACK"),
    "YARDS AND METERS": ("YARDS TO METERS", "METERS TO YARDS", "BACK"),
    "SPEED TO M/S": ("KM/H TO M/S", "MPH TO M/S", "BACK"),
}
UNITS = {1: " M", 2: " M/S", 3: " M/S²", 4: " "}     # Str4 for menu choice 1..4
NO_UNIT = {1: 0, 2: 0, 3: 0, 4: 1}                    # E: 0→E before the menu, 1→E for OTHER (NO UNIT)

# ----------------------------------------------------------------------------- info screens
INFO = {
    "MAG_ANGLE": ("MAG+ANGLE TO X,Y",
                  "ANGLE- COUNTERCLOCKWISE",
                  "FROM +X. 0 RIGHT, 90 UP,",
                  "180 LEFT, 270 OR -90 DOWN.",
                  "120 POINTS UP AND LEFT.",
                  "30° BELOW +X IS -30 OR 330",
                  "NEGATIVE = (-) KEY"),
    "XY": ("X,Y TO MAG+ANGLE",
           "X IS + RIGHT, - LEFT.",
           "Y IS + UP, - DOWN.",
           "NEGATIVE = (-) KEY"),
    "AVG": ("AVG SPEED AND VELOCITY",
            "A TRIP OF 1 TO 4 LEGS.",
            "EACH LEG HAS A DISTANCE",
            "(M), A DIRECTION (+ OR -)",
            "AND A TIME (S).",
            "AVG SPEED=DISTANCE/TIME",
            "AVG VEL=DISPLACEMENT/TIME"),
    "LEG": ("DISTANCE IN M (0 OR MORE)",      # after the "LEG i OF n" row
            "DIRECTION- 1 FOR THE +",
            "WAY, -1 FOR THE - WAY",
            "TIME IN S (0 OR MORE)",
            "NEGATIVE = (-) KEY"),
    "J1": ("S PROP TO V² (STOPPING)",
           "STOPPING (VF=0) WITH THE",
           "SAME A- VF²=V0²+2AS GIVES",
           "S=-V0²/(2A), S PROP TO V².",
           "2X V GIVES 4X S.",
           "(ALSO MAX HEIGHT VS V0)",
           "(K IS 3 IF V TRIPLES)",
           "NEGATIVE = (-) KEY"),
    "J2": ("S PROP TO T² (FROM REST)",
           "FROM REST (V0=0), SAME A-",
           "S=V0T+(1/2)AT²=(1/2)AT²,",
           "SO S PROP TO T².",
           "2X T GIVES 4X S.",
           "(K IS 2 IF T DOUBLES)",
           "(A DROP HAS S<0, UP IS +)",
           "NEGATIVE = (-) KEY"),
    "J3": ("T PROP TO √(H) (FALL TIME)",
           "DROPPED FROM REST FROM A",
           "HEIGHT H- H=(1/2)(9.8)T²,",
           "SO T=√(2H/9.8) AND",
           "T PROP TO √(H).",
           "4X H GIVES 2X T.",
           "(K IS 2 IF H DOUBLES)"),
    "J4": ("V PROP TO √(H) (IMPACT)",
           "DROPPED FROM REST FROM A",
           "HEIGHT H- VF²=V0²+2AS",
           "GIVES V²=2(9.8)H, SO",
           "V PROP TO √(H).",
           "4X H GIVES 2X V.",
           "(K IS 2 IF H DOUBLES)",
           "NEGATIVE = (-) KEY"),
    "J5": ("V PROP TO T (FROM REST)",
           "FROM REST (V0=0), SAME A-",
           "VF=V0+AT=AT, SO",
           "V PROP TO T.",
           "2X T GIVES 2X V.",
           "(K IS 2 IF T DOUBLES)",
           "NEGATIVE = (-) KEY"),
    "RAMP": ("RAMP A FROM SLOPE",
             "FROM REST, S=(1/2)AT².",
             "PLOT S ON THE Y AXIS AND",
             "T² ON THE X AXIS- A LINE",
             "THROUGH 0 WITH SLOPE=A/2,",
             "SO A=2*SLOPE.",
             "NEGATIVE = (-) KEY"),
    "PDIFF": ("PERCENT DIFFERENCE",
              "COMPARES TWO MEASURED",
              "VALUES (NEITHER IS THE",
              "ACCEPTED VALUE)-",
              "%DIFF=|A-B|/|AVG|*100",
              "AVG=(A+B)/2",
              "NEGATIVE = (-) KEY"),
    "PERR": ("PERCENT ERROR",
             "COMPARES YOUR MEASURED",
             "(EXPERIMENTAL) VALUE WITH",
             "THE ACCEPTED (TRUE) VALUE-",
             "%ERROR=|ACC-EXP|/|ACC|*100",
             "NEGATIVE = (-) KEY"),
    "YD2M": ("YARDS TO METERS",
             "1 M IS 1.0936 YD, SO",
             "METERS=YARDS/1.0936",
             "NEGATIVE = (-) KEY"),
    "M2YD": ("METERS TO YARDS",
             "1 M IS 1.0936 YD, SO",
             "YARDS=METERS*1.0936",
             "NEGATIVE = (-) KEY"),
    "KMH": ("KM/H TO M/S",
            "1 KM IS 1000 M AND 1 H IS",
            "3600 S, SO 1 KM/H IS",
            "1000/3600 OR 1/3.6 M/S-",
            "M/S=(KM/H)/3.6",
            "NEGATIVE = (-) KEY"),
    "MPH": ("MPH TO M/S",
            "1 MILE IS 1609.344 M AND",
            "1 H IS 3600 S, SO 1 MPH",
            "IS 0.44704 M/S-",
            "M/S=MPH*0.44704",
            "NEGATIVE = (-) KEY"),
}

PROMPTS = {
    "MAG_ANGLE": ("MAGNITUDE=", "ANGLE (DEG)="),
    "XY": ("X COMPONENT=", "Y COMPONENT="),
    "LEGS": ("NUMBER OF LEGS=",),
    "LEG": ("DISTANCE (M)=", "DIRECTION (1/-1)=", "TIME (S)="),
    "J1": ("OLD S (M)=", "V FACTOR K="),
    "J2": ("OLD S (M)=", "T FACTOR K="),
    "J3": ("OLD T (S)=", "H FACTOR K="),
    "J4": ("OLD V (M/S)=", "H FACTOR K="),
    "J5": ("OLD V (M/S)=", "T FACTOR K="),
    "RAMP": ("SLOPE (M/S²)=",),
    "PDIFF": ("VALUE A=", "VALUE B="),
    "PERR": ("EXPERIMENTAL=", "ACCEPTED="),
    "YD2M": ("YARDS=",),
    "M2YD": ("METERS=",),
    "KMH": ("KM/H=",),
    "MPH": ("MPH=",),
}


# ----------------------------------------------------------------------------- screens
class Screen:
    def __init__(self):
        self.rows = []
        self.values = []

    @property
    def title(self):
        return self.rows[0] if self.rows else ""

    def disp(self, text):
        """Disp of a string: one row (the program keeps these within 26 characters)."""
        assert len(text) <= COLS, f"row longer than {COLS}: {text!r}"
        self.rows.append(text)

    def zline(self, text):
        """prgmZLINE: Str0 wrapped into 26-character rows."""
        for k in range(0, len(text), COLS):
            self.rows.append(text[k:k + COLS])

    def val(self, name, x, tail="", wrap=False):
        """Disp "NAME = "+Str9+tail after x->Z, prgmZFMT (wrap=True: built in Str0, prgmZLINE)."""
        shown = x if isinstance(x, str) else fmt3(x)
        row = f"{name} = {shown}{tail}"
        if wrap:
            self.zline(row)
        else:
            self.disp(row)
        self.values.append((name, x, tail))

    def __repr__(self):
        return f"Screen({self.rows!r})"


class Result:
    def __init__(self):
        self.screens = []
        self.messages = []
        self.prompts = []
        self.info = []
        self.results = {}
        self.leg_info = []

    def clrhome(self):
        s = Screen()
        self.screens.append(s)
        return s

    def message(self, label):
        """ClrHome, the message rows, Pause (then back to the tool's menu / PHYSOLVE)."""
        self.messages.append(label)
        s = self.clrhome()
        for row in MESSAGES[label]:
            s.disp(row)
        return self

    def ask(self, key):
        self.prompts.extend(PROMPTS[key])

    def by_title(self, title):
        for s in self.screens:
            if s.title == title:
                return s
        raise KeyError(title)


def fmt_sign_word(x, pos, neg, e=0):
    """' (RIGHT)' / ' (LEFT)' style suffix: only when ZFMT shows a nonzero number.
    e=1 (no unit, Str4=" ") drops the word's leading space: sub(" (RIGHT)",1+E,8-E)."""
    if x >= TINY:
        return pos[e:]
    if x <= -TINY:
        return neg[e:]
    return ""


# ============================================================================= H. vectors
def vector_mag_angle(unit, m, n):
    """Menu VECTOR COMPONENTS 1 (MAG+ANGLE TO X,Y); unit = WHAT KIND OF VECTOR? choice 1..4."""
    r = Result()
    str4 = UNITS[unit]                               # " M" / " M/S" / " M/S²" / " " -> Str4
    E = NO_UNIT[unit]                                # 0→E (Lbl HU) / 1→E (Lbl U4)
    r.info = list(INFO["MAG_ANGLE"])
    r.ask("MAG_ANGLE")
    M, N = m, n                                      # Input "MAGNITUDE=",M / "ANGLE (DEG)=",N
    if M < 0:                                        # If M<0 / Goto H6
        return r.message("H6")
    if M > BIG:                                      # If M>1ᴇ9 / Goto HA
        return r.message("HA")
    if abs(N) > 360:                                 # If abs(N)>360 / Goto H7
        return r.message("H7")
    str1, str2 = fmt3(M), fmt3(N)                    # Str1, Str2
    P = tf(M * trig_deg("cos", N))                   # M*cos(N)→P   (Degree mode)
    Q = tf(M * trig_deg("sin", N))                   # M*sin(N)→Q

    s = r.clrhome()                                  # STEP 1: X component
    s.disp("STEP 1  X COMPONENT")
    s.disp("ANGLE IS FROM +X, SO X IS")
    s.disp("THE ADJACENT SIDE (COS)-")
    s.disp("X=MAGNITUDE*COS(ANGLE)")
    s.zline("X=(" + str1 + ")COS(" + str2 + "°)")
    tail_x = str4 + fmt_sign_word(P, " (RIGHT)", " (LEFT)", E)
    s.val("X", P, tail_x)                            # Str3 = "X = ..."
    s.disp("(+X IS RIGHT, -X IS LEFT)")

    s = r.clrhome()                                  # STEP 2: Y component
    s.disp("STEP 2  Y COMPONENT")
    s.disp("ANGLE IS FROM +X, SO Y IS")
    s.disp("THE OPPOSITE SIDE (SIN)-")
    s.disp("Y=MAGNITUDE*SIN(ANGLE)")
    s.zline("Y=(" + str1 + ")SIN(" + str2 + "°)")
    tail_y = str4 + fmt_sign_word(Q, " (UP)", " (DOWN)", E)
    s.val("Y", Q, tail_y)                            # Str0 = "Y = ..."
    s.disp("(+Y IS UP, -Y IS DOWN)")

    s = r.clrhome()                                  # SUMMARY
    s.disp("SUMMARY  MAG,ANGLE TO X,Y")
    s.val("MAGNITUDE", M, str4)
    s.val("ANGLE", N, "°")
    s.disp("(COUNTERCLOCKWISE FROM +X)")
    s.val("X", P, tail_x)                            # Disp Str3
    s.val("Y", Q, tail_y)                            # Disp Str0
    r.results = dict(X=P, Y=Q)
    return r                                         # Goto H0


QUAD_LINE = {1: "QUADRANT I (X>0, Y>0)", 2: "QUADRANT II (X<0, Y>0)", 3: "QUADRANT III (X<0, Y<0)",
             4: "QUADRANT IV (X>0, Y<0)", 5: "ON THE +X AXIS (Y IS 0)", 6: "ON THE -X AXIS (Y IS 0)",
             7: "ON THE +Y AXIS (X IS 0)", 8: "ON THE -Y AXIS (X IS 0)"}
AXIS_RULE = {5: "+X IS 0°", 6: "-X IS 180°", 7: "+Y IS 90°", 8: "-Y IS 270°"}
AXIS_WORDS = {5: "ALONG +X (RIGHT)", 6: "ALONG -X (LEFT)", 7: "STRAIGHT UP (ALONG +Y)",
              8: "STRAIGHT DOWN (ALONG -Y)"}
QUAD_WORDS = {1: "° ABOVE +X", 2: "° ABOVE -X", 3: "° BELOW -X", 4: "° BELOW +X"}
QUAD_RULE = {1: "ANGLE=REF=", 2: "ANGLE=180-REF=180-", 3: "ANGLE=180+REF=180+", 4: "ANGLE=360-REF=360-"}


def r2p_theta(x, y):
    """R►Pθ( in Degree mode: angle of (x, y) in (-180, 180], stored with 14 digits."""
    return tf(math.degrees(math.atan2(y, x)))


def case_code(P, Q):
    """C = 1..4 quadrant I..IV, 5/6 on +X/-X, 7/8 on +Y/-Y (P, Q not both 0)."""
    C = None
    if P > 0 and Q > 0:
        C = 1
    if P < 0 and Q > 0:
        C = 2
    if P < 0 and Q < 0:
        C = 3
    if P > 0 and Q < 0:
        C = 4
    if P > 0 and Q == 0:
        C = 5
    if P < 0 and Q == 0:
        C = 6
    if P == 0 and Q > 0:
        C = 7
    if P == 0 and Q < 0:
        C = 8
    return C


def vector_xy(unit, p, q):
    """Menu VECTOR COMPONENTS 2 (X,Y TO MAG+ANGLE)."""
    r = Result()
    str4 = UNITS[unit]
    r.info = list(INFO["XY"])
    r.ask("XY")
    P, Q = p, q                                      # Input "X COMPONENT=",P / "Y COMPONENT=",Q
    if max(abs(P), abs(Q)) > BIG:                    # If max(abs(P),abs(Q))>1ᴇ9 / Goto H8
        return r.message("H8")
    if P == 0 and Q == 0:                            # If P=0 and Q=0 / Goto H9: zero vector
        r.messages.append("H9")
        s = r.clrhome()
        s.disp("ZERO VECTOR")
        s.disp("X AND Y ARE BOTH 0, SO")
        s.val("MAGNITUDE", "0", str4)                # Disp "MAGNITUDE = 0"+Str4
        s.disp("A ZERO VECTOR POINTS NO")
        s.disp("WAY, SO ITS ANGLE IS")
        s.disp("UNDEFINED.")
        return r
    str1, str2 = fmt3(P), fmt3(Q)
    M = tf(math.sqrt(tf(tf(P * P) + tf(Q * Q))))     # √(P²+Q²)→M   (Pythagoras)

    s = r.clrhome()                                  # STEP 1: magnitude
    s.disp("STEP 1  MAGNITUDE")
    s.disp("X AND Y ARE PERPENDICULAR,")
    s.disp("SO USE PYTHAGORAS-")
    s.disp("MAGNITUDE=√(X²+Y²)")
    s.zline("=√((" + str1 + ")²+(" + str2 + ")²)")
    str3 = fmt3(M)
    s.val("MAGNITUDE", M, str4)

    B = r2p_theta(abs(P), abs(Q))                    # R►Pθ(abs(P),abs(Q))→B   reference angle 0..90
    A = r2p_theta(P, Q)                              # R►Pθ(P,Q)→A
    if A < 0:                                        # If A<0 / A+360→A   (0..360)
        A = tf(A + 360)

    s = r.clrhome()                                  # STEP 2: reference angle
    s.disp("STEP 2  REFERENCE ANGLE")
    s.disp("ANGLE BETWEEN THE VECTOR")
    s.disp("AND THE X AXIS (0 TO 90)-")
    s.disp("REF=TAN⁻1(|Y|/|X|)")
    line = "=TAN⁻1(" + fmt3(abs(Q)) + "/" + fmt3(abs(P)) + ")"
    if P == 0:                                       # If P=0: "X IS 0, SO REF IS 90°"→Str0
        line = "X IS 0, SO REF IS 90°"
    s.zline(line)
    s.val("REF ANGLE", B, "°")

    C = case_code(P, Q)                              # 1→C ... 8→C
    ref = fmt3(B)                                    # B→Z, ZFMT
    words = (ref + QUAD_WORDS[C]) if C <= 4 else AXIS_WORDS[C]      # → Str2
    rule = (QUAD_RULE[C] + ref) if C <= 4 else AXIS_RULE[C]         # → Str0

    s = r.clrhome()                                  # STEP 3: angle from +X
    s.disp("STEP 3  ANGLE FROM +X")
    s.disp("MEASURED COUNTERCLOCKWISE")
    s.disp("FROM +X (0 TO 360)-")
    s.disp(QUAD_LINE[C])                             # Disp Str1
    s.zline(rule)                                    # prgmZLINE
    s.val("ANGLE", A, "°")
    if A > 180:                                      # If A>180: Disp "OR "+(A-360)+"° (CLOCKWISE)"
        s.disp("OR " + fmt3(tf(A - 360)) + "° (CLOCKWISE)")
    s.disp(words)                                    # Disp Str2

    s = r.clrhome()                                  # SUMMARY
    s.disp("SUMMARY  X,Y TO MAG,ANGLE")
    s.val("X", P, str4)
    s.val("Y", Q, str4)
    s.val("MAGNITUDE", M, str4)                      # Str3
    s.val("ANGLE", A, "°")
    s.disp("(CCW FROM +X, 0 TO 360)")
    if A > 180:
        s.disp("OR " + fmt3(tf(A - 360)) + "° (CLOCKWISE)")
    s.disp(words)
    r.results = dict(MAG=M, REF=B, ANGLE=A, CASE=C, WORDS=words, MAG_STR=str3)
    return r                                         # Goto H0


# ============================================================================= I. averages
def averages(n, legs=()):
    """Menu choice AVG SPEED/VELOCITY. n = NUMBER OF LEGS typed; legs = [(distance, dir, time), ...]
    as typed (only the legs the program actually asks for are used)."""
    r = Result()
    r.info = list(INFO["AVG"])
    r.ask("LEGS")
    N = num(n)                                       # Input "NUMBER OF LEGS=",N
    if N < 1 or N > 4 or N != N.to_integral_value(ROUND_DOWN):   # If N<1 or N>4 or fPart(N)≠0
        return r.message("I2")                       # Goto I2
    N = int(N)
    P = Q = D = Decimal(0)                           # 0→P (distance), 0→Q (displacement), 0→D (time)
    str1 = str2 = str3 = None
    for I in range(1, N + 1):                        # Lbl I1 ... I+1→I / If I≤N / Goto I1
        r.leg_info.append([f"LEG {I} OF {N}"] + list(INFO["LEG"]))
        r.ask("LEG")
        A, B, C = (num(v) for v in legs[I - 1])      # Input distance A, direction B, time C
        if A < 0:                                    # If A<0 / Goto I3
            return r.message("I3")
        if B != 1 and B != -1:                       # If B≠1 and B≠⁻1 / Goto I4
            return r.message("I4")
        if C < 0:                                    # If C<0 / Goto I5
            return r.message("I5")
        if A > BIGD or C > BIGD:                     # If A>1ᴇ9 or C>1ᴇ9 / Goto I6
            return r.message("I6")
        P = ti(P + A)                                # P+A→P
        Q = ti(Q + ti(B * A))                        # Q+B*A→Q
        D = ti(D + C)                                # D+C→D
        a = fmt3(A)
        str1 = a if I == 1 else str1 + "+" + a       # "100+50.0"
        if B == 1 and I > 1:
            a = "+" + a
        if B == -1:
            a = "-" + a
        str2 = a if I == 1 else str2 + a             # "100-50.0"
        c = fmt3(C)
        str3 = c if I == 1 else str3 + "+" + c       # "10.0+5.00"
    if D < TINYD:                                    # If D<1ᴇ⁻9 / Goto I7
        return r.message("I7")
    E = div(P, D)                                    # P/D→E   average speed
    F = div(Q, D)                                    # Q/D→F   average velocity

    def direction(s):
        if Q >= TINYD:
            s.disp("(IN THE + DIRECTION)")
        if Q <= -TINYD:
            s.disp("(IN THE - DIRECTION)")
        if abs(Q) < TINYD:
            s.disp("(ENDS WHERE IT STARTED)")

    s = r.clrhome()                                  # STEP 1: total distance
    s.disp("STEP 1  TOTAL DISTANCE")
    s.disp("ADD EVERY LEG AS POSITIVE")
    s.disp("(DIRECTION DOES NOT")
    s.disp("MATTER FOR DISTANCE)-")
    s.zline("=" + str1)
    s.val("DISTANCE", P, " M")

    s = r.clrhome()                                  # STEP 2: displacement
    s.disp("STEP 2  DISPLACEMENT")
    s.disp("ADD THE LEGS WITH THEIR")
    s.disp("SIGNS (- LEGS SUBTRACT)-")
    s.zline("S=" + str2)
    s.val("DISPLACEMENT", Q, " M")
    direction(s)

    s = r.clrhome()                                  # STEP 3: total time
    s.disp("STEP 3  TOTAL TIME")
    s.disp("ADD THE TIMES OF ALL LEGS-")
    s.zline("=" + str3)
    s.val("TOTAL TIME", D, " S")

    s = r.clrhome()                                  # STEP 4: average speed
    s.disp("STEP 4  AVERAGE SPEED")
    s.disp("AVG SPEED=DISTANCE/TIME")
    s.disp("=" + fmt3(P) + "/" + fmt3(D))
    s.val("AVG SPEED", E, " M/S")
    s.disp("(SPEED HAS NO DIRECTION,")
    s.disp("SO IT IS NEVER NEGATIVE)")

    s = r.clrhome()                                  # STEP 5: average velocity
    s.disp("STEP 5  AVERAGE VELOCITY")
    s.disp("AVG VEL=DISPLACEMENT/TIME")
    s.disp("=" + fmt3(Q) + "/" + fmt3(D))
    s.val("AVG VEL", F, " M/S")
    direction(s)

    s = r.clrhome()                                  # SUMMARY
    s.disp("SUMMARY  AVERAGES")
    s.val("DISTANCE", P, " M")
    s.val("DISPLACEMENT", Q, " M")
    s.val("TOTAL TIME", D, " S")
    s.val("AVG SPEED", E, " M/S")
    s.val("AVG VEL", F, " M/S")
    direction(s)
    r.results = dict(DISTANCE=P, DISPLACEMENT=Q, TIME=D, AVG_SPEED=E, AVG_VEL=F)
    return r                                         # Return (to PHYSOLVE page 2)


# ============================================================================= J. factor of change
# relationship -> (Str1 quantity, Str2 unit, Str3 what changes, F power)
RELATIONS = {
    1: ("S", " M", "V", 2),        # S PROP TO V²   (stopping distance / max height, same a)
    2: ("S", " M", "T", 2),        # S PROP TO T²   (from rest, same a)
    3: ("T", " S", "H", 0.5),      # T PROP TO √(H) (fall time)
    4: ("V", " M/S", "H", 0.5),    # V PROP TO √(H) (impact speed of a drop)
    5: ("V", " M/S", "T", 1),      # V PROP TO T    (from rest)
}


def factor(rel, old, k):
    """Menu FACTOR OF CHANGE option rel (1..5): old value L and factor K."""
    r = Result()
    r.info = list(INFO[f"J{rel}"])
    r.ask(f"J{rel}")
    L, M = num(old), num(k)                          # Input "OLD ...=",L / "... FACTOR K=",M
    if rel == 3 and L < 0:                           # J3 only: If L<0 / Goto J8
        return r.message("J8")
    str1, str2, str3, F = RELATIONS[rel]
    if M < 0:                                        # Lbl J9: If M<0 / Goto J6
        return r.message("J6")
    if abs(L) > BIGD or M > BIGD:                    # If abs(L)>1ᴇ9 or M>1ᴇ9 / Goto J7
        return r.message("J7")
    if F == 2:
        G = ti(M * M)                                # M²→G
    elif F == 1:
        G = M                                        # M→G
    else:
        G = ti(M.sqrt(_TI))                          # √(M)→G
    H = ti(L * G)                                    # L*G→H   new = old * multiplier
    str4 = {2: "K²", 1: "K", 0.5: "√(K)"}[F]
    k_str = fmt3(M)
    sub = {2: "=(" + k_str + ")²", 1: "=" + k_str, 0.5: "=√(" + k_str + ")"}[F]

    s = r.clrhome()                                  # STEP 1: multiplier
    s.disp("STEP 1  MULTIPLIER")
    s.disp(str3 + " IS MULTIPLIED BY K, SO")
    s.disp(str1 + " IS MULTIPLIED BY " + str4)
    s.disp("MULTIPLIER=" + str4)
    s.disp(sub)
    s.val("MULTIPLIER", G)

    s = r.clrhome()                                  # STEP 2: new value
    s.disp("STEP 2  NEW " + str1)
    s.disp("NEW " + str1 + "=OLD " + str1 + "*" + str4)
    s.zline("NEW " + str1 + "=(" + fmt3(L) + ")(" + fmt3(G) + ")")
    s.val("NEW " + str1, H, str2)

    s = r.clrhome()                                  # SUMMARY
    s.disp("SUMMARY  FACTOR OF CHANGE")
    s.disp(str1 + " PROP TO " + {2: str3 + "²", 1: str3, 0.5: "√(" + str3 + ")"}[F])
    s.val("OLD " + str1, L, str2)
    s.val(str3 + " FACTOR K", M)
    s.val("MULTIPLIER", G)
    s.val("NEW " + str1, H, str2)
    s.zline(fmt3(M) + "X " + str3 + " GIVES " + fmt3(G) + "X " + str1)
    r.results = dict(MULT=G, NEW=H)
    return r                                         # Goto J0


# ============================================================================= K. lab tools
def ramp(slope):
    """LAB TOOLS 1: a = 2 * slope of the s vs t² graph."""
    r = Result()
    r.info = list(INFO["RAMP"])
    r.ask("RAMP")
    M = num(slope)                                   # Input "SLOPE (M/S²)=",M
    if abs(M) > BIGD:                                # If abs(M)>1ᴇ9 / Goto K6
        return r.message("K6")
    A = ti(2 * M)                                    # 2*M→A
    s = r.clrhome()
    s.disp("STEP 1  ACCELERATION")
    s.disp("S=(1/2)AT² IS A LINE")
    s.disp("Y=(SLOPE)X WITH Y=S AND")
    s.disp("X=T², SO SLOPE=A/2 AND")
    s.disp("A=2*SLOPE")
    s.disp("A=2(" + fmt3(M) + ")")
    s.val("A", A, " M/S²")
    s = r.clrhome()
    s.disp("SUMMARY  RAMP")
    s.val("SLOPE", M, " M/S²")
    s.val("A", A, " M/S²")
    s.disp("(ALONG THE RAMP)")
    r.results = dict(A=A)
    return r


def pct_diff(a, b):
    """LAB TOOLS 2: |A-B| / |(A+B)/2| * 100."""
    r = Result()
    r.info = list(INFO["PDIFF"])
    r.ask("PDIFF")
    A, B = num(a), num(b)                            # Input "VALUE A=",A / "VALUE B=",B
    if max(abs(A), abs(B)) > BIGD:                   # If max(abs(A),abs(B))>1ᴇ9 / Goto K6
        return r.message("K6")
    C = div(ti(A + B), 2)                            # (A+B)/2→C
    if C == 0:                                       # If C=0 / Goto K7
        return r.message("K7")
    D = abs(ti(A - B))                               # abs(A-B)→D
    E = div(ti(100 * D), abs(C))                     # 100*D/abs(C)→E
    str1 = fmt3(A)
    str2 = fmt3(B)
    if B < 0:
        str2 = "(" + str2 + ")"
    s = r.clrhome()                                  # STEP 1: average
    s.disp("STEP 1  AVERAGE")
    s.disp("AVG=(A+B)/2")
    s.zline("AVG=(" + str1 + "+" + str2 + ")/2")
    s.val("AVG", C)
    str3 = fmt3(abs(ti(A + B)))                      # abs(A+B)→Z: |AVG| is shown as (|A+B|/2) so
    s = r.clrhome()                                  # the numbers on screen give the result shown
    s.disp("STEP 2  PERCENT DIFFERENCE")             # (2.10, 1.95: 0.150/(4.05/2)*100 = 7.41)
    s.disp("%DIFF=|A-B|/|AVG|*100")
    s.disp("=|A-B|/(|A+B|/2)*100")
    s.zline("=|" + str1 + "-" + str2 + "|/(" + str3 + "/2)*100")
    s.zline("=" + fmt3(D) + "/(" + str3 + "/2)*100")
    s.val("PERCENT DIFF", E, " %")
    s.disp("(UNROUNDED VALUES USED)")
    s = r.clrhome()                                  # SUMMARY
    s.disp("SUMMARY  PERCENT DIFF")
    s.val("VALUE A", A)
    s.val("VALUE B", B)
    s.val("AVG", C)
    s.val("PERCENT DIFF", E, " %")
    r.results = dict(AVG=C, DIFF=D, PCT=E)
    return r


def pct_error(exp, acc):
    """LAB TOOLS 3: |ACC-EXP| / |ACC| * 100."""
    r = Result()
    r.info = list(INFO["PERR"])
    r.ask("PERR")
    A, B = num(exp), num(acc)                        # Input "EXPERIMENTAL=",A / "ACCEPTED=",B
    if max(abs(A), abs(B)) > BIGD:                   # If max(abs(A),abs(B))>1ᴇ9 / Goto K6
        return r.message("K6")
    if B == 0:                                       # If B=0 / Goto K8
        return r.message("K8")
    if abs(ti(A - B)) > ti(Decimal("1E80") * abs(B)):   # If abs(A-B)>1ᴇ80*abs(B) / Goto K8
        return r.message("K8")
    D = abs(ti(A - B))                               # abs(A-B)→D
    E = div(ti(100 * D), abs(B))                     # 100*D/abs(B)→E
    str1 = fmt3(A)
    str2 = "(" + str1 + ")" if A < 0 else str1       # EXP in parentheses when negative
    str3 = fmt3(abs(B))
    s = r.clrhome()                                  # STEP 1: percent error
    s.disp("STEP 1  PERCENT ERROR")
    s.disp("%ERROR=|ACC-EXP|/|ACC|*100")
    s.zline("=|" + fmt3(B) + "-" + str2 + "|/" + str3 + "*100")
    s.zline("=" + fmt3(D) + "/" + str3 + "*100")
    s.val("PERCENT ERROR", E, " %", wrap=True)
    s.disp("(UNROUNDED VALUES USED)")
    s = r.clrhome()                                  # SUMMARY
    s.disp("SUMMARY  PERCENT ERROR")
    s.val("EXPERIMENTAL", A)
    s.val("ACCEPTED", B)
    s.val("PERCENT ERROR", E, " %", wrap=True)
    r.results = dict(DIFF=D, PCT=E)
    return r


def yd_to_m(yd):
    """LAB TOOLS 4 -> YARDS AND METERS 1 (YARDS TO METERS): m = yd / 1.0936."""
    r = Result()
    r.info = list(INFO["YD2M"])
    r.ask("YD2M")
    A = num(yd)                                      # Input "YARDS=",A
    if abs(A) > BIGD:                                # If abs(A)>1ᴇ9 / Goto K6
        return r.message("K6")
    B = div(A, Decimal("1.0936"))                    # A/1.0936→B
    str1, str2 = fmt3(A), fmt3(B)
    s = r.clrhome()
    s.disp("STEP 1  YARDS TO METERS")
    s.disp("METERS=YARDS/1.0936")
    s.disp("METERS=" + str1 + "/1.0936")
    s.val("METERS", B, " M")
    s = r.clrhome()
    s.disp("SUMMARY  YD TO M")
    s.val("YARDS", A, " YD")
    s.val("METERS", B, " M")
    r.results = dict(OUT=B)
    return r


def m_to_yd(m):
    """LAB TOOLS 4 -> YARDS AND METERS 2 (METERS TO YARDS): yd = m * 1.0936."""
    r = Result()
    r.info = list(INFO["M2YD"])
    r.ask("M2YD")
    A = num(m)                                       # Input "METERS=",A
    if abs(A) > BIGD:                                # If abs(A)>1ᴇ9 / Goto K6
        return r.message("K6")
    B = ti(Decimal("1.0936") * A)                    # 1.0936*A→B
    str1, str2 = fmt3(A), fmt3(B)
    s = r.clrhome()
    s.disp("STEP 1  METERS TO YARDS")
    s.disp("YARDS=METERS*1.0936")
    s.disp("YARDS=" + str1 + "*1.0936")
    s.val("YARDS", B, " YD")
    s = r.clrhome()
    s.disp("SUMMARY  M TO YD")
    s.val("METERS", A, " M")
    s.val("YARDS", B, " YD")
    r.results = dict(OUT=B)
    return r


def kmh_to_ms(v):
    """LAB TOOLS 5 -> SPEED TO M/S 1 (KM/H TO M/S): m/s = (km/h) / 3.6."""
    r = Result()
    r.info = list(INFO["KMH"])
    r.ask("KMH")
    A = num(v)                                       # Input "KM/H=",A
    if abs(A) > BIGD:                                # If abs(A)>1ᴇ9 / Goto K6 (ZFMT needs |x| < 9.995E99)
        return r.message("K6")
    B = div(A, Decimal("3.6"))                       # A/3.6→B
    s = r.clrhome()
    s.disp("STEP 1  KM/H TO M/S")
    s.disp("M/S=(KM/H)/3.6")
    s.disp("M/S=" + fmt3(A) + "/3.6")
    s.val("SPEED", B, " M/S")
    s = r.clrhome()
    s.disp("SUMMARY  KM/H TO M/S")
    s.val("SPEED", A, " KM/H")
    s.val("SPEED", B, " M/S")
    r.results = dict(OUT=B)
    return r


def mph_to_ms(v):
    """LAB TOOLS 5 -> SPEED TO M/S 2 (MPH TO M/S): m/s = mph * 0.44704."""
    r = Result()
    r.info = list(INFO["MPH"])
    r.ask("MPH")
    A = num(v)                                       # Input "MPH=",A
    if abs(A) > BIGD:                                # If abs(A)>1ᴇ9 / Goto K6
        return r.message("K6")
    B = ti(Decimal("0.44704") * A)                   # 0.44704*A→B
    s = r.clrhome()
    s.disp("STEP 1  MPH TO M/S")
    s.disp("M/S=MPH*0.44704")
    s.disp("M/S=" + fmt3(A) + "*0.44704")
    s.val("SPEED", B, " M/S")
    s = r.clrhome()
    s.disp("SUMMARY  MPH TO M/S")
    s.val("SPEED", A, " MPH")
    s.val("SPEED", B, " M/S")
    r.results = dict(OUT=B)
    return r
