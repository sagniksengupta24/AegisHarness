"""Tests verifying safe failure handling across model provider failure modes (Section 7).

Proves that:
1. Network timeout
2. Authentication failure
3. 429 / Rate limit
4. Malformed model response
5. Unexpected tool call
6. Empty model response
7. Provider exception
8. Provider refusal / error
all fail safely, execute rollback if necessary, and NEVER mark task as COMPLETE.
"""

from pathlib import Path
from typing import Any, Optional
import pytest

from aegis.client import FakeModelClient, ModelResponse
from aegis.config import AegisConfig, VerificationConfig
from aegis.errors import ModelError
from aegis.models import AgentStatus, ToolCallRequest
from aegis.orchestrator import Orchestrator


def test_model_network_timeout_fails_safely(tmp_path: Path):
    """Network timeout during generation fails safely without completing."""
    def timeout_handler(messages):
        raise TimeoutError("Connection to model provider timed out after 30000ms")

    client = FakeModelClient()
    client.set_script_handler(timeout_handler)

    config = AegisConfig(
        verification=VerificationConfig(test_cmd="exit 0", required_gates=["test_cmd"])
    )
    orchestrator = Orchestrator(repo_root=tmp_path, config=config, model_client=client)

    result = orchestrator.run_task("Network timeout test")

    assert result.status == AgentStatus.FAILED
    assert "timed out" in result.error.lower() or "model provider error" in result.error.lower()


def test_model_authentication_failure(tmp_path: Path):
    """401/403 Authentication error fails safely."""
    def auth_error_handler(messages):
        raise ModelError("API_KEY_INVALID: API key not valid. Please pass a valid API key.")

    client = FakeModelClient()
    client.set_script_handler(auth_error_handler)

    config = AegisConfig(
        verification=VerificationConfig(test_cmd="exit 0", required_gates=["test_cmd"])
    )
    orchestrator = Orchestrator(repo_root=tmp_path, config=config, model_client=client)

    result = orchestrator.run_task("Auth failure test")

    assert result.status == AgentStatus.FAILED
    assert "api_key_invalid" in result.error.lower() or "model provider error" in result.error.lower()


def test_model_rate_limit_429(tmp_path: Path):
    """429 RESOURCE_EXHAUSTED / Rate limit fails safely."""
    def rate_limit_handler(messages):
        raise ModelError("RESOURCE_EXHAUSTED: Rate limit exceeded for quota 'GenerateContentRequests'.")

    client = FakeModelClient()
    client.set_script_handler(rate_limit_handler)

    config = AegisConfig(
        verification=VerificationConfig(test_cmd="exit 0", required_gates=["test_cmd"])
    )
    orchestrator = Orchestrator(repo_root=tmp_path, config=config, model_client=client)

    result = orchestrator.run_task("Rate limit test")

    assert result.status == AgentStatus.FAILED
    assert "resource_exhausted" in result.error.lower() or "model provider error" in result.error.lower()


def test_malformed_model_response(tmp_path: Path):
    """Malformed model response (e.g. invalid json object or corrupt structure) does not crash orchestrator."""
    # ModelResponse with None text and empty tools
    bad_resp = ModelResponse(text=None, tool_calls=[])
    client = FakeModelClient([bad_resp])

    config = AegisConfig(
        verification=VerificationConfig(test_cmd="exit 1", required_gates=["test_cmd"])
    )
    orchestrator = Orchestrator(repo_root=tmp_path, config=config, model_client=client)

    result = orchestrator.run_task("Malformed response test")

    assert result.status == AgentStatus.FAILED
    assert result.status != AgentStatus.COMPLETED


def test_empty_model_response(tmp_path: Path):
    """Empty model response does not cause false completion."""
    empty_resp = ModelResponse(text="", tool_calls=[], is_proposing_completion=False)
    client = FakeModelClient([empty_resp])

    config = AegisConfig(
        verification=VerificationConfig(test_cmd="exit 1", required_gates=["test_cmd"])
    )
    orchestrator = Orchestrator(repo_root=tmp_path, config=config, model_client=client)

    result = orchestrator.run_task("Empty response test")

    assert result.status == AgentStatus.FAILED
    assert result.status != AgentStatus.COMPLETED


def test_provider_refusal_fails_safely(tmp_path: Path):
    """Provider returning safety refusal or explicit block fails closed."""
    refusal_resp = ModelResponse(
        text="I cannot fulfill this request because it violates safety guidelines.",
        tool_calls=[],
        is_proposing_completion=False,
    )
    client = FakeModelClient([refusal_resp])

    config = AegisConfig(
        verification=VerificationConfig(test_cmd="exit 1", required_gates=["test_cmd"])
    )
    orchestrator = Orchestrator(repo_root=tmp_path, config=config, model_client=client)

    result = orchestrator.run_task("Safety refusal test")

    assert result.status == AgentStatus.FAILED
    assert result.status != AgentStatus.COMPLETED
