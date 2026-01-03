#!/usr/bin/env python3
"""
Count comma-separated tokens from a named column (corpus rows only), print counts + total,
and generate a LaTeX table mapping each token ("Dimension") to the NEW KEYs ("Papers in Corpus")
that appear in rows containing that token.

Requirements:
- Headers are in row 2 (ignore row 1) -> read_excel(..., header=1)
- Only include rows where "Exclude Decision" == "corpus" (strict match; case-insensitive; trimmed)
- Tokenization: split ONLY on commas, strip whitespace, drop empty tokens
- Print tokens and counts, then print TOTAL
- Create LaTeX table with columns:
    Dimension | Papers in Corpus
  where Dimension rows are sorted from highest count to lowest (ties: alphabetical)
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Set, Tuple

import pandas as pd


def split_comma_tokens(cell) -> List[str]:
    """Split only on commas; strip whitespace; drop empty tokens."""
    if cell is None or (isinstance(cell, float) and pd.isna(cell)):
        return []
    s = str(cell).strip()
    if not s:
        return []
    return [tok.strip() for tok in s.split(",") if tok.strip()]


def latex_escape(s: str) -> str:
    """Escape common LaTeX special characters."""
    repl = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(repl.get(ch, ch) for ch in s)


def count_and_map_keys(tokens_series: pd.Series, key_series: pd.Series) -> Tuple[Counter, Dict[str, Set[str]]]:
    """
    Returns:
      - Counter(token -> occurrences)
      - token_to_keys: token -> set of NEW KEYs seen in rows containing token
    """
    counts: Counter = Counter()
    token_to_keys: Dict[str, Set[str]] = defaultdict(set)

    for cell, key in zip(tokens_series, key_series):
        if pd.isna(key):
            continue
        key_str = str(key).strip()
        if not key_str:
            continue

        for tok in split_comma_tokens(cell):
            counts[tok] += 1
            token_to_keys[tok].add(key_str)

    return counts, token_to_keys


def make_latex_table_dimension_to_papers(
    counts: Counter,
    token_to_keys: Dict[str, Set[str]],
    caption: str | None = None,
    label: str | None = None,
) -> str:
    """
    Build a LaTeX table:
      Dimension | Papers in Corpus
    Rows sorted by count desc, ties alphabetical.
    """
    items = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))

    lines: List[str] = []
    lines.append(r"\begin{table}[ht]")
    lines.append(r"\centering")
    lines.append(r"\begin{tabular}{p{0.35\linewidth} p{0.55\linewidth}}")
    lines.append(r"\hline")
    lines.append(r"\textbf{Dimension} & \textbf{Papers in Corpus} \\")
    lines.append(r"\hline")

    for tok, _cnt in items:
        keys_sorted = sorted(token_to_keys.get(tok, set()))
        keys_str = ", ".join(keys_sorted)
        lines.append(f"{latex_escape(tok)} & {latex_escape(keys_str)} \\\\")

    lines.append(r"\hline")
    lines.append(r"\end{tabular}")
    if caption:
        lines.append(rf"\caption{{{latex_escape(caption)}}}")
    if label:
        lines.append(rf"\label{{{latex_escape(label)}}}")
    lines.append(r"\end{table}")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Count comma-separated tokens (corpus rows only), print totals, and output a LaTeX table mapping tokens to NEW KEYs."
    )
    parser.add_argument("excel_path", help="Path to the Excel file (.xlsx, .xlsm, etc.)")
    parser.add_argument("sheet_name", help="Name of the sheet to read")
    parser.add_argument(
        "column_name",
        help="Name of the column to analyse (tokens split by commas). Used as 'Dimension' values in the LaTeX table.",
    )
    parser.add_argument(
        "--latex_out",
        default="dimension_to_papers_table.tex",
        help="Output .tex file path for the LaTeX table (default: dimension_to_papers_table.tex)",
    )
    parser.add_argument("--caption", default=None, help="Optional LaTeX caption")
    parser.add_argument("--label", default=None, help="Optional LaTeX label (e.g., tab:dimension-papers)")
    args = parser.parse_args()

    excel_path = Path(args.excel_path)
    if not excel_path.exists():
        raise FileNotFoundError(f"Excel file not found: {excel_path}")

    # Headers in row 2 => header index 1 (0-based)
    df = pd.read_excel(excel_path, sheet_name=args.sheet_name, header=1)

    # Required columns
    required = ["Exclude Decision", "NEW KEY", args.column_name]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise KeyError(f"Missing required column(s): {missing}. Found columns: {list(df.columns)}")

    # Filter: ONLY rows where Exclude Decision == 'corpus' (case-insensitive, trimmed)
    mask = df["Exclude Decision"].astype(str).str.strip().str.lower().eq("corpus")
    df = df.loc[mask].copy()

    # Count + map
    counts, token_to_keys = count_and_map_keys(df[args.column_name], df["NEW KEY"])

    # Print rows highest -> lowest (ties alphabetical)
    for tok, cnt in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])):
        print(f"{tok}: {cnt}")

    # Print TOTAL
    total_count = sum(counts.values())
    print(f"TOTAL: {total_count}")

    # LaTeX table (rows highest -> lowest)
    latex = make_latex_table_dimension_to_papers(
        counts=counts,
        token_to_keys=token_to_keys,
        caption=args.caption,
        label=args.label,
    )
    out_path = Path(args.latex_out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(latex, encoding="utf-8")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
