from telegram.constants import ReactionEmoji

from core.application.reactions.reaction_intent import ReactionKind
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

    def kind(self, emoji: str) -> ReactionKind:
        if emoji in {
            ReactionEmoji.THUMBS_UP,
            ReactionEmoji.FIRE,
            ReactionEmoji.CLAPPING_HANDS,
            ReactionEmoji.SMILING_FACE_WITH_HEARTS,
            ReactionEmoji.GRINNING_FACE_WITH_SMILING_EYES,
            ReactionEmoji.GRINNING_FACE_WITH_STAR_EYES,
            ReactionEmoji.SMILING_FACE_WITH_HEART_SHAPED_EYES,
            ReactionEmoji.ROLLING_ON_THE_FLOOR_LAUGHING,
            ReactionEmoji.GRINNING_FACE_WITH_ONE_LARGE_AND_ONE_SMALL_EYE,
            ReactionEmoji.TROPHY,
        }:
            return ReactionKind.POSITIVE
        if emoji in {
            ReactionEmoji.THUMBS_DOWN,
            ReactionEmoji.PILL,
            ReactionEmoji.REVERSED_HAND_WITH_MIDDLE_FINGER_EXTENDED,
            ReactionEmoji.FACE_WITH_UNEVEN_EYES_AND_WAVY_MOUTH,
            ReactionEmoji.YAWNING_FACE,
            ReactionEmoji.CLOWN_FACE,
            ReactionEmoji.PILE_OF_POO,
            ReactionEmoji.FACE_WITH_OPEN_MOUTH_VOMITING,
        }:
            return ReactionKind.NEGATIVE
        return ReactionKind.NEUTRAL
