"""
Парсер access.log Xray для получения активных подключений.

Формат лога Xray (пример):
  2026/01/27 12:00:00 [Info] app/proxyman/inbound: [user@email] 1.2.3.4:12345 accepted tcp:example.com:443

Примечание: по логам видим только connect (accepted). Disconnect и длительность
при необходимости можно выводить из других строк или считать по таймауту на стороне Collector.
"""
import asyncio
import logging
import re
from datetime import datetime
from pathlib import Path

from ..config import Settings
from ..models import ConnectionReport
from .base import BaseCollector

logger = logging.getLogger(__name__)

# Формат: 2026/01/27 12:00:00 [Info] ... [user@email] 1.2.3.4:12345 accepted
LOG_PATTERN = re.compile(
    r"(\d{4}/\d{2}/\d{2}\s+\d{2}:\d{2}:\d{2}).*?\[(\S+?@\S+?)\].*?(\d+\.\d+\.\d+\.\d+):(\d+)\s+accepted",
    re.IGNORECASE,
)


def _parse_timestamp(s: str) -> datetime:
    """Парсит Xray timestamp: 2026/01/27 12:00:00 -> datetime UTC."""
    try:
        return datetime.strptime(s.strip(), "%Y/%m/%d %H:%M:%S")
    except ValueError:
        return datetime.utcnow()


class XrayLogCollector(BaseCollector):
    """Читает access.log Xray и возвращает список подключений (accepted)."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self._log_path = Path(settings.xray_log_path)
        self._buffer_size = settings.log_read_buffer_bytes
        self._node_uuid = settings.node_uuid

    async def collect(self) -> list[ConnectionReport]:
        """Читает конец лог-файла и парсит строки с 'accepted'."""
        if not self._log_path.exists():
            logger.warning("Log file does not exist: %s", self._log_path)
            return []

        try:
            content = await asyncio.to_thread(
                _read_tail,
                self._log_path,
                self._buffer_size,
            )
        except OSError as e:
            logger.warning("Cannot read log file %s: %s", self._log_path, e)
            return []

        connections: list[ConnectionReport] = []
        seen: set[tuple[str, str]] = set()  # (user_email, ip) — дедупликация за батч

        for line in content.splitlines():
            line = line.strip()
            if not line or "accepted" not in line.lower():
                continue
            match = LOG_PATTERN.search(line)
            if not match:
                continue
            ts_str, user_email, ip, port = match.groups()
            key = (user_email, ip)
            if key in seen:
                continue
            seen.add(key)
            try:
                connected_at = _parse_timestamp(ts_str)
            except Exception:
                connected_at = datetime.utcnow()
            connections.append(
                ConnectionReport(
                    user_email=user_email,
                    ip_address=ip,
                    node_uuid=self._node_uuid,
                    connected_at=connected_at,
                    disconnected_at=None,
                    bytes_sent=0,
                    bytes_received=0,
                )
            )

        logger.debug("Collected %s connections from log", len(connections))
        return connections


def _read_tail(path: Path, size: int) -> str:
    """Читает последние `size` байт файла."""
    with path.open("rb") as f:
        f.seek(0, 2)
        total = f.tell()
        start = max(0, total - size)
        f.seek(start)
        return f.read().decode("utf-8", errors="replace")
