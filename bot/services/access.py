from typing import Optional

from bot.utils.time import now_ts


def compute_delete_after(access_until: Optional[int]) -> int:
    now = now_ts()
    default_delete = now + 86400
    if access_until and access_until < default_delete:
        return access_until
    return default_delete
