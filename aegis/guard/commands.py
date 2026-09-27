"""CommandGuard for safe command tokenization, argument inspection, and policy enforcement."""

import re
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
    "curl",
    "wget",
    "ssh",
    "scp",
    "rsync",
    "ftp",
}

DEFAULT_BLOCKED_PATTERNS = [
    ":(){ :|:& };:",
    "rm -rf /",
    "rm -rf /*",
    "dd if=/dev",
    "mkfs",
]

CHAINING_OPERATORS = {";", "&&", "||", "|", "|&", "&"}


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

    def _split_into_subcommands(self, tokens: list[str]) -> list[list[str]]:
        """Splits token stream on chaining and pipe operators (;, &&, ||, |, &)."""
        subcommands: list[list[str]] = []
        current: list[str] = []

        for token in tokens:
            if token in CHAINING_OPERATORS:
                if current:
                    subcommands.append(current)
                    current = []
            else:
                current.append(token)
        if current:
            subcommands.append(current)

        return subcommands

    def evaluate_command(self, cmd_input: Union[str, list[str]]) -> PolicyResult:
        """Evaluates command string or tokens against security policy."""
        cmd_raw = cmd_input if isinstance(cmd_input, str) else " ".join(cmd_input)

        # 1. Raw string checks against custom blocked patterns (fork bombs, etc.)
        for blocked_pat in self.custom_blocked:
            clean_pat = blocked_pat.strip()
            if clean_pat and clean_pat in cmd_raw:
                return PolicyResult(
                    decision=PolicyDecision.DENY,
                    reason=f"Command matches blocked pattern '{clean_pat}'",
                    rule_name="custom_blocked_command",
                )

        # 2. Check for dangerous command substitutions in raw string
        if "$(" in cmd_raw or "`" in cmd_raw:
            # Check if substitution contains blocked binaries
            sub_matches = re.findall(r"\$\(([^)]+)\)|`([^`]+)`", cmd_raw)
            for m1, m2 in sub_matches:
                inner_cmd = m1 or m2
                inner_eval = self.evaluate_command(inner_cmd)
                if inner_eval.decision != PolicyDecision.ALLOW:
                    return PolicyResult(
                        decision=PolicyDecision.DENY,
                        reason=f"Command substitution blocked: {inner_eval.reason}",
                        rule_name="nested_command_substitution",
                    )

        # 3. Tokenize command
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

        # 4. Split into subcommands across operators (; && || | &)
        subcommands = self._split_into_subcommands(tokens)

        for sub_tokens in subcommands:
            if not sub_tokens:
                continue

            # Strip path prefix: /usr/bin/sudo -> sudo
            executable = sub_tokens[0].lower().split("/")[-1]

            # Check blocked binaries
            if executable in BLOCKED_EXECUTABLES:
                return PolicyResult(
                    decision=PolicyDecision.DENY,
                    reason=f"Executable '{executable}' is blocked by security policy (privilege escalation or interactive editor)",
                    rule_name="blocked_executable",
                    metadata={"executable": executable, "subcommand": sub_tokens},
                )

            # Check network tools if network not allowed
            if not self.allow_network and executable in BLOCKED_NETWORK_TOOLS:
                return PolicyResult(
                    decision=PolicyDecision.DENY,
                    reason=f"Network tool '{executable}' is forbidden when network is disabled",
                    rule_name="network_isolation",
                    metadata={"executable": executable},
                )

            # Check destructive recursive deletion
            if executable == "rm":
                args = [a.lower() for a in sub_tokens[1:]]
                has_recursive = any(
                    a in ("-r", "-rf", "-fr", "--recursive") or (a.startswith("-") and "r" in a)
                    for a in args
                )
                targets = [a for a in sub_tokens[1:] if not a.startswith("-")]
                if has_recursive:
                    dangerous_targets = {"/", "/*", "~", "~/", "*"}
                    for target in targets:
                        clean_target = target.rstrip("/")
                        if (
                            target in dangerous_targets
                            or clean_target in dangerous_targets
                            or target == "/"
                            or clean_target.startswith("/etc")
                            or clean_target.startswith("/var")
                            or clean_target.startswith("/usr")
                            or clean_target.startswith("/boot")
                            or clean_target.startswith("/sys")
                        ):
                            return PolicyResult(
                                decision=PolicyDecision.DENY,
                                reason=f"Destructive recursive deletion of system target '{target}' is forbidden",
                                rule_name="destructive_rm",
                            )

            # Check dangerous system-level redirects
            for idx, token in enumerate(sub_tokens):
                target_file = ""
                if token in (">", ">>", "1>", "2>", "&>"):
                    if idx + 1 < len(sub_tokens):
                        target_file = sub_tokens[idx + 1].strip()
                elif token.startswith(">") or token.startswith(">>"):
                    target_file = token.lstrip(">").strip()

                if target_file and (
                    target_file.startswith("/etc")
                    or target_file.startswith("/boot")
                    or target_file.startswith("/sys")
                    or target_file.startswith("/root")
                ):
                    return PolicyResult(
                        decision=PolicyDecision.DENY,
                        reason=f"System file redirection to '{target_file}' is forbidden",
                        rule_name="system_redirection",
                    )

        return PolicyResult(
            decision=PolicyDecision.ALLOW,
            reason="Command passed tokenization and policy checks across all subcommands",
            rule_name="allow_command",
            metadata={"tokens": tokens, "subcommands_count": len(subcommands)},
        )

    def validate_command(self, cmd_input: Union[str, list[str]]) -> list[str]:
        """Validates command and returns parsed tokens if ALLOW, else raises CommandBlockedError."""
        res = self.evaluate_command(cmd_input)
        if res.decision != PolicyDecision.ALLOW:
            raise CommandBlockedError(res.reason, details=res.metadata)
        return res.metadata.get("tokens", [])
