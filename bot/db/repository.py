import json
import logging
from typing import Iterable, List, Optional

from bot.db.database import Database
from bot.utils.time import add_days, now_ts


async def get_or_create_user(db: Database, user_id: int) -> dict:
    logger = logging.getLogger("db.repository")
    user = await db.fetchone("SELECT * FROM users WHERE id = ?", (user_id,))
    if user:
        return user
    created_at = now_ts()
    await db.execute(
        "INSERT INTO users (id, created_at, is_corporate) VALUES (?, ?, 0)",
        (user_id, created_at),
    )
    logger.info("Created user user_id=%s", user_id)
    return {
        "id": user_id,
        "created_at": created_at,
        "is_corporate": 0,
        "corporate_unlocked_at": None,
    }


async def get_user(db: Database, user_id: int) -> Optional[dict]:
    return await db.fetchone("SELECT * FROM users WHERE id = ?", (user_id,))


async def set_user_corporate(db: Database, user_id: int) -> None:
    logger = logging.getLogger("db.repository")
    await db.execute(
        "UPDATE users SET is_corporate = 1, corporate_unlocked_at = ? WHERE id = ?",
        (now_ts(), user_id),
    )
    logger.info("Set corporate user_id=%s", user_id)


async def set_user_corporate_status(db: Database, user_id: int, is_corporate: bool) -> None:
    logger = logging.getLogger("db.repository")
    if is_corporate:
        await db.execute(
            "UPDATE users SET is_corporate = 1, corporate_unlocked_at = ? WHERE id = ?",
            (now_ts(), user_id),
        )
    else:
        await db.execute(
            "UPDATE users SET is_corporate = 0, corporate_unlocked_at = NULL WHERE id = ?",
            (user_id,),
        )
    logger.info("Updated corporate status user_id=%s is_corporate=%s", user_id, is_corporate)


async def seed_videos(db: Database, file_ids: List[str]) -> None:
    logger = logging.getLogger("db.repository")
    for index in range(1, 11):
        title = f"Урок {index}"
        file_id = file_ids[index - 1] if index - 1 < len(file_ids) else ""
        existing = await db.fetchone("SELECT * FROM videos WHERE id = ?", (index,))
        if existing is None:
            await db.execute(
                "INSERT INTO videos (id, title, file_id) VALUES (?, ?, ?)",
                (index, title, file_id),
            )
            logger.info("Seeded video id=%s has_file_id=%s", index, bool(file_id))
        else:
            existing_title = (existing.get("title") or "").strip()
            if existing_title == f"Видео {index}":
                await db.execute(
                    "UPDATE videos SET title = ? WHERE id = ?",
                    (title, index),
                )
                logger.info("Updated video title id=%s", index)
            if file_id and file_id != (existing.get("file_id") or ""):
                await db.execute(
                    "UPDATE videos SET file_id = ? WHERE id = ?",
                    (file_id, index),
                )
                logger.info("Updated video file_id id=%s", index)


async def get_video(db: Database, video_id: int) -> Optional[dict]:
    return await db.fetchone("SELECT * FROM videos WHERE id = ?", (video_id,))


async def list_videos(db: Database) -> List[dict]:
    return await db.fetchall("SELECT * FROM videos ORDER BY id")


async def list_videos_for_sale(db: Database) -> List[dict]:
    return await db.fetchall(
        "SELECT * FROM videos WHERE file_id IS NOT NULL AND file_id != '' ORDER BY id"
    )


async def get_next_video_id(db: Database) -> int:
    row = await db.fetchone("SELECT MAX(id) AS max_id FROM videos")
    max_id = row["max_id"] if row and row.get("max_id") is not None else 0
    return int(max_id) + 1


async def add_video(db: Database, title: str, file_id: str) -> int:
    logger = logging.getLogger("db.repository")
    video_id = await get_next_video_id(db)
    final_title = title.strip() or f"Видео {video_id}"
    await db.execute(
        "INSERT INTO videos (id, title, file_id) VALUES (?, ?, ?)",
        (video_id, final_title, file_id),
    )
    logger.info("Added video id=%s title=%s", video_id, final_title)
    return video_id


async def delete_video(db: Database, video_id: int) -> None:
    logger = logging.getLogger("db.repository")
    await db.execute("DELETE FROM videos WHERE id = ?", (video_id,))
    await db.execute("DELETE FROM user_video_access WHERE video_id = ?", (video_id,))
    logger.info("Deleted video id=%s", video_id)


async def update_video_file_id(db: Database, video_id: int, file_id: str) -> None:
    logger = logging.getLogger("db.repository")
    await db.execute("UPDATE videos SET file_id = ? WHERE id = ?", (file_id, video_id))
    logger.info("Updated video file_id id=%s", video_id)


async def get_corporate_auth(db: Database, user_id: int) -> Optional[dict]:
    return await db.fetchone("SELECT * FROM corporate_auth WHERE user_id = ?", (user_id,))


async def set_corporate_auth(db: Database, user_id: int, attempts: int, blocked_until: Optional[int]) -> None:
    logger = logging.getLogger("db.repository")
    existing = await get_corporate_auth(db, user_id)
    if existing is None:
        await db.execute(
            "INSERT INTO corporate_auth (user_id, attempts, blocked_until) VALUES (?, ?, ?)",
            (user_id, attempts, blocked_until),
        )
    else:
        await db.execute(
            "UPDATE corporate_auth SET attempts = ?, blocked_until = ? WHERE user_id = ?",
            (attempts, blocked_until, user_id),
        )
    logger.debug(
        "Corporate auth updated user_id=%s attempts=%s blocked_until=%s",
        user_id,
        attempts,
        blocked_until,
    )


async def reset_corporate_auth(db: Database, user_id: int) -> None:
    logger = logging.getLogger("db.repository")
    await db.execute(
        "UPDATE corporate_auth SET attempts = 0, blocked_until = NULL WHERE user_id = ?",
        (user_id,),
    )
    logger.debug("Corporate auth reset user_id=%s", user_id)


async def get_setting(db: Database, key: str) -> Optional[str]:
    row = await db.fetchone("SELECT value FROM settings WHERE key = ?", (key,))
    if not row:
        return None
    return row.get("value")


async def set_setting(db: Database, key: str, value: str) -> None:
    logger = logging.getLogger("db.repository")
    existing = await get_setting(db, key)
    if existing is None:
        await db.execute("INSERT INTO settings (key, value) VALUES (?, ?)", (key, value))
    else:
        await db.execute("UPDATE settings SET value = ? WHERE key = ?", (value, key))
    logger.info("Updated setting key=%s", key)


async def get_setting_or_default(db: Database, key: str, default: str) -> str:
    value = await get_setting(db, key)
    if value is None or value.strip() == "":
        return default
    return value


async def get_access_until(db: Database, user_id: int, video_id: int) -> Optional[int]:
    row = await db.fetchone(
        "SELECT access_until FROM user_video_access WHERE user_id = ? AND video_id = ?",
        (user_id, video_id),
    )
    if row is None:
        return None
    return row.get("access_until")


async def list_accessible_video_ids(db: Database, user_id: int) -> List[int]:
    now = now_ts()
    rows = await db.fetchall(
        "SELECT video_id FROM user_video_access WHERE user_id = ? AND access_until > ? ORDER BY video_id",
        (user_id, now),
    )
    return [row["video_id"] for row in rows]


async def list_accessible_videos(db: Database, user_id: int) -> List[dict]:
    now = now_ts()
    return await db.fetchall(
        """
        SELECT v.*, uva.access_until FROM videos v
        JOIN user_video_access uva ON uva.video_id = v.id
        WHERE uva.user_id = ? AND uva.access_until > ?
        ORDER BY v.id
        """,
        (user_id, now),
    )


async def get_max_access_until(db: Database, user_id: int) -> Optional[int]:
    row = await db.fetchone(
        "SELECT MAX(access_until) AS max_until FROM user_video_access WHERE user_id = ?",
        (user_id,),
    )
    if not row:
        return None
    return row.get("max_until")


async def get_notified_until(db: Database, user_id: int) -> Optional[int]:
    row = await db.fetchone(
        "SELECT notified_until FROM access_notifications WHERE user_id = ?",
        (user_id,),
    )
    if not row:
        return None
    return row.get("notified_until")


async def set_notified_until(db: Database, user_id: int, notified_until: int) -> None:
    logger = logging.getLogger("db.repository")
    existing = await get_notified_until(db, user_id)
    if existing is None:
        await db.execute(
            "INSERT INTO access_notifications (user_id, notified_until) VALUES (?, ?)",
            (user_id, notified_until),
        )
    else:
        await db.execute(
            "UPDATE access_notifications SET notified_until = ? WHERE user_id = ?",
            (notified_until, user_id),
        )
    logger.info("Updated access notification user_id=%s notified_until=%s", user_id, notified_until)


async def grant_access(db: Database, user_id: int, video_ids: Iterable[int], days: int = 30) -> None:
    logger = logging.getLogger("db.repository")
    now = now_ts()
    for video_id in video_ids:
        existing = await get_access_until(db, user_id, video_id)
        base_ts = max(now, existing or 0)
        new_until = add_days(base_ts, days)
        if existing is None:
            await db.execute(
                "INSERT INTO user_video_access (user_id, video_id, access_until) VALUES (?, ?, ?)",
                (user_id, video_id, new_until),
            )
        else:
            await db.execute(
                "UPDATE user_video_access SET access_until = ? WHERE user_id = ? AND video_id = ?",
                (new_until, user_id, video_id),
            )
        logger.info(
            "Granted access user_id=%s video_id=%s access_until=%s",
            user_id,
            video_id,
            new_until,
        )


async def create_payment(
    db: Database,
    user_id: int,
    label: str,
    amount: int,
    selected_video_ids: List[int],
    duration_days: int,
) -> int:
    logger = logging.getLogger("db.repository")
    created_at = now_ts()
    payload = json.dumps(selected_video_ids)
    await db.execute(
        """
        INSERT INTO payments (user_id, label, amount, status, selected_video_ids, duration_days, created_at)
        VALUES (?, ?, ?, 'pending', ?, ?, ?)
        """,
        (user_id, label, amount, payload, duration_days, created_at),
    )
    row = await db.fetchone("SELECT id FROM payments WHERE label = ?", (label,))
    logger.info(
        "Created payment id=%s user_id=%s amount=%s videos=%s duration_days=%s",
        row["id"],
        user_id,
        amount,
        selected_video_ids,
        duration_days,
    )
    return int(row["id"])


async def get_payment(db: Database, payment_id: int) -> Optional[dict]:
    return await db.fetchone("SELECT * FROM payments WHERE id = ?", (payment_id,))


async def get_pending_payments(db: Database) -> List[dict]:
    return await db.fetchall("SELECT * FROM payments WHERE status = 'pending' ORDER BY created_at")


async def get_pending_payment_for_user(db: Database, user_id: int) -> Optional[dict]:
    return await db.fetchone(
        "SELECT * FROM payments WHERE user_id = ? AND status = 'pending' ORDER BY created_at DESC LIMIT 1",
        (user_id,),
    )


async def mark_payment_success(db: Database, payment_id: int, paid_at: int) -> bool:
    logger = logging.getLogger("db.repository")
    rowcount = await db.execute(
        "UPDATE payments SET status = 'success', paid_at = ? WHERE id = ? AND status = 'pending'",
        (paid_at, payment_id),
        return_rowcount=True,
    )
    logger.info("Payment status updated id=%s success=%s", payment_id, bool(rowcount))
    return bool(rowcount)


async def add_sent_video(db: Database, user_id: int, chat_id: int, message_id: int, delete_after: int) -> None:
    logger = logging.getLogger("db.repository")
    created_at = now_ts()
    await db.execute(
        """
        INSERT INTO sent_videos (user_id, chat_id, message_id, delete_after, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (user_id, chat_id, message_id, delete_after, created_at),
    )
    logger.debug(
        "Stored sent_video user_id=%s chat_id=%s message_id=%s delete_after=%s",
        user_id,
        chat_id,
        message_id,
        delete_after,
    )


async def list_due_sent_videos(db: Database, now: int) -> List[dict]:
    return await db.fetchall(
        "SELECT * FROM sent_videos WHERE delete_after <= ? ORDER BY delete_after",
        (now,),
    )


async def delete_sent_video(db: Database, record_id: int) -> None:
    logger = logging.getLogger("db.repository")
    await db.execute("DELETE FROM sent_videos WHERE id = ?", (record_id,))
    logger.debug("Deleted sent_video id=%s", record_id)


async def list_users(db: Database) -> List[dict]:
    return await db.fetchall("SELECT * FROM users ORDER BY created_at")


async def list_payments(db: Database) -> List[dict]:
    return await db.fetchall("SELECT * FROM payments ORDER BY created_at")


async def list_access(db: Database) -> List[dict]:
    return await db.fetchall(
        """
        SELECT uva.user_id, uva.video_id, uva.access_until, v.title
        FROM user_video_access uva
        LEFT JOIN videos v ON v.id = uva.video_id
        ORDER BY uva.user_id, uva.video_id
        """
    )
