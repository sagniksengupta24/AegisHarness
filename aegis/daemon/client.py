"""IPC Client for communicating with the Aegis background daemon."""

import json
import socket
import uuid
from pathlib import Path
from typing import Any, Optional

from aegis.daemon.protocol import DaemonRequest, DaemonResponse
from aegis.errors import DaemonError


class DaemonClient:
    """Client for Unix domain socket or localhost TCP communication with Aegis daemon."""

    def __init__(self, repo_root: Path):
        self.repo_root = repo_root.resolve()
        self.sock_path = self.repo_root / ".aegis" / "daemon.sock"
        self.port_path = self.repo_root / ".aegis" / "daemon.port"

    def is_running(self) -> bool:
        """Checks if daemon socket/port exists and responds to ping."""
        if not self.sock_path.exists() and not self.port_path.exists():
            return False
        try:
            resp = self.send_request("ping", timeout=2.0)
            return resp.status == "OK" and resp.result.get("pong") is True
        except Exception:
            return False

    def send_request(
        self,
        command: str,
        payload: Optional[dict[str, Any]] = None,
        timeout: float = 15.0,
    ) -> DaemonResponse:
        """Sends a structured request and awaits response."""
        client_sock = None

        if self.sock_path.exists():
            try:
                client_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                client_sock.settimeout(timeout)
                client_sock.connect(str(self.sock_path))
            except Exception:
                if client_sock:
                    client_sock.close()
                client_sock = None

        if client_sock is None and self.port_path.exists():
            try:
                port = int(self.port_path.read_text().strip())
                client_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                client_sock.settimeout(timeout)
                client_sock.connect(("127.0.0.1", port))
            except Exception as e:
                if client_sock:
                    client_sock.close()
                raise DaemonError(f"Failed to connect to daemon TCP port: {e}") from e

        if client_sock is None:
            raise DaemonError("Aegis daemon is not reachable (neither socket nor port available)")

        try:
            request = DaemonRequest(
                request_id=f"req_{uuid.uuid4().hex[:8]}",
                command=command,
                payload=payload or {},
            )
            data = (json.dumps(request.model_dump()) + "\n").encode("utf-8")
            client_sock.sendall(data)

            chunks = []
            while True:
                chunk = client_sock.recv(4096)
                if not chunk:
                    break
                chunks.append(chunk)
                if b"\n" in chunk:
                    break

            raw = b"".join(chunks).decode("utf-8")
            if not raw.strip():
                raise DaemonError("Received empty response from daemon")

            res_dict = json.loads(raw)
            return DaemonResponse.model_validate(res_dict)

        except socket.error as e:
            raise DaemonError(f"Socket communication error with daemon: {e}") from e
        except json.JSONDecodeError as e:
            raise DaemonError(f"Malformed JSON response from daemon: {e}") from e
        finally:
            client_sock.close()
