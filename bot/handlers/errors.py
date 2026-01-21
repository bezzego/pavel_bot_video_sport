import logging
import traceback
from typing import Any

from aiogram import Bot, Router
from aiogram.types import ErrorEvent

from bot.config.settings import Settings

router = Router()


def _safe_dump_update(update: Any) -> str:
    if update is None:
        return "no update payload"
    try:
        if hasattr(update, "model_dump"):
            data = update.model_dump(exclude_none=True)
            text = str(data)
        else:
            text = str(update)
    except Exception:
        text = repr(update)
    if len(text) > 1000:
        return text[:1000] + "..."
    return text


@router.errors()
async def on_error(event: ErrorEvent, bot: Bot, config: Settings) -> None:
    logging.getLogger("errors").exception("Unhandled error", exc_info=event.exception)

    admin_id = config.error_admin_id
    if not admin_id:
        return

    update_text = _safe_dump_update(getattr(event, "update", None))
    tb_text = "".join(traceback.format_exception(event.exception))
    if len(tb_text) > 2500:
        tb_text = tb_text[-2500:]

    message = (
        "Ошибка в боте:\n"
        f"<b>{type(event.exception).__name__}</b>: {event.exception}\n\n"
        f"<b>Update</b>:\n<pre>{update_text}</pre>\n\n"
        f"<b>Traceback</b>:\n<pre>{tb_text}</pre>"
    )
    if len(message) > 3900:
        message = message[:3900] + "..."
    try:
        await bot.send_message(admin_id, message)
    except Exception:
        logging.getLogger("errors").exception("Failed to notify admin")
