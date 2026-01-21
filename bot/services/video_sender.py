import logging
from typing import Optional

from aiogram import Bot

from bot.db.database import Database
from bot.db.repository import add_sent_video
from bot.services.access import compute_delete_after


async def send_video_and_schedule(
    bot: Bot,
    db: Database,
    chat_id: int,
    user_id: int,
    file_id: str,
    access_until: Optional[int],
) -> None:
    logger = logging.getLogger("video_sender")
    logger.debug(
        "Sending video user_id=%s chat_id=%s access_until=%s",
        user_id,
        chat_id,
        access_until,
    )
    message = await bot.send_video(chat_id=chat_id, video=file_id)
    delete_after = compute_delete_after(access_until)
    await add_sent_video(db, user_id, chat_id, message.message_id, delete_after)
    logger.info(
        "Sent video user_id=%s message_id=%s delete_after=%s",
        user_id,
        message.message_id,
        delete_after,
    )
