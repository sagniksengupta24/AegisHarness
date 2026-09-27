"""True Live End-to-End Tests with real Gemini API and real Aegis Orchestrator (Section 4).

Executed only when GEMINI_API_KEY is configured in the environment.
Exercises:
1. True Live E2E Success Path:
   Real Gemini -> Real Aegis Orchestrator -> Plan -> Real Tool Call -> Real File Change -> Real Verification -> COMPLETED.
2. True Live E2E Failure & Diagnosis/Repair Loop:
   Pre-existing failing test -> Real Verification Fail -> Gemini receives diagnosis -> Gemini applies repair -> Verification PASS -> COMPLETED.
"""

import os
import shutil
import sys
from pathlib import Path
import pytest

from aegis.client import GeminiModelClient
from aegis.config import AegisConfig, VerificationConfig
from aegis.models import AgentStatus
from aegis.orchestrator import Orchestrator


@pytest.fixture
def clean_e2e_repo(tmp_path_factory) -> Path:
    repo = tmp_path_factory.mktemp("aegis_live_e2e_repo")
    (repo / "src").mkdir(parents=True, exist_ok=True)
    (repo / "tests").mkdir(parents=True, exist_ok=True)
    return repo


def test_live_gemini_e2e_success_path(clean_e2e_repo: Path):
    """Proves the entire chain from real model prompt to file creation and verification passing."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key or not api_key.strip():
        pytest.skip("GEMINI_API_KEY not configured; skipping live Gemini E2E test")

    python_bin = sys.executable
    config = AegisConfig(
        verification=VerificationConfig(
            test_cmd=f"{python_bin} -m pytest tests/ -q",
            required_gates=["test_cmd"],
            timeout_seconds=30,
        )
    )

    client = GeminiModelClient(api_key=api_key)
    orchestrator = Orchestrator(
        repo_root=clean_e2e_repo,
        config=config,
        model_client=client,
    )

    task_prompt = (
        "Create a module src/calc.py with a function 'add(a, b)' that returns the sum of two numbers. "
        "Also create tests/test_calc.py with a test function verifying add(2, 3) == 5. "
        "Use write_patch to create the files and run_verification to verify."
    )

    result = orchestrator.run_task(task_prompt)

    # Invariants:
    # 1. State must be COMPLETED
    assert result.status == AgentStatus.COMPLETED, f"Live task failed: {result.error}"
    # 2. Files created on real disk
    assert (clean_e2e_repo / "src" / "calc.py").exists()
    assert (clean_e2e_repo / "tests" / "test_calc.py").exists()
    # 3. Verification report is PASS
    assert result.verification is not None
    assert result.verification.status == "PASS"


def test_live_gemini_e2e_failure_repair_loop(clean_e2e_repo: Path):
    """Proves the live repair loop: verification fails, Gemini receives failure, patches code, and passes."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key or not api_key.strip():
        pytest.skip("GEMINI_API_KEY not configured; skipping live Gemini repair test")

    # Seed an intentional bug in the repository
    (clean_e2e_repo / "src" / "math_ops.py").write_text(
        "def multiply(a, b):\n    return a + b  # Intentional bug for repair test\n",
        encoding="utf-8",
    )
    (clean_e2e_repo / "tests" / "test_math_ops.py").write_text(
        "from src.math_ops import multiply\n\ndef test_multiply():\n    assert multiply(3, 4) == 12\n",
        encoding="utf-8",
    )

    python_bin = sys.executable
    config = AegisConfig(
        verification=VerificationConfig(
            test_cmd=f"{python_bin} -m pytest tests/ -q",
            required_gates=["test_cmd"],
            timeout_seconds=30,
        )
    )

    client = GeminiModelClient(api_key=api_key)
    orchestrator = Orchestrator(
        repo_root=clean_e2e_repo,
        config=config,
        model_client=client,
    )

    task_prompt = (
        "Run verification, diagnose the failing test in tests/test_math_ops.py, "
        "fix the implementation in src/math_ops.py, and verify until tests pass."
    )

    result = orchestrator.run_task(task_prompt)

    # Invariants:
    assert result.status == AgentStatus.COMPLETED, f"Live repair failed: {result.error}"
    assert result.verification is not None
    assert result.verification.status == "PASS"
    # Ensure bug was actually fixed in the file
    content = (clean_e2e_repo / "src" / "math_ops.py").read_text(encoding="utf-8")
    assert "a * b" in content or "return a*b" in content or "return a * b" in content
