"""Structured logging configuration for operational entrypoints."""

import json
import logging
import time
from collections.abc import Mapping
from typing import Any

_RESERVED_LOG_RECORD_FIELDS = frozenset(logging.makeLogRecord({}).__dict__) | {
    "asctime",
    "message",
}


class KeyValueFormatter(logging.Formatter):
    """Render log records as flat key-value pairs."""

    converter = time.gmtime
    default_msec_format = "%s.%03dZ"

    def format(self, record: logging.LogRecord) -> str:
        parts = [
            f"ts={self.formatTime(record)}",
            f"level={record.levelname.lower()}",
            f"logger={record.name}",
            f"message={json.dumps(record.getMessage(), ensure_ascii=True)}",
        ]
        for key, value in _iter_extra_fields(record.__dict__).items():
            parts.append(f"{key}={json.dumps(value, default=str, ensure_ascii=True)}")
        if record.exc_info:
            parts.append(
                f"exception={json.dumps(self.formatException(record.exc_info), ensure_ascii=True)}"
            )
        return " ".join(parts)


def configure_logging(*, debug: bool) -> None:
    """Configure process logging for CLI execution."""

    handler = logging.StreamHandler()
    handler.setFormatter(KeyValueFormatter())

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.DEBUG if debug else logging.INFO)


def _iter_extra_fields(record_data: Mapping[str, Any]) -> dict[str, Any]:
    """Return sorted structured extras from a log record."""

    return {
        key: record_data[key]
        for key in sorted(record_data)
        if key not in _RESERVED_LOG_RECORD_FIELDS and not key.startswith("_")
    }
