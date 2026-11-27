import json
import logging
import sys

from services.logging_config import JsonFormatter, RedactionFilter, configure_logging, request_id_var, sync_id_var


def test_redaction_filter_hides_authorization_tokens_and_emails():
    record = logging.LogRecord(
        "test", logging.INFO, __file__, 1,
        "Authorization: token ghp_12345678901234567890\ntoken=abc123 user=dev@example.com",
        (), None,
    )
    assert RedactionFilter().filter(record)
    message = record.getMessage()
    assert "ghp_12345678901234567890" not in message
    assert "abc123" not in message
    assert "dev@example.com" not in message
    assert "[EMAIL REDIGIDO]" in message


def test_json_formatter_adds_context_and_duration_without_secrets():
    sync_token = sync_id_var.set("sync-123")
    request_token = request_id_var.set("request-456")
    try:
        record = logging.LogRecord("sync", logging.INFO, __file__, 1, "iniciando para dev@example.com", (), None)
        record.duration_ms = 12.5
        payload = json.loads(JsonFormatter().format(record))
    finally:
        sync_id_var.reset(sync_token)
        request_id_var.reset(request_token)
    assert payload["sync_id"] == "sync-123"
    assert payload["request_id"] == "request-456"
    assert payload["duration_ms"] == 12.5
    assert "dev@example.com" not in payload["message"]


def test_redaction_filter_redacts_exception_tracebacks():
    try:
        raise RuntimeError("Authorization: Bearer secret-token-value user=dev@example.com")
    except RuntimeError:
        record = logging.LogRecord("test", logging.ERROR, __file__, 1, "falha", (), sys.exc_info())
    assert RedactionFilter().filter(record)
    assert "secret-token-value" not in (record.exc_text or "")
    assert "dev@example.com" not in (record.exc_text or "")
    assert record.exc_info is None


def test_default_logging_preserves_existing_handler_and_formatter():
    root = logging.getLogger()
    old_handlers = root.handlers[:]
    old_level = root.level
    handler = logging.StreamHandler()
    formatter = logging.Formatter("formato-local: %(message)s")
    handler.setFormatter(formatter)
    try:
        root.handlers.clear()
        root.addHandler(handler)
        configure_logging(log_format="text")
        assert root.handlers == [handler]
        assert handler.formatter is formatter
        assert any(isinstance(item, RedactionFilter) for item in handler.filters)
    finally:
        root.handlers.clear()
        for old_handler in old_handlers:
            root.addHandler(old_handler)
        root.setLevel(old_level)
