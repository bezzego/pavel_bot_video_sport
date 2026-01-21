import time


def now_ts() -> int:
    return int(time.time())


def add_days(ts: int, days: int) -> int:
    return ts + days * 86400
