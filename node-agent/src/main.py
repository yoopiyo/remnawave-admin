"""
Remnawave Node Agent — entry point.

Цикл: собрать подключения из Xray (access.log) → отправить в Collector API → sleep(interval).
"""
import asyncio
import logging
import sys
from pathlib import Path

from .config import Settings
from .collectors import XrayLogCollector
from .sender import CollectorSender

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


async def run_agent() -> None:
    settings = Settings()
    # Устанавливаем уровень логирования
    log_level = settings.log_level.upper()
    if log_level in ("DEBUG", "INFO", "WARNING", "ERROR"):
        logging.getLogger().setLevel(getattr(logging, log_level))
        logger.info("Log level set to: %s", log_level)
    else:
        logger.warning("Invalid log level '%s', using INFO", log_level)
        logging.getLogger().setLevel(logging.INFO)

    collector = XrayLogCollector(settings)
    sender = CollectorSender(settings)

    # Проверяем доступность файла логов при старте
    log_path = Path(settings.xray_log_path)
    if log_path.exists():
        stat = log_path.stat()
        logger.info(
            "Log file found: %s (size: %d bytes)",
            settings.xray_log_path,
            stat.st_size
        )
    else:
        logger.warning(
            "Log file not found: %s - agent will wait for file to appear",
            settings.xray_log_path
        )

    logger.info(
        "Node Agent started: node_uuid=%s, collector=%s, interval=%ss",
        settings.node_uuid,
        settings.collector_url,
        settings.interval_seconds,
    )

    cycle_count = 0
    while True:
        cycle_count += 1
        try:
            logger.debug("Cycle #%d: collecting connections...", cycle_count)
            connections = await collector.collect()
            
            if connections:
                logger.info("Cycle #%d: collected %d connections, sending batch...", cycle_count, len(connections))
                ok = await sender.send_batch(connections)
                if ok:
                    logger.info("Cycle #%d: batch sent successfully", cycle_count)
                else:
                    logger.warning("Cycle #%d: send failed, will retry next cycle", cycle_count)
            else:
                # Показываем INFO каждые 10 циклов, чтобы видеть что агент работает
                if cycle_count % 10 == 0:
                    logger.info("Cycle #%d: no connections found in log (agent is running)", cycle_count)
                else:
                    logger.debug("Cycle #%d: no connections found in log", cycle_count)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.exception("Cycle #%d error: %s", cycle_count, e)

        await asyncio.sleep(settings.interval_seconds)


def main() -> None:
    try:
        asyncio.run(run_agent())
    except KeyboardInterrupt:
        logger.info("Stopped by user")


if __name__ == "__main__":
    main()
