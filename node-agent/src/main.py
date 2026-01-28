"""
Remnawave Node Agent — entry point.

Цикл: собрать подключения из Xray (access.log) → отправить в Collector API → sleep(interval).
"""
import asyncio
import logging
import sys

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
    if settings.log_level.upper() in ("DEBUG", "INFO", "WARNING", "ERROR"):
        logging.getLogger().setLevel(getattr(logging, settings.log_level.upper()))

    collector = XrayLogCollector(settings)
    sender = CollectorSender(settings)

    logger.info(
        "Node Agent started: node_uuid=%s, collector=%s, interval=%ss",
        settings.node_uuid,
        settings.collector_url,
        settings.interval_seconds,
    )

    while True:
        try:
            connections = await collector.collect()
            if connections:
                ok = await sender.send_batch(connections)
                if not ok:
                    logger.warning("Send failed, will retry next cycle")
            else:
                logger.debug("No connections to send")
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.exception("Cycle error: %s", e)

        await asyncio.sleep(settings.interval_seconds)


def main() -> None:
    try:
        asyncio.run(run_agent())
    except KeyboardInterrupt:
        logger.info("Stopped by user")


if __name__ == "__main__":
    main()
