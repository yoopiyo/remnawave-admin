"""
Базовый класс коллектора подключений.
"""
from abc import ABC, abstractmethod

from ..models import ConnectionReport


class BaseCollector(ABC):
    """Абстрактный коллектор — источник данных о подключениях (Xray log, Stats API и т.д.)."""

    @abstractmethod
    async def collect(self) -> list[ConnectionReport]:
        """Собрать текущие подключения. Вызывается периодически агентом."""
        ...
