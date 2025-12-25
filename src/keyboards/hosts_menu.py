from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.i18n import gettext as _

from src.keyboards.navigation import NavTarget, nav_row


def hosts_menu_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для меню хостов."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=_("host.create"), callback_data="hosts:create")],
            nav_row(NavTarget.NODES_MENU),
        ]
    )

