"""Unit tests for configuration loading and validation."""

from pathlib import Path
import pytest
import yaml

from aegis.config import AegisConfig, load_config
from aegis.errors import ConfigurationError


def test_default_config(tmp_path: Path):
    cfg = load_config(tmp_path)
    assert cfg.version == 1
    assert cfg.guardrails.fail_closed is True
    assert ".git/**" in cfg.guardrails.deny_paths
    assert ".env" in cfg.guardrails.deny_paths
    assert cfg.model.resolved_model in ("gemini-3.8-flash", "gemini-2.5-flash")


def test_custom_valid_config(tmp_path: Path):
    config_file = tmp_path / ".aegis.yaml"
    data = {
        "version": 1,
        "project": {"name": "test_service", "stack": "python"},
        "agent": {"max_turns": 15, "max_repairs": 3},
        "verification": {"test_cmd": "pytest tests/ -v"},
    }
    config_file.write_text(yaml.dump(data), encoding="utf-8")

    cfg = load_config(tmp_path)
    assert cfg.project.name == "test_service"
    assert cfg.agent.max_turns == 15
    assert cfg.agent.max_repairs == 3
    assert cfg.verification.test_cmd == "pytest tests/ -v"


def test_invalid_yaml_raises_configuration_error(tmp_path: Path):
    config_file = tmp_path / ".aegis.yaml"
    config_file.write_text("invalid: yaml: : content [", encoding="utf-8")

    with pytest.raises(ConfigurationError):
        load_config(tmp_path)


def test_pydantic_validation_error_on_bad_types(tmp_path: Path):
    config_file = tmp_path / ".aegis.yaml"
    data = {
        "version": 1,
        "agent": {"max_turns": "not_an_int"},
    }
    config_file.write_text(yaml.dump(data), encoding="utf-8")

    with pytest.raises(ConfigurationError):
        load_config(tmp_path)
