"""Adversarial tests for command chaining, command substitutions, and execution boundaries."""

import pytest
from aegis.guard.commands import CommandGuard
from aegis.models import PolicyDecision


def test_command_chaining_with_semicolon_blocks_second_command():
    guard = CommandGuard()
    res = guard.evaluate_command("echo hello; sudo rm -rf /")
    assert res.decision == PolicyDecision.DENY
    assert "sudo" in res.reason.lower() or "blocked" in res.reason.lower()


def test_command_chaining_with_and_operator_blocks_subcommand():
    guard = CommandGuard()
    res = guard.evaluate_command("pytest tests/ -q && sudo cat /etc/shadow")
    assert res.decision == PolicyDecision.DENY
    assert "sudo" in res.reason.lower()


def test_command_chaining_with_or_operator_blocks_subcommand():
    guard = CommandGuard()
    res = guard.evaluate_command("pytest -q || su - root")
    assert res.decision == PolicyDecision.DENY
    assert "su" in res.reason.lower()


def test_pipe_chaining_blocks_subcommand():
    guard = CommandGuard()
    res = guard.evaluate_command("cat file.txt | sudo tee /etc/crontab")
    assert res.decision == PolicyDecision.DENY
    assert "sudo" in res.reason.lower()


def test_command_substitution_dollar_parentheses_blocked():
    guard = CommandGuard()
    res = guard.evaluate_command("echo $(sudo whoami)")
    assert res.decision == PolicyDecision.DENY
    assert "substitution" in res.reason.lower() or "sudo" in res.reason.lower()


def test_command_substitution_backticks_blocked():
    guard = CommandGuard()
    res = guard.evaluate_command("echo `su - root`")
    assert res.decision == PolicyDecision.DENY
    assert "substitution" in res.reason.lower() or "su" in res.reason.lower()


def test_absolute_binary_path_blocked():
    guard = CommandGuard()
    assert guard.evaluate_command("/usr/bin/sudo whoami").decision == PolicyDecision.DENY
    assert guard.evaluate_command("/bin/su root").decision == PolicyDecision.DENY
    assert guard.evaluate_command("/usr/local/bin/vim test.py").decision == PolicyDecision.DENY


def test_network_tools_blocked_when_network_disabled():
    guard = CommandGuard(allow_network=False)
    for tool in ("curl", "wget", "ssh", "scp", "rsync", "nc", "netcat", "socat"):
        res = guard.evaluate_command(f"{tool} example.com")
        assert res.decision == PolicyDecision.DENY, f"Expected {tool} to be denied when network is disabled"
        assert "network" in res.reason.lower() or "forbidden" in res.reason.lower()


def test_system_file_redirection_blocked():
    guard = CommandGuard()
    res = guard.evaluate_command("echo 'evil' > /etc/passwd")
    assert res.decision == PolicyDecision.DENY
    assert "redirect" in res.reason.lower() or "forbidden" in res.reason.lower()


def test_fork_bomb_blocked():
    guard = CommandGuard()
    res = guard.evaluate_command(":(){ :|:& };:")
    assert res.decision == PolicyDecision.DENY
    assert "blocked pattern" in res.reason.lower()


def test_interactive_editors_blocked():
    guard = CommandGuard()
    for ed in ("vim", "vi", "nano", "emacs", "pico"):
        res = guard.evaluate_command(f"{ed} test.txt")
        assert res.decision == PolicyDecision.DENY


def test_malformed_shell_quotes_rejected():
    guard = CommandGuard()
    res = guard.evaluate_command("echo 'unclosed quote")
    assert res.decision == PolicyDecision.DENY
    assert "syntax" in res.reason.lower() or "parsing" in res.reason.lower()
