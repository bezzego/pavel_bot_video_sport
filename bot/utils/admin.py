from typing import Iterable


def is_admin(user_id: int, admin_ids: Iterable[int]) -> bool:
    return int(user_id) in set(admin_ids)
