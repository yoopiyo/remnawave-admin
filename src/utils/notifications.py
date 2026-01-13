"""Утилиты для отправки уведомлений в Telegram топики."""
from datetime import datetime

from aiogram import Bot
from aiogram.types import Message

from src.config import get_settings
from src.utils.formatters import format_bytes, format_datetime
from src.utils.logger import logger


async def _get_squad_name_by_uuid(squad_uuid: str) -> str:
    """Получает имя сквада по UUID из API."""
    try:
        from src.services.api_client import api_client
        squads_res = await api_client.get_internal_squads()
        all_squads = squads_res.get("response", {}).get("internalSquads", [])
        # Ищем сквад по UUID
        for squad in all_squads:
            if squad.get("uuid") == squad_uuid:
                return squad.get("name", squad_uuid[:8] + "...")
        # Если не нашли, возвращаем короткий UUID
        return squad_uuid[:8] + "..."
    except Exception as exc:
        logger.debug("Failed to get squad name from API for uuid=%s: %s", squad_uuid, exc)
        # Если не удалось получить из API, возвращаем короткий UUID
        return squad_uuid[:8] + "..."


async def send_user_notification(
    bot: Bot,
    action: str,  # "created", "updated", "deleted"
    user_info: dict,
    old_user_info: dict | None = None,
) -> None:
    """Отправляет уведомление о действии с пользователем в Telegram топик."""
    settings = get_settings()
    
    if not settings.notifications_chat_id:
        logger.debug("Notifications disabled: NOTIFICATIONS_CHAT_ID not set")
        return  # Уведомления отключены
    
    logger.info(
        "Sending user notification action=%s chat_id=%s topic_id=%s",
        action,
        settings.notifications_chat_id,
        settings.notifications_topic_id,
    )
    
    try:
        info = user_info.get("response", user_info)
        
        lines = []
        
        if action == "created":
            lines.append("✅ <b>Пользователь создан</b>")
        elif action == "updated":
            lines.append("✏️ <b>Пользователь изменен</b>")
        elif action == "deleted":
            lines.append("🗑 <b>Пользователь удален</b>")
        
        lines.append("")
        lines.append(f"👤 <b>Username:</b> <code>{_esc(info.get('username', 'n/a'))}</code>")
        
        # Лимит трафика
        traffic_limit = info.get("trafficLimitBytes")
        if traffic_limit:
            traffic_display = format_bytes(traffic_limit)
        else:
            traffic_display = "Безлимит"
        
        if action == "updated" and old_user_info:
            old_info = old_user_info.get("response", old_user_info)
            old_traffic_limit = old_info.get("trafficLimitBytes")
            if old_traffic_limit:
                old_traffic_display = format_bytes(old_traffic_limit)
            else:
                old_traffic_display = "Безлимит"
            
            if old_traffic_display != traffic_display:
                lines.append(f"📶 <b>Лимит трафика:</b> <code>{old_traffic_display}</code> → <code>{traffic_display}</code>")
            else:
                lines.append(f"📶 <b>Лимит трафика:</b> <code>{traffic_display}</code>")
        else:
            lines.append(f"📶 <b>Лимит трафика:</b> <code>{traffic_display}</code>")
        
        # Дата истечения подписки
        expire_at = info.get("expireAt")
        if expire_at:
            expire_display = format_datetime(expire_at)
        else:
            expire_display = "—"
        
        if action == "updated" and old_user_info:
            old_info = old_user_info.get("response", old_user_info)
            old_expire_at = old_info.get("expireAt")
            if old_expire_at:
                old_expire_display = format_datetime(old_expire_at)
            else:
                old_expire_display = "—"
            
            if old_expire_display != expire_display:
                lines.append(f"⏳ <b>Дата истечения подписки:</b> <code>{old_expire_display}</code> → <code>{expire_display}</code>")
            else:
                lines.append(f"⏳ <b>Дата истечения подписки:</b> <code>{expire_display}</code>")
        else:
            lines.append(f"⏳ <b>Дата истечения подписки:</b> <code>{expire_display}</code>")
        
        # Ссылка на подписку
        subscription_url = info.get("subscriptionUrl")
        if subscription_url:
            if action == "updated" and old_user_info:
                old_info = old_user_info.get("response", old_user_info)
                old_subscription_url = old_info.get("subscriptionUrl")
                
                if old_subscription_url != subscription_url:
                    lines.append(f"🔗 <b>Ссылка на подписку:</b> {_esc(old_subscription_url)} → {_esc(subscription_url)}")
                else:
                    lines.append(f"🔗 <b>Ссылка на подписку:</b> {_esc(subscription_url)}")
            else:
                lines.append(f"🔗 <b>Ссылка на подписку:</b> {_esc(subscription_url)}")
        else:
            lines.append(f"🔗 <b>Ссылка на подписку:</b> —")
        
        # Внутренний сквад
        active_squads = info.get("activeInternalSquads", [])
        external_squad = info.get("externalSquadUuid")
        
        squad_display = "—"
        if active_squads:
            # Сначала проверяем, есть ли информация о сквадах в данных
            squad_info = info.get("internalSquads", [])
            if squad_info and isinstance(squad_info, list) and len(squad_info) > 0:
                # Если есть информация о сквадах, используем имя
                squad_display = squad_info[0].get("name", active_squads[0])
            else:
                # Если нет информации о сквадах, получаем имя из API
                squad_display = await _get_squad_name_by_uuid(active_squads[0])
        elif external_squad:
            squad_display = f"External: {external_squad[:8]}..."
        
        if action == "updated" and old_user_info:
            old_info = old_user_info.get("response", old_user_info)
            old_active_squads = old_info.get("activeInternalSquads", [])
            old_external_squad = old_info.get("externalSquadUuid")
            
            old_squad_display = "—"
            if old_active_squads:
                # Сначала проверяем, есть ли информация о сквадах в данных
                old_squad_info = old_info.get("internalSquads", [])
                if old_squad_info and isinstance(old_squad_info, list) and len(old_squad_info) > 0:
                    # Если есть информация о сквадах, используем имя
                    old_squad_display = old_squad_info[0].get("name", old_active_squads[0])
                else:
                    # Если нет информации о сквадах, получаем имя из API
                    old_squad_display = await _get_squad_name_by_uuid(old_active_squads[0])
            elif old_external_squad:
                old_squad_display = f"External: {old_external_squad[:8]}..."
            
            if old_squad_display != squad_display:
                lines.append(f"👥 <b>Внутренний сквад:</b> <code>{old_squad_display}</code> → <code>{squad_display}</code>")
            else:
                lines.append(f"👥 <b>Внутренний сквад:</b> <code>{squad_display}</code>")
        else:
            lines.append(f"👥 <b>Внутренний сквад:</b> <code>{squad_display}</code>")
        
        # HWID (только если есть)
        hwid_limit = info.get("hwidDeviceLimit")
        if hwid_limit is not None:
            hwid_display = "Безлимит" if hwid_limit == 0 else str(hwid_limit)
            if action == "updated" and old_user_info:
                old_info = old_user_info.get("response", old_user_info)
                old_hwid_limit = old_info.get("hwidDeviceLimit")
                if old_hwid_limit is not None:
                    old_hwid_display = "Безлимит" if old_hwid_limit == 0 else str(old_hwid_limit)
                else:
                    old_hwid_display = "—"
                
                if old_hwid_display != hwid_display:
                    lines.append(f"💻 <b>HWID:</b> <code>{old_hwid_display}</code> → <code>{hwid_display}</code>")
                else:
                    lines.append(f"💻 <b>HWID:</b> <code>{hwid_display}</code>")
            else:
                lines.append(f"💻 <b>HWID:</b> <code>{hwid_display}</code>")
        
        # Период сброса трафика
        traffic_strategy = info.get("trafficLimitStrategy") or "NO_RESET"
        strategy_display = traffic_strategy
        if action == "updated" and old_user_info:
            old_info = old_user_info.get("response", old_user_info)
            old_strategy = old_info.get("trafficLimitStrategy") or "NO_RESET"
            old_strategy_display = old_strategy
            
            if old_strategy_display != strategy_display:
                lines.append(f"🔁 <b>Период сброса трафика:</b> <code>{old_strategy_display}</code> → <code>{strategy_display}</code>")
            else:
                lines.append(f"🔁 <b>Период сброса трафика:</b> <code>{strategy_display}</code>")
        else:
            lines.append(f"🔁 <b>Период сброса трафика:</b> <code>{strategy_display}</code>")
        
        # TG ID (только если есть)
        telegram_id = info.get("telegramId")
        if telegram_id is not None:
            tg_display = str(telegram_id)
            if action == "updated" and old_user_info:
                old_info = old_user_info.get("response", old_user_info)
                old_telegram_id = old_info.get("telegramId")
                old_tg_display = str(old_telegram_id) if old_telegram_id is not None else "—"
                
                if old_tg_display != tg_display:
                    lines.append(f"✈️ <b>TG ID:</b> <code>{old_tg_display}</code> → <code>{tg_display}</code>")
                else:
                    lines.append(f"✈️ <b>TG ID:</b> <code>{tg_display}</code>")
            else:
                lines.append(f"✈️ <b>TG ID:</b> <code>{tg_display}</code>")
        
        # Описание (только если есть)
        description = info.get("description")
        if description:
            if action == "updated" and old_user_info:
                old_info = old_user_info.get("response", old_user_info)
                old_description = old_info.get("description")
                
                if old_description != description:
                    lines.append(f"📝 <b>Описание:</b> <code>{_esc(old_description or '—')}</code> → <code>{_esc(description)}</code>")
                else:
                    lines.append(f"📝 <b>Описание:</b> <code>{_esc(description)}</code>")
            else:
                lines.append(f"📝 <b>Описание:</b> <code>{_esc(description)}</code>")
        
        text = "\n".join(lines)
        
        # Отправляем в топик
        message_kwargs = {
            "chat_id": settings.notifications_chat_id,
            "text": text,
            "parse_mode": "HTML",
        }
        
        # Добавляем message_thread_id только если он указан
        if settings.notifications_topic_id is not None:
            message_kwargs["message_thread_id"] = settings.notifications_topic_id
        
        await bot.send_message(**message_kwargs)
        logger.info("User notification sent successfully action=%s chat_id=%s", action, settings.notifications_chat_id)
        
    except Exception as exc:
        logger.exception(
            "Failed to send user notification action=%s user_uuid=%s chat_id=%s topic_id=%s error=%s",
            action,
            info.get("uuid", "unknown"),
            settings.notifications_chat_id,
            settings.notifications_topic_id,
            exc,
        )


async def send_generic_notification(
    bot: Bot,
    title: str,
    message: str,
    emoji: str = "ℹ️",
) -> None:
    """Отправляет общее уведомление в Telegram топик."""
    settings = get_settings()
    
    if not settings.notifications_chat_id:
        logger.debug("Notifications disabled: NOTIFICATIONS_CHAT_ID not set")
        return
    
    try:
        text = f"{emoji} <b>{title}</b>\n\n{message}"
        
        message_kwargs = {
            "chat_id": settings.notifications_chat_id,
            "text": text,
            "parse_mode": "HTML",
        }
        
        if settings.notifications_topic_id is not None:
            message_kwargs["message_thread_id"] = settings.notifications_topic_id
        
        await bot.send_message(**message_kwargs)
        logger.info("Generic notification sent successfully title=%s", title)
        
    except Exception as exc:
        logger.exception("Failed to send generic notification title=%s error=%s", title, exc)


async def send_node_notification(
    bot: Bot,
    event: str,
    node_data: dict,
) -> None:
    """Отправляет уведомление о событии с нодой."""
    settings = get_settings()
    
    if not settings.notifications_chat_id:
        logger.debug("Notifications disabled: NOTIFICATIONS_CHAT_ID not set")
        return
    
    try:
        node_info = node_data.get("response", node_data) if isinstance(node_data, dict) else node_data
        
        lines = []
        
        # Определяем заголовок по типу события
        event_titles = {
            "node.created": "🆕 <b>Нода создана</b>",
            "node.modified": "✏️ <b>Нода изменена</b>",
            "node.disabled": "❌ <b>Нода отключена</b>",
            "node.enabled": "✅ <b>Нода включена</b>",
            "node.deleted": "🗑 <b>Нода удалена</b>",
            "node.connection_lost": "🔴 <b>Потеряно соединение с нодой</b>",
            "node.connection_restored": "🟢 <b>Соединение с нодой восстановлено</b>",
            "node.traffic_notify": "📊 <b>Уведомление о трафике ноды</b>",
        }
        
        lines.append(event_titles.get(event, f"ℹ️ <b>Событие ноды: {event}</b>"))
        lines.append("")
        
        # Информация о ноде
        node_name = node_info.get("name", "n/a")
        node_uuid = node_info.get("uuid", "n/a")
        address = node_info.get("address", "—")
        port = node_info.get("port", "—")
        country = node_info.get("countryCode", "—")
        status = node_info.get("status", "—")
        
        lines.append(f"🖥 <b>Название:</b> <code>{_esc(node_name)}</code>")
        lines.append(f"🆔 <b>UUID:</b> <code>{node_uuid[:8]}...</code>")
        lines.append(f"🌐 <b>Адрес:</b> <code>{_esc(str(address))}</code>")
        if port != "—":
            lines.append(f"🔌 <b>Порт:</b> <code>{port}</code>")
        if country != "—":
            lines.append(f"🌍 <b>Страна:</b> <code>{country}</code>")
        if status != "—":
            lines.append(f"📊 <b>Статус:</b> <code>{status}</code>")
        
        # Трафик (если есть)
        traffic_limit = node_info.get("trafficLimitBytes")
        if traffic_limit:
            lines.append(f"📶 <b>Лимит трафика:</b> <code>{format_bytes(traffic_limit)}</code>")
        
        text = "\n".join(lines)
        
        message_kwargs = {
            "chat_id": settings.notifications_chat_id,
            "text": text,
            "parse_mode": "HTML",
        }
        
        if settings.notifications_topic_id is not None:
            message_kwargs["message_thread_id"] = settings.notifications_topic_id
        
        await bot.send_message(**message_kwargs)
        logger.info("Node notification sent successfully event=%s node_uuid=%s", event, node_uuid)
        
    except Exception as exc:
        logger.exception("Failed to send node notification event=%s error=%s", event, exc)


async def send_service_notification(
    bot: Bot,
    event: str,
    event_data: dict,
) -> None:
    """Отправляет уведомление о событии сервиса."""
    settings = get_settings()
    
    if not settings.notifications_chat_id:
        logger.debug("Notifications disabled: NOTIFICATIONS_CHAT_ID not set")
        return
    
    try:
        lines = []
        
        event_titles = {
            "service.panel_started": "🚀 <b>Панель запущена</b>",
            "service.login_attempt_failed": "⚠️ <b>Неудачная попытка входа</b>",
            "service.login_attempt_success": "✅ <b>Успешный вход</b>",
        }
        
        lines.append(event_titles.get(event, f"ℹ️ <b>Событие сервиса: {event}</b>"))
        lines.append("")
        
        # Дополнительная информация
        if event == "service.login_attempt_failed" or event == "service.login_attempt_success":
            username = event_data.get("username", "—")
            ip = event_data.get("ip", "—")
            user_agent = event_data.get("userAgent", "—")
            
            lines.append(f"👤 <b>Username:</b> <code>{_esc(username)}</code>")
            if ip != "—":
                lines.append(f"🌐 <b>IP:</b> <code>{_esc(ip)}</code>")
            if user_agent != "—":
                lines.append(f"🔍 <b>User Agent:</b> <code>{_esc(user_agent[:50])}</code>")
        
        text = "\n".join(lines)
        
        message_kwargs = {
            "chat_id": settings.notifications_chat_id,
            "text": text,
            "parse_mode": "HTML",
        }
        
        if settings.notifications_topic_id is not None:
            message_kwargs["message_thread_id"] = settings.notifications_topic_id
        
        await bot.send_message(**message_kwargs)
        logger.info("Service notification sent successfully event=%s", event)
        
    except Exception as exc:
        logger.exception("Failed to send service notification event=%s error=%s", event, exc)


async def send_hwid_notification(
    bot: Bot,
    event: str,
    event_data: dict,
) -> None:
    """Отправляет уведомление о HWID устройстве."""
    settings = get_settings()
    
    if not settings.notifications_chat_id:
        logger.debug("Notifications disabled: NOTIFICATIONS_CHAT_ID not set")
        return
    
    try:
        lines = []
        
        event_titles = {
            "user_hwid_devices.added": "➕ <b>HWID устройство добавлено</b>",
            "user_hwid_devices.deleted": "➖ <b>HWID устройство удалено</b>",
        }
        
        lines.append(event_titles.get(event, f"💻 <b>Событие HWID: {event}</b>"))
        lines.append("")
        
        # Информация о пользователе
        user_data = event_data.get("user", {})
        hwid_data = event_data.get("hwidDevice", {})
        
        if user_data:
            username = user_data.get("username", "n/a")
            user_uuid = user_data.get("uuid", "n/a")
            lines.append(f"👤 <b>Пользователь:</b> <code>{_esc(username)}</code>")
            lines.append(f"🆔 <b>UUID:</b> <code>{user_uuid[:8]}...</code>")
        
        if hwid_data:
            hwid = hwid_data.get("hwid", "—")
            created_at = hwid_data.get("createdAt")
            if hwid != "—":
                lines.append(f"💻 <b>HWID:</b> <code>{_esc(hwid[:40])}...</code>")
            if created_at:
                lines.append(f"📅 <b>Создано:</b> <code>{format_datetime(created_at)}</code>")
        
        text = "\n".join(lines)
        
        message_kwargs = {
            "chat_id": settings.notifications_chat_id,
            "text": text,
            "parse_mode": "HTML",
        }
        
        if settings.notifications_topic_id is not None:
            message_kwargs["message_thread_id"] = settings.notifications_topic_id
        
        await bot.send_message(**message_kwargs)
        logger.info("HWID notification sent successfully event=%s", event)
        
    except Exception as exc:
        logger.exception("Failed to send HWID notification event=%s error=%s", event, exc)


async def send_error_notification(
    bot: Bot,
    event: str,
    event_data: dict,
) -> None:
    """Отправляет уведомление об ошибке."""
    settings = get_settings()
    
    if not settings.notifications_chat_id:
        logger.debug("Notifications disabled: NOTIFICATIONS_CHAT_ID not set")
        return
    
    try:
        lines = []
        
        lines.append("⚠️ <b>Ошибка системы</b>")
        lines.append("")
        lines.append(f"<b>Тип:</b> <code>{_esc(event)}</code>")
        
        # Дополнительная информация
        message = event_data.get("message", "")
        if message:
            lines.append(f"<b>Сообщение:</b> <code>{_esc(message)}</code>")
        
        text = "\n".join(lines)
        
        message_kwargs = {
            "chat_id": settings.notifications_chat_id,
            "text": text,
            "parse_mode": "HTML",
        }
        
        if settings.notifications_topic_id is not None:
            message_kwargs["message_thread_id"] = settings.notifications_topic_id
        
        await bot.send_message(**message_kwargs)
        logger.info("Error notification sent successfully event=%s", event)
        
    except Exception as exc:
        logger.exception("Failed to send error notification event=%s error=%s", event, exc)


async def send_crm_notification(
    bot: Bot,
    event: str,
    event_data: dict,
) -> None:
    """Отправляет уведомление о событиях CRM (биллинг инфраструктуры)."""
    settings = get_settings()
    
    if not settings.notifications_chat_id:
        logger.debug("Notifications disabled: NOTIFICATIONS_CHAT_ID not set")
        return
    
    try:
        lines = []
        
        event_titles = {
            "crm.infra_billing_node_payment_in_7_days": "📅 <b>Оплата ноды через 7 дней</b>",
            "crm.infra_billing_node_payment_in_48hrs": "⏰ <b>Оплата ноды через 48 часов</b>",
            "crm.infra_billing_node_payment_in_24hrs": "⏰ <b>Оплата ноды через 24 часа</b>",
            "crm.infra_billing_node_payment_due_today": "🔴 <b>Оплата ноды сегодня</b>",
            "crm.infra_billing_node_payment_overdue_24hrs": "⚠️ <b>Оплата ноды просрочена на 24 часа</b>",
            "crm.infra_billing_node_payment_overdue_48hrs": "⚠️ <b>Оплата ноды просрочена на 48 часов</b>",
            "crm.infra_billing_node_payment_overdue_7_days": "🚨 <b>Оплата ноды просрочена на 7 дней</b>",
        }
        
        lines.append(event_titles.get(event, f"💰 <b>Событие CRM: {event}</b>"))
        lines.append("")
        
        # Информация о ноде и провайдере
        node_data = event_data.get("node", {})
        provider_data = event_data.get("provider", {})
        billing_data = event_data.get("billingNode", {})
        
        if node_data:
            node_name = node_data.get("name", "n/a")
            lines.append(f"🖥 <b>Нода:</b> <code>{_esc(node_name)}</code>")
        
        if provider_data:
            provider_name = provider_data.get("name", "n/a")
            lines.append(f"🏢 <b>Провайдер:</b> <code>{_esc(provider_name)}</code>")
        
        if billing_data:
            amount = billing_data.get("amount")
            next_billing_at = billing_data.get("nextBillingAt")
            if amount is not None:
                lines.append(f"💵 <b>Сумма:</b> <code>{amount}</code>")
            if next_billing_at:
                lines.append(f"📅 <b>Следующая оплата:</b> <code>{format_datetime(next_billing_at)}</code>")
        
        text = "\n".join(lines)
        
        message_kwargs = {
            "chat_id": settings.notifications_chat_id,
            "text": text,
            "parse_mode": "HTML",
        }
        
        if settings.notifications_topic_id is not None:
            message_kwargs["message_thread_id"] = settings.notifications_topic_id
        
        await bot.send_message(**message_kwargs)
        logger.info("CRM notification sent successfully event=%s", event)
        
    except Exception as exc:
        logger.exception("Failed to send CRM notification event=%s error=%s", event, exc)


def _esc(text: str) -> str:
    """Экранирует HTML символы."""
    if not text:
        return ""
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )
