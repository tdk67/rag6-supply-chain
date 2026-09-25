"""Cryptographic hashing utilities for document and data integrity."""

import hashlib
from pathlib import Path
from typing import Union


def calculate_sha256(content: Union[str, bytes]) -> str:
    """Calculate the SHA-256 hash of a string or bytes.

    Args:
        content: String or bytes to hash.

    Returns:
        Hexadecimal SHA-256 digest string.
    """
    if isinstance(content, str):
        content = content.encode("utf-8")
    return hashlib.sha256(content).hexdigest()


def calculate_file_sha256(file_path: Union[str, Path], chunk_size: int = 65536) -> str:
    """Calculate the SHA-256 hash of a file on disk.

    Args:
        file_path: Path to the target file.
        chunk_size: Block size in bytes for reading.

    Returns:
        Hexadecimal SHA-256 digest string.
    """
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(f"File not found for hashing: {file_path}")

    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            hasher.update(chunk)
    return hasher.hexdigest()
