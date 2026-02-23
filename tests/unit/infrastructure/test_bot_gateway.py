"""Тесты для BotGateway абстракции."""

import pytest

from core.infrastructure.bot.fake_bot_gateway import (
    FakeBotGateway,
    FakeChat,
    FakeChatMember,
)


@pytest.fixture
def fake_gateway():
    """Создать FakeBotGateway для тестов."""
    return FakeBotGateway()


@pytest.fixture
def fake_gateway_with_delay():
    """Создать FakeBotGateway с задержкой."""
    return FakeBotGateway(simulate_delay=True, delay_seconds=0.01)


class TestFakeBotGateway:
    """Тесты для FakeBotGateway."""

    @pytest.mark.asyncio
    async def test_send_message(self, fake_gateway: FakeBotGateway):
        """Тест отправки сообщения."""
        result = await fake_gateway.send_message(
            chat_id=123,
            text="Hello, World!",
            reply_to_message_id=456,
        )

        assert result["message_id"] == 1
        assert result["chat_id"] == 123
        assert result["text"] == "Hello, World!"
        assert result["from_user_id"] == 999999

        assert len(fake_gateway.sent_messages) == 1
        assert fake_gateway.sent_messages[0].chat_id == 123
        assert fake_gateway.sent_messages[0].text == "Hello, World!"

    @pytest.mark.asyncio
    async def test_set_message_reaction_string(self, fake_gateway: FakeBotGateway):
        """Тест установки реакции (строка)."""
        result = await fake_gateway.set_message_reaction(
            chat_id=123,
            message_id=456,
            reaction="👍",
        )

        assert result is True
        assert len(fake_gateway.set_reactions) == 1
        assert fake_gateway.set_reactions[0].chat_id == 123
        assert fake_gateway.set_reactions[0].message_id == 456
        assert fake_gateway.set_reactions[0].reaction == "👍"

    @pytest.mark.asyncio
    async def test_set_message_reaction_list(self, fake_gateway: FakeBotGateway):
        """Тест установки реакции (список)."""
        result = await fake_gateway.set_message_reaction(
            chat_id=123,
            message_id=456,
            reaction=["👍", "🔥"],
        )

        assert result is True
        assert len(fake_gateway.set_reactions) == 1
        assert fake_gateway.set_reactions[0].reaction == ["👍", "🔥"]

    @pytest.mark.asyncio
    async def test_get_chat_cached(self, fake_gateway: FakeBotGateway):
        """Тест получения чата."""
        fake_gateway.add_chat(FakeChat(id=123, title="Test Chat"))

        result = await fake_gateway.get_chat(123)

        assert result["id"] == 123
        assert result["title"] == "Test Chat"
        assert result["type"] == "supergroup"

    @pytest.mark.asyncio
    async def test_get_chat_not_exists(self, fake_gateway: FakeBotGateway):
        """Тест получения несуществующего чата (создаёт фейковый)."""
        result = await fake_gateway.get_chat(999)

        assert result["id"] == 999
        assert result["type"] == "supergroup"

    @pytest.mark.asyncio
    async def test_get_chat_member(self, fake_gateway: FakeBotGateway):
        """Тест получения участника чата."""
        fake_gateway.add_chat_member(
            FakeChatMember(user_id=456, username="testuser", status="administrator"),
            chat_id=123,
        )

        result = await fake_gateway.get_chat_member(123, 456)

        assert result["user_id"] == 456
        assert result["username"] == "testuser"
        assert result["status"] == "administrator"

    @pytest.mark.asyncio
    async def test_answer_callback_query(self, fake_gateway: FakeBotGateway):
        """Тест ответа на callback query."""
        result = await fake_gateway.answer_callback_query(
            callback_query_id="abc123",
            text="Response text",
        )

        assert result is True
        assert len(fake_gateway.callback_answers) == 1
        assert fake_gateway.callback_answers[0] == ("abc123", "Response text")

    @pytest.mark.asyncio
    async def test_clear_history(self, fake_gateway: FakeBotGateway):
        """Тест очистки истории."""
        await fake_gateway.send_message(123, "msg1")
        await fake_gateway.send_message(123, "msg2")
        await fake_gateway.set_message_reaction(123, 1, "👍")

        fake_gateway.clear_history()

        assert len(fake_gateway.sent_messages) == 0
        assert len(fake_gateway.set_reactions) == 0
        assert fake_gateway.call_count == 0

    @pytest.mark.asyncio
    async def test_get_stats(self, fake_gateway: FakeBotGateway):
        """Тест получения статистики."""
        await fake_gateway.send_message(123, "msg1")
        await fake_gateway.send_message(123, "msg2")
        await fake_gateway.set_message_reaction(123, 1, "👍")
        await fake_gateway.answer_callback_query("abc", "text")

        stats = fake_gateway.get_stats()

        assert stats["total_calls"] == 4
        assert stats["send_message"] == 2
        assert stats["set_message_reaction"] == 1
        assert stats["answer_callback_query"] == 1
        assert stats["errors"] == 0

    @pytest.mark.asyncio
    async def test_simulate_delay(self, fake_gateway_with_delay: FakeBotGateway):
        """Тест имитации задержки сети."""
        import time

        start = time.time()
        await fake_gateway_with_delay.send_message(123, "msg")
        elapsed = time.time() - start

        assert elapsed >= 0.01

    @pytest.mark.asyncio
    async def test_fail_probability(self):
        """Тест вероятности ошибки."""
        gateway = FakeBotGateway(fail_probability=1.0)

        with pytest.raises(RuntimeError, match="Simulated network error"):
            await gateway.send_message(123, "msg")

        assert gateway.error_count == 1

    @pytest.mark.asyncio
    async def test_multiple_calls_tracking(self, fake_gateway: FakeBotGateway):
        """Тест отслеживания множественных вызовов."""
        for i in range(10):
            await fake_gateway.send_message(123, f"msg{i}")

        assert len(fake_gateway.sent_messages) == 10
        assert fake_gateway.call_count == 10
        assert fake_gateway.sent_messages[-1].text == "msg9"
