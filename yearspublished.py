#!/usr/bin/env python3
"""
Count comma-separated tokens from a named column in a named Excel sheet (CORPUS ONLY),
then save a histogram.

Change:
- Filters the dataframe to ONLY rows where "Exclude Decision" is exactly "corpus"
  (case-insensitive, surrounding whitespace ignored).
"""

from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path
from typing import Dict, List, Tuple

import pandas as pd
import matplotlib.pyplot as plt


def count_comma_tokens(series: pd.Series) -> Counter:
    """
    Count comma-separated tokens from a pandas Series.

    Rules:
    - Split only on commas.
    - Preserve original token text (case/punctuation unchanged).
    - Do not do stemming or further tokenization.
    - Ignore empty tokens produced by blanks like ", ,".
    - Strip only leading/trailing whitespace around each token.
    """
    counter: Counter = Counter()

    for cell in series.dropna().astype(str):
        if not cell.strip():
            continue
        for tok in cell.split(","):
            tok = tok.strip()
            if tok:
                counter[tok] += 1

    return counter


def token_to_year(token: str) -> int | None:
    """
    Try to interpret a token as a 4-digit year.
    Accepts common Excel artifacts like '2020.0' or '2020.00'.
    Returns an int year or None.
    """
    t = token.strip()

    if t.isdigit() and len(t) == 4:
        return int(t)

    if t.endswith(".0"):
        t2 = t[:-2]
        if t2.isdigit() and len(t2) == 4:
            return int(t2)

    try:
        f = float(t)
        i = int(f)
        if abs(f - i) < 1e-9 and 1000 <= i <= 9999:
            return i
    except Exception:
        return None

    return None


def save_histogram_from_counts(counts: Counter, out_path: Path) -> None:
    """
    Build a pandas Series from counts and save a histogram-like bar chart.

    Behavior:
    - If at least one token parses as a year, the chart will include every year between
      min(year) and max(year), inserting 0 counts for missing years so they still appear.
    - Otherwise, falls back to plotting tokens as categorical labels.
    """
    year_counts: Dict[int, int] = {}
    other_items: List[Tuple[str, int]] = []

    for tok, cnt in counts.items():
        y = token_to_year(tok)
        if y is not None:
            year_counts[y] = year_counts.get(y, 0) + cnt
        else:
            other_items.append((tok, cnt))

    if year_counts:
        min_year = min(year_counts)
        max_year = max(year_counts)
        all_years = list(range(min_year, max_year + 1))

        s = pd.Series([year_counts.get(y, 0) for y in all_years], index=[str(y) for y in all_years])

        plt.figure(figsize=(max(10, 0.35 * len(s)), 6))
        ax = s.plot(kind="bar")
        ax.set_xlabel("Year")
        ax.set_ylabel("# Papers")
        ax.set_title("Papers Published by Year")
        plt.xticks(rotation=45, ha="center")
        plt.tight_layout()

    else:
        s = pd.Series({k: v for k, v in sorted(counts.items(), key=lambda kv: kv[0])})

        plt.figure(figsize=(max(10, 0.35 * len(s)), 6))
        ax = s.plot(kind="bar")
        ax.set_xlabel("Token")
        ax.set_ylabel("Count")
        ax.set_title("Token Counts Histogram")
        plt.xticks(rotation=45, ha="right")
        plt.tight_layout()

    out_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_path, dpi=300)
    plt.close()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Grouped counts of comma-separated tokens in a chosen column from a named Excel sheet (corpus only), plus saved histogram (with missing years shown as 0)."
    )
    parser.add_argument("excel_path", help="Path to the Excel file (.xlsx, .xlsm, etc.)")
    parser.add_argument("sheet_name", help="Name of the sheet to read")
    parser.add_argument("column_name", help="Name of the column to analyse")
    parser.add_argument(
        "--hist_out",
        default="yearspublished.pdf",
        help="Output path for the saved histogram image (default: yearspublished.pdf)",
    )
    parser.add_argument(
        "--filter_col",
        default="Exclude Decision",
        help='Column used to filter rows (default: "Exclude Decision")',
    )
    parser.add_argument(
        "--filter_value",
        default="corpus",
        help='Value required in the filter column (default: "corpus")',
    )
    args = parser.parse_args()

    excel_path = Path(args.excel_path)
    if not excel_path.exists():
        raise FileNotFoundError(f"Excel file not found: {excel_path}")

    df = pd.read_excel(excel_path, sheet_name=args.sheet_name, header=1)

    # --- NEW: filter to corpus only ---
    if args.filter_col not in df.columns:
        raise KeyError(
            f"Filter column '{args.filter_col}' not found in sheet '{args.sheet_name}'. "
            f"Found columns: {list(df.columns)}"
        )

    mask = (
        df[args.filter_col]
        .astype(str)
        .str.strip()
        .str.lower()
        .eq(str(args.filter_value).strip().lower())
    )
    df = df.loc[mask].copy()
    # -------------------------------

    col_name = args.column_name
    if col_name not in df.columns:
        raise KeyError(
            f"Column '{col_name}' not found in sheet '{args.sheet_name}'. "
            f"Found columns: {list(df.columns)}"
        )

    counts = count_comma_tokens(df[col_name])

    for token in sorted(counts.keys()):
        print(f"{token}: {counts[token]}")

    save_histogram_from_counts(counts, Path(args.hist_out))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
