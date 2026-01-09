from core.dto.chat_message_dto import ChatMessageDTO


class ChatMessageMapper:
    @staticmethod
    def from_record(row) -> ChatMessageDTO:
        return ChatMessageDTO(
            id=row["id"],
            chat_id=row["chat_id"],
            tg_message_id=row["tg_message_id"],
            author_user_id=row["author_user_id"],
            message_type=row["message_type"],
            message_meta=row["message_meta"],
            created_at=row["created_at"],
            stored_at=row["stored_at"],
        )
