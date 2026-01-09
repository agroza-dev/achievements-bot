from core.dto.reaction_dto import ReactionDTO


class ReactionMapper:
    @staticmethod
    def from_record(row) -> ReactionDTO:
        return ReactionDTO(
            chat_id=row["chat_id"],
            message_id=row["message_id"],
            from_user_id=row["from_user_id"],
            to_user_id=row["to_user_id"],
            reaction=row["reaction"],
        )
