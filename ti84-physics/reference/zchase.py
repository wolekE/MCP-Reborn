"""
Reference implementation of prgmZCHASE (PHYSOLVE page 2, option 2: CHASE PROBLEM), mirroring
src/ZCHASE.txt line for line: the same input checks in the same order, the same equations, the
same branches, and the same screens and messages (every row is rebuilt here, including the rows
prgmZQUAD writes, so the tests can compare whole screens).

Physics (class facts): set both positions equal. Time 0 is when car 1 passes car 2 (D0 = 0) or
is D0 ahead of it. Car 1: X1 = D0 + V1*T. Car 2 waits TD seconds, then starts from rest:
X2 = (1/2)A(T-TD)^2 for T >= TD. With U = T - TD (time since car 2 started), X1 = X2 gives
    (1/2)A U^2 - V1 U - (D0 + V1*TD) = 0
solved by prgmZQUAD with L = A/2, M = -V1, N = -(D0+V1*TD) (ZQUAD calls the unknown T; here it
is U). The product of the roots is N/L <= 0, so the larger root I is the physical one and the
smaller root is negative (before car 2 starts) or 0 (the side-by-side start when D0 = TD = 0).
Then T = U + TD, S = (1/2)A U^2, V2 = A U, and V2/V1 (= 2 for a side-by-side start, since
U = 2 V1/A; more than 2 with any lead).

TI variables (the same letters are used below):
    V = V1 (typed)   B = D0 (typed)   A = A (typed)   C = TD (typed)
    Q = lead of car 1 when car 2 starts = D0 + V1*TD
    L, M, N -> prgmZQUAD;  J, H, I, G <- prgmZQUAD (roots H <= I, discriminant G)
    D = U = I (catch-up time after car 2 starts)     E = T = U + TD (after time 0)
    S = (1/2)A U^2 (distance car 2 travels)            F = V2 = A U (car 2 speed)
    P = V2/V1 (only when V1 > 0)
    Str1 = fmt3(V1), Str2 = fmt3(D0) then fmt3(U), Str3 = fmt3(TD), Str4 = fmt3(A)

run(v1, d0, a, td) returns a Result whose .screens list has one Screen per Pause screen
(title, values [(name, value, unit)] for every "NAME = VALUE UNIT" row, rows = exact text).
Result.messages lists the message labels shown (E1..E7).
"""
import math

from common import fmt3

COLS = 26
BIG = 1e9        # inputs above this are rejected (E4)
SMALL = 1e-6     # nonzero V1, D0, TD and A below this are rejected (E5): keeps every
                 # number ZQUAD shows (L = A/2 too) above ZFMT's 1E-9 zero cutoff, and far from overflow

MESSAGES = {
    "E1": ("V1 CANNOT BE NEGATIVE.",            # V1 < 0
           "ENTER CAR 1 SPEED AS A",
           "POSITIVE NUMBER (0 IF IT",
           "IS PARKED). BOTH CARS GO",
           "THE SAME WAY."),
    "E2": ("D0 CANNOT BE NEGATIVE.",            # D0 < 0
           "D0 IS HOW FAR CAR 1 IS",
           "AHEAD OF CAR 2 AT TIME 0",
           "(0 IF IT JUST PASSES)."),
    "E3": ("TD CANNOT BE NEGATIVE.",            # TD < 0
           "TD IS HOW LONG CAR 2 WAITS",
           "AFTER TIME 0 BEFORE IT",
           "STARTS (0 IF NO DELAY)."),
    "E4": ("THAT NUMBER IS TOO LARGE.",         # an input above 1E9
           "KEEP EVERY NUMBER AT OR",
           "BELOW 1E9 (1 BILLION)."),
    "E5": ("A NUMBER IS TOO SMALL.",            # 0 < V1, D0 or TD < 1E-6, or A < 1E-6
           "USE 0 OR AT LEAST 1E-6 FOR",
           "V1, D0 AND TD, AND AT",
           "LEAST 1E-6 FOR A."),
    "E6": ("CAR 1 IS PARKED (V1 IS 0)",         # V1 = 0 and D0 = 0: already together
           "RIGHT AT CAR 2 START (D0",
           "IS 0), SO THEY ARE ALREADY",
           "TOGETHER AT TIME 0- THE",
           "CATCH-UP TIME IS 0 S."),
    "E7": ("A MUST BE MORE THAN 0.",            # A <= 0: car 2 never moves forward
           "CAR 2 STARTS FROM REST, SO",
           "WITH A OF 0 OR LESS IT",
           "NEVER MOVES FORWARD AND",
           "NEVER CATCHES CAR 1."),
}

INFO_ROWS = ("CHASE PROBLEM",
             "CAR 1- CONSTANT SPEED V1.",
             "CAR 2- STARTS FROM REST",
             "WITH ACCELERATION A.",
             "TIME 0- CAR 1 IS D0 AHEAD",
             "OF CAR 2 (0 IF IT PASSES).",
             "CAR 2 WAITS TD SECONDS",
             "AFTER TIME 0 (0 IF NONE).",
             "BOTH GO THE SAME WAY.")
INPUT_ROWS = ("CHASE- ENTER EACH VALUE",
              "V1- CAR 1 SPEED",
              "D0- CAR 1 LEAD AT TIME 0",
              "A- CAR 2 ACCELERATION",
              "TD- CAR 2 WAIT (DELAY)")
PROMPTS = ("V1 (M/S)=", "D0 (M)=", "A (M/S²)=", "TD (S)=")


class Screen:
    def __init__(self):
        self.rows = []
        self.values = []

    @property
    def title(self):
        return self.rows[0] if self.rows else ""

    def disp(self, text):
        assert len(text) <= COLS, f"row longer than {COLS}: {text!r}"
        self.rows.append(text)

    def zline(self, text):
        for k in range(0, len(text), COLS):
            self.rows.append(text[k:k + COLS])

    def val(self, name, x, unit):
        shown = x if isinstance(x, str) else fmt3(x)
        self.disp(f"{name} = {shown} {unit}" if unit else f"{name} = {shown}")
        self.values.append((name, x, unit))

    def __repr__(self):
        return f"Screen({self.rows!r})"


class Result:
    def __init__(self):
        self.screens = []
        self.messages = []
        self.results = {}

    def clrhome(self):
        s = Screen()
        self.screens.append(s)
        return s

    def message(self, label):
        self.messages.append(label)
        s = self.clrhome()
        for row in MESSAGES[label]:
            s.disp(row)
        return self

    @property
    def summary(self):
        """{name: value} of the SUMMARY (CHASE) screen."""
        for s in self.screens:
            if s.title == "SUMMARY (CHASE)":
                return {n: v for n, v, u in s.values}
        return {}


def zquad(s, l, m, n):
    """Mirror of prgmZQUAD for L*T^2 + M*T + N = 0: ClrHome is done by the caller (s is the new
    screen); writes ZQUAD's rows to s and returns (J, H, I, G)."""
    s.disp("SOLVE QUADRATIC FOR T")
    str0 = fmt3(l) + "T²"
    str9 = fmt3(m)
    if m >= 0:
        str9 = "+" + str9
    str0 = str0 + str9 + "T"
    str9 = fmt3(n)
    if n >= 0:
        str9 = "+" + str9
    str0 = str0 + str9 + "=0"
    s.zline(str0)
    if l == 0:
        s.disp("NO T² TERM, SO LINEAR")
        if m == 0:
            s.disp("NO SOLUTION FOR T")
            return 0, None, None, None
        h = -n / m
        s.val("T", h, "S")
        return 1, h, h, None
    g = m ** 2 - 4 * l * n
    if abs(g) < 1e-10 * (m ** 2 + abs(4 * l * n)):
        g = 0.0
    s.disp("T=(-B+/-√(B²-4AC))/(2A)")
    s.val("B²-4AC", g, "")
    if g < 0:
        s.disp("B²-4AC<0 SO NO REAL ROOT")
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
    s.val("T1", h, "S")
    s.val("T2", i, "S")
    return 2, h, i, g


def run(v1, d0, a, td):
    """v1, d0, a, td: the four numbers typed at the input screen."""
    r = Result()
    s = r.clrhome()                                  # info screen, Pause
    for row in INFO_ROWS:
        s.disp(row)
    V, B, A, C = v1, d0, a, td                       # Input V1->V, D0->B, A->A, TD->C
    if V < 0:                                        # If V<0 / Goto E1
        return r.message("E1")
    if B < 0:                                        # If B<0 / Goto E2
        return r.message("E2")
    if C < 0:                                        # If C<0 / Goto E3
        return r.message("E3")
    if max(max(V, B), max(A, C)) > BIG:              # Goto E4
        return r.message("E4")
    if V == 0 and B == 0:                            # If V=0 and B=0 / Goto E6
        return r.message("E6")
    if A <= 0:                                       # If A≤0 / Goto E7
        return r.message("E7")
    if (0 < V < SMALL) or (0 < B < SMALL) or (0 < C < SMALL) or A < SMALL:
        return r.message("E5")                       # Goto E5
    Q = B + V * C                                    # B+VC→Q   (lead when car 2 starts)
    L = A / 2                                        # A/2→L
    M = -V                                           # ⁻V→M
    N = -Q                                           # ⁻Q→N

    s = r.clrhome()                                  # STEP 1: set X1 = X2 (all text)
    for row in ("STEP 1  SET X1=X2",
                "T FROM TIME 0, X FROM THE",
                "START POINT OF CAR 2.",
                "CAR 1- X1=D0+V1*T",
                "CAR 2- X2=(1/2)A(T-TD)²",
                "LET U=T-TD (TIME SINCE",
                "CAR 2 STARTED), T=U+TD.",
                "X1=X2 GIVES",
                "D0+V1(U+TD)=(1/2)AU²",
                "(1/2)AU²-V1*U-(D0+V1*TD)=0"):
        s.disp(row)

    str1, str2, str3, str4 = fmt3(V), fmt3(B), fmt3(C), fmt3(A)
    s = r.clrhome()                                  # STEP 2: the numbers
    s.disp("STEP 2  PUT IN NUMBERS")
    s.disp("LEAD OF CAR 1 WHEN CAR 2")
    s.disp("STARTS IS D0+V1*TD-")
    s.zline("LEAD=" + str2 + "+(" + str1 + ")(" + str3 + ")")
    s.val("LEAD", Q, "M")
    s.zline("(1/2)(" + str4 + ")U²-" + str1 + "U-" + fmt3(Q) + "=0")
    s.disp("ON THE NEXT SCREEN T IS U")
    s.disp("(TIME AFTER CAR 2 STARTS).")

    s = r.clrhome()                                  # prgmZQUAD (its ClrHome) + 3 rows, Pause
    J, H, I, G = zquad(s, L, M, N)
    D = I                                            # I→D
    str2 = fmt3(D)                                   # D -> ZFMT -> Str2
    if B == 0 and C == 0:                            # If B=0 and C=0
        s.disp("T1 IS 0, THE START (SIDE")
        s.disp("BY SIDE), NOT A CATCH-UP.")
    else:
        s.disp("T1<0 IS BEFORE CAR 2")
        s.disp("STARTS- NOT PHYSICAL.")
    s.val("SO U", D, "S")

    E = D + C                                        # D+C→E   (T = U + TD)
    s = r.clrhome()                                  # STEP 3: catch-up time
    s.disp("STEP 3  CATCH-UP TIME")
    if C > 0:
        s.disp("AFTER CAR 2 STARTS-")
        s.val("U", D, "S")
        s.disp("AFTER TIME 0 (CAR 2")
        s.disp("WAITED TD)- T=U+TD")
        s.disp("T=" + str2 + "+" + str3)
        s.val("T", E, "S")
    else:
        s.disp("TD IS 0, SO CAR 2 STARTS")
        s.disp("AT TIME 0 AND T=U.")
        s.val("T", D, "S")

    S = A * D ** 2 / 2                               # AD²/2→S
    s = r.clrhome()                                  # STEP 4: distance
    s.disp("STEP 4  DISTANCE")
    s.disp("CAR 2 SPEEDS UP FROM REST")
    s.disp("FOR U SECONDS-")
    s.disp("S=(1/2)AU²")
    s.zline("S=(1/2)(" + str4 + ")(" + str2 + ")²")
    s.val("S", S, "M")
    s.disp("(FROM CAR 2 START POINT)")
    s.disp("CHECK- CAR 1 X1=D0+V1*T")
    X1 = B + V * E                                   # B+VE→Z
    s.val("X1", X1, "M")

    F = A * D                                        # AD→F
    P = None
    s = r.clrhome()                                  # STEP 5: car 2 speed and the ratio
    s.disp("STEP 5  CAR 2 SPEED")
    s.disp("VF=V0+AT WITH V0 IS 0,")
    s.disp("SO V2=AU")
    s.disp("V2=(" + str4 + ")(" + str2 + ")")
    s.val("V2", F, "M/S")
    if V > 0:
        P = F / V                                    # F/V→P
        s.disp("V2/V1=" + fmt3(F) + "/" + str1)
        s.val("V2/V1", P, "")
        if B == 0 and C == 0:
            s.disp("RULE- FROM REST, SIDE BY")
            s.disp("SIDE, IT CATCHES UP AT 2X")
            s.disp("THE SPEED OF CAR 1.")
        else:
            s.disp("THE 2X RULE IS ONLY FOR A")
            s.disp("SIDE BY SIDE START. WITH A")
            s.disp("LEAD IT IS MORE THAN 2X.")
    else:
        s.disp("CAR 1 IS PARKED (V1 IS 0)")
        s.disp("SO THERE IS NO SPEED")
        s.disp("RATIO.")

    s = r.clrhome()                                  # SUMMARY
    s.disp("SUMMARY (CHASE)")
    if C > 0:
        s.val("U", D, "S")
        s.disp("(AFTER CAR 2 STARTS)")
        s.val("T", E, "S")
        s.disp("(AFTER TIME 0)")
    else:
        s.val("T", D, "S")
        s.disp("(CATCH-UP TIME)")
    s.val("S", S, "M")
    s.disp("(FROM CAR 2 START POINT)")
    s.val("V2", F, "M/S")
    if V > 0:
        s.val("V2/V1", P, "")
    r.results = dict(LEAD=Q, J=J, T1=H, T2=I, DISC=G, U=D, T=E, S=S, X1=X1, V2=F, RATIO=P)
    return r                                         # Return (back to PHYSOLVE page 2)
