import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery

from bot.config.settings import Settings
from bot.keyboards.menu import main_menu_only_kb
from bot.utils.cleanup import send_and_replace

router = Router()
logger = logging.getLogger("handlers.support")


@router.callback_query(F.data == "menu:support")
async def support(query: CallbackQuery, config: Settings) -> None:
    contact = config.support_contact or "@support"
    logger.info("Support requested user_id=%s", query.from_user.id)
    await send_and_replace(
        query.message,
        f"Связаться с поддержкой: {contact}",
        reply_markup=main_menu_only_kb(),
    )
    await query.answer()
