import logging
from contextvars import ContextVar
from uuid import uuid4

_trace_id: ContextVar[str | None] = ContextVar("trace_id", default=None)


def new_trace_id() -> str:
    tid = uuid4().hex[:8]
    _trace_id.set(tid)
    return tid


def get_trace_id() -> str | None:
    return _trace_id.get()


class TraceLogger(logging.LoggerAdapter):
    def process(self, msg, kwargs):
        trace_id = get_trace_id()
        prefix = f"[trace={trace_id}] " if trace_id else ""
        return prefix + msg, kwargs


def get_logger(name: str) -> TraceLogger:
    return TraceLogger(logging.getLogger(name), {})
