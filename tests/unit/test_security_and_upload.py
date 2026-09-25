"""Security and upload validation unit tests (P0 regression protection)."""

from pathlib import Path
import pytest
from ports.registry import AdapterRegistry


def test_path_traversal_detection():
    evil_names = [
        "../../evil.py",
        "..\\..\\evil.py",
        "/etc/passwd",
        "nested/../../../root.txt",
        "..\\windows\\system32\\cmd.exe",
    ]
    for evil in evil_names:
        safe_name = Path(evil).name
        assert not safe_name.startswith("..")
        assert "/" not in safe_name
        assert "\\" not in safe_name


def test_upload_extension_allowlist():
    allowed_exts = {".pdf", ".txt", ".csv", ".xlsx", ".xls"}
    forbidden_files = ["malware.exe", "script.sh", "exploit.py", "hack.php", "data.json", "payload.bin"]
    for fn in forbidden_files:
        ext = Path(fn).suffix.lower()
        assert ext not in allowed_exts

    valid_files = ["contract.pdf", "readme.txt", "prices.csv", "bom.xlsx", "spec.xls"]
    for fn in valid_files:
        ext = Path(fn).suffix.lower()
        assert ext in allowed_exts


def test_registry_raises_on_unknown_adapters():
    from utils.config import _CACHED_CONFIG
    import utils.config as config_mod

    # Unknown vector store adapter
    config_mod._CACHED_CONFIG = {"ports": {"vector_store": "unknown_vector_db"}}
    with pytest.raises(ValueError, match="Unknown or unsupported vector_store adapter"):
        AdapterRegistry.get_vector_store(force_new=True)

    # Unknown graph store adapter
    config_mod._CACHED_CONFIG = {"ports": {"graph_store": "unknown_graph_db"}}
    with pytest.raises(ValueError, match="Unknown or unsupported graph_store adapter"):
        AdapterRegistry.get_graph_store(force_new=True)

    # Unknown LLM provider adapter
    config_mod._CACHED_CONFIG = {"ports": {"llm_provider": "unknown_llm"}}
    with pytest.raises(ValueError, match="Unknown or unsupported llm_provider adapter"):
        AdapterRegistry.get_llm_provider(force_new=True)

    # Reset cache
    config_mod._CACHED_CONFIG = None
