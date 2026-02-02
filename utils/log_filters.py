import logging


class ProjectOnlyFilter(logging.Filter):
    def __init__(self, allowed_prefixes: tuple[str, ...]):
        self.allowed_prefixes = allowed_prefixes

    def filter(self, record: logging.LogRecord) -> bool:
        return record.name.startswith(self.allowed_prefixes)
