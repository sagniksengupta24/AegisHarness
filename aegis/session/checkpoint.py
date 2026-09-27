"""Transactional session checkpointing and surgical rollback protection."""

import json
import shutil
import subprocess
import uuid
from pathlib import Path
from typing import Any, Optional, Set

from aegis.diff.engine import compute_unified_diff
from aegis.errors import RollbackError
from aegis.logging import get_logger

logger = get_logger("aegis.session")


class SessionCheckpoint:
    """Manages transactional session boundaries, per-file backups, and surgical rollback."""

    def __init__(self, repo_root: Path, session_id: Optional[str] = None):
        self.repo_root = repo_root.resolve()
        self.session_id = session_id or str(uuid.uuid4())[:8]
        self.session_dir = self.repo_root / ".aegis" / "sessions" / self.session_id
        self.backups_dir = self.session_dir / "backups"
        
        self.touched_files: set[str] = set()    # Rel paths of files modified by Aegis
        self.created_files: set[str] = set()    # Rel paths of files newly created by Aegis
        self.pre_existing_status: dict[str, Any] = {}

        self._initialize_session()

    def _initialize_session(self) -> None:
        """Sets up session directories and captures baseline git state without modifying files."""
        self.backups_dir.mkdir(parents=True, exist_ok=True)
        meta_file = self.session_dir / "meta.json"
        
        if meta_file.exists():
            try:
                data = json.loads(meta_file.read_text(encoding="utf-8"))
                self.touched_files = set(data.get("touched_files", []))
                self.created_files = set(data.get("created_files", []))
                self.pre_existing_status = data.get("baseline", {})
                return
            except Exception:
                pass

        self.pre_existing_status = self._capture_git_baseline()
        self._save_meta()

    def _save_meta(self) -> None:
        """Persists session state and touched/created files list."""
        meta = {
            "session_id": self.session_id,
            "repo_root": str(self.repo_root),
            "baseline": self.pre_existing_status,
            "touched_files": sorted(list(self.touched_files)),
            "created_files": sorted(list(self.created_files)),
        }
        with open(self.session_dir / "meta.json", "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2)

    def _capture_git_baseline(self) -> dict[str, Any]:
        """Captures existing modified and untracked files from git if repository exists."""
        status = {"is_git": False, "modified": [], "untracked": []}
        try:
            res = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=str(self.repo_root),
                capture_output=True,
                text=True,
                timeout=5,
            )
            if res.returncode == 0:
                status["is_git"] = True
                for line in res.stdout.splitlines():
                    if len(line) >= 4:
                        code = line[:2].strip()
                        file_path = line[3:].strip()
                        if code in ("M", "MM", "AM", "A", "D"):
                            status["modified"].append(file_path)
                        elif code == "??":
                            status["untracked"].append(file_path)
        except Exception as e:
            logger.debug(f"Git baseline check failed: {e}")
        return status

    def backup_before_write(self, target_path: Path) -> None:
        """Backs up existing file before it is modified for the first time in this session."""
        rel_path = target_path.resolve().relative_to(self.repo_root)
        rel_str = str(rel_path).replace("\\", "/")

        if rel_str in self.touched_files or rel_str in self.created_files:
            return  # Already tracked in this session

        if target_path.exists() and target_path.is_file():
            backup_file = self.backups_dir / rel_path
            backup_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(target_path, backup_file)
            self.touched_files.add(rel_str)
        else:
            self.created_files.add(rel_str)
        self._save_meta()

    def rollback(self) -> None:
        """Surgically rolls back ONLY files touched or created in this session.
        
        Preserves all pre-existing user modifications and untracked files.
        """
        logger.info(f"Initiating surgical rollback for session {self.session_id}...")
        errors = []

        # 1. Delete files newly created by Aegis
        for rel_str in list(self.created_files):
            file_path = self.repo_root / rel_str
            if file_path.exists():
                try:
                    if file_path.is_file():
                        file_path.unlink()
                    elif file_path.is_dir():
                        shutil.rmtree(file_path)
                    logger.debug(f"Removed session-created file: {rel_str}")
                except Exception as e:
                    errors.append(f"Failed to remove created file {rel_str}: {e}")

        # 2. Restore modified files from their pre-session backup
        for rel_str in list(self.touched_files):
            backup_file = self.backups_dir / rel_str
            target_file = self.repo_root / rel_str
            if backup_file.exists():
                try:
                    target_file.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(backup_file, target_file)
                    logger.debug(f"Restored modified file from backup: {rel_str}")
                except Exception as e:
                    errors.append(f"Failed to restore {rel_str} from backup: {e}")

        if errors:
            raise RollbackError(f"Session rollback encountered errors: {'; '.join(errors)}")

        logger.info(f"Rollback completed successfully for session {self.session_id}.")

    def get_session_diff(self) -> str:
        """Computes unified diff for all files modified by Aegis relative to their backup."""
        diff_chunks = []

        for rel_str in sorted(self.touched_files):
            backup_file = self.backups_dir / rel_str
            current_file = self.repo_root / rel_str
            orig_text = backup_file.read_text(encoding="utf-8", errors="replace") if backup_file.exists() else ""
            curr_text = current_file.read_text(encoding="utf-8", errors="replace") if current_file.exists() else ""
            diff = compute_unified_diff(orig_text, curr_text, file_path=rel_str)
            if diff:
                diff_chunks.append(diff)

        for rel_str in sorted(self.created_files):
            current_file = self.repo_root / rel_str
            if current_file.exists() and current_file.is_file():
                curr_text = current_file.read_text(encoding="utf-8", errors="replace")
                diff = compute_unified_diff("", curr_text, file_path=rel_str)
                if diff:
                    diff_chunks.append(diff)

        return "\n".join(diff_chunks)
