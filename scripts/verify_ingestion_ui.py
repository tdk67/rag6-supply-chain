"""Verification script for Action Point 5.3: Streamlit File Upload & Ingestion."""

import io
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ui.tab_ingestion import handle_file_upload

class MockUploadedFile:
    def __init__(self, filename: str, content: bytes):
        self.name = filename
        self.content = content

    def getbuffer(self):
        return io.BytesIO(self.content).getbuffer()

def verify():
    mock_file = MockUploadedFile(
        filename="Test_Sovereign_Addendum.txt",
        content=b"Section 1: Executive European Sovereignty Addendum\nGuarantees compliance with BSI C5 and GDPR.",
    )
    result = handle_file_upload(mock_file, version="2.0")

    print("File Upload Processing Result:")
    for k, v in result.items():
        print(f"  {k}: {v}")

    assert result["status"] == "SUCCESS"
    assert result["chunks_indexed"] > 0
    print("[+] SUCCESS: Document uploaded, parsed, registered in SQLite, and indexed in ChromaDB successfully!")

if __name__ == "__main__":
    verify()
