"""Self-dogfooding runner executing an Aegis task against its own codebase."""

import sys
from pathlib import Path

from aegis.client import FakeModelClient, ModelResponse
from aegis.config import load_config
from aegis.models import AgentStatus, ToolCallRequest
from aegis.orchestrator import Orchestrator


def main():
    repo_root = Path(__file__).resolve().parent.parent
    config = load_config(repo_root)

    print(f"=== Aegis Self-Dogfooding Task ===")
    print(f"Repository: {repo_root}")
    print(f"Verification Gate: {config.verification.test_cmd}")

    # Script an intelligent agent task:
    # 1. Read aegis/verifier/runner.py
    # 2. Add an edge case unit test in tests/unit/test_verifier_dogfood.py
    # 3. Call run_verification
    # 4. Propose completion

    new_test_code = '''"""Dogfood test verifying VerificationRunner empty gates handling."""

from aegis.config import VerificationConfig
from aegis.execution.sandbox import LocalExecutor
from aegis.verifier.runner import VerificationRunner


def test_verification_runner_empty_gates(tmp_path):
    executor = LocalExecutor(tmp_path)
    config = VerificationConfig(pre_flight=None, lint=None, test_cmd=None, build_cmd=None)
    runner = VerificationRunner(tmp_path, executor, config)
    report = runner.run_all()
    assert report.status == "PASS"
    assert len(report.gates) == 0
'''

    resp1 = ModelResponse(
        text="I am analyzing aegis/verifier/runner.py and will add an edge-case test for empty gates.",
        tool_calls=[
            ToolCallRequest(
                id="call_read",
                name="read_file",
                arguments={"file_path": "aegis/verifier/runner.py", "start_line": 1, "end_line": 30},
            ),
            ToolCallRequest(
                id="call_write_test",
                name="write_patch",
                arguments={
                    "file_path": "tests/unit/test_verifier_dogfood.py",
                    "content": new_test_code,
                },
            ),
        ],
    )

    resp2 = ModelResponse(
        text="The new dogfood test was created. Now invoking the verification engine.",
        tool_calls=[
            ToolCallRequest(
                id="call_verify",
                name="run_verification",
                arguments={},
            ),
        ],
        is_proposing_completion=True,
    )

    client = FakeModelClient(responses=[resp1, resp2])
    orchestrator = Orchestrator(
        repo_root=repo_root,
        config=config,
        model_client=client,
    )

    task_desc = "Review the verifier implementation and add any missing tests"
    result = orchestrator.run_task(task_desc)

    print("\n=== Dogfooding Execution Report ===")
    print(f"Status: {result.status.value}")
    print(f"Session ID: {result.session_id}")
    print(f"Turns: {result.turns}")
    print(f"Duration: {round(result.duration_seconds, 2)}s")
    print(f"Changed Files: {result.changed_files}")

    if result.status == AgentStatus.COMPLETED:
        print("[✓] Self-dogfooding succeeded! Task was verified against real repository gates.")
        return 0
    else:
        print(f"[✗] Self-dogfooding failed: {result.error}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
