#!/usr/bin/env python3
"""
Stacked bar chart: tokenized "Domain Application" by "Year" (corpus only), with styling.

Requirements implemented:
1) Filter: include ONLY rows where "Exclude Decision" contains "corpus" (case-insensitive).
2) Tokenize "Domain Application" by commas (strip whitespace).
3) Bars are stacked per year with highest-count domains at the bottom and lowest at the top
   (ties alphabetically), based on SINGLE-TOKEN rows.
4) Styling: every *unit* count is separated by a thin white line (i.e., drawn as 1-high slices).
5) Multi-token rows (e.g., two tokens that would be 0.5 each) are grouped as ONE unit total:
   - drawn as a single "unit block" split internally into equal fractional slices (e.g., 0.5/0.5),
   - no white separator inside the block,
   - the entire grouped unit block(s) sit at the TOP of the bar for that year.
6) Years missing from the "Year" column still appear (0-height bars).

Coloring:
- Provide your HEX colors in DOMAIN_HEX_COLORS for the listed categories.
- Any token not found uses DEFAULT_COLOR.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Patch


# ----------------------------
# PLACEHOLDER: put your HEX colors here
# ----------------------------
DOMAIN_HEX_COLORS: Dict[str, str] = {
    "Climate": "#86BD72",            # 86BD72: replace
    "Public Health": "#E9C475",      # TODO: replace
    "Medicine": "#8ED0AE",           # TODO: replace
    "Social/Civic": "#85B0CF",       # TODO: replace
    "Industry": "#D06E88",           # TODO: replace
    "Science Education": "#B7A1DA",  # TODO: replace
    "Journalism": "#6983C6",         # TODO: replace
    "Various": "#C689D0",            # TODO: replace
    "Agnostic": "#918F9D",           # TODO: replace
}
DEFAULT_COLOR = "#9e9e9e"  # used for any token not present in DOMAIN_HEX_COLORS


def coerce_year_to_int(x) -> Optional[int]:
    """Coerce common Excel year values (e.g., 2020, 2020.0, '2020.0') to int; else None."""
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return None
    s = str(x).strip()
    if not s:
        return None
    try:
        f = float(s)
        i = int(f)
        if abs(f - i) < 1e-9 and 1000 <= i <= 9999:
            return i
    except Exception:
        return None
    return None


def split_comma_tokens(cell) -> List[str]:
    """Split ONLY on commas, strip whitespace, drop empty tokens."""
    if cell is None or (isinstance(cell, float) and pd.isna(cell)):
        return []
    s = str(cell).strip()
    if not s:
        return []
    return [tok.strip() for tok in s.split(",") if tok.strip()]


def get_color(domain: str) -> str:
    return DOMAIN_HEX_COLORS.get(domain, DEFAULT_COLOR)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Stacked bar chart of tokenized 'Domain Application' by 'Year' (corpus only), with unit white separators and grouped multi-token rows."
    )
    parser.add_argument("excel_path", help="Path to the Excel file (.xlsx, .xlsm, etc.)")
    parser.add_argument("sheet_name", help="Name of the sheet to read")
    parser.add_argument("--year_col", default="Year", help="Column title for year (default: 'Year')")
    parser.add_argument(
        "--domain_col",
        default="Domain Application",
        help="Column title for domain application (default: 'Domain Application')",
    )
    parser.add_argument(
        "--filter_col",
        default="Exclude Decision",
        help="Column title for corpus filter (default: 'Exclude Decision')",
    )
    parser.add_argument(
        "--out",
        default="domainbyyear.pdf",
        help="Output image file path (default: domainbyyear.pdf)",
    )
    parser.add_argument("--title", default="Domain Application by Year", help="Chart title")
    parser.add_argument(
        "--unit_linewidth",
        type=float,
        default=0.6,
        help="Line width for white unit separators (default: 0.6)",
    )
    args = parser.parse_args()

    excel_path = Path(args.excel_path)
    if not excel_path.exists():
        raise FileNotFoundError(f"Excel file not found: {excel_path}")

    # Headers in row 2 => header index 1 (0-based)
    df = pd.read_excel(excel_path, sheet_name=args.sheet_name, header=1)

    for required in (args.year_col, args.domain_col, args.filter_col):
        if required not in df.columns:
            raise KeyError(f"Required column '{required}' not found. Found: {list(df.columns)}")

    # 1) Filter: Exclude Decision contains "corpus" (case-insensitive)
    mask = (
        df[args.filter_col]
        .astype(str)
        .str.lower()
        .str.contains("corpus", na=False)
    )
    df = df.loc[mask].copy()

    # Clean years
    df["__year__"] = df[args.year_col].apply(coerce_year_to_int)
    df = df.dropna(subset=["__year__"]).copy()
    df["__year__"] = df["__year__"].astype(int)

    if df.empty:
        raise ValueError("No rows remain after filtering and year coercion.")

    # Split domains and build per-year structures:
    # - single_counts[year][domain] = integer count from single-token rows
    # - grouped_units[year] = list of groups; each group is list of domain tokens (length >= 2)
    single_counts: Dict[int, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    grouped_units: Dict[int, List[List[str]]] = defaultdict(list)
    all_domains: set[str] = set()

    for _, row in df.iterrows():
        year = int(row["__year__"])
        tokens = split_comma_tokens(row[args.domain_col])
        if not tokens:
            continue
        for t in tokens:
            all_domains.add(t)

        if len(tokens) == 1:
            single_counts[year][tokens[0]] += 1
        else:
            # treat this row as ONE unit, to be drawn at the top, split internally across tokens
            grouped_units[year].append(tokens)

    if not all_domains:
        raise ValueError("No domain tokens found after tokenization.")

    # Include missing years between min and max
    min_year = int(df["__year__"].min())
    max_year = int(df["__year__"].max())
    years = list(range(min_year, max_year + 1))

    # Prepare x-axis
    x = list(range(len(years)))

    # Plot
    fig, ax = plt.subplots(figsize=(max(10, 0.6 * len(years)), 6))

    # For legend: show all observed domains (alphabetical) with their assigned colors
    domains_sorted = sorted(all_domains)
    legend_handles = [Patch(facecolor=get_color(d), edgecolor="none", label=d) for d in domains_sorted]

    # 2) Per-year draw:
    #    - draw single-token contributions as 1-high slices with white edges (unit separators),
    #      stacking order by (count desc, domain asc) per year
    #    - then draw grouped multi-token "unit blocks" at top of bar for that year,
    #      with no internal white separators, but with white boundary lines around the whole block
    for i, year in enumerate(years):
        year_counts = single_counts.get(year, {})
        # domains present in this year for single-token rows
        present = [d for d, c in year_counts.items() if c > 0]

        # order bottom->top for single-token stack: high->low; ties alphabetically
        ordered = sorted(present, key=lambda d: (-year_counts[d], d))

        bottom = 0.0

        # Draw single-token units as 1-high slices
        for d in ordered:
            c = int(year_counts[d])
            if c <= 0:
                continue
            color = get_color(d)

            # draw as c slices of height 1 with thin white edge
            for _ in range(c):
                ax.bar(
                    i,
                    1.0,
                    bottom=bottom,
                    color=color,
                    edgecolor="white",
                    linewidth=args.unit_linewidth,
                )
                bottom += 1.0

        # Draw grouped multi-token units on top
        groups = grouped_units.get(year, [])
        for g in groups:
            if not g:
                continue
            n = len(g)
            # one unit total, split into n equal parts (e.g., 0.5 + 0.5)
            h = 1.0 / n

            group_bottom = bottom
            # internal slices: no white edges
            for tok in g:
                ax.bar(
                    i,
                    h,
                    bottom=bottom,
                    color=get_color(tok),
                    edgecolor="none",
                    linewidth=0.0,
                )
                bottom += h

            group_top = bottom
            # white boundary lines around the whole grouped unit
            ax.hlines([group_bottom, group_top], i - 0.4, i + 0.4, colors="white", linewidth=args.unit_linewidth)

    ax.set_xlabel("Year")
    ax.set_ylabel("Paper count (unit blocks; multi-token rows count as 1 unit)")
    ax.set_title(args.title)
    ax.set_xticks(x)
    ax.set_xticklabels([str(y) for y in years], rotation=45, ha="center")

    # Legend outside
    ax.legend(
        handles=legend_handles,
        title="Domain Application",
        bbox_to_anchor=(1.02, 1),
        loc="upper left",
        borderaxespad=0,
    )

    plt.tight_layout()

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_path, dpi=300)
    plt.close(fig)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
