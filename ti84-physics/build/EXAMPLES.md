# Example runs (simulated on PHYSICS.8xp)

## A. VOVFSTA solver: v0 = 8.0 m/s, a = 1.5 m/s², s = 120 m; vf and t unknown (999)

Menu choices: VOVFSTA SOLVER > QUIT TO MAIN MENU

Typed: V0 (M/S)= 8; VF (M/S)= 999; S (M)= 120; T (S)= 999; A (M/S²)= 1.5

```
+--------------------------+
|VOVFSTA SOLVER            |
|KNOW 3 OF V0,VF,S,T,A.    |
|IT FINDS THE OTHER 2.     |
|ENTER 999 IF UNKNOWN.     |
|UP/FORWARD IS +           |
|DOWN/BACKWARD IS -        |
|FROM REST MEANS V0 IS 0.  |
|STOPS/AT TOP MEANS VF IS 0|
|UNITS M/S, M, S, M/S²     |
|                          |
+--------------------------+
+--------------------------+
|GIVEN                     |
|V0 = 8.00 M/S             |
|S = 120 M                 |
|A = 1.50 M/S²             |
|UNKNOWNS ARE T AND VF     |
|1) T FROM S=V0T+(1/2)AT²  |
|   (IT HAS NO VF)         |
|2) VF FROM VF=V0+AT       |
|   (NOW T IS KNOWN)       |
|                          |
+--------------------------+
+--------------------------+
|STEP 1 - FIND T           |
|USE S=V0T+(1/2)AT²        |
|(IT HAS NO VF)            |
|(120)=(8.00)T             |
|  +(1/2)(1.50)T²          |
|T IS SQUARED, SO WRITE    |
|(1/2)AT²+V0T-S=0 AND USE  |
|THE QUADRATIC FORMULA WITH|
|A,B,C AS (1/2)A, V0, -S   |
|                          |
+--------------------------+
+--------------------------+
|SOLVE QUADRATIC FOR T     |
|0.750T²+8.00T-120=0       |
|T=(-B+/-√(B²-4AC))/(2A)   |
|B²-4AC = 424              |
|T1 = -19.1 S              |
|T2 = 8.39 S               |
|T1<0 IS BEFORE THE START, |
|SO T = 8.39 S             |
|                          |
|                          |
+--------------------------+
+--------------------------+
|STEP 2 - FIND VF          |
|USE VF=V0+AT              |
|(NOW T IS KNOWN)          |
|VF=(8.00)+(1.50)(8.39)    |
|VF = 20.6 M/S             |
|                          |
|                          |
|                          |
|                          |
|                          |
+--------------------------+
+--------------------------+
|SUMMARY                   |
|V0 = 8.00 M/S             |
|VF = 20.6 M/S             |
|S = 120 M                 |
|T = 8.39 S                |
|A = 1.50 M/S²             |
|T FROM S=V0T+(1/2)AT²     |
|VF FROM VF=V0+AT          |
|                          |
|                          |
+--------------------------+
```

## B. Free fall: thrown up at 10 m/s from a 15 m roof (FREE FALL > 4 THROWN UP (HEIGHT H))

Menu choices: FREE FALL > THROWN UP (HEIGHT H) > BACK > QUIT TO MAIN MENU

Typed: HEIGHT H (M)= 15; V0 UP (M/S)= 10

```
+--------------------------+
|STEP 1  TIME TO THE TOP   |
|AT THE TOP VF IS 0.       |
|USE VF=V0+AT (NO S)       |
|0=10.0+(-9.8)T            |
|T=V0/9.8                  |
|T=10.0/9.8                |
|T TO TOP = 1.02 S         |
|                          |
|                          |
|                          |
+--------------------------+
+--------------------------+
|STEP 2  MAX HEIGHT        |
|AT THE TOP VF IS 0.       |
|USE VF²=V0²+2AS (NO T)    |
|0=(10.0)²+2(-9.8)S        |
|S=V0²/(2(9.8))            |
|S=(10.0)²/(2(9.8))        |
|ABOVE LAUNCH = 5.10 M     |
|ABOVE GROUND IS H+S       |
|ABOVE GROUND = 20.1 M     |
|                          |
+--------------------------+
+--------------------------+
|STEP 3  TIME TO GROUND    |
|IT ENDS H BELOW THE START,|
|S = -15.0 M               |
|VF NOT KNOWN, SO USE      |
|S=V0T+(1/2)AT²            |
|-15.0=(10.0)T-4.9T²       |
|((1/2)(-9.8) IS -4.9)     |
|REARRANGE TO 4.9T²-V0T+S=0|
|                          |
|                          |
+--------------------------+
+--------------------------+
|SOLVE QUADRATIC FOR T     |
|4.90T²-10.0T-15.0=0       |
|T=(-B+/-√(B²-4AC))/(2A)   |
|B²-4AC = 394              |
|T1 = -1.01 S              |
|T2 = 3.05 S               |
|T1<0 IS BEFORE THE THROW, |
|SO USE T2 (WHEN IT LANDS).|
|T TOTAL = 3.05 S          |
|                          |
+--------------------------+
+--------------------------+
|STEP 4  TOP TO GROUND     |
|AT THE TOP V IS 0, THEN IT|
|FALLS THE WHOLE MAX HEIGHT|
|ABOVE GROUND = 20.1 M     |
|S=(1/2)AT², SO T=√(2S/A)  |
|T=√(2(-20.1)/(-9.8))      |
|(USES UNROUNDED HEIGHT)   |
|T FROM TOP = 2.03 S       |
|CHECK- T TO TOP PLUS THIS |
|IS ABOUT T TOTAL (ROUNDED)|
+--------------------------+
+--------------------------+
|STEP 5  IMPACT VELOCITY   |
|USE VF²=V0²+2AS (NO T)    |
|VF²=(10.0)²               |
|   +2(-9.8)(-15.0)        |
|VF² IS 394                |
|IT MOVES DOWN, SO VF IS   |
|THE NEGATIVE ROOT.        |
|VF=-√(394)                |
|(USES UNROUNDED VF²)      |
|VF = -19.8 M/S (DOWN)     |
+--------------------------+
+--------------------------+
|SUMMARY (UP FROM HEIGHT)  |
|V0 = 10.0 M/S (UP)        |
|T TO TOP = 1.02 S         |
|MAX HEIGHT REACHED-       |
|ABOVE LAUNCH = 5.10 M     |
|ABOVE GROUND = 20.1 M     |
|T FROM TOP = 2.03 S       |
|T TOTAL = 3.05 S          |
|VF = -19.8 M/S (DOWN)     |
|                          |
+--------------------------+
```

## C. Horizontal launch: H = 20 m, speed 15 m/s (HORIZONTAL LAUNCH > 1 GIVEN H AND SPEED V)

Menu choices: HORIZONTAL LAUNCH > GIVEN H AND SPEED V > QUIT TO MAIN MENU

Typed: HEIGHT H (M)= 20; SPEED V (M/S)= 15

```
+--------------------------+
|STEP 1  TIME TO FALL      |
|VERTICAL- V0Y IS 0 AND A  |
|IS -9.8 M/S². IT ENDS H   |
|BELOW THE START, SO       |
|S = -20.0 M               |
|USE S=V0YT+(1/2)AT²       |
|-20.0=0+(1/2)(-9.8)T²     |
|T=√(2H/9.8)               |
|T=√(2(20.0)/9.8)          |
|T FLIGHT = 2.02 S         |
+--------------------------+
+--------------------------+
|STEP 2  RANGE             |
|HORIZONTAL- A IS 0, SO VX |
|STAYS V THE WHOLE TIME.   |
|X AND Y SHARE THE SAME T. |
|RANGE=VX*T                |
|RANGE=(15.0)(2.02)        |
|RANGE = 30.3 M            |
|(CALC KEEPS ALL DIGITS)   |
|                          |
|                          |
+--------------------------+
+--------------------------+
|STEP 3  FINAL VX AND VY   |
|HORIZONTAL- VX NEVER      |
|CHANGES (A IS 0), SO      |
|VFX = 15.0 M/S            |
|VERTICAL- USE VF=V0+AT    |
|VFY=0+(-9.8)(2.02)        |
|VFY = -19.8 M/S (DOWN)    |
|                          |
|                          |
|                          |
+--------------------------+
+--------------------------+
|STEP 4  IMPACT SPEED/ANGLE|
|SPEED=√(VFX²+VFY²)        |
|SPEED=√(15.0²+19.8²)      |
|HIT SPEED = 24.8 M/S      |
|ANGLE BELOW HORIZONTAL-   |
|ANGLE=TAN⁻1(|VFY|/VFX)    |
|ANGLE=TAN⁻1(19.8/15.0)    |
|ANGLE = 52.9° BELOW       |
|                          |
|                          |
+--------------------------+
+--------------------------+
|SUMMARY (HORIZONTAL)      |
|H = 20.0 M                |
|T FLIGHT = 2.02 S         |
|VX = 15.0 M/S             |
|RANGE = 30.3 M            |
|VFX = 15.0 M/S            |
|VFY = -19.8 M/S (DOWN)    |
|HIT SPEED = 24.8 M/S      |
|ANGLE = 52.9° BELOW       |
|                          |
+--------------------------+
```

## D. Angled launch: 25.0 m/s at 50°, level ground (height 0)

Menu choices: ANGLED LAUNCH > QUIT TO MAIN MENU

Typed: SPEED V0 (M/S)= 25; ANGLE (DEG)= 50; HEIGHT H (M)= 0

```
+--------------------------+
|STEP 1  COMPONENTS OF V0  |
|VX=V0COS(ANGLE)           |
|VX=(25.0)COS(50.0°)       |
|VX = 16.1 M/S             |
|V0Y=V0SIN(ANGLE)          |
|V0Y=(25.0)SIN(50.0°)      |
|V0Y = 19.2 M/S (UP)       |
|(CALC KEEPS ALL DIGITS)   |
|                          |
|                          |
+--------------------------+
+--------------------------+
|STEP 2  TIME TO TOP, MAX H|
|AT TOP VY IS 0- VF=V0+AT  |
|0=19.2+(-9.8)T            |
|T TOP = 1.95 S            |
|RISE ABOVE THE LAUNCH-    |
|USE VF²=V0²+2AS           |
|0=(19.2)²+2(-9.8)S        |
|RISE = 18.7 M             |
|H+RISE=0+18.7             |
|MAX H = 18.7 M            |
+--------------------------+
+--------------------------+
|STEP 3  FLIGHT TIME       |
|VERTICAL- IT LANDS H BELOW|
|THE LAUNCH, SO S IS -H-   |
|S = 0 M                   |
|USE S=V0YT+(1/2)AT²       |
|(1/2)A IS -4.9, SO        |
|0=19.2T-4.9T²             |
|4.9T²-V0YT-H=0 (QUADRATIC)|
|SOLVE IT FOR T (NEXT).    |
|                          |
+--------------------------+
+--------------------------+
|SOLVE QUADRATIC FOR T     |
|4.90T²-19.2T+0=0          |
|T=(-B+/-√(B²-4AC))/(2A)   |
|B²-4AC = 367              |
|T1 = 0 S                  |
|T2 = 3.91 S               |
|T1 IS 0 (THE LAUNCH), SO  |
|IT LANDS AT T2-           |
|T FLIGHT = 3.91 S         |
|                          |
+--------------------------+
+--------------------------+
|STEP 4  RANGE (HORIZONTAL)|
|HORIZONTAL- A IS 0, SO VX |
|NEVER CHANGES (VFX IS VX).|
|VX = 16.1 M/S             |
|RANGE=VX*T                |
|RANGE=(16.1)(3.91)        |
|RANGE = 62.8 M            |
|LEVEL GROUND- T=2V0Y/9.8  |
|AND MAX RANGE IS AT 45°.  |
|                          |
+--------------------------+
+--------------------------+
|STEP 5  VFY AT IMPACT     |
|VERTICAL- USE VF=V0+AT    |
|VFY=19.2+(-9.8)(3.91)     |
|VFY = -19.2 M/S (DOWN)    |
|(- MEANS MOVING DOWNWARD) |
|                          |
|                          |
|                          |
|                          |
|                          |
+--------------------------+
+--------------------------+
|STEP 6  IMPACT SPEED/ANGLE|
|SPEED=√(VFX²+VFY²)        |
|SPEED=√(16.1²+19.2²)      |
|HIT SPEED = 25.0 M/S      |
|ANGLE BELOW HORIZONTAL-   |
|ANGLE=TAN⁻1(|VFY|/VFX)    |
|ANGLE=TAN⁻1(19.2/16.1)    |
|ANGLE = 50.0° BELOW       |
|                          |
|                          |
+--------------------------+
+--------------------------+
|SUMMARY (ANGLED LAUNCH)   |
|VX = 16.1 M/S             |
|V0Y = 19.2 M/S (UP)       |
|T TOP = 1.95 S            |
|MAX H = 18.7 M            |
|T FLIGHT = 3.91 S         |
|RANGE = 62.8 M            |
|HIT SPEED = 25.0 M/S      |
|ANGLE = 50.0° BELOW       |
|                          |
+--------------------------+
```

## E. Throw lab (work backward): H = 2.0 m, t = 2.4 s, range 50 yd (THROW LAB > 2 RANGE IN YARDS)

Menu choices: THROW LAB (BACKWARD) > RANGE IN YARDS > QUIT TO MAIN MENU

Typed: HEIGHT H (M)= 2; TIME T (S)= 2.4; RANGE (YD)= 50

```
+--------------------------+
|STEP 1  VX (HORIZONTAL)   |
|YARDS TO METERS- DIVIDE   |
|BY 1.0936 (1 M=1.0936 YD) |
|RANGE=50.0/1.0936         |
|RANGE = 45.7 M            |
|HORIZONTAL- A IS 0, SO    |
|VX=RANGE/T                |
|VX=45.7/2.40              |
|VX = 19.1 M/S             |
|(CALC KEEPS ALL DIGITS)   |
+--------------------------+
+--------------------------+
|STEP 2  V0Y (VERTICAL)    |
|IT ENDS H BELOW THE START,|
|SO S IS -H. A IS -9.8.    |
|S = -2.00 M               |
|USE S=V0YT+(1/2)AT²       |
|(1/2)A IS -4.9, SO        |
|V0Y=(S+4.9T²)/T           |
|=(-2.00+4.9(2.40)²)/2.40  |
|V0Y = 10.9 M/S (UP)       |
|                          |
+--------------------------+
+--------------------------+
|STEP 3  LAUNCH SPEED/ANGLE|
|V0=√(VX²+V0Y²)            |
|V0=√(19.1²+10.9²)         |
|V0 = 22.0 M/S             |
|ANGLE FROM HORIZONTAL-    |
|ANGLE=TAN⁻1(V0Y/VX)       |
|ANGLE=TAN⁻1(10.9/19.1)    |
|ANGLE = 29.8° (ABOVE)     |
|                          |
|                          |
+--------------------------+
+--------------------------+
|SUMMARY (THROW LAB)       |
|H = 2.00 M                |
|T FLIGHT = 2.40 S         |
|RANGE = 45.7 M            |
|(FROM 50.0 YD)            |
|VX = 19.1 M/S             |
|V0Y = 10.9 M/S (UP)       |
|V0 = 22.0 M/S             |
|ANGLE = 29.8° (ABOVE)     |
|                          |
+--------------------------+
```

## F. River crossing: boat 6.00 m/s, river 3.00 m/s, width 120 m (MORE > 1)

Menu choices: MORE > > RIVER CROSSING > BACK > QUIT TO MAIN MENU

Typed: VB (M/S)= 6; VR (M/S)= 3; W (M)= 120

```
+--------------------------+
|STEP 1  CROSSING TIME     |
|ACROSS AND DOWNSTREAM     |
|MOTIONS ARE INDEPENDENT.  |
|THE BOAT IS AIMED ACROSS, |
|SO ONLY VB TAKES IT ACROSS|
|T=W/VB                    |
|T=120/6.00                |
|T = 20.0 S                |
|                          |
|                          |
+--------------------------+
+--------------------------+
|STEP 2  DRIFT             |
|MEANWHILE THE RIVER       |
|CARRIES THE BOAT          |
|DOWNSTREAM AT VR.         |
|DRIFT=VR*T                |
|DRIFT=(3.00)(20.0)        |
|DRIFT = 60.0 M            |
|(DOWNSTREAM OF THE POINT  |
|STRAIGHT ACROSS)          |
|                          |
+--------------------------+
+--------------------------+
|STEP 3  RESULTANT SPEED   |
|VB IS ACROSS AND VR IS    |
|DOWNSTREAM- THEY ARE      |
|PERPENDICULAR, SO USE     |
|PYTHAGORAS.               |
|V=√(VB²+VR²)              |
|V=√(6.00²+3.00²)          |
|V RESULT = 6.71 M/S       |
|(SPEED SEEN FROM SHORE)   |
|                          |
+--------------------------+
+--------------------------+
|STEP 4  PATH ANGLE        |
|TAN(ANGLE)=VR/VB          |
|ANGLE=TAN⁻1(3.00/6.00)    |
|FROM ACROSS = 26.6°       |
|(TOWARD DOWNSTREAM). FROM |
|THE BANK IT IS 90-ANGLE.  |
|FROM BANK = 63.4°         |
|HEADING IS STRAIGHT ACROSS|
|BUT THE PATH IS SLANTED.  |
|                          |
+--------------------------+
+--------------------------+
|STEP 5  HEADING UPSTREAM  |
|TO LAND DIRECTLY ACROSS,  |
|THE UPSTREAM PART OF VB   |
|MUST CANCEL VR, SO        |
|VB SIN(ANGLE)=VR          |
|ANGLE=SIN⁻1(3.00/6.00)    |
|FROM ACROSS = 30.0°       |
|FROM BANK = 60.0°         |
|(AIM UPSTREAM)            |
|                          |
+--------------------------+
+--------------------------+
|STEP 6  NEW CROSSING TIME |
|ONLY THE ACROSS PART OF   |
|VB MOVES THE BOAT ACROSS- |
|V ACROSS=VB COS(ANGLE)    |
|=√(VB²-VR²)               |
|=√(6.00²-3.00²)           |
|V ACROSS = 5.20 M/S       |
|T=W/V ACROSS              |
|T=120/5.20                |
|T = 23.1 S                |
+--------------------------+
+--------------------------+
|SUMMARY 1/2 (AIMED ACROSS)|
|T = 20.0 S                |
|DRIFT = 60.0 M            |
|V RESULT = 6.71 M/S       |
|PATH ANGLE (DOWNSTREAM)-  |
|FROM ACROSS = 26.6°       |
|FROM BANK = 63.4°         |
|HEADING- STRAIGHT ACROSS, |
|NOT ALONG THE PATH.       |
|                          |
+--------------------------+
+--------------------------+
|SUMMARY 2/2 (LAND ACROSS) |
|HEADING (UPSTREAM)-       |
|FROM ACROSS = 30.0°       |
|FROM BANK = 60.0°         |
|PATH- STRAIGHT ACROSS,    |
|NOT ALONG THE HEADING.    |
|V ACROSS = 5.20 M/S       |
|(SPEED SEEN FROM SHORE)   |
|T = 23.1 S                |
|DRIFT = 0 M               |
+--------------------------+
```

## G. Chase problem: car 30 m/s, no head start, police 3.0 m/s² from rest, no delay (MORE > 2)

Menu choices: MORE > > CHASE PROBLEM > BACK > QUIT TO MAIN MENU

Typed: V1 (M/S)= 30; D0 (M)= 0; A (M/S²)= 3; TD (S)= 0

```
+--------------------------+
|CHASE PROBLEM             |
|CAR 1- CONSTANT SPEED V1. |
|CAR 2- STARTS FROM REST   |
|WITH ACCELERATION A.      |
|TIME 0- CAR 1 IS D0 AHEAD |
|OF CAR 2 (D0 IS 0 IF THEY |
|ARE SIDE BY SIDE).        |
|CAR 2 WAITS TD SECONDS    |
|AFTER TIME 0 (0 IF NONE). |
|BOTH GO THE SAME WAY.     |
+--------------------------+
+--------------------------+
|STEP 1  SET X1=X2         |
|T FROM TIME 0, X FROM THE |
|START POINT OF CAR 2.     |
|CAR 1- X1=D0+V1*T         |
|CAR 2- X2=(1/2)A(T-TD)²   |
|LET U=T-TD (TIME SINCE    |
|CAR 2 STARTED), T=U+TD.   |
|X1=X2 GIVES               |
|D0+V1(U+TD)=(1/2)AU²      |
|(1/2)AU²-V1*U-(D0+V1*TD)=0|
+--------------------------+
+--------------------------+
|STEP 2  PUT IN NUMBERS    |
|LEAD OF CAR 1 WHEN CAR 2  |
|STARTS IS D0+V1*TD.       |
|LEAD=0+(30.0)(0)          |
|LEAD = 0 M                |
|(1/2)(3.00)U²-30.0U-0=0   |
|ON THE NEXT SCREEN T IS U |
|(TIME AFTER CAR 2 STARTS).|
|                          |
|                          |
+--------------------------+
+--------------------------+
|SOLVE QUADRATIC FOR T     |
|1.50T²-30.0T+0=0          |
|T=(-B+/-√(B²-4AC))/(2A)   |
|B²-4AC = 900              |
|T1 = 0 S                  |
|T2 = 20.0 S               |
|T1 IS 0, THE START (SIDE  |
|BY SIDE), NOT A CATCH-UP. |
|SO U = 20.0 S             |
|                          |
+--------------------------+
+--------------------------+
|STEP 3  CATCH-UP TIME     |
|TD IS 0, SO CAR 2 STARTS  |
|AT TIME 0 AND T=U.        |
|T = 20.0 S                |
|                          |
|                          |
|                          |
|                          |
|                          |
|                          |
+--------------------------+
+--------------------------+
|STEP 4  DISTANCE          |
|CAR 2 SPEEDS UP FROM REST |
|FOR U SECONDS-            |
|S=(1/2)AU²                |
|S=(1/2)(3.00)(20.0)²      |
|S = 600 M                 |
|(FROM CAR 2 START POINT)  |
|CHECK- CAR 1 X1=D0+V1*T   |
|X1 = 600 M                |
|                          |
+--------------------------+
+--------------------------+
|STEP 5  CAR 2 SPEED       |
|VF=V0+AT WITH V0 IS 0,    |
|SO V2=AU                  |
|V2=(3.00)(20.0)           |
|V2 = 60.0 M/S             |
|V2/V1=60.0/30.0           |
|V2/V1 = 2.00              |
|RULE- FROM REST, SIDE BY  |
|SIDE, IT CATCHES UP AT 2X |
|THE SPEED OF CAR 1.       |
+--------------------------+
+--------------------------+
|SUMMARY (CHASE)           |
|T = 20.0 S                |
|(CATCH-UP TIME)           |
|S = 600 M                 |
|(FROM CAR 2 START POINT)  |
|V2 = 60.0 M/S             |
|V2/V1 = 2.00              |
|                          |
|                          |
|                          |
+--------------------------+
```

## H. Vector components: 20 m at 30° to X and Y (MORE > 3 > 1 MAG+ANGLE > 1 DISPLACEMENT)

Menu choices: MORE > > VECTOR COMPONENTS > MAG+ANGLE TO X,Y > DISPLACEMENT (M) > BACK > BACK > QUIT TO MAIN MENU

Typed: MAGNITUDE= 20; ANGLE (DEG)= 30

```
+--------------------------+
|STEP 1  X COMPONENT       |
|ANGLE IS FROM +X, SO X IS |
|THE ADJACENT SIDE (COS)-  |
|X=MAGNITUDE*COS(ANGLE)    |
|X=(20.0)COS(30.0°)        |
|X = 17.3 M (RIGHT)        |
|(+X IS RIGHT, -X IS LEFT) |
|                          |
|                          |
|                          |
+--------------------------+
+--------------------------+
|STEP 2  Y COMPONENT       |
|ANGLE IS FROM +X, SO Y IS |
|THE OPPOSITE SIDE (SIN)-  |
|Y=MAGNITUDE*SIN(ANGLE)    |
|Y=(20.0)SIN(30.0°)        |
|Y = 10.0 M (UP)           |
|(+Y IS UP, -Y IS DOWN)    |
|                          |
|                          |
|                          |
+--------------------------+
+--------------------------+
|SUMMARY  MAG,ANGLE TO X,Y |
|MAGNITUDE = 20.0 M        |
|ANGLE = 30.0°             |
|(COUNTERCLOCKWISE FROM +X)|
|X = 17.3 M (RIGHT)        |
|Y = 10.0 M (UP)           |
|                          |
|                          |
|                          |
|                          |
+--------------------------+
```

## I. Averages: 2 legs: 100 m forward in 10 s, 50 m back in 5 s (MORE > 4)

Menu choices: MORE > > AVG SPEED/VELOCITY > BACK > QUIT TO MAIN MENU

Typed: NUMBER OF LEGS= 2; DISTANCE (M)= 100; DIRECTION (1/-1)= 1; TIME (S)= 10; DISTANCE (M)= 50; DIRECTION (1/-1)= ⁻1; TIME (S)= 5

```
+--------------------------+
|STEP 1  TOTAL DISTANCE    |
|ADD EVERY LEG AS POSITIVE |
|(DIRECTION DOES NOT       |
|MATTER FOR DISTANCE)-     |
|=100+50.0                 |
|DISTANCE = 150 M          |
|                          |
|                          |
|                          |
|                          |
+--------------------------+
+--------------------------+
|STEP 2  DISPLACEMENT      |
|ADD THE LEGS WITH THEIR   |
|SIGNS (- LEGS SUBTRACT)-  |
|S=100-50.0                |
|DISPLACEMENT = 50.0 M     |
|(IN THE + DIRECTION)      |
|                          |
|                          |
|                          |
|                          |
+--------------------------+
+--------------------------+
|STEP 3  TOTAL TIME        |
|ADD THE TIMES OF ALL LEGS-|
|=10.0+5.00                |
|TOTAL TIME = 15.0 S       |
|                          |
|                          |
|                          |
|                          |
|                          |
|                          |
+--------------------------+
+--------------------------+
|STEP 4  AVERAGE SPEED     |
|AVG SPEED=DISTANCE/TIME   |
|=150/15.0                 |
|AVG SPEED = 10.0 M/S      |
|(SPEED HAS NO DIRECTION,  |
|SO IT IS NEVER NEGATIVE)  |
|                          |
|                          |
|                          |
|                          |
+--------------------------+
+--------------------------+
|STEP 5  AVERAGE VELOCITY  |
|AVG VEL=DISPLACEMENT/TIME |
|=50.0/15.0                |
|AVG VEL = 3.33 M/S        |
|(IN THE + DIRECTION)      |
|                          |
|                          |
|                          |
|                          |
|                          |
+--------------------------+
+--------------------------+
|SUMMARY  AVERAGES         |
|DISTANCE = 150 M          |
|DISPLACEMENT = 50.0 M     |
|TOTAL TIME = 15.0 S       |
|AVG SPEED = 10.0 M/S      |
|AVG VEL = 3.33 M/S        |
|(IN THE + DIRECTION)      |
|                          |
|                          |
|                          |
+--------------------------+
```

## J. Factor of change: stopping distance 20 m, speed x3 (MORE > 5 > 1 S PROP TO V²)

Menu choices: MORE > > FACTOR OF CHANGE > S PROP TO V² (STOP) > BACK > BACK > QUIT TO MAIN MENU

Typed: OLD S (M)= 20; V FACTOR K= 3

```
+--------------------------+
|STEP 1  MULTIPLIER        |
|V IS MULTIPLIED BY K, SO  |
|S IS MULTIPLIED BY K²     |
|MULTIPLIER=K²             |
|=(3.00)²                  |
|MULTIPLIER = 9.00         |
|                          |
|                          |
|                          |
|                          |
+--------------------------+
+--------------------------+
|STEP 2  NEW S             |
|NEW S=OLD S*K²            |
|NEW S=(20.0)(9.00)        |
|NEW S = 180 M             |
|                          |
|                          |
|                          |
|                          |
|                          |
|                          |
+--------------------------+
+--------------------------+
|SUMMARY  FACTOR OF CHANGE |
|S PROP TO V²              |
|OLD S = 20.0 M            |
|V FACTOR K = 3.00         |
|MULTIPLIER = 9.00         |
|NEW S = 180 M             |
|3.00X V GIVES 9.00X S     |
|                          |
|                          |
|                          |
+--------------------------+
```

## K. Lab tools: ramp slope 0.40 (MORE > 6 > 1 RAMP)

Menu choices: MORE > > LAB TOOLS > RAMP A FROM SLOPE > BACK > BACK > QUIT TO MAIN MENU

Typed: SLOPE (M/S²)= .4

```
+--------------------------+
|STEP 1  ACCELERATION      |
|S=(1/2)AT² IS A LINE      |
|Y=(SLOPE)X WITH Y=S AND   |
|X=T², SO SLOPE=A/2 AND    |
|A=2*SLOPE                 |
|A=2(0.400)                |
|A = 0.800 M/S²            |
|                          |
|                          |
|                          |
+--------------------------+
+--------------------------+
|SUMMARY  RAMP             |
|SLOPE = 0.400 M/S²        |
|A = 0.800 M/S²            |
|(ALONG THE RAMP)          |
|                          |
|                          |
|                          |
|                          |
|                          |
|                          |
+--------------------------+
```

## K. Lab tools: percent difference of 2.10 and 1.95 (MORE > 6 > 2)

Menu choices: MORE > > LAB TOOLS > PERCENT DIFFERENCE > BACK > BACK > QUIT TO MAIN MENU

Typed: VALUE A= 2.1; VALUE B= 1.95

```
+--------------------------+
|STEP 1  AVERAGE           |
|AVG=(A+B)/2               |
|AVG=(2.10+1.95)/2         |
|AVG = 2.03                |
|                          |
|                          |
|                          |
|                          |
|                          |
|                          |
+--------------------------+
+--------------------------+
|STEP 2  PERCENT DIFFERENCE|
|%DIFF=|A-B|/|AVG|*100     |
|=|A-B|/(|A+B|/2)*100      |
|=|2.10-1.95|/(4.05/2)*100 |
|=0.150/(4.05/2)*100       |
|PERCENT DIFF = 7.41 %     |
|(UNROUNDED VALUES USED)   |
|                          |
|                          |
|                          |
+--------------------------+
+--------------------------+
|SUMMARY  PERCENT DIFF     |
|VALUE A = 2.10            |
|VALUE B = 1.95            |
|AVG = 2.03                |
|PERCENT DIFF = 7.41 %     |
|                          |
|                          |
|                          |
|                          |
|                          |
+--------------------------+
```
