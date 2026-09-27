"""Typed domain models and schemas for Aegis."""

from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field


class AgentState(str, Enum):
    """Explicit state machine states."""
    IDLE = "IDLE"
    PLAN = "PLAN"
    IMPLEMENT = "IMPLEMENT"
    VERIFY = "VERIFY"
    DIAGNOSE = "DIAGNOSE"
    COMMIT = "COMMIT"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"
    ABORTED = "ABORTED"
    BLOCKED = "BLOCKED"


class AgentStatus(str, Enum):
    """Terminal statuses for fail-closed completion."""
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    ABORTED = "ABORTED"
    BLOCKED = "BLOCKED"


class PolicyDecision(str, Enum):
    """GateGuard policy evaluation outcomes."""
    ALLOW = "ALLOW"
    DENY = "DENY"
    REVIEW = "REVIEW"


class PolicyResult(BaseModel):
    """Result of policy evaluation by a guard."""
    decision: PolicyDecision
    reason: str
    rule_name: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class Plan(BaseModel):
    """Structured plan produced by the model before implementation."""
    goal: str
    steps: list[str] = Field(default_factory=list)
    touched_files: list[str] = Field(default_factory=list)
    verification_strategy: str = ""
    notes: Optional[str] = None


class ToolCallRequest(BaseModel):
    """Structured tool call invocation."""
    id: str
    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class ToolResult(BaseModel):
    """Structured result returned by tool execution."""
    tool_name: str
    call_id: str
    success: bool
    output: str
    error: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class VerificationGateResult(BaseModel):
    """Result of a single verification gate."""
    gate_name: str
    status: str  # "PASS" | "FAIL"
    command: str
    exit_code: int
    stdout: str
    stderr: str
    duration_ms: int
    error: Optional[str] = None


class VerificationReport(BaseModel):
    """Comprehensive verification result across all gates."""
    status: str  # "PASS" | "FAIL"
    gates: list[VerificationGateResult] = Field(default_factory=list)
    summary: str = ""
    actionable_instruction: Optional[str] = None


class FailureDiagnosis(BaseModel):
    """Machine-readable diagnosis of a verification or tool failure."""
    root_cause: str
    failed_command: str
    error_snippet: str
    suggested_fix: str
    files_to_modify: list[str] = Field(default_factory=list)


class MemoryLesson(BaseModel):
    """Episodic memory entry persisted in .aegis/memory.json."""
    id: str
    lesson: str
    context: list[str] = Field(default_factory=list)
    source: str = "session"
    created_at: str
    confidence: float = 1.0
    files: list[str] = Field(default_factory=list)


class TaskResult(BaseModel):
    """Overall result of an agent task run."""
    status: AgentStatus
    session_id: str
    task: str
    turns: int
    changed_files: list[str] = Field(default_factory=list)
    verification: Optional[VerificationReport] = None
    lessons_learned: list[MemoryLesson] = Field(default_factory=list)
    error: Optional[str] = None
    duration_seconds: float = 0.0


class AuditRecord(BaseModel):
    """Structured audit trail item for telemetry."""
    timestamp: str
    session_id: str
    event_type: str
    details: dict[str, Any] = Field(default_factory=dict)
