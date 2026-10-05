"""Python reference for prgmZVOVF - the VOVFSTA solver (A) and its free-fall mode (B).

It mirrors src/ZVOVF.txt line for line: the same validation order, the same case table
(which unknown is found first and with which equation), the same formulas written in the
same operation order, the same quadratic root choice and the same messages.

Arithmetic is done the way the calculator (and tools/tisim.py) does it: decimal numbers
with 14 significant digits, rounded after every operation. So the numbers returned here
are exactly the numbers ZVOVF puts on screen once formatted with fmt3().

    solve(v0, vf, s, t, a, k=1)    k = 1 (or anything but 2): general VOVFSTA solver
                                   k = 2: free fall, a is ignored and A = -9.8

Pass UNKNOWN (999) for each unknown. The result is a dict:
    kind      'summary' or 'message'
    code      'SUMMARY' or the TI label of the message screen ('E1' ... 'EF')
    lines     the rows of the final screen (the SUMMARY screen or the message screen)
    case      1..10 (row of the case table) when it got that far, else None
    eqs       (U1, EQ1, U2, EQ2): unknown found first + its equation, then the second
    summary   {name: (value, unit_text)} for every NAME = VALUE UNIT summary row
    steps     [(name, value), ...] results shown on the step screens, in order
    quad      {'J','H','I','G'} from the quadratic (cases 2 and 5), after root clean-up
    answers   1 or 2 (two physical answers: both quadratic roots are > 0)
"""
from decimal import Decimal, Context, ROUND_HALF_UP

from common import UNKNOWN, fmt3

_CTX = Context(prec=14, rounding=ROUND_HALF_UP, Emax=999, Emin=-999)
_SMALL = Decimal("1E-9")      # ZFMT shows 0 below this; also the input-size lower limit
_BIG = Decimal("1E9")         # input-size upper limit (keeps every result < 1E100)


# ---------------------------------------------------------------- calculator arithmetic
def num(x):
    """A number as the calculator stores it (14 significant digits)."""
    if isinstance(x, float):
        x = Decimal(repr(x))
    elif not isinstance(x, Decimal):
        x = Decimal(str(x))
    x = _CTX.plus(x)
    if x != 0 and abs(x) >= Decimal("1E100"):
        raise OverflowError("ERR:OVERFLOW")
    if x != 0 and abs(x) < Decimal("1E-99"):
        return Decimal(0)
    return x


def add(a, b):
    return num(a + b)


def sub(a, b):
    return num(a - b)


def mul(a, b):
    return num(Decimal(a) * Decimal(b))


def div(a, b):
    if b == 0:
        raise ZeroDivisionError("ERR:DIVIDE BY 0")
    return num(_CTX.divide(Decimal(a), Decimal(b)))


def sq(a):
    return num(a * a)


def neg(a):
    return num(-a)


def sqrt(a):
    if a < 0:
        raise ValueError("ERR:NONREAL ANS")
    return num(a.sqrt(_CTX))


# ---------------------------------------------------------------- prgmZQUAD mirror
def zquad(L, M, N):
    """prgmZQUAD: solve L*T^2 + M*T + N = 0. Returns (J, H, I, G)."""
    if L == 0:                                   # "NO T² TERM, SO LINEAR"
        if M == 0:
            return 0, None, None, None           # "NO SOLUTION FOR T"
        H = div(neg(N), M)                       # ⁻N/M→H
        return 1, H, H, None
    G_ = sub(sq(M), mul(mul(4, L), N))           # M²-4LN→G
    if abs(G_) < mul(Decimal("1E-10"), add(sq(M), abs(mul(mul(4, L), N)))):
        G_ = Decimal(0)
    if G_ < 0:
        return 0, None, None, G_                 # "B²-4AC<0 SO NO REAL ROOT"
    if M >= 0:                                   # If M≥0
        Z = div(sub(neg(M), sqrt(G_)), 2)        # (⁻M-√(G))/2→Z
    else:                                        # If M<0
        Z = div(add(neg(M), sqrt(G_)), 2)        # (⁻M+√(G))/2→Z
    if Z == 0:                                   # If Z=0
        H = I = Decimal(0)                       # 0→H, 0→I
    else:
        H = div(Z, L)                            # Z/L→H
        I = div(N, Z)                            # N/Z→I
    if H > I:
        H, I = I, H
    return 2, H, I, G_


# ---------------------------------------------------------------- the case table
# C: (unknown pair, U1, EQ1, U2, EQ2) - find U1 with EQ1 (it has no U2), then U2 with EQ2.
CASES = {
    1: ("VF", "VF=V0+AT", "S", "S=V0T+(1/2)AT²"),
    2: ("T", "S=V0T+(1/2)AT²", "VF", "VF=V0+AT"),
    3: ("VF", "S=(1/2)(V0+VF)T", "A", "VF=V0+AT"),
    4: ("V0", "VF=V0+AT", "S", "S=VFT-(1/2)AT²"),
    5: ("T", "S=VFT-(1/2)AT²", "V0", "VF=V0+AT"),
    6: ("V0", "S=(1/2)(V0+VF)T", "A", "VF=V0+AT"),
    7: ("S", "VF²=V0²+2AS", "T", "VF=V0+AT"),
    8: ("S", "S=(1/2)(V0+VF)T", "A", "VF=V0+AT"),
    9: ("T", "S=(1/2)(V0+VF)T", "A", "VF²=V0²+2AS"),
    10: ("V0", "S=V0T+(1/2)AT²", "VF", "S=VFT-(1/2)AT²"),
}
# which two variables are unknown in each case (same order as the If tests in ZVOVF)
CASE_UNKNOWNS = [(1, "FS"), (2, "FD"), (3, "FA"), (4, "VS"), (5, "VD"), (6, "VA"),
                 (7, "SD"), (8, "SA"), (9, "DA"), (10, "VF")]


# ---------------------------------------------------------------- message screens
def message_lines(code, J=None, Q=1, C=None, S=None):
    """The rows of each message screen, exactly as ZVOVF displays them."""
    if code == "E1":
        rows = ["WRONG NUMBER OF UNKNOWNS", "YOU ENTERED 999 (UNKNOWN)",
                "FOR " + "012345"[J] + " OF THE " + ("5" if Q == 1 else "4") + " VALUES."]
        if Q == 1:
            rows += ["ENTER EXACTLY 3 KNOWNS"]
        else:
            rows += ["A IS -9.8 (AUTO), SO ENTER", "EXACTLY 2 OF V0,VF,S,T"]
        return rows + ["AND 999 FOR THE OTHER 2."]
    if code == "E2":
        return ["NUMBER OUT OF RANGE", "EACH KNOWN MUST BE 0, OR", "FROM 1E-9 TO 1E9 IN SIZE",
                "(+ OR -).", "999 MEANS UNKNOWN."]
    if code == "E3":
        return ["CHECK T", "T MUST BE MORE THAN 0.", "T IS THE TIME FROM THE",
                "START TO THE END, SO IT", "CANNOT BE 0 OR NEGATIVE."]
    if code == "E5":       # quadratic with B²-4AC < 0 (negative under the square root)
        rows = ["IMPOSSIBLE", "B²-4AC<0, SO THERE IS NO", "REAL T (A NEGATIVE NUMBER",
                "UNDER THE √)."]
        if C == 2:
            rows += ["IT NEVER GETS TO THAT S.", "(EX. A BALL THROWN UP AT",
                     "10 M/S NEVER RISES 10 M.)"]
        else:
            rows += ["NO START VELOCITY CAN END", "AT THIS VF AFTER THIS S.",
                     "(EX. A BALL CANNOT BE AT", "ITS TOP BELOW ITS START.)"]
        return rows + ["CHECK S AND THE SIGNS.", "(DOWN/BACKWARD IS -.)"]
    if code == "E6":       # quadratic/linear: no root T > 0
        rows = ["NO PHYSICAL SOLUTION"]
        if S == 0:
            rows += ["S IS 0 ONLY AT THE START", "(T IS 0). IT NEVER COMES",
                     "BACK TO ITS START."]
        else:
            rows += ["NO ROOT IS AFTER THE START", "(T>0). IT WAS AT S ONLY",
                     "BEFORE THE START, SO IT", "NEVER GETS THERE."]
        return rows + ["CHECK S AND THE SIGNS."]
    if code == "E7":
        return ["NOT ENOUGH INFORMATION", "A IS 0 AND VF IS THE SAME", "AS V0 (STEADY VELOCITY).",
                "S IS V0 TIMES T, BUT BOTH", "ARE UNKNOWN, SO THEY", "CANNOT BE FOUND.",
                "USE S OR T AS A KNOWN", "INSTEAD OF VF."]
    if code == "E8":
        return ["IMPOSSIBLE", "A IS 0, SO THE VELOCITY", "CANNOT CHANGE, BUT VF IS",
                "NOT THE SAME AS V0.", "CHECK A, V0 AND VF."]
    if code == "E9":
        return ["NO MOTION TO SOLVE", "VF IS THE SAME AS V0 AND", "A IS NOT 0, SO T IS 0 AND",
                "S IS 0 (STILL AT THE", "START). CHECK V0 AND VF."]
    if code == "EA":
        return ["NO PHYSICAL SOLUTION", "A HAS THE WRONG SIGN.", "T IS (VF-V0)/A, WHICH IS",
                "NEGATIVE HERE. VF-V0 AND A", "MUST HAVE THE SAME SIGN.", "(UP/FORWARD IS +.)",
                "CHECK THE SIGNS."]
    if code == "EB":
        return ["NOT ENOUGH INFORMATION", "V0+VF IS 0 AND S IS 0.", "MANY T AND A FIT THIS",
                "(EX. THROWN UP, CAUGHT AT", "THE SAME HEIGHT).", "USE T OR A AS A KNOWN."]
    if code == "EC":
        return ["IMPOSSIBLE", "S IS (1/2)(V0+VF)T, AND", "V0+VF IS 0, SO S IS 0 FOR",
                "ANY T. BUT S IS NOT 0.", "CHECK V0, VF AND S."]
    if code == "ED":
        return ["NO MOTION TO SOLVE", "S IS 0 BUT V0+VF IS NOT,", "SO T IS 2S/(V0+VF), WHICH",
                "IS 0 (THE START). THEN A", "CANNOT BE FOUND.", "CHECK V0, VF AND S."]
    if code == "EE":
        return ["NO PHYSICAL SOLUTION", "T IS 2S/(V0+VF), WHICH IS", "NEGATIVE HERE. S AND V0+VF",
                "MUST HAVE THE SAME SIGN.", "(UP/FORWARD IS +.)", "CHECK THE SIGNS."]
    if code == "EF":       # case 2/5 with A = 0 and the known velocity 0: it never moves
        rows = ["NOT ENOUGH INFORMATION" if S == 0 else "IMPOSSIBLE"]
        rows += ["A IS 0 AND V0 IS 0, SO" if C == 2 else "A IS 0 AND VF IS 0, SO"]
        rows += ["IT NEVER MOVES."]
        rows += ["S IS 0 FOR ANY T, SO T", "CANNOT BE FOUND."] if S == 0 else ["IT CAN NEVER GET TO S."]
        return rows + ["CHECK YOUR VALUES."]
    raise KeyError(code)


def _direction(Q, x, line, up_limit=None, down_limit=None):
    """' (UP)' / ' (DOWN)' added to a free-fall summary row (Q=2), as ZVOVF does."""
    if Q == 2 and x >= _SMALL and (up_limit is None or len(line) <= up_limit):
        line += " (UP)"
    if Q == 2 and x <= -_SMALL and (down_limit is None or len(line) <= down_limit):
        line += " (DOWN)"
    return line


def _row(name, x, unit):
    return f"{name} = {fmt3(x)} {unit}"


# ---------------------------------------------------------------- the solver
def solve(v0, vf, s, t, a=None, k=1):
    Q = 2 if k == 2 else 1                       # 1→Q / If K=2 / 2→Q
    out = {"kind": None, "code": None, "lines": [], "case": None, "eqs": None,
           "summary": {}, "steps": [], "quad": None, "answers": 1, "mode": Q}

    def message(code, **kw):
        out.update(kind="message", code=code, lines=message_lines(code, Q=Q, **kw))
        return out

    V, F, S, D = num(v0), num(vf), num(s), num(t)
    A = num(a) if Q == 1 else num("-9.8")        # Input A / ⁻9.8→A
    J = sum(1 for x in (V, F, S, D, A) if x == UNKNOWN)
    if J != 2:
        return message("E1", J=J)                # wrong number of unknowns
    E = 0
    for x in (V, F, S, D, A):                    # each known: 0, or 1E-9 <= |x| <= 1E9
        if abs(x) > _BIG or (x != 0 and abs(x) < _SMALL):
            E = 1
    if E == 1:
        return message("E2")
    if D != UNKNOWN and D <= 0:
        return message("E3")                     # T must be more than 0

    unknown = {"V": V == UNKNOWN, "F": F == UNKNOWN, "S": S == UNKNOWN, "D": D == UNKNOWN,
               "A": A == UNKNOWN}
    C = None
    for c, pair in CASE_UNKNOWNS:
        if unknown[pair[0]] and unknown[pair[1]]:
            C = c
    out["case"] = C
    U1, EQ1, U2, EQ2 = CASES[C]
    out["eqs"] = (U1, EQ1, U2, EQ2)
    # GIVEN screen (no numbers computed)

    # impossible / not-enough-information checks, in the order ZVOVF does them
    if C == 7 and A == 0 and F == V:
        return message("E7")
    if C == 7 and A == 0:
        return message("E8")
    if C == 7 and F == V:
        return message("E9")
    if C == 7 and mul(sub(F, V), A) < 0:         # T=(VF-V0)/A would be negative
        return message("EA")
    small_sum = abs(add(V, F)) <= mul(Decimal("1E-12"), add(abs(V), abs(F)))
    if C == 9 and small_sum and S == 0:
        return message("EB")
    if C == 9 and small_sum:
        return message("EC")
    if C == 9 and S == 0:
        return message("ED")
    if C == 9 and mul(S, add(V, F)) < 0:         # T=2S/(V0+VF) would be negative
        return message("EE")
    if C == 2 and A == 0 and V == 0:
        return message("EF", C=C, S=S)
    if C == 5 and A == 0 and F == 0:
        return message("EF", C=C, S=S)

    E = 1
    P = B = None
    steps = out["steps"]
    if C in (2, 5):
        # STEP 1: S=V0T+(1/2)AT² (case 2) or S=VFT-(1/2)AT² (case 5) is a quadratic in T
        L = div(A, 2)                            # A/2→L
        M = V                                    # V→M
        if C == 5:
            L = div(neg(A), 2)                   # ⁻A/2→L
            M = F                                # F→M
        N = neg(S)                               # ⁻S→N
        J, H, I, G_ = zquad(L, M, N)
        # The smaller root from T1*T2 = N/L (no cancellation; exactly 0 when S=0).
        if J == 2 and abs(H) < abs(I):
            H = div(N, mul(L, I))                # N/(LI)→H
        if J == 2 and abs(I) < abs(H):
            I = div(N, mul(L, H))                # N/(LH)→I
        out["quad"] = {"J": J, "H": H, "I": I, "G": G_}
        E = 0
        if J == 1 and H > 0:                     # linear (A=0): one root, and T>0
            E, D = 1, H
        if J == 2 and H <= 0 and I > 0:          # "T1<0 IS BEFORE THE START, SO T = T2"
            E, D = 1, I
        if J == 2 and H > 0 and G_ == 0:         # double root: "ONE ROOT (B²-4AC IS 0)"
            E, D = 1, H
        if J == 2 and H > 0 and G_ != 0:         # both roots > 0: two physical answers
            E, D, P = 2, H, I
        if J == 0:
            return message("E5", C=C)            # negative under the square root
        if E == 0:
            return message("E6", S=S)            # no root after the start
        # STEP 2: VF=V0+AT (case 2) or V0=VF-AT (case 5) for each physical T
        for Lk in range(1, E + 1):
            Nk = D if Lk == 1 else P
            if C == 2:
                Mk = add(V, mul(A, Nk))          # V+AN→M
            else:
                Mk = sub(F, mul(A, Nk))          # F-AN→M
            name = U2 if E == 1 else f"{U2}(T{Lk})"
            steps.append((name, Mk))
            if Lk == 2:
                B = Mk
            if Lk == 1 and C == 2:
                F = Mk
            if Lk == 1 and C == 5:
                V = Mk
        steps.insert(0, ("T", D) if E == 1 else ("T1", D))
        if E == 2:
            steps.insert(1, ("T2", P))
    elif C == 1:
        F = add(V, mul(A, D))                    # VF=V0+AT          V+AD→F
        steps.append(("VF", F))
        S = add(mul(V, D), div(mul(A, sq(D)), 2))  # S=V0T+(1/2)AT²  VD+AD²/2→S
        steps.append(("S", S))
    elif C == 3:
        F = sub(div(mul(2, S), D), V)            # VF=2S/T-V0        2S/D-V→F
        steps.append(("VF", F))
        A = div(sub(F, V), D)                    # A=(VF-V0)/T       (F-V)/D→A
        steps.append(("A", A))
    elif C == 4:
        V = sub(F, mul(A, D))                    # V0=VF-AT          F-AD→V
        steps.append(("V0", V))
        S = sub(mul(F, D), div(mul(A, sq(D)), 2))  # S=VFT-(1/2)AT²  FD-AD²/2→S
        steps.append(("S", S))
    elif C == 6:
        V = sub(div(mul(2, S), D), F)            # V0=2S/T-VF        2S/D-F→V
        steps.append(("V0", V))
        A = div(sub(F, V), D)                    # A=(VF-V0)/T
        steps.append(("A", A))
    elif C == 7:
        S = div(sub(sq(F), sq(V)), mul(2, A))    # S=(VF²-V0²)/(2A)  (F²-V²)/(2A)→S
        steps.append(("S", S))
        D = div(sub(F, V), A)                    # T=(VF-V0)/A       (F-V)/A→D
        steps.append(("T", D))
    elif C == 8:
        S = div(mul(add(V, F), D), 2)            # S=(1/2)(V0+VF)T   (V+F)D/2→S
        steps.append(("S", S))
        A = div(sub(F, V), D)                    # A=(VF-V0)/T
        steps.append(("A", A))
    elif C == 9:
        D = div(mul(2, S), add(V, F))            # T=2S/(V0+VF)      2S/(V+F)→D
        steps.append(("T", D))
        A = div(sub(sq(F), sq(V)), mul(2, S))    # A=(VF²-V0²)/(2S)  (F²-V²)/(2S)→A
        steps.append(("A", A))
    elif C == 10:
        V = div(sub(S, div(mul(A, sq(D)), 2)), D)  # V0=(S-(1/2)AT²)/T  (S-AD²/2)/D→V
        steps.append(("V0", V))
        F = div(add(S, div(mul(A, sq(D)), 2)), D)  # VF=(S+(1/2)AT²)/T  (S+AD²/2)/D→F
        steps.append(("VF", F))

    out["answers"] = E
    summ = out["summary"]
    froms = [f"{U1} FROM {EQ1}", f"{U2} FROM {EQ2}"]
    if E == 1:
        lines = ["SUMMARY" if Q == 1 else "SUMMARY (FREE FALL)"]
        for name, x, unit, directional in (("V0", V, "M/S", True), ("VF", F, "M/S", True),
                                           ("S", S, "M", True), ("T", D, "S", False),
                                           ("A", A, "M/S²", False)):
            row = _row(name, x, unit)
            if directional:
                row = _direction(Q, x, row)
            summ[name] = (x, row.split(" = ", 1)[1].split(" ", 1)[1])
            lines.append(row)
    else:
        lines = ["SUMMARY (2 ANSWERS)"]
        kname, kval = ("V0", V) if C == 2 else ("VF", F)
        for name, x, unit, directional in ((kname, kval, "M/S", True), ("S", S, "M", True),
                                           ("A", A, "M/S²", False)):
            row = _row(name, x, unit)
            if directional:
                row = _direction(Q, x, row)
            summ[name] = (x, row.split(" = ", 1)[1].split(" ", 1)[1])
            lines.append(row)
        first = F if C == 2 else V
        for n_, (tval, uval) in enumerate(((D, first), (P, B)), 1):
            row = _row(f"T{n_}", tval, "S")
            summ[f"T{n_}"] = (tval, "S")
            lines.append(row)
            name = f"{U2}(T{n_})"
            row = _direction(Q, uval, _row(name, uval, "M/S"), up_limit=21, down_limit=19)
            summ[name] = (uval, row.split(" = ", 1)[1].split(" ", 1)[1])
            lines.append(row)
    lines += froms
    out.update(kind="summary", code="SUMMARY", lines=lines)
    return out


def free_fall(v0, vf, s, t):
    """Section B: the same solver with A = -9.8 filled in (K=2)."""
    return solve(v0, vf, s, t, None, k=2)
