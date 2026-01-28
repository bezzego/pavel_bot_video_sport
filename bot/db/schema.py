from bot.db.database import Database


async def init_db(db: Database) -> None:
    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            created_at INTEGER NOT NULL,
            is_corporate INTEGER NOT NULL DEFAULT 0,
            corporate_unlocked_at INTEGER
        )
        """
    )
    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS videos (
            id INTEGER PRIMARY KEY,
            title TEXT NOT NULL,
            file_id TEXT
        )
        """
    )
    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS user_video_access (
            user_id INTEGER NOT NULL,
            video_id INTEGER NOT NULL,
            access_until INTEGER NOT NULL,
            PRIMARY KEY (user_id, video_id)
        )
        """
    )
    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            label TEXT NOT NULL,
            amount INTEGER NOT NULL,
            status TEXT NOT NULL,
            selected_video_ids TEXT NOT NULL,
            duration_days INTEGER NOT NULL DEFAULT 30,
            created_at INTEGER NOT NULL,
            paid_at INTEGER
        )
        """
    )
    try:
        await db.execute("ALTER TABLE payments ADD COLUMN duration_days INTEGER NOT NULL DEFAULT 30")
    except Exception:
        pass
    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS sent_videos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            chat_id INTEGER NOT NULL,
            message_id INTEGER NOT NULL,
            delete_after INTEGER NOT NULL,
            created_at INTEGER NOT NULL
        )
        """
    )
    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS corporate_auth (
            user_id INTEGER PRIMARY KEY,
            attempts INTEGER NOT NULL DEFAULT 0,
            blocked_until INTEGER
        )
        """
    )
    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
        """
    )
    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS access_notifications (
            user_id INTEGER PRIMARY KEY,
            notified_until INTEGER NOT NULL
        )
        """
    )
    try:
        await db.execute("ALTER TABLE access_notifications ADD COLUMN notified_until INTEGER NOT NULL")
    except Exception:
        pass
