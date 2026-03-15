import re
from typing import ClassVar

from core.application.transfers.transfer_intent import TransferDirection, TransferIntent


class TransferParser:
    """
    Production парсер трансферов.

    Pipeline:

        strict grammar
        → noise filters
        → token parser
        → confidence check
    """

    MAX_LENGTH = 160
    MAX_AMOUNT = 10000
    MIN_CONFIDENCE = 0.6

    TOKEN_RE = re.compile(r"@\w+|[+-]?\d+|\w+")

    URL_RE = re.compile(r"https?://")
    PHONE_RE = re.compile(r"\+\d{5,}")
    MATH_RE = re.compile(r"\d+\s*[+-]\s*\d+")

    POSITIVE_SIGN_RE = re.compile(r"\+\s*\d+")
    NEGATIVE_SIGN_RE = re.compile(r"-\s*\d+")

    POSITIVE_COMMANDS: ClassVar[set[str]]  = {
        "получай",
        "забирай",

        "отправляю",
        "начисляю",
        "увеличиваю",

        "даю",
        "отдаю",
        "дарю",

        "лови",
        "держи",

        "плюс",
    }

    NEGATIVE_COMMANDS: ClassVar[set[str]]  = {
        "штрафую",
        "штраф",
        "списываю",
        "отнимаю",
        "забираю",
        "отбираю",
        "минус",
        "вычитаю",
        "уменьшаю",
        "минусую",
    }

    STRICT_PATTERNS: ClassVar[list[re.Pattern[str]]] = [

        # @user +10
        re.compile(
            r"^(?P<user>@\w+)\s*(?P<sign>[+-])\s*(?P<amount>\d+)$"
        ),

        # +10 @user
        re.compile(
            r"^(?P<sign>[+-])\s*(?P<amount>\d+)\s*(?P<user>@\w+)$"
        ),

        # cmd @user 10
        re.compile(
            r"^(?P<cmd>\w+)\s+(?P<user>@\w+)\s+(?P<amount>\d+)$"
        ),

        # @user cmd 10
        re.compile(
            r"^(?P<user>@\w+)\s+(?P<cmd>\w+)\s+(?P<amount>\d+)$"
        ),
    ]

    @classmethod
    def parse(cls, text: str) -> TransferIntent | None:

        text = cls._normalize(text)

        if not text:
            return None

        if len(text) > cls.MAX_LENGTH:
            return None

        # 1 strict grammar
        strict = cls._parse_strict(text)

        if strict:
            return strict

        # 2 noise filters
        if cls._is_noise(text):
            return None

        # 3 token parse
        tokens = cls._tokenize(text)

        amount = cls._extract_amount(tokens)

        if not amount:
            return None

        direction = cls._detect_direction(text, tokens)

        if not direction:
            return None


        return TransferIntent(
            amount=amount,
            direction=direction,
        )

    @staticmethod
    def _normalize(text: str) -> str:

        text = text.lower()
        text = re.sub(r"\s+", " ", text)

        return text.strip()

    @classmethod
    def _parse_strict(cls, text: str) -> TransferIntent | None:

        for pattern in cls.STRICT_PATTERNS:

            m = pattern.match(text)

            if not m:
                continue

            data = m.groupdict()

            amount = int(data["amount"])

            if not cls._valid_amount(amount):
                return None

            sign = data.get("sign")
            cmd = data.get("cmd")

            direction = None

            if sign == "+":
                direction = TransferDirection.POSITIVE

            elif sign == "-":
                direction = TransferDirection.NEGATIVE

            elif cmd in cls.POSITIVE_COMMANDS:
                direction = TransferDirection.POSITIVE

            elif cmd in cls.NEGATIVE_COMMANDS:
                direction = TransferDirection.NEGATIVE

            if not direction:
                return None

            return TransferIntent(
                amount=amount,
                direction=direction,
            )

        return None

    @classmethod
    def _is_noise(cls, text: str) -> bool:

        if cls.URL_RE.search(text):
            return True

        if cls.PHONE_RE.search(text):
            return True

        return bool(cls.MATH_RE.search(text))

    @classmethod
    def _tokenize(cls, text: str) -> list[str]:

        return cls.TOKEN_RE.findall(text)

    @classmethod
    def _extract_amount(cls, tokens: list[str]) -> int | None:

        numbers = []

        for token in tokens:

            if token.lstrip("+-").isdigit():
                numbers.append(int(token.lstrip("+-")))

        if not numbers:
            return None

        value = numbers[-1]

        if not cls._valid_amount(value):
            return None

        return value

    @classmethod
    def _valid_amount(cls, value: int) -> bool:

        return 0 < value <= cls.MAX_AMOUNT


    @classmethod
    def _detect_direction(cls, text: str, tokens: list[str]):

        for token in tokens:
            if text.startswith("+") and token[1:].isdigit():
                return TransferDirection.POSITIVE

            if text.startswith("-") and token[1:].isdigit():
                return TransferDirection.NEGATIVE

        for token in tokens:

            if token in cls.POSITIVE_COMMANDS:
                return TransferDirection.POSITIVE

            if token in cls.NEGATIVE_COMMANDS:
                return TransferDirection.NEGATIVE

        return None
