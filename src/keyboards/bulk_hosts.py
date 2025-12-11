from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.i18n import gettext as _

from src.keyboards.navigation import NavTarget, nav_row


def bulk_hosts_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=_("bulk_hosts.enable"), callback_data="bulk:hosts:enable"),
                InlineKeyboardButton(text=_("bulk_hosts.disable"), callback_data="bulk:hosts:disable"),
            ],
            [InlineKeyboardButton(text=_("bulk_hosts.delete"), callback_data="bulk:hosts:delete")],
            [InlineKeyboardButton(text=_("bulk_hosts.list"), callback_data="bulk:hosts:list")],
            [InlineKeyboardButton(text=_("bulk_hosts.prompt"), callback_data="bulk:hosts:prompt")],
            nav_row(NavTarget.BULK_MENU),
        ]
    )
