import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from bot.config.settings import Settings
from bot.db.database import Database
from bot.db import repository
from bot.keyboards.menu import corporate_videos_kb
from bot.utils.time import now_ts

router = Router()
logger = logging.getLogger("handlers.corporate")


class CorporateStates(StatesGroup):
    waiting_password = State()


@router.callback_query(F.data == "menu:corporate")
async def corporate_entry(query: CallbackQuery, db: Database, config: Settings, state: FSMContext) -> None:
    await repository.get_or_create_user(db, query.from_user.id)
    user = await repository.get_user(db, query.from_user.id)
    if user and user.get("is_corporate"):
        videos = await repository.list_videos(db)
        logger.info("Corporate menu access user_id=%s", query.from_user.id)
        await query.message.answer(
            "Корпоративный доступ активен. Выберите видео:",
            reply_markup=corporate_videos_kb(videos),
        )
        await query.answer()
        return

    auth = await repository.get_corporate_auth(db, query.from_user.id)
    if auth and auth.get("blocked_until") and auth["blocked_until"] > now_ts():
        remain = int((auth["blocked_until"] - now_ts()) / 60) + 1
        logger.warning("Corporate blocked user_id=%s minutes=%s", query.from_user.id, remain)
        await query.message.answer(
            f"Слишком много попыток. Повторите через {remain} мин.")
        await query.answer()
        return

    logger.info("Corporate password requested user_id=%s", query.from_user.id)
    await state.set_state(CorporateStates.waiting_password)
    await query.message.answer("Введите корпоративный пароль:")
    await query.answer()


@router.message(CorporateStates.waiting_password)
async def corporate_password(message: Message, db: Database, config: Settings, state: FSMContext) -> None:
    password = (message.text or "").strip()
    effective_password = await repository.get_setting_or_default(
        db,
        "corporate_password",
        config.corporate_password,
    )
    if password == effective_password:
        logger.info("Corporate password success user_id=%s", message.from_user.id)
        await repository.set_user_corporate(db, message.from_user.id)
        await repository.reset_corporate_auth(db, message.from_user.id)
        await state.clear()
        videos = await repository.list_videos(db)
        await message.answer(
            "Пароль принят. Доступ открыт.",
            reply_markup=corporate_videos_kb(videos),
        )
        return

    logger.warning("Corporate password failed user_id=%s", message.from_user.id)
    auth = await repository.get_corporate_auth(db, message.from_user.id)
    attempts = auth.get("attempts", 0) + 1 if auth else 1
    blocked_until = None
    if attempts >= config.corporate_max_attempts:
        blocked_until = now_ts() + config.corporate_block_minutes * 60
        attempts = 0
        await state.clear()
        await message.answer(
            f"Неверный пароль. Попробуйте снова через {config.corporate_block_minutes} мин.")
    else:
        await message.answer(
            f"Неверный пароль. Осталось попыток: {config.corporate_max_attempts - attempts}"
        )
    await repository.set_corporate_auth(db, message.from_user.id, attempts, blocked_until)
