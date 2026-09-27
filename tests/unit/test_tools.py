"""Unit tests for built-in tools (view_tree, read_file, write_patch, search, run_command)."""

from pathlib import Path
from aegis.execution.sandbox import LocalExecutor
from aegis.guard import GateGuard
from aegis.session.checkpoint import SessionCheckpoint
from aegis.tools.base import ToolContext
from aegis.tools.fs import ReadFileTool, SearchTool, ViewTreeTool, WritePatchTool
from aegis.tools.registry import create_default_registry
from aegis.tools.shell import RunCommandTool


def build_test_context(repo_root: Path) -> ToolContext:
    gateguard = GateGuard(repo_root)
    executor = LocalExecutor(repo_root)
    checkpoint = SessionCheckpoint(repo_root)
    return ToolContext(
        repo_root=repo_root,
        gateguard=gateguard,
        executor=executor,
        checkpoint=checkpoint,
    )


def test_write_patch_and_read_file(tmp_path: Path):
    ctx = build_test_context(tmp_path)
    write_tool = WritePatchTool()
    read_tool = ReadFileTool()

    # Write file
    w_res = write_tool.execute(
        {"file_path": "hello.py", "content": "print('hello world')\n"},
        ctx,
        call_id="call_1",
    )
    assert w_res.success is True
    assert (tmp_path / "hello.py").exists()

    # Read file
    r_res = read_tool.execute(
        {"file_path": "hello.py"},
        ctx,
        call_id="call_2",
    )
    assert r_res.success is True
    assert "print('hello world')" in r_res.output


def test_write_patch_protected_path_denied(tmp_path: Path):
    ctx = build_test_context(tmp_path)
    write_tool = WritePatchTool()

    # Attempt to write to .env
    res = write_tool.execute(
        {"file_path": ".env", "content": "SECRET=123"},
        ctx,
        call_id="call_deny",
    )
    assert res.success is False
    assert "Write denied" in res.error or "Access denied" in res.error


def test_view_tree(tmp_path: Path):
    ctx = build_test_context(tmp_path)
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("code", encoding="utf-8")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_main.py").write_text("test", encoding="utf-8")

    tree_tool = ViewTreeTool()
    res = tree_tool.execute({"directory": "."}, ctx, call_id="call_tree")
    assert res.success is True
    assert "main.py" in res.output
    assert "test_main.py" in res.output


def test_search_tool(tmp_path: Path):
    ctx = build_test_context(tmp_path)
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "calc.py").write_text("def multiply(a, b): return a * b\n", encoding="utf-8")

    search_tool = SearchTool()
    res = search_tool.execute({"query": "multiply"}, ctx, call_id="call_search")
    assert res.success is True
    assert "calc.py" in res.output
    assert "multiply" in res.output


def test_run_command_tool(tmp_path: Path):
    ctx = build_test_context(tmp_path)
    cmd_tool = RunCommandTool()

    res = cmd_tool.execute({"command": "echo 'Aegis Verified'"}, ctx, call_id="call_cmd")
    assert res.success is True
    assert "Aegis Verified" in res.output


def test_run_command_blocked_executable(tmp_path: Path):
    ctx = build_test_context(tmp_path)
    cmd_tool = RunCommandTool()

    res = cmd_tool.execute({"command": "sudo whoami"}, ctx, call_id="call_sudo")
    assert res.success is False
    assert "blocked" in res.error.lower()
