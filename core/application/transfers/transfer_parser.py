import re

from core.application.transfers.transfer_intent import (
    TransferDirection,
    TransferIntent,
)


class TransferParser:
    _pattern = re.compile(
        r"(?P<sign>[+-])\s*(?P<amount>\d+)",
        re.IGNORECASE,
    )

    @classmethod
    def parse(cls, text: str) -> TransferIntent | None:
        match = cls._pattern.search(text)
        if not match:
            return None

        amount = int(match.group("amount"))
        sign = match.group("sign")

        direction = (
            TransferDirection.POSITIVE
            if sign == "+"
            else TransferDirection.NEGATIVE
        )

        return TransferIntent(amount=amount, direction=direction)
