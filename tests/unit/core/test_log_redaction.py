"""Secret redaction tests for structured logging."""

import json
import logging

from core.logging.formatters import FMMSJSONFormatter


def test_formatter_redacts_sensitive_extra_and_bearer_token() -> None:
    record = logging.LogRecord(
        name="fmms.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="request Authorization=Bearer abc.def.ghi password=hunter2",
        args=(),
        exc_info=None,
    )
    record.payload = {"SAP_PASSWORD": "secret", "safe": "value"}

    payload = json.loads(FMMSJSONFormatter().format(record))

    assert "hunter2" not in payload["message"]
    assert "abc.def.ghi" not in payload["message"]
    assert payload["payload"] == {"SAP_PASSWORD": "[REDACTED]", "safe": "value"}
