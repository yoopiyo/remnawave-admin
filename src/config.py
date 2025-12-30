import os
from functools import lru_cache
from pathlib import Path
from typing import List

from dotenv import load_dotenv
from pydantic import AnyHttpUrl, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


class Settings(BaseSettings):
    bot_token: str = Field(..., alias="BOT_TOKEN")
    api_base_url: AnyHttpUrl = Field(..., alias="API_BASE_URL")
    api_token: str | None = Field(default=None, alias="API_TOKEN")
    default_locale: str = Field("ru", alias="DEFAULT_LOCALE")
    admins: List[int] = Field(default_factory=list, alias="ADMINS")
    log_level: str = Field("INFO", alias="LOG_LEVEL")

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        populate_by_name=True,
        extra="ignore",
    )

    @property
    def allowed_admins(self) -> set[int]:
        return set(self.admins)

    @field_validator("admins", mode="before")
    @classmethod
    def parse_admins(cls, value):
        """Парсит список администраторов из строки или списка."""
        # Логируем для отладки (используем print, так как logger может быть еще не инициализирован)
        raw_env_value = os.getenv("ADMINS", "NOT_SET")
        print(f"DEBUG parse_admins: raw_env_value={repr(raw_env_value)}, value={repr(value)}, type={type(value)}")
        
        if value is None or value == "":
            print("DEBUG parse_admins: value is None or empty, returning []")
            return []
        if isinstance(value, str):
            # Разделяем по запятой и убираем пробелы
            parts = [x.strip() for x in value.split(",")]
            print(f"DEBUG parse_admins: parts after split={parts}")
            # Фильтруем только цифры и конвертируем в int
            # Используем try/except для более надежной обработки
            admins = []
            for part in parts:
                if not part:  # Пропускаем пустые строки
                    continue
                try:
                    admin_id = int(part)
                    if admin_id > 0:  # Telegram user IDs всегда положительные
                        admins.append(admin_id)
                except ValueError:
                    # Игнорируем нечисловые значения
                    print(f"DEBUG parse_admins: failed to parse part={repr(part)}")
                    continue
            print(f"DEBUG parse_admins: final admins={admins}")
            return admins
        if isinstance(value, list):
            result = [int(x) for x in value if isinstance(x, (int, str)) and str(x).isdigit()]
            print(f"DEBUG parse_admins: value is list, result={result}")
            return result
        print(f"DEBUG parse_admins: value type not handled, returning []")
        return []


@lru_cache
def get_settings() -> Settings:
    return Settings()
