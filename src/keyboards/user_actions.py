from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.i18n import gettext as _

from src.keyboards.navigation import NavTarget, nav_row


def user_actions_keyboard(user_uuid: str, status: str, back_to: str = NavTarget.USERS_MENU) -> InlineKeyboardMarkup:
    toggle_action = "enable" if status == "DISABLED" else "disable"
    toggle_text = _("actions.enable") if status == "DISABLED" else _("actions.disable")
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=toggle_text, callback_data=f"user:{user_uuid}:{toggle_action}"),
                InlineKeyboardButton(text=_("actions.reset_traffic"), callback_data=f"user:{user_uuid}:reset"),
            ],
            [
                InlineKeyboardButton(text=_("actions.revoke"), callback_data=f"user:{user_uuid}:revoke"),
                InlineKeyboardButton(text=_("user.configs_button"), callback_data=f"user_configs:{user_uuid}"),
            ],
            [
                InlineKeyboardButton(text=_("user.edit"), callback_data=f"user_edit:{user_uuid}"),
            ],
            nav_row(back_to),
        ]
    )


def user_edit_keyboard(user_uuid: str, back_to: str = NavTarget.USERS_MENU) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=_("user.edit_status_active"), callback_data=f"uef:status:ACTIVE:{user_uuid}"),
                InlineKeyboardButton(text=_("user.edit_status_disabled"), callback_data=f"uef:status:DISABLED:{user_uuid}"),
            ],
            [
                InlineKeyboardButton(text=_("user.edit_traffic_limit"), callback_data=f"uef:traffic::{user_uuid}"),
                InlineKeyboardButton(text=_("user.edit_strategy"), callback_data=f"uef:strategy::{user_uuid}"),
            ],
            [
                InlineKeyboardButton(text="NO_RESET", callback_data=f"uef:strategy:NO_RESET:{user_uuid}"),
                InlineKeyboardButton(text="DAY", callback_data=f"uef:strategy:DAY:{user_uuid}"),
                InlineKeyboardButton(text="WEEK", callback_data=f"uef:strategy:WEEK:{user_uuid}"),
                InlineKeyboardButton(text="MONTH", callback_data=f"uef:strategy:MONTH:{user_uuid}"),
            ],
            [
                InlineKeyboardButton(text=_("user.edit_expire"), callback_data=f"uef:expire::{user_uuid}"),
                InlineKeyboardButton(text=_("user.edit_hwid"), callback_data=f"uef:hwid::{user_uuid}"),
            ],
            [
                InlineKeyboardButton(text=_("user.edit_description"), callback_data=f"uef:description::{user_uuid}"),
                InlineKeyboardButton(text=_("user.edit_tag"), callback_data=f"uef:tag::{user_uuid}"),
            ],
            [
                InlineKeyboardButton(text=_("user.edit_telegram"), callback_data=f"uef:telegram::{user_uuid}"),
                InlineKeyboardButton(text=_("user.edit_email"), callback_data=f"uef:email::{user_uuid}"),
            ],
            nav_row(back_to),
        ]
    )
