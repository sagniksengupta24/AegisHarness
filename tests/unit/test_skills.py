"""Unit tests for dynamic skills loader and progressive activation."""

from pathlib import Path
from aegis.skills.detector import SkillDetector
from aegis.skills.loader import SkillLoader
from aegis.skills.schema import SkillDefinition, SkillTriggers


def test_skill_manifest_loading(tmp_path: Path):
    skills_dir = tmp_path / ".aegis" / "skills"
    skills_dir.mkdir(parents=True, exist_ok=True)
    manifest = """
name: "pytest_rules"
description: "Rules for python testing"
triggers:
  files: ["test_*.py"]
  keywords: ["test", "pytest"]
  stacks: ["python"]
instructions: "Write clean assertions."
tools: []
enabled: true
"""
    (skills_dir / "pytest_rules.yaml").write_text(manifest, encoding="utf-8")

    loader = SkillLoader(tmp_path)
    skills = loader.load_all_skills()
    assert len(skills) == 1
    assert skills[0].name == "pytest_rules"
    assert skills[0].instructions.strip() == "Write clean assertions."


def test_progressive_skill_activation(tmp_path: Path):
    detector = SkillDetector(tmp_path)
    skill_py = SkillDefinition(
        name="python_skill",
        description="Python rules",
        triggers=SkillTriggers(stacks=["python"], keywords=["python", "pip"]),
        instructions="Python instructions",
    )
    skill_react = SkillDefinition(
        name="react_skill",
        description="React rules",
        triggers=SkillTriggers(stacks=["react"], keywords=["react", "jsx"]),
        instructions="React instructions",
    )

    # Context: python task
    active = detector.detect_active_skills(
        available_skills=[skill_py, skill_react],
        task="Add input validation to python api",
        stack="python",
    )
    assert len(active) == 1
    assert active[0].name == "python_skill"
