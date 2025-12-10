from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.i18n import gettext as _

from src.keyboards.navigation import NavTarget, nav_row


def template_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=_("template.create"), callback_data="template:create")],
            [InlineKeyboardButton(text=_("template.reorder"), callback_data="template:reorder")],
            nav_row(NavTarget.RESOURCES_MENU),
        ]
    )
