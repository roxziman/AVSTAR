#!/usr/bin/env python3
"""
Build a token-to-token co-occurrence matrix from two comma-separated columns and plot a Plotly heatmap.

Update:
- If the Y axis corresponds to "Emotional Valence" (exact match), it is ordered TOP->BOTTOM as:
  Positive–Negative, Positive, Positive–Neutral, Neutral, Neutral–Negative, Negative
  (unknown tokens appended afterward alphabetically).
- If the X axis corresponds to "Emotional Valence", the same ordering is applied LEFT->RIGHT.

Other features:
- Filters to rows where "Exclude Decision" contains "corpus"
- Stepwise monochrome colorscale from white (0) to mid-blue (max)
- Colorbar shown as stepwise integer counts with labels centered on each step
- Outputs interactive HTML heatmap (and optional CSV)
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import List, Tuple

import pandas as pd
import plotly.graph_objects as go


VALENCE_ORDER_TOP_TO_BOTTOM = [
    "Positive–Negative",
    "Positive",
    "Positive–Neutral",
    "Neutral",
    "Neutral–Negative",
    "Negative",
]

WHITE_RGB = (255, 255, 255)
BLUE_RGB = (59, 130, 246)  # ~"#3b82f6"


def split_comma_tokens(cell) -> List[str]:
    """Split on commas, strip whitespace, drop empty tokens."""
    if cell is None or (isinstance(cell, float) and pd.isna(cell)):
        return []
    s = str(cell).strip()
    if not s:
        return []
    return [tok.strip() for tok in s.split(",") if tok.strip()]


def order_valence_tokens(tokens: List[str]) -> List[str]:
    """Apply the requested valence ordering; append unknown tokens alphabetically."""
    token_set = list(dict.fromkeys(tokens))  # stable unique
    known = [t for t in VALENCE_ORDER_TOP_TO_BOTTOM if t in token_set]
    unknown = sorted([t for t in token_set if t not in VALENCE_ORDER_TOP_TO_BOTTOM])
    return known + unknown


def lerp(a: int, b: int, t: float) -> int:
    return int(round(a + (b - a) * t))


def rgb_to_str(rgb: Tuple[int, int, int]) -> str:
    return f"rgb({rgb[0]},{rgb[1]},{rgb[2]})"


def make_stepwise_colorscale(max_count: int) -> List[List[float | str]]:
    """
    Create a discrete (stepwise) colorscale for integer counts 0..max_count.

    Assumes zmin=0 and zmax=max_count+1 so each integer i occupies [i, i+1).
    """
    if max_count < 0:
        max_count = 0
    denom = max_count if max_count > 0 else 1

    colors = []
    for i in range(max_count + 1):
        t = i / denom
        c = (
            lerp(WHITE_RGB[0], BLUE_RGB[0], t),
            lerp(WHITE_RGB[1], BLUE_RGB[1], t),
            lerp(WHITE_RGB[2], BLUE_RGB[2], t),
        )
        colors.append(rgb_to_str(c))

    zmax = max_count + 1
    scale: List[List[float | str]] = []
    for i, col in enumerate(colors):
        left = i / zmax
        right = (i + 1) / zmax
        scale.append([left, col])
        scale.append([right, col])
    return scale


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Tokenize two columns and plot a co-occurrence heatmap (corpus rows only) with ordered Emotional Valence axis and a stepwise white→blue scale."
    )
    parser.add_argument("excel_path", help="Path to Excel file (.xlsx, .xlsm, etc.)")
    parser.add_argument("sheet_name", help="Sheet name to read")
    parser.add_argument("col_x", help="First column name (heatmap x-axis tokens)")
    parser.add_argument("col_y", help="Second column name (heatmap y-axis tokens)")
    parser.add_argument(
        "--out_html",
        default="cooccurrence_heatmap.html",
        help="Output HTML for the interactive heatmap (default: cooccurrence_heatmap.html)",
    )
    parser.add_argument("--out_csv", default=None, help="Optional output CSV for the co-occurrence matrix")
    parser.add_argument(
        "--min_count",
        type=int,
        default=1,
        help="Hide tokens whose total co-occurrence sum is below this (default: 1)",
    )
    parser.add_argument(
        "--max_tokens",
        type=int,
        default=60,
        help="If >0, keep only the top-N tokens on each axis by total frequency (default: 60). Set 0 for no limit.",
    )
    parser.add_argument("--title", default=None, help="Optional plot title")
    args = parser.parse_args()

    excel_path = Path(args.excel_path)
    if not excel_path.exists():
        raise FileNotFoundError(f"Excel file not found: {excel_path}")

    df = pd.read_excel(excel_path, sheet_name=args.sheet_name, header=1)

    required_cols = ["Exclude Decision", args.col_x, args.col_y]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise KeyError(f"Missing required column(s): {missing}. Found columns: {list(df.columns)}")

    mask = df["Exclude Decision"].astype(str).str.lower().str.contains("corpus", na=False)
    df = df.loc[mask].copy()

    co = pd.DataFrame(dtype=int)

    for _, row in df.iterrows():
        xs = split_comma_tokens(row[args.col_x])
        ys = split_comma_tokens(row[args.col_y])
        if not xs or not ys:
            continue

        if co.empty:
            co = pd.DataFrame(0, index=sorted(set(ys)), columns=sorted(set(xs)), dtype=int)

        new_rows = [t for t in ys if t not in co.index]
        if new_rows:
            co = pd.concat([co, pd.DataFrame(0, index=new_rows, columns=co.columns, dtype=int)], axis=0)

        new_cols = [t for t in xs if t not in co.columns]
        if new_cols:
            co = pd.concat([co, pd.DataFrame(0, index=co.index, columns=new_cols, dtype=int)], axis=1)

        for y in ys:
            for x in xs:
                co.at[y, x] += 1

    if co.empty or co.values.sum() == 0:
        raise ValueError("No co-occurrences found after filtering and tokenization.")

    if args.min_count > 1:
        row_sums = co.sum(axis=1)
        col_sums = co.sum(axis=0)
        co = co.loc[row_sums[row_sums >= args.min_count].index, col_sums[col_sums >= args.min_count].index]

    if args.max_tokens and args.max_tokens > 0:
        top_rows = co.sum(axis=1).sort_values(ascending=False).head(args.max_tokens).index
        top_cols = co.sum(axis=0).sort_values(ascending=False).head(args.max_tokens).index
        co = co.loc[top_rows, top_cols]

    # Default ordering by totals (descending)
    row_order = list(co.sum(axis=1).sort_values(ascending=False).index)
    col_order = list(co.sum(axis=0).sort_values(ascending=False).index)

    # Apply Emotional Valence ordering
    if args.col_y == "Emotional Valence":
        row_order = order_valence_tokens(row_order)
    if args.col_x == "Emotional Valence":
        col_order = order_valence_tokens(col_order)

    co = co.loc[row_order, col_order]

    max_count = int(co.to_numpy().max())
    colorscale = make_stepwise_colorscale(max_count)

    # Stepwise colorbar ticks centered in each step [i, i+1)
    zmin = 0
    zmax = max_count + 1
    tickvals = [i + 0.5 for i in range(0, max_count + 1)]
    ticktext = [str(i) for i in range(0, max_count + 1)]

    title = args.title or f"Co-occurrence heatmap: {args.col_y} (rows) vs {args.col_x} (cols)"

    fig = go.Figure(
        data=go.Heatmap(
            z=co.to_numpy(),
            x=co.columns.tolist(),
            y=co.index.tolist(),
            zmin=zmin,
            zmax=zmax,
            colorscale=colorscale,
            colorbar=dict(
                title="Count",
                tickmode="array",
                tickvals=tickvals,
                ticktext=ticktext,
                ticks="outside",
                # ticklen=4,
                # thickness=16,
            ),
            hovertemplate=(
                f"{args.col_y}: %{{y}}<br>"
                f"{args.col_x}: %{{x}}<br>"
                "Count: %{z}<extra></extra>"
            ),
        )
    )

    # For Plotly heatmaps, the first y category is drawn at the bottom by default.
    # To make Positive–Negative appear at the TOP, reverse the y-axis.
    if args.col_y == "Emotional Valence":
        fig.update_yaxes(autorange="reversed")

    fig.update_layout(
        title=title,
        xaxis_title=args.col_x,
        yaxis_title=args.col_y,
        margin=dict(l=80, r=80, t=70, b=80),
    )

    out_html = Path(args.out_html)
    out_html.parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(str(out_html), include_plotlyjs="cdn", full_html=True)

    if args.out_csv:
        out_csv = Path(args.out_csv)
        out_csv.parent.mkdir(parents=True, exist_ok=True)
        co.to_csv(out_csv, encoding="utf-8")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
