"""
Парсер access.log Xray для получения активных подключений.

Формат лога Xray (реальный пример):
  2026/01/28 11:23:18.306521 from 188.170.87.33:20129 accepted tcp:accounts.google.com:443 [Sweden1 >> DIRECT] email: 154

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

# Формат: 2026/01/28 11:23:18.306521 from 188.170.87.33:20129 accepted tcp:... email: 154
# Парсим: timestamp, client_ip, client_port, user_id
LOG_PATTERN = re.compile(
    r"(\d{4}/\d{2}/\d{2}\s+\d{2}:\d{2}:\d{2}(?:\.\d+)?)\s+from\s+(\d+\.\d+\.\d+\.\d+):(\d+)\s+accepted.*?email:\s*(\d+)",
    re.IGNORECASE,
)


def _parse_timestamp(s: str) -> datetime:
    """Парсит Xray timestamp: 2026/01/28 11:23:18.306521 или 2026/01/28 11:23:18 -> datetime UTC."""
    try:
        s = s.strip()
        # Пробуем парсить с микросекундами
        if '.' in s:
            try:
                # Формат: 2026/01/28 11:23:18.306521
                date_part, time_part = s.split(' ', 1)
                time_base, microseconds = time_part.split('.', 1)
                # Ограничиваем микросекунды до 6 цифр
                microseconds = microseconds[:6].ljust(6, '0')
                dt = datetime.strptime(f"{date_part} {time_base}.{microseconds}", "%Y/%m/%d %H:%M:%S.%f")
                return dt
            except ValueError:
                pass
        
        # Если не получилось с микросекундами, парсим без них
        return datetime.strptime(s.split('.')[0], "%Y/%m/%d %H:%M:%S")
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
            # Проверяем размер файла
            stat = await asyncio.to_thread(self._log_path.stat)
            file_size = stat.st_size
            logger.debug("Log file exists, size: %d bytes", file_size)
            
            if file_size == 0:
                logger.debug("Log file is empty")
                return []
            
            content = await asyncio.to_thread(
                _read_tail,
                self._log_path,
                self._buffer_size,
            )
            logger.debug("Read %d bytes from log file (last %d bytes)", len(content), min(self._buffer_size, file_size))
        except OSError as e:
            logger.warning("Cannot read log file %s: %s", self._log_path, e)
            return []

        connections: list[ConnectionReport] = []
        # Группируем по (user_email, ip) и используем самое позднее время подключения
        connections_map: dict[tuple[str, str], tuple[datetime, str]] = {}
        
        lines_count = 0
        accepted_lines = 0
        matched_lines = 0

        for line in content.splitlines():
            lines_count += 1
            line = line.strip()
            if not line:
                continue
            if "accepted" not in line.lower():
                continue
            accepted_lines += 1
            match = LOG_PATTERN.search(line)
            if not match:
                logger.debug("Line matched 'accepted' but regex failed: %s", line[:100] if len(line) > 100 else line)
                continue
            matched_lines += 1
            ts_str, client_ip, client_port, user_id = match.groups()
            # Используем user_id как идентификатор (будет обработан в Collector API)
            # Временно используем формат "user_{id}" для совместимости с текущей моделью
            # Collector API будет искать пользователя по разным идентификаторам
            user_identifier = f"user_{user_id}"
            key = (user_identifier, client_ip)
            
            try:
                connected_at = _parse_timestamp(ts_str)
            except Exception:
                connected_at = datetime.utcnow()
            
            # Сохраняем самое позднее время подключения для каждой пары (user, ip)
            if key not in connections_map:
                connections_map[key] = (connected_at, user_identifier)
            else:
                existing_time, _ = connections_map[key]
                if connected_at > existing_time:
                    connections_map[key] = (connected_at, user_identifier)
        
        # Преобразуем в список ConnectionReport
        for (user_identifier, client_ip), (connected_at, _) in connections_map.items():
            connections.append(
                ConnectionReport(
                    user_email=user_identifier,
                    ip_address=client_ip,
                    node_uuid=self._node_uuid,
                    connected_at=connected_at,
                    disconnected_at=None,
                    bytes_sent=0,
                    bytes_received=0,
                )
            )

        logger.info(
            "Log parsing: total_lines=%d accepted_lines=%d matched_lines=%d connections=%d",
            lines_count,
            accepted_lines,
            matched_lines,
            len(connections)
        )
        return connections


def _read_tail(path: Path, size: int) -> str:
    """Читает последние `size` байт файла."""
    with path.open("rb") as f:
        f.seek(0, 2)
        total = f.tell()
        start = max(0, total - size)
        f.seek(start)
        return f.read().decode("utf-8", errors="replace")
