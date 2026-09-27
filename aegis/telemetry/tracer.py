"""Structured telemetry and trace recording for Aegis."""

import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from aegis.logging import scrub_secrets
from aegis.models import TaskResult, VerificationReport


class TelemetryTracer:
    """Records sanitized operational execution traces to .aegis/traces/<session_id>.json."""

    def __init__(self, repo_root: Path, traces_dir_rel: str = ".aegis/traces", enabled: bool = True):
        self.repo_root = repo_root.resolve()
        self.traces_dir = (self.repo_root / traces_dir_rel).resolve()
        self.enabled = enabled

    def _ensure_dir(self) -> None:
        if self.enabled:
            self.traces_dir.mkdir(parents=True, exist_ok=True)

    def write_trace(
        self,
        session_id: str,
        task: str,
        model_name: str,
        turns: int,
        tool_audit: list[dict[str, Any]],
        task_result: TaskResult,
        token_usage: Optional[dict[str, int]] = None,
    ) -> Optional[Path]:
        """Saves a structured trace document sanitized of secrets."""
        if not self.enabled:
            return None

        self._ensure_dir()
        trace_file = self.traces_dir / f"{session_id}.json"

        trace_data = {
            "session_id": session_id,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "task": task,
            "model": model_name,
            "turns": turns,
            "status": task_result.status.value,
            "duration_seconds": round(task_result.duration_seconds, 2),
            "changed_files": task_result.changed_files,
            "tool_calls_count": len(tool_audit),
            "tool_calls": tool_audit,
            "verification": task_result.verification.model_dump() if task_result.verification else None,
            "token_usage": token_usage or {},
            "error": task_result.error,
        }

        # Double check scrubbing of any accidental secret values
        raw_json = json.dumps(trace_data, indent=2)
        clean_json = scrub_secrets(raw_json)

        try:
            trace_file.write_text(clean_json, encoding="utf-8")
            return trace_file
        except Exception:
            return None
