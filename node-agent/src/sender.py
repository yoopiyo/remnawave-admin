"""
Отправка батчей подключений в Collector API (Admin Bot).
"""
import asyncio
import logging
from datetime import datetime

import httpx

from .config import Settings
from .models import BatchReport, ConnectionReport

logger = logging.getLogger(__name__)


class CollectorSender:
    """HTTP-клиент для отправки данных в Collector."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self._url = f"{settings.collector_url.rstrip('/')}/api/v1/connections/batch"
        self._headers = {"Authorization": f"Bearer {settings.auth_token}"}

    async def send_batch(self, connections: list[ConnectionReport]) -> bool:
        """Отправить батч подключений. Возвращает True при успехе."""
        if not connections:
            return True

        report = BatchReport(
            node_uuid=self.settings.node_uuid,
            timestamp=datetime.utcnow(),
            connections=connections,
        )
        payload = report.model_dump(mode="json")

        for attempt in range(1, self.settings.send_max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    resp = await client.post(
                        self._url,
                        json=payload,
                        headers=self._headers,
                    )
                    resp.raise_for_status()
                    logger.debug(
                        "Batch sent: %s connections, response %s",
                        len(connections),
                        resp.json(),
                    )
                    return True
            except httpx.HTTPStatusError as e:
                logger.warning(
                    "Collector returned %s on attempt %s: %s",
                    e.response.status_code,
                    attempt,
                    e.response.text,
                )
            except Exception as e:
                logger.warning("Send attempt %s failed: %s", attempt, e)

            if attempt < self.settings.send_max_retries:
                await asyncio.sleep(self.settings.send_retry_delay_seconds)

        logger.error("Failed to send batch after %s attempts", self.settings.send_max_retries)
        return False
