"""Verification gates definitions and execution runner."""

from pathlib import Path
from typing import Any, List, Optional

from aegis.config import VerificationConfig
from aegis.execution.runner import BaseExecutor, ExecutionResult
from aegis.models import VerificationGateResult, VerificationReport


class GateDefinition:
    """Specification of a verification gate."""

    def __init__(self, name: str, command: Optional[str], required: bool = True):
        self.name = name
        self.command = command
        self.required = required


class VerificationRunner:
    """Executes configured verification gates in order and compiles structured reports."""

    def __init__(self, repo_root: Path, executor: BaseExecutor, config: VerificationConfig):
        self.repo_root = repo_root.resolve()
        self.executor = executor
        self.config = config

    def build_gates(self) -> list[GateDefinition]:
        """Constructs list of verification gates based on configuration."""
        gates = []
        if self.config.pre_flight:
            gates.append(GateDefinition("pre_flight", self.config.pre_flight, required=True))
        if self.config.lint:
            gates.append(GateDefinition("lint", self.config.lint, required="lint" in self.config.required_gates))
        if self.config.test_cmd:
            gates.append(GateDefinition("test", self.config.test_cmd, required=True))
        if self.config.build_cmd:
            gates.append(GateDefinition("build", self.config.build_cmd, required="build" in self.config.required_gates))
        return gates

    def run_all(self, timeout_override: Optional[int] = None) -> VerificationReport:
        """Executes all active verification gates."""
        gates = self.build_gates()
        gate_results: list[VerificationGateResult] = []
        overall_status = "PASS"
        actionable_instruction = None
        summary_lines = []

        timeout = timeout_override or self.config.timeout_seconds

        for gate in gates:
            if not gate.command:
                continue

            exec_res: ExecutionResult = self.executor.execute(
                gate.command,
                cwd=self.repo_root,
                timeout=timeout,
            )

            is_pass = (exec_res.exit_code == 0 and not exec_res.timed_out)
            status_str = "PASS" if is_pass else "FAIL"

            error_snippet = None
            if not is_pass:
                error_snippet = (
                    exec_res.stderr.strip()
                    or exec_res.stdout.strip()
                    or exec_res.error
                    or f"Command '{gate.command}' exited with code {exec_res.exit_code}"
                )
                # Extract last 10 lines of error for diagnosis
                lines = error_snippet.splitlines()
                if len(lines) > 10:
                    error_snippet = "\n".join(lines[-10:])

            gate_res = VerificationGateResult(
                gate_name=gate.name,
                status=status_str,
                command=gate.command,
                exit_code=exec_res.exit_code,
                stdout=exec_res.stdout,
                stderr=exec_res.stderr,
                duration_ms=exec_res.duration_ms,
                error=error_snippet,
            )
            gate_results.append(gate_res)

            summary_lines.append(f"Gate '{gate.name}': {status_str} (exit {exec_res.exit_code}, {exec_res.duration_ms}ms)")

            if not is_pass and gate.required:
                overall_status = "FAIL"
                actionable_instruction = (
                    f"Gate '{gate.name}' failed with exit code {exec_res.exit_code}.\n"
                    f"Command: {gate.command}\n"
                    f"Error summary: {error_snippet}\n"
                    f"Instruction: Do not finalize. Inspect the failure, locate the cause, apply a surgical patch, and verify again."
                )
                break  # Fail fast on required gate failure

        return VerificationReport(
            status=overall_status,
            gates=gate_results,
            summary="; ".join(summary_lines),
            actionable_instruction=actionable_instruction,
        )
