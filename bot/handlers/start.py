import logging

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.config.settings import Settings
from bot.content_texts import WELCOME_SHORT_DESCRIPTION
from bot.db.database import Database
from bot.db.repository import get_or_create_user
from bot.keyboards.menu import main_menu_kb
from bot.utils.admin import is_admin

router = Router()
logger = logging.getLogger("handlers.start")


@router.message(CommandStart())
async def cmd_start(message: Message, db: Database, config: Settings, state: FSMContext) -> None:
    await state.clear()
    await get_or_create_user(db, message.from_user.id)
    logger.info("Start command user_id=%s", message.from_user.id)
    if config.welcome_video_file_id:
        await message.answer_video(config.welcome_video_file_id)
    await message.answer(WELCOME_SHORT_DESCRIPTION, parse_mode="HTML")
    if config.promo_video_file_id:
        await message.answer_video(config.promo_video_file_id)
    await message.answer(
        "Добро пожаловать! Выберите тип доступа или откройте меню:",
        reply_markup=main_menu_kb(is_admin=is_admin(message.from_user.id, config.admin_ids)),
    )


@router.callback_query(F.data == "menu:main")
async def menu_main(query: CallbackQuery, state: FSMContext, config: Settings) -> None:
    logger.debug("Main menu requested user_id=%s", query.from_user.id)
    await state.clear()
    await query.message.answer(
        "Главное меню:",
        reply_markup=main_menu_kb(is_admin=is_admin(query.from_user.id, config.admin_ids)),
    )
    await query.answer()
