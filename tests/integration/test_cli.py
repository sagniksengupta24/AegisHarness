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
