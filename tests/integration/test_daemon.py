"""Integration test for Aegis background daemon IPC."""

import threading
import time
from pathlib import Path
from aegis.daemon.client import DaemonClient
from aegis.daemon.server import DaemonServer


def test_daemon_lifecycle(tmp_path: Path):
    server = DaemonServer(tmp_path)

    # Run daemon server in background thread
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

    # 3. Stop
    stop_resp = client.send_request("stop")
    assert stop_resp.status == "OK"

    time.sleep(0.5)
    # Server should be stopped
    assert not client.is_running()
