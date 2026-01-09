from core.domain.messages.chat_message_policy import ChatMessagePolicy
from core.dto.chat_message_create_dto import ChatMessageCreateDTO


class DefaultChatMessagePolicy(ChatMessagePolicy):

    def can_add(self, message: ChatMessageCreateDTO) -> bool:
        return True
