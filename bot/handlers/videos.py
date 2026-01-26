import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery

from bot.config.settings import Settings
from bot.db.database import Database
from bot.db import repository
from bot.keyboards.menu import corporate_videos_kb, main_menu_only_kb, my_videos_kb
from bot.services.video_sender import send_video_and_schedule
from bot.utils.time import now_ts

router = Router()
logger = logging.getLogger("handlers.videos")


@router.callback_query(F.data == "menu:my_videos")
async def my_videos(query: CallbackQuery, db: Database, config: Settings) -> None:
    await repository.get_or_create_user(db, query.from_user.id)
    user = await repository.get_user(db, query.from_user.id)
    if user and user.get("is_corporate"):
        logger.info("My videos corporate user_id=%s", query.from_user.id)
        videos = await repository.list_videos(db)
        await query.message.answer(
            "Корпоративный доступ активен. Все видео доступны:",
            reply_markup=corporate_videos_kb(videos),
        )
        await query.answer()
        return

    accessible_videos = await repository.list_accessible_videos(db, query.from_user.id)
    if not accessible_videos:
        logger.info("My videos empty user_id=%s", query.from_user.id)
        await query.message.answer(
            "У вас пока нет активного доступа. Выберите видео и оплатите.",
            reply_markup=my_videos_kb([]),
        )
        await query.answer()
        return

    video_ids = [video["id"] for video in accessible_videos]
    logger.info("My videos list user_id=%s videos=%s", query.from_user.id, video_ids)
    await query.message.answer(
        "Ваши доступные видео:",
        reply_markup=my_videos_kb(accessible_videos),
    )
    await query.answer()


@router.callback_query(F.data.startswith("video:"))
async def open_video(query: CallbackQuery, db: Database, config: Settings) -> None:
    try:
        video_id = int(query.data.split(":")[1])
    except (IndexError, ValueError):
        await query.answer("Некорректное видео")
        return

    await repository.get_or_create_user(db, query.from_user.id)
    user = await repository.get_user(db, query.from_user.id)
    is_corporate = bool(user and user.get("is_corporate"))
    logger.info(
        "Video request user_id=%s video_id=%s corporate=%s",
        query.from_user.id,
        video_id,
        is_corporate,
    )

    access_until = None
    if not is_corporate:
        access_until = await repository.get_access_until(db, query.from_user.id, video_id)
        if not access_until or access_until <= now_ts():
            logger.warning(
                "Video access denied user_id=%s video_id=%s access_until=%s",
                query.from_user.id,
                video_id,
                access_until,
            )
            await query.message.answer(
                "Доступ к этому видео отсутствует или истек.",
                reply_markup=main_menu_only_kb(),
            )
            await query.answer()
            return

    video = await repository.get_video(db, video_id)
    if not video or not video.get("file_id"):
        logger.warning("Video missing file_id video_id=%s", video_id)
        await query.message.answer(
            "Видео пока не добавлено. Попробуйте позже.",
            reply_markup=main_menu_only_kb(),
        )
        await query.answer()
        return

    await send_video_and_schedule(
        bot=query.bot,
        db=db,
        chat_id=query.message.chat.id,
        user_id=query.from_user.id,
        file_id=video["file_id"],
        access_until=access_until,
    )
    await query.answer()
