"""Aegis logging and secret-scrubbing facilities."""

import logging
import os
import re
import sys
from typing import Any, Optional

# Secret patterns to scrub from all logs and traces
SECRET_PATTERNS = [
    re.compile(r"(?i)(api[_-]?key|secret|password|token|bearer|authorization)\s*[:=]\s*['\"]?([a-zA-Z0-9_\-\.\/+=]{8,})['\"]?"),
    re.compile(r"sk-[a-zA-Z0-9_\-]{20,}"),
    re.compile(r"ghp_[a-zA-Z0-9]{36}"),
    re.compile(r"gho_[a-zA-Z0-9]{36}"),
    re.compile(r"AIza[0-9A-Za-z\-_]{35}"),
    re.compile(r"xox[baprs]-[0-9a-zA-Z]{10,48}"),
    re.compile(r"-----BEGIN (?:RSA|OPENSSH|DSA|EC|PGP)? PRIVATE KEY-----[\s\S]*?-----END (?:RSA|OPENSSH|DSA|EC|PGP)? PRIVATE KEY-----"),
]


def scrub_secrets(text: str) -> str:
    """Redacts known token/credential patterns from string."""
    if not text:
        return text
    scrubbed = text
    for pattern in SECRET_PATTERNS:
        # If private key block
        if "PRIVATE KEY" in pattern.pattern:
            scrubbed = pattern.sub("[REDACTED_PRIVATE_KEY]", scrubbed)
        else:
            def _repl(match: re.Match) -> str:
                if len(match.groups()) >= 2:
                    k, v = match.group(1), match.group(2)
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

    # Avoid duplicate handlers
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setLevel(level)
        formatter = SafeFormatter("[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s", datefmt="%H:%M:%S")
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    _logger = logger
    return logger if name == "aegis" else logger.getChild(name)
