import unittest
from datetime import datetime
from unittest.mock import Mock

from telegram import Chat, MessageReactionUpdated, ReactionTypeEmoji, Update, User

from core.models import ReactionData


class TestReactionData(unittest.TestCase):
    """Test cases for ReactionData class"""

    def setUp(self):
        """Set up test fixtures before each test method."""
        # Create mock objects to simulate Telegram Update
        self.mock_user = Mock(spec=User)
        self.mock_user.id = 763524027
        self.mock_user.first_name = "Mad"
        self.mock_user.last_name = "Borodach"
        self.mock_user.is_bot = False
        self.mock_user.is_premium = True
        self.mock_user.language_code = "ru"
        self.mock_user.username = "mad_borodach"

        self.mock_chat = Mock(spec=Chat)
        self.mock_chat.id = -1003641843826
        self.mock_chat.is_forum = True
        self.mock_chat.title = "TestAchievements"
        self.mock_chat.type = "SUPERGROUP"

        self.mock_old_reaction = [
            Mock(spec=ReactionTypeEmoji),
            Mock(spec=ReactionTypeEmoji)
        ]
        self.mock_old_reaction[0].emoji = "🔥"
        self.mock_old_reaction[0].type = "EMOJI"
        self.mock_old_reaction[1].emoji = "❤"
        self.mock_old_reaction[1].type = "EMOJI"

        self.mock_new_reaction = [
            Mock(spec=ReactionTypeEmoji),
            Mock(spec=ReactionTypeEmoji),
            Mock(spec=ReactionTypeEmoji)
        ]
        self.mock_new_reaction[0].emoji = "🔥"
        self.mock_new_reaction[0].type = "EMOJI"
        self.mock_new_reaction[1].emoji = "❤"
        self.mock_new_reaction[1].type = "EMOJI"
        self.mock_new_reaction[2].emoji = "👍"
        self.mock_new_reaction[2].type = "EMOJI"

        self.mock_message_reaction = Mock(spec=MessageReactionUpdated)
        self.mock_message_reaction.user = self.mock_user
        self.mock_message_reaction.chat = self.mock_chat
        self.mock_message_reaction.message_id = 2
        self.mock_message_reaction.old_reaction = tuple(self.mock_old_reaction)
        self.mock_message_reaction.new_reaction = tuple(self.mock_new_reaction)
        self.mock_message_reaction.date = datetime(2025, 12, 23, 8, 48, 43)

        self.mock_update = Mock(spec=Update)
        self.mock_update.message_reaction = self.mock_message_reaction

    def test_from_update_creates_reaction_data_instance(self):
        """Test that from_update method creates a proper ReactionData instance"""
        reaction_data = ReactionData.from_update(self.mock_update)

        self.assertIsInstance(reaction_data, ReactionData)
        self.assertEqual(reaction_data.chat_id, -1003641843826)
        self.assertEqual(reaction_data.message_id, 2)
        self.assertEqual(reaction_data.user_id, 763524027)
        self.assertEqual(reaction_data.username, "mad_borodach")
        self.assertEqual(reaction_data.first_name, "Mad")
        self.assertEqual(reaction_data.last_name, "Borodach")
        self.assertEqual(reaction_data.is_bot, False)
        self.assertEqual(reaction_data.is_premium, True)
        self.assertEqual(reaction_data.language_code, "ru")
        self.assertEqual(reaction_data.timestamp.year, 2025)
        self.assertEqual(len(reaction_data.old_reactions), 2)
        self.assertEqual(len(reaction_data.new_reactions), 3)

    def test_from_update_with_no_old_reactions(self):
        """Test that from_update handles cases with no old reactions (reaction added)"""
        self.mock_message_reaction.old_reaction = None

        reaction_data = ReactionData.from_update(self.mock_update)

        self.assertEqual(reaction_data.action, 'added')
        self.assertEqual(len(reaction_data.old_reactions), 0)

    def test_from_update_with_no_new_reactions(self):
        """Test that from_update handles cases with no new reactions (reaction removed)"""
        self.mock_message_reaction.new_reaction = None

        reaction_data = ReactionData.from_update(self.mock_update)

        self.assertEqual(reaction_data.action, 'removed')
        self.assertEqual(len(reaction_data.new_reactions), 0)

    def test_determine_action_added(self):
        """Test that action is correctly determined as 'added'"""
        old_reactions = []
        new_reactions = [Mock(emoji="👍")]

        action = ReactionData._determine_action(old_reactions, new_reactions)

        self.assertEqual(action, 'added')

    def test_determine_action_removed(self):
        """Test that action is correctly determined as 'removed'"""
        old_reactions = [Mock(emoji="👍")]
        new_reactions = []

        action = ReactionData._determine_action(old_reactions, new_reactions)

        self.assertEqual(action, 'removed')

    def test_determine_action_updated(self):
        """Test that action is correctly determined as 'updated'"""
        old_reactions = [Mock(emoji="👍")]
        new_reactions = [Mock(emoji="❤")]

        action = ReactionData._determine_action(old_reactions, new_reactions)

        self.assertEqual(action, 'updated')

    def test_determine_action_unchanged(self):
        """Test that action is correctly determined as 'unchanged'"""
        old_reactions = [Mock(emoji="👍")]
        new_reactions = [Mock(emoji="👍")]

        action = ReactionData._determine_action(old_reactions, new_reactions)

        self.assertEqual(action, 'unchanged')

    def test_from_update_with_empty_reactions(self):
        """Test that from_update handles empty old and new reactions"""
        self.mock_message_reaction.old_reaction = ()
        self.mock_message_reaction.new_reaction = ()

        reaction_data = ReactionData.from_update(self.mock_update)

        self.assertEqual(len(reaction_data.old_reactions), 0)
        self.assertEqual(len(reaction_data.new_reactions), 0)
        self.assertEqual(reaction_data.action, 'unknown')

    def test_from_update_raises_error_when_no_message_reaction(self):
        """Test that from_update raises ValueError when no message_reaction exists"""
        mock_update_no_reaction = Mock(spec=Update)
        mock_update_no_reaction.message_reaction = None

        with self.assertRaises(ValueError) as context:
            ReactionData.from_update(mock_update_no_reaction)

        self.assertIn("Update does not contain message_reaction data", str(context.exception))


if __name__ == '__main__':
    unittest.main()
