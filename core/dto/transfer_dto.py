from dataclasses import dataclass


@dataclass(frozen=True)
class TransferCommandDTO:
    initiator_user_id: int
    chat_id: int
    raw_text:str
    reply_to_message_id: int|None
    mentioned_usernames: list[str]|None
