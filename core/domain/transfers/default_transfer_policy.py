import math

from core.application.transfers.transfer_intent import TransferDirection
from core.domain.transfers.transfer_policy import TransferPolicy


class DefaultTransferPolicy(TransferPolicy):
    def tax(self, amount: int, direction: TransferDirection) -> int:
        percent = {
            TransferDirection.POSITIVE: 0.1,
            TransferDirection.NEGATIVE: 0.2,
        }.get(direction, 0)

        if percent == 0:
            return 0

        raw_tax = amount * percent
        tax_in_tenths = ceil_to_tenths(raw_tax)

        # обратно в целые очки (делим на 10 с округлением вверх)
        return math.ceil(tax_in_tenths / 10)

    def get_max_transfer_amount(self) -> int:
        return 25



def ceil_to_tenths(value: float) -> int:
    """
    Округляет в большую сторону до десятых и
    возвращает значение в целых (x10).
    """
    return math.ceil(value * 10)
