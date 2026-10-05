"""
Reference implementation of prgmZRIVER (PHYSOLVE page 2, option 1: RIVER CROSSING), mirroring
src/ZRIVER.txt line for line: the same input checks in the same order, the same equations, the
same branches, and the same screens and messages (every row is rebuilt here, so the tests can
compare whole screens).

Class facts used: the across and downstream motions are independent; crossing time =
width / (boat speed across); drift = VR * t; resultant speed = sqrt(VB^2 + VR^2) (perpendicular
velocities); path angle = tan^-1(VR/VB); the heading (where the boat points) is not the path;
to land directly across aim upstream at sin^-1(VR/VB).

TI variables (the same letters are used below):
    B = VB  boat speed relative to the water (typed)     C = VR  river speed (typed)
    E = W   river width (typed)
    D = T   crossing time, boat aimed straight across = W/VB
    S = drift downstream = VR*T
    V = resultant speed = sqrt(VB^2+VR^2)
    A = path angle measured from straight across = tan^-1(VR/VB)   (degrees)
    P = path angle measured from the bank = 90 - A
    F = upstream heading measured from straight across = sin^-1(VR/VB)   (only when VR < VB)
    Q = across speed when aimed upstream = sqrt((VB-VR)(VB+VR))  (= sqrt(VB^2-VR^2) = VB cos F)
    G = crossing time when aimed upstream = W/Q
    Str1..Str4 = ZFMT of VB, VR, W, T

run(vb, vr, w) returns a Result whose .screens list has one Screen per Pause screen:
    Screen.title  = first row
    Screen.values = [(name, value, unit)] for each "NAME = VALUE UNIT" row, in screen order;
                    value is a number (the tests format it with fmt3, like prgmZFMT) or a
                    literal string the program prints as text (e.g. the "0" of "DRIFT = 0 M")
    Screen.rows   = every row the program writes on that screen (exact text)
Result.messages lists the message labels shown (E1..E5 = bad input, N1 = cannot land across).
"""
import math

from common import fmt3

COLS = 26
BIG = 1e9        # inputs above this are rejected (E4)
SMALL = 1e-9     # VB below this is rejected (E5): keeps W/VB and W/sqrt(VB^2-VR^2) far from overflow

# Message screens (label -> rows), exactly as the TI program displays them.
MESSAGES = {
    "E1": ("VB MUST BE MORE THAN 0.",           # VB <= 0
           "ENTER THE BOAT SPEED (IN",
           "STILL WATER) AS A POSITIVE",
           "NUMBER. A BOAT THAT DOES",
           "NOT MOVE NEVER CROSSES."),
    "E2": ("VR CANNOT BE NEGATIVE.",            # VR < 0
           "ENTER THE RIVER SPEED AS A",
           "POSITIVE NUMBER (0 FOR",
           "STILL WATER). ITS",
           "DIRECTION IS CALLED",
           "DOWNSTREAM."),
    "E3": ("W MUST BE MORE THAN 0.",            # W <= 0
           "ENTER THE RIVER WIDTH AS",
           "A POSITIVE NUMBER (M)."),
    "E4": ("THAT NUMBER IS TOO LARGE.",         # an input above 1E9
           "KEEP EVERY NUMBER AT OR",
           "BELOW 1E9 (1 BILLION)."),
    "E5": ("VB IS TOO SMALL (BELOW",            # 0 < VB < 1E-9
           "1E-9 M/S). THE CROSSING",
           "WOULD TAKE FOREVER. USE A",
           "LARGER BOAT SPEED."),
    "N1": ("TO LAND DIRECTLY ACROSS",           # VR >= VB: cannot land directly across
           "THE UPSTREAM PART OF VB",
           "MUST CANCEL VR. BUT VR IS",
           "AS FAST AS OR FASTER THAN",
           "THE BOAT (VR ≥ VB), SO IT",
           "IS IMPOSSIBLE. THE BOAT",
           "ALWAYS DRIFTS DOWNSTREAM."),
}

INPUT_ROWS = ("RIVER CROSSING",
              "BOAT AIMED STRAIGHT ACROSS",
              "VB IS THE BOAT SPEED IN",
              "STILL WATER.",
              "VR IS THE RIVER SPEED.",
              "W IS THE RIVER WIDTH.",
              "ALL POSITIVE (VR CAN BE 0)")
PROMPTS = ("VB (M/S)=", "VR (M/S)=", "W (M)=")


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

    def val(self, name, x, unit):
        """Disp "NAME = "+Str9+" UNIT" (or +"°" with no space) after x->Z, prgmZFMT."""
        shown = x if isinstance(x, str) else fmt3(x)
        sep = "" if unit.startswith("°") else " "
        self.disp(f"{name} = {shown}{sep}{unit}" if unit else f"{name} = {shown}")
        self.values.append((name, x, unit))

    def __repr__(self):
        return f"Screen({self.rows!r})"


class Result:
    def __init__(self):
        self.screens = []
        self.messages = []

    def clrhome(self):
        s = Screen()
        self.screens.append(s)
        return s

    def message(self, label):
        """ClrHome, the message rows, Pause."""
        self.messages.append(label)
        s = self.clrhome()
        for row in MESSAGES[label]:
            s.disp(row)
        return self

    @property
    def summary(self):
        """{name: value} of SUMMARY 1/2 and SUMMARY 2/2 (keys prefixed '1:' and '2:')."""
        out = {}
        for k, title in ((1, "SUMMARY 1/2 (AIMED ACROSS)"), (2, "SUMMARY 2/2 (LAND ACROSS)")):
            for s in self.screens:
                if s.title == title:
                    out.update({f"{k}:{n}": v for n, v, u in s.values})
        return out


def run(vb, vr, w):
    """vb, vr, w: the three numbers typed at the input screen."""
    r = Result()
    B, C, E = vb, vr, w                              # Input "VB (M/S)=",B / "VR (M/S)=",C / "W (M)=",E
    if B <= 0:                                       # If B≤0 / Goto E1
        return r.message("E1")
    if C < 0:                                        # If C<0 / Goto E2
        return r.message("E2")
    if E <= 0:                                       # If E≤0 / Goto E3
        return r.message("E3")
    if max(B, max(C, E)) > BIG:                      # If max(B,max(C,E))>1ᴇ9 / Goto E4
        return r.message("E4")
    if B < SMALL:                                    # If B<1ᴇ⁻9 / Goto E5
        return r.message("E5")
    str1, str2, str3 = fmt3(B), fmt3(C), fmt3(E)     # B, C, E -> ZFMT -> Str1, Str2, Str3
    D = E / B                                        # E/B→D
    str4 = fmt3(D)                                   # D -> ZFMT -> Str4

    s = r.clrhome()                                  # STEP 1: crossing time (only VB goes across)
    s.disp("STEP 1  CROSSING TIME")
    s.disp("ACROSS AND DOWNSTREAM")
    s.disp("MOTIONS ARE INDEPENDENT.")
    s.disp("THE BOAT IS AIMED ACROSS,")
    s.disp("SO ONLY VB TAKES IT ACROSS")
    s.disp("T=W/VB")
    s.disp("T=" + str3 + "/" + str1)
    s.val("T", D, "S")

    S = C * D                                        # CD→S   (drift = VR*T)
    s = r.clrhome()                                  # STEP 2: drift downstream
    s.disp("STEP 2  DRIFT")
    s.disp("MEANWHILE THE RIVER")
    s.disp("CARRIES THE BOAT")
    s.disp("DOWNSTREAM AT VR.")
    s.disp("DRIFT=VR*T")
    s.zline("DRIFT=(" + str2 + ")(" + str4 + ")")
    s.val("DRIFT", S, "M")
    s.disp("(DOWNSTREAM OF THE POINT")
    s.disp("STRAIGHT ACROSS)")

    V = math.sqrt(B ** 2 + C ** 2)                   # √(B²+C²)→V   (Pythagoras)
    s = r.clrhome()                                  # STEP 3: resultant speed
    s.disp("STEP 3  RESULTANT SPEED")
    s.disp("VB IS ACROSS AND VR IS")
    s.disp("DOWNSTREAM- THEY ARE")
    s.disp("PERPENDICULAR, SO USE")
    s.disp("PYTHAGORAS.")
    s.disp("V=√(VB²+VR²)")
    s.disp("V=√(" + str1 + "²+" + str2 + "²)")
    s.val("V RESULT", V, "M/S")
    s.disp("(SPEED SEEN FROM SHORE)")

    A = math.degrees(math.atan(C / B))               # tan⁻¹(C/B)→A   (Degree mode)
    P = 90 - A                                       # 90-A→P
    s = r.clrhome()                                  # STEP 4: path angle; heading is not the path
    s.disp("STEP 4  PATH ANGLE")
    s.disp("TAN(ANGLE)=VR/VB")
    s.zline("ANGLE=TAN⁻1(" + str2 + "/" + str1 + ")")
    s.val("FROM ACROSS", A, "°")
    s.disp("(TOWARD DOWNSTREAM). FROM")
    s.disp("THE BANK IT IS 90-ANGLE-")
    s.val("FROM BANK", P, "°")
    s.disp("HEADING IS STRAIGHT ACROSS")
    s.disp("BUT THE PATH IS SLANTED.")

    F = Q = G = None
    if C >= B:                                       # If C≥B / Goto N1
        r.message("N1")                              # Lbl N1: cannot land directly across
    else:
        F = math.degrees(math.asin(C / B))           # sin⁻¹(C/B)→F
        Q = math.sqrt((B - C) * (B + C))             # √((B-C)(B+C))→Q
        G = E / Q                                    # E/Q→G
        s = r.clrhome()                              # STEP 5: heading upstream
        s.disp("STEP 5  HEADING UPSTREAM")
        s.disp("TO LAND DIRECTLY ACROSS,")
        s.disp("THE UPSTREAM PART OF VB")
        s.disp("MUST CANCEL VR-")
        s.disp("VB SIN(ANGLE)=VR")
        s.zline("ANGLE=SIN⁻1(" + str2 + "/" + str1 + ")")
        s.val("FROM ACROSS", F, "°")
        s.val("FROM BANK", 90 - F, "°")              # 90-F→Z
        if C == 0:                                   # If C=0 / Disp ...
            s.disp("(NO CURRENT- AIM ACROSS)")
        if C > 0:                                    # If C>0 / Disp ...
            s.disp("(AIM UPSTREAM)")
        s = r.clrhome()                              # STEP 6: crossing time aimed upstream
        s.disp("STEP 6  NEW CROSSING TIME")
        s.disp("ONLY THE ACROSS PART OF")
        s.disp("VB MOVES THE BOAT ACROSS-")
        s.disp("V ACROSS=VB COS(ANGLE)")
        s.disp("=√(VB²-VR²)")
        s.disp("=√(" + str1 + "²-" + str2 + "²)")
        s.val("V ACROSS", Q, "M/S")
        s.disp("T=W/V ACROSS")
        s.disp("T=" + str3 + "/" + fmt3(Q))
        s.val("T", G, "S")
        # Goto S1

    s = r.clrhome()                                  # Lbl S1: SUMMARY 1/2
    s.disp("SUMMARY 1/2 (AIMED ACROSS)")
    s.val("T", D, "S")
    s.val("DRIFT", S, "M")
    s.val("V RESULT", V, "M/S")
    s.disp("PATH ANGLE (DOWNSTREAM)-")
    s.val("FROM ACROSS", A, "°")
    s.val("FROM BANK", P, "°")
    s.disp("HEADING- STRAIGHT ACROSS,")
    s.disp("NOT ALONG THE PATH.")

    s = r.clrhome()                                  # SUMMARY 2/2
    s.disp("SUMMARY 2/2 (LAND ACROSS)")
    if C < B:                                        # If C<B / Then
        s.disp("HEADING (UPSTREAM)-")
        s.val("FROM ACROSS", F, "°")
        s.val("FROM BANK", 90 - F, "°")
        s.val("V ACROSS", Q, "M/S")
        s.val("T", G, "S")
        s.val("DRIFT", "0", "M")
    else:                                            # Else
        s.disp("IMPOSSIBLE- THE RIVER IS")
        s.disp("AS FAST AS OR FASTER THAN")
        s.disp("THE BOAT (VR ≥ VB), SO IT")
        s.disp("ALWAYS DRIFTS DOWNSTREAM.")
    r.results = dict(T=D, DRIFT=S, V=V, PATH_ACROSS=A, PATH_BANK=P, HEAD_ACROSS=F,
                     HEAD_BANK=None if F is None else 90 - F, V_ACROSS=Q, T_LAND=G)
    return r                                         # Return (back to PHYSOLVE page 2)
