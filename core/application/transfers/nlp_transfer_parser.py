import re
from typing import ClassVar, Final

import pymorphy3

from core.application.transfers.transfer_intent import (
    TransferDirection,
    TransferIntent,
)


class NLPTransferParser:
    """
    NLP-парсер трансферов на основе pymorphy3.

    Обрабатывает только сообщения до 150 символов — более длинные
    скорее всего не относятся к трансферам.

    Извлекает только amount и direction.
    Получатель определяется отдельно через:
    - reply_to_message (автор сообщения)
    - @username mentions (из Telegram entities)
    """

    MAX_LENGTH: Final[int] = 150

    # Глаголы/маркеры положительного трансфера (дать, передать)
    POSITIVE_TRIGGERS: ClassVar[set[str]] = {
        "дать", "давать", "передай", "передать", "отдать",
        "лови", "ловить", "получи", "получить",
        "начисли", "начислить", "подари", "подарить", "кинь", "кидать",
        "брось", "бросать", "переведи", "перевести", "отправь", "отправить",
        "возьми", "брать", "взять",
        # Слова "плюс" и варианты
        "плюс", "plus",
        # Увеличение рейтинга
        "увеличить", "увеличивать", "увеличиваем", "увеличиваю", "увеличиваешь",
    }

    # Глаголы/маркеры отрицательного трансфера (списать, забрать)
    NEGATIVE_TRIGGERS: ClassVar[set[str]] = {
        "списать", "снимать", "отнять", "отнимать", "штраф", "штрафовать",
        "забрать", "отобрать", "вычесть", "вычитать",
        # Слова "минус"
        "минус", "minus",
        # Уменьшение рейтинга
        "уменьшить", "уменьшать", "уменьшаем", "уменьшаю", "уменьшаешь",
        # Отбирание
        "отбираю", "отбирать", "отнимаю",
        # Забирание (отрицательное) - не императив
        "забирать", "забираю",
    }

    # Токены положительного направления (оригинальные формы, не леммы)
    POSITIVE_TOKENS: ClassVar[set[str]] = {
        "забери",  # императив "забрать" — положительное
    }

    def __init__(self):
        self._morph = pymorphy3.MorphAnalyzer()

    def parse(self, text: str) -> TransferIntent | None:
        """
        Парсит сообщение и извлекает интент трансфера.

        Args:
            text: Текст сообщения

        Returns:
            TransferIntent если найден трансфер, None иначе
        """
        # Быстрый фильтр по длине
        if len(text) > self.MAX_LENGTH:
            return None

        # Быстрый фильтр: есть ли хотя бы одно число в тексте
        if not re.search(r"\d+", text):
            return None

        # Фильтр: URL с числами (товары, ID) — не трансфер
        if self._is_url_with_id(text):
            return None

        # Фильтр: номера телефонов — не трансфер
        if self._is_phone_number(text):
            return None

        # Фильтр: математические выражения (1+1, 100-500) — не трансфер
        if self._is_math_expression(text):
            return None

        # Фильтр: погода и подобные конструкции (+30, +3 ч к МСК) — не трансфер
        if self._is_weather_or_time(text):
            return None

        # Токенизация (простая, по пробелам и знакам препинания)
        tokens = re.findall(r"[\w@]+|[^\w\s]", text, flags=re.UNICODE)

        # Лемматизация токенов
        lemmas = []
        for token in tokens:
            parsed = self._morph.parse(token)[0]
            lemmas.append(parsed.normal_form.lower())

        # Извлекаем сумму (первое число в тексте)
        amount = self._extract_amount(text)
        if amount is None or amount <= 0:
            return None

        # Извлекаем направление
        direction = self._extract_direction(lemmas, text, tokens)
        if direction is None:
            return None

        return TransferIntent(
            amount=amount,
            direction=direction,
        )

    def _is_url_with_id(self, text: str) -> bool:
        """
        Проверяет, является ли текст URL с числовым ID в конце.
        Примеры:
        - https://ozon.ru/product/12345
        - https://.../product/name-123456
        """
        # Ищем URL с числом в конце (после / или -)
        url_pattern = re.compile(
            r"https?://[^\s]+?[/\-](\d+)$"
        )
        return bool(url_pattern.search(text))

    def _is_phone_number(self, text: str) -> bool:
        """
        Проверяет, содержит ли текст номер телефона.
        Примеры: +7-999-123-45-67, +7 999 123 45 67
        """
        # Паттерн для номера телефона: +<цифры> с дефисами/пробелами
        phone_pattern = re.compile(
            r"\+\d{1,3}[\s\-]?\d{3,4}[\s\-]?\d{3,4}[\s\-]?\d{2,4}"
        )
        return bool(phone_pattern.search(text))

    def _is_math_expression(self, text: str) -> bool:
        """
        Проверяет, является ли текст математическим выражением.
        Примеры:
        - 1+1, 2+2
        - 100-500 (диапазон)
        - Сколько будет 1+1

        Не фильтрует:
        - +100, -100 (трансферы)
        - @user +100 (трансферы)
        """
        # Паттерн: число + пробел? оператор (+/-) + пробел? число
        # Это ловит 1+1, 1+ 1, 1 +1, 1 + 1, 100-500
        math_pattern = re.compile(
            r"\d+\s*[+-]\s*\d+"
        )
        return bool(math_pattern.search(text))

    def _is_weather_or_time(self, text: str) -> bool:
        """
        Проверяет, является ли текст погодой или временем.
        Примеры:
        - +30 (погода)
        - +3 ч к МСК (временная зона)
        - -5 градусов (температура)

        Паттерн: знак +/- в начале числа, за которым следует:
        - Единицы измерения температуры (градусов, °C, °F)
        - Единицы времени (ч, мин, сек, часа, минут)
        - Слова "погода", "температура", "МСК", "UTC"
        """
        # Паттерн: +/- число с последующими единицами измерения
        weather_pattern = re.compile(
            r"[+-]\s*\d+\s*(?:градусов|градуса|градус|°[CF]|ч\s+к\s+МСК|ч\s+к|часов|часа|минут|мин|секунд|сек|погод|температур|МСК|UTC)",
            re.IGNORECASE
        )
        if weather_pattern.search(text):
            return True

        # Дополнительная проверка: если в тексте есть "погода" и "+число"
        # Пример: "Сегодня в Сочи +30.А у вас какая погода"
        return bool(
            re.search(r"погод", text, re.IGNORECASE) and re.search(r"[+-]\s*\d+", text)
        )

    def _extract_amount(self, text: str) -> int | None:
        """Извлекает первое число из текста."""
        match = re.search(r"\d+", text)
        if match:
            return int(match.group())
        return None

    def _extract_direction(
        self,
        lemmas: list[str],
        original_text: str,
        tokens: list[str] | None = None
    ) -> TransferDirection | None:
        """
        Определяет направление трансфера по глаголам-триггерам.

        Если триггеры не найдены, проверяем наличие '+' или '-' в тексте.
        Явный знак '-' перед числом имеет приоритет над глаголами.
        """
        # Сначала проверяем явные знаки + / - перед числом
        # Паттерн: пробел + знак + пробел? + число (например, "на -500", "на +100")
        explicit_negative = re.search(r"\s-\s*\d+", original_text)
        explicit_positive = re.search(r"\s\+\s*\d+", original_text)

        # Если есть явный знак перед числом, он имеет приоритет
        if explicit_negative and not explicit_positive:
            return TransferDirection.NEGATIVE
        if explicit_positive and not explicit_negative:
            return TransferDirection.POSITIVE

        # Проверяем оригинальные токены на POSITIVE_TOKENS (императивы)
        if tokens:
            for token in tokens:
                if token.lower() in self.POSITIVE_TOKENS:
                    return TransferDirection.POSITIVE

        # Проверяем леммы на триггеры
        for lemma in lemmas:
            if lemma in self.POSITIVE_TRIGGERS:
                return TransferDirection.POSITIVE

            if lemma in self.NEGATIVE_TRIGGERS:
                return TransferDirection.NEGATIVE

        # Fallback: ищем явные знаки + / - в любом месте
        if "+" in original_text:
            return TransferDirection.POSITIVE
        if "-" in original_text:
            return TransferDirection.NEGATIVE

        # Если есть глагол передачи без явного направления — считаем положительным
        transfer_verbs = {
            "передать", "передай", "дать", "давай", "давать",
            "отправить", "отправь", "перевести", "переведи"
        }
        for lemma in lemmas:
            if lemma in transfer_verbs:
                return TransferDirection.POSITIVE

        return None
