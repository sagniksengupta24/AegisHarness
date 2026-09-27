"""Episodic memory manager for persisting repository lessons with corruption resilience."""

import json
import os
import shutil
import time
import uuid
from pathlib import Path
from typing import List, Optional

from aegis.logging import get_logger
from aegis.models import MemoryLesson

logger = get_logger("aegis.memory")


class EpisodicMemoryManager:
    """Manages persistent repository memory in .aegis/memory.json."""

    def __init__(self, repo_root: Path, memory_path: str = ".aegis/memory.json", max_entries: int = 200):
        self.repo_root = repo_root.resolve()
        self.memory_file = (self.repo_root / memory_path).resolve()
        self.max_entries = max_entries

    def _ensure_dir(self) -> None:
        self.memory_file.parent.mkdir(parents=True, exist_ok=True)

    def load_lessons(self) -> list[MemoryLesson]:
        """Loads and validates stored lessons. Handles corrupted files gracefully."""
        if not self.memory_file.exists():
            return []

        try:
            raw_text = self.memory_file.read_text(encoding="utf-8")
            if not raw_text.strip():
                return []
            data = json.loads(raw_text)
            if not isinstance(data, list):
                raise ValueError("Expected list of memory objects")

            valid_lessons: list[MemoryLesson] = []
            for item in data:
                try:
                    valid_lessons.append(MemoryLesson.model_validate(item))
                except Exception as ve:
                    logger.warning(f"Skipping malformed memory entry: {ve}")
            return valid_lessons

        except Exception as e:
            logger.warning(f"Corrupted memory file detected at '{self.memory_file}': {e}. Creating backup.")
            try:
                bak_path = self.memory_file.with_suffix(".json.corrupt.bak")
                shutil.copy2(self.memory_file, bak_path)
            except Exception:
                pass
            return []

    def save_lesson(
        self,
        lesson: str,
        context: Optional[list[str]] = None,
        files: Optional[list[str]] = None,
        confidence: float = 1.0,
        source: str = "session",
    ) -> MemoryLesson:
        """Adds a new validated lesson and persists to disk."""
        self._ensure_dir()
        existing = self.load_lessons()
        cleaned_lesson = lesson.strip()

        # Deduplication check: merge if identical normalized lesson exists
        norm_key = cleaned_lesson.lower()
        matched_idx = -1
        for idx, entry in enumerate(existing):
            if entry.lesson.strip().lower() == norm_key:
                matched_idx = idx
                break

        if matched_idx >= 0:
            existing_entry = existing[matched_idx]
            merged_context = sorted(list(set(existing_entry.context + (context or []))))
            merged_files = sorted(list(set(existing_entry.files + (files or []))))
            new_entry = MemoryLesson(
                id=existing_entry.id,
                lesson=cleaned_lesson,
                context=merged_context,
                source=source,
                created_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                confidence=max(existing_entry.confidence, confidence),
                files=merged_files,
            )
            existing[matched_idx] = new_entry
        else:
            new_entry = MemoryLesson(
                id=str(uuid.uuid4())[:8],
                lesson=cleaned_lesson,
                context=context or [],
                source=source,
                created_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                confidence=confidence,
                files=files or [],
            )
            existing.append(new_entry)

        # Enforce maximum entries bound
        if len(existing) > self.max_entries:
            existing = existing[-self.max_entries :]

        try:
            serialized = [item.model_dump() for item in existing]
            temp_path = self.memory_file.with_suffix(".json.tmp")
            temp_path.write_text(json.dumps(serialized, indent=2), encoding="utf-8")
            temp_path.replace(self.memory_file)
        except Exception as e:
            logger.error(f"Failed to persist memory lesson: {e}")

        return new_entry
