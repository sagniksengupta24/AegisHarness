"""Local and Docker execution backends with process group isolation and resource bounds."""

import os
import signal
import subprocess
import time
from pathlib import Path
from typing import Any, Optional, Union

from aegis.errors import ConfigurationError, ExecutionTimeout
from aegis.execution.runner import BaseExecutor, ExecutionResult
from aegis.guard.secrets import SecretGuard


def is_docker_available() -> bool:
    """Checks whether the docker binary is present and daemon is responding."""
    try:
        res = subprocess.run(
            ["docker", "info"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=3,
        )
        return res.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
        return False


class LocalExecutor(BaseExecutor):
    """Executes commands on local host inside workspace with process group cleanup and sanitized env."""

    def __init__(
        self,
        repo_root: Path,
        timeout_seconds: int = 60,
        max_output_bytes: int = 100_000,
        secret_guard: Optional[SecretGuard] = None,
    ):
        super().__init__(repo_root, timeout_seconds, max_output_bytes)
        self.secret_guard = secret_guard or SecretGuard()

    def execute(
        self,
        command: Union[str, list[str]],
        cwd: Optional[Path] = None,
        extra_env: Optional[dict[str, str]] = None,
        timeout: Optional[int] = None,
    ) -> ExecutionResult:
        work_dir = (cwd or self.repo_root).resolve()
        timeout_val = timeout or self.timeout_seconds
        env = self.secret_guard.get_safe_env(extra_env=extra_env)

        cmd_str = command if isinstance(command, str) else " ".join(command)
        start_time = time.perf_counter()

        # We execute via a safe shell runner if command is a string with arguments
        use_shell = isinstance(command, str)

        proc = None
        timed_out = False
        stdout_bytes = b""
        stderr_bytes = b""

        try:
            # start_new_session=True creates a new process group for clean teardown
            proc = subprocess.Popen(
                command,
                shell=use_shell,
                cwd=str(work_dir),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True,
            )

            stdout_bytes, stderr_bytes = proc.communicate(timeout=timeout_val)
            exit_code = proc.returncode

        except subprocess.TimeoutExpired:
            timed_out = True
            exit_code = -1
            if proc is not None:
                try:
                    # Kill entire process group
                    pgid = os.getpgid(proc.pid)
                    os.killpg(pgid, signal.SIGKILL)
                except Exception:
                    try:
                        proc.kill()
                    except Exception:
                        pass
                try:
                    stdout_bytes, stderr_bytes = proc.communicate(timeout=2)
                except Exception:
                    pass

        except Exception as e:
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            return ExecutionResult(
                command=cmd_str,
                exit_code=-1,
                stdout="",
                stderr=str(e),
                duration_ms=duration_ms,
                timed_out=False,
                error=f"Execution error: {e}",
                backend="local",
            )

        duration_ms = int((time.perf_counter() - start_time) * 1000)

        # Output truncation
        if len(stdout_bytes) > self.max_output_bytes:
            stdout_bytes = stdout_bytes[: self.max_output_bytes] + b"\n... [TRUNCATED - Output exceeded limit]"
        if len(stderr_bytes) > self.max_output_bytes:
            stderr_bytes = stderr_bytes[: self.max_output_bytes] + b"\n... [TRUNCATED - Output exceeded limit]"

        stdout_decoded = stdout_bytes.decode("utf-8", errors="replace")
        stderr_decoded = stderr_bytes.decode("utf-8", errors="replace")

        # Scrub any accidental secrets
        stdout_clean = self.secret_guard.sanitize_content(stdout_decoded)
        stderr_clean = self.secret_guard.sanitize_content(stderr_decoded)

        return ExecutionResult(
            command=cmd_str,
            exit_code=exit_code,
            stdout=stdout_clean,
            stderr=stderr_clean,
            duration_ms=duration_ms,
            timed_out=timed_out,
            error="Command timed out" if timed_out else None,
            backend="local",
        )


class DockerExecutor(BaseExecutor):
    """Executes commands inside a Docker container with workspace mount and restricted network."""

    def __init__(
        self,
        repo_root: Path,
        image: str = "python:3.12-slim",
        network: str = "none",
        timeout_seconds: int = 60,
        max_output_bytes: int = 100_000,
        secret_guard: Optional[SecretGuard] = None,
    ):
        super().__init__(repo_root, timeout_seconds, max_output_bytes)
        self.image = image
        self.network = network
        self.secret_guard = secret_guard or SecretGuard()

    def execute(
        self,
        command: Union[str, list[str]],
        cwd: Optional[Path] = None,
        extra_env: Optional[dict[str, str]] = None,
        timeout: Optional[int] = None,
    ) -> ExecutionResult:
        if not is_docker_available():
            raise ConfigurationError("Docker execution was requested, but Docker daemon is not available.")

        timeout_val = timeout or self.timeout_seconds
        cmd_str = command if isinstance(command, str) else " ".join(command)
        start_time = time.perf_counter()

        # Build docker run invocation
        docker_cmd = [
            "docker", "run", "--rm",
            "-v", f"{self.repo_root}:/workspace:rw",
            "-w", "/workspace",
            "--network", self.network,
            "--memory", "1g",
        ]

        # Pass safe extra env vars
        if extra_env:
            for k, v in extra_env.items():
                if k not in self.secret_guard.sensitive_vars:
                    docker_cmd.extend(["-e", f"{k}={v}"])

        docker_cmd.extend([self.image, "sh", "-c", cmd_str])

        try:
            res = subprocess.run(
                docker_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout_val,
            )
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            return ExecutionResult(
                command=cmd_str,
                exit_code=res.returncode,
                stdout=self.secret_guard.sanitize_content(res.stdout.decode("utf-8", errors="replace")),
                stderr=self.secret_guard.sanitize_content(res.stderr.decode("utf-8", errors="replace")),
                duration_ms=duration_ms,
                timed_out=False,
                backend="docker",
            )
        except subprocess.TimeoutExpired:
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            return ExecutionResult(
                command=cmd_str,
                exit_code=-1,
                stdout="",
                stderr="Docker execution timed out",
                duration_ms=duration_ms,
                timed_out=True,
                error="Docker command timed out",
                backend="docker",
            )


def get_executor(
    repo_root: Path,
    backend: str = "auto",
    timeout_seconds: int = 60,
    max_output_bytes: int = 100_000,
    network: str = "none",
) -> BaseExecutor:
    """Factory creating LocalExecutor or DockerExecutor based on configuration and availability."""
    secret_guard = SecretGuard()
    if backend == "docker":
        if is_docker_available():
            return DockerExecutor(
                repo_root=repo_root,
                network=network,
                timeout_seconds=timeout_seconds,
                max_output_bytes=max_output_bytes,
                secret_guard=secret_guard,
            )
        raise ConfigurationError("Docker backend was explicitly configured but Docker daemon is not available.")
    
    if backend == "auto":
        # Docker is optional isolation if available, but local executor is always dependable
        return LocalExecutor(
            repo_root=repo_root,
            timeout_seconds=timeout_seconds,
            max_output_bytes=max_output_bytes,
            secret_guard=secret_guard,
        )

    return LocalExecutor(
        repo_root=repo_root,
        timeout_seconds=timeout_seconds,
        max_output_bytes=max_output_bytes,
        secret_guard=secret_guard,
    )
