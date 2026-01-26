import json
import logging
import uuid

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery

from bot.config.settings import Settings
from bot.content_texts import LESSONS_LIST
from bot.db.database import Database
from bot.db import repository
from bot.keyboards.menu import my_videos_kb, payment_kb, purchase_selection_kb
from bot.services.pricing import calculate_total
from bot.services.yoomoney import YooMoneyClient
from bot.utils.time import now_ts

router = Router()
logger = logging.getLogger("handlers.purchase")


class PurchaseStates(StatesGroup):
    selecting = State()


DEFAULT_PURCHASE_INTRO = (
    "Подберите уроки под свои задачи: короткие и практичные видео помогут быстрее внедрять спорт-рутины.\n\n"
    "Выберите уроки. Можно купить любое количество."
)


async def _selection_text(db: Database, selected_ids: list[int], total: int, duration_days: int) -> str:
    intro = await repository.get_setting_or_default(db, "purchase_intro", DEFAULT_PURCHASE_INTRO)
    if duration_days == 7:
        duration_label = "1 неделю"
    else:
        duration_label = "1 месяц"
    if selected_ids:
        selected_str = ", ".join(str(x) for x in selected_ids)
    else:
        selected_str = "ничего не выбрано"
    return (
        f"{intro}\n\n"
        f"{LESSONS_LIST}\n\n"
        "Стоимость занятий с доступом на 1 неделю:\n"
        "1 урок — 300р.\n"
        "5 уроков — 1200р.\n"
        "10 уроков — 2300р.\n\n"
        "Стоимость занятий с доступом на 1 месяц:\n"
        "1 урок — 500р.\n"
        "5 уроков — 2000р.\n"
        "10 уроков — 3800р.\n\n"
        f"Выбранный срок доступа: {duration_label}\n"
        f"Выбрано: {selected_str}\n"
        f"Стоимость: {total} ₽"
    )


async def _show_selection(query: CallbackQuery, db: Database, state: FSMContext, config: Settings) -> None:
    data = await state.get_data()
    selected_ids = data.get("selected_ids", [])
    duration_days = int(data.get("duration_days", 30))
    videos = await repository.list_videos_for_sale(db)
    available_ids = {video["id"] for video in videos}
    selected_ids = [video_id for video_id in selected_ids if video_id in available_ids]
    await state.update_data(selected_ids=selected_ids)
    total = calculate_total(len(selected_ids), duration_days)
    text = await _selection_text(db, selected_ids, total, duration_days)
    if query.message.text:
        await query.message.edit_text(
            text,
            reply_markup=purchase_selection_kb(selected_ids, videos, duration_days),
        )
    else:
        await query.message.answer(
            text,
            reply_markup=purchase_selection_kb(selected_ids, videos, duration_days),
        )
    await query.answer()


@router.callback_query(F.data.in_({"menu:regular", "menu:buy"}))
async def purchase_entry(
    query: CallbackQuery,
    db: Database,
    config: Settings,
    state: FSMContext,
) -> None:
    await repository.get_or_create_user(db, query.from_user.id)
    user = await repository.get_user(db, query.from_user.id)
    if user and user.get("is_corporate"):
        await query.message.answer("У вас корпоративный доступ. Покупка не требуется.")
        await query.answer()
        return

    await state.set_state(PurchaseStates.selecting)
    await state.update_data(selected_ids=[], duration_days=30)
    await _show_selection(query, db, state, config)


@router.callback_query(PurchaseStates.selecting, F.data.startswith("sel:"))
async def selection_action(
    query: CallbackQuery,
    db: Database,
    config: Settings,
    state: FSMContext,
    yoomoney: YooMoneyClient,
) -> None:
    action = query.data.split(":", 1)[1]
    data = await state.get_data()
    selected_ids = set(data.get("selected_ids", []))
    duration_days = int(data.get("duration_days", 30))
    videos = await repository.list_videos_for_sale(db)
    available_ids = {video["id"] for video in videos}
    selected_ids = selected_ids & available_ids

    if action.startswith("toggle:"):
        try:
            video_id = int(action.split(":")[1])
        except (IndexError, ValueError):
            await query.answer("Некорректный выбор")
            return
        if video_id not in available_ids:
            await query.answer("Видео недоступно")
            return
        if video_id in selected_ids:
            selected_ids.remove(video_id)
        else:
            selected_ids.add(video_id)
    elif action.startswith("duration:"):
        try:
            duration_days = int(action.split(":")[1])
        except (IndexError, ValueError):
            await query.answer("Некорректный срок")
            return
        if duration_days not in {7, 30}:
            await query.answer("Некорректный срок")
            return
    elif action == "all":
        selected_ids = set(available_ids)
    elif action == "clear":
        selected_ids = set()
    elif action == "pay":
        selected_list = sorted(selected_ids)
        if not selected_list:
            await query.answer("Выберите хотя бы одно видео")
            return
        if not available_ids:
            await query.answer("Сейчас нет доступных видео")
            return
        if not yoomoney.enabled:
            await query.message.answer("Оплата временно недоступна. Попробуйте позже.")
            await query.answer()
            return

        amount = calculate_total(len(selected_list), duration_days)
        existing = await repository.get_pending_payment_for_user(db, query.from_user.id)
        if existing:
            existing_selected = json.loads(existing["selected_video_ids"])
            existing_duration = int(existing.get("duration_days") or 30)
            if sorted(existing_selected) == selected_list and existing_duration == duration_days:
                payment_id = existing["id"]
                label = existing["label"]
                amount = existing["amount"]
                logging.getLogger("payment").info(
                    "Reusing pending payment id=%s user_id=%s amount=%s videos=%s duration_days=%s",
                    payment_id,
                    query.from_user.id,
                    amount,
                    selected_list,
                    duration_days,
                )
            else:
                existing = None

        if not existing:
            label = f"{query.from_user.id}-{uuid.uuid4().hex[:8]}"
            payment_id = await repository.create_payment(
                db,
                query.from_user.id,
                label,
                amount,
                selected_list,
                duration_days,
            )
            logging.getLogger("payment").info(
                "Created payment id=%s user_id=%s amount=%s videos=%s duration_days=%s label=%s",
                payment_id,
                query.from_user.id,
                amount,
                selected_list,
                duration_days,
                label,
            )

        pay_url = yoomoney.build_payment_url(amount, label, "Доступ к видео-урокам")
        await query.message.answer(
            "Ссылка на оплату подготовлена. После оплаты нажмите кнопку проверки.",
            reply_markup=payment_kb(pay_url, payment_id),
        )
        await state.clear()
        await query.answer()
        return

    await state.update_data(selected_ids=sorted(selected_ids), duration_days=duration_days)
    await _show_selection(query, db, state, config)


@router.callback_query(F.data.startswith("payment:check:"))
async def payment_check(
    query: CallbackQuery,
    db: Database,
    config: Settings,
    yoomoney: YooMoneyClient,
) -> None:
    try:
        payment_id = int(query.data.split(":")[2])
    except (IndexError, ValueError):
        await query.answer("Некорректный платеж")
        return

    payment = await repository.get_payment(db, payment_id)
    if not payment or payment["user_id"] != query.from_user.id:
        await query.answer("Платеж не найден")
        return

    if payment["status"] == "success":
        videos = await repository.list_accessible_videos(db, payment["user_id"])
        await query.message.answer(
            "Оплата уже подтверждена.",
            reply_markup=my_videos_kb(videos),
        )
        await query.answer()
        return

    logging.getLogger("payment").debug(
        "Manual check payment id=%s user_id=%s label=%s",
        payment_id,
        query.from_user.id,
        payment["label"],
    )
    is_paid = await yoomoney.check_payment(payment["label"])
    if not is_paid:
        await query.message.answer("Платеж пока не найден. Попробуйте позже.")
        await query.answer()
        return

    paid_at = now_ts()
    updated = await repository.mark_payment_success(db, payment_id, paid_at)
    if updated:
        selected_ids = json.loads(payment["selected_video_ids"])
        duration_days = int(payment.get("duration_days") or 30)
        await repository.grant_access(db, payment["user_id"], selected_ids, days=duration_days)
        videos = await repository.list_accessible_videos(db, payment["user_id"])
        logging.getLogger("payment").info(
            "Payment confirmed manually id=%s user_id=%s",
            payment_id,
            payment["user_id"],
        )
        await query.message.answer(
            "Оплата подтверждена. Доступ открыт на 30 дней.",
            reply_markup=my_videos_kb(videos),
        )
    else:
        logging.getLogger("payment").warning(
            "Payment already processed id=%s user_id=%s",
            payment_id,
            payment["user_id"],
        )
        await query.message.answer("Оплата уже обработана.")
    await query.answer()
