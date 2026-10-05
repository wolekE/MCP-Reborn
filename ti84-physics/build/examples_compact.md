**A. VOVFSTA solver** (v0 = 8.0 m/s, a = 1.5 m/s², s = 120 m; vf and t unknown (999))

Typed: `V0 (M/S)= 8`, `VF (M/S)= 999`, `S (M)= 120`, `T (S)= 999`, `A (M/S²)= 1.5`

```
+--------------------------+
|SUMMARY                   |
|V0 = 8.00 M/S             |
|VF = 20.6 M/S             |
|S = 120 M                 |
|T = 8.39 S                |
|A = 1.50 M/S²             |
|T FROM S=V0T+(1/2)AT²     |
|VF FROM VF=V0+AT          |
+--------------------------+
```

**B. Free fall** (thrown up at 10 m/s from a 15 m roof (FREE FALL > 4 THROWN UP (HEIGHT H)))

Typed: `HEIGHT H (M)= 15`, `V0 UP (M/S)= 10`

```
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
+--------------------------+
```

**C. Horizontal launch** (H = 20 m, speed 15 m/s (HORIZONTAL LAUNCH > 1 GIVEN H AND SPEED V))

Typed: `HEIGHT H (M)= 20`, `SPEED V (M/S)= 15`

```
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
+--------------------------+
```

**D. Angled launch** (25.0 m/s at 50°, level ground (height 0))

Typed: `SPEED V0 (M/S)= 25`, `ANGLE (DEG)= 50`, `HEIGHT H (M)= 0`

```
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
+--------------------------+
```

**E. Throw lab (work backward)** (H = 2.0 m, t = 2.4 s, range 50 yd (THROW LAB > 2 RANGE IN YARDS))

Typed: `HEIGHT H (M)= 2`, `TIME T (S)= 2.4`, `RANGE (YD)= 50`

```
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
+--------------------------+
```

**F. River crossing** (boat 6.00 m/s, river 3.00 m/s, width 120 m (MORE > 1))

Typed: `VB (M/S)= 6`, `VR (M/S)= 3`, `W (M)= 120`

```
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

**G. Chase problem** (car 30 m/s, no head start, police 3.0 m/s² from rest, no delay (MORE > 2))

Typed: `V1 (M/S)= 30`, `D0 (M)= 0`, `A (M/S²)= 3`, `TD (S)= 0`

```
+--------------------------+
|SUMMARY (CHASE)           |
|T = 20.0 S                |
|(CATCH-UP TIME)           |
|S = 600 M                 |
|(FROM CAR 2 START POINT)  |
|V2 = 60.0 M/S             |
|V2/V1 = 2.00              |
+--------------------------+
```

**H. Vector components** (20 m at 30° to X and Y (MORE > 3 > 1 MAG+ANGLE > 1 DISPLACEMENT))

Typed: `MAGNITUDE= 20`, `ANGLE (DEG)= 30`

```
+--------------------------+
|SUMMARY  MAG,ANGLE TO X,Y |
|MAGNITUDE = 20.0 M        |
|ANGLE = 30.0°             |
|(COUNTERCLOCKWISE FROM +X)|
|X = 17.3 M (RIGHT)        |
|Y = 10.0 M (UP)           |
+--------------------------+
```

**I. Averages** (2 legs: 100 m forward in 10 s, 50 m back in 5 s (MORE > 4))

Typed: `NUMBER OF LEGS= 2`, `DISTANCE (M)= 100`, `DIRECTION (1/-1)= 1`, `TIME (S)= 10`, `DISTANCE (M)= 50`, `DIRECTION (1/-1)= ⁻1`, `TIME (S)= 5`

```
+--------------------------+
|SUMMARY  AVERAGES         |
|DISTANCE = 150 M          |
|DISPLACEMENT = 50.0 M     |
|TOTAL TIME = 15.0 S       |
|AVG SPEED = 10.0 M/S      |
|AVG VEL = 3.33 M/S        |
|(IN THE + DIRECTION)      |
+--------------------------+
```

**J. Factor of change** (stopping distance 20 m, speed x3 (MORE > 5 > 1 S PROP TO V²))

Typed: `OLD S (M)= 20`, `V FACTOR K= 3`

```
+--------------------------+
|SUMMARY  FACTOR OF CHANGE |
|S PROP TO V²              |
|OLD S = 20.0 M            |
|V FACTOR K = 3.00         |
|MULTIPLIER = 9.00         |
|NEW S = 180 M             |
|3.00X V GIVES 9.00X S     |
+--------------------------+
```

**K. Lab tools** (ramp slope 0.40 (MORE > 6 > 1 RAMP))

Typed: `SLOPE (M/S²)= .4`

```
+--------------------------+
|SUMMARY  RAMP             |
|SLOPE = 0.400 M/S²        |
|A = 0.800 M/S²            |
|(ALONG THE RAMP)          |
+--------------------------+
```

**K. Lab tools** (percent difference of 2.10 and 1.95 (MORE > 6 > 2))

Typed: `VALUE A= 2.1`, `VALUE B= 1.95`

```
+--------------------------+
|SUMMARY  PERCENT DIFF     |
|VALUE A = 2.10            |
|VALUE B = 1.95            |
|AVG = 2.03                |
|PERCENT DIFF = 7.41 %     |
+--------------------------+
```
