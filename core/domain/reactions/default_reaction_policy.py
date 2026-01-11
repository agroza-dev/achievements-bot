from core.domain.reactions.reaction_policy import ReactionPolicy


class DefaultReactionPolicy(ReactionPolicy):
    MAX_REACTIONS = 3

    def can_add(self, existing, reaction: str) -> bool:
        if len(existing) >= self.MAX_REACTIONS:
            return False

        if any(r.reaction == reaction for r in existing):  # noqa: SIM103
            return False

        return True

    def rating_delta(self, reaction: str) -> int:
        return 1

    def tax(self, reaction: str) -> int:
        return 0
