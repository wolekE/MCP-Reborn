"""Shared helpers for the Python reference implementations."""
from decimal import Decimal, ROUND_HALF_UP

G = 9.8          # m/s^2, class convention (up is positive, so a = -G in free fall)
UNKNOWN = 999    # sentinel the student types for an unknown in the VOVFSTA solver


def fmt3(x):
    """Independent re-implementation of what prgmZFMT prints: 3 significant figures,
    trailing zeros kept, leading '0.' for |x|<1, scientific 'd.ddE[-]n' outside 1E-3..1E6,
    '-' for negatives and '0' for |x| < 1E-9."""
    x = Decimal(repr(float(x))) if not isinstance(x, Decimal) else x
    x = Decimal(f"{x:.13E}")                # the calculator stores 14 significant digits
    if abs(x) < Decimal("1E-9"):
        return "0"
    sign = "-" if x < 0 else ""
    a = abs(x)
    # round the mantissa half-up to 2 decimals, like TI's round(
    e = a.adjusted()
    m = (a.scaleb(-e)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    if m >= 10 and e >= 99:            # 1.00E100 does not exist on the calculator
        m = Decimal("9.99")
    if m >= 10:
        m = m / 10
        e += 1
    digits = f"{m:.2f}".replace(".", "")    # 3 digits
    if e >= 6 or e <= -4:
        return f"{sign}{digits[0]}.{digits[1:]}E{e}"
    if e >= 2:
        return sign + digits + "0" * (e - 2)
    if e == 1:
        return f"{sign}{digits[:2]}.{digits[2]}"
    if e == 0:
        return f"{sign}{digits[0]}.{digits[1:]}"
    return sign + "0." + "0" * (-e - 1) + digits
