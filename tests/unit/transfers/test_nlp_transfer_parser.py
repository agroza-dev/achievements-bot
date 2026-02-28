import pytest

from core.application.transfers.nlp_transfer_parser import NLPTransferParser
from core.application.transfers.transfer_intent import TransferDirection


@pytest.fixture
def parser() -> NLPTransferParser:
    """Фикстура для создания парсера."""
    return NLPTransferParser()


class TestNLPTransferParser:
    """Тесты для NLPTransferParser."""

    def test_positive_with_trigger_and_name(self, parser: NLPTransferParser):
        """Вася, лови 10 очков — явный триггер."""
        result = parser.parse("Вася, лови 10 очков")

        assert result is not None
        assert result.amount == 10
        assert result.direction == TransferDirection.POSITIVE

    def test_positive_with_peredai(self, parser: NLPTransferParser):
        """Передай Саше 20 баллов."""
        result = parser.parse("Передай Саше 20 баллов")

        assert result is not None
        assert result.amount == 20
        assert result.direction == TransferDirection.POSITIVE

    def test_negative_with_trigger(self, parser: NLPTransferParser):
        """Списать 5 у Пети."""
        result = parser.parse("Списать 5 у Пети")

        assert result is not None
        assert result.amount == 5
        assert result.direction == TransferDirection.NEGATIVE

    def test_simple_positive_number_only(self, parser: NLPTransferParser):
        """+10 — только число со знаком."""
        result = parser.parse("+10")

        assert result is not None
        assert result.amount == 10
        assert result.direction == TransferDirection.POSITIVE

    def test_simple_negative_number_only(self, parser: NLPTransferParser):
        """-5 — только число со знаком."""
        result = parser.parse("-5")

        assert result is not None
        assert result.amount == 5
        assert result.direction == TransferDirection.NEGATIVE

    def test_too_long_message(self, parser: NLPTransferParser):
        """Сообщения длиннее 150 символов игнорируются."""
        long_text = (
            "Это очень длинное сообщение которое точно больше ста пятидесяти символов "
            "и поэтому не должно обрабатываться парсером трансферов"
        )
        result = parser.parse(long_text)

        assert result is None

    def test_long_message_within_limit(self, parser: NLPTransferParser):
        """Сообщения в пределах 150 символов обрабатываются."""
        # Ровно 150 символов или меньше
        text = "Вася, лови 10 очков от всей души! Это очень щедрый подарок тебе на день рождения"
        result = parser.parse(text)

        assert result is not None
        assert result.amount == 10
        assert result.direction == TransferDirection.POSITIVE

    def test_no_number_in_text(self, parser: NLPTransferParser):
        """Текст без чисел не парсится."""
        result = parser.parse("Привет Вася")

        assert result is None

    def test_no_trigger_no_sign(self, parser: NLPTransferParser):
        """Текст с числом, но без триггера и знака."""
        result = parser.parse("У меня есть 100 очков")

        # Нет триггера трансфера и нет знака + / -
        assert result is None

    def test_with_at_mention(self, parser: NLPTransferParser):
        """@username формат упоминания — парсится только amount/direction."""
        result = parser.parse("@vasya забери 15 очков")

        assert result is not None
        assert result.amount == 15
        assert result.direction == TransferDirection.POSITIVE

    def test_case_insensitive_trigger(self, parser: NLPTransferParser):
        """Триггеры работают в любом регистре."""
        result = parser.parse("ВАСЯ, ЛОВИ 25 ОЧКОВ")

        assert result is not None
        assert result.amount == 25
        assert result.direction == TransferDirection.POSITIVE

    def test_gift_synonym(self, parser: NLPTransferParser):
        """Синонимы передачи: подари."""
        result = parser.parse("Подари Кате 50 очков")

        assert result is not None
        assert result.amount == 50
        assert result.direction == TransferDirection.POSITIVE

    def test_penalty_context(self, parser: NLPTransferParser):
        """Отрицательный трансфер: штраф."""
        result = parser.parse("Штраф Петру 10 очков")

        assert result is not None
        assert result.amount == 10
        assert result.direction == TransferDirection.NEGATIVE

    def test_fallback_plus_sign(self, parser: NLPTransferParser):
        """Fallback: знак + без глаголов."""
        result = parser.parse("Васе +10 очков")

        assert result is not None
        assert result.amount == 10
        assert result.direction == TransferDirection.POSITIVE

    def test_fallback_minus_sign(self, parser: NLPTransferParser):
        """Fallback: знак - без глаголов."""
        result = parser.parse("С Васи -5 очков")

        assert result is not None
        assert result.amount == 5
        assert result.direction == TransferDirection.NEGATIVE

    def test_space_between_sign_and_number(self, parser: NLPTransferParser):
        """Пробел между знаком и числом: + 100."""
        result = parser.parse("+ 100")

        assert result is not None
        assert result.amount == 100
        assert result.direction == TransferDirection.POSITIVE
