"""Execution runner abstraction and structured execution result."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Optional
from pydantic import BaseModel, Field


class ExecutionResult(BaseModel):
    """Structured result of executing a command in an execution backend."""
    command: str
    exit_code: int
    stdout: str
    stderr: str
    duration_ms: int
    timed_out: bool = False
    error: Optional[str] = None
    backend: str = "local"


class BaseExecutor(ABC):
    """Abstract interface for Aegis command execution backends."""

    def __init__(self, repo_root: Path, timeout_seconds: int = 60, max_output_bytes: int = 100_000):
        self.repo_root = repo_root.resolve()
        self.timeout_seconds = timeout_seconds
        self.max_output_bytes = max_output_bytes

    @abstractmethod
    def execute(
        self,
        command: str | list[str],
        cwd: Optional[Path] = None,
        extra_env: Optional[dict[str, str]] = None,
        timeout: Optional[int] = None,
    ) -> ExecutionResult:
        """Executes a command and returns an ExecutionResult."""
        pass
