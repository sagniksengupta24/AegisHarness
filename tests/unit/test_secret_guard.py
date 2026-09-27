"""Unit tests for SecretGuard and environment sanitization."""

import os
from aegis.guard.secrets import SecretGuard
from aegis.models import PolicyDecision


def test_secret_scan_detects_api_key():
    guard = SecretGuard()
    sample = "My key is sk-12345678901234567890abcdef"
    res = guard.scan_content(sample)
    assert res.decision == PolicyDecision.DENY
    assert "Secret token" in res.reason


def test_secret_scan_detects_private_key():
    guard = SecretGuard()
    sample = "-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEA0...\n-----END RSA PRIVATE KEY-----"
    res = guard.scan_content(sample)
    assert res.decision == PolicyDecision.DENY


def test_secret_scan_allows_normal_code():
    guard = SecretGuard()
    sample = "def compute(x, y):\n    return x + y\n"
    res = guard.scan_content(sample)
    assert res.decision == PolicyDecision.ALLOW


def test_sanitize_content_redacts_tokens():
    guard = SecretGuard()
    text = "Authorization: Bearer sk-123456789012345678901234"
    sanitized = guard.sanitize_content(text)
    assert "sk-123456789012345678901234" not in sanitized
    assert "[REDACTED_SECRET]" in sanitized


def test_safe_env_strips_sensitive_variables():
    guard = SecretGuard()
    mock_env = {
        "PATH": "/usr/bin:/bin",
        "HOME": "/home/user",
        "GEMINI_API_KEY": "secret-gemini-key",
        "OPENROUTER_API_KEY": "sk-or-v1-secret",
        "AWS_SECRET_ACCESS_KEY": "aws-secret",
        "CUSTOM_APP_TOKEN": "my-token",
        "LANG": "en_US.UTF-8",
    }
    safe = guard.get_safe_env(base_env=mock_env)
    assert "PATH" in safe
    assert "HOME" in safe
    assert "LANG" in safe
    assert "GEMINI_API_KEY" not in safe
    assert "OPENROUTER_API_KEY" not in safe
    assert "AWS_SECRET_ACCESS_KEY" not in safe
    assert "CUSTOM_APP_TOKEN" not in safe
    assert safe["CI"] == "1"
