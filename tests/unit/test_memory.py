"""Unit tests for memory persistence, corruption resilience, and untrusted retrieval."""

from pathlib import Path
from aegis.memory.episodic import EpisodicMemoryManager
from aegis.memory.retrieval import MemoryRetriever
from aegis.models import MemoryLesson


def test_memory_save_and_load(tmp_path: Path):
    manager = EpisodicMemoryManager(tmp_path, memory_path=".aegis/memory.json")
    item = manager.save_lesson(
        lesson="Always pass -q to pytest",
        context=["tests", "pytest"],
        files=["tests/conftest.py"],
        confidence=0.9,
    )
    assert item.lesson == "Always pass -q to pytest"

    loaded = manager.load_lessons()
    assert len(loaded) == 1
    assert loaded[0].id == item.id
    assert loaded[0].lesson == item.lesson


def test_corrupted_memory_json_resilience(tmp_path: Path):
    mem_file = tmp_path / ".aegis" / "memory.json"
    mem_file.parent.mkdir(parents=True, exist_ok=True)
    mem_file.write_text("{corrupted json broken", encoding="utf-8")

    manager = EpisodicMemoryManager(tmp_path, memory_path=".aegis/memory.json")
    # Must not raise an exception; must return empty list and create backup
    loaded = manager.load_lessons()
    assert loaded == []
    assert (tmp_path / ".aegis" / "memory.json.corrupt.bak").exists()


def test_memory_retrieval_relevance_and_untrusted_header():
    retriever = MemoryRetriever(top_k=2)
    lessons = [
        MemoryLesson(id="1", lesson="FastAPI requires pydantic v2", context=["fastapi", "api"], created_at="2026-01-01", files=["main.py"]),
        MemoryLesson(id="2", lesson="Pytest requires conftest fixture", context=["pytest", "tests"], created_at="2026-01-01", files=["tests/conftest.py"]),
        MemoryLesson(id="3", lesson="Docker network none restricts internet", context=["docker"], created_at="2026-01-01", files=[]),
    ]

    retrieved = retriever.retrieve(lessons, query="How do I run pytest tests?")
    assert len(retrieved) > 0
    assert retrieved[0].id == "2"

    untrusted_text = retriever.format_untrusted_context(retrieved)
    assert "UNTRUSTED HISTORICAL MEMORY ADVISORY" in untrusted_text
    assert "Pytest requires conftest fixture" in untrusted_text
