"""Unix domain socket and localhost TCP daemon server for background Aegis execution."""

import json
import os
import signal
import socket
import sys
import threading
import time
from pathlib import Path
from typing import Any, Optional

from aegis.config import load_config
from aegis.daemon.protocol import DaemonRequest, DaemonResponse
from aegis.errors import DaemonError
from aegis.execution.sandbox import get_executor
from aegis.logging import get_logger
from aegis.verifier.runner import VerificationRunner

logger = get_logger("aegis.daemon")


class DaemonServer:
    """IPC Server providing background daemon services via Unix socket or localhost TCP fallback."""

    def __init__(self, repo_root: Path):
        self.repo_root = repo_root.resolve()
        self.aegis_dir = self.repo_root / ".aegis"
        self.sock_path = self.aegis_dir / "daemon.sock"
        self.port_path = self.aegis_dir / "daemon.port"
        self.pid_path = self.aegis_dir / "daemon.pid"
        self.running = False
        self.server_socket: Optional[socket.socket] = None
        self.start_time = time.time()
        self.is_tcp = False
        self.active_tasks: dict[str, Any] = {}
        self._task_lock = threading.Lock()

    def _cleanup_stale_resources(self) -> None:
        """Removes existing socket, port, and pid file if previous process died."""
        if self.pid_path.exists():
            try:
                old_pid = int(self.pid_path.read_text().strip())
                os.kill(old_pid, 0)
                raise DaemonError(f"Daemon appears to already be running with PID {old_pid}")
            except (ProcessLookupError, ValueError):
                try:
                    self.pid_path.unlink()
                except Exception:
                    pass
            except PermissionError:
                raise DaemonError("Another daemon instance is running under a different user")

        if self.sock_path.exists():
            try:
                self.sock_path.unlink()
            except Exception:
                pass

        if self.port_path.exists():
            try:
                self.port_path.unlink()
            except Exception:
                pass

    def start(self, foreground: bool = False) -> None:
        """Starts the daemon listener."""
        self.aegis_dir.mkdir(parents=True, exist_ok=True)
        self._cleanup_stale_resources()

        # Write current PID
        self.pid_path.write_text(str(os.getpid()), encoding="utf-8")

        # Decide whether to use Unix socket or localhost TCP
        # macOS has ~104 byte limit on AF_UNIX paths
        sock_path_str = str(self.sock_path)
        use_unix = hasattr(socket, "AF_UNIX") and len(sock_path_str.encode("utf-8")) < 95

        server = None
        if use_unix:
            try:
                server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                server.bind(sock_path_str)
                try:
                    os.chmod(self.sock_path, 0o600)
                except Exception:
                    pass
                self.is_tcp = False
            except OSError as oe:
                logger.warning(f"Unix socket bind failed ({oe}). Falling back to localhost TCP.")
                if server:
                    server.close()
                server = None

        if server is None:
            # Localhost TCP fallback (restricted to 127.0.0.1)
            server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server.bind(("127.0.0.1", 0))
            port = server.getsockname()[1]
            self.port_path.write_text(str(port), encoding="utf-8")
            try:
                os.chmod(self.port_path, 0o600)
            except Exception:
                pass
            self.is_tcp = True
            logger.info(f"Aegis daemon using localhost TCP port {port}")

        server.listen(5)
        server.settimeout(1.0)
        self.server_socket = server
        self.running = True
        logger.info(f"Aegis daemon started (PID: {os.getpid()})")

        if threading.current_thread() is threading.main_thread():
            def _handle_term(signum, frame):
                logger.info("Termination signal received, shutting down daemon...")
                self.stop()
                sys.exit(0)

            try:
                signal.signal(signal.SIGTERM, _handle_term)
                signal.signal(signal.SIGINT, _handle_term)
            except (ValueError, AttributeError):
                pass

        try:
            while self.running:
                try:
                    conn, _ = server.accept()
                except socket.timeout:
                    continue
                except OSError:
                    break

                t = threading.Thread(target=self._handle_client, args=(conn,), daemon=True)
                t.start()
        finally:
            self._shutdown_resources()

    def _handle_client(self, conn: socket.socket) -> None:
        """Processes an incoming JSON request."""
        try:
            conn.settimeout(30.0)
            data_chunks = []
            while True:
                chunk = conn.recv(4096)
                if not chunk:
                    break
                data_chunks.append(chunk)
                if b"\n" in chunk:
                    break

            raw_bytes = b"".join(data_chunks)
            if not raw_bytes.strip():
                return

            req_dict = json.loads(raw_bytes.decode("utf-8"))
            request = DaemonRequest.model_validate(req_dict)
            response = self._dispatch_command(request)

            resp_bytes = (json.dumps(response.model_dump()) + "\n").encode("utf-8")
            conn.sendall(resp_bytes)
        except Exception as e:
            logger.error(f"Error handling client request: {e}")
            err_resp = DaemonResponse(
                request_id="unknown",
                status="ERROR",
                error=str(e),
            )
            try:
                conn.sendall((json.dumps(err_resp.model_dump()) + "\n").encode("utf-8"))
            except Exception:
                pass
        finally:
            try:
                conn.close()
            except Exception:
                pass

    def _dispatch_command(self, request: DaemonRequest) -> DaemonResponse:
        cmd = request.command.lower()

        if cmd == "ping":
            return DaemonResponse(
                request_id=request.request_id,
                status="OK",
                result={"pong": True, "server_time": time.time()},
            )

        elif cmd == "status":
            uptime = int(time.time() - self.start_time)
            return DaemonResponse(
                request_id=request.request_id,
                status="OK",
                result={
                    "pid": os.getpid(),
                    "uptime_seconds": uptime,
                    "repo_root": str(self.repo_root),
                    "transport": "tcp" if self.is_tcp else "unix_socket",
                },
            )

        elif cmd == "verify":
            config = load_config(self.repo_root)
            executor = get_executor(self.repo_root, backend=config.execution.backend)
            runner = VerificationRunner(self.repo_root, executor, config.verification)
            report = runner.run_all()
            return DaemonResponse(
                request_id=request.request_id,
                status="OK",
                result=report.model_dump(),
            )

        elif cmd == "run":
            task_str = request.payload.get("task")
            if not task_str:
                return DaemonResponse(
                    request_id=request.request_id,
                    status="ERROR",
                    error="Missing required 'task' in run request payload",
                )
            config = load_config(self.repo_root)
            model_override = request.payload.get("model")

            custom_client = getattr(self, "model_client", None)
            if custom_client is None:
                try:
                    from aegis.client import GeminiModelClient
                    custom_client = GeminiModelClient(
                        model_name=model_override or config.model.resolved_model,
                        temperature=config.model.temperature,
                    )
                except Exception as me:
                    return DaemonResponse(
                        request_id=request.request_id,
                        status="ERROR",
                        error=f"Model initialization error: {me}",
                    )

            from aegis.orchestrator import Orchestrator
            from aegis.models import AgentStatus
            orchestrator = Orchestrator(
                repo_root=self.repo_root,
                config=config,
                model_client=custom_client,
            )
            with self._task_lock:
                self.active_tasks[request.request_id] = orchestrator

            try:
                result = orchestrator.run_task(task_str)
            finally:
                with self._task_lock:
                    self.active_tasks.pop(request.request_id, None)

            return DaemonResponse(
                request_id=request.request_id,
                status="OK" if result.status == AgentStatus.COMPLETED else "FAILED",
                result=result.model_dump(),
                error=result.error,
            )

        elif cmd == "cancel":
            target_id = request.payload.get("target_id") or request.payload.get("request_id")
            with self._task_lock:
                if target_id and target_id in self.active_tasks:
                    self.active_tasks[target_id].cancel()
                    return DaemonResponse(
                        request_id=request.request_id,
                        status="OK",
                        result={"message": f"Task '{target_id}' cancellation signal sent"},
                    )
                elif not target_id and self.active_tasks:
                    for orch in self.active_tasks.values():
                        orch.cancel()
                    return DaemonResponse(
                        request_id=request.request_id,
                        status="OK",
                        result={"message": f"Cancelled {len(self.active_tasks)} active tasks"},
                    )
                else:
                    return DaemonResponse(
                        request_id=request.request_id,
                        status="ERROR",
                        error=f"No active task found matching '{target_id}'",
                    )

        elif cmd == "stop":
            def _delayed_stop():
                time.sleep(0.2)
                self.stop()
            threading.Thread(target=_delayed_stop, daemon=True).start()

            return DaemonResponse(
                request_id=request.request_id,
                status="OK",
                result={"message": "Daemon stopping"},
            )

        else:
            return DaemonResponse(
                request_id=request.request_id,
                status="ERROR",
                error=f"Unknown command '{request.command}'",
            )

    def stop(self) -> None:
        self.running = False
        self._shutdown_resources()

    def _shutdown_resources(self) -> None:
        if self.server_socket:
            try:
                self.server_socket.close()
            except Exception:
                pass
            self.server_socket = None

        if self.sock_path.exists():
            try:
                self.sock_path.unlink()
            except Exception:
                pass

        if self.port_path.exists():
            try:
                self.port_path.unlink()
            except Exception:
                pass

        if self.pid_path.exists():
            try:
                self.pid_path.unlink()
            except Exception:
                pass
        logger.info("Aegis daemon stopped and cleaned up resources.")
