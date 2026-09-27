"""Unit tests verifying that interactive diff approval occurs BEFORE writes to disk."""

from pathlib import Path
from aegis.guard import GateGuard
from aegis.session.checkpoint import SessionCheckpoint
from aegis.tools.base import ToolContext
from aegis.tools.fs import WritePatchTool


def test_interactive_diff_approval_rejection_leaves_file_unchanged(tmp_path: Path):
    target_file = tmp_path / "greeting.py"
    target_file.write_text("orig_content = 'hello'\n", encoding="utf-8")

    captured_diffs = []

    def mock_reject_callback(file_path: str, diff_text: str) -> bool:
        captured_diffs.append((diff_text, file_path))
        return False  # User rejects the proposed patch

    gateguard = GateGuard(repo_root=tmp_path)
    checkpoint = SessionCheckpoint(tmp_path)
    ctx = ToolContext(
        repo_root=tmp_path,
        gateguard=gateguard,
        executor=None,
        checkpoint=checkpoint,
        interactive=True,
        approval_callback=mock_reject_callback,
    )

    tool = WritePatchTool()
    res = tool.execute(
        arguments={"file_path": "greeting.py", "content": "new_content = 'modified'\n"},
        context=ctx,
        call_id="call_patch_1",
    )

    assert res.success is False
    assert "rejected" in res.error.lower()
    # Invariant: Diff was presented before write, and rejection left file unchanged!
    assert len(captured_diffs) == 1
    assert "greeting.py" in captured_diffs[0][1]
    assert "-orig_content = 'hello'" in captured_diffs[0][0]
    assert target_file.read_text(encoding="utf-8") == "orig_content = 'hello'\n"


def test_interactive_diff_approval_acceptance_applies_write(tmp_path: Path):
    target_file = tmp_path / "service.py"
    target_file.write_text("status = 'pending'\n", encoding="utf-8")

    captured_diffs = []

    def mock_approve_callback(file_path: str, diff_text: str) -> bool:
        captured_diffs.append((diff_text, file_path))
        return True  # User approves the proposed patch

    gateguard = GateGuard(repo_root=tmp_path)
    checkpoint = SessionCheckpoint(tmp_path)
    ctx = ToolContext(
        repo_root=tmp_path,
        gateguard=gateguard,
        executor=None,
        checkpoint=checkpoint,
        interactive=True,
        approval_callback=mock_approve_callback,
    )

    tool = WritePatchTool()
    res = tool.execute(
        arguments={"file_path": "service.py", "content": "status = 'ready'\n"},
        context=ctx,
        call_id="call_patch_2",
    )

    assert res.success is True
    assert len(captured_diffs) == 1
    assert target_file.read_text(encoding="utf-8") == "status = 'ready'\n"
