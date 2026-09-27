"""Aegis logging and secret-scrubbing facilities."""

import logging
import os
import re
import sys
from typing import Any, Optional, Set

# Secret patterns to scrub from all logs, traces, and tool outputs
SECRET_PATTERNS = [
    re.compile(r"(?i)(api[_-]?key|secret|password|token|bearer|authorization)\s*[:=]\s*['\"]?([a-zA-Z0-9_\-\.\/+=]{6,})['\"]?"),
    re.compile(r"(?i)\b(TEST_SECRET_[a-zA-Z0-9_\-]+)\b"),
    re.compile(r"(?i)\bBearer\s+([a-zA-Z0-9_\-\.]{12,})\b"),
    re.compile(r"sk-[a-zA-Z0-9_\-]{16,}"),
    re.compile(r"ghp_[a-zA-Z0-9]{20,}"),
    re.compile(r"gho_[a-zA-Z0-9]{20,}"),
    re.compile(r"AIza[0-9A-Za-z\-_]{25,}"),
    re.compile(r"xox[baprs]-[0-9a-zA-Z]{10,48}"),
    re.compile(r"-----BEGIN (?:RSA|OPENSSH|DSA|EC|PGP)? PRIVATE KEY-----[\s\S]*?-----END (?:RSA|OPENSSH|DSA|EC|PGP)? PRIVATE KEY-----"),
]

_CUSTOM_REGISTERED_SECRETS: set[str] = set()


def register_custom_secret(secret: str) -> None:
    """Registers a specific secret string to be scrubbed from all outputs."""
    clean = secret.strip()
    if len(clean) >= 4:
        _CUSTOM_REGISTERED_SECRETS.add(clean)


def scrub_secrets(text: str) -> str:
    """Redacts known token/credential patterns from string."""
    if not text:
        return text
    scrubbed = text

    # First scrub custom registered secrets verbatim
    for s in _CUSTOM_REGISTERED_SECRETS:
        if s in scrubbed:
            scrubbed = scrubbed.replace(s, "[REDACTED_SECRET]")

    for pattern in SECRET_PATTERNS:
        if "PRIVATE KEY" in pattern.pattern:
            scrubbed = pattern.sub("[REDACTED_PRIVATE_KEY]", scrubbed)
        elif "TEST_SECRET" in pattern.pattern:
            scrubbed = pattern.sub("[REDACTED_SECRET]", scrubbed)
        elif "Bearer" in pattern.pattern:
            scrubbed = pattern.sub("Bearer [REDACTED_SECRET]", scrubbed)
        else:
            def _repl(match: re.Match) -> str:
                if len(match.groups()) >= 2:
                    k = match.group(1)
                    return f"{k}=[REDACTED_SECRET]"
                return "[REDACTED_SECRET]"
            scrubbed = pattern.sub(_repl, scrubbed)

    return scrubbed


class SafeFormatter(logging.Formatter):
    """Logging formatter that sanitizes secret patterns before rendering."""
    def format(self, record: logging.LogRecord) -> str:
        orig = super().format(record)
        return scrub_secrets(orig)


_logger: Optional[logging.Logger] = None


def get_logger(name: str = "aegis") -> logging.Logger:
    """Returns the configured Aegis logger with safe formatting."""
    global _logger
    if _logger is not None:
        return _logger.getChild(name) if name != "aegis" else _logger

    level_name = os.environ.get("AEGIS_LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    logger = logging.getLogger("aegis")
    logger.setLevel(level)
    logger.propagate = False

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setLevel(level)
        formatter = SafeFormatter("[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s", datefmt="%H:%M:%S")
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    _logger = logger
    return logger if name == "aegis" else logger.getChild(name)
