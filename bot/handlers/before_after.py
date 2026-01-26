import logging
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InputMediaPhoto
from aiogram.types.input_file import FSInputFile

from bot.keyboards.menu import before_after_kb, main_menu_only_kb
from bot.services.before_after import build_collage, list_before_after_pairs
from bot.utils.cleanup import delete_last, send_and_replace, track_last

router = Router()
logger = logging.getLogger("handlers.before_after")


class BeforeAfterStates(StatesGroup):
    viewing = State()


async def _show_page(query: CallbackQuery, state: FSMContext, page: int) -> None:
    pairs = list_before_after_pairs()
    total = len(pairs)
    if total == 0:
        await send_and_replace(
            query.message,
            "Пока нет фото для раздела До/После.",
            reply_markup=main_menu_only_kb(),
        )
        await query.answer()
        return

    page = max(1, min(page, total))
    pair = pairs[page - 1]

    data = await state.get_data()
    media_message_id = data.get("media_message_id")
    caption = f"До/После"
    collage_path = build_collage(pair.before_path, pair.after_path)

    try:
        if media_message_id:
            try:
                await query.bot.edit_message_media(
                    chat_id=query.message.chat.id,
                    message_id=media_message_id,
                    media=InputMediaPhoto(media=FSInputFile(collage_path)),
                )
                await query.bot.edit_message_caption(
                    chat_id=query.message.chat.id,
                    message_id=media_message_id,
                    caption=caption,
                    reply_markup=before_after_kb(page, total),
                )
            except Exception:
                media_message_id = None

        if not media_message_id:
            await delete_last(query.bot, query.message.chat.id)
            sent = await query.message.answer_photo(
                FSInputFile(collage_path),
                caption=caption,
                reply_markup=before_after_kb(page, total),
            )
            media_message_id = sent.message_id
            track_last(query.message.chat.id, media_message_id)
    finally:
        try:
            collage_path.unlink()
        except OSError:
            logger.debug("Failed to удалить коллаж %s", collage_path, exc_info=True)

    await state.set_state(BeforeAfterStates.viewing)
    await state.update_data(
        page=page,
        media_message_id=media_message_id,
    )
    await query.answer()


@router.callback_query(F.data == "menu:before_after")
async def before_after_entry(query: CallbackQuery, state: FSMContext) -> None:
    logger.info("Before/After entry user_id=%s", query.from_user.id)
    await _show_page(query, state, page=1)


@router.callback_query(F.data.startswith("ba:page:"))
async def before_after_page(query: CallbackQuery, state: FSMContext) -> None:
    try:
        page = int(query.data.split(":")[2])
    except (IndexError, ValueError):
        await query.answer("Некорректная страница")
        return
    await _show_page(query, state, page=page)


@router.callback_query(F.data == "ba:noop")
async def before_after_noop(query: CallbackQuery) -> None:
    await query.answer()
