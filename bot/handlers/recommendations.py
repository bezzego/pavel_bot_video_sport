import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery

from bot.content_texts import RECOMMENDATIONS_TEXT, RECOMMENDATIONS_TITLE
from bot.keyboards.menu import main_menu_only_kb

router = Router()
logger = logging.getLogger("handlers.recommendations")


@router.callback_query(F.data == "menu:recommendations")
async def recommendations(query: CallbackQuery) -> None:
    logger.info("Recommendations requested user_id=%s", query.from_user.id)
    await query.message.answer(
        f"{RECOMMENDATIONS_TITLE}\n\n{RECOMMENDATIONS_TEXT}",
        parse_mode="HTML",
        reply_markup=main_menu_only_kb(),
    )
    await query.answer()
