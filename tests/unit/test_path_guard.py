"""Unit tests for PathGuard containment and protected path rules."""

from pathlib import Path
import pytest

from aegis.errors import PathGuardError
from aegis.guard.paths import PathGuard
from aegis.models import PolicyDecision


def test_allowed_contained_path(tmp_path: Path):
    guard = PathGuard(tmp_path)
    res = guard.evaluate_path("src/module.py")
    assert res.decision == PolicyDecision.ALLOW


def test_path_traversal_blocked(tmp_path: Path):
    guard = PathGuard(tmp_path)
    res = guard.evaluate_path("../outside.txt")
    assert res.decision == PolicyDecision.DENY
    assert "traversal" in res.reason.lower()

    with pytest.raises(PathGuardError):
        guard.validate_path("../../etc/passwd")


def test_absolute_path_outside_repo_blocked(tmp_path: Path):
    guard = PathGuard(tmp_path)
    res = guard.evaluate_path("/etc/hosts")
    assert res.decision == PolicyDecision.DENY
    assert "outside repository root" in res.reason.lower()


def test_git_directory_protected(tmp_path: Path):
    guard = PathGuard(tmp_path)
    assert guard.evaluate_path(".git").decision == PolicyDecision.DENY
    assert guard.evaluate_path(".git/config").decision == PolicyDecision.DENY
    assert guard.evaluate_path(".git/HEAD").decision == PolicyDecision.DENY


def test_env_files_protected(tmp_path: Path):
    guard = PathGuard(tmp_path)
    assert guard.evaluate_path(".env").decision == PolicyDecision.DENY
    assert guard.evaluate_path(".env.local").decision == PolicyDecision.DENY
    assert guard.evaluate_path(".env.production").decision == PolicyDecision.DENY


def test_secrets_and_keys_protected(tmp_path: Path):
    guard = PathGuard(tmp_path)
    assert guard.evaluate_path("secrets/private.key").decision == PolicyDecision.DENY
    assert guard.evaluate_path("cert.pem").decision == PolicyDecision.DENY
    assert guard.evaluate_path("id_rsa").decision == PolicyDecision.DENY
    assert guard.evaluate_path("credentials.json").decision == PolicyDecision.DENY
