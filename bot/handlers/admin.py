import logging
import re

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message

from bot.config.settings import Settings
from bot.db.database import Database
from bot.db import repository

router = Router()
logger = logging.getLogger("handlers.admin")


class AdminStates(StatesGroup):
    waiting_video = State()


def _is_admin(user_id: int, admin_ids: list[int]) -> bool:
    return user_id in admin_ids


@router.message(Command("cp"))
async def cmd_cp(message: Message, state: FSMContext, config: Settings) -> None:
    if not _is_admin(message.from_user.id, config.admin_ids):
        return
    logger.info("Admin /cp started user_id=%s", message.from_user.id)
    await state.set_state(AdminStates.waiting_video)
    await message.answer(
        "Отправьте видео. Можно добавить номер (1-10) в подписи, "
        "чтобы сразу обновить базу."
    )


@router.message(AdminStates.waiting_video, F.video)
async def cp_receive_video(message: Message, db: Database, state: FSMContext) -> None:
    file_id = message.video.file_id
    caption = message.caption or ""
    match = re.search(r"\b(10|[1-9])\b", caption)
    video_id = int(match.group(1)) if match else None
    if video_id:
        await repository.update_video_file_id(db, video_id, file_id)
        logger.info("Admin updated video file_id user_id=%s video_id=%s", message.from_user.id, video_id)
    else:
        logger.info("Admin received video file_id user_id=%s", message.from_user.id)

    line_hint = f"VIDEO_{video_id}_FILE_ID={file_id}" if video_id else f"VIDEO_N_FILE_ID={file_id}"
    await message.answer(
        "file_id получен:\n"
        f"<code>{file_id}</code>\n\n"
        "Строка для .env:\n"
        f"<code>{line_hint}</code>",
        parse_mode="HTML",
    )
    await state.clear()


@router.message(AdminStates.waiting_video)
async def cp_waiting_video(message: Message) -> None:
    logger.warning("Admin /cp non-video user_id=%s", message.from_user.id)
    await message.answer("Нужно отправить именно видео.")
