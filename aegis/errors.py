"""Aegis domain-specific error hierarchy."""

from typing import Any, Optional


class AegisError(Exception):
    """Base error class for all Aegis exceptions."""
    def __init__(self, message: str, details: Optional[dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "details": self.details,
        }


class ConfigurationError(AegisError):
    """Raised when configuration is missing, invalid, or unparseable."""
    pass


class PolicyViolationError(AegisError):
    """Base class for security and guardrail denials."""
    pass


class PathGuardError(PolicyViolationError):
    """Raised when a filesystem path is forbidden, outside workspace, or protected."""
    pass


class SecretLeakError(PolicyViolationError):
    """Raised when a secret or token is detected in outputs or inputs."""
    pass


class CommandBlockedError(PolicyViolationError):
    """Raised when a requested command violates execution policy."""
    pass


class ToolDeniedError(PolicyViolationError):
    """Raised when a tool execution is denied by GateGuard."""
    pass


class ASTScanError(PolicyViolationError):
    """Raised when static AST risk analysis rejects dangerous code constructs."""
    pass


class VerificationFailed(AegisError):
    """Raised when required verification gates fail."""
    def __init__(self, message: str, report: Any = None):
        super().__init__(message, {"report": getattr(report, "model_dump", lambda: str(report))() if report else None})
        self.report = report


class ModelError(AegisError):
    """Raised when the model client encounters API or response errors."""
    pass


class ExecutionTimeout(AegisError):
    """Raised when a local or sandbox command times out."""
    pass


class DaemonError(AegisError):
    """Raised when IPC daemon fails to start, connect, or process requests."""
    pass


class RollbackError(AegisError):
    """Raised when transactional session rollback fails."""
    pass


class LoopBudgetExceeded(AegisError):
    """Raised when agent loop reaches max turns, repairs, or repeated failures."""
    pass
