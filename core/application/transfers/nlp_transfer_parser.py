import re

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

    MAX_LENGTH = 150

    # Глаголы/маркеры положительного трансфера (дать, передать)
    POSITIVE_TRIGGERS = {
        "дать", "давать", "передай", "передать", "отдать",
        "лови", "ловить", "забери", "забрать", "получи", "получить",
        "начисли", "начислить", "подари", "подарить", "кинь", "кидать",
        "брось", "бросать", "переведи", "перевести", "отправь", "отправить",
        "возьми", "брать", "взять",
        # Слова "плюс" и варианты
        "плюс", "plus",
        # Увеличение рейтинга
        "увеличить", "увеличивать", "увеличиваем", "увеличиваю", "увеличиваешь"
    }

    # Глаголы/маркеры отрицательного трансфера (списать, забрать)
    NEGATIVE_TRIGGERS = {
        "списать", "снимать", "отнять", "отнимать", "штраф", "штрафовать",
        "забрать", "отобрать", "вычесть", "вычитать",
        # Слова "минус"
        "минус", "minus",
        # Уменьшение рейтинга
        "уменьшить", "уменьшать", "уменьшаем", "уменьшаю", "уменьшаешь",
        # Отбирание
        "отбираю", "отбирать", "отнимаю"
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
        direction = self._extract_direction(lemmas, text)
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

    def _extract_amount(self, text: str) -> int | None:
        """Извлекает первое число из текста."""
        match = re.search(r"\d+", text)
        if match:
            return int(match.group())
        return None

    def _extract_direction(
        self,
        lemmas: list[str],
        original_text: str
    ) -> TransferDirection | None:
        """
        Определяет направление трансфера по глаголам-триггерам.

        Если триггеры не найдены, проверяем наличие '+' или '-' в тексте.
        """
        for lemma in lemmas:
            if lemma in self.POSITIVE_TRIGGERS:
                return TransferDirection.POSITIVE

            if lemma in self.NEGATIVE_TRIGGERS:
                return TransferDirection.NEGATIVE

        # Fallback: ищем явные знаки + / -
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
