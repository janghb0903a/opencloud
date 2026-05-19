from __future__ import annotations

import re
from typing import Any

REDACTED = "[REDACTED]"

SENSITIVE_KEYS = re.compile(
    r"(password|passwd|token|secret|application_credential_secret|auth|authorization|x-auth-token|"
    r"access_key|secret_key|private_key|client_secret)",
    re.IGNORECASE,
)

SENSITIVE_PATTERNS = [
    re.compile(r"(?i)(authorization:\s*bearer\s+)[A-Za-z0-9._~:/+=-]+"),
    re.compile(r"(?i)(x-auth-token:\s*)[A-Za-z0-9._~:/+=-]+"),
    re.compile(r"(?i)((?:password|token|secret|client_secret)\s*[=:]\s*)[^\s,;]+"),
]


def redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: (REDACTED if SENSITIVE_KEYS.search(str(key)) else redact(item)) for key, item in value.items()}
    if isinstance(value, list):
        return [redact(item) for item in value]
    if isinstance(value, tuple):
        return tuple(redact(item) for item in value)
    if isinstance(value, str):
        text = value
        for pattern in SENSITIVE_PATTERNS:
            text = pattern.sub(lambda m: m.group(1) + REDACTED, text)
        return text
    return value

