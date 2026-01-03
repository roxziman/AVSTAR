#!/usr/bin/env python3
"""
Count comma-separated tokens from a named column in a named Excel sheet, but ONLY for rows
where "Exclude Decision" == "corpus", and print the total token count at the end.

Steps:
1) Open an Excel file
2) Read a specific sheet by name
3) Use row 2 as the header (ignore row 1)
4) Filter to rows with 'corpus' written under column "Exclude Decision" (strict match)
5) Extract the target column (argument: column_name)
6) Split by commas and count unique tokens (no stemming/tokenization)
7) Print alphabetically: "token: count"
8) Print total count of all tokens at the end
"""

from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

import pandas as pd


def count_comma_tokens(series: pd.Series) -> Counter:
    """
    Count comma-separated tokens from a pandas Series.

    Rules:
    - Split only on commas.
    - Preserve original token text (case/punctuation unchanged).
    - Do not do stemming or further tokenization.
    - Ignore empty tokens produced by blanks like ", ,".
    - Strip only leading/trailing whitespace around each token (to avoid "sad" vs " sad").
    """
    counter: Counter = Counter()

    # Drop NaN; convert to string for safety
    for cell in series.dropna().astype(str):
        if not cell.strip():
            continue

        for tok in cell.split(","):
            tok = tok.strip()
            if tok:
                counter[tok] += 1

    return counter


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Grouped counts of comma-separated tokens in a chosen column (corpus rows only) from a named Excel sheet."
    )
    parser.add_argument("excel_path", help="Path to the Excel file (.xlsx, .xlsm, etc.)")
    parser.add_argument("sheet_name", help="Name of the sheet to read")
    parser.add_argument("column_name", help="Name of the column to analyse")
    args = parser.parse_args()

    excel_path = Path(args.excel_path)
    if not excel_path.exists():
        raise FileNotFoundError(f"Excel file not found: {excel_path}")

    # Header is in row 2 => zero-based header index = 1
    df = pd.read_excel(excel_path, sheet_name=args.sheet_name, header=1)

    # Required columns
    if "Exclude Decision" not in df.columns:
        raise KeyError(
            "Column 'Exclude Decision' not found. "
            f"Found columns: {list(df.columns)}"
        )

    col_name = args.column_name
    if col_name not in df.columns:
        raise KeyError(
            f"Column '{col_name}' not found in sheet '{args.sheet_name}'. "
            f"Found columns: {list(df.columns)}"
        )

    # 1) STRICT filter: ONLY rows where Exclude Decision == 'corpus' (case-insensitive, trimmed)
    mask = df["Exclude Decision"].astype(str).str.strip().str.lower().eq("corpus")
    df = df.loc[mask].copy()

    counts = count_comma_tokens(df[col_name])

    # 2) Print alphabetical list
    for token in sorted(counts.keys()):
        print(f"{token}: {counts[token]}")

    # 3) Print total count (sum of all token occurrences)
    total_count = sum(counts.values())
    print(f"TOTAL: {total_count}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
