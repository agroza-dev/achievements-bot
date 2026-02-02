class TransferError(Exception):
    """Базовая ошибка трансфера"""

class RecipientNotFoundError(TransferError):
    pass
