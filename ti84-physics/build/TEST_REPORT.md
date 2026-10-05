# Required test cases

Each case was run three ways: the Python reference implementation (`reference/*.py`), the
TI-Basic itself (the simulator executing **`PHYSICS.8xp`**, the file sent to the calculator,
through its real menus), and the expected value from the assignment. PASS means the TI screen
shows exactly the reference value at 3 significant figures and agrees with the expected value
at the precision it was given.

| Case | Quantity | Expected | Python reference (3 s.f.) | TI-Basic screen | Result |
|---|---|---|---|---|---|
| v0 = 8.0, a = 1.5, s = 120 (VOVFSTA) | vf | 20.6 | 20.6 | 20.6 | PASS |
| v0 = 8.0, a = 1.5, s = 120 (VOVFSTA) | t | 8.39 | 8.39 | 8.39 | PASS |
| Chase: car 30 m/s, police from rest 3.0 m/s² | t | 20 | 20.0 | 20.0 | PASS |
| Chase: car 30 m/s, police from rest 3.0 m/s² | s | 600 | 600 | 600 | PASS |
| Chase: car 30 m/s, police from rest 3.0 m/s² | police speed | 60 | 60.0 | 60.0 | PASS |
| Thrown up at 19.6 m/s | time to top | 2.0 | 2.00 | 2.00 | PASS |
| Thrown up at 19.6 m/s | max height | 19.6 | 19.6 | 19.6 | PASS |
| Dropped from 45 m | t | 3.03 | 3.03 | 3.03 | PASS |
| Dropped from 45 m | vf | -29.7 | -29.7 | -29.7 | PASS |
| Thrown up at 10 m/s from a 15 m roof | max above roof | 5.10 | 5.10 | 5.10 | PASS |
| Thrown up at 10 m/s from a 15 m roof | vf | -19.8 | -19.8 | -19.8 | PASS |
| Thrown up at 10 m/s from a 15 m roof | total t | 3.05 | 3.05 | 3.05 | PASS |
| Angled, level ground: 25.0 m/s at 50° | vx | 16.07 | 16.1 | 16.1 | PASS |
| Angled, level ground: 25.0 m/s at 50° | v0y | 19.15 | 19.2 | 19.2 | PASS |
| Angled, level ground: 25.0 m/s at 50° | T | 3.91 | 3.91 | 3.91 | PASS |
| Angled, level ground: 25.0 m/s at 50° | R | 62.8 | 62.8 | 62.8 | PASS |
| Angled, level ground: 25.0 m/s at 50° | hmax | 18.7 | 18.7 | 18.7 | PASS |
| Angled from a height: 5.0 m/s at 30° from 1.0 m | t | 0.774 | 0.774 | 0.774 | PASS |
| Angled from a height: 5.0 m/s at 30° from 1.0 m | x | 3.35 | 3.35 | 3.35 | PASS |
| Angled from a height: 4.9 m/s at 20° from 0.85 m | T | 0.621 | 0.621 | 0.621 | PASS |
| Angled from a height: 4.9 m/s at 20° from 0.85 m | R | 2.86 | 2.86 | 2.86 | PASS |
| Throw lab: H = 2.0 m, t = 2.4 s, range 50 yd | range | 45.7 | 45.7 | 45.7 | PASS |
| Throw lab: H = 2.0 m, t = 2.4 s, range 50 yd | vx | 19.05 | 19.1 | 19.1 | PASS |
| Throw lab: H = 2.0 m, t = 2.4 s, range 50 yd | v0y | 10.93 | 10.9 | 10.9 | PASS |
| Throw lab: H = 2.0 m, t = 2.4 s, range 50 yd | speed | 21.96 | 22.0 | 22.0 | PASS |
| Throw lab: H = 2.0 m, t = 2.4 s, range 50 yd | angle | 29.8 | 29.8 | 29.8 | PASS |
| River: boat 6.00 m/s, river 3.00 m/s (width 120 m) | resultant | 6.71 | 6.71 | 6.71 | PASS |
| River: boat 6.00 m/s, river 3.00 m/s (width 120 m) | path angle from straight across | 26.6 | 26.6 | 26.6 | PASS |
| Ramp: slope 0.40 | a | 0.80 | 0.800 | 0.800 | PASS |
| Percent difference of 2.10 and 1.95 | percent difference | 7.4 | 7.41 | 7.41 | PASS |

**30 of 30 values match.**
