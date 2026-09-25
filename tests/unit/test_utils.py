"""Unit tests for utility functions (hashing, config, prompt loader)."""

from pathlib import Path
from utils.hashing import calculate_sha256
from utils.config import load_config, get_project_root, resolve_path
from utils.prompt_loader import get_prompt


def test_calculate_sha256():
    h1 = calculate_sha256("test-content")
    h2 = calculate_sha256("test-content")
    assert h1 == h2
    assert len(h1) == 64


def test_load_config():
    cfg = load_config()
    assert "app" in cfg
    assert "llm" in cfg
    assert "embedding" in cfg
    assert cfg["app"]["name"] == "Aethelgard Infra-GraphRAG"


def test_resolve_path():
    root = get_project_root()
    p = resolve_path("data")
    assert p.is_absolute()
    assert str(root) in str(p)


def test_prompt_loader():
    prompt = get_prompt("text_to_sql.txt", {"question": "What is the cost?"})
    assert "What is the cost?" in prompt
    assert "SQLite" in prompt


def test_file_hashing_and_logging():
    from utils.hashing import calculate_file_sha256
    from utils.logging_setup import setup_logger
    import logging

    h = calculate_file_sha256("config.json")
    assert len(h) == 64

    logger = setup_logger("test_logger", level=logging.DEBUG)
    assert logger.name == "test_logger"
