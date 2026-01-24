"""Общие утилиты для всех обработчиков."""
import asyncio

from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message
from aiogram.utils.i18n import gettext as _

from src.handlers.state import ADMIN_COMMAND_DELETE_DELAY, LAST_BOT_MESSAGES
from src.services.api_client import ApiClientError, NotFoundError, UnauthorizedError
from src.utils.auth import is_admin
from src.utils.logger import logger


async def _cleanup_message(message: Message, delay: float = 0.0) -> None:
    """Удаляет сообщение с задержкой."""
    if not isinstance(message, Message):
        return
    try:
        if delay > 0:
            await asyncio.sleep(delay)
        await message.delete()
    except Exception as exc:
        logger.warning(
            "🧹 Failed to delete message chat_id=%s message_id=%s err=%s",
            message.chat.id,
            getattr(message, "message_id", None),
            exc,
        )


def _schedule_message_cleanup(message: Message, delay: float = 0.5) -> None:
    """Планирует удаление сообщения пользователя после обработки."""
    if isinstance(message, Message):
        asyncio.create_task(_cleanup_message(message, delay=delay))


async def _send_clean_message(
    target: Message | CallbackQuery,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
    parse_mode: str | None = None,
) -> Message:
    """Отправляет или редактирует сообщение, заменяя предыдущее в чате."""
    msg = target.message if isinstance(target, CallbackQuery) else target
    bot = msg.bot
    chat_id = msg.chat.id

    prev_id = LAST_BOT_MESSAGES.get(chat_id)
    if prev_id:
        try:
            edited = await bot.edit_message_text(
                chat_id=chat_id, message_id=prev_id, text=text, reply_markup=reply_markup, parse_mode=parse_mode
            )
            return edited
        except Exception:
            try:
                await bot.delete_message(chat_id=chat_id, message_id=prev_id)
            except Exception:
                pass

    sent = await msg.answer(text, reply_markup=reply_markup, parse_mode=parse_mode)
    LAST_BOT_MESSAGES[chat_id] = sent.message_id
    return sent


async def _not_admin(message: Message | CallbackQuery) -> bool:
    """Проверяет, является ли пользователь администратором. Удаляет команды автоматически."""
    from src.handlers.state import PENDING_INPUT
    
    user_id = message.from_user.id if hasattr(message, "from_user") else None
    if user_id is None or not is_admin(user_id):
        text = _("errors.unauthorized")
        if isinstance(message, CallbackQuery):
            await message.answer(text, show_alert=True)
        else:
            await _send_clean_message(message, text)
        return True
    if isinstance(message, Message):
        is_command = bool(getattr(message, "text", "") and message.text.startswith("/"))
        # Если это ожидаемый ввод (пользователь в PENDING_INPUT), не удаляем сообщение сразу
        # Оно будет удалено после обработки в соответствующем обработчике
        is_pending_input = user_id in PENDING_INPUT
        if is_command:
            delay = ADMIN_COMMAND_DELETE_DELAY
            asyncio.create_task(_cleanup_message(message, delay=delay))
        elif not is_pending_input:
            # Для обычных текстовых сообщений (не команды и не ожидаемый ввод) удаляем сразу
            # НО: если это может быть ожидаемый ввод (например, после промпта поиска),
            # не удаляем сразу, а дадим обработчику handle_pending решить
            # Удаление произойдет в handle_pending, если это не ожидаемый ввод
            pass  # Не удаляем здесь, пусть handle_pending решает
    return False


def _get_target_user_id(target: Message | CallbackQuery) -> int | None:
    """Извлекает user_id из Message или CallbackQuery."""
    if isinstance(target, CallbackQuery):
        return target.from_user.id
    return target.from_user.id if getattr(target, "from_user", None) else None


def _clear_user_state(user_id: int | None, keep_search: bool = False, keep_subs: bool = False) -> None:
    """Очищает состояние пользователя."""
    from src.handlers.state import (
        PENDING_INPUT,
        SUBS_PAGE_BY_USER,
        USER_DETAIL_BACK_TARGET,
        USER_SEARCH_CONTEXT,
    )

    if user_id is None:
        return
    # НЕ удаляем PENDING_INPUT, если это поиск - он будет установлен в _start_user_search_flow
    # PENDING_INPUT должен сохраняться для ожидаемого ввода
    if not keep_search:
        PENDING_INPUT.pop(user_id, None)
        USER_SEARCH_CONTEXT.pop(user_id, None)
        USER_DETAIL_BACK_TARGET.pop(user_id, None)
        if not keep_subs:
            SUBS_PAGE_BY_USER.pop(user_id, None)


async def _edit_text_safe(
    message: Message, text: str, reply_markup: InlineKeyboardMarkup | None = None, parse_mode: str | None = None
) -> None:
    """Безопасно редактирует текст сообщения, обрабатывая ошибки."""
    from aiogram.exceptions import TelegramBadRequest

    try:
        await message.edit_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
    except TelegramBadRequest as exc:
        if "message is not modified" in str(exc):
            # Сообщение не изменилось - это нормально, просто игнорируем
            return
        # Другие ошибки - пробуем отправить новое сообщение
        try:
            await message.delete()
        except Exception:
            pass
        await message.answer(text, reply_markup=reply_markup, parse_mode=parse_mode)
    except Exception:
        # Любая другая ошибка - пробуем отправить новое сообщение
        try:
            await message.delete()
        except Exception:
            pass
        await message.answer(text, reply_markup=reply_markup, parse_mode=parse_mode)


def _get_error_message(exc: Exception, include_code: bool = True, include_hint: bool = True) -> str:
    """Возвращает понятное сообщение об ошибке на основе типа исключения.
    
    Args:
        exc: Исключение для обработки
        include_code: Включать ли код ошибки в сообщение
        include_hint: Включать ли подсказку по исправлению
    
    Returns:
        Форматированное сообщение об ошибке
    """
    from src.services.api_client import (
        ApiClientError,
        NetworkError,
        NotFoundError,
        RateLimitError,
        ServerError,
        TimeoutError,
        UnauthorizedError,
        ValidationError,
    )
    
    # Определяем базовое сообщение, код и подсказку
    message = ""
    error_code = ""
    hint = ""
    
    if isinstance(exc, UnauthorizedError):
        message = _("errors.unauthorized")
        error_code = exc.code
        hint = _("errors.hint_unauthorized")
    elif isinstance(exc, NotFoundError):
        message = _("errors.not_found")
        error_code = exc.code
        hint = _("errors.hint_not_found")
    elif isinstance(exc, TimeoutError):
        message = _("errors.timeout_error")
        error_code = exc.code
        hint = _("errors.hint_timeout")
    elif isinstance(exc, NetworkError):
        message = _("errors.network_error")
        error_code = exc.code
        hint = _("errors.hint_network")
    elif isinstance(exc, RateLimitError):
        message = _("errors.rate_limit")
        error_code = exc.code
        hint = _("errors.hint_rate_limit")
    elif isinstance(exc, ServerError):
        message = _("errors.server_error")
        error_code = exc.code
        hint = _("errors.hint_server")
    elif isinstance(exc, ValidationError):
        message = _("errors.validation_error")
        error_code = exc.code
        # Для ошибок валидации добавляем информацию о поле, если есть
        if exc.field:
            hint = _("errors.hint_validation_field").format(field=exc.field)
        else:
            hint = _("errors.hint_validation")
    elif isinstance(exc, ApiClientError):
        # Общая ошибка API
        message = _("errors.generic")
        error_code = getattr(exc, "code", "ERR_API_000")
        hint = _("errors.hint_generic")
    else:
        # Для других типов ошибок возвращаем общее сообщение
        message = _("errors.generic")
        error_code = "ERR_UNK_001"
        hint = _("errors.hint_generic")
    
    # Формируем финальное сообщение
    parts = [message]
    
    if include_hint and hint:
        parts.append(f"\n💡 {hint}")
    
    if include_code and error_code:
        parts.append(f"\n🔢 Код: `{error_code}`")
    
    return "".join(parts)

