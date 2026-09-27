"""Schema for Aegis dynamic runtime skills."""

from typing import List, Optional
from pydantic import BaseModel, Field


class SkillTriggers(BaseModel):
    files: list[str] = Field(default_factory=list, description="File glob patterns that trigger this skill (e.g. *.py, pyproject.toml)")
    keywords: list[str] = Field(default_factory=list, description="Task keywords that trigger this skill (e.g. test, pytest, api)")
    stacks: list[str] = Field(default_factory=list, description="Project stacks that trigger this skill (e.g. python, node)")


class SkillDefinition(BaseModel):
    name: str
    description: str
    triggers: SkillTriggers = Field(default_factory=SkillTriggers)
    instructions: str
    tools: list[str] = Field(default_factory=list)
    enabled: bool = True
