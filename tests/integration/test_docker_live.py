"""Docker execution backend integration tests.

When Docker daemon is available: runs a real container to verify execution, mounts, timeouts, and network isolation.
When Docker is unavailable: tests fallback behavior and reports Docker runtime path not live-verified.
"""

from pathlib import Path
import pytest

from aegis.execution.sandbox import DockerExecutor, get_executor, is_docker_available, LocalExecutor
from aegis.errors import ConfigurationError


def test_docker_backend_live_or_fallback(tmp_path: Path):
    """Exercises DockerExecutor when available, or verifies clean LocalExecutor fallback."""
    test_file = tmp_path / "hello.txt"
    test_file.write_text("workspace content\n", encoding="utf-8")

    if not is_docker_available():
        # Test fallback path
        fallback_exec = get_executor(tmp_path, backend="auto")
        assert isinstance(fallback_exec, LocalExecutor)

        # Verifying explicit docker backend raises ConfigurationError when daemon not available
        with pytest.raises(ConfigurationError):
            get_executor(tmp_path, backend="docker")

        pytest.skip(
            "Docker daemon not running in this environment. "
            "Verified fallback path to LocalExecutor. "
            "Docker runtime path classified as: NOT LIVE-VERIFIED."
        )

    # Docker IS available: execute real container tests
    executor = DockerExecutor(tmp_path, image="python:3.12-slim", network="none", timeout_seconds=15)

    # 1. Container created, workspace mounted, command executed, stdout & exit code captured
    res = executor.execute("cat hello.txt && echo 'container_success'")
    assert res.exit_code == 0
    assert "workspace content" in res.stdout
    assert "container_success" in res.stdout
    assert res.backend == "docker"

    # 2. Stderr captured
    res_err = executor.execute("python3 -c 'import sys; sys.stderr.write(\"docker_error_stream\\n\"); sys.exit(7)'")
    assert res_err.exit_code == 7
    assert "docker_error_stream" in res_err.stderr

    # 3. Timeout handled & container cleaned up
    res_timeout = executor.execute("python3 -c 'import time; time.sleep(10)'", timeout=1)
    assert res_timeout.timed_out is True
    assert res_timeout.exit_code == -1

    # 4. Network isolation verified (--network none blocks socket connect)
    res_net = executor.execute("python3 -c 'import urllib.request; urllib.request.urlopen(\"http://1.1.1.1\", timeout=2)'")
    assert res_net.exit_code != 0
