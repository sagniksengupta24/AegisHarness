"""Skill loader for reading and validating skill manifests from .aegis/skills/."""

from pathlib import Path
from typing import List, Optional
import yaml

from aegis.logging import get_logger
from aegis.skills.schema import SkillDefinition

logger = get_logger("aegis.skills")


class SkillLoader:
    """Discovers and parses skill manifests from repository skills directory."""

    def __init__(self, repo_root: Path, skills_dir_rel: str = ".aegis/skills"):
        self.repo_root = repo_root.resolve()
        self.skills_dir = (self.repo_root / skills_dir_rel).resolve()

    def load_all_skills(self) -> list[SkillDefinition]:
        """Loads all valid YAML skill files from skills directory."""
        if not self.skills_dir.exists() or not self.skills_dir.is_dir():
            return []

        skills = []
        for file in sorted(self.skills_dir.glob("*.yaml")) + sorted(self.skills_dir.glob("*.yml")):
            try:
                content = file.read_text(encoding="utf-8")
                raw = yaml.safe_load(content)
                if isinstance(raw, dict):
                    skill = SkillDefinition.model_validate(raw)
                    if skill.enabled:
                        skills.append(skill)
            except Exception as e:
                logger.warning(f"Failed to load skill manifest '{file.name}': {e}")

        return skills
