"""Adversarial tests for PathGuard covering symlinks, encodings, case variants, and dot segments."""

import os
from pathlib import Path
import pytest

from aegis.guard.paths import PathGuard
from aegis.models import PolicyDecision
from aegis.tools.base import ToolContext
from aegis.tools.fs import ReadFileTool, WritePatchTool, ViewTreeTool
from aegis.guard import GateGuard
from aegis.session.checkpoint import SessionCheckpoint


def test_url_encoded_path_traversal(tmp_path: Path):
    guard = PathGuard(tmp_path)
    # URL encoded ../../
    assert guard.evaluate_path("%2e%2e%2f%2e%2e%2fetc%2fpasswd").decision == PolicyDecision.DENY
    assert guard.evaluate_path("%2e%2e/secret.txt").decision == PolicyDecision.DENY


def test_complex_dot_segments_traversal(tmp_path: Path):
    guard = PathGuard(tmp_path)
    assert guard.evaluate_path("./nested/dir/../../../../etc/shadow").decision == PolicyDecision.DENY
    assert guard.evaluate_path("foo/bar/../../../outside.txt").decision == PolicyDecision.DENY


def test_absolute_system_paths_denied(tmp_path: Path):
    guard = PathGuard(tmp_path)
    assert guard.evaluate_path("/etc/passwd").decision == PolicyDecision.DENY
    assert guard.evaluate_path("/var/log/syslog").decision == PolicyDecision.DENY
    assert guard.evaluate_path("/root/.ssh/id_rsa").decision == PolicyDecision.DENY


def test_symlink_pointing_outside_workspace_blocked(tmp_path: Path):
    guard = PathGuard(tmp_path)
    outside_file = tmp_path.parent / "outside_target.txt"
    outside_file.write_text("outside data", encoding="utf-8")

    symlink_path = tmp_path / "link_to_outside"
    try:
        os.symlink(outside_file, symlink_path)
    except OSError:
        pytest.skip("Symlink creation not supported on this OS/user")

    res = guard.evaluate_path("link_to_outside")
    assert res.decision == PolicyDecision.DENY
    assert "symlink" in res.reason.lower() or "outside" in res.reason.lower()


def test_nested_symlinks_pointing_outside_blocked(tmp_path: Path):
    guard = PathGuard(tmp_path)
    outside_dir = tmp_path.parent / "outside_dir"
    outside_dir.mkdir(exist_ok=True)
    outside_target = outside_dir / "target.txt"
    outside_target.write_text("secret", encoding="utf-8")

    sub_dir = tmp_path / "subdir"
    sub_dir.mkdir()
    symlink_nested = sub_dir / "escape_link"

    try:
        os.symlink(outside_target, symlink_nested)
    except OSError:
        pytest.skip("Symlink creation not supported")

    res = guard.evaluate_path("subdir/escape_link")
    assert res.decision == PolicyDecision.DENY


def test_case_variant_protected_files_denied(tmp_path: Path):
    guard = PathGuard(tmp_path)
    assert guard.evaluate_path(".ENV").decision == PolicyDecision.DENY
    assert guard.evaluate_path(".Env").decision == PolicyDecision.DENY
    assert guard.evaluate_path(".GIT/config").decision == PolicyDecision.DENY
    assert guard.evaluate_path("SECRETS/key.pem").decision == PolicyDecision.DENY
    assert guard.evaluate_path("ID_RSA").decision == PolicyDecision.DENY


def test_centralized_guard_enforced_across_all_fs_tools(tmp_path: Path):
    """Verifies view_tree, read_file, and write_patch all uniformly block path traversal."""
    gateguard = GateGuard(repo_root=tmp_path)
    checkpoint = SessionCheckpoint(tmp_path)
    ctx = ToolContext(
        repo_root=tmp_path,
        gateguard=gateguard,
        executor=None,
        checkpoint=checkpoint,
    )

    read_tool = ReadFileTool()
    write_tool = WritePatchTool()
    tree_tool = ViewTreeTool()

    # Read traversal
    res_read = read_tool.execute({"file_path": "../../etc/passwd"}, ctx, "c1")
    assert res_read.success is False
    assert "denied" in res_read.error.lower() or "traversal" in res_read.error.lower()

    # Write traversal
    res_write = write_tool.execute({"file_path": "../outside.py", "content": "x = 1"}, ctx, "c2")
    assert res_write.success is False
    assert "denied" in res_write.error.lower() or "traversal" in res_write.error.lower()

    # Tree traversal
    res_tree = tree_tool.execute({"directory": "../.."}, ctx, "c3")
    assert res_tree.success is False
    assert "denied" in res_tree.error.lower() or "traversal" in res_tree.error.lower()
