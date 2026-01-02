#!/usr/bin/env python3
"""
Filter to BN == 'corpus', parse comma-separated Engagement Citation tokens (keeping '/' inside tokens),
map tokens -> NEW KEYs, and output a full-width LaTeX table.

Key requirement:
- Tokens are separated ONLY by commas.
- If a token contains '/', it remains a single token (NOT split).
- In the LaTeX output, '/' is displayed as ', ' (so "A/B" prints as "A, B"),
  but it is still treated as one token for counting and key-mapping.

No stemming or extra tokenization beyond comma-splitting. Token text is otherwise preserved
(except for display-time replacement of '/' with ', ').
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Set, Tuple

import pandas as pd


def excel_col_to_index(col: str) -> int:
    """Convert Excel column letters (e.g., 'A', 'S', 'BN') to 0-based index."""
    col = col.strip().upper()
    n = 0
    for ch in col:
        if not ("A" <= ch <= "Z"):
            raise ValueError(f"Invalid Excel column: {col}")
        n = n * 26 + (ord(ch) - ord("A") + 1)
    return n - 1


def split_tokens_commas_only(cell) -> List[str]:
    """
    Split ONLY on commas. Preserve token text (including any '/').
    Strip outer whitespace; drop empty tokens.
    """
    if cell is None or (isinstance(cell, float) and pd.isna(cell)):
        return []
    s = str(cell)
    if not s.strip():
        return []

    out: List[str] = []
    for tok in s.split(","):
        tok = tok.strip()
        if tok:
            out.append(tok)
    return out


def display_slashes_as_commas(token: str) -> str:
    """
    For LaTeX display only: replace '/' with ', ' in the final string.
    Does NOT affect counting or token identity.
    """
    return token.replace("/", ", ")


def latex_escape(s: str) -> str:
    """Escape LaTeX special characters."""
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


def build_counts_and_mapping(
    df: pd.DataFrame, idx_key: int, idx_citations: int
) -> Tuple[Counter, Dict[str, Set[str]]]:
    """
    Returns:
      counts: token -> count (each occurrence counted)
      token_to_keys: token -> set of NEW KEYs appearing in rows containing token
    """
    counts: Counter = Counter()
    token_to_keys: Dict[str, Set[str]] = defaultdict(set)

    keys = df.iloc[:, idx_key]
    citations = df.iloc[:, idx_citations]

    for key, cell in zip(keys, citations):
        if pd.isna(key):
            continue
        key_str = str(key).strip()
        if not key_str:
            continue

        for tok in split_tokens_commas_only(cell):
            counts[tok] += 1
            token_to_keys[tok].add(key_str)

    return counts, token_to_keys


def make_latex_table_full_width(
    token_to_keys: Dict[str, Set[str]],
    definition_placeholder: str = "definition written here",
    caption: str | None = None,
    label: str | None = None,
) -> str:
    """
    Full-width LaTeX table using table* + tabular* spanning \\textwidth.
    """
    tokens = sorted(token_to_keys.keys())

    lines: List[str] = []
    lines.append(r"\begin{table*}[t]")
    lines.append(r"\centering")
    lines.append(r"\setlength{\tabcolsep}{6pt}")
    lines.append(r"\renewcommand{\arraystretch}{1.15}")
    lines.append(
        r"\begin{tabular*}{\textwidth}{@{\extracolsep{\fill}} p{0.26\textwidth} p{0.34\textwidth} p{0.36\textwidth} @{} }"
    )
    lines.append(r"\hline")
    lines.append(
        r"\textbf{Citation for Engagement} & "
        r"\textbf{Engagement definition} & "
        r"\textbf{Papers in Corpus} \\"
    )
    lines.append(r"\hline")

    for tok in tokens:
        tok_display = display_slashes_as_commas(tok)  # display-only transform
        keys_sorted = sorted(token_to_keys[tok])
        keys_str = ", ".join(keys_sorted)

        lines.append(
            f"{latex_escape(tok_display)} & "
            f"{latex_escape(definition_placeholder)} & "
            f"{latex_escape(keys_str)} \\\\"
        )

    lines.append(r"\hline")
    lines.append(r"\end{tabular*}")
    if caption:
        lines.append(rf"\caption{{{latex_escape(caption)}}}")
    if label:
        lines.append(rf"\label{{{latex_escape(label)}}}")
    lines.append(r"\end{table*}")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create a full-width LaTeX table mapping Engagement Citation tokens (col S) to NEW KEYs (col A), filtered to BN == 'corpus'. Tokens split only on commas; '/' preserved as part of token but displayed as ', '."
    )
    parser.add_argument("excel_path", help="Path to Excel file (.xlsx, .xlsm, etc.)")
    parser.add_argument("sheet_name", help="Sheet name to read")
    parser.add_argument("--out", default=None, help="Output .tex file path (default: print to stdout)")
    parser.add_argument("--caption", default=None, help="Optional LaTeX caption")
    parser.add_argument("--label", default=None, help="Optional LaTeX label (e.g., tab:engagement)")
    parser.add_argument(
        "--print-counts",
        action="store_true",
        help="Also print token counts as LaTeX comments (lines starting with %).",
    )
    args = parser.parse_args()

    excel_path = Path(args.excel_path)
    if not excel_path.exists():
        raise FileNotFoundError(f"Excel file not found: {excel_path}")

    # Headers in row 2 => header index 1 (0-based)
    df = pd.read_excel(excel_path, sheet_name=args.sheet_name, header=1)

    # Column indices by Excel letter (A, S, BN)
    idx_key = excel_col_to_index("A")
    idx_citations = excel_col_to_index("S")
    idx_bn = excel_col_to_index("BN")

    need = max(idx_key, idx_citations, idx_bn) + 1
    if df.shape[1] < need:
        raise IndexError(f"Sheet has {df.shape[1]} columns; need at least {need} to access A/S/BN.")

    # STRICT filter: include ONLY rows where BN is exactly 'corpus'
    bn = df.iloc[:, idx_bn]
    mask = bn.astype(str).str.strip().str.lower().eq("corpus")
    df = df.loc[mask].copy()

    counts, token_to_keys = build_counts_and_mapping(df, idx_key=idx_key, idx_citations=idx_citations)

    latex = make_latex_table_full_width(
        token_to_keys=token_to_keys,
        definition_placeholder="definition written here",
        caption=args.caption,
        label=args.label,
    )

    if args.out:
        Path(args.out).write_text(latex, encoding="utf-8")
    else:
        print(latex)

    if args.print_counts:
        out_lines = ["% Token counts (for reference):"]
        for tok in sorted(counts.keys()):
            # Show counts using the same display transform for easier auditing in LaTeX
            out_lines.append(f"% {latex_escape(display_slashes_as_commas(tok))}: {counts[tok]}")
        extra = "\n".join(out_lines)

        if args.out:
            with Path(args.out).open("a", encoding="utf-8") as f:
                f.write("\n\n" + extra + "\n")
        else:
            print("\n" + extra)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())