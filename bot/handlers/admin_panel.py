import html
import logging
import os
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from aiogram.types.input_file import FSInputFile
from openpyxl import Workbook
from aiogram.types import InputMediaPhoto, InputMediaVideo

from bot.config.settings import Settings
from bot.db.database import Database
from bot.db import repository
from bot.keyboards.menu import admin_confirm_kb, admin_export_kb, admin_panel_kb, admin_videos_kb
from bot.utils.admin import is_admin
from bot.utils.time import now_ts

router = Router()
logger = logging.getLogger("handlers.admin_panel")


class AdminPanelStates(StatesGroup):
    broadcast_waiting = State()
    broadcast_confirm = State()
    corp_reset_waiting = State()
    corp_password_waiting = State()
    intro_waiting = State()
    video_add_waiting = State()


def _format_ts(ts: Any) -> str:
    if not ts:
        return ""
    try:
        return datetime.utcfromtimestamp(int(ts)).isoformat()
    except Exception:
        return str(ts)


def _build_export_file(prefix: str, headers: list[str], rows: list[list[Any]]) -> str:
    path = f"/tmp/{prefix}_{int(time.time())}.xlsx"
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(headers)
    for row in rows:
        sheet.append(row)
    workbook.save(path)
    return path


def _broadcast_data_from_message(message: Message) -> Dict[str, Any] | None:
    if message.photo:
        photo = message.photo[-1]
        return {
            "type": "photo",
            "file_id": photo.file_id,
            "caption": message.caption or "",
            "caption_entities": message.caption_entities or [],
        }
    if message.video:
        return {
            "type": "video",
            "file_id": message.video.file_id,
            "caption": message.caption or "",
            "caption_entities": message.caption_entities or [],
        }
    if message.video_note:
        return {
            "type": "video_note",
            "file_id": message.video_note.file_id,
        }
    if message.text:
        return {
            "type": "text",
            "text": message.text,
            "entities": message.entities or [],
        }
    return None


def _build_media_group(items: List[Dict[str, Any]]) -> List[InputMediaPhoto | InputMediaVideo]:
    media: List[InputMediaPhoto | InputMediaVideo] = []
    caption_set = False
    for item in items:
        if item["type"] == "photo":
            media_item = InputMediaPhoto(media=item["file_id"])
        elif item["type"] == "video":
            media_item = InputMediaVideo(media=item["file_id"])
        else:
            continue
        if not caption_set and item.get("caption"):
            media_item.caption = item["caption"]
            if item.get("caption_entities"):
                media_item.caption_entities = item["caption_entities"]
            caption_set = True
        media.append(media_item)
    return media


async def _ensure_admin(event: CallbackQuery | Message, config: Settings) -> bool:
    user_id = event.from_user.id
    if is_admin(user_id, config.admin_ids):
        return True
    if isinstance(event, CallbackQuery):
        await event.answer("Недостаточно прав", show_alert=True)
    else:
        await event.answer("Недостаточно прав")
    return False


@router.callback_query(F.data == "menu:admin")
async def admin_panel(query: CallbackQuery, state: FSMContext, config: Settings) -> None:
    if not await _ensure_admin(query, config):
        return
    logger.info("Admin panel opened user_id=%s", query.from_user.id)
    await state.clear()
    await query.message.answer("Админ-панель:", reply_markup=admin_panel_kb())
    await query.answer()


@router.callback_query(F.data == "admin:stats")
async def admin_stats(query: CallbackQuery, db: Database, config: Settings) -> None:
    if not await _ensure_admin(query, config):
        return
    logger.info("Admin stats requested user_id=%s", query.from_user.id)

    total_users = await db.fetchone("SELECT COUNT(*) AS cnt FROM users")
    corporate_users = await db.fetchone("SELECT COUNT(*) AS cnt FROM users WHERE is_corporate = 1")
    active_access = await db.fetchone(
        "SELECT COUNT(DISTINCT user_id) AS cnt FROM user_video_access WHERE access_until > ?",
        (now_ts(),),
    )
    videos_total = await db.fetchone("SELECT COUNT(*) AS cnt FROM videos")
    videos_available = await db.fetchone(
        "SELECT COUNT(*) AS cnt FROM videos WHERE file_id IS NOT NULL AND file_id != ''"
    )
    payments_total = await db.fetchone("SELECT COUNT(*) AS cnt FROM payments")
    payments_success = await db.fetchone("SELECT COUNT(*) AS cnt FROM payments WHERE status = 'success'")
    payments_pending = await db.fetchone("SELECT COUNT(*) AS cnt FROM payments WHERE status = 'pending'")

    message_text = (
        "Статистика бота:\n"
        f"Пользователей всего: {total_users['cnt']}\n"
        f"Корпоративных: {corporate_users['cnt']}\n"
        f"С активным доступом: {active_access['cnt']}\n"
        f"Видео в базе: {videos_total['cnt']}\n"
        f"Видео доступно к продаже: {videos_available['cnt']}\n"
        f"Платежей всего: {payments_total['cnt']}\n"
        f"Платежей успешных: {payments_success['cnt']}\n"
        f"Платежей в ожидании: {payments_pending['cnt']}"
    )
    await query.message.answer(message_text, reply_markup=admin_panel_kb())
    await query.answer()


@router.callback_query(F.data == "admin:export")
async def admin_export_menu(query: CallbackQuery, config: Settings) -> None:
    if not await _ensure_admin(query, config):
        return
    logger.info("Admin export menu user_id=%s", query.from_user.id)
    await query.message.answer("Экспорт данных:", reply_markup=admin_export_kb())
    await query.answer()


@router.callback_query(F.data.startswith("admin:export:"))
async def admin_export(query: CallbackQuery, db: Database, config: Settings) -> None:
    if not await _ensure_admin(query, config):
        return

    export_type = query.data.split(":")[2]
    logger.info("Admin export type=%s user_id=%s", export_type, query.from_user.id)
    if export_type == "users":
        users = await repository.list_users(db)
        rows = [
            [u["id"], _format_ts(u["created_at"]), u["is_corporate"], _format_ts(u.get("corporate_unlocked_at"))]
            for u in users
        ]
        path = _build_export_file(
            "users",
            ["id", "created_at", "is_corporate", "corporate_unlocked_at"],
            rows,
        )
    elif export_type == "payments":
        payments = await repository.list_payments(db)
        rows = [
            [
                p["id"],
                p["user_id"],
                p["label"],
                p["amount"],
                p["status"],
                p["selected_video_ids"],
                p.get("duration_days", 30),
                _format_ts(p["created_at"]),
                _format_ts(p.get("paid_at")),
            ]
            for p in payments
        ]
        path = _build_export_file(
            "payments",
            [
                "id",
                "user_id",
                "label",
                "amount",
                "status",
                "selected_video_ids",
                "duration_days",
                "created_at",
                "paid_at",
            ],
            rows,
        )
    elif export_type == "access":
        access_rows = await repository.list_access(db)
        rows = [
            [
                row["user_id"],
                row["video_id"],
                row.get("title") or "",
                _format_ts(row["access_until"]),
            ]
            for row in access_rows
        ]
        path = _build_export_file(
            "access",
            ["user_id", "video_id", "title", "access_until"],
            rows,
        )
    else:
        await query.answer("Неизвестный экспорт")
        return

    await query.message.answer_document(FSInputFile(path), reply_markup=admin_export_kb())
    try:
        os.remove(path)
    except OSError:
        logger.warning("Failed to удалить экспортный файл %s", path)
    await query.answer()


@router.callback_query(F.data == "admin:broadcast")
async def admin_broadcast_start(query: CallbackQuery, state: FSMContext, config: Settings) -> None:
    if not await _ensure_admin(query, config):
        return
    logger.info("Admin broadcast start user_id=%s", query.from_user.id)
    await state.set_state(AdminPanelStates.broadcast_waiting)
    await query.message.answer(
        "Отправьте контент для рассылки: текст, фото, видео или кружочек. "
        "Поддерживается HTML-разметка.",
    )
    await query.answer()


@router.message(AdminPanelStates.broadcast_waiting)
async def admin_broadcast_capture(message: Message, state: FSMContext, config: Settings) -> None:
    if not await _ensure_admin(message, config):
        return
    payload = _broadcast_data_from_message(message)
    if not payload:
        await message.answer("Пришлите текст, фото, видео или кружочек.")
        return
    logger.info("Admin broadcast payload type=%s user_id=%s", payload["type"], message.from_user.id)

    if message.media_group_id:
        data = await state.get_data()
        items = data.get("media_group_items", [])
        if data.get("media_group_id") and data["media_group_id"] != message.media_group_id:
            await message.answer("Уже есть активный альбом. Завершите его или отмените.")
            return
        items.append(payload)
        await state.update_data(media_group_id=message.media_group_id, media_group_items=items)
        await state.set_state(AdminPanelStates.broadcast_confirm)
        if len(items) == 1:
            await message.answer(
                "Альбом принят. Отправьте остальные элементы и нажмите «Отправить».",
                reply_markup=admin_confirm_kb("broadcast"),
            )
        return

    await state.update_data(broadcast_payload=payload)
    await state.set_state(AdminPanelStates.broadcast_confirm)
    await message.answer("Подтвердите рассылку:", reply_markup=admin_confirm_kb("broadcast"))


@router.callback_query(AdminPanelStates.broadcast_confirm, F.data == "admin:confirm:broadcast")
async def admin_broadcast_send(
    query: CallbackQuery,
    db: Database,
    state: FSMContext,
    config: Settings,
) -> None:
    if not await _ensure_admin(query, config):
        return
    data = await state.get_data()
    payload = data.get("broadcast_payload")
    media_group_items = data.get("media_group_items") or []
    if not payload and not media_group_items:
        await query.message.answer("Нет данных для рассылки.")
        await state.clear()
        return

    users = await repository.list_users(db)
    logger.info("Broadcast sending to %s users", len(users))
    sent = 0
    failed = 0
    for user in users:
        try:
            if media_group_items:
                media = _build_media_group(media_group_items)
                await query.bot.send_media_group(user["id"], media)
            elif payload["type"] == "text":
                await query.bot.send_message(
                    user["id"],
                    payload["text"],
                    entities=payload.get("entities") or None,
                )
            elif payload["type"] == "photo":
                await query.bot.send_photo(
                    user["id"],
                    payload["file_id"],
                    caption=payload.get("caption"),
                    caption_entities=payload.get("caption_entities") or None,
                )
            elif payload["type"] == "video":
                await query.bot.send_video(
                    user["id"],
                    payload["file_id"],
                    caption=payload.get("caption"),
                    caption_entities=payload.get("caption_entities") or None,
                )
            elif payload["type"] == "video_note":
                await query.bot.send_video_note(user["id"], payload["file_id"])
            sent += 1
        except Exception:
            failed += 1
            logger.exception("Broadcast failed user_id=%s", user["id"])
    logger.info("Broadcast finished sent=%s failed=%s", sent, failed)
    await query.message.answer(
        f"Рассылка завершена. Успешно: {sent}, ошибки: {failed}",
        reply_markup=admin_panel_kb(),
    )
    await state.clear()
    await query.answer()


@router.callback_query(F.data == "admin:cancel")
async def admin_cancel(query: CallbackQuery, state: FSMContext, config: Settings) -> None:
    if not await _ensure_admin(query, config):
        return
    logger.info("Admin action canceled user_id=%s", query.from_user.id)
    await state.clear()
    await query.message.answer("Действие отменено.", reply_markup=admin_panel_kb())
    await query.answer()


@router.callback_query(F.data == "admin:corp_reset")
async def admin_corp_reset(query: CallbackQuery, state: FSMContext, config: Settings) -> None:
    if not await _ensure_admin(query, config):
        return
    logger.info("Admin corporate reset start user_id=%s", query.from_user.id)
    await state.set_state(AdminPanelStates.corp_reset_waiting)
    await query.message.answer("Введите ID пользователя для перевода в обычного клиента:")
    await query.answer()


@router.message(AdminPanelStates.corp_reset_waiting)
async def admin_corp_reset_apply(message: Message, db: Database, state: FSMContext, config: Settings) -> None:
    if not await _ensure_admin(message, config):
        return
    try:
        user_id = int((message.text or "").strip())
    except ValueError:
        await message.answer("Нужно указать числовой ID пользователя.")
        return
    user = await repository.get_user(db, user_id)
    if not user:
        await message.answer("Пользователь не найден.")
        return
    await repository.set_user_corporate_status(db, user_id, False)
    logger.info("Admin corporate reset applied target_user_id=%s", user_id)
    await state.clear()
    await message.answer("Пользователь переведен в обычного клиента.", reply_markup=admin_panel_kb())


@router.callback_query(F.data == "admin:corp_password")
async def admin_corp_password(query: CallbackQuery, state: FSMContext, config: Settings) -> None:
    if not await _ensure_admin(query, config):
        return
    logger.info("Admin corporate password change start user_id=%s", query.from_user.id)
    await state.set_state(AdminPanelStates.corp_password_waiting)
    await query.message.answer("Введите новый пароль для корпоративных клиентов:")
    await query.answer()


@router.message(AdminPanelStates.corp_password_waiting)
async def admin_corp_password_apply(message: Message, db: Database, state: FSMContext, config: Settings) -> None:
    if not await _ensure_admin(message, config):
        return
    password = (message.text or "").strip()
    if not password:
        await message.answer("Пароль не может быть пустым.")
        return
    await repository.set_setting(db, "corporate_password", password)
    logger.info("Admin corporate password updated user_id=%s", message.from_user.id)
    await state.clear()
    await message.answer("Пароль обновлен.", reply_markup=admin_panel_kb())


@router.callback_query(F.data == "admin:intro")
async def admin_intro(query: CallbackQuery, db: Database, state: FSMContext, config: Settings) -> None:
    if not await _ensure_admin(query, config):
        return
    logger.info("Admin intro edit start user_id=%s", query.from_user.id)
    current = await repository.get_setting(db, "purchase_intro")
    if not current:
        current = "(текущее значение по умолчанию)"
    safe_current = html.escape(current)
    await state.set_state(AdminPanelStates.intro_waiting)
    await query.message.answer(
        "Текущий текст перед выбором:\n"
        f"<pre>{safe_current}</pre>\n\n"
        "Отправьте новый текст (часть до \"Выбрано\" и \"Итого\").",
        parse_mode="HTML",
    )
    await query.answer()


@router.message(AdminPanelStates.intro_waiting)
async def admin_intro_apply(message: Message, db: Database, state: FSMContext, config: Settings) -> None:
    if not await _ensure_admin(message, config):
        return
    text = (message.text or "").strip()
    if not text:
        await message.answer("Текст не может быть пустым.")
        return
    await repository.set_setting(db, "purchase_intro", text)
    logger.info("Admin intro updated user_id=%s", message.from_user.id)
    await state.clear()
    await message.answer("Текст обновлен.", reply_markup=admin_panel_kb())


@router.callback_query(F.data == "admin:videos")
async def admin_videos(query: CallbackQuery, db: Database, config: Settings) -> None:
    if not await _ensure_admin(query, config):
        return
    logger.info("Admin videos menu user_id=%s", query.from_user.id)
    videos = await repository.list_videos(db)
    await query.message.answer("Управление видео:", reply_markup=admin_videos_kb(videos))
    await query.answer()


@router.callback_query(F.data == "admin:video:add")
async def admin_video_add_start(query: CallbackQuery, state: FSMContext, config: Settings) -> None:
    if not await _ensure_admin(query, config):
        return
    logger.info("Admin video add start user_id=%s", query.from_user.id)
    await state.set_state(AdminPanelStates.video_add_waiting)
    await query.message.answer("Отправьте видео. Подпись будет названием урока.")
    await query.answer()


@router.message(AdminPanelStates.video_add_waiting, F.video)
async def admin_video_add_apply(
    message: Message,
    db: Database,
    state: FSMContext,
    config: Settings,
) -> None:
    if not await _ensure_admin(message, config):
        return
    file_id = message.video.file_id
    title = (message.caption or "").strip()
    video_id = await repository.add_video(db, title, file_id)
    logger.info("Admin video added id=%s user_id=%s", video_id, message.from_user.id)
    await state.clear()
    videos = await repository.list_videos(db)
    await message.answer(f"Видео добавлено. ID: {video_id}", reply_markup=admin_videos_kb(videos))


@router.message(AdminPanelStates.video_add_waiting)
async def admin_video_add_invalid(message: Message, config: Settings) -> None:
    if not await _ensure_admin(message, config):
        return
    await message.answer("Нужно отправить именно видео.")


@router.callback_query(F.data.startswith("admin:video:del:"))
async def admin_video_delete(query: CallbackQuery, db: Database, config: Settings) -> None:
    if not await _ensure_admin(query, config):
        return
    try:
        video_id = int(query.data.split(":")[3])
    except (IndexError, ValueError):
        await query.answer("Некорректный ID")
        return
    await repository.delete_video(db, video_id)
    logger.info("Admin video deleted id=%s user_id=%s", video_id, query.from_user.id)
    videos = await repository.list_videos(db)
    await query.message.answer("Видео удалено.", reply_markup=admin_videos_kb(videos))
    await query.answer()
