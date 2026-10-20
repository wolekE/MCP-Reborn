# FORCES - Newton's laws solver for AP Physics 1 (TI-84 Plus / TI-84 Plus CE)
#
# This template is the single source for both calculators.  tools/build.py
# expands it into plain TI-BASIC (TI-84_Plus/FORCES.txt, TI-84_Plus_CE/FORCES.txt)
# and tokenizes each into FORCES.8xp.
#
# Template syntax (never reaches the calculator):
#   # ...                     comment line
#   {MONO TEXT|CE TEXT}       per-calculator alternative inside any line
#   @MONO line / @CE line     line (or screen item) for one calculator only
#   @IN v;prompt;cond;err     Input with a Repeat loop until cond is true
#   @OPT v;prompt;cond;err    optional Input via Str8: ENTER alone or 0 gives
#                             v=0 (works whether a blank ENTER stores "" or
#                             leaves Str8 unchanged)
#   @UNITCOL                  mono only: store the unit-column formula in Str9
#   @SCREEN ... @END          a result screen; build.py lays the items out with
#                             Output( (8 rows mono, 10 rows CE), adds ClrHome and
#                             a Pause after every page
#     @T text                 literal text row
#     @S strexpr              string-expression row (Str1, "A"+Str2, ...)
#     @V label;unit;expr      value row: LABEL=round(expr,3) UNIT
#     @BR / @MBR / @CBR       page break (both / mono only / CE only)
#
# Variables: G = g (kept between runs), Z = saved angle mode, X and Str9 =
# answer layout on the mono screen (@UNITCOL), Str8 = raw text of optional
# inputs.  No lists, no matrices.

# ---------------------------------------------------------------- start-up
sin(90)=1→Z
Degree
Float
Normal
Full
@UNITCOL
ClrHome
If G≠9.8 and G≠9.81 and G≠10
9.8→G
If G≠9.8
Then
@SCREEN
@T {NOTE: USING|NOTE: NOT THE USUAL G}
@V G;M/S²;G
@T {CHANGE IT IN|CHANGE IT IN MORE >}
@T {MORE > SETTINGS|SETTINGS (G)}
@END
End

# ------------------------------------------------------------ main menu
Lbl 0
Menu("NEWTON SOLVER","ELEVATOR",E,"{ATWOOD(2 HANG)|ATWOOD (2 HANGING)}",A,"TABLE + HANGER",T,"{FLAT SURF PULL|FLAT SURFACE PULL}",F,"INCLINE",I,"3RD LAW",L,"MORE >",M)

# =========================================================== 1 ELEVATOR
Lbl E
Menu("ELEVATOR","FIND SCALE N",EA,"{ACCEL FROM N|FIND ACCEL FROM SCALE}",EB,"FREE FALL",EC,"FIND MASS",ED,"BACK",0)

# ---- 1A find the scale reading N
Lbl EA
ClrHome
Disp "{FIND SCALE N|ELEVATOR: FIND SCALE N}"
@IN M;M (KG)=;M>0;MUST BE >0
Disp "{SIZE OF A ONLY|ENTER THE SIZE OF A ONLY}"
@IN A;{A (M/S²)=|ACCEL SIZE (M/S²)=};A≥0;MUST BE ≥0
Menu("{ACCEL DIRECTION|ACCELERATION DIRECTION?}","UP",E1,"DOWN",E2,"{ZERO|ZERO (CONSTANT V)}",E3,"{FROM MOTION >|FIGURE OUT FROM MOTION >}",E4)
Lbl E1
A→Y
"{A UP (GIVEN)|ACCEL GIVEN AS UP}"→Str2
Goto E9
Lbl E2
⁻A→Y
"{A DOWN (GIVEN)|ACCEL GIVEN AS DOWN}"→Str2
Goto E9
Lbl E3
0→Y
"{CONST V: A=0|REST OR CONSTANT V: A=0}"→Str2
Goto E9
Lbl E4
Menu("{ELEVATOR IS|THE ELEVATOR IS}","MOVING UP",E5,"MOVING DOWN",E6,"{AT REST|AT REST (STAYING)}",E3)
Lbl E5
1→V
Goto E7
Lbl E6
⁻1→V
Lbl E7
Menu("AND IT IS","SPEEDING UP",E8,"SLOWING DOWN",EE,"{CONSTANT V|CONSTANT SPEED}",E3)
Lbl E8
AV→Y
"{A SAME DIR AS V|SPEEDING UP: A ALONG V}"→Str2
Goto E9
Lbl EE
⁻AV→Y
"{A OPPOSITE TO V|SLOWING DOWN: A OPPOSITE V}"→Str2
Lbl E9
M(G+Y)→N
"ACCEL: NONE"→Str1
If Y>0
"ACCEL: UP"→Str1
If Y<0
"ACCEL: DOWN"→Str1
"NORMAL (N=MG)"→Str3
If Y>0
"HEAVIER (N>MG)"→Str3
If Y<0
"LIGHTER (N<MG)"→Str3
If N=0
"WEIGHTLESS (N=0)"→Str3
If N<0
Then
@SCREEN
@T + = UP
@T N-MG=MA
@T N<0: LIFTS OFF
@MONO @T A IS MORE THAN
@MONO @T G DOWN, SO YOU
@MONO @T FLOAT OFF THE
@MONO @T SCALE
@CE @T ACCEL IS MORE THAN G DOWN,
@CE @T SO YOU FLOAT OFF THE SCALE
@V {SCALE|SCALE READS};N;0
@END
Else
@SCREEN
@T + = UP
@T N-MG=MA
@CE @T SO N=M(G+AY)
@S Str2
@V {AY|ACCEL AY};M/S²;Y
@V {N|SCALE N};N;N
@V {MG|TRUE WEIGHT MG};N;MG
@S Str1
@S Str3
@END
End
Goto 0

# ---- 1B find the acceleration from the scale reading
Lbl EB
ClrHome
Disp "{ACCEL FROM N|ELEVATOR: ACCEL FROM SCALE}"
@IN M;M (KG)=;M>0;MUST BE >0
@IN N;{SCALE N (N)=|SCALE READING N (N)=};N≥0;MUST BE ≥0
(N-MG)/M→Y
"ACCEL: NONE"→Str1
If Y>0
"ACCEL: UP"→Str1
If Y<0
"ACCEL: DOWN"→Str1
@SCREEN
@T + = UP
@T N-MG=MA
@T AY=(N-MG)/M
@V {AY|ACCEL AY};M/S²;Y
@V {MG|TRUE WEIGHT MG};N;MG
@S Str1
@T {THEN PICK V DIR|NEXT: PICK THE VELOCITY}
@END
Menu("{VELOCITY IS|VELOCITY DIRECTION IS}","UP",EF,"DOWN",EG,"{UNKNOWN|UNKNOWN (SHOW BOTH)}",EH)
Lbl EF
1→V
"VELOCITY: UP"→Str6
Goto EI
Lbl EG
⁻1→V
"VELOCITY: DOWN"→Str6
Goto EI
Lbl EH
0→V
"{V: UNKNOWN|VELOCITY: UNKNOWN}"→Str6
Lbl EI
(Y>0)-(Y<0)→S
" "→Str4
" "→Str5
If S=0
Then
"{A=0, SO V IS|A=0, SO THE VELOCITY IS}"→Str2
"CONSTANT"→Str3
"(OR AT REST)"→Str4
"EQUILIBRIUM"→Str5
Else
If V=0
Then
"COULD BE EITHER:"→Str2
"OR"→Str4
If S>0
Then
"UP+SPEEDING"→Str3
"DOWN+SLOWING"→Str5
Else
"DOWN+SPEEDING"→Str3
"UP+SLOWING"→Str5
End
Else
If S=V
Then
"{V, A SAME DIR|V AND A: SAME DIRECTION}"→Str2
"SPEEDING UP"→Str3
Else
"{V, A OPPOSITE|V AND A: OPPOSITE}"→Str2
"SLOWING DOWN"→Str3
End
End
End
@SCREEN
@S Str1
@S Str6
@S Str2
@S Str3
@S Str4
@S Str5
@END
Goto 0

# ---- 1C free fall
Lbl EC
@SCREEN
@T + = UP
@T {N-MG=MA, N=0|N-MG=MA WITH N=0}
@T {SO A=-G|SO -MG=MA AND A=-G}
@V {N|SCALE N};N;0
@V {AY|ACCEL AY};M/S²;⁻G
@T ACCEL: DOWN
@T WEIGHTLESS
@T {(MASS SAME)|(MASS AND MG UNCHANGED)}
@END
Goto 0

# ---- 1D find the mass from N and a
Lbl ED
ClrHome
Disp "{FIND MASS|ELEVATOR: FIND MASS}"
@IN N;{SCALE N (N)=|SCALE READING N (N)=};N>0;MUST BE >0
Input "{AY (+UP/-DN)=|AY (+ UP, - DOWN)=}",Y
"ACCEL: NONE"→Str1
If Y>0
"ACCEL: UP"→Str1
If Y<0
"ACCEL: DOWN"→Str1
If G+Y≤0
Then
@SCREEN
@T + = UP
@T N-MG=MA
@T IMPOSSIBLE:
@T {N>0 NEEDS|A READING N>0 NEEDS}
@T {AY>-G|AY > -G (NOT FREE FALL)}
@END
Else
N/(G+Y)→M
@SCREEN
@T + = UP
@T N-MG=MA
@T M=N/(G+AY)
@V {M|MASS M};KG;M
@V {MG|TRUE WEIGHT MG};N;MG
@S Str1
@END
End
Goto 0

# ============================================================= 2 ATWOOD
Lbl A
Menu("{ATWOOD(2 HANG)|ATWOOD (2 HANGING)}","FIND A AND T",AA,"{FIND 2ND MASS|FIND OTHER MASS FROM A}",AB,"BACK",0)

# ---- 2A acceleration and tension
Lbl AA
ClrHome
Disp "{ATWOOD: A, T|ATWOOD: FIND A AND T}"
@IN P;M1 (KG)=;P>0;MUST BE >0
@IN Q;M2 (KG)=;Q>0;MUST BE >0
max(P,Q)→H
min(P,Q)→L
(H-L)G/(H+L)→A
L(G+A)→T
If P=Q
Then
@SCREEN
@T + = UP (EITHER)
@T T-MG=MA (BOTH)
@T EQUAL MASSES
@V A;M/S²;A
@V T;N;T
@T T=MG ON EACH
@T EQUILIBRIUM
@T {AT REST/CONST V|AT REST OR CONSTANT V}
@END
Else
"M1"→Str1
"M2"→Str2
If Q>P
Then
"M2"→Str1
"M1"→Str2
End
"+="+Str1+" DOWN,"+Str2+" UP"→Str5
Str1+"G-T="+Str1+"A"→Str3
"T-"+Str2+"G="+Str2+"A"→Str4
Str1+" (HEAVY): DOWN"→Str6
Str2+" (LIGHT): UP"→Str7
Str2+"G<T<"+Str1+"G"→Str8
LG<T and T<HG→C
"CHECK "+sub("FAILOK",1+4C,4-2C)→Str1
@SCREEN
@S Str5
@S Str3
@S Str4
@CE @T A=(HEAVY-LIGHT)G/(SUM)
@V A;M/S²;A
@V T;N;T
@S Str6
@S Str7
@BR
@T {CHECK WEIGHTS:|CHECK: LIGHT WT<T<HEAVY WT}
@V M1G;N;PG
@V M2G;N;QG
@V T;N;T
@S Str8
@S Str1
@END
End
Goto 0

# ---- 2B given a and one mass, find the other mass
Lbl AB
ClrHome
Disp "{FIND 2ND MASS|ATWOOD: FIND OTHER MASS}"
@IN A;A (M/S²)=;A≥0;MUST BE ≥0
@IN K;{KNOWN M (KG)=|KNOWN MASS (KG)=};K>0;MUST BE >0
Menu("{KNOWN MASS IS|THE KNOWN MASS IS THE}","{HEAVIER (DOWN)|HEAVIER ONE (GOES DOWN)}",A1,"{LIGHTER (UP)|LIGHTER ONE (GOES UP)}",A2)
Lbl A1
1→W
Goto A3
Lbl A2
0→W
Lbl A3
If A≥G
Then
@SCREEN
@T IMPOSSIBLE:
@T {ATWOOD NEEDS|AN ATWOOD MACHINE NEEDS}
@T {A < G|0 ≤ A < G}
@END
Else
If W
Then
K→H
K(G-A)/(G+A)→L
L→U
Else
K→L
K(G+A)/(G-A)→H
H→U
End
L(G+A)→T
@SCREEN
@T +=HEAVY DOWN
@T HEAVY: MG-T=MA
@T LIGHT: T-MG=MA
@V {OTHER|OTHER MASS};KG;U
@V T;N;T
@V {HEAVY|HEAVY MASS};KG;H
@V {LIGHT|LIGHT MASS};KG;L
@T {HEAVY GOES DOWN|HEAVY GOES DOWN, LIGHT UP}
@END
End
Goto 0

# ===================================================== 3 TABLE + HANGER
Lbl T
ClrHome
Disp "{TABLE + HANGER|TABLE MASS + HANGING MASS}"
@IN M;{TABLE M (KG)=|TABLE MASS (KG)=};M>0;MUST BE >0
@IN H;{HANG M (KG)=|HANGING MASS (KG)=};H>0;MUST BE >0
@IN K;{MUK (0=NONE)=|MUK (0 = FRICTIONLESS)=};K≥0;MUST BE ≥0
K→S
If K>0
Then
Disp "{MUS? 0 OR ENTER|MUS? TYPE 0 OR PRESS ENTER}"
Disp "{= SAME AS MUK|TO USE THE MUK VALUE}"
@OPT S;MUS=;S=0 or S≥K;{NEED MUS≥MUK|MUS MUST BE ≥ MUK}
If S=0
K→S
End
MG→N
HG>SMG→C
If K=0
1→C
If C
Then
(HG-KMG)/(M+H)→A
H(G-A)→T
KN→F
"TABLE: T-FK=MA"→Str1
If K=0
"TABLE: T=MA"→Str1
@SCREEN
@T +=TOWARD PULLEY
@T HANG: MG-T=MA
@S Str1
@V A;M/S²;A
@V T;N;T
@T HANGER: DOWN
@T {TABLE: TO PULLEY|TABLE: TOWARD PULLEY}
@MBR
@MONO @T TABLE MASS:
@MONO @T N-MG=0
@V {N|N ON TABLE};N;N
@V {FK|FK (KINETIC)};N;F
@T {FK=MUK*N|(FK=MUK*N, OPPOSES MOTION)}
@MONO @T (AGAINST MOTION)
@END
Else
HG→T
HG→F
@SCREEN
@T BLOCK STAYS PUT
@T {HANG WT≤MUS*N|HANGER WEIGHT ≤ MUS*N}
@V A;M/S²;0
@V T;N;T
@V {FS|FS (STATIC)};N;F
@V {FS MAX|FS MAX = MUS*N};N;SN
@T {FS POINTS AWAY|FS POINTS AWAY FROM PULLEY}
@MONO @T FROM PULLEY
@END
End
Goto 0

# =================================================== 4 FLAT SURFACE PULL
Lbl F
ClrHome
Disp "{FLAT SURF PULL|FLAT SURFACE PULL (AY=0)}"
@IN M;M (KG)=;M>0;MUST BE >0
@IN P;{PULL F (N)=|APPLIED FORCE F (N)=};P≥0;MUST BE ≥0
Disp "{θ ABOVE HORIZ.|θ = ANGLE ABOVE HORIZONTAL}"
Disp "{NEG=PUSH DOWN|(NEGATIVE = PUSHING DOWN)}"
@IN θ;θ (DEG)=;abs(θ)≤90;USE -90 TO 90
Menu("{FRICTION INFO|WHAT DO YOU KNOW?}","{FRICTION (N)|FRICTION FORCE (N)}",F1,"{MUK|MUK (FK = MUK*N)}",F2,"{CONSTANT V|CONSTANT V (EQUILIBRIUM)}",F3,"{ACCEL AX|ACCELERATION AX}",F4)
Lbl F1
ClrHome
@IN F;{FRICTION (N)=|FRICTION FORCE (N)=};F≥0;MUST BE ≥0
1→W
Goto F9
Lbl F2
ClrHome
@IN K;MUK=;K≥0;MUST BE ≥0
2→W
Goto F9
Lbl F3
0→A
3→W
Goto F9
Lbl F4
ClrHome
Input "{AX (+=PULL)=|AX (+ = PULL DIR)=}",A
4→W
Lbl F9
Pcos(θ)→U
Psin(θ)→V
MG-V→N
If N<0
Then
@SCREEN
@T +X=RIGHT,+Y=UP
@T N+FSINθ-MG=0
@V FY;N;V
@V MG;N;MG
@T N<0: LIFTS OFF
@MONO @T FSINθ>MG, SO
@MONO @T THE BOX LEAVES
@MONO @T THE FLOOR
@CE @T F SINθ > MG, SO THE BOX
@CE @T LEAVES THE FLOOR (AY≠0)
@END
Else
If W=2
KN→F
If W≤2
(U-F)/M→A
If W≥3
U-MA→F
"ACCEL: NONE"→Str1
If A>0
"ACCEL: RIGHT"→Str1
If A<0
"{ACCEL: LEFT|ACCEL: LEFT (SLOWING)}"→Str1
@SCREEN
@T +X=RIGHT,+Y=UP
@CE @T FCOSθ-FRIC=MA
@T N+FSINθ-MG=0
@V FX;N;U
@V FY;N;V
@V N;N;N
@MBR
@MONO @T FCOSθ-FRIC=MA
@V FRIC;N;F
@V AX;M/S²;A
@S Str1
@T FRIC POINTS LEFT
@END
If W=4 and F<0
Then
@SCREEN
@T {FRIC<0: NOT|FRICTION < 0 IS NOT}
@T {POSSIBLE. THE|POSSIBLE: THE PULL IS}
@T {PULL IS TOO|TOO SMALL FOR THAT AX}
@MONO @T SMALL FOR AX
@END
End
If W≤2 and A<0
Then
@SCREEN
@T {FRICTION > FX:|FRICTION > FX, SO:}
@T {IF AT REST, THE|IF AT REST, THE BLOCK}
@T {BLOCK STAYS PUT|STAYS PUT. IF MOVING,}
@T {IF MOVING, IT|IT SLOWS DOWN.}
@MONO @T SLOWS DOWN
@END
End
If W=3 and N>0
Then
@SCREEN
@T {CONSTANT V:|CONSTANT V: AX=0, SO}
@T {FRIC=FCOSθ|FRICTION = F COSθ}
@MONO @T MU NEEDED=FRIC/N
@V {MU|MU NEEDED};;F/N
@END
End
End
Goto 0

# ============================================================= 5 INCLINE
Lbl I
Menu("INCLINE","AT REST",IA,"{SLIDING W/ MUK|SLIDING DOWN WITH MUK}",IB,"FRICTIONLESS",IC,"{MIN MUS (HOLD)|MIN MUS TO HOLD AT REST}",ID,"BACK",0)
Lbl IA
1→W
Goto I0
Lbl IB
2→W
Goto I0
Lbl IC
3→W
Goto I0
Lbl ID
4→W
Lbl I0
ClrHome
Disp "{INCLINE|INCLINE (SLOPE ANGLE θ)}"
@IN M;M (KG)=;M>0;MUST BE >0
@IN θ;{θ (DEG)=|SLOPE ANGLE θ (DEG)=};θ≥0 and θ<90;{USE 0≤θ<90|USE 0 ≤ θ < 90}
MGsin(θ)→U
MGcos(θ)→V
V→N
"ACCEL: NONE"→Str1
# ---- 5A at rest
If W=1
Then
Disp "{MUS? 0 OR ENTER|MUS? TYPE 0 OR PRESS ENTER}"
Disp "{= SKIP CHECK|TO SKIP THE CHECK}"
@OPT S;MUS=;S≥0;MUST BE ≥0
S>0→C
U→F
SN→D
"{YES: STAYS PUT|YES: BLOCK STAYS PUT}"→Str1
If F>D
"NO: WILL SLIDE"→Str1
@SCREEN
@T +X=UPHILL
@T FS-MGSINθ=0
@T N-MGCOSθ=0
@V MGSINθ;N;U
@V MGCOSθ;N;V
@V N;N;N
@V FS;N;F
@T FS POINTS UPHILL
@END
If C
Then
@SCREEN
@T {CHECK FS≤MUS*N|CHECK: IS FS ≤ MUS*N ?}
@V FS;N;F
@V {MUS*N|FS MAX = MUS*N};N;D
@V {MIN MUS|MIN MUS = TANθ};;tan(θ)
@S Str1
@END
Else
@SCREEN
@T {TO HOLD IT|TO HOLD IT AT REST}
@T {NEEDS MUS≥TANθ|IT NEEDS MUS ≥ TANθ}
@V {MIN MUS|MIN MUS};;tan(θ)
@END
End
End
# ---- 5B sliding down with kinetic friction
If W=2
Then
@IN K;MUK=;K≥0;MUST BE ≥0
G(sin(θ)-Kcos(θ))→A
KN→F
If A>0
"{ACCEL: DOWNHILL|ACCEL: DOWNHILL (SPEEDING)}"→Str1
If A<0
"{A UPHILL:SLOWS|ACCEL: UPHILL (SLOWING)}"→Str1
@SCREEN
@T +X=DOWNHILL
@T MGSINθ-FK=MA
@T N-MGCOSθ=0
@CE @T A=G(SINθ-MUK*COSθ)
@V A;M/S²;A
@S Str1
@T FK POINTS UPHILL
@BR
@T COMPONENTS:
@V MGSINθ;N;U
@V MGCOSθ;N;V
@V N;N;N
@V FK;N;F
@T FK=MUK*N
@END
If A<0
Then
@SCREEN
@T {FK > MGSINθ:|FK > MG SINθ, SO:}
@T {IF SLIDING, IT|IF SLIDING, IT SLOWS DOWN.}
@T {SLOWS DOWN. AT|IF AT REST, IT WILL NOT}
@T {REST IT WILL|START TO SLIDE.}
@MONO @T NOT START
@END
End
End
# ---- 5C frictionless
If W=3
Then
Gsin(θ)→A
If A>0
"ACCEL: DOWNHILL"→Str1
@SCREEN
@T +X=DOWNHILL
@T MGSINθ=MA
@T A=GSINθ
@V A;M/S²;A
@S Str1
@V MGSINθ;N;U
@V MGCOSθ;N;V
@V N;N;N
@END
End
# ---- 5D minimum mu_s to hold
If W=4
Then
tan(θ)→S
@SCREEN
@T +X=UPHILL
@T FS=MGSINθ
@T N=MGCOSθ
@T {MUS≥FS/N=TANθ|FS ≤ MUS*N, SO MUS ≥ TANθ}
@V {MIN MUS|MIN MUS};;S
@V MGSINθ;N;U
@V MGCOSθ;N;V
@T {(MASS CANCELS)|(MASS CANCELS: ANY M OK)}
@END
End
Goto 0

# ============================================================= 6 3RD LAW
Lbl L
ClrHome
Disp "{NEWTON 3RD LAW|NEWTON 3RD LAW}"
@IN P;{MA (KG)=|MASS A (KG)=};P>0;MUST BE >0
@IN Q;{MB (KG)=|MASS B (KG)=};Q>0;MUST BE >0
Disp "{F? 0 OR ENTER|F? TYPE 0 OR PRESS ENTER}"
Disp "{= RATIO ONLY|FOR THE RATIO ONLY}"
@OPT F;{F (N)=|FORCE F (N)=};1;
abs(F)→F
F>0→C
If C
Then
@SCREEN
@T +=F ON B DIR
@T {FAB=-FBA (OPP)|F(A ON B)=-F(B ON A)}
@CE @T SAME SIZE, OPPOSITE DIRS
@V {F|F (EACH)};N;F
@V {AB|AB=F/MB};M/S²;F/Q
@V {AA|AA=-F/MA};M/S²;⁻F/P
@T {AA/AB=MB/MA|SIZE RATIO AA/AB = MB/MA}
@V RATIO;;Q/P
@T {LIGHTER: MORE A|LIGHTER ONE GETS MORE A}
@END
Else
@SCREEN
@T +=F ON B DIR
@T {FAB=-FBA|F(A ON B)=-F(B ON A)}
@T SAME SIZE F,
@T OPPOSITE DIRS
@T {A=F/M, SO|A=F/M, SO SIZE RATIO IS}
@T AA/AB=MB/MA
@V RATIO;;Q/P
@T {LIGHTER: MORE A|LIGHTER ONE GETS MORE A}
@END
End
@SCREEN
@T REMEMBER:
@T {N AND MG: NOT|N AND MG ARE NOT A 3RD}
@T {A 3RD LAW PAIR|LAW PAIR (SAME OBJECT).}
@MONO @T (SAME OBJECT)
@T {EARTH PULLS YOU|EARTH PULLS YOU DOWN. ITS}
@T {DOWN. PARTNER:|PARTNER IS YOU PULLING}
@T {YOU PULL EARTH|EARTH UP.}
@MONO @T UP
@BR
@T {PAIRS ACT ON|3RD LAW PAIRS ACT ON}
@T {DIFFERENT|DIFFERENT OBJECTS, SO THEY}
@T {OBJECTS, SO|NEVER CANCEL ON ONE}
@T {THEY NEVER|FREE-BODY DIAGRAM.}
@MONO @T CANCEL ON ONE
@MONO @T DIAGRAM
@END
Goto 0

# ================================================================ 7 MORE
Lbl M
Menu("MORE","SIMPLE CASES",S,"CONCEPT CHECK",C,"SETTINGS (G)",G,"QUIT",Q,"BACK",0)

# ------------------------------------------------------- simple cases
Lbl S
Menu("SIMPLE CASES","{HANGING, REST|HANGING AT REST (T=MG)}",SA,"{TERMINAL VEL.|TERMINAL VELOCITY}",SB,"{HANG + ACCEL|HANGING, ACCELERATING}",SC,"{SUM F=MA|SUM OF FORCES = MA}",SD,"BACK",0)

Lbl SA
ClrHome
Disp "{HANGING AT REST|HANGING AT REST ON A ROPE}"
@IN M;M (KG)=;M>0;MUST BE >0
@SCREEN
@T + = UP
@T T-MG=0
@T SO T=MG
@V T;N;MG
@T T UP, MG DOWN
@T EQUILIBRIUM
@T (A=0)
@END
Goto 0

Lbl SB
ClrHome
Disp "{TERMINAL VEL.|TERMINAL VELOCITY}"
@IN M;M (KG)=;M>0;MUST BE >0
@SCREEN
@T + = UP
@T FAIR-MG=0
@T SO FAIR=MG
@V FAIR;N;MG
@V A;M/S²;0
@T {FAIR UP,V DOWN|AIR FORCE UP, V DOWN}
@T EQUILIBRIUM
@T (CONSTANT V)
@END
Goto 0

Lbl SC
ClrHome
Disp "{HANGING + ACCEL|HANGING MASS, ACCELERATING}"
@IN M;M (KG)=;M>0;MUST BE >0
Input "{AY (+UP/-DN)=|AY (+ UP, - DOWN)=}",Y
M(G+Y)→T
"ACCEL: NONE"→Str1
If Y>0
"ACCEL: UP"→Str1
If Y<0
"ACCEL: DOWN"→Str1
"T=MG"→Str2
If Y>0
"T>MG"→Str2
If Y<0
"T<MG"→Str2
If T<0
Then
@SCREEN
@T + = UP
@T T-MG=MA
@T T<0: ROPE SLACK
@T {A ROPE CANNOT|A ROPE CAN ONLY PULL,}
@T {PUSH, SO AY|SO AY MUST BE ≥ -G}
@MONO @T MUST BE ≥ -G
@END
Else
@SCREEN
@T + = UP
@T T-MG=MA
@T T=M(G+AY)
@V T;N;T
@V MG;N;MG
@V AY;M/S²;Y
@S Str1
@S Str2
@END
End
Goto 0

Lbl SD
ClrHome
Disp "{SUM F=MA|SUM OF FORCES = MA}"
Disp "{+ = YOUR CHOICE|+ DIRECTION = YOUR CHOICE}"
Disp "{0 OR ENTER=NONE|0 OR ENTER ALONE = NONE}"
0→F
@OPT D;F1 (N)=;1;
F+D→F
@OPT D;F2 (N)=;1;
F+D→F
@OPT D;F3 (N)=;1;
F+D→F
@OPT D;F4 (N)=;1;
F+D→F
@IN M;M (KG)=;M>0;MUST BE >0
F/M→A
"{NET F: + DIR|NET FORCE: + DIRECTION}"→Str1
If F<0
"{NET F: - DIR|NET FORCE: - DIRECTION}"→Str1
If F=0
"{NET F: ZERO|NET FORCE: ZERO}"→Str1
"EQUILIBRIUM: NO"→Str2
If F=0
"EQUILIBRIUM: YES"→Str2
@SCREEN
@T + = YOUR CHOICE
@T SUM F=MA
@T A=(SUM F)/M
@V FNET;N;F
@V A;M/S²;A
@S Str1
@S Str2
@END
Goto 0

# ------------------------------------------------------- concept check
Lbl C
Menu("{THE OBJECT IS|THE OBJECT IS}","MOVING UP",C1,"MOVING DOWN",C2,"MOVING RIGHT",C3,"MOVING LEFT",C4,"{AT REST|AT REST (STAYING)}",C5,"{V=0 1 INSTANT|V=0 FOR ONE INSTANT}",C6)
Lbl C1
"UP"→Str1
"DOWN"→Str2
Goto C7
Lbl C2
"DOWN"→Str1
"UP"→Str2
Goto C7
Lbl C3
"RIGHT"→Str1
"LEFT"→Str2
Goto C7
Lbl C4
"LEFT"→Str1
"RIGHT"→Str2
Lbl C7
Menu("AND IT IS","SPEEDING UP",C8,"SLOWING DOWN",C9,"{CONSTANT V|CONSTANT VELOCITY}",CA)
Lbl C8
@SCREEN
@S "MOVING "+Str1
@T SPEEDING UP
@T A SAME DIR AS V
@S "ACCEL: "+Str1
@S "NET F: "+Str1
@T EQUILIBRIUM: NO
@T (SUM F NOT 0)
@END
Goto 0
Lbl C9
@SCREEN
@S "MOVING "+Str1
@T SLOWING DOWN
@T A OPPOSITE TO V
@S "ACCEL: "+Str2
@S "NET F: "+Str2
@T EQUILIBRIUM: NO
@T (SUM F NOT 0)
@END
Goto 0
Lbl CA
@SCREEN
@S "MOVING "+Str1
@T CONSTANT V
@T ACCEL: ZERO
@T NET F: ZERO
@T EQUILIBRIUM: YES
@T (SUM F=0)
@END
Goto 0
Lbl C5
@SCREEN
@T AT REST (STAYS)
@T ACCEL: ZERO
@T NET F: ZERO
@T EQUILIBRIUM: YES
@T (SUM F=0)
@END
Goto 0
Lbl C6
@SCREEN
@T V=0 ONE INSTANT
@T {EQUILIBRIUM IS|EQUILIBRIUM IS NOT}
@T {NOT GUARANTEED|GUARANTEED (IT NEEDS A=0)}
@T {EG TOP OF TOSS:|EXAMPLE: TOP OF A TOSS}
@T ACCEL: G DOWN
@T NET F: MG DOWN
@T EQUILIBRIUM: NO
@MONO @T (NEEDS A=0)
@END
Goto 0

# ------------------------------------------------------------ settings
Lbl G
@SCREEN
@T SETTINGS
@T {CURRENT G:|CURRENT G:}
@V G;M/S²;G
@T {PICK A NEW G|PICK A NEW G NEXT}
@T {NEXT|(KEPT BETWEEN RUNS)}
@END
Menu("{SET G (M/S²)|SET G (M/S²)}","9.8",G1,"9.81",G2,"10",G3,"{KEEP|KEEP CURRENT G}",0)
Lbl G1
9.8→G
Goto G4
Lbl G2
9.81→G
Goto G4
Lbl G3
10→G
Lbl G4
@SCREEN
@T SETTINGS
@T {NEW G SAVED:|NEW G SAVED:}
@V G;M/S²;G
@END
Goto 0

# ---------------------------------------------------------------- quit
Lbl Q
If not(Z)
Radian
ClrHome
Stop
