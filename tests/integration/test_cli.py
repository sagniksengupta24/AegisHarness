"""Integration tests for Aegis CLI commands."""

from pathlib import Path
from aegis.cli import main


def test_cli_init_and_doctor(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    # aegis init
    ret = main(["init"])
    assert ret == 0
    assert (tmp_path / ".aegis.yaml").exists()
    assert (tmp_path / ".aegis" / "skills").exists()
    assert (tmp_path / ".vscode" / "tasks.json").exists()

    # aegis doctor
    ret_doc = main(["doctor"])
    assert ret_doc in (0, 1)

    # aegis status
    ret_status = main(["status"])
    assert ret_status == 0


def test_cli_memory_add_and_list(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    main(["init"])

    # Add memory
    ret_add = main(["memory", "add", "--lesson", "Test lesson text", "--tags", "test,cli"])
    assert ret_add == 0

    # List memory
    ret_list = main(["memory", "list"])
    assert ret_list == 0


def test_cli_verify_gate(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    main(["init"])

    # Overwrite .aegis.yaml with passing test_cmd
    cfg_file = tmp_path / ".aegis.yaml"
    cfg_text = cfg_file.read_text(encoding="utf-8").replace('test_cmd: "pytest tests/ -q"', 'test_cmd: "echo pass && exit 0"')
    cfg_file.write_text(cfg_text, encoding="utf-8")

    ret_verify = main(["verify"])
    assert ret_verify == 0


def test_cli_commit_and_remember_dry_run(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    main(["init"])

    # Set passing verification gate
    cfg_file = tmp_path / ".aegis.yaml"
    cfg_text = cfg_file.read_text(encoding="utf-8").replace('test_cmd: "pytest tests/ -q"', 'test_cmd: "exit 0"')
    cfg_file.write_text(cfg_text, encoding="utf-8")

    # Create dummy modified file
    (tmp_path / "app.py").write_text("print('hello')\n", encoding="utf-8")

    # Execute commit --dry-run with lesson
    ret = main(["commit", "--dry-run", "--lesson", "Remember to test dry run"])
    assert ret == 0

    # Verify lesson was saved in memory
    mem_file = tmp_path / ".aegis" / "memory.json"
    assert mem_file.exists()
    assert "Remember to test dry run" in mem_file.read_text(encoding="utf-8")


def test_cli_commit_blocks_on_failing_verification(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    main(["init"])

    # Set failing verification gate
    cfg_file = tmp_path / ".aegis.yaml"
    cfg_text = cfg_file.read_text(encoding="utf-8").replace('test_cmd: "pytest tests/ -q"', 'test_cmd: "exit 1"')
    cfg_file.write_text(cfg_text, encoding="utf-8")

    (tmp_path / "bad.py").write_text("broken = True\n", encoding="utf-8")

    # Invariant: Commit must abort with exit code 1 when verification fails
    ret = main(["commit", "--dry-run"])
    assert ret == 1


def test_cli_diff_invocation(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    main(["init"])

    ret = main(["diff"])
    assert ret in (0, 1)
