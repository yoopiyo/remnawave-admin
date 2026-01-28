"""
Конфигурация Node Agent.
Переменные окружения или .env в папке node-agent.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="AGENT_",
        extra="ignore",
    )

    # Идентификация ноды (UUID из Remnawave/Admin Bot)
    node_uuid: str

    # URL Collector API в Admin Bot (без trailing slash)
    # Пример: https://admin.example.com или http://host.docker.internal:8000
    collector_url: str

    # Токен для аутентификации агента (выдаётся в Admin Bot)
    auth_token: str

    # Интервал отправки батчей (секунды)
    interval_seconds: int = 30

    # Путь к access.log на ноде (Remnawave использует /var/log/remnanode/access.log)
    # В Docker: монтировать том с логами
    xray_log_path: str = "/var/log/remnanode/access.log"

    # Размер буфера при tail (байт) — сколько читать с конца при старте
    log_read_buffer_bytes: int = 1024 * 1024  # 1 MB

    # Retry при отправке в Collector
    send_max_retries: int = 3
    send_retry_delay_seconds: float = 5.0

    # Логирование
    log_level: str = "INFO"
