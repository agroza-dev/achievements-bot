import re

from core.application.transfers.nlp_transfer_parser import NLPTransferParser
from core.application.transfers.transfer_intent import (
    TransferDirection,
    TransferIntent,
)


class TransferParser:
    """
    Гибридный парсер трансферов.

    Сначала проверяет строгое соответствие простым форматам:
    - +100, -100
    - @username +100, @username -100
    
    Если не подошло — использует NLP-парсер для умных конструкций
    типа "Вася, лови 10 очков", "Передай Саше 20 баллов" и т.д.

    Сообщения со ссылками, телефонами и другим "мусором" игнорируются.
    """

    # Строгий паттерн для простых трансферов:
    # - +100, -100 (только знак и число, ничего больше)
    # - @username +100, @username -100 (опционально упоминание в начале)
    _strict_pattern = re.compile(
        r"^(?:@[\w_]+\s+)?(?P<sign>[+-])\s*(?P<amount>\d+)\s*$",
        re.IGNORECASE,
    )

    # Любые URL — не трансфер (реклама, репосты, товары и т.д.)
    _url_pattern = re.compile(
        r"https?://[^\s]+"
    )

    # Номера телефонов — не трансфер
    _phone_pattern = re.compile(
        r"\+\d{1,3}[\s\-]?\d{3,4}[\s\-]?\d{3,4}[\s\-]?\d{2,4}"
    )

    # Кэш для NLP-парсера (singleton)
    _nlp_parser: NLPTransferParser | None = None

    @classmethod
    def _get_nlp_parser(cls) -> NLPTransferParser:
        """Ленивая загрузка NLP-парсера."""
        if cls._nlp_parser is None:
            cls._nlp_parser = NLPTransferParser()
        return cls._nlp_parser

    @classmethod
    def parse(cls, text: str) -> TransferIntent | None:
        # 1. Фильтр: любые URL — не трансфер (реклама, репосты, товары)
        if cls._url_pattern.search(text):
            return None

        # 2. Фильтр: номера телефонов — не трансфер
        if cls._phone_pattern.search(text):
            return None

        # 3. Быстрый путь: строгое соответствие для +100, -100, @user +100
        match = cls._strict_pattern.match(text)
        if match:
            amount = int(match.group("amount"))
            sign = match.group("sign")
            direction = (
                TransferDirection.POSITIVE
                if sign == "+"
                else TransferDirection.NEGATIVE
            )
            return TransferIntent(amount=amount, direction=direction)

        # 4. Умный путь: NLP для конструкций типа "лови 10 очков"
        nlp_parser = cls._get_nlp_parser()
        return nlp_parser.parse(text)
