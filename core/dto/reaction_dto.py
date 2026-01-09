from dataclasses import dataclass


@dataclass(slots=True)
class ReactionDTO:
    chat_id: int
    message_id: int
    from_user_id: int
    to_user_id: int
    reaction: str
