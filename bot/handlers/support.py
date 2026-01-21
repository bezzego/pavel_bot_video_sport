import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery

from bot.config.settings import Settings

router = Router()
logger = logging.getLogger("handlers.support")


@router.callback_query(F.data == "menu:support")
async def support(query: CallbackQuery, config: Settings) -> None:
    contact = config.support_contact or "@support"
    logger.info("Support requested user_id=%s", query.from_user.id)
    await query.message.answer(f"Связаться с поддержкой: {contact}")
    await query.answer()
