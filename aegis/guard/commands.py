"""CommandGuard for safe command tokenization, argument inspection, and policy enforcement."""

import shlex
from typing import List, Optional, Tuple, Union

from aegis.errors import CommandBlockedError
from aegis.models import PolicyDecision, PolicyResult

BLOCKED_EXECUTABLES = {
    "sudo",
    "su",
    "doas",
    "pkexec",
    "shutdown",
    "reboot",
    "poweroff",
    "init",
    "mkfs",
    "fdisk",
    "parted",
    "dd",
    # Interactive editors that hang terminal
    "vim",
    "vi",
    "nano",
    "emacs",
    "pico",
}

BLOCKED_NETWORK_TOOLS = {
    "nc",
    "netcat",
    "ncat",
    "socat",
    "telnet",
}


DEFAULT_BLOCKED_PATTERNS = [
    ":(){ :|:& };:",
    "rm -rf /",
    "rm -rf /*",
    "dd if=/dev",
    "mkfs",
]


class CommandGuard:
    """Enforces execution boundaries, tokenizes commands safely, and blocks dangerous utilities."""

    def __init__(
        self,
        blocked_commands: Optional[list[str]] = None,
        allow_network: bool = False,
    ):
        self.custom_blocked = list(blocked_commands) if blocked_commands is not None else list(DEFAULT_BLOCKED_PATTERNS)
        self.allow_network = allow_network

    def tokenize_command(self, cmd_input: Union[str, list[str]]) -> list[str]:
        """Safely parses string command into arguments using shlex."""
        if isinstance(cmd_input, list):
            return [str(arg) for arg in cmd_input]
        if not isinstance(cmd_input, str):
            raise CommandBlockedError(f"Command must be string or list of strings, got {type(cmd_input)}")
        
        trimmed = cmd_input.strip()
        if not trimmed:
            raise CommandBlockedError("Empty command string provided")

        try:
            tokens = shlex.split(trimmed)
        except ValueError as e:
            raise CommandBlockedError(f"Command parsing failed (invalid shell syntax): {e}") from e

        return tokens

    def evaluate_command(self, cmd_input: Union[str, list[str]]) -> PolicyResult:
        """Evaluates tokenized command against security policy."""
        # 1. Check raw command string against blocked patterns first (catches fork bombs & raw substrings)
        cmd_raw = cmd_input if isinstance(cmd_input, str) else " ".join(cmd_input)
        for blocked_pat in self.custom_blocked:
            clean_pat = blocked_pat.strip()
            if clean_pat and clean_pat in cmd_raw:
                return PolicyResult(
                    decision=PolicyDecision.DENY,
                    reason=f"Command matches blocked pattern '{clean_pat}'",
                    rule_name="custom_blocked_command",
                )

        try:
            tokens = self.tokenize_command(cmd_input)
        except CommandBlockedError as e:
            return PolicyResult(
                decision=PolicyDecision.DENY,
                reason=str(e),
                rule_name="command_tokenization",
            )

        if not tokens:
            return PolicyResult(
                decision=PolicyDecision.DENY,
                reason="No command tokens found",
                rule_name="empty_command",
            )

        cmd_str = " ".join(tokens)
        executable = tokens[0].lower().split("/")[-1]

        # Check explicitly blocked binaries
        if executable in BLOCKED_EXECUTABLES:
            return PolicyResult(
                decision=PolicyDecision.DENY,
                reason=f"Executable '{executable}' is blocked by security policy (privilege escalation or interactive editor)",
                rule_name="blocked_executable",
                metadata={"executable": executable},
            )

        # Check network tools if network not allowed
        if not self.allow_network and executable in BLOCKED_NETWORK_TOOLS:
            return PolicyResult(
                decision=PolicyDecision.DENY,
                reason=f"Network tool '{executable}' is forbidden when network is disabled",
                rule_name="network_isolation",
            )

        # Check destructive deletion patterns (e.g., rm -rf / or rm -rf ~)
        if executable == "rm":
            args = [a.lower() for a in tokens[1:]]
            has_recursive = any(a in ("-r", "-rf", "-fr", "--recursive") or (a.startswith("-") and "r" in a) for a in args)
            targets = [a for a in tokens[1:] if not a.startswith("-")]
            if has_recursive:
                dangerous_targets = {"/", "/*", "~", "~/", "*"}
                for target in targets:
                    if target in dangerous_targets or target.startswith("/etc") or target.startswith("/var"):
                        return PolicyResult(
                            decision=PolicyDecision.DENY,
                            reason=f"Destructive recursive deletion of system target '{target}' is forbidden",
                            rule_name="destructive_rm",
                        )

        # Check fork bombs and custom block patterns
        for blocked_pat in self.custom_blocked:
            clean_pat = blocked_pat.strip()
            if clean_pat and clean_pat in cmd_str:
                return PolicyResult(
                    decision=PolicyDecision.DENY,
                    reason=f"Command matches blocked pattern '{clean_pat}'",
                    rule_name="custom_blocked_command",
                )

        return PolicyResult(
            decision=PolicyDecision.ALLOW,
            reason="Command passed tokenization and policy checks",
            rule_name="allow_command",
            metadata={"executable": executable, "tokens": tokens},
        )

    def validate_command(self, cmd_input: Union[str, list[str]]) -> list[str]:
        """Validates command and returns parsed tokens if ALLOW, else raises CommandBlockedError."""
        res = self.evaluate_command(cmd_input)
        if res.decision != PolicyDecision.ALLOW:
            raise CommandBlockedError(res.reason, details=res.metadata)
        return res.metadata.get("tokens", [])
