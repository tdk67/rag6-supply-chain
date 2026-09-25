"""Unit tests for CSV and Excel tabular document parser and chunking."""

from pathlib import Path
from ingestion.parser import parse_csv, parse_excel, parse_document
from ingestion.chunker import chunk_document


def test_csv_parser_and_chunker(tmp_path: Path):
    csv_file = tmp_path / "test_pricing.csv"
    csv_file.write_text(
        "sku,component,supplier,cost_eur\n"
        "SKU-GPU-1,NVIDIA H200,NVIDIA,30000.0\n"
        "SKU-GPU-2,AMD MI300X,AMD,18500.0\n"
        "SKU-OPT-1,800G OSFP,Broadcom,950.0\n",
        encoding="utf-8",
    )

    parsed = parse_csv(csv_file)
    assert parsed.classification == "TABLE_DATA"
    assert parsed.total_pages >= 1
    assert "NVIDIA H200" in parsed.pages[0].text
    assert parsed.metadata.get("row_count") == 3

    chunks = chunk_document(parsed)
    assert len(chunks) >= 1
    assert chunks[0].metadata.get("classification") == "TABLE_DATA"


def test_excel_parser(tmp_path: Path):
    import pandas as pd

    excel_file = tmp_path / "test_bom.xlsx"
    df1 = pd.DataFrame({"part": ["Pump-A", "Pump-B"], "flow_lpm": [120, 150]})
    df2 = pd.DataFrame({"rack": ["R01", "R02"], "power_kw": [48, 64]})

    with pd.ExcelWriter(excel_file) as writer:
        df1.to_excel(writer, sheet_name="Pumps", index=False)
        df2.to_excel(writer, sheet_name="Racks", index=False)

    parsed = parse_excel(excel_file)
    assert parsed.classification == "TABLE_DATA"
    assert parsed.total_pages == 2
    assert "Pumps" in parsed.pages[0].text
    assert "Racks" in parsed.pages[1].text
