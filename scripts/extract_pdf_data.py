#!/usr/bin/env python3
"""
Extract structured data from AI Basketball/Soccer Analysis Dashboard PDFs.
Saves raw extractions to data/raw/ with product_line, source_file, page, and content.
If PDFs are image-based (no tables/text), writes a placeholder and relies on
clean_and_model to produce schema-consistent mock data for the dashboard.
"""
from __future__ import annotations

import csv
import os
import re
from pathlib import Path

try:
    import pdfplumber
except ImportError:
    pdfplumber = None

# Project root: directory containing this script -> parent
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
RAW_DIR = PROJECT_ROOT / "data" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

# PDF filename patterns: 1-AI篮球... / 2-AI足球... / 足篮球复盘
BASKETBALL_PATTERN = re.compile(r"1-.*[Bb]asketball.*\.pdf$", re.I)
SOCCER_PATTERN = re.compile(r"2-.*[Ss]occer.*\.pdf$", re.I)
RECAP_PATTERN = re.compile(r"足篮球.*复盘\.pdf$", re.I)


def detect_product_line(filename: str) -> str | None:
    if BASKETBALL_PATTERN.search(filename):
        return "篮球"
    if SOCCER_PATTERN.search(filename):
        return "足球"
    if RECAP_PATTERN.search(filename):
        return "复盘"
    return None


def extract_from_pdf(pdf_path: Path) -> list[dict]:
    """Extract tables and text from one PDF. Return list of row dicts."""
    rows: list[dict] = []
    if not pdfplumber:
        return rows
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages, start=1):
                # Tables
                tables = page.extract_tables()
                if tables:
                    for ti, table in enumerate(tables):
                        for ri, row in enumerate(table or []):
                            cells = [str(c).strip() if c is not None else "" for c in (row if isinstance(row, (list, tuple)) else [row])]
                            if any(cells):
                                rows.append({
                                    "product_line": "",  # filled by caller
                                    "source_file": pdf_path.name,
                                    "page": page_num,
                                    "table_index": ti,
                                    "row_index": ri,
                                    "content_type": "table",
                                    "cell_values": "|".join(cells),
                                })
                # Text
                text = page.extract_text()
                if text and text.strip():
                    for line in text.strip().splitlines():
                        line = line.strip()
                        if not line:
                            continue
                        # Heuristic: "label 123" or "指标：16"
                        rows.append({
                            "product_line": "",
                            "source_file": pdf_path.name,
                            "page": page_num,
                            "table_index": -1,
                            "row_index": -1,
                            "content_type": "text",
                            "cell_values": line[:500],
                        })
    except Exception as e:
        rows.append({
            "product_line": "",
            "source_file": pdf_path.name,
            "page": 0,
            "table_index": -1,
            "row_index": -1,
            "content_type": "error",
            "cell_values": str(e),
        })
    return rows


def main() -> None:
    os.chdir(PROJECT_ROOT)
    pdf_files: list[tuple[Path, str]] = []
    for f in PROJECT_ROOT.iterdir():
        if f.suffix.lower() != ".pdf" or not f.is_file():
            continue
        product = detect_product_line(f.name)
        if product:
            pdf_files.append((f, product))

    all_rows: list[dict] = []
    for pdf_path, product_line in pdf_files:
        extracted = extract_from_pdf(pdf_path)
        for r in extracted:
            r["product_line"] = product_line
            all_rows.append(r)

    # Save raw extraction
    raw_csv = RAW_DIR / "extracted_raw.csv"
    fieldnames = ["product_line", "source_file", "page", "table_index", "row_index", "content_type", "cell_values"]
    with open(raw_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(all_rows)

    # If no content extracted (image-based PDFs), write a marker row so clean script knows to use mock data
    if not any(r["content_type"] in ("table", "text") for r in all_rows):
        marker_csv = RAW_DIR / "extraction_marker.txt"
        marker_csv.write_text("no_tables_or_text_extracted", encoding="utf-8")

    print(f"Extraction done: {len(all_rows)} rows from {len(pdf_files)} PDFs -> {raw_csv}")


if __name__ == "__main__":
    main()
