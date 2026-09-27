"""Skill detector for progressive runtime skill activation based on context."""

import fnmatch
from pathlib import Path
from typing import List, Optional, Set

from aegis.skills.schema import SkillDefinition


class SkillDetector:
    """Matches repository conditions and task context to dynamically activate skills."""

    def __init__(self, repo_root: Path):
        self.repo_root = repo_root.resolve()

    def detect_active_skills(
        self,
        available_skills: list[SkillDefinition],
        task: str,
        stack: str = "generic",
        touched_files: Optional[list[str]] = None,
        max_active: int = 3,
    ) -> list[SkillDefinition]:
        """Progressively activates skills whose triggers match current execution context."""
        active: list[SkillDefinition] = []
        task_lower = task.lower()
        stack_lower = stack.lower()

        # Gather relevant file paths
        candidate_files = set(touched_files or [])
        # Sample repo root files for trigger matching
        try:
            for item in self.repo_root.iterdir():
                candidate_files.add(item.name)
        except Exception:
            pass

        for skill in available_skills:
            if not skill.enabled:
                continue

            triggers = skill.triggers
            matched = False

            # 1. Stack match
            if triggers.stacks:
                for s in triggers.stacks:
                    if s.lower() in stack_lower:
                        matched = True
                        break

            # 2. Keyword match in task
            if not matched and triggers.keywords:
                for kw in triggers.keywords:
                    if kw.lower() in task_lower:
                        matched = True
                        break

            # 3. File pattern match
            if not matched and triggers.files:
                for pat in triggers.files:
                    for cf in candidate_files:
                        if fnmatch.fnmatch(cf, pat):
                            matched = True
                            break
                    if matched:
                        break

            if matched and skill not in active:
                active.append(skill)
                if len(active) >= max_active:
                    break

        return active

    def format_skills_instructions(self, skills: list[SkillDefinition]) -> str:
        """Formats activated skills instructions into bounded prompt guidance."""
        if not skills:
            return ""

        sections = ["=== [ACTIVATED REPOSITORY SKILLS] ==="]
        for s in skills:
            sections.append(f"### Skill: {s.name} ({s.description})")
            sections.append(s.instructions.strip())
            sections.append("")
        sections.append("=====================================\n")
        return "\n".join(sections)
