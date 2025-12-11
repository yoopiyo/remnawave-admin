from src.config import get_settings


def is_admin(user_id: int) -> bool:
    settings = get_settings()
    # Если список админов не пустой, проверяем принадлежность
    # Если пустой, никто не является админом (безопасность по умолчанию)
    return user_id in settings.allowed_admins
