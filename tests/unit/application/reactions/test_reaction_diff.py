from core.application.reactions.reaction_diff import ReactionDiff


def test_reaction_diff_added_and_removed():
    diff = ReactionDiff(
        old_reactions=["👍", "👎"],
        new_reactions=["👍", "🔥"],
    )

    assert diff.added == {"🔥"}
    assert diff.removed == {"👎"}
    assert diff.unchanged == {"👍"}
    assert diff.has_changes

def test_reaction_diff_empty():
    diff = ReactionDiff(
        old_reactions=[],
        new_reactions=[],
    )

    assert not diff.has_changes


def test_reaction_diff_all_added():
    diff = ReactionDiff(
        old_reactions=[],
        new_reactions=["👍", "🔥"],
    )

    assert diff.added == {"👍", "🔥"}
    assert diff.removed == set()
    assert diff.unchanged == set()
    assert diff.has_changes


def test_reaction_diff_all_removed():
    diff = ReactionDiff(
        old_reactions=["👍", "🔥"],
        new_reactions=[],
    )

    assert diff.added == set()
    assert diff.removed == {"👍", "🔥"}
    assert diff.unchanged == set()
    assert diff.has_changes


def test_reaction_diff_no_changes():
    diff = ReactionDiff(
        old_reactions=["👍", "🔥"],
        new_reactions=["👍", "🔥"],
    )

    assert diff.added == set()
    assert diff.removed == set()
    assert diff.unchanged == {"👍", "🔥"}
    assert not diff.has_changes


def test_reaction_diff_bool_conversion():
    diff_with_changes = ReactionDiff(
        old_reactions=["👍"],
        new_reactions=["🔥"],
    )
    assert diff_with_changes

    diff_without_changes = ReactionDiff(
        old_reactions=["👍"],
        new_reactions=["👍"],
    )
    assert not diff_without_changes
