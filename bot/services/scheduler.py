import asyncio
import json
import logging
from typing import List

from aiogram import Bot

from bot.config.settings import Settings
from bot.db.database import Database
from bot.db import repository
from bot.keyboards.menu import my_videos_kb
from bot.services.yoomoney import YooMoneyClient
from bot.utils.time import now_ts


async def payment_checker_loop(
    bot: Bot,
    db: Database,
    yoomoney: YooMoneyClient,
    config: Settings,
) -> None:
    logger = logging.getLogger("payment_checker")
    logger.info("Payment checker started interval=%ss", config.check_payments_interval_sec)
    while True:
        try:
            pending = await repository.get_pending_payments(db)
            if pending:
                logger.debug("Pending payments count=%s", len(pending))
            for payment in pending:
                logger.debug(
                    "Checking payment id=%s user_id=%s label=%s amount=%s",
                    payment["id"],
                    payment["user_id"],
                    payment["label"],
                    payment["amount"],
                )
                is_paid = await yoomoney.check_payment(payment["label"])
                if not is_paid:
                    continue
                paid_at = now_ts()
                updated = await repository.mark_payment_success(db, payment["id"], paid_at)
                if not updated:
                    logger.warning("Payment already processed id=%s", payment["id"])
                    continue
                logger.info("Payment confirmed id=%s user_id=%s", payment["id"], payment["user_id"])
                selected_ids = json.loads(payment["selected_video_ids"])
                duration_days = int(payment.get("duration_days") or 30)
                await repository.grant_access(db, payment["user_id"], selected_ids, days=duration_days)
                video_ids = await repository.list_accessible_videos(db, payment["user_id"])
                try:
                    await bot.send_message(
                        payment["user_id"],
                        f"Оплата подтверждена. Доступ к видео открыт на {duration_days} дней.",
                        reply_markup=my_videos_kb(video_ids),
                    )
                except Exception:
                    logger.exception("Failed to notify user %s", payment["user_id"])
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Payment checker loop failed")
        await asyncio.sleep(config.check_payments_interval_sec)


async def delete_checker_loop(bot: Bot, db: Database, config: Settings) -> None:
    logger = logging.getLogger("delete_checker")
    logger.info("Delete checker started interval=%ss", config.delete_check_interval_sec)
    while True:
        try:
            now = now_ts()
            due_records = await repository.list_due_sent_videos(db, now)
            if due_records:
                logger.debug("Messages due for deletion count=%s", len(due_records))
            for record in due_records:
                try:
                    await bot.delete_message(record["chat_id"], record["message_id"])
                except Exception:
                    logger.warning(
                        "Failed to delete message %s in chat %s",
                        record["message_id"],
                        record["chat_id"],
                    )
                await repository.delete_sent_video(db, record["id"])
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Delete checker loop failed")
        await asyncio.sleep(config.delete_check_interval_sec)


async def access_notify_loop(bot: Bot, db: Database, config: Settings) -> None:
    logger = logging.getLogger("access_notify")
    logger.info(
        "Access notify started interval=%ss days=%s",
        config.access_notify_interval_sec,
        config.access_notify_days,
    )
    while True:
        try:
            now = now_ts()
            threshold = now + config.access_notify_days * 86400
            rows = await db.fetchall(
                """
                SELECT user_id, MAX(access_until) AS max_until
                FROM user_video_access
                GROUP BY user_id
                """
            )
            for row in rows:
                user_id = row["user_id"]
                max_until = row.get("max_until")
                if not max_until or max_until <= now or max_until > threshold:
                    continue
                notified_until = await repository.get_notified_until(db, user_id)
                if notified_until and int(notified_until) == int(max_until):
                    continue
                remaining_days = max(0, int((max_until - now) / 86400) + 1)
                try:
                    await bot.send_message(
                        user_id,
                        f"Доступ к урокам истекает через {remaining_days} дн. "
                        "Чтобы продлить, выберите новые уроки в меню.",
                    )
                    await repository.set_notified_until(db, user_id, int(max_until))
                except Exception:
                    logger.exception("Failed to notify user %s", user_id)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Access notify loop failed")
        await asyncio.sleep(config.access_notify_interval_sec)


def start_background_tasks(
    bot: Bot,
    db: Database,
    yoomoney: YooMoneyClient,
    config: Settings,
) -> List[asyncio.Task]:
    tasks = [
        asyncio.create_task(payment_checker_loop(bot, db, yoomoney, config)),
        asyncio.create_task(delete_checker_loop(bot, db, config)),
        asyncio.create_task(access_notify_loop(bot, db, config)),
    ]
    return tasks


async def stop_background_tasks(tasks: List[asyncio.Task]) -> None:
    for task in tasks:
        task.cancel()
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)
