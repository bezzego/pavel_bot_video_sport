import json
import os
from dataclasses import dataclass
from typing import Dict, List

from dotenv import load_dotenv


def _parse_admin_ids(raw: str) -> List[int]:
    if not raw:
        return []
    items = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            items.append(int(part))
        except ValueError:
            continue
    return items


def _parse_int(raw: str, default: int = 0) -> int:
    try:
        return int(raw)
    except (TypeError, ValueError):
        return default


def _parse_price_coef(raw: str) -> Dict[int, float]:
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    result: Dict[int, float] = {}
    for key, value in data.items():
        try:
            result[int(key)] = float(value)
        except (TypeError, ValueError):
            continue
    return result


def _load_video_file_ids() -> List[str]:
    return [os.getenv(f"VIDEO_{i}_FILE_ID", "") for i in range(1, 11)]


@dataclass
class Settings:
    bot_token: str
    log_level: str
    admin_ids: List[int]
    error_admin_id: int
    support_contact: str
    welcome_video_file_id: str
    corporate_password: str
    db_url: str
    yoomoney_token: str
    yoomoney_wallet: str
    price_base: int
    price_coef: Dict[int, float]
    check_payments_interval_sec: int
    delete_check_interval_sec: int
    corporate_max_attempts: int
    corporate_block_minutes: int
    video_file_ids: List[str]


def load_settings() -> Settings:
    load_dotenv()

    bot_token = os.getenv("BOT_TOKEN", "").strip()
    if not bot_token:
        raise ValueError("BOT_TOKEN is required")

    admin_ids = _parse_admin_ids(os.getenv("ADMIN_IDS", ""))
    error_admin_id = _parse_int(
        os.getenv("ERROR_ADMIN_ID", ""),
        admin_ids[0] if admin_ids else 0,
    )

    return Settings(
        bot_token=bot_token,
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        admin_ids=admin_ids,
        error_admin_id=error_admin_id,
        support_contact=os.getenv("SUPPORT_CONTACT", ""),
        welcome_video_file_id=os.getenv("WELCOME_VIDEO_FILE_ID", ""),
        corporate_password=os.getenv("CORPORATE_PASSWORD", ""),
        db_url=os.getenv("DB_URL", "sqlite+aiosqlite:///./db.sqlite3"),
        yoomoney_token=os.getenv("YOUMONEY_TOKEN", ""),
        yoomoney_wallet=os.getenv("YOUMONEY_WALLET", ""),
        price_base=int(os.getenv("PRICE_BASE", "199")),
        price_coef=_parse_price_coef(os.getenv("PRICE_COEF_JSON", "")),
        check_payments_interval_sec=int(os.getenv("CHECK_PAYMENTS_INTERVAL_SEC", "10")),
        delete_check_interval_sec=int(os.getenv("DELETE_CHECK_INTERVAL_SEC", "60")),
        corporate_max_attempts=int(os.getenv("CORPORATE_MAX_ATTEMPTS", "5")),
        corporate_block_minutes=int(os.getenv("CORPORATE_BLOCK_MINUTES", "10")),
        video_file_ids=_load_video_file_ids(),
    )
