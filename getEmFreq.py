#!/usr/bin/env python3
"""
Create frequency bar charts (PDF) for comma-separated tokens in a chosen column,
filtered to rows where "Exclude Decision" == "corpus".

Outputs TWO PDFs:
1) Alphabetical order by token
2) Descending order by count (ties: alphabetical)

Uses the same counting logic as the prior script (split on commas, strip whitespace).
"""

from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path
from typing import List, Tuple

import pandas as pd
import matplotlib.pyplot as plt


def split_comma_tokens(cell) -> List[str]:
    """Split only on commas; strip outer whitespace; drop empty tokens."""
    if cell is None or (isinstance(cell, float) and pd.isna(cell)):
        return []
    s = str(cell).strip()
    if not s:
        return []
    return [tok.strip() for tok in s.split(",") if tok.strip()]


def count_tokens(series: pd.Series) -> Counter:
    """Count comma-separated tokens from a pandas Series."""
    counter: Counter = Counter()
    for cell in series:
        for tok in split_comma_tokens(cell):
            counter[tok] += 1
    return counter


def plot_bar_pdf(items: List[Tuple[str, int]], title: str, out_pdf: Path) -> None:
    """
    Plot a bar chart from (token, count) items and save to PDF.

    Notes:
    - Uses matplotlib defaults (no manual color specification).
    - Figure width scales with number of tokens for readability.
    """
    if not items:
        raise ValueError("No items to plot.")

    tokens = [t for t, _ in items]
    counts = [c for _, c in items]

    # Scale width with number of categories (cap within a sensible range)
    fig_w = max(10, min(0.35 * len(tokens), 40))
    fig_h = 6

    plt.figure(figsize=(fig_w, fig_h))
    plt.bar(tokens, counts)
    plt.title(title)
    plt.xlabel("Token")
    plt.ylabel("Count")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()

    out_pdf.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_pdf, format="pdf")
    plt.close()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create two frequency bar chart PDFs (alphabetical and descending) for comma-separated tokens, filtered to Exclude Decision == 'corpus'."
    )
    parser.add_argument("excel_path", help="Path to the Excel file (.xlsx, .xlsm, etc.)")
    parser.add_argument("sheet_name", help="Name of the sheet to read")
    parser.add_argument("column_name", help="Name of the column to analyse (tokenized by commas)")
    parser.add_argument(
        "--out_alpha",
        default="token_frequencies_alpha.pdf",
        help="Output PDF for alphabetical chart (default: token_frequencies_alpha.pdf)",
    )
    parser.add_argument(
        "--out_desc",
        default="token_frequencies_desc.pdf",
        help="Output PDF for descending chart (default: token_frequencies_desc.pdf)",
    )
    parser.add_argument(
        "--title_prefix",
        default="Token Frequencies",
        help="Prefix for chart titles (default: 'Token Frequencies')",
    )
    args = parser.parse_args()

    excel_path = Path(args.excel_path)
    if not excel_path.exists():
        raise FileNotFoundError(f"Excel file not found: {excel_path}")

    # Header is in row 2 => zero-based header index = 1
    df = pd.read_excel(excel_path, sheet_name=args.sheet_name, header=1)

    required_cols = ["Exclude Decision", args.column_name]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise KeyError(f"Missing required column(s): {missing}. Found columns: {list(df.columns)}")

    # Strict corpus filter
    mask = df["Exclude Decision"].astype(str).str.strip().str.lower().eq("corpus")
    df_corpus = df.loc[mask].copy()

    counts = count_tokens(df_corpus[args.column_name])

    # Prepare orderings
    items_alpha = sorted(counts.items(), key=lambda kv: kv[0])
    items_desc = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))

    # Plot and save PDFs
    plot_bar_pdf(
        items_alpha,
        title=f"{args.title_prefix} (Alphabetical)",
        out_pdf=Path(args.out_alpha),
    )
    plot_bar_pdf(
        items_desc,
        title=f"{args.title_prefix} (Highest to Lowest)",
        out_pdf=Path(args.out_desc),
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
