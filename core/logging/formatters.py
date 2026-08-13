"""
FMMS Structured JSON Log Formatter.

All log records emitted by FMMS are formatted as JSON with a consistent
set of fields, enabling log aggregation, searching, and alerting.
"""

import json
import logging
import traceback
from datetime import UTC, datetime
from typing import Any

from core.logging.redaction import redact


class FMMSJSONFormatter(logging.Formatter):
    """
    Formats log records as structured JSON.

    Every record includes the mandatory FMMS log fields:
    timestamp, level, service, domain, module, request_id,
    user_id, message, exception.
    """

    SERVICE_NAME = "fmms"

    def format(self, record: logging.LogRecord) -> str:
        """
        Format a log record as a JSON string.

        Args:
            record: The log record to format.

        Returns:
            A JSON-encoded string representing the log record.
        """
        log_entry: dict[str, Any] = {
            "timestamp": datetime.now(tz=UTC).isoformat(),
            "level": record.levelname,
            "service": self.SERVICE_NAME,
            "domain": getattr(record, "domain", "core"),
            "module": record.module,
            "logger": record.name,
            "request_id": getattr(record, "request_id", None),
            "user_id": getattr(record, "user_id", None),
            "message": record.getMessage(),
            "exception": None,
        }

        if record.exc_info:
            log_entry["exception"] = traceback.format_exception(*record.exc_info)

        if record.stack_info:
            log_entry["stack_info"] = self.formatStack(record.stack_info)

        # Include any extra fields passed via logger.info(..., extra={...})
        for key, value in record.__dict__.items():
            if key not in {
                "args",
                "asctime",
                "created",
                "exc_info",
                "exc_text",
                "filename",
                "funcName",
                "id",
                "levelname",
                "levelno",
                "lineno",
                "module",
                "msecs",
                "message",
                "msg",
                "name",
                "pathname",
                "process",
                "processName",
                "relativeCreated",
                "stack_info",
                "thread",
                "threadName",
                "domain",
                "request_id",
                "user_id",
            }:
                if not key.startswith("_"):
                    log_entry[key] = value

        return json.dumps(redact(log_entry), default=str, ensure_ascii=False)
