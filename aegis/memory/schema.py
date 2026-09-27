"""Memory schemas for working memory and episodic memory."""

from typing import Any, List, Optional
from pydantic import BaseModel, Field

from aegis.models import MemoryLesson, VerificationReport


class WorkingMemory(BaseModel):
    """Ephemeral, in-memory session working state."""
    session_id: str
    task: str
    current_plan: Optional[str] = None
    files_touched: list[str] = Field(default_factory=list)
    commands_run: list[str] = Field(default_factory=list)
    failures_encountered: list[str] = Field(default_factory=list)
    repair_attempts: int = 0
    active_skills: list[str] = Field(default_factory=list)
    last_verification: Optional[VerificationReport] = None
