import math

from core.application.transfers.transfer_intent import TransferDirection
from core.domain.transfers.transfer_policy import TransferPolicy


class DefaultTransferPolicy(TransferPolicy):
    def tax(self, amount: int, direction: TransferDirection, tax_rate: float = 0.0) -> int:
        # Если налог не настроен (0%), не берём налог
        if tax_rate == 0.0:
            return 0

        # Конвертируем процент в долю (15.0 -> 0.15)
        percent = tax_rate / 100.0

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
