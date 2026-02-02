from core.application.transfers.transfer_intent import TransferDirection


class TransferPolicy:
    def tax(self, amount: int, direction: TransferDirection) -> int:
        raise NotImplementedError

    def get_max_transfer_amount(self) -> int:
        raise NotImplementedError
