from aiogram import Router

from bot.handlers import (
    admin,
    admin_panel,
    before_after,
    corporate,
    errors,
    purchase,
    recommendations,
    start,
    support,
    videos,
)


def setup_router() -> Router:
    router = Router()
    router.include_router(start.router)
    router.include_router(corporate.router)
    router.include_router(purchase.router)
    router.include_router(videos.router)
    router.include_router(admin.router)
    router.include_router(admin_panel.router)
    router.include_router(before_after.router)
    router.include_router(recommendations.router)
    router.include_router(support.router)
    router.include_router(errors.router)
    return router


router = setup_router()
