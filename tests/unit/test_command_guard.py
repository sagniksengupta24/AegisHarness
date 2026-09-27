"""Unit tests for CommandGuard tokenization and security policies."""

import pytest
from aegis.errors import CommandBlockedError
from aegis.guard.commands import CommandGuard
from aegis.models import PolicyDecision


def test_command_tokenization():
    guard = CommandGuard()
    tokens = guard.tokenize_command("pytest tests/ -v --capture=no")
    assert tokens == ["pytest", "tests/", "-v", "--capture=no"]


def test_blocked_executables():
    guard = CommandGuard()
    assert guard.evaluate_command("sudo rm file").decision == PolicyDecision.DENY
    assert guard.evaluate_command("su - root").decision == PolicyDecision.DENY
    assert guard.evaluate_command("vim file.txt").decision == PolicyDecision.DENY
    assert guard.evaluate_command("nano script.py").decision == PolicyDecision.DENY


def test_destructive_rm_blocked():
    guard = CommandGuard()
    assert guard.evaluate_command("rm -rf /").decision == PolicyDecision.DENY
    assert guard.evaluate_command("rm -rf /*").decision == PolicyDecision.DENY
    assert guard.evaluate_command("rm -r /").decision == PolicyDecision.DENY


def test_network_isolation_when_disabled():
    guard = CommandGuard(allow_network=False)
    assert guard.evaluate_command("nc -l 8080").decision == PolicyDecision.DENY
    assert guard.evaluate_command("netcat host 1234").decision == PolicyDecision.DENY


def test_allowed_commands():
    guard = CommandGuard()
    assert guard.evaluate_command("python3 -m unittest").decision == PolicyDecision.ALLOW
    assert guard.evaluate_command("pytest tests/ -q").decision == PolicyDecision.ALLOW
    assert guard.evaluate_command("git status").decision == PolicyDecision.ALLOW
    assert guard.evaluate_command("ls -la src").decision == PolicyDecision.ALLOW


def test_custom_blocked_patterns():
    guard = CommandGuard(blocked_commands=["mkfs", ":(){ :|:& };:"])
    assert guard.evaluate_command("mkfs.ext4 /dev/sda1").decision == PolicyDecision.DENY
    assert guard.evaluate_command(":(){ :|:& };:").decision == PolicyDecision.DENY
