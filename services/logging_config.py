"""Configuração de logs em texto (padrão) ou JSON, com correlação e redação de dados sensíveis."""
from __future__ import annotations

import json
import logging
import os
import re
import traceback
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any

sync_id_var: ContextVar[str | None] = ContextVar("sync_id", default=None)
request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)

_PATTERNS = (
    (re.compile(r"(?i)(authorization\s*[:=]\s*)[^\r\n]+"), r"\1[REDACTED]"),
    (re.compile(r"(?i)\b(bearer\s+)[A-Za-z0-9._~+/=-]+"), r"\1[REDACTED]"),
    (re.compile(r"(?i)\b(token|access_token|api[_-]?key|password|secret|github_token)\s*[:=]\s*([^\s,;]+)"), r"\1=[REDACTED]"),
    (re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{16,}|github_pat_[A-Za-z0-9_]{16,}|ATATT[A-Za-z0-9_=\-]{16,})\b"), "[REDACTED]"),
    (re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.IGNORECASE), "[EMAIL REDIGIDO]"),
)


def redact_text(value: str) -> str:
    result = value
    for pattern, replacement in _PATTERNS:
        result = pattern.sub(replacement, result)
    return result


class RedactionFilter(logging.Filter):
    """Redige a mensagem já formatada para não deixar argumentos sensíveis escaparem."""

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            message = record.getMessage()
        except Exception:
            message = "[mensagem de log inválida]"
        record.msg = redact_text(message)
        record.args = ()
        if record.exc_info:
            record.exc_text = redact_text("".join(traceback.format_exception(*record.exc_info)))
            record.exc_info = None
        if record.stack_info:
            record.stack_info = redact_text(record.stack_info)
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, timezone.utc).isoformat().replace("+00:00", "Z"),
            "level": record.levelname,
            "logger": record.name,
            "message": redact_text(record.getMessage()),
        }
        sync_id = getattr(record, "sync_id", None) or sync_id_var.get()
        request_id = getattr(record, "request_id", None) or request_id_var.get()
        duration = getattr(record, "duration_ms", None)
        if sync_id:
            payload["sync_id"] = redact_text(str(sync_id))
        if request_id:
            payload["request_id"] = redact_text(str(request_id))
        if duration is not None:
            payload["duration_ms"] = duration
        if record.exc_text:
            payload["exception"] = redact_text(record.exc_text)
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def configure_logging(level: int = logging.INFO, log_format: str | None = None) -> None:
    """Configura o root logger. `LOG_FORMAT=json` ativa JSON; o padrão mantém texto."""
    selected = (log_format or os.getenv("LOG_FORMAT", "text")).strip().lower()
    root = logging.getLogger()
    if selected == "json":
        handler = logging.StreamHandler()
        handler.addFilter(RedactionFilter())
        handler.setFormatter(JsonFormatter())
        root.handlers.clear()
        root.addHandler(handler)
    else:
        # Preserve handlers/formatters instalados pelo Streamlit ou pelo ambiente local.
        if not root.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
            root.addHandler(handler)
        for handler in root.handlers:
            if not any(isinstance(item, RedactionFilter) for item in handler.filters):
                handler.addFilter(RedactionFilter())
    root.setLevel(level)
