from collections.abc import Iterable


class ReactionDiff:
    """
    Value Object для вычисления разницы между двумя наборами реакций.
    Иммутабелен, не содержит бизнес-логики.
    """

    __slots__ = ("_added", "_removed", "_unchanged")

    def __init__(
        self,
        old_reactions: Iterable[str],
        new_reactions: Iterable[str],
    ):
        old_set: frozenset[str] = frozenset(old_reactions)
        new_set: frozenset[str] = frozenset(new_reactions)

        self._added = new_set - old_set
        self._removed = old_set - new_set
        self._unchanged = old_set & new_set

    @property
    def added(self) -> frozenset[str]:
        return self._added

    @property
    def removed(self) -> frozenset[str]:
        return self._removed

    @property
    def unchanged(self) -> frozenset[str]:
        return self._unchanged

    @property
    def has_changes(self) -> bool:
        return bool(self._added or self._removed)

    def __bool__(self) -> bool:
        """Позволяет писать: if diff:"""
        return self.has_changes
