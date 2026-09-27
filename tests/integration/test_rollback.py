"""Integration test for transactional workspace safety and surgical rollback."""

from pathlib import Path
from aegis.session.checkpoint import SessionCheckpoint
from aegis.tools.fs import WritePatchTool
from aegis.tools.base import ToolContext
from aegis.guard import GateGuard
from aegis.execution.sandbox import LocalExecutor


def test_surgical_rollback_preserves_pre_existing_modifications(tmp_path: Path):
    """Proves that Aegis rollback reverts ONLY Aegis changes and leaves user modifications intact."""
    repo = tmp_path

    # Step 1: Pre-existing user files and modifications
    user_file = repo / "user_feature.py"
    user_file.write_text("print('user pre-existing code')\n", encoding="utf-8")

    user_untracked = repo / "notes.txt"
    user_untracked.write_text("user notes\n", encoding="utf-8")

    # Step 2: Aegis session begins
    checkpoint = SessionCheckpoint(repo, session_id="test_sess")
    gateguard = GateGuard(repo)
    executor = LocalExecutor(repo)
    ctx = ToolContext(
        repo_root=repo,
        gateguard=gateguard,
        executor=executor,
        checkpoint=checkpoint,
    )
    write_tool = WritePatchTool()

    # Step 3: Aegis modifies an existing file and creates a new file
    target_existing = repo / "service.py"
    target_existing.write_text("def service(): return 1\n", encoding="utf-8")

    # Aegis touches service.py
    write_tool.execute(
        {"file_path": "service.py", "content": "def service(): return 2  # aegis broken change\n"},
        ctx,
        call_id="call_1",
    )
    # Aegis creates a new broken file
    write_tool.execute(
        {"file_path": "broken_extra.py", "content": "broken code\n"},
        ctx,
        call_id="call_2",
    )

    # Concurrently user makes another modification to user_feature.py
    user_file.write_text("print('user pre-existing code + user extra edit')\n", encoding="utf-8")

    # Step 4: Verification fails -> Rollback is triggered
    checkpoint.rollback()

    # Step 5: Verification of invariants:
    # A) Pre-existing user work survived completely intact!
    assert user_file.read_text(encoding="utf-8") == "print('user pre-existing code + user extra edit')\n"
    assert user_untracked.read_text(encoding="utf-8") == "user notes\n"

    # B) Aegis's modified file was reverted to its pre-session content!
    assert target_existing.read_text(encoding="utf-8") == "def service(): return 1\n"

    # C) Aegis's newly created file was deleted!
    assert not (repo / "broken_extra.py").exists()
