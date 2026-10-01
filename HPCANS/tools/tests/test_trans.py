"""Transformations y = A*F(BX+C)+K (main menu 4). Study guide Section 5, cram sheet 5."""

BASE = ["t:4", "t:-4", "t:2", "t:-2", "t:-2", "t:1", "t:4", "t:3", "t:0", "k1"]  # base graph A,B,C,D, solid ends
BASE_SAVED = {"ʟBX": [-4, -2, 1, 3], "ʟBY": [2, -2, 4, 0], "ʟBC": [1, 1]}


def changes(cid, src, a, b, c, k, expect, official, path=None):
    return dict(id=cid, source=src, actions=["k4", "k1", f"t:{a}", f"t:{b}", f"t:{c}", f"t:{k}", "k2"],
                expect=expect, official=official,
                path=path or f"4 → 1:LIST THE CHANGES; A={a or 'ENTER'} B={b or 'ENTER'} C={c or 'ENTER'} K={k or 'ENTER'}")


def dr(cid, src, a, b, c, k, dom, rng, expect, official):
    acts = ["k4", "k3", f"t:{a}", f"t:{b}", f"t:{c}", f"t:{k}", "k1",
            f"t:{dom[0]}", f"t:{dom[1]}", "k1", f"t:{rng[0]}", f"t:{rng[1]}", "k1", "k2"]
    return dict(id=cid, source=src, actions=acts, expect=expect, official=official,
                path=f"4 → 3:NEW DOMAIN AND RANGE; A={a} B={b} C={c} K={k}; 1:D AND R; "
                     f"D {dom[0]} to {dom[1]} [ ]; R {rng[0]} to {rng[1]} [ ]")


CASES = [
    changes("REG-T1", "H(X)=-3F(X-2)+1", "-3", "", "-2", "1",
            ["REFLECT X-AXIS", "VERT STRETCH 3", "RIGHT 2", "UP 1"], "REFLECT X-AXIS, VERT STRETCH 3, RIGHT 2, UP 1"),
    changes("REG-T2", "F(4X-8) (student does not factor)", "", "4", "-8", "",
            ["HORIZ COMPRESS 1/4", "RIGHT 2"], "HORIZ COMPRESS 1/4, RIGHT 2"),
    dict(id="REG-T3", source="2F((-4/3)X+4)-3, old point (-4,2)",
         actions=["k4", "k2", "t:2", "t:-4/3", "t:4", "t:-3", "k1", "t:-4", "t:2", "k2"],
         expect=["(6,1)"], official="(6,1)",
         path="4 → 2:NEW POINT(S); A=2 B=-4/3 C=4 K=-3; 1:TYPE ONE POINT; OLD X=-4 OLD Y=2"),
    dr("REG-T4", "2F((-4/3)X+4)-3 with Df=[-4,8], Rf=[-2,4]", "2", "-4/3", "4", "-3", ("-4", "8"), ("-2", "4"),
       ["D=[-3,6]", "R=[-7,5]"], "D=[-3,6], R=[-7,5]"),
    changes("PR-5.1", "State the transformations in order: y=-f(x-5)+2", "⁻", "", "-5", "2",
            ["REFLECT X-AXIS", "RIGHT 5", "UP 2"], "Reflect over the x-axis; right 5; up 2."),
    changes("PR-5.2", "State the transformations in order: y=3f(1/2 x+2)-4", "3", "1/2", "2", "-4",
            ["VERT STRETCH 3", "HORIZ STRETCH 2", "LEFT 4", "DOWN 4"],
            "Vertical stretch by 3; horizontal stretch by 2; left 4; down 4."),
    dict(id="PR-5.3", source="Mapping table for h(x)=-f(2x)+3 on the base graph; D_h and R_h",
         actions=["k4", "k2", "t:⁻", "t:2", "t:", "t:3", "k2"] + BASE + ["k2"],
         expect=["(-2,1)", "(-1,5)", "(1/2,-1)", "(3/2,3)", "D=[-2,3/2]", "R=[-1,5]"],
         official="(-2,1), (-1,5), (1/2,-1), (3/2,3); D_h=[-2,3/2], R_h=[-1,5]",
         path="4 → 2:NEW POINT(S); A=(-) B=2 C=ENTER K=3; 2:ALL CORNERS; 4 points (-4,2) (-2,-2) (1,4) (3,0); 1:SOLID",
         graph="base graph corners typed from the figure"),
    dr("PR-5.4", "f: D=[-6,2], R=[-3,5]; k(x)=-2f(3x-3)+4", "-2", "3", "-3", "4", ("-6", "2"), ("-3", "5"),
       ["D=[-1,5/3]", "R=[-6,10]"], "D_k=[-1,5/3], R_k=[-6,10]"),
    dict(id="PR-5.5", source="Write an equation: vertical stretch by 5, horizontal compression by 1/2, right 3, down 1",
         actions=["k4", "k4", "k3", "t:5", "k4", "t:1/2", "k5", "t:3", "k6", "t:-1", "k7", "k2"],
         expect=["Y=5F(2(X-3))-1", "=5F(2X-6)-1"], official="y=5f(2(x-3))-1 (=5f(2x-6)-1)",
         path="4 → 4:WRITE THE EQUATION; 3 then 5; 4 then 1/2; 5 then 3; 6 then -1; 7:DONE"),
    changes("PR-5.6", "y=f(3x-12): correct 'shifted right 12'", "", "3", "-12", "",
            ["HORIZ COMPRESS 1/3", "RIGHT 4"], "horizontal compression by 1/3, then right 4, not 12"),
    changes("EX-5.1a", "h(x)=2f(x+1)-3: transformations", "2", "", "1", "-3",
            ["VERT STRETCH 2", "LEFT 1", "DOWN 3"], "vertical stretch by 2; left 1; down 3"),
    dict(id="EX-5.1b", source="h(x)=2f(x+1)-3: mapping table on the base graph, D_h, R_h",
         actions=["k4", "k2", "t:2", "t:", "t:1", "t:-3", "k2", "k1", "k2"], lists=BASE_SAVED,
         expect=["(-5,1)", "(-3,-7)", "(0,5)", "(2,-3)", "D=[-5,2]", "R=[-7,5]"],
         official="(-5,1), (-3,-7), (0,5), (2,-3); D_h=[-5,2], R_h=[-7,5]",
         path="4 → 2; A=2 B=ENTER C=1 K=-3; 2:ALL CORNERS; 1:USE SAVED GRAPH"),
    changes("EX-5.2a", "g(x)=f(3x+6)-1", "", "3", "6", "-1",
            ["HORIZ COMPRESS 1/3", "LEFT 2", "DOWN 1"], "Horizontal compression by 1/3, left 2 (not left 6), down 1."),
    changes("EX-5.2b", "y=f(2x-6)", "", "2", "-6", "", ["HORIZ COMPRESS 1/2", "RIGHT 3"],
            "horizontal compression by 1/2, right 3"),
    changes("EX-5.2c", "y=f(-x+3)", "", "⁻", "3", "", ["REFLECT Y-AXIS", "RIGHT 3"], "reflect over the y-axis, right 3"),
    changes("EX-5.3a", "h(x)=-1/2 f(-2x+4)+1", "-1/2", "-2", "4", "1",
            ["REFLECT X-AXIS", "VERT COMPRESS 1/2", "REFLECT Y-AXIS", "HORIZ COMPRESS 1/2", "RIGHT 2", "UP 1"],
            "reflect over the x-axis; vertical compression by 1/2; reflect over the y-axis; "
            "horizontal compression by 1/2; right 2; up 1"),
    dict(id="EX-5.3b", source="h(x)=-1/2 f(-2x+4)+1: table and D, R", lists=BASE_SAVED,
         actions=["k4", "k2", "t:-1/2", "t:-2", "t:4", "t:1", "k2", "k1", "k2"],
         expect=["(1/2,1)", "(3/2,-1)", "(3,2)", "(4,0)", "D=[1/2,4]", "R=[-1,2]"],
         official="(4,0), (3,2), (3/2,-1), (1/2,1); D_h=[1/2,4], R_h=[-1,2]",
         path="4 → 2; A=-1/2 B=-2 C=4 K=1; 2:ALL CORNERS; 1:USE SAVED GRAPH"),
    dr("EX-5.4", "f: D=[-3,5], R=[-2,6]; h(x)=4f(-1/2x+3)-1", "4", "-1/2", "3", "-1", ("-3", "5"), ("-2", "6"),
       ["D=[-4,12]", "R=[-9,23]"], "D_h=[-4,12], R_h=[-9,23]"),
    dict(id="EX-5.5i", source="Horizontal stretch by a factor of 3, then shift left 2",
         actions=["k4", "k4", "k4", "t:3", "k5", "t:-2", "k7", "k2"],
         expect=["Y=F((1/3)(X+2))"], official="y=f(1/3(x+2))",
         path="4 → 4; 4 then 3; 5 then -2; 7"),
    dict(id="EX-5.5ii", source="Reflect over the x-axis, then shift down 4",
         actions=["k4", "k4", "k1", "k6", "t:-4", "k7", "k2"], expect=["Y=-F(X)-4"], official="y=-f(x)-4",
         path="4 → 4; 1; 6 then -4; 7"),
    dict(id="EX-5.5iii", source="Shift down 4, THEN reflect over the x-axis",
         actions=["k4", "k4", "k6", "t:-4", "k1", "k7", "k2"], expect=["Y=-F(X)+4"], official="y=-(f(x)-4)=-f(x)+4",
         path="4 → 4; 6 then -4; 1; 7"),
    changes("CRAM-5a", "h=2f(-4/3x+4)-3", "2", "-4/3", "4", "-3",
            ["VERT STRETCH 2", "REFLECT Y-AXIS", "HORIZ COMPRESS 3/4", "RIGHT 3", "DOWN 3"],
            "vertical stretch by 2, reflect over y-axis, horizontal compression by 3/4, right 3, down 3"),
    dr("CRAM-5b", "Df=[-2,6], Rf=[-1,7], h=-5f(-1/3x-6)+4", "-5", "-1/3", "-6", "4", ("-2", "6"), ("-1", "7"),
       ["D=[-36,-12]", "R=[-31,9]"], "D_h=[-36,-12]; R_h=[-31,9]"),
    changes("CRAM-5c", "-f(x)+3", "⁻", "", "", "3", ["REFLECT X-AXIS", "UP 3"], "reflect, then up 3"),
    changes("CRAM-5d", "f(4x-2)", "", "4", "-2", "", ["HORIZ COMPRESS 1/4", "RIGHT 1/2"], "right 1/2 (after compress)"),
    dict(id="CORR-1", source="Quiz review #1 (corrected): h(x)=-2f(-x)+3 on f's points (-4,0),(-3,4),(0,-2),(2,2)",
         actions=["k4", "k2", "t:-2", "t:⁻", "t:", "t:3", "k2", "t:4", "t:-4", "t:0", "t:-3", "t:4", "t:0", "t:-2",
                  "t:2", "t:2", "k1", "k2"],
         expect=["(-2,-1)", "(0,7)", "(3,-5)", "(4,3)", "D=[-2,4]", "R=[-5,7]"],
         official="(4,3), (3,-5), (0,7), (-2,-1); range [-5,7] (not [-7,7]); domain [-2,4]",
         path="4 → 2:NEW POINT(S); A=-2 B=(-) C=ENTER K=3; 2:ALL CORNERS; 4 points; 1:SOLID",
         graph="the quiz's points typed in"),
]
