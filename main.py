import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

from bot.config.settings import load_settings
from bot.db.database import Database
from bot.db.schema import init_db
from bot.db.repository import seed_videos
from bot.handlers import router as main_router
from bot.services.scheduler import start_background_tasks, stop_background_tasks
from bot.services.yoomoney import YooMoneyClient
from bot.utils.logger import setup_logging


async def on_startup(dispatcher: Dispatcher, bot: Bot) -> None:
    config = dispatcher["config"]
    db = dispatcher["db"]
    yoomoney = dispatcher["yoomoney"]

    await yoomoney.start()
    await init_db(db)
    await seed_videos(db, config.video_file_ids)

    tasks = start_background_tasks(bot, db, yoomoney, config)
    dispatcher["tasks"] = tasks


async def on_shutdown(dispatcher: Dispatcher, bot: Bot) -> None:
    tasks = dispatcher.get("tasks", [])
    await stop_background_tasks(tasks)
    yoomoney = dispatcher["yoomoney"]
    await yoomoney.close()


async def main() -> None:
    config = load_settings()
    setup_logging(config.log_level)

    db = Database(config.db_url)
    yoomoney = YooMoneyClient(config.yoomoney_token, config.yoomoney_wallet)

    bot = Bot(
        token=config.bot_token,
        default=DefaultBotProperties(parse_mode="HTML", protect_content=True),
    )
    dispatcher = Dispatcher(storage=MemoryStorage())
    dispatcher.include_router(main_router)
    dispatcher["config"] = config
    dispatcher["db"] = db
    dispatcher["yoomoney"] = yoomoney

    dispatcher.startup.register(on_startup)
    dispatcher.shutdown.register(on_shutdown)

    logging.getLogger("aiogram.event").setLevel(logging.INFO)

    await dispatcher.start_polling(bot, db=db, config=config, yoomoney=yoomoney)


if __name__ == "__main__":
    asyncio.run(main())
