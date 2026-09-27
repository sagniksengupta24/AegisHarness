"""Base abstractions and permission categories for Aegis tools."""

from abc import ABC, abstractmethod
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Optional, Type
from pydantic import BaseModel, Field

from aegis.execution.runner import BaseExecutor
from aegis.guard import GateGuard
from aegis.models import ToolResult
from aegis.session.checkpoint import SessionCheckpoint


class ToolPermission(str, Enum):
    """Categorization of tool capabilities for security and approval checks."""
    READ = "READ"
    WRITE = "WRITE"
    EXECUTE = "EXECUTE"
    ADMIN = "ADMIN"


class ToolContext:
    """Runtime context provided to tools during execution."""

    def __init__(
        self,
        repo_root: Path,
        gateguard: GateGuard,
        executor: BaseExecutor,
        checkpoint: SessionCheckpoint,
        verifier: Optional[Any] = None,
        memory_manager: Optional[Any] = None,
        interactive: bool = False,
        approval_callback: Optional[Callable[[str, str], bool]] = None,
    ):
        self.repo_root = repo_root.resolve()
        self.gateguard = gateguard
        self.executor = executor
        self.checkpoint = checkpoint
        self.verifier = verifier
        self.memory_manager = memory_manager
        self.interactive = interactive
        self.approval_callback = approval_callback


class BaseTool(ABC):
    """Abstract base class for all Aegis tools."""

    name: str
    description: str
    permission: ToolPermission
    timeout_seconds: int = 30
    args_schema: Type[BaseModel]

    @abstractmethod
    def execute(self, arguments: dict[str, Any], context: ToolContext, call_id: str) -> ToolResult:
        """Executes the tool with validated arguments and returns structured ToolResult."""
        pass

    def get_json_schema(self) -> dict[str, Any]:
        """Returns JSON Schema representation of the tool parameters."""
        return self.args_schema.model_json_schema()
