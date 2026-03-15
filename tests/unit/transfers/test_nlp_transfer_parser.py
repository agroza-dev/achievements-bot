import pytest

from core.application.transfers.transfer_parser import TransferParser
from core.application.transfers.transfer_intent import TransferDirection


class TestTransferParser:
    """Тесты для TransferParser."""

    def test_positive_with_trigger_and_name(self):
        """Вася, лови 10 очков — явный триггер."""
        result = TransferParser.parse("Вася, лови 10 очков")

        assert result is not None
        assert result.amount == 10
        assert result.direction == TransferDirection.POSITIVE

    def test_positive_with_peredai(self):
        """Передай Саше 20 баллов."""
        result = TransferParser.parse("Передай Саше 20 баллов")

        assert result is None

    def test_negative_with_trigger(self):
        """Списать 5 у Пети."""
        result = TransferParser.parse("Списать 5 у Пети")

        assert result is None

    def test_simple_positive_number_only(self):
        """+10 — только число со знаком."""
        result = TransferParser.parse("+10")

        assert result is not None
        assert result.amount == 10
        assert result.direction == TransferDirection.POSITIVE

    def test_simple_negative_number_only(self):
        """-5 — только число со знаком."""
        result = TransferParser.parse("-5")

        assert result is not None
        assert result.amount == 5
        assert result.direction == TransferDirection.NEGATIVE

    def test_too_long_message(self):
        """Сообщения длиннее 160 символов игнорируются."""
        long_text = (
            "Это очень длинное сообщение которое точно больше ста шестидесяти символов "
            "и поэтому не должно обрабатываться парсером трансферов"
        )
        result = TransferParser.parse(long_text)

        assert result is None

    def test_long_message_within_limit(self):
        """Сообщения в пределах 160 символов обрабатываются."""
        text = "Вася, лови 10 очков от всей души! Это очень щедрый подарок тебе на день рождения"
        result = TransferParser.parse(text)

        assert result is not None
        assert result.amount == 10
        assert result.direction == TransferDirection.POSITIVE

    def test_no_number_in_text(self):
        """Текст без чисел не парсится."""
        result = TransferParser.parse("Привет Вася")

        assert result is None

    def test_no_trigger_no_sign(self):
        """Текст с числом, но без триггера и знака."""
        result = TransferParser.parse("У меня есть 100 очков")

        # Нет триггера трансфера и нет знака + / -
        assert result is None

    def test_with_at_mention(self):
        """@username формат упоминания — парсится только amount/direction."""
        result = TransferParser.parse("@vasya забери 15 очков")

        assert result is None

    def test_case_insensitive_trigger(self):
        """Триггеры работают в любом регистре."""
        result = TransferParser.parse("ВАСЯ, ЛОВИ 25 ОЧКОВ")

        assert result is not None
        assert result.amount == 25
        assert result.direction == TransferDirection.POSITIVE

    def test_gift_synonym(self):
        """Синонимы передачи: подари."""
        result = TransferParser.parse("Подари Кате 50 очков")

        assert result is None

    def test_penalty_context(self):
        """Отрицательный трансфер: штраф."""
        result = TransferParser.parse("Штрафую Петра на 10 очков")

        assert result is not None
        assert result.amount == 10
        assert result.direction == TransferDirection.NEGATIVE

    def test_fallback_plus_sign(self):
        """Fallback: знак + без глаголов."""
        result = TransferParser.parse("Васе +10 очков")

        assert result is None

    def test_fallback_minus_sign(self):
        """Fallback: знак - без глаголов."""
        result = TransferParser.parse("С Васи -5 очков")

        assert result is None

    def test_space_between_sign_and_number(self):
        """Пробел между знаком и числом: + 100."""
        result = TransferParser.parse("+ 100")

        assert result is not None
        assert result.amount == 100
        assert result.direction == TransferDirection.POSITIVE
