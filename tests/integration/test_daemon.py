"""Integration tests for Aegis background daemon IPC handling real tasks, verify, ping, stop, and concurrency."""

import json
import socket
import threading
import time
from pathlib import Path
import pytest

from aegis.daemon.client import DaemonClient
from aegis.daemon.server import DaemonServer
from aegis.client import FakeModelClient, ModelResponse
from aegis.models import ToolCallRequest, AgentStatus


def test_daemon_lifecycle_and_real_task_execution(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    # Setup repo configuration with a passing gate
    from aegis.cli import main
    main(["init"])
    cfg_file = tmp_path / ".aegis.yaml"
    cfg_text = cfg_file.read_text(encoding="utf-8").replace('test_cmd: "pytest tests/ -q"', 'test_cmd: "exit 0"')
    cfg_file.write_text(cfg_text, encoding="utf-8")

    server = DaemonServer(tmp_path)

    # Inject fake model client capable of executing a task
    resp1 = ModelResponse(
        text="Creating file",
        tool_calls=[
            ToolCallRequest(id="tc1", name="write_patch", arguments={"file_path": "daemon_test.py", "content": "x = 42\n"}),
        ],
        is_proposing_completion=True,
    )
    server.model_client = FakeModelClient(responses=[resp1])

    # Run daemon in background thread
    server_thread = threading.Thread(target=server.start, kwargs={"foreground": True}, daemon=True)
    server_thread.start()

    time.sleep(0.3)
    client = DaemonClient(tmp_path)

    # 1. Ping
    assert client.is_running() is True
    ping_resp = client.send_request("ping")
    assert ping_resp.status == "OK"
    assert ping_resp.result.get("pong") is True

    # 2. Status
    status_resp = client.send_request("status")
    assert status_resp.status == "OK"
    assert "pid" in status_resp.result

    # 3. Verify gate via daemon
    verify_resp = client.send_request("verify")
    assert verify_resp.status == "OK"
    assert verify_resp.result.get("status") == "PASS"

    # 4. Run real task via daemon
    run_resp = client.send_request("run", payload={"task": "Create daemon_test.py"})
    assert run_resp.status == "OK"
    assert (tmp_path / "daemon_test.py").exists()
    assert (tmp_path / "daemon_test.py").read_text(encoding="utf-8") == "x = 42\n"

    # 5. Stop
    stop_resp = client.send_request("stop")
    assert stop_resp.status == "OK"

    time.sleep(0.5)
    assert not client.is_running()


def test_daemon_handles_malformed_requests(tmp_path: Path):
    server = DaemonServer(tmp_path)
    server_thread = threading.Thread(target=server.start, kwargs={"foreground": True}, daemon=True)
    server_thread.start()
    time.sleep(0.3)

    client = DaemonClient(tmp_path)
    assert client.is_running()

    # Send raw malformed bytes directly to port/socket
    sock = client._connect()
    try:
        sock.sendall(b"NOT_A_VALID_JSON_STRING\n")
        sock.settimeout(2.0)
        data = sock.recv(4096)
        resp_obj = json.loads(data.decode("utf-8"))
        assert resp_obj["status"] == "ERROR"
    finally:
        sock.close()

    # Clean shutdown
    client.send_request("stop")
    time.sleep(0.3)


def test_daemon_handles_concurrent_requests(tmp_path: Path):
    server = DaemonServer(tmp_path)
    server_thread = threading.Thread(target=server.start, kwargs={"foreground": True}, daemon=True)
    server_thread.start()
    time.sleep(0.3)

    client = DaemonClient(tmp_path)
    results = []

    def make_call(i):
        c = DaemonClient(tmp_path)
        resp = c.send_request("ping", payload={"call_index": i})
        results.append(resp.status)

    threads = [threading.Thread(target=make_call, args=(i,)) for i in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(results) == 5
    assert all(r == "OK" for r in results)

    client.send_request("stop")
    time.sleep(0.3)
