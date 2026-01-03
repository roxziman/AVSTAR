#!/usr/bin/env python3
"""
Create a "DOI Fixed" column from "DOI Link" by extracting the substring starting at "10.".

Behavior:
- Opens an Excel file and a specified sheet.
- Finds the column named exactly "DOI Link".
- Creates/overwrites a new column immediately to the right of "DOI Link" titled "DOI Fixed".
- For each row:
    * If the cell contains "10.", write everything from the first occurrence of "10." to the end.
    * Otherwise, write blank.
- Writes a new Excel file (does not overwrite by default).

Notes:
- Uses openpyxl to preserve the original workbook structure better than a roundtrip via pandas.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional

from openpyxl import load_workbook


def extract_from_10(value: Optional[object]) -> str:
    if value is None:
        return ""
    s = str(value)
    idx = s.find("10.")
    if idx == -1:
        return ""
    return s[idx:].strip()


def main() -> int:
    parser = argparse.ArgumentParser(description='Create "DOI Fixed" column from "DOI Link".')
    parser.add_argument("excel_path", help="Path to input Excel file (.xlsx, .xlsm)")
    parser.add_argument("sheet_name", help="Sheet name to edit")
    parser.add_argument(
        "--out",
        default=None,
        help="Output Excel path (default: <input_stem>_doi_fixed.xlsx)",
    )
    args = parser.parse_args()

    in_path = Path(args.excel_path)
    if not in_path.exists():
        raise FileNotFoundError(f"Excel file not found: {in_path}")

    out_path = Path(args.out) if args.out else in_path.with_name(f"{in_path.stem}_doi_fixed.xlsx")

    wb = load_workbook(in_path)
    if args.sheet_name not in wb.sheetnames:
        raise KeyError(f"Sheet '{args.sheet_name}' not found. Available: {wb.sheetnames}")

    ws = wb[args.sheet_name]

    # Find "DOI Link" header (search entire sheet for robustness)
    doi_col = None
    header_row = None
    for row in ws.iter_rows():
        for cell in row:
            if cell.value == "DOI Link":
                doi_col = cell.column  # 1-based
                header_row = cell.row
                break
        if doi_col is not None:
            break

    if doi_col is None or header_row is None:
        raise KeyError('Could not find a header cell with exact value "DOI Link".')

    # Insert/overwrite the column immediately to the right
    fixed_col = doi_col + 1

    # If the existing header in fixed_col is not "DOI Fixed", we still set it.
    ws.cell(row=header_row, column=fixed_col).value = "DOI Fixed"

    # Fill values down to last used row
    last_row = ws.max_row
    for r in range(header_row + 1, last_row + 1):
        raw = ws.cell(row=r, column=doi_col).value
        ws.cell(row=r, column=fixed_col).value = extract_from_10(raw)

    wb.save(out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
