"""Unit tests for LocalExecutor security: timeouts, process trees, truncation, and containment."""

import os
import signal
import sys
import time
from pathlib import Path
import pytest

from aegis.execution.sandbox import LocalExecutor


def test_hung_process_timeout(tmp_path: Path):
    executor = LocalExecutor(tmp_path, timeout_seconds=1)
    # Process sleeps for 10 seconds, but timeout is 1s
    cmd = "python3 -c 'import time; time.sleep(10)'"
    start = time.perf_counter()
    res = executor.execute(cmd)
    elapsed = time.perf_counter() - start

    assert res.timed_out is True
    assert res.exit_code == -1
    assert elapsed < 4.0  # Finished within reasonable margin of timeout


def test_child_process_tree_cleanup_on_timeout(tmp_path: Path):
    """Verifies that grandchild processes are terminated when timeout kills the process group."""
    executor = LocalExecutor(tmp_path, timeout_seconds=1)

    # Command spawns a background child process that sleeps
    cmd = "python3 -c 'import subprocess, sys; p = subprocess.Popen([sys.executable, \"-c\", \"import time; time.sleep(15)\"]); p.wait()'"
    start = time.perf_counter()
    res = executor.execute(cmd)
    elapsed = time.perf_counter() - start

    assert res.timed_out is True
    assert elapsed < 4.0


def test_large_stdout_truncation(tmp_path: Path):
    max_bytes = 2048
    executor = LocalExecutor(tmp_path, max_output_bytes=max_bytes)

    # Generate 100KB stdout
    cmd = "python3 -c 'print(\"A\" * 100_000)'"
    res = executor.execute(cmd)

    assert res.exit_code == 0
    assert len(res.stdout.encode("utf-8")) <= max_bytes + 200
    assert "TRUNCATED" in res.stdout


def test_large_stderr_truncation(tmp_path: Path):
    max_bytes = 1024
    executor = LocalExecutor(tmp_path, max_output_bytes=max_bytes)

    # Generate 50KB stderr
    cmd = "python3 -c 'import sys; sys.stderr.write(\"E\" * 50_000)'"
    res = executor.execute(cmd)

    assert res.exit_code == 0
    assert len(res.stderr.encode("utf-8")) <= max_bytes + 200
    assert "TRUNCATED" in res.stderr


def test_nonzero_exit_code_captured(tmp_path: Path):
    executor = LocalExecutor(tmp_path)
    res = executor.execute("python3 -c 'import sys; sys.exit(42)'")

    assert res.exit_code == 42
    assert res.timed_out is False


def test_working_directory_containment(tmp_path: Path):
    executor = LocalExecutor(tmp_path)
    outside_dir = tmp_path.parent

    res = executor.execute("pwd", cwd=outside_dir)
    assert res.exit_code == -1
    assert "outside repository root" in res.stderr.lower() or "security violation" in res.stderr.lower()
