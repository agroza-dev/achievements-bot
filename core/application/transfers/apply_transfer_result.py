from dataclasses import dataclass


@dataclass(frozen=True)
class ApplyTransferResult:
    """Результат применения трансфера."""
    amount: int
    tax: int
    initiator_balance_after: int
    recipient_balance_after: int
