"""IPC Protocol definitions for Aegis background daemon."""

from typing import Any, Optional
from pydantic import BaseModel, Field


class DaemonRequest(BaseModel):
    """Structured request sent from CLI to daemon."""
    request_id: str
    command: str  # ping, run_task, verify, status, stop
    payload: dict[str, Any] = Field(default_factory=dict)


class DaemonResponse(BaseModel):
    """Structured response sent from daemon back to CLI."""
    request_id: str
    status: str  # OK | ERROR
    result: dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None
