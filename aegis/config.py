"""Configuration loader and Pydantic validation for Aegis."""

from pathlib import Path
from typing import Any, List, Optional
import os
import yaml
from pydantic import BaseModel, Field, ValidationError

from aegis.errors import ConfigurationError


class ProjectConfig(BaseModel):
    name: str = "workspace"
    stack: str = "generic"


class ModelConfig(BaseModel):
    provider: str = "gemini"
    model: Optional[str] = None
    temperature: float = 0.2
    api_key_env: str = "GEMINI_API_KEY"

    @property
    def resolved_model(self) -> str:
        if self.model:
            return self.model
        env_model = os.environ.get("GEMINI_MODEL")
        if env_model:
            return env_model
        return "gemini-3.8-flash"


class AgentBudgetConfig(BaseModel):
    max_turns: int = 24
    max_repairs: int = 5
    max_tool_calls: int = 100
    max_execution_time_seconds: int = 300
    max_command_runtime_seconds: int = 60
    max_output_size_bytes: int = 100_000
    max_files_touched: int = 20


class VerificationConfig(BaseModel):
    pre_flight: Optional[str] = None
    lint: Optional[str] = None
    test_cmd: Optional[str] = "pytest tests/ -q"
    build_cmd: Optional[str] = None
    timeout_seconds: int = 60
    required_gates: list[str] = Field(default_factory=lambda: ["test_cmd"])


class GuardrailsConfig(BaseModel):
    deny_paths: list[str] = Field(default_factory=lambda: [
        ".git/**",
        ".env",
        ".env.*",
        "secrets/**",
        "*.pem",
        "*.key",
        "id_rsa*",
        "credentials*",
        ".ssh/**",
    ])
    fail_closed: bool = True
    interactive_by_default: bool = False
    blocked_commands: list[str] = Field(default_factory=lambda: [
        "rm -rf /",
        "rm -rf /*",
        "sudo",
        "su",
        "shutdown",
        "reboot",
        "mkfs",
        "dd if=/dev",
        ":(){ :|:& };:",
    ])
    allow_network: bool = False


class ExecutionConfig(BaseModel):
    backend: str = "auto"  # auto, local, docker
    network: str = "none"
    timeout_seconds: int = 60


class MemoryConfig(BaseModel):
    enabled: bool = True
    path: str = ".aegis/memory.json"
    top_k: int = 5


class TelemetryConfig(BaseModel):
    enabled: bool = True
    path: str = ".aegis/traces"


class AegisConfig(BaseModel):
    version: int = 1
    project: ProjectConfig = Field(default_factory=ProjectConfig)
    model: ModelConfig = Field(default_factory=ModelConfig)
    agent: AgentBudgetConfig = Field(default_factory=AgentBudgetConfig)
    verification: VerificationConfig = Field(default_factory=VerificationConfig)
    guardrails: GuardrailsConfig = Field(default_factory=GuardrailsConfig)
    execution: ExecutionConfig = Field(default_factory=ExecutionConfig)
    memory: MemoryConfig = Field(default_factory=MemoryConfig)
    telemetry: TelemetryConfig = Field(default_factory=TelemetryConfig)


def find_repo_root(start_dir: Optional[Path] = None) -> Path:
    """Finds repository root by searching upward for .aegis.yaml, .git, or stopping at filesystem root."""
    current = (start_dir or Path.cwd()).resolve()
    for parent in [current, *current.parents]:
        if (parent / ".aegis.yaml").is_file() or (parent / ".git").exists():
            return parent
    return current


def load_config(repo_root: Optional[Path] = None, config_path: Optional[Path] = None) -> AegisConfig:
    """Loads and validates Aegis configuration from .aegis.yaml or returns default config."""
    root = repo_root or find_repo_root()
    target_file = config_path or (root / ".aegis.yaml")

    if not target_file.is_file():
        # Fall back to default config
        return AegisConfig()

    try:
        with open(target_file, "r", encoding="utf-8") as f:
            raw_data = yaml.safe_load(f) or {}
    except Exception as e:
        raise ConfigurationError(f"Failed to parse configuration file '{target_file}': {e}") from e

    try:
        return AegisConfig.model_validate(raw_data)
    except ValidationError as e:
        raise ConfigurationError(f"Configuration validation failed for '{target_file}': {e}") from e
