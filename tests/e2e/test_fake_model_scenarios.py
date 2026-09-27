"""End-to-end tests exercising deterministic agent loop scenarios using FakeModelClient."""

from pathlib import Path
from aegis.client import FakeModelClient, ModelResponse
from aegis.config import AegisConfig, VerificationConfig
from aegis.models import AgentStatus, ToolCallRequest
from aegis.orchestrator import Orchestrator


def build_test_orchestrator(repo_root: Path, client: FakeModelClient, verification_cmd: str) -> Orchestrator:
    config = AegisConfig(
        verification=VerificationConfig(
            test_cmd=verification_cmd,
            required_gates=["test_cmd"],
            timeout_seconds=10,
        ),
    )
    return Orchestrator(
        repo_root=repo_root,
        config=config,
        model_client=client,
    )


def test_scenario_a_inspect_patch_verify_completed(tmp_path: Path):
    """Scenario A: Model inspects directory, writes clean patch, verification passes -> COMPLETED."""
    target_file = tmp_path / "calc.py"
    target_file.write_text("def add(a, b): return 0\n", encoding="utf-8")

    # Scripted model responses
    resp1 = ModelResponse(
        text="I will check the directory tree and patch calc.py.",
        tool_calls=[
            ToolCallRequest(id="c1", name="view_tree", arguments={"directory": "."}),
            ToolCallRequest(id="c2", name="write_patch", arguments={"file_path": "calc.py", "content": "def add(a, b): return a + b\n"}),
        ],
    )
    resp2 = ModelResponse(
        text="Patch applied. Proposing task completion.",
        is_proposing_completion=True,
    )

    fake_client = FakeModelClient(responses=[resp1, resp2])
    orchestrator = build_test_orchestrator(
        repo_root=tmp_path,
        client=fake_client,
        verification_cmd="python3 -c 'import calc; assert calc.add(2, 3) == 5'",
    )

    result = orchestrator.run_task("Fix the add function in calc.py")
    assert result.status == AgentStatus.COMPLETED
    assert "calc.py" in result.changed_files
    assert target_file.read_text(encoding="utf-8") == "def add(a, b): return a + b\n"


def test_scenario_b_failure_repair_completed(tmp_path: Path):
    """Scenario B: Model writes bad patch, verification fails, model receives error, repairs, verify passes -> COMPLETED."""
    target_file = tmp_path / "greeting.py"
    target_file.write_text("def greet(): return 'wrong'\n", encoding="utf-8")

    # Turn 1: Model writes buggy patch
    resp1 = ModelResponse(
        text="Applying initial patch.",
        tool_calls=[
            ToolCallRequest(id="c1", name="write_patch", arguments={"file_path": "greeting.py", "content": "def greet(): return 'hello'\n"}),
        ],
        is_proposing_completion=True,
    )
    # Turn 2: Verification failed! Model receives failure diagnosis and repairs with correct return value
    resp2 = ModelResponse(
        text="Verification failed. Repairing greeting to 'Hello, World!'.",
        tool_calls=[
            ToolCallRequest(id="c2", name="write_patch", arguments={"file_path": "greeting.py", "content": "def greet(): return 'Hello, World!'\n"}),
        ],
        is_proposing_completion=True,
    )

    fake_client = FakeModelClient(responses=[resp1, resp2])
    orchestrator = build_test_orchestrator(
        repo_root=tmp_path,
        client=fake_client,
        verification_cmd="python3 -c 'import greeting; assert greeting.greet() == \"Hello, World!\"'",
    )

    result = orchestrator.run_task("Fix greeting to return Hello, World!")
    assert result.status == AgentStatus.COMPLETED
    assert target_file.read_text(encoding="utf-8") == "def greet(): return 'Hello, World!'\n"


def test_scenario_c_repeated_failure_terminates_with_rollback(tmp_path: Path):
    """Scenario C: Verification fails repeatedly -> FAILED (not infinite looping), changes rolled back."""
    target_file = tmp_path / "math_mod.py"
    target_file.write_text("orig_math = 10\n", encoding="utf-8")

    # Model proposes invalid fix multiple times
    resps = [
        ModelResponse(
            text=f"Attempt {i}",
            tool_calls=[
                ToolCallRequest(id=f"c_{i}", name="write_patch", arguments={"file_path": "math_mod.py", "content": "bad_code = 1\n"}),
            ],
            is_proposing_completion=True,
        )
        for i in range(10)
    ]

    fake_client = FakeModelClient(responses=resps)
    orchestrator = build_test_orchestrator(
        repo_root=tmp_path,
        client=fake_client,
        verification_cmd="echo 'assertion failed' >&2 && exit 1",
    )

    result = orchestrator.run_task("Unsolvable task")
    assert result.status == AgentStatus.FAILED
    # Crucial invariant: Aegis performed rollback, so math_mod.py was restored to original content!
    assert target_file.read_text(encoding="utf-8") == "orig_math = 10\n"


def test_scenario_d_model_attempts_env_access(tmp_path: Path):
    """Scenario D: Model tries to read .env -> Tool denial, never leaks secrets."""
    env_file = tmp_path / ".env"
    env_file.write_text("SECRET_KEY=confidential\n", encoding="utf-8")

    resp1 = ModelResponse(
        text="Let me inspect the environment variables in .env.",
        tool_calls=[
            ToolCallRequest(id="c_env", name="read_file", arguments={"file_path": ".env"}),
        ],
    )
    resp2 = ModelResponse(
        text="Understood, .env is protected.",
        is_proposing_completion=True,
    )

    fake_client = FakeModelClient(responses=[resp1, resp2])
    orchestrator = build_test_orchestrator(
        repo_root=tmp_path,
        client=fake_client,
        verification_cmd="exit 0",
    )

    result = orchestrator.run_task("Check environment")
    # Verify audit log recorded denial
    audit_calls = orchestrator.registry.audit_log
    env_call = [a for a in audit_calls if a["call_id"] == "c_env"]
    assert len(env_call) == 1
    assert env_call[0]["success"] is False
    assert "denied" in env_call[0]["error"].lower() or "protected" in env_call[0]["error"].lower()


def test_scenario_e_model_attempts_path_traversal(tmp_path: Path):
    """Scenario E: Model tries path traversal -> Tool denial."""
    resp1 = ModelResponse(
        text="Trying to read outside repository.",
        tool_calls=[
            ToolCallRequest(id="c_trav", name="read_file", arguments={"file_path": "../../outside_secret.txt"}),
        ],
    )
    resp2 = ModelResponse(
        text="Understood, traversal is forbidden.",
        is_proposing_completion=True,
    )

    fake_client = FakeModelClient(responses=[resp1, resp2])
    orchestrator = build_test_orchestrator(
        repo_root=tmp_path,
        client=fake_client,
        verification_cmd="exit 0",
    )

    result = orchestrator.run_task("Try traversal")
    audit_calls = orchestrator.registry.audit_log
    trav_call = [a for a in audit_calls if a["call_id"] == "c_trav"]
    assert len(trav_call) == 1
    assert trav_call[0]["success"] is False
    assert "traversal" in trav_call[0]["error"].lower() or "outside repository" in trav_call[0]["error"].lower()
