import logging
from typing import Any, Dict

from aiogram.types import Message

logger = logging.getLogger("utils.cleanup")

_last_bot_message: Dict[int, int] = {}


def _set_last(chat_id: int, message_id: int) -> None:
    _last_bot_message[chat_id] = message_id


def _get_last(chat_id: int) -> int | None:
    return _last_bot_message.get(chat_id)


async def send_and_replace(message: Message, text: str, **kwargs: Any) -> Message:
    chat_id = message.chat.id
    last_id = _get_last(chat_id)
    if last_id:
        try:
            await message.bot.delete_message(chat_id, last_id)
        except Exception:
            logger.debug("Failed to delete previous bot message chat_id=%s msg_id=%s", chat_id, last_id)
    sent = await message.answer(text, **kwargs)
    _set_last(chat_id, sent.message_id)
    return sent
