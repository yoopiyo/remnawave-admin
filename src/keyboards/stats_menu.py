from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.i18n import gettext as _

from src.keyboards.navigation import NavTarget, nav_row


def stats_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=_("stats.panel_stats"), callback_data="stats:panel")],
            [InlineKeyboardButton(text=_("stats.server_stats"), callback_data="stats:server")],
            nav_row(NavTarget.SYSTEM_MENU),
        ]
    )

