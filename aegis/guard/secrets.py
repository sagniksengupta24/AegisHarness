"""SecretGuard for secret detection, environment sanitization, and exfiltration prevention."""

import os
import re
from typing import Any, Optional

from aegis.errors import SecretLeakError
from aegis.logging import SECRET_PATTERNS, scrub_secrets
from aegis.models import PolicyDecision, PolicyResult

# Environment variable keys that should always be stripped from execution environments
SENSITIVE_ENV_KEYS = {
    "GEMINI_API_KEY",
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "OPENROUTER_API_KEY",
    "AWS_SECRET_ACCESS_KEY",
    "AWS_SESSION_TOKEN",
    "GITHUB_TOKEN",
    "GH_TOKEN",
    "GITLAB_TOKEN",
    "SLACK_BOT_TOKEN",
    "DATABASE_URL",
    "DB_PASSWORD",
    "SECRET_KEY",
    "PRIVATE_KEY",
    "SSH_PRIVATE_KEY",
}


class SecretGuard:
    """Detects secrets and provides a sanitized environment for subprocess execution."""

    def __init__(self, additional_sensitive_vars: Optional[set[str]] = None):
        self.sensitive_vars = set(SENSITIVE_ENV_KEYS)
        if additional_sensitive_vars:
            self.sensitive_vars.update(additional_sensitive_vars)

    def register_secret(self, secret_str: str) -> None:
        """Registers a custom secret string to be scrubbed across all operations."""
        from aegis.logging import register_custom_secret
        register_custom_secret(secret_str)

    def scan_content(self, text: str, context: str = "content") -> PolicyResult:
        """Inspects text for obvious high-entropy credentials or private keys."""
        if not text:
            return PolicyResult(decision=PolicyDecision.ALLOW, reason="Empty text", rule_name="secret_scan")

        for pattern in SECRET_PATTERNS:
            match = pattern.search(text)
            if match:
                sample = match.group(0)[:15] + "..."
                return PolicyResult(
                    decision=PolicyDecision.DENY,
                    reason=f"Secret token or private key detected in {context} ({sample})",
                    rule_name="secret_detection",
                    metadata={"matched_pattern": pattern.pattern},
                )

        return PolicyResult(
            decision=PolicyDecision.ALLOW,
            reason="No secret credential pattern detected",
            rule_name="secret_scan",
        )

    def sanitize_content(self, text: str) -> str:
        """Redacts secret patterns from text."""
        return scrub_secrets(text)

    def get_safe_env(self, base_env: Optional[dict[str, str]] = None, extra_env: Optional[dict[str, str]] = None) -> dict[str, str]:
        """Constructs a sanitized execution environment for commands.
        
        Explicitly excludes API keys and sensitive credentials.
        """
        source = dict(base_env or os.environ)
        safe_env: dict[str, str] = {}

        # Safe essential keys to carry over
        pass_through_prefixes = ("LC_", "LANG", "TERM", "PATH", "HOME", "USER", "TMPDIR", "VIRTUAL_ENV", "PYTHON")
        safe_exact_keys = {"PATH", "HOME", "USER", "SHELL", "TMPDIR", "TERM", "LANG", "TZ"}

        for k, v in source.items():
            k_upper = k.upper()
            # If explicitly sensitive
            if k_upper in self.sensitive_vars:
                continue
            # If contains sensitive substrings
            if any(s in k_upper for s in ("SECRET", "TOKEN", "API_KEY", "PASSWORD", "AUTH_KEY", "CREDENTIAL")):
                continue
            
            # Keep if safe standard key or matches safe prefix
            if k in safe_exact_keys or any(k.startswith(p) for p in pass_through_prefixes):
                safe_env[k] = v

        # Set safe default flags
        safe_env["CI"] = "1"
        safe_env["PYTHONUNBUFFERED"] = "1"
        safe_env["PYTHONDONTWRITEBYTECODE"] = "1"

        if extra_env:
            for ek, ev in extra_env.items():
                if ek.upper() not in self.sensitive_vars:
                    safe_env[ek] = ev

        return safe_env
