#!/usr/bin/env python3
"""
Interactive stacked bar chart (saved as HTML) with tooltips showing paper titles.

What it does:
- Reads an Excel sheet (headers in row 2 -> header=1).
- Filters to rows where "Exclude Decision" contains "corpus" (case-insensitive).
- Tokenizes "Domain Application" by commas, stripping whitespace.
- Builds a per-year stacked bar composed of *unit squares* (height = 1 per paper):
  - Single-token rows: each paper contributes 1 full unit in that token’s color.
    Units are separated by thin white lines.
  - Multi-token rows: the paper contributes 1 unit total at the TOP of that year’s bar,
    split internally into equal fractional colored slices (e.g., 0.5/0.5 for two tokens).
    The multi-token unit is outlined in white but has no internal white separators.
- Stacking order (per year, for single-token domains only): highest count at bottom, lowest at top;
  ties alphabetically.
- Missing years between min and max are included (with empty bars).
- Hovering any colored block shows the paper "Title" (and the token).

Output:
- An interactive HTML file (default: domain_application_interactive.html)

Dependencies:
- pandas
- openpyxl (for .xlsx reading via pandas)
- plotly
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd
import plotly.graph_objects as go


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
DEFAULT_COLOR = "#9e9e9e"


def get_color(domain: str) -> str:
    return DOMAIN_HEX_COLORS.get(domain, DEFAULT_COLOR)


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


def rect_shape(x0: float, x1: float, y0: float, y1: float, fill: str, line_color: str = "white", line_width: float = 1.0):
    return dict(
        type="rect",
        xref="x",
        yref="y",
        x0=x0,
        x1=x1,
        y0=y0,
        y1=y1,
        fillcolor=fill,
        line=dict(color=line_color, width=line_width),
        layer="above",
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Interactive stacked unit-square bar chart of tokenized 'Domain Application' by 'Year' (corpus only), with tooltips showing paper titles."
    )
    parser.add_argument("excel_path", help="Path to the Excel file (.xlsx, .xlsm, etc.)")
    parser.add_argument("sheet_name", help="Name of the sheet to read")
    parser.add_argument("--year_col", default="Year", help="Column title for year (default: 'Year')")
    parser.add_argument("--domain_col", default="Domain Application", help="Column title (default: 'Domain Application')")
    parser.add_argument("--filter_col", default="Exclude Decision", help="Filter column (default: 'Exclude Decision')")
    parser.add_argument("--title_col", default="Title", help="Paper title column (default: 'Title')")
    parser.add_argument("--out", default="domain_application_interactive.html", help="Output HTML (default: domain_application_interactive.html)")
    parser.add_argument("--chart_title", default="Domain Application by Year (Corpus)", help="Chart title")
    parser.add_argument("--bar_width", type=float, default=0.8, help="Bar width in x units (default: 0.8)")
    parser.add_argument("--unit_linewidth", type=float, default=1.0, help="White separator line width (default: 1.0)")
    args = parser.parse_args()

    excel_path = Path(args.excel_path)
    if not excel_path.exists():
        raise FileNotFoundError(f"Excel file not found: {excel_path}")

    # Headers in row 2 => header index 1 (0-based)
    df = pd.read_excel(excel_path, sheet_name=args.sheet_name, header=1)

    for required in (args.year_col, args.domain_col, args.filter_col, args.title_col):
        if required not in df.columns:
            raise KeyError(f"Required column '{required}' not found. Found: {list(df.columns)}")

    # Filter to corpus (contains, case-insensitive)
    mask = (
        df[args.filter_col]
        .astype(str)
        .str.lower()
        .str.contains("corpus", na=False)
    )
    df = df.loc[mask].copy()

    # Coerce year and drop invalid
    df["__year__"] = df[args.year_col].apply(coerce_year_to_int)
    df = df.dropna(subset=["__year__"]).copy()
    df["__year__"] = df["__year__"].astype(int)

    if df.empty:
        raise ValueError("No rows remain after filtering and year coercion.")

    # Tokenize domains and keep titles
    records: List[Tuple[int, List[str], str]] = []
    all_domains = set()

    for _, r in df.iterrows():
        year = int(r["__year__"])
        tokens = split_comma_tokens(r[args.domain_col])
        if not tokens:
            continue
        title = str(r[args.title_col]).strip() if not pd.isna(r[args.title_col]) else ""
        records.append((year, tokens, title))
        for t in tokens:
            all_domains.add(t)

    if not records:
        raise ValueError("No usable records after tokenization.")

    min_year = min(y for y, _, _ in records)
    max_year = max(y for y, _, _ in records)
    years = list(range(min_year, max_year + 1))

    # Group records by year into single-token and multi-token lists
    by_year_single: Dict[int, Dict[str, List[str]]] = {y: {} for y in years}  # domain -> [titles]
    by_year_multi: Dict[int, List[Tuple[List[str], str]]] = {y: [] for y in years}  # ([tokens], title)

    for year, tokens, title in records:
        if len(tokens) == 1:
            d = tokens[0]
            by_year_single.setdefault(year, {}).setdefault(d, []).append(title)
        else:
            by_year_multi.setdefault(year, []).append((tokens, title))

    # Create plotly figure with shapes + invisible hover points
    fig = go.Figure()

    shapes = []
    hover_x = []
    hover_y = []
    hover_text = []

    half_w = args.bar_width / 2.0

    # X axis will be numeric positions 0..len(years)-1
    for xi, year in enumerate(years):
        x0 = xi - half_w
        x1 = xi + half_w

        # Determine per-year domain ordering for SINGLE-token contributions:
        # bottom->top: highest count to lowest, ties alphabetically
        single_map = by_year_single.get(year, {})
        domain_counts = [(d, len(titles)) for d, titles in single_map.items() if len(titles) > 0]
        domain_counts.sort(key=lambda dc: (-dc[1], dc[0]))

        y_bottom = 0.0

        # Draw single-token unit squares (height=1 each) with white separators
        for d, cnt in domain_counts:
            titles = single_map[d]
            # draw one unit per title (paper)
            for k in range(cnt):
                y0 = y_bottom
                y1 = y_bottom + 1.0

                shapes.append(
                    rect_shape(
                        x0=x0, x1=x1, y0=y0, y1=y1,
                        fill=get_color(d),
                        line_color="white",
                        line_width=args.unit_linewidth,
                    )
                )

                # Hover point at the center of this unit
                hover_x.append(xi)
                hover_y.append((y0 + y1) / 2.0)
                t = titles[k] if k < len(titles) else ""
                hover_text.append(f"Title: {t}<br>Domain: {d}<br>Year: {year}")

                y_bottom = y1

        # Draw multi-token "unit blocks" at TOP (each paper contributes 1 unit)
        # No internal white separators; outlined as a whole in white.
        for tokens, title in by_year_multi.get(year, []):
            if not tokens:
                continue
            n = len(tokens)
            h = 1.0 / n

            block_y0 = y_bottom
            # internal slices without separators
            for tok in tokens:
                y0 = y_bottom
                y1 = y_bottom + h

                shapes.append(
                    rect_shape(
                        x0=x0, x1=x1, y0=y0, y1=y1,
                        fill=get_color(tok),
                        line_color="rgba(0,0,0,0)",
                        line_width=0.0,
                    )
                )

                # Hover point for this slice (still shows the same paper title)
                hover_x.append(xi)
                hover_y.append((y0 + y1) / 2.0)
                hover_text.append(f"Title: {title}<br>Domain: {tok}<br>Year: {year}<br>(multi-domain row)")

                y_bottom = y1

            block_y1 = y_bottom
            # outline the whole block
            shapes.append(
                rect_shape(
                    x0=x0, x1=x1, y0=block_y0, y1=block_y1,
                    fill="rgba(0,0,0,0)",
                    line_color="white",
                    line_width=args.unit_linewidth,
                )
            )

    # Add invisible scatter for hover tooltips
    fig.add_trace(
        go.Scatter(
            x=hover_x,
            y=hover_y,
            mode="markers",
            marker=dict(size=12, opacity=0.0),
            hovertext=hover_text,
            hoverinfo="text",
            showlegend=False,
        )
    )

    # Axis formatting
    fig.update_layout(
        title=args.chart_title,
        xaxis=dict(
            title="Year",
            tickmode="array",
            tickvals=list(range(len(years))),
            ticktext=[str(y) for y in years],
        ),
        yaxis=dict(
            title="Paper count (unit squares; multi-domain rows count as 1 unit)",
            rangemode="tozero",
        ),
        shapes=shapes,
        margin=dict(l=60, r=260, t=70, b=70),
        hovermode="closest",
    )

    # Legend (fixed domain -> color), shown at right
    domains_sorted = sorted(all_domains)
    for d in domains_sorted:
        fig.add_trace(
            go.Scatter(
                x=[None],
                y=[None],
                mode="markers",
                marker=dict(size=10, color=get_color(d)),
                name=d,
                showlegend=True,
                hoverinfo="skip",
            )
        )

    fig.update_layout(
        legend=dict(
            title="Domain Application",
            x=1.02,
            y=1.0,
            xanchor="left",
            yanchor="top",
        )
    )

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(str(out_path), include_plotlyjs="cdn", full_html=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
