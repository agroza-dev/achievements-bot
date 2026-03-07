"""
Тесты для гибридного TransferParser (regex + NLP fallback).
"""

from core.application.transfers.transfer_intent import TransferDirection
from core.application.transfers.transfer_parser import TransferParser


class TestHybridTransferParser:
    """Тесты для гибридного парсера."""

    # === Regex путь (быстрый) ===

    def test_regex_simple_positive(self):
        """Простой положительный трансфер: +10"""
        result = TransferParser.parse("+10")

        assert result is not None
        assert result.amount == 10
        assert result.direction == TransferDirection.POSITIVE

    def test_regex_simple_negative(self):
        """Простой отрицательный трансфер: -5"""
        result = TransferParser.parse("-5")

        assert result is not None
        assert result.amount == 5
        assert result.direction == TransferDirection.NEGATIVE

    def test_regex_with_space(self):
        """Пробел между знаком и числом: + 100"""
        result = TransferParser.parse("+ 100")

        assert result is not None
        assert result.amount == 100
        assert result.direction == TransferDirection.POSITIVE

    def test_regex_in_text_with_trigger(self):
        """
        Знак с числом внутри текста с глаголом-триггером.
        "даю +50 очков" → NLP найдёт триггер "давать"
        """
        result = TransferParser.parse("даю +50 очков")

        # NLP должен найти триггер "давать" и определить направление
        # Но из-за наличия "+" в тексте, direction будет POSITIVE
        assert result is not None
        assert result.amount == 50
        assert result.direction == TransferDirection.POSITIVE

    # === NLP путь (fallback) ===

    def test_nlp_trigger_catch(self):
        """NLP: глагол-триггер без знака + / -"""
        result = TransferParser.parse("Вася, лови 10 очков")

        assert result is not None
        assert result.amount == 10
        assert result.direction == TransferDirection.POSITIVE

    def test_nlp_peredai(self):
        """NLP: "передай" триггер"""
        result = TransferParser.parse("Передай Саше 20 баллов")

        assert result is not None
        assert result.amount == 20
        assert result.direction == TransferDirection.POSITIVE

    def test_nlp_negative_shtraf(self):
        """NLP: отрицательный трансфер через "штраф" """
        result = TransferParser.parse("Штраф Петру 10 очков")

        assert result is not None
        assert result.amount == 10
        assert result.direction == TransferDirection.NEGATIVE

    def test_nlp_negative_spisat(self):
        """NLP: "списать" триггер"""
        result = TransferParser.parse("Списать 5 у Пети")

        assert result is not None
        assert result.amount == 5
        assert result.direction == TransferDirection.NEGATIVE

    # === Отказ в парсинге ===

    def test_no_transfer_intent(self):
        """Сообщение без трансфер-интента"""
        result = TransferParser.parse("Привет всем!")

        assert result is None

    def test_number_without_trigger_or_sign(self):
        """Число без триггера и без знака"""
        result = TransferParser.parse("У меня 100 очков")

        assert result is None

    def test_too_long_message(self):
        """Длинные сообщения игнорируются"""
        long_text = "Это очень длинное сообщение которое точно больше пятидесяти символов и не должно парситься"
        result = TransferParser.parse(long_text)

        assert result is None

    # === Приоритет regex над NLP ===

    def test_regex_priority_over_nlp(self):
        """
        Если есть и знак + и триггер, regex срабатывает первым.
        "лови +10" → regex заберёт +10
        """
        result = TransferParser.parse("лови +10")

        assert result is not None
        assert result.amount == 10
        assert result.direction == TransferDirection.POSITIVE

    def test_regex_priority_negative(self):
        """
        Если есть и знак - и триггер, regex срабатывает первым.
        "забери -5" → regex заберёт -5
        """
        result = TransferParser.parse("забери -5")

        assert result is not None
        assert result.amount == 5
        assert result.direction == TransferDirection.NEGATIVE

    # === Спам/ссылки/мусор — не должны парситься ===

    def test_any_url_with_product_id(self):
        """
        Любая ссылка с товаром — не трансфер.
        Пример: https://www.ozon.ru/product/...
        """
        result = TransferParser.parse(
            "https://www.ozon.ru/product/podarok-muzhu-podushka-igrushka-grud18-288450186"
        )

        assert result is None

    def test_yandex_market_link(self):
        """Ссылка на Яндекс.Маркет — не трансфер."""
        result = TransferParser.parse(
            "https://market.yandex.ru/product/12345/card?sku=100500"
        )

        assert result is None

    def test_telegram_post_link(self):
        """Ссылка на пост в Telegram — не трансфер (репост)."""
        result = TransferParser.parse(
            "https://t.me/somechannel/12345"
        )

        assert result is None

    def test_youtube_link(self):
        """Ссылка на YouTube — не трансфер."""
        result = TransferParser.parse(
            "Смотри https://youtube.com/watch?v=abc123"
        )

        assert result is None

    def test_shortened_url(self):
        """Короткая ссылка — не трансфер."""
        result = TransferParser.parse(
            "Переходи по ссылке: https://bit.ly/abc123"
        )

        assert result is None

    def test_url_with_text_before(self):
        """Ссылка с текстом перед — не трансфер."""
        result = TransferParser.parse("Смотрите тут: https://ozon.ru/product/123")

        assert result is None

    def test_spam_emoji_text(self):
        """Спам с эмодзи — не трансфер."""
        result = TransferParser.parse("🔥🔥🔥 АКЦИЯ! Переходи по ссылке! 🔥🔥🔥")

        assert result is None

    def test_long_advertisement(self):
        """Длинное рекламное сообщение — не трансфер."""
        result = TransferParser.parse(
            "Продам гараж недорого! Звоните по телефону +7-999-123-45-67. "
            "Цена договорная, торг уместен. Срочно!"
        )

        assert result is None

    def test_phone_number_only(self):
        """Только номер телефона — не трансфер."""
        result = TransferParser.parse("+7-999-123-45-67")

        assert result is None

    def test_phone_with_text(self):
        """Телефон с текстом — не трансфер."""
        result = TransferParser.parse("Звоните: +7 999 123 45 67")

        assert result is None

    def test_price_not_transfer(self):
        """Указание цены — не трансфер."""
        result = TransferParser.parse("Цена: 1500 рублей за штуку")

        assert result is None

    def test_year_not_transfer(self):
        """Год — не трансфер."""
        result = TransferParser.parse("Встречаемся в 2025 году на конференции")

        assert result is None

    def test_time_not_transfer(self):
        """Время — не трансфер."""
        result = TransferParser.parse("Начало в 14:30, не опаздывайте!")

        assert result is None

    def test_room_number_not_transfer(self):
        """Номер комнаты/кабинета — не трансфер."""
        result = TransferParser.parse("Офис 305, третий этаж")

        assert result is None

    # === Тесты из promt.md ===

    # Positive кейсы
    def test_promt_lovi_100(self):
        """Лови 100 очков"""
        result = TransferParser.parse("Лови 100 очков")

        assert result is not None
        assert result.amount == 100
        assert result.direction == TransferDirection.POSITIVE

    def test_promt_prosto_tak(self):
        """просто так лови 500 очков"""
        result = TransferParser.parse("просто так лови 500 очков")

        assert result is not None
        assert result.amount == 500
        assert result.direction == TransferDirection.POSITIVE

    def test_promt_za_izobretatelnost(self):
        """за изобретательность лови + 500 баллов"""
        result = TransferParser.parse("за изобретательность лови + 500 баллов")

        assert result is not None
        assert result.amount == 500
        assert result.direction == TransferDirection.POSITIVE

    def test_promt_plus_500_gospodin(self):
        """+500 этому господину"""
        result = TransferParser.parse("+500 этому господину")

        assert result is not None
        assert result.amount == 500
        assert result.direction == TransferDirection.POSITIVE

    def test_promt_plus_1_gospodin(self):
        """+1 этому господину"""
        result = TransferParser.parse("+1 этому господину")

        assert result is not None
        assert result.amount == 1
        assert result.direction == TransferDirection.POSITIVE

    def test_promt_goditsya_plus_190(self):
        """годится, +190 этому господину за старания"""
        result = TransferParser.parse("годится, +190 этому господину за старания")

        assert result is not None
        assert result.amount == 190
        assert result.direction == TransferDirection.POSITIVE

    def test_promt_plus_500_tovarish(self):
        """+500 этому товарищу"""
        result = TransferParser.parse("+500 этому товарищу")

        assert result is not None
        assert result.amount == 500
        assert result.direction == TransferDirection.POSITIVE

    def test_promt_plus_1_tovarish(self):
        """+1 этому товарищу"""
        result = TransferParser.parse("+1 этому товарищу")

        assert result is not None
        assert result.amount == 1
        assert result.direction == TransferDirection.POSITIVE

    def test_promt_goditsya_plyus_190_tebe(self):
        """годится, плюс 190 тебе"""
        result = TransferParser.parse("годится, плюс 190 тебе")

        assert result is not None
        assert result.amount == 190
        assert result.direction == TransferDirection.POSITIVE

    def test_promt_plus_555(self):
        """+555"""
        result = TransferParser.parse("+555")

        assert result is not None
        assert result.amount == 555
        assert result.direction == TransferDirection.POSITIVE

    def test_promt_plus_100_ochkov(self):
        """+100 очков"""
        result = TransferParser.parse("+100 очков")

        assert result is not None
        assert result.amount == 100
        assert result.direction == TransferDirection.POSITIVE

    def test_promt_plus_space_101(self):
        """+ 101 очков"""
        result = TransferParser.parse("+ 101 очков")

        assert result is not None
        assert result.amount == 101
        assert result.direction == TransferDirection.POSITIVE

    def test_promt_50_gospodin(self):
        """50 очков этому господину"""
        result = TransferParser.parse("50 очков этому господину")

        # Нет триггера или знака +, поэтому не парсится
        assert result is None

    def test_promt_50_tovarish(self):
        """50 очков этому товарищу"""
        result = TransferParser.parse("50 очков этому товарищу")

        # Нет триггера или знака +, поэтому не парсится
        assert result is None

    def test_promt_21_tovarish(self):
        """21 очков этому товарищу"""
        result = TransferParser.parse("21 очков этому товарищу")

        # Нет триггера или знака +, поэтому не парсится
        assert result is None

    def test_promt_plyus_10_ochkov(self):
        """плюс 10 очков"""
        result = TransferParser.parse("плюс 10 очков")

        assert result is not None
        assert result.amount == 10
        assert result.direction == TransferDirection.POSITIVE

    def test_promt_uvelichit_reiting_100(self):
        """увеличить социальный рейтинг на 100"""
        result = TransferParser.parse("увеличить социальный рейтинг на 100")

        assert result is not None
        assert result.amount == 100
        assert result.direction == TransferDirection.POSITIVE

    def test_promt_uvelichivaem_reiting_100(self):
        """увеличиваем социальный рейтинг на 100"""
        result = TransferParser.parse("увеличиваем социальный рейтинг на 100")

        assert result is not None
        assert result.amount == 100
        assert result.direction == TransferDirection.POSITIVE

    def test_promt_rice_tovarish(self):
        """+100 мисок риса этому товарищу за поднятое настроение"""
        result = TransferParser.parse("+100 мисок риса этому товарищу за поднятое настроение и создание доброй атмосферы.")

        assert result is not None
        assert result.amount == 100
        assert result.direction == TransferDirection.POSITIVE

    # Negative кейсы
    def test_promt_minus_space_100(self):
        """- 100 очков"""
        result = TransferParser.parse("- 100 очков")

        assert result is not None
        assert result.amount == 100
        assert result.direction == TransferDirection.NEGATIVE

    def test_promt_minus_555(self):
        """-555"""
        result = TransferParser.parse("-555")

        assert result is not None
        assert result.amount == 555
        assert result.direction == TransferDirection.NEGATIVE

    def test_promt_minus_5(self):
        """-5"""
        result = TransferParser.parse("-5")

        assert result is not None
        assert result.amount == 5
        assert result.direction == TransferDirection.NEGATIVE

    def test_promt_minus_101(self):
        """-101 очков"""
        result = TransferParser.parse("-101 очков")

        assert result is not None
        assert result.amount == 101
        assert result.direction == TransferDirection.NEGATIVE

    def test_promt_minus_123(self):
        """-123 очка"""
        result = TransferParser.parse("-123 очка")

        assert result is not None
        assert result.amount == 123
        assert result.direction == TransferDirection.NEGATIVE

    def test_promt_minus_words_123(self):
        """минус 123 очка"""
        result = TransferParser.parse("минус 123 очка")

        assert result is not None
        assert result.amount == 123
        assert result.direction == TransferDirection.NEGATIVE

    def test_promt_otbirayu_100(self):
        """отбираю 100 очков"""
        result = TransferParser.parse("отбираю 100 очков")

        assert result is not None
        assert result.amount == 100
        assert result.direction == TransferDirection.NEGATIVE

    def test_promt_otnimayu_100(self):
        """отнимаю 100"""
        result = TransferParser.parse("отнимаю 100")

        assert result is not None
        assert result.amount == 100
        assert result.direction == TransferDirection.NEGATIVE

    def test_promt_minus_5_ochkov(self):
        """минус 5 очков"""
        result = TransferParser.parse("минус 5 очков")

        assert result is not None
        assert result.amount == 5
        assert result.direction == TransferDirection.NEGATIVE

    def test_promt_minus_21_ochko(self):
        """минус 21 очко"""
        result = TransferParser.parse("минус 21 очко")

        assert result is not None
        assert result.amount == 21
        assert result.direction == TransferDirection.NEGATIVE

    def test_promt_reiting_minus_500(self):
        """увеличить социальный рейтинг на -500"""
        result = TransferParser.parse("увеличить социальный рейтинг на -500 👀")

        # Знак минус в числе
        assert result is not None
        assert result.amount == 500
        assert result.direction == TransferDirection.NEGATIVE

    def test_promt_umenshaem_reiting_100(self):
        """уменьшаем социальный рейтинг на 100"""
        result = TransferParser.parse("уменьшаем социальный рейтинг на 100")

        assert result is not None
        assert result.amount == 100
        assert result.direction == TransferDirection.NEGATIVE

    def test_promt_umenshit_reiting_100(self):
        """уменьшить социальный рейтинг на 100"""
        result = TransferParser.parse("уменьшить социальный рейтинг на 100")

        assert result is not None
        assert result.amount == 100
        assert result.direction == TransferDirection.NEGATIVE

    def test_promt_rice_negative(self):
        """-130 мисок риса этому товарищу, ты сеешь смуту"""
        result = TransferParser.parse("-130 мисок риса этому товарищу, ты сеешь смуту и вносишь раздрай в наш уютный мир.")

        assert result is not None
        assert result.amount == 130
        assert result.direction == TransferDirection.NEGATIVE

    # === Тесты на ложные срабатывания (из promt.md) ===

    def test_false_positive_weather_msk(self):
        """Ложное срабатывание: @mad_borodach +3 ч к МСК"""
        result = TransferParser.parse("@mad_borodach +3 ч к МСК")

        # Не должно парситься — это не трансфер
        assert result is None

    def test_false_positive_weather_sochi(self):
        """Ложное срабатывание: Сегодня в Сочи +30"""
        result = TransferParser.parse("Сегодня в Сочи +30.А у вас какая погода @mad_borodach")

        # Не должно парситься — это не трансфер
        assert result is None

    def test_false_positive_math(self):
        """Ложное срабатывание: Сколько будет 1+1"""
        result = TransferParser.parse("Сколько будет 1+1")

        # Не должно парситься — это не трансфер
        assert result is None

    def test_false_positive_range(self):
        """Ложное срабатывание: 100-500"""
        result = TransferParser.parse("100-500")

        # Не должно парситься — это диапазон, не трансфер
        assert result is None

    # === Валидные простые форматы (из promt.md) ===

    def test_valid_simple_positive(self):
        """Валидный: +100"""
        result = TransferParser.parse("+100")

        assert result is not None
        assert result.amount == 100
        assert result.direction == TransferDirection.POSITIVE

    def test_valid_simple_negative(self):
        """Валидный: -100"""
        result = TransferParser.parse("-100")

        assert result is not None
        assert result.amount == 100
        assert result.direction == TransferDirection.NEGATIVE

    def test_valid_with_mention_positive(self):
        """Валидный: @mad_borodach +100"""
        result = TransferParser.parse("@mad_borodach +100")

        assert result is not None
        assert result.amount == 100
        assert result.direction == TransferDirection.POSITIVE

    def test_valid_with_mention_negative(self):
        """Валидный: @mad_borodach -100"""
        result = TransferParser.parse("@mad_borodach -100")

        assert result is not None
        assert result.amount == 100
        assert result.direction == TransferDirection.NEGATIVE

    def test_valid_with_mention_and_space(self):
        """Валидный: @mad_borodach +55"""
        result = TransferParser.parse("@mad_borodach +55")

        assert result is not None
        assert result.amount == 55
        assert result.direction == TransferDirection.POSITIVE

    def test_valid_with_space(self):
        """Валидный: + 100"""
        result = TransferParser.parse("+ 100")

        assert result is not None
        assert result.amount == 100
        assert result.direction == TransferDirection.POSITIVE

    # === NLP должен обрабатывать сообщения с глаголами ===

    def test_nlp_zabirayu(self):
        """NLP: @mad_borodach забираю 10"""
        result = TransferParser.parse("@mad_borodach забираю 10")

        # NLP должен найти триггер "забирать" (NEGATIVE)
        assert result is not None
        assert result.amount == 10
        assert result.direction == TransferDirection.NEGATIVE
