from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Set, Tuple

import pandas as pd
import plotly.graph_objects as go

import bibtexparser
import subprocess
from bibtexparser.bwriter import BibTexWriter
from bibtexparser.bibdatabase import BibDatabase

def write_bibtex(entries, output_path):
    db = BibDatabase()
    db.entries = entries

    writer = BibTexWriter()
    writer.indent = "    "   # optional, makes it readable
    writer.order_entries_by = None  # keep current order

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(writer.write(db))

def load_bibtex_as_dicts(path):
    with open(path, "r", encoding="utf-8") as f:
        bib_database = bibtexparser.load(f)

    # Each entry is already a dict
    return bib_database.entries

def explode_df_by_sep(i_df, col: str, sep: str):
    i_df = (
    i_df
    .assign(**{ 
        col: i_df[col]
        .str.split(sep)
    })
    .explode(col))

    i_df[col] = i_df[col].str.strip()
    return i_df

def excel_col_to_index(col: str) -> int:
    """Convert Excel column letters (e.g., 'A', 'R', 'BN') to 0-based index."""
    col = col.strip().upper()
    n = 0
    for ch in col:
        if not ("A" <= ch <= "Z"):
            raise ValueError(f"Invalid Excel column: {col}")
        n = n * 26 + (ord(ch) - ord("A") + 1)
    return n - 1


def split_tokens_commas_only(cell) -> List[str]:
    """Split ONLY on commas; preserve '/' inside tokens; strip outer whitespace; drop empties."""
    if cell is None or (isinstance(cell, float) and pd.isna(cell)):
        return []
    s = str(cell).strip()
    if not s:
        return []
    return [tok.strip() for tok in s.split(",") if tok.strip()]


def display_slashes_as_commas(token: str) -> str:
    """Display-only transformation: '/' → ', ' (token identity remains unchanged)."""
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


# ---------- Table 1: Engagement Citation tokens (col R) -> NEW KEYs (col A) ----------

def build_counts_and_mapping_tokens(
    df: pd.DataFrame, idx_key: int, idx_citations: int
) -> Tuple[Counter, Dict[str, Set[str]]]:
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


def make_latex_table_full_width_engagement(
    token_to_keys: Dict[str, Set[str]],
    definition_placeholder: str = "definition written here",
    caption: str | None = None,
    label: str | None = None,
) -> str:
    tokens = sorted(token_to_keys.keys())

    lines: List[str] = []
    lines.append(r"\begin{table*}[t]")
    lines.append(r"\centering")
    lines.append(r"\setlength{\tabcolsep}{6pt}")
    lines.append(r"\renewcommand{\arraystretch}{1.15}")
    lines.append(
        r"\begin{tabular*}{\textwidth}{@{\extracolsep{\fill}} "
        r"p{0.26\textwidth} p{0.34\textwidth} p{0.36\textwidth} @{} }"
    )
    lines.append(r"\hline")
    lines.append(
        r"\textbf{Citation for Engagement} & "
        r"\textbf{Engagement definition} & "
        r"\textbf{Papers in Corpus} \\"
    )
    lines.append(r"\hline")

    for tok in tokens:
        tok_disp = display_slashes_as_commas(tok)
        keys_str = ", ".join(sorted(token_to_keys[tok]))
        lines.append(
            f"{latex_escape(tok_disp)} & "
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


# ---------- Table 2: Emotion Model Citation (col U) -> NEW KEYs (col A), with Emotion Model (col T) ----------

def build_mapping_emotion_model(
    df: pd.DataFrame, idx_key: int, idx_model: int, idx_model_cit: int
) -> Tuple[Dict[str, Set[str]], Dict[str, Set[str]]]:
    """
    Returns:
      cit_to_keys:  Emotion Model Citation (U) -> set of NEW KEYs (A)
      cit_to_models: Emotion Model Citation (U) -> set of Emotion Models (T)
    """
    cit_to_keys: Dict[str, Set[str]] = defaultdict(set)
    cit_to_models: Dict[str, Set[str]] = defaultdict(set)

    keys = df.iloc[:, idx_key]
    models = df.iloc[:, idx_model]
    model_cits = df.iloc[:, idx_model_cit]

    for key, model, mc in zip(keys, models, model_cits):
        if pd.isna(mc) or str(mc).strip() == "":
            continue
        mc_str = str(mc).strip()

        if not pd.isna(key):
            key_str = str(key).strip()
            if key_str:
                cit_to_keys[mc_str].add(key_str)

        if not pd.isna(model):
            model_str = str(model).strip()
            if model_str:
                cit_to_models[mc_str].add(model_str)

    return cit_to_keys, cit_to_models


def make_latex_table_full_width_emotion_model(
    cit_to_keys: Dict[str, Set[str]],
    cit_to_models: Dict[str, Set[str]],
    caption: str | None = None,
    label: str | None = None,
) -> str:
    citations = sorted(cit_to_keys.keys())

    lines: List[str] = []
    lines.append(r"\begin{table*}[t]")
    lines.append(r"\centering")
    lines.append(r"\setlength{\tabcolsep}{6pt}")
    lines.append(r"\renewcommand{\arraystretch}{1.15}")
    lines.append(
        r"\begin{tabular*}{\textwidth}{@{\extracolsep{\fill}} "
        r"p{0.30\textwidth} p{0.32\textwidth} p{0.34\textwidth} @{} }"
    )
    lines.append(r"\hline")
    lines.append(
        r"\textbf{Emotion Model Citation} & "
        r"\textbf{Emotion Model} & "
        r"\textbf{Citing Papers} \\"
    )
    lines.append(r"\hline")

    for cit in citations:
        keys_str = ", ".join(sorted(cit_to_keys.get(cit, set())))
        models_set = cit_to_models.get(cit, set())
        # If multiple models appear for the same citation, keep them (unique) and join.
        models_str = " | ".join(sorted(models_set)) if models_set else ""
        lines.append(
            f"{latex_escape(cit)} & {latex_escape(models_str)} & {latex_escape(keys_str)} \\\\"
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
        description="Create two LaTeX tables from an Excel sheet (filtered to BN=='corpus'): engagement citations (col R) and emotion model citations (col U)."
    )
    parser.add_argument("excel_path", help="Path to Excel file (.xlsx, .xlsm, etc.)")
    parser.add_argument("sheet_name", help="Sheet name to read")
    parser.add_argument(
        "--out-engagement",
        default="engagement_table.tex",
        help="Output .tex file for engagement table (default: engagement_table.tex)",
    )
    parser.add_argument(
        "--out-emotion-model",
        default="emotion_model_table.tex",
        help="Output .tex file for emotion model table (default: emotion_model_table.tex)",
    )
    parser.add_argument("--caption-engagement", default=None, help="Optional caption for engagement table")
    parser.add_argument("--label-engagement", default=None, help="Optional label for engagement table")
    parser.add_argument("--caption-emotion-model", default=None, help="Optional caption for emotion model table")
    parser.add_argument("--label-emotion-model", default=None, help="Optional label for emotion model table")
    parser.add_argument(
        "--print-counts",
        action="store_true",
        help="Append token counts as LaTeX comments to the engagement output file.",
    )
    args = parser.parse_args()

    excel_path = Path(args.excel_path)
    if not excel_path.exists():
        raise FileNotFoundError(f"Excel file not found: {excel_path}")

    # Headers in row 2 => header index 1 (0-based)
    df = pd.read_excel(excel_path, sheet_name=args.sheet_name, header=1)
    # Strip of whitespaces of the column names
    df.columns = df.columns.str.strip()

    needed_columns = ["NEW KEY", "Engagement Citation", "Exclude Decision", "Emotion Model", "Emotion Model Citation"]

    for col in needed_columns:
        if col not in df.columns:
            print(f"####### Required column {col} does not exist in the excel sheet. #######")

    # STRICT filter: include ONLY rows where BN is exactly 'corpus'
    corpus = df[df['Exclude Decision'].str.strip() == 'corpus'].copy()
    print(corpus.shape)

    bib_entries = load_bibtex_as_dicts("_MAINbib.bib")

    # Normalize corpus DOI column for matching (trim, lowercase)
    corpus_doi_norm = corpus["DOI"].astype(str).str.strip().str.lower()
    
    # Match BibTeX entries to corpus rows and update "BibTex Key"
    for entry in bib_entries:
        entry_id = entry.get("ID")
        if not entry_id:
            continue
        
        # Build list of DOI candidates from entry (doi, longdoi, shortdoi)
        doi_candidates = [entry.get(k, "").strip().lower() for k in ("doi", "longdoi", "shortdoi") if entry.get(k)]
        if not doi_candidates:
            continue
        
        # Find matching rows in corpus
        matches = corpus_doi_norm.isin(doi_candidates)
        if matches.any():
            # Update the "BibTex Key" column for matched rows
            corpus.loc[matches, "BibTex Key"] = entry_id
    
    print(f"\nMatched {corpus['BibTex Key'].notna().sum()} rows with BibTeX entries")
    print(corpus[corpus['BibTex Key'].notna()][["NEW KEY", "DOI", "BibTex Key"]])

    # Write results to Excel
    output_path = Path(args.excel_path).stem + "_matched.xlsx"
    corpus.to_excel(output_path, sheet_name=args.sheet_name, index=False)
    print(f"\nResults written to {output_path}")
    
    return 0

if __name__ == "__main__":
    raise SystemExit(main())