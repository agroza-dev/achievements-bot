from core.dto.chat_message_create_dto import ChatMessageCreateDTO


class ChatMessagePolicy:
    def can_add(self, message: ChatMessageCreateDTO) -> bool:
        raise NotImplementedError
