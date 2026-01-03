#!/usr/bin/env python3
"""
Count comma-separated tokens from a named column in a named Excel sheet, but ONLY for rows
where "Exclude Decision" == "corpus", and report affiliated NEW KEYs.

Steps:
1) Open an Excel file
2) Read a specific sheet by name
3) Use row 2 as the header (ignore row 1)
4) Filter to rows with 'corpus' written under column "Exclude Decision" (strict match)
5) Extract the target column (argument: column_name)
6) Split by commas and count unique tokens (no stemming/tokenization)
7) For each unique token, list the NEW KEY identifiers from the same rows
8) Print alphabetically: "token (count) : NEW KEY1, NEW KEY2, ..."
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Set, Tuple

import pandas as pd


def split_comma_tokens(cell) -> List[str]:
    """
    Split only on commas; preserve token text; strip outer whitespace; drop empties.
    """
    if cell is None or (isinstance(cell, float) and pd.isna(cell)):
        return []
    s = str(cell)
    if not s.strip():
        return []
    return [tok.strip() for tok in s.split(",") if tok.strip()]


def count_tokens_and_map_keys(series: pd.Series, keys: pd.Series) -> Tuple[Counter, Dict[str, Set[str]]]:
    """
    Count comma-separated tokens from `series` and map each token -> set of NEW KEYs from `keys`.
    """
    counter: Counter = Counter()
    token_to_keys: Dict[str, Set[str]] = defaultdict(set)

    for cell, key in zip(series, keys):
        if pd.isna(cell) or pd.isna(key):
            continue

        key_str = str(key).strip()
        if not key_str:
            continue

        for tok in split_comma_tokens(cell):
            counter[tok] += 1
            token_to_keys[tok].add(key_str)

    return counter, token_to_keys


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Count comma-separated tokens in a column (corpus rows only) and list affiliated NEW KEYs."
    )
    parser.add_argument("excel_path", help="Path to the Excel file (.xlsx, .xlsm, etc.)")
    parser.add_argument("sheet_name", help="Name of the sheet to read")
    parser.add_argument("column_name", help="Name of the column to analyse (tokenized by commas)")
    args = parser.parse_args()

    excel_path = Path(args.excel_path)
    if not excel_path.exists():
        raise FileNotFoundError(f"Excel file not found: {excel_path}")

    # Header is in row 2 => zero-based header index = 1
    df = pd.read_excel(excel_path, sheet_name=args.sheet_name, header=1)

    # Required columns
    required_cols = ["Exclude Decision", "NEW KEY", args.column_name]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise KeyError(f"Missing required column(s): {missing}. Found columns: {list(df.columns)}")

    # 1) STRICT filter: ONLY rows where Exclude Decision == 'corpus' (case-insensitive, trimmed)
    mask = df["Exclude Decision"].astype(str).str.strip().str.lower().eq("corpus")
    df = df.loc[mask].copy()

    # 2) Count tokens and map to NEW KEYs
    counts, token_to_keys = count_tokens_and_map_keys(df[args.column_name], df["NEW KEY"])

    # 3) Print alphabetically: token (count) : NEW KEY list
    for token in sorted(counts.keys()):
        keys_sorted = sorted(token_to_keys.get(token, set()))
        keys_str = ", ".join(keys_sorted)
        print(f"{token} ({counts[token]}) : {keys_str}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
