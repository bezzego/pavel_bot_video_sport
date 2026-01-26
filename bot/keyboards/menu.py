from typing import List, Sequence

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def _video_title(video: dict) -> str:
    title = (video.get("title") or "").strip()
    if title:
        if title.lower().startswith("видео"):
            return title.replace("Видео", "Урок", 1).replace("видео", "Урок", 1)
        return title
    return f"Урок {video.get('id')}"


def main_menu_kb(is_admin: bool = False) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="Корпоративный клиент", callback_data="menu:corporate"),
        InlineKeyboardButton(text="Клиент", callback_data="menu:regular"),
        width=2,
    )
    builder.row(
        InlineKeyboardButton(text="Мои видео", callback_data="menu:my_videos"),
        InlineKeyboardButton(text="Купить доступ", callback_data="menu:buy"),
        width=2,
    )
    builder.row(InlineKeyboardButton(text="До/После", callback_data="menu:before_after"))
    builder.row(InlineKeyboardButton(text="Рекомендации", callback_data="menu:recommendations"))
    builder.row(InlineKeyboardButton(text="Поддержка", callback_data="menu:support"))
    if is_admin:
        builder.row(InlineKeyboardButton(text="Админ-панель", callback_data="menu:admin"))
    return builder.as_markup()


def corporate_videos_kb(videos: Sequence[dict]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for video in videos:
        builder.add(
            InlineKeyboardButton(
                text=_video_title(video),
                callback_data=f"video:{video['id']}",
            )
        )
    builder.adjust(2)
    builder.row(InlineKeyboardButton(text="Главное меню", callback_data="menu:main"))
    return builder.as_markup()


def my_videos_kb(videos: Sequence[dict]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for video in videos:
        builder.add(
            InlineKeyboardButton(
                text=_video_title(video),
                callback_data=f"video:{video['id']}",
            )
        )
    builder.adjust(2)
    builder.row(
        InlineKeyboardButton(text="Купить доступ", callback_data="menu:buy"),
        InlineKeyboardButton(text="Главное меню", callback_data="menu:main"),
        width=2,
    )
    return builder.as_markup()


def purchase_selection_kb(
    selected_ids: List[int],
    videos: Sequence[dict],
    duration_days: int,
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for video in videos:
        video_id = video["id"]
        selected = video_id in selected_ids
        marker = "[x]" if selected else "[ ]"
        builder.add(
            InlineKeyboardButton(
                text=f"{marker} {_video_title(video)}",
                callback_data=f"sel:toggle:{video_id}",
            )
        )
    if videos:
        builder.adjust(2)
        builder.row(
            InlineKeyboardButton(text="Выбрать все", callback_data="sel:all"),
            InlineKeyboardButton(text="Очистить", callback_data="sel:clear"),
            width=2,
        )
        builder.row(
            InlineKeyboardButton(
                text=f"{'✅' if duration_days == 7 else ''} 1 неделя",
                callback_data="sel:duration:7",
            ),
            InlineKeyboardButton(
                text=f"{'✅' if duration_days == 30 else ''} 1 месяц",
                callback_data="sel:duration:30",
            ),
            width=2,
        )
        builder.row(InlineKeyboardButton(text="Оплатить", callback_data="sel:pay"))
    builder.row(InlineKeyboardButton(text="Главное меню", callback_data="menu:main"))
    return builder.as_markup()


def payment_kb(pay_url: str, payment_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="Перейти к оплате", url=pay_url))
    builder.row(
        InlineKeyboardButton(
            text="Проверить оплату",
            callback_data=f"payment:check:{payment_id}",
        )
    )
    builder.row(InlineKeyboardButton(text="Главное меню", callback_data="menu:main"))
    return builder.as_markup()


def main_menu_only_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="Главное меню", callback_data="menu:main"))
    return builder.as_markup()


def admin_panel_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="Статистика", callback_data="admin:stats"),
        InlineKeyboardButton(text="Экспорт", callback_data="admin:export"),
        width=2,
    )
    builder.row(
        InlineKeyboardButton(text="Рассылка", callback_data="admin:broadcast"),
        InlineKeyboardButton(text="Корп. -> Обычный", callback_data="admin:corp_reset"),
        width=2,
    )
    builder.row(
        InlineKeyboardButton(text="Пароль корп.", callback_data="admin:corp_password"),
        InlineKeyboardButton(text="Видео", callback_data="admin:videos"),
        width=2,
    )
    builder.row(
        InlineKeyboardButton(text="Текст покупки", callback_data="admin:intro"),
        InlineKeyboardButton(text="Главное меню", callback_data="menu:main"),
        width=2,
    )
    return builder.as_markup()


def admin_export_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="Пользователи", callback_data="admin:export:users"),
        InlineKeyboardButton(text="Платежи", callback_data="admin:export:payments"),
        width=2,
    )
    builder.row(
        InlineKeyboardButton(text="Доступы", callback_data="admin:export:access"),
        InlineKeyboardButton(text="Назад", callback_data="menu:admin"),
        width=2,
    )
    return builder.as_markup()


def admin_videos_kb(videos: Sequence[dict]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="Добавить видео", callback_data="admin:video:add"))
    for video in videos:
        builder.row(
            InlineKeyboardButton(
                text=f"Удалить {_video_title(video)}",
                callback_data=f"admin:video:del:{video['id']}",
            )
        )
    builder.row(InlineKeyboardButton(text="Назад", callback_data="menu:admin"))
    return builder.as_markup()


def admin_confirm_kb(action: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="Отправить", callback_data=f"admin:confirm:{action}"),
        InlineKeyboardButton(text="Отмена", callback_data="admin:cancel"),
        width=2,
    )
    return builder.as_markup()


def admin_cancel_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="Отмена", callback_data="admin:cancel"))
    return builder.as_markup()


def before_after_kb(page: int, total: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    prev_page = max(1, page - 1)
    next_page = min(total, page + 1)
    builder.row(
        InlineKeyboardButton(text="⬅️ Назад", callback_data=f"ba:page:{prev_page}"),
        InlineKeyboardButton(
            text=f"{page}/{total}",
            callback_data="ba:noop",
        ),
        InlineKeyboardButton(text="Вперед ➡️", callback_data=f"ba:page:{next_page}"),
        width=3,
    )
    builder.row(InlineKeyboardButton(text="Главное меню", callback_data="menu:main"))
    return builder.as_markup()
