from typing import Dict, Tuple


TIERS: Dict[int, Dict[int, int]] = {
    7: {1: 2, 5: 1200, 10: 2300},
    30: {1: 2, 5: 2000, 10: 3800},
}


def _interpolate(x: int, p1: Tuple[int, int], p2: Tuple[int, int]) -> int:
    (x1, y1), (x2, y2) = p1, p2
    if x2 == x1:
        return y1
    ratio = (x - x1) / (x2 - x1)
    return int(round(y1 + (y2 - y1) * ratio))


def calculate_total(count: int, duration_days: int) -> int:
    if count <= 0:
        return 0
    tiers = TIERS.get(duration_days, TIERS[30])
    if count <= 1:
        return tiers[1]
    if count >= 10:
        return tiers[10]
    if count <= 5:
        return _interpolate(count, (1, tiers[1]), (5, tiers[5]))
    return _interpolate(count, (5, tiers[5]), (10, tiers[10]))
