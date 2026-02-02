from core.application.reactions.reaction_intent import ReactionKind


class ReactionPolicy:
    def can_add(self, existing, reaction: str) -> bool:
        raise NotImplementedError

    def rating_delta(self, reaction: str) -> int:
        raise NotImplementedError

    def tax(self, reaction: str) -> int:
        raise NotImplementedError

    def kind(self, emoji: str) -> ReactionKind:
        raise NotImplementedError
