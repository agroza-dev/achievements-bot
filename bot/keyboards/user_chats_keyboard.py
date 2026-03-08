from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from core.dto.chat_user_dto import UserChatDTO


def build_user_chats_keyboard(
    chats: list[UserChatDTO],
    callback_prefix: str = "stats:chat:",
) -> InlineKeyboardMarkup:
    buttons: list[list[InlineKeyboardButton]] = []

    for chat in chats:
        buttons.append(
            [
                InlineKeyboardButton(
                    text=chat.title,
                    callback_data=f"{callback_prefix}{chat.chat_id}",
                )
            ]
        )

    return InlineKeyboardMarkup(buttons)
