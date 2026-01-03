#!/usr/bin/env python3
"""
Stacked bar chart: tokenized "Domain Application" by "Year" (corpus only), with styling.

PDF export styling updates:
- Save with *no* surrounding whitespace: bbox_inches="tight", pad_inches=0
- Only left and bottom spines (axes lines) are shown; top/right spines removed
- No tick marks (optional, but common for a clean axis-only look); keep labels
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
import matplotlib.pyplot as plt


# ----------------------------
# Domain colors
# ----------------------------
DOMAIN_HEX_COLORS: Dict[str, str] = {
    "Climate": "#86BD72",
    "Public Health": "#E9C475",
    "Medicine": "#8ED0AE",
    "Social/Civic": "#85B0CF",
    "Industry": "#D06E88",
    "Science Education": "#B7A1DA",
    "Journalism": "#6983C6",
    "Various": "#C689D0",
    "Agnostic": "#918F9D",
}
DEFAULT_COLOR = "#9e9e9e"


def coerce_year_to_int(x) -> Optional[int]:
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
    parser.add_argument("--domain_col", default="Domain Application", help="Domain column (default: 'Domain Application')")
    parser.add_argument("--filter_col", default="Exclude Decision", help="Filter column (default: 'Exclude Decision')")
    parser.add_argument("--out", default="domainbyyear.pdf", help="Output PDF path (default: domainbyyear.pdf)")
    parser.add_argument("--title", default="Papers Published by Domain and Year", help="Chart title")
    parser.add_argument("--unit_linewidth", type=float, default=0.6, help="White separator line width")
    args = parser.parse_args()

    excel_path = Path(args.excel_path)
    if not excel_path.exists():
        raise FileNotFoundError(f"Excel file not found: {excel_path}")

    df = pd.read_excel(excel_path, sheet_name=args.sheet_name, header=1)

    for required in (args.year_col, args.domain_col, args.filter_col):
        if required not in df.columns:
            raise KeyError(f"Required column '{required}' not found. Found: {list(df.columns)}")

    # Filter: Exclude Decision contains "corpus" (case-insensitive)
    mask = df[args.filter_col].astype(str).str.lower().str.contains("corpus", na=False)
    df = df.loc[mask].copy()

    # Clean years
    df["__year__"] = df[args.year_col].apply(coerce_year_to_int)
    df = df.dropna(subset=["__year__"]).copy()
    df["__year__"] = df["__year__"].astype(int)

    if df.empty:
        raise ValueError("No rows remain after filtering and year coercion.")

    single_counts: Dict[int, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    grouped_units: Dict[int, List[List[str]]] = defaultdict(list)
    all_domains: set[str] = set()

    for _, row in df.iterrows():
        year = int(row["__year__"])
        tokens = split_comma_tokens(row[args.domain_col])
        if not tokens:
            continue
        all_domains.update(tokens)

        if len(tokens) == 1:
            single_counts[year][tokens[0]] += 1
        else:
            grouped_units[year].append(tokens)

    if not all_domains:
        raise ValueError("No domain tokens found after tokenization.")

    min_year = int(df["__year__"].min())
    max_year = int(df["__year__"].max())
    years = list(range(min_year, max_year + 1))

    bar_width = 0.8
    x_step = bar_width * 1.5
    half_w = bar_width / 2.0
    x = [i * x_step for i in range(len(years))]

    fig, ax = plt.subplots(figsize=(max(10, 0.5 * len(years)), 6))
    ax.set_aspect("equal", adjustable="box")

    for xi, year in enumerate(years):
        xpos = x[xi]

        year_counts = single_counts.get(year, {})
        present = [d for d, c in year_counts.items() if c > 0]
        ordered = sorted(present, key=lambda d: (-year_counts[d], d))

        bottom = 0.0

        for d in ordered:
            c = int(year_counts[d])
            if c <= 0:
                continue
            color = get_color(d)
            for _ in range(c):
                ax.bar(
                    xpos,
                    1.0,
                    bottom=bottom,
                    width=bar_width,
                    color=color,
                    edgecolor="white",
                    linewidth=args.unit_linewidth,
                    align="center",
                )
                bottom += 1.0

        for g in grouped_units.get(year, []):
            if not g:
                continue
            n = len(g)
            h = 1.0 / n

            group_bottom = bottom
            for tok in g:
                ax.bar(
                    xpos,
                    h,
                    bottom=bottom,
                    width=bar_width,
                    color=get_color(tok),
                    edgecolor="none",
                    linewidth=0.0,
                    align="center",
                )
                bottom += h

            group_top = bottom
            ax.hlines(
                [group_bottom, group_top],
                xpos - half_w,
                xpos + half_w,
                colors="white",
                linewidth=args.unit_linewidth,
            )

    ax.set_xlabel("Year")
    ax.set_ylabel("Number of Papers")
    ax.set_title(args.title)

    ax.set_xticks(x)
    ax.set_xticklabels([str(y) for y in years], rotation=45, ha="center")
    ax.set_xlim(min(x) - x_step, max(x) + x_step)

    # ---- Styling: only left/bottom axes lines, no top/right border ----
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    # Keep left/bottom spines black; ensure ticks/labels are black too
    ax.spines["left"].set_color("black")
    ax.spines["bottom"].set_color("black")
    ax.tick_params(axis="both", colors="black")

    # Optional: remove tick marks (keeps labels). Comment out if you want tick marks.
    ax.tick_params(axis="both", which="both", length=0)

    # ---- Export: no whitespace around the figure ----
    # Avoid tight_layout (it can add padding for labels); instead use bbox_inches+pad_inches
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=300, bbox_inches="tight", pad_inches=0)
    plt.close(fig)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
