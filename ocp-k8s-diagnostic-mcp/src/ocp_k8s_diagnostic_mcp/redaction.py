from __future__ import annotations

import re
from typing import Any

SENSITIVE_KEYS = re.compile(
    r"(token|password|passwd|secret|authorization|client-key|client-certificate|certificate-authority-data|"
    r"access_key|secret_key|bearer|api[_-]?key)",
    re.IGNORECASE,
)
SENSITIVE_VALUE_PATTERNS = [
    re.compile(r"(?i)(authorization:\s*bearer\s+)[A-Za-z0-9._~+/=-]+"),
    re.compile(r"(?i)((?:token|password|secret|api[_-]?key)\s*[=:]\s*)[^\s,;]+"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.DOTALL),
]
REDACTED = "[REDACTED]"


def redact(value: Any) -> Any:
    if isinstance(value, dict):
        redacted: dict[Any, Any] = {}
        for key, item in value.items():
            if SENSITIVE_KEYS.search(str(key)):
                redacted[key] = REDACTED
            else:
                redacted[key] = redact(item)
        return redacted
    if isinstance(value, list):
        return [redact(item) for item in value]
    if isinstance(value, tuple):
        return tuple(redact(item) for item in value)
    if isinstance(value, str):
        text = value
        for pattern in SENSITIVE_VALUE_PATTERNS:
            text = pattern.sub(lambda m: m.group(1) + REDACTED if m.groups() else REDACTED, text)
        return text
    return value

