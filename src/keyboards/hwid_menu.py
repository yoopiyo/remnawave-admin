from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.i18n import gettext as _

from src.keyboards.navigation import NavTarget, nav_row


def hwid_management_keyboard(user_uuid: str, back_to: str = NavTarget.USERS_MENU) -> InlineKeyboardMarkup:
    """Клавиатура для меню управления HWID."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=_("user.edit_hwid"), callback_data=f"uef:hwid::{user_uuid}"),
            ],
            [
                InlineKeyboardButton(text=_("user.hwid_devices"), callback_data=f"user_hwid:{user_uuid}"),
            ],
            nav_row(back_to),
        ]
    )
