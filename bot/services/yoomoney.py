import logging
from typing import Optional
from urllib.parse import urlencode

import aiohttp


PAYMENT_URL = "https://yoomoney.ru/quickpay/confirm.xml"
HISTORY_URL = "https://yoomoney.ru/api/operation-history"


class YooMoneyClient:
    def __init__(self, token: str, wallet: str) -> None:
        self._token = token
        self._wallet = wallet
        self._session: Optional[aiohttp.ClientSession] = None
        self._logger = logging.getLogger("yoomoney")

    @property
    def enabled(self) -> bool:
        return bool(self._token and self._wallet)

    async def start(self) -> None:
        if self._session is None:
            self._session = aiohttp.ClientSession()

    async def close(self) -> None:
        if self._session is not None:
            await self._session.close()
            self._session = None

    def build_payment_url(self, amount: int, label: str, description: str) -> str:
        params = {
            "receiver": self._wallet,
            "quickpay-form": "shop",
            "targets": description,
            "paymentType": "SB",
            "sum": str(amount),
            "label": label,
        }
        url = f"{PAYMENT_URL}?{urlencode(params)}"
        self._logger.info("Built payment URL label=%s amount=%s", label, amount)
        self._logger.debug("Payment URL: %s", url)
        return url

    async def check_payment(self, label: str) -> bool:
        if not self.enabled:
            return False
        if self._session is None:
            raise RuntimeError("YooMoneyClient is not started")
        headers = {"Authorization": f"Bearer {self._token}"}
        data = {"label": label}
        self._logger.debug("Checking YooMoney payment label=%s", label)
        try:
            async with self._session.post(HISTORY_URL, data=data, headers=headers) as resp:
                if resp.status != 200:
                    self._logger.warning("YooMoney status %s for label %s", resp.status, label)
                    return False
                payload = await resp.json()
        except Exception:
            self._logger.exception("Failed to check YooMoney payment")
            return False

        for operation in payload.get("operations", []):
            if operation.get("label") == label and operation.get("status") == "success":
                self._logger.info("Payment success label=%s", label)
                return True
        self._logger.info("Payment not found or not success label=%s", label)
        return False
