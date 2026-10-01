# Student's redesign request (verbatim excerpts — the source of truth for behavior)

MY GOAL IS NOT A STUDY GUIDE. MY GOAL IS THIS:
I look at a quiz question. I choose the option on my calculator that LOOKS LIKE the question.
I type the numbers I see. The calculator tells me the ANSWER I should write.

I am a beginner with the TI-84. Assume I do NOT know how to: factor an inside expression first;
identify a,b,h,k; remember transformation rules; remember power-function parity rules; remember
inverse formulas; remember domain rules; navigate complicated calculator menus.
THE PROGRAM MUST DO AS MUCH OF THAT THINKING AS POSSIBLE.

PHASE 1 — For EVERY practice problem: problem number, what information appears in the question,
what answer the student is expected to give, which calculator solver will handle it, what the
student must enter, what the calculator will output. THE PROGRAM IS NOT FINISHED IF A PRACTICE
PROBLEM HAS NO SOLVER PATH. For graph problems, it is acceptable for the student to manually enter
the labeled coordinates or function values shown on the paper. It is NOT acceptable to just show a
formula and make the student finish the problem themselves when the TI-84 can reasonably calculate it.

MAIN MENU answers "WHAT DOES YOUR PROBLEM LOOK LIKE?": 1:F+G OR F/G 2:F(G(X)) 3:F^-1 4:A*F(BX+C)+K
5:ABS BARS 6:KX^P / ROOTS 7:DECOMPOSE. Each submenu then asks "WHAT DO THEY WANT?".
Transformations: 1:LIST CHANGES 2:NEW POINT 3:DOMAIN/RANGE 4:WRITE EQUATION.
Powers: 1:FIND K,P 2:SYMMETRY/QUADS 3:ALL PROPERTIES 4:BUILD EQUATION.
Inverses: 1:FIND INVERSE 2:VERIFY TWO FUNCS 3:DOMAIN/RANGE 4:HLT.

GLOBAL UI RULE: every solver: 1. ask the fewest possible questions 2. calculate 3. first result
screen begins with ANSWER: 4. show exactly what the student should write 5. only AFTER the answer,
optionally allow 1:WHY 2:AGAIN 3:HOME. DO NOT show lessons before giving the answer. NO walls of
text. NO long reference pages. NO hunting through formulas. Keep screens short.

USE RAW EQUATION COEFFICIENTS: for A*F(BX+C)+K ask A, B, C, K directly and compute H=-C/B inside.

SOLVER 1 — FUNCTION OPERATIONS / DOMAIN: support the function families the materials use
(linear, quadratic, polynomial where needed, square-root, rational linear-over-linear,
reciprocal/rational forms used in the guide, domains supplied directly as intervals, functions
supplied as graphs where the user enters values/zeros/domains). Ask the TYPE of f and g, then
coefficients. Operations add/subtract/multiply/divide: calculate as much of the requested
expression as is practical. DOMAIN: sum/difference/product = intersection; quotient = intersection
and remove denominator zeros. NEVER lose original restrictions after simplification. Output like
"ANSWER: ALL REAL EXCEPT X=0,2,5" or intervals with open/closed ends. Support a denominator that is
zero on an interval when the problem gives that information from a graph.

SOLVER 2 — COMPOSITION: support every composition structure used in the PDFs (linear, quadratic,
rational linear-over-linear, reciprocal forms, square-root functions, quadratic inside a square
root, graph-value compositions). Ask which functions are f and g using templates, then
1:F(G(X)) 2:G(F(X)). Output ANSWER: [simplified result] and DOMAIN: [exact domain]. Preserve
restrictions that disappear during simplification. For square-root compositions solve the required
linear/quadratic inequality. For graph compositions ask only the values needed (G(5)=? then
F(that value)=?) and output the final answer.

SOLVER 3 — DECOMPOSITION: template solvers for every decomposition structure in the guide
((AX+B)^N, sqrt(AX+B), absolute value of a chunk plus a constant, 1/(chunk)^N, polynomial in a
repeated inner chunk, exponential chunks, rational expressions with a nested chunk). Ask what the
expression LOOKS LIKE, then coefficients/exponents. Output ANSWER: G(X)=... F(X)=...; two
decompositions when the guide expects two. Never g(x)=x.

SOLVER 4 — INVERSES: actual inverse solvers: linear, rational (AX+B)/(CX+D), reciprocal-linear
A/(BX+C), power/cube forms, cube root forms, square root (with domain/range restrictions),
fractional power forms used in the guide. VERIFY TWO FUNCTIONS: compose both directions, output
"YES, INVERSES" or "NO, NOT INVERSES" and which composition fails. INVERSE DOMAIN/RANGE: swap,
preserving open/closed ends. HLT: answer automatically for families classifiable from structure;
for graphs ask whether any horizontal line hits twice.

SOLVER 5 — TRANSFORMATIONS (done).

SOLVER 6 — ABSOLUTE VALUE: |F(X)|, F(|X|), A|F(BX+C)+D|+K, A*F(|BX+C|)+K and combinations in the
guide. For point/graph questions the user enters important original points (corners, endpoints,
x-intercepts, any required y-intercept); calculate the transformed points. |F(X)|: replace y with
abs(y). F(|X|): use the x>=0 portion and mirror it. Apply operations in the exact order the source
materials require. Output transformed important points, domain, range. Domain/range-only questions
ask only the needed interval information. Domain [2,7] under F(|X|) → [-7,-2] U [2,7].
Do not include F(-|X|).

SOLVER 7 — POWER FUNCTIONS: 1:FIND K,P 2:PROPERTIES 3:BUILD FUNCTION. FIND K,P: wizard for the
disguised forms used in the PDFs (K*nth-root(X^M), K/nth-root(X^M), K/(X*sqrt(X)), sqrt(C*X^M),
K/X^N, every other disguise in the practice/examples). Ask simple structural questions (X IN
DENOM? ROOT INDEX? POWER ON X? NUMBER UNDER ROOT? OUTSIDE COEFFICIENT?), pull constants out of
radicals when exact, combine powers, make denominator exponents negative, reduce p.
Example Y=-4/(cube root(X^2)) → K=-4, P=-2/3. PROPERTIES: ask K, A, B; reduce; output P,
SYMMETRY, QUADRANTS, DOMAIN, RANGE, INCREASING, DECREASING, BOUNDED ABOVE/BELOW, ASYMPTOTES,
END BEHAVIOR, CONTINUITY using the class rules (negative numerators, even/odd numerator and
denominator, k<0 reflection, p>1, 0<p<1, p<0, x=0 exclusion; A=-2 is EVEN). BUILD FUNCTION: ask
quadrants, increasing/decreasing, curves up/down, asymptotes, sign of k → output ONE valid function.

GRAPH QUESTIONS: the TI-84 cannot see the graph; ask only what can be read (F(3)=?, points X1,Y1...,
left/right endpoint, open/closed, zeros, zero intervals) then do all remaining calculations.

EXACT ANSWERS: never turn -17/4 into -4.25.

BEGINNER UX: every prompt makes sense without a manual; remind once to use (-) for negatives; every
solver ends with 1:AGAIN 2:HOME; never make the user restart; no walls of text; answer first.

TESTING: for EVERY practice problem in Sections 1–7, enter the values, record output, compare to
the official Section 9 solution, fix until it matches. Also test every worked example.

Regression tests for power: K=1 A=3 B=7 → ODD, QI,QIII; K=1 A=4 B=7 → EVEN, QI,QII; K=1 A=3 B=2 →
NEGATIVE X UNDEFINED, QI; K=-1 A=4 B=7 → EVEN, QIII,QIV; K=1 A=-2 B=1 → EVEN, X=0 EXCLUDED,
ASYMPTOTES X=0,Y=0, QI,QII. Power disguise Y=-4/(cube root(X^2)) → K=-4, P=-2/3.
