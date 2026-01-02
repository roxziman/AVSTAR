import json
import re
from pathlib import Path

import pandas as pd


# -----------------------------
# Config: expected header names
# -----------------------------
COL_KEY = "NEW KEY"
COL_DOMAIN = "Domain application"
COL_VIS = "Vis Type Grouped"
COL_EMO = "Specific Emotions"

COL_TITLE = "Title"
COL_AUTH = "Authors"
COL_COUNTRY = "Country"
COL_ABS = "Abstract"
COL_DOI = "DOI Link"
COL_YEAR = "Year"
COL_EXCLUDE = "Exclude Decision"

# Dataset source / Vis source / Interactivity / Animation are *by column letter*
COL_LETTER_DATASET = "AI"   # dataset source
COL_LETTER_VISSRC  = "AJ"   # visualization source
COL_LETTER_INTER   = "AF"   # interactivity
COL_LETTER_ANIM    = "AG"   # animation


# -----------------------------
# Helpers
# -----------------------------
def excel_col_to_idx(col: str) -> int:
    col = col.upper().strip()
    n = 0
    for ch in col:
        if "A" <= ch <= "Z":
            n = n * 26 + (ord(ch) - ord("A") + 1)
    return n - 1


def get_series_by_letter(df_: pd.DataFrame, letter: str) -> pd.Series:
    return df_.iloc[:, excel_col_to_idx(letter)]


def safe_str(x) -> str:
    return "" if pd.isna(x) else str(x).strip()


def split_top_level(s: str):
    res, cur, depth = [], [], 0
    for ch in s:
        if ch == "(":
            depth += 1
            cur.append(ch)
        elif ch == ")":
            depth = max(0, depth - 1)
            cur.append(ch)
        elif depth == 0 and ch in [",", ";", "\n", "\r", "\t", "|", "•"]:
            tok = "".join(cur).strip()
            if tok:
                res.append(tok)
            cur = []
        else:
            cur.append(ch)
    tok = "".join(cur).strip()
    if tok:
        res.append(tok)
    return res


def extract_terms(cell):
    """Parse emotion terms like: 'Anger (hostility), frustration; ...'"""
    if pd.isna(cell):
        return []
    s = str(cell).strip()
    if not s:
        return []
    items = split_top_level(s)
    out = []
    for it in items:
        it = it.strip()
        if not it:
            continue
        m = re.match(r"^(.*?)\((.*?)\)\s*$", it)
        if m:
            main = m.group(1).strip()
            inside = m.group(2).strip()
            if main:
                out.append(main)
            if inside:
                out.extend([x.strip() for x in split_top_level(inside) if x.strip()])
        else:
            out.append(it)
    out = [re.sub(r'^[\"\'“”]+|[\"\'“”]+$', "", x).strip() for x in out]
    seen, ded = set(), []
    for x in out:
        k = x.lower().rstrip(".")
        if x and k not in seen:
            seen.add(k)
            ded.append(x)
    return ded


def extract_multi(cell):
    """Generic multi-value split for domains, sources, etc."""
    if pd.isna(cell):
        return []
    s = str(cell).strip()
    if not s:
        return []
    parts = re.split(r"[;\n\r]+|,(?![^()]*\))", s)
    out = [p.strip() for p in parts if p.strip()]
    seen, ded = set(), []
    for x in out:
        k = x.lower().strip()
        if k not in seen:
            seen.add(k)
            ded.append(x)
    return ded


def split_vis(cell):
    if pd.isna(cell):
        return []
    return [p.strip() for p in re.split(r"[;\n\r]+|,", str(cell)) if p.strip()]


def norm(t: str) -> str:
    t = t.strip().lower()
    t = re.sub(r"[^a-z\s\-]", "", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def norm_doi_link(x) -> str:
    if pd.isna(x):
        return ""
    s = str(x).strip()
    if not s:
        return ""
    if s.lower().startswith("http"):
        return s
    s = re.sub(r"^doi:\s*", "", s, flags=re.I).strip()
    return ("https://doi.org/" + s) if s else ""


# -----------------------------
# Emotion family mapping
# -----------------------------
F_ANGER_HOST = "Anger/Hostility"
F_IRR_FRUS = "Irritation/Frustration"

FAMILIES = [
    "Interest", "Amusement", "Pride", "Joy", "Pleasure", "Love", "Awe", "Relief", "Surprise", "Nostalgia",
    "Compassion", "Sadness", "Fear", "Shame", "Guilt", "Regret", "Jealousy", "Disgust", "Contempt",
    F_IRR_FRUS, F_ANGER_HOST
]

POS_FAMS = {"Relief", "Awe", "Love", "Pleasure", "Joy", "Pride", "Amusement", "Interest"}
NEG_FAMS = {F_ANGER_HOST, F_IRR_FRUS, "Contempt", "Disgust", "Jealousy", "Regret", "Guilt", "Shame", "Fear", "Sadness", "Compassion"}

# +1 positive, 0 neutral, -1 negative
FAM_SIGN = [-1 if f in NEG_FAMS else (1 if f in POS_FAMS else 0) for f in FAMILIES]

TERM_TO_FAMILY = {
    "anger": F_ANGER_HOST, "angry": F_ANGER_HOST, "hostility": F_ANGER_HOST, "hostile": F_ANGER_HOST, "rage": F_ANGER_HOST,
    "irritation": F_IRR_FRUS, "irritated": F_IRR_FRUS, "annoyance": F_IRR_FRUS, "annoyed": F_IRR_FRUS,
    "frustration": F_IRR_FRUS, "frustrated": F_IRR_FRUS, "impatience": F_IRR_FRUS, "impatient": F_IRR_FRUS,

    "interest": "Interest", "curiosity": "Interest", "engaged": "Interest",
    "amusement": "Amusement", "laughter": "Amusement",
    "pride": "Pride",
    "joy": "Joy", "happiness": "Joy", "delight": "Joy", "excitement": "Joy",
    "pleasure": "Pleasure", "enjoyment": "Pleasure", "satisfaction": "Pleasure",
    "love": "Love", "trust": "Love",
    "awe": "Awe", "admiration": "Awe", "wonder": "Awe",
    "relief": "Relief", "calm": "Relief", "relaxed": "Relief",
    "surprise": "Surprise", "astonishment": "Surprise", "confused": "Surprise",
    "nostalgia": "Nostalgia", "longing": "Nostalgia",
    "compassion": "Compassion", "empathy": "Compassion",
    "sadness": "Sadness",
    "fear": "Fear", "anxiety": "Fear", "stress": "Fear", "worry": "Fear",
    "shame": "Shame", "embarrassment": "Shame",
    "guilt": "Guilt",
    "regret": "Regret", "disappointment": "Regret",
    "jealousy": "Jealousy", "envy": "Jealousy",
    "disgust": "Disgust",
    "contempt": "Contempt", "scorn": "Contempt", "hate": "Contempt",
}


def map_to_family(term: str):
    t = norm(term)
    if not t:
        return None
    if t in TERM_TO_FAMILY:
        return TERM_TO_FAMILY[t]
    # heuristics
    if "hostil" in t or "rage" in t or "anger" in t:
        return F_ANGER_HOST
    if "frustr" in t or "irrit" in t or "annoy" in t or "impatient" in t:
        return F_IRR_FRUS
    if "anx" in t or "stress" in t or "worr" in t:
        return "Fear"
    if "sad" in t:
        return "Sadness"
    return None


# -----------------------------
# Color scale (discrete tripolar; fixed scale)
# -----------------------------
NEG_HUE = "#6D3C7B"          # mauve
POS_HUE = "#6495ED"          # cornflower blue
NEU_HUE = "#808080"          # grey for neutral emotions
BASE_NO_PAPERS = "#FFFFFF"   # white for 0 papers


def hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def rgb_to_hex(rgb):
    return "#%02x%02x%02x" % rgb


def mix(c0, c1, t):
    r0, g0, b0 = hex_to_rgb(c0)
    r1, g1, b1 = hex_to_rgb(c1)
    return rgb_to_hex((
        int(round(r0 + (r1 - r0) * t)),
        int(round(g0 + (g1 - g0) * t)),
        int(round(b0 + (b1 - b0) * t)),
    ))


def stepwise_tripolar_colorscale(
    N: int,
    pos_hue=POS_HUE,
    neu_hue=NEU_HUE,
    neg_hue=NEG_HUE,
    base=BASE_NO_PAPERS,
    gamma: float = 1.8,   # <— smaller => more separation between steps
):
    """
    Discrete Plotly colorscale for z in [0..3N]:
      0 -> white
      1..N -> positive steps
      N+1..2N -> neutral steps
      2N+1..3N -> negative steps
    """
    N = max(int(N), 1)
    maxz = 3 * N 

    def ramp(hue: str, k: int, denom: int) -> str:
        # gamma curve makes steps visually more distinct
        t = (k / denom) ** gamma
        return mix(base, hue, t)

    def color_for_z(z: int) -> str:
        if z <= 0:
            return base
        if z <= N:
            return ramp(pos_hue, z, N)
        if z <= 2 * N:
            return ramp(neu_hue, z - N, N)
        return ramp(neg_hue, z - 2 * N, N)

    cs = []
    for z in range(0, maxz):
        p0 = z / maxz
        p1 = (z + 1) / maxz
        col = color_for_z(z)
        cs.append([p0, col])
        cs.append([p1, col])

    cs.append([1.0, color_for_z(maxz)])
    cs[0][0] = 0.0
    cs[-1][0] = 1.0
    return cs


# -----------------------------
# Build browser
# -----------------------------
def build(xlsx_path: Path, out_html: Path):
    df = pd.read_excel(xlsx_path, header=1)
    final = df[df[COL_EXCLUDE].isna()].copy()

    # letter-based columns
    ser_dataset = get_series_by_letter(final, COL_LETTER_DATASET)
    ser_vissrc = get_series_by_letter(final, COL_LETTER_VISSRC)
    ser_inter = get_series_by_letter(final, COL_LETTER_INTER)
    ser_anim = get_series_by_letter(final, COL_LETTER_ANIM)

    final["_domains"] = final[COL_DOMAIN].apply(extract_multi)
    final["_vis"] = final[COL_VIS].apply(split_vis)
    final["_families"] = final[COL_EMO].apply(lambda cell: sorted({map_to_family(t) for t in extract_terms(cell)} - {None}))
    final["_dataset"] = ser_dataset.apply(extract_multi)
    final["_vissrc"] = ser_vissrc.apply(extract_multi)
    final["_inter"] = ser_inter.apply(extract_multi)
    final["_anim"] = ser_anim.apply(extract_multi)

    paper_meta = {}
    years = []
    for _, r in final.iterrows():
        k = safe_str(r[COL_KEY])
        y_raw = safe_str(r.get(COL_YEAR, ""))
        try:
            y_num = int(float(y_raw)) if y_raw else None
        except Exception:
            y_num = None

        if y_num is not None:
            years.append(y_num)

        paper_meta[k] = {
            "title": safe_str(r.get(COL_TITLE, "")),
            "authors": safe_str(r.get(COL_AUTH, "")),
            "country": safe_str(r.get(COL_COUNTRY, "")),
            "abstract": safe_str(r.get(COL_ABS, "")),
            "doi": norm_doi_link(r.get(COL_DOI, "")),
            "year": y_num,
        }

    min_year = min(years) if years else 0
    max_year = max(years) if years else 0

    paper_facets = {}
    for _, r in final.iterrows():
        k = safe_str(r[COL_KEY])
        paper_facets[k] = {
            "domains": r["_domains"],
            "families": r["_families"],
            "vis": r["_vis"],
            "dataset": r["_dataset"],
            "vissrc": r["_vissrc"],
            "inter": r["_inter"],
            "anim": r["_anim"],
            "year": paper_meta.get(k, {}).get("year", None),
        }

    all_keys = sorted(final[COL_KEY].dropna().astype(str).unique().tolist())

    def unique_sorted(list_of_lists):
        s = set()
        for lst in list_of_lists:
            for x in lst:
                if x and str(x).strip():
                    s.add(str(x).strip())
        return sorted(s, key=lambda x: x.lower())

    domains = unique_sorted(final["_domains"])
    vis_values = unique_sorted(final["_vis"])
    dataset_values = unique_sorted(final["_dataset"])
    vissrc_values = unique_sorted(final["_vissrc"])
    inter_values = unique_sorted(final["_inter"])
    anim_values = unique_sorted(final["_anim"])

    # fixed scale: max cell count over full corpus domain x family
    domain_idx = {d: i for i, d in enumerate(domains)}
    fam_idx = {f: i for i, f in enumerate(FAMILIES)}
    cells = [[set() for _ in range(len(FAMILIES))] for __ in range(len(domains))]
    for k, fac in paper_facets.items():
        for d in fac["domains"]:
            di = domain_idx.get(d)
            if di is None:
                continue
            for f in fac["families"]:
                fi = fam_idx.get(f)
                if fi is None:
                    continue
                cells[di][fi].add(k)
    N_full = max([len(cells[i][j]) for i in range(len(domains)) for j in range(len(FAMILIES))] + [1])

    payload = {
        "all_keys": all_keys,
        "paper_meta": paper_meta,
        "paper_facets": paper_facets,
        "domains": domains,
        "families": FAMILIES,
        "fam_sign": FAM_SIGN,
        "vis_values": vis_values,
        "dataset_values": dataset_values,
        "vissrc_values": vissrc_values,
        "inter_values": inter_values,
        "anim_values": anim_values,
        "min_year": int(min_year),
        "max_year": int(max_year),
        "N_full": int(N_full),
        "colorscale": stepwise_tripolar_colorscale(N_full),
    }

    html = render_html(payload)
    out_html.write_text(html, encoding="utf-8")
    print(f"Wrote: {out_html} ({out_html.stat().st_size:,} bytes)")


def render_html(payload: dict) -> str:
    DATA_JSON = json.dumps(payload, ensure_ascii=False)
    # safety: prevent any accidental </script> termination (rare but safe)
    DATA_JSON = DATA_JSON.replace("</", "<\\/")

    html = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Paper Browser</title>
<script src="https://cdn.plot.ly/plotly-2.30.0.min.js"></script>
<style>
  :root{ --bg:#0b1220; --panel:#0f1a2e; --panel2:#0c1628; --text:#e8eefc;
    --muted:rgba(232,238,252,0.72); --border:rgba(232,238,252,0.12); --chip:rgba(232,238,252,0.10); }
  html,body{height:100%;}
  body{margin:0;font-family:ui-sans-serif,system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;
    background:radial-gradient(1200px 800px at 20% 20%, rgba(90,162,255,0.12), transparent 60%),
               radial-gradient(900px 700px at 70% 30%, rgba(135,90,255,0.10), transparent 60%), var(--bg);
    color:var(--text);}

  .app{display:grid;grid-template-columns:360px 1fr;height:100%;}

  .sidebar{background:linear-gradient(180deg,var(--panel),var(--panel2));
    border-right:1px solid var(--border);padding:14px;overflow-y:scroll;scrollbar-gutter:stable;}
  .main{padding:14px;overflow-y:scroll;scrollbar-gutter:stable;}

  .section{border:1px solid var(--border);border-radius:14px;padding:10px;margin:10px 0;background:rgba(255,255,255,0.03);}
  .sectionTitle{font-size:12px;text-transform:uppercase;letter-spacing:0.08em;color:var(--muted);margin:0 0 8px 0;}
  .chip{display:inline-flex;align-items:center;padding:4px 8px;border-radius:999px;background:var(--chip);
    border:1px solid var(--border);font-size:12px;color:rgba(232,238,252,0.85);}
  .btn{cursor:pointer;border:1px solid var(--border);border-radius:12px;padding:8px 10px;
    background:rgba(255,255,255,0.05);color:var(--text);font-size:12px;}
  .btn:hover{background:rgba(255,255,255,0.08);}
  .row{display:flex;gap:8px;align-items:center;flex-wrap:wrap;}
  .range{width:100%;accent-color:#5aa2ff;}
  .rangeRow{display:flex;justify-content:space-between;gap:8px;font-size:12px;color:rgba(232,238,252,0.85);}
  #yearChart{width:100%;height:170px;}
  .searchBox{width:100%;border-radius:12px;border:1px solid var(--border);background:rgba(0,0,0,0.25);
    color:var(--text);padding:8px 10px;outline:none;font-size:12px;}
  .list{max-height:150px;overflow:auto;padding-right:4px;}
  .item{display:flex;align-items:flex-start;gap:8px;padding:6px;border-radius:10px;}
  .item:hover{background:rgba(255,255,255,0.06);}
  .item input{margin-top:2px;}
  .item label{font-size:12px;line-height:1.25;color:rgba(232,238,252,0.9);cursor:pointer;}

  .topbar{display:grid;grid-template-columns: 1fr auto;gap:12px;align-items:start;margin-bottom:10px;}
  .titleBlock h2{margin:0;font-size:18px;}
  .titleBlock .desc{margin-top:4px;font-size:12px;color:var(--muted);max-width:1100px;}
  .actions{
    display:grid; grid-auto-flow: column; grid-auto-columns: max-content;
    gap:8px; align-items:start; justify-content:end; min-width: 560px;
  }
  #countChip{
    display:inline-block; width: 320px;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis; text-align: right;
  }
  .select{border-radius:12px;border:1px solid var(--border);background:rgba(0,0,0,0.25);
    color:var(--text);padding:8px 10px;outline:none;font-size:12px;}
  .card{border:1px solid var(--border);border-radius:16px;background:rgba(255,255,255,0.03);
    padding:10px 12px;box-shadow:0 10px 28px rgba(0,0,0,0.28);}
  .heatCard{padding:10px 8px;}
  #heatmap{width:100%;height:620px;}

  details.paper{border:1px solid var(--border);border-radius:14px;padding:8px 10px;margin:10px 0;background:rgba(0,0,0,0.18);}
  summary{cursor:pointer;font-weight:650;}
  .summaryLine{font-size:12px;color:rgba(232,238,252,0.85);margin-top:4px;}
  .metaLine{font-size:12px;color:rgba(232,238,252,0.82);margin-top:6px;}
  .abs{font-size:12px;color:rgba(232,238,252,0.92);white-space:pre-wrap;line-height:1.35;margin-top:8px;}
  a{color:#9ec2ff;text-decoration:none;} a:hover{text-decoration:underline;}

  @media (max-width:1000px){
    .app{grid-template-columns:1fr;}
    .sidebar{border-right:none;border-bottom:1px solid var(--border);}
    #heatmap{height:560px;}
    .actions{min-width:0;grid-auto-flow:row;justify-content:start;}
    #countChip{width:auto;text-align:left;}
  }

  .hmWrap{display:flex;gap:14px;align-items:stretch;}
  #heatmap{flex: 1 1 auto;min-width: 0;}

  /* FIX: remove percentage height (it breaks flex alignment unless parent has explicit height) */
  .bandLegend{
    flex: 0 0 auto; width: 180px;
    align-self: stretch; display:flex;
    align-items:flex-end; justify-content:flex-end;
    padding-bottom: 0px; box-sizing: border-box;
  }
</style>
</head>
<body>
<div class="app">
  <aside class="sidebar">
    <div class="section">
      <div class="sectionTitle">Publication year</div>
      <div id="yearChart"></div>
      <div class="rangeRow"><span id="yearMinLbl"></span><span id="yearMaxLbl"></span></div>
      <input id="yearMin" class="range" type="range" min="__MIN_YEAR__" max="__MAX_YEAR__" step="1" value="__MIN_YEAR__">
      <input id="yearMax" class="range" type="range" min="__MIN_YEAR__" max="__MAX_YEAR__" step="1" value="__MAX_YEAR__">
      <div class="row" style="margin-top:6px;">
        <span class="chip" id="yearChip"></span>
        <button class="btn" id="resetYears">Reset</button>
        <button class="btn" id="clearYearExact">Clear year</button>
      </div>
    </div>

    <div class="section">
      <div class="sectionTitle">Visualization type</div>
      <input id="visSearch" class="searchBox" placeholder="Search…">
      <div id="visList" class="list"></div>
      <div class="row"><button class="btn" id="visAll">All</button><button class="btn" id="visNone">None</button></div>
    </div>

    <div class="section">
      <div class="sectionTitle">Dataset source</div>
      <input id="datasetSearch" class="searchBox" placeholder="Search…">
      <div id="datasetList" class="list"></div>
      <div class="row"><button class="btn" id="datasetAll">All</button><button class="btn" id="datasetNone">None</button></div>
    </div>

    <div class="section">
      <div class="sectionTitle">Visualization source</div>
      <input id="vissrcSearch" class="searchBox" placeholder="Search…">
      <div id="vissrcList" class="list"></div>
      <div class="row"><button class="btn" id="vissrcAll">All</button><button class="btn" id="vissrcNone">None</button></div>
    </div>

    <div class="section">
      <div class="sectionTitle">Interactivity</div>
      <div id="interList" class="list"></div>
      <div class="row"><button class="btn" id="interAll">All</button><button class="btn" id="interNone">None</button></div>
    </div>

    <div class="section">
      <div class="sectionTitle">Animation</div>
      <div id="animList" class="list"></div>
      <div class="row"><button class="btn" id="animAll">All</button><button class="btn" id="animNone">None</button></div>
    </div>
  </aside>

  <main class="main">
    <div class="topbar">
      <div class="titleBlock">
        <h2>Domain application × Emotion family</h2>
        <div class="desc">Sorting: emotions can be ordered by valence (negative → positive) or by most-studied. The palette/legend are fixed to the global maximum for the corpus.</div>
      </div>
      <div class="actions">
        <span class="chip" id="countChip"></span>
        <select id="colOrderSel" class="select">
          <option value="valence">Emotions: negative → positive</option>
          <option value="studied_desc">Emotions: most → least studied</option>
        </select>
        <select id="rowOrderSel" class="select">
          <option value="studied_desc">Domains: most → least studied</option>
          <option value="alpha_asc">Domains: A → Z</option>
        </select>
        <button class="btn" id="resetAll">Reset all filters</button>
        <button class="btn" id="clearCell">Clear cell</button>
      </div>
    </div>

    <div class="card heatCard">
      <div class="hmWrap">
        <div id="heatmap"></div>
        <div id="bandLegend" class="bandLegend"></div>
      </div>
    </div>

    <div class="card" style="margin-top:12px;">
      <div class="row" style="justify-content:space-between;align-items:flex-end;gap:12px;">
        <div style="flex:1;min-width:260px;">
          <div class="sectionTitle" style="margin:0 0 6px 0;">Search papers</div>
          <input id="paperSearch" class="searchBox" placeholder="Search title/authors/abstract…">
        </div>
        <div>
          <div class="sectionTitle" style="margin:0 0 6px 0;">Sort</div>
          <select id="paperSortSel" class="select">
            <option value="year_desc">Year (newest → oldest)</option>
            <option value="year_asc">Year (oldest → newest)</option>
            <option value="title_asc">Title (A → Z)</option>
            <option value="title_desc">Title (Z → A)</option>
          </select>
        </div>
        <button class="btn" id="clearPaperSearch">Clear search</button>
      </div>
      <div id="paperList"></div>
    </div>
  </main>
</div>

<script>
const DATA = __DATA_JSON__;

const state = {
  yearMin: DATA.min_year,
  yearMax: DATA.max_year,
  yearExact: null,
  selectedVis: new Set(),
  selectedDataset: new Set(),
  selectedVissrc: new Set(),
  selectedInter: new Set(),
  selectedAnim: new Set(),
  colOrder: "valence",
  rowOrder: "studied_desc",
  paperSort: "year_desc",
  paperSearch: "",
  cellFilter: null
};

function escapeHtml(s){
  return (s||"").replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;')
                .replaceAll('"','&quot;').replaceAll("'","&#039;");
}
function normText(s){ return (s||"").toLowerCase(); }

function intersects(list, set){
  if (!set || set.size===0) return true;
  for (const v of (list || [])) if (set.has(v)) return true;
  return false;
}

function yearPass(y){
  if (y===null || y===undefined) return false;
  if (state.yearExact !== null) return y === state.yearExact;
  return (y>=state.yearMin && y<=state.yearMax);
}

function passCellFilter(k){
  if (!state.cellFilter) return true;
  const fac = DATA.paper_facets[k];
  if (!fac) return false;
  const hasDomain = (fac.domains || []).includes(state.cellFilter.domain);
  const hasFam = (fac.families || []).includes(state.cellFilter.family);
  return hasDomain && hasFam;
}

function cellFilterLabel(){
  if (!state.cellFilter) return "";
  return " · cell: " + state.cellFilter.domain + " × " + state.cellFilter.family;
}

function applyFilters(keys){
  const out=[];
  for (const k of keys){
    const fac = DATA.paper_facets[k];
    if (!fac) continue;
    if (!yearPass(fac.year)) continue;
    if (!intersects(fac.vis, state.selectedVis)) continue;
    if (!intersects(fac.dataset, state.selectedDataset)) continue;
    if (!intersects(fac.vissrc, state.selectedVissrc)) continue;
    if (!intersects(fac.inter, state.selectedInter)) continue;
    if (!intersects(fac.anim, state.selectedAnim)) continue;
    if (!passCellFilter(k)) continue;
    out.push(k);
  }
  return out;
}

function applyFiltersIgnoringYear(keys){
  const out=[];
  for (const k of keys){
    const fac = DATA.paper_facets[k];
    if (!fac) continue;
    if (!intersects(fac.vis, state.selectedVis)) continue;
    if (!intersects(fac.dataset, state.selectedDataset)) continue;
    if (!intersects(fac.vissrc, state.selectedVissrc)) continue;
    if (!intersects(fac.inter, state.selectedInter)) continue;
    if (!intersects(fac.anim, state.selectedAnim)) continue;
    out.push(k);
  }
  return out;
}

function renderCheckboxList(containerId, values, selectedSet, searchId=null){
  const container = document.getElementById(containerId);
  const search = searchId ? document.getElementById(searchId) : null;
  const q = search ? normText(search.value).trim() : "";
  container.innerHTML = "";
  for (const v of values){
    if (q && !normText(v).includes(q)) continue;
    const id = containerId + "_" + Math.random().toString(16).slice(2);
    const row = document.createElement("div");
    row.className = "item";
    row.innerHTML = `<input type="checkbox" id="${id}"><label for="${id}">${escapeHtml(v)}</label>`;
    const cb = row.querySelector("input");
    cb.checked = selectedSet.has(v);
    cb.addEventListener("change", ()=>{
      if (cb.checked) selectedSet.add(v); else selectedSet.delete(v);
      refresh();
    });
    container.appendChild(row);
  }
}

function setAll(values, set){ set.clear(); for (const v of values) set.add(v); }
function setNone(set){ set.clear(); }

function syncYearUI(){
  const yMin = document.getElementById("yearMin");
  const yMax = document.getElementById("yearMax");
  if (parseInt(yMin.value,10) > parseInt(yMax.value,10)) {
    const tmp = yMin.value; yMin.value = yMax.value; yMax.value = tmp;
  }
  state.yearMin = parseInt(yMin.value,10);
  state.yearMax = parseInt(yMax.value,10);
  document.getElementById("yearMinLbl").textContent = state.yearMin;
  document.getElementById("yearMaxLbl").textContent = state.yearMax;
  document.getElementById("yearChip").textContent =
    (state.yearExact!==null) ? `Year: ${state.yearExact}` : `${state.yearMin} — ${state.yearMax}`;
}

function renderYearChart(){
  const keys = applyFiltersIgnoringYear(DATA.all_keys);
  const yearCounts={};
  for (const k of keys){
    const y = DATA.paper_facets[k]?.year;
    if (y===null || y===undefined) continue;
    yearCounts[y] = (yearCounts[y]||0) + 1;
  }
  const xs=[]; const ys=[];
  for (let y=DATA.min_year; y<=DATA.max_year; y++){ xs.push(y); ys.push(yearCounts[y]||0); }

  const trace={type:"bar", x:xs, y:ys, hovertemplate:"Year %{x}<br># papers %{y}<extra></extra>"};
  const shapes=[];
  if (state.yearExact!==null){
    shapes.push({type:"rect",xref:"x",yref:"paper",x0:state.yearExact-0.5,x1:state.yearExact+0.5,y0:0,y1:1,
      fillcolor:"rgba(90,162,255,0.22)",line:{width:0},layer:"below"});
  } else {
    shapes.push({type:"rect",xref:"x",yref:"paper",x0:state.yearMin-0.5,x1:state.yearMax+0.5,y0:0,y1:1,
      fillcolor:"rgba(90,162,255,0.18)",line:{width:0},layer:"below"});
  }

  const layout={
    height:170, margin:{l:28,r:10,t:6,b:26},
    paper_bgcolor:"rgba(0,0,0,0)", plot_bgcolor:"rgba(0,0,0,0)",
    xaxis:{tickfont:{size:10}, automargin:true},
    yaxis:{tickfont:{size:10}, automargin:true, rangemode:"tozero"},
    font:{color:"rgba(232,238,252,0.95)"}, shapes
  };

  Plotly.react("yearChart",[trace],layout,{displaylogo:false,responsive:true}).then(gd=>{
    if (gd.removeAllListeners) gd.removeAllListeners("plotly_click");
    gd.on("plotly_click",(evt)=>{
      const year = evt.points[0].x;
      state.yearExact = (state.yearExact===year) ? null : year;
      syncYearUI();
      refresh();
    });
  });
}

function orderColsByValence(){
  const labels=DATA.families;
  const neg=[], neu=[], pos=[];
  for (let j=0;j<labels.length;j++) {
    const s=DATA.fam_sign[j];
    if (s<0) neg.push(j); else if (s>0) pos.push(j); else neu.push(j);
  }
  const alpha=(a,b)=>labels[a].localeCompare(labels[b]);
  neg.sort(alpha); neu.sort(alpha); pos.sort(alpha);
  return [...neg,...neu,...pos];
}

function buildMatrix(keys){
  const D = DATA.domains.length, F = DATA.families.length;
  const cell = Array.from({length:D}, ()=>Array.from({length:F}, ()=>new Set()));
  for (const k of keys){
    const fac = DATA.paper_facets[k];
    if (!fac) continue;
    for (const d of (fac.domains||[])) {
      const di = DATA.domains.indexOf(d);
      if (di<0) continue;
      for (const f of (fac.families||[])) {
        const fi = DATA.families.indexOf(f);
        if (fi<0) continue;
        cell[di][fi].add(k);
      }
    }
  }
  const counts = cell.map(row => row.map(s => s.size));
  const keysMat = cell.map(row => row.map(s => Array.from(s).sort()));
  return {counts, keysMat};
}

function hexToRgb(h){
  h = (h||"").replace("#","");
  const r = parseInt(h.slice(0,2),16), g = parseInt(h.slice(2,4),16), b = parseInt(h.slice(4,6),16);
  return {r,g,b};
}
function rgbToHex(r,g,b){
  const to = (x)=>("0"+x.toString(16)).slice(-2);
  return "#"+to(r)+to(g)+to(b);
}
function mixHex(c0, c1, t){
  const a=hexToRgb(c0), b=hexToRgb(c1);
  const r=Math.round(a.r+(b.r-a.r)*t), g=Math.round(a.g+(b.g-a.g)*t), bb=Math.round(a.b+(b.b-a.b)*t);
  return rgbToHex(r,g,bb);
}

function syncSquareCells(gd, nRows, nCols){
  if (!gd || !gd._fullLayout) return Promise.resolve();

  const m = gd._fullLayout.margin || {l:0,r:0,t:0,b:0};
  const outerW = gd.getBoundingClientRect().width;
  const plotW = Math.max(1, outerW - (m.l||0) - (m.r||0));
  const cell = plotW / Math.max(1, nCols);
  const desiredH = Math.round(cell * Math.max(1, nRows) + (m.t||0) + (m.b||0));

  const currentH = gd._fullLayout.height || 0;
  if (Math.abs(currentH - desiredH) > 2) {
    return Plotly.relayout(gd, { height: desiredH });
  }
  return Promise.resolve();
}

function makeDiscreteTripolarColorscale(N){
  const base = "#FFFFFF";
  const negHue = "#6D3C7B";
  const neuHue = "#808080";
  const posHue = "#6495ED";

  const maxZ = 3 * N;

  function colorForCount(hue, c){
    if (c <= 0) return base;
    return mixHex(base, hue, c / N);
  }

  function colorForZ(v){
    if (v <= 0) return base;
    if (v <= N) return colorForCount(posHue, v);
    if (v <= 2*N) return colorForCount(neuHue, v - N);
    return colorForCount(negHue, v - 2*N);
  }

  const cs = [];
  for (let v = 0; v <= maxZ; v++){
    const col = colorForZ(v);
    const p0 = Math.max(0, (v - 0.5) / maxZ);
    const p1 = Math.min(1, (v + 0.5) / maxZ);
    cs.push([p0, col], [p1, col]);
  }

  cs.sort((a,b)=>a[0]-b[0]);
  cs[0][0] = 0;
  cs[cs.length-1][0] = 1;
  return cs;
}

function renderBandLegend(){
  const el = document.getElementById("bandLegend");
  if (!el) return;

  const MAX_STEP = Math.min(5, DATA.N_full);

  const base = "#FFFFFF";
  const negHue = "#6D3C7B";
  const neuHue = "#808080";
  const posHue = "#6495ED";

  function scaleColors(hue){
    const arr = [];
    for (let s=0; s<=MAX_STEP; s++){
      if (s===0) arr.push(base);
      else arr.push(mixHex(base, hue, s / MAX_STEP));
    }
    return arr;
  }

  const neg = scaleColors(negHue);
  const neu = scaleColors(neuHue);
  const pos = scaleColors(posHue);

  const rows = [];
  for (let v=MAX_STEP; v>=0; v--) rows.push(v);

  const squareStyle = (c)=>(
    `width:16px;height:16px;background:${c};border:1px solid rgba(0,0,0,0.25);border-radius:3px;`
  );

  el.innerHTML = `
  <div style="
    display:grid;
    grid-template-columns: 24px 28px 28px 28px;
    grid-auto-rows: 22px;
    align-items:center;
    justify-content:start;
    column-gap:10px;
    row-gap:6px;
    font-size:12px;
    color:rgba(232,238,252,0.92);
  ">
    <div></div>
    <div style="text-align:center;font-weight:700;">Neg</div>
    <div style="text-align:center;font-weight:700;">Neu</div>
    <div style="text-align:center;font-weight:700;">Pos</div>

    ${rows.map(v=>`
      <div style="text-align:center;line-height:22px;">${v}</div>
      <div style="display:flex;justify-content:center;"><div style="${squareStyle(neg[v])}"></div></div>
      <div style="display:flex;justify-content:center;"><div style="${squareStyle(neu[v])}"></div></div>
      <div style="display:flex;justify-content:center;"><div style="${squareStyle(pos[v])}"></div></div>
    `).join("")}
  </div>`;
}

function syncLegendToPlot(gd){
  const leg = document.getElementById("bandLegend");
  if (!leg || !gd || !gd._fullLayout || !gd._fullLayout.yaxis) return;

  const outerH = gd.getBoundingClientRect().height;

  // Bottom of the actual plot/tile area in pixels from the top
  const ya = gd._fullLayout.yaxis;
  const plotBottom = (ya._offset || 0) + (ya._length || 0);

  // Space between plot bottom and div bottom
  const bottomGap = Math.max(0, outerH - plotBottom);

  leg.style.boxSizing = "border-box";
  leg.style.height = outerH + "px";
  leg.style.paddingBottom = bottomGap + "px";
}

function renderHeatmap(keys){
  const {counts, keysMat} = buildMatrix(keys);

  let rIdx = Array.from({length: DATA.domains.length}, (_,i)=>i);
  const rowTotals = counts.map(r => r.reduce((a,b)=>a+b,0));
  if (state.rowOrder === "alpha_asc") {
    rIdx.sort((a,b)=>DATA.domains[a].localeCompare(DATA.domains[b]));
  } else {
    rIdx.sort((a,b)=>(rowTotals[b]-rowTotals[a]) || DATA.domains[a].localeCompare(DATA.domains[b]));
  }

  let cIdx;
  const colTotals = Array.from({length: DATA.families.length}, (_,j)=>counts.reduce((a,row)=>a+row[j],0));
  if (state.colOrder === "studied_desc") {
    cIdx = Array.from({length: DATA.families.length}, (_,j)=>j);
    cIdx.sort((a,b)=>(colTotals[b]-colTotals[a]) || DATA.families[a].localeCompare(DATA.families[b]));
  } else {
    cIdx = orderColsByValence();
  }

  const y = rIdx.map(i=>DATA.domains[i]);
  const x = cIdx.map(j=>DATA.families[j]);
  const N = DATA.N_full;

  const z = rIdx.map(i => cIdx.map(j => {
    const count = counts[i][j];
    if (!count) return 0;
    const sign = DATA.fam_sign[j]; // +1, 0, -1
    const offset = (sign > 0) ? 0 : ((sign === 0) ? N : 2*N);
    return offset + count;
  }));

  const countRe = rIdx.map(i => cIdx.map(j => counts[i][j]));
  const keysRe = rIdx.map(i => cIdx.map(j => keysMat[i][j]));
  const custom = countRe.map((row,i)=>row.map((c,j)=>({count:c, keys_str:keysRe[i][j].join(", ")})));

  const trace = {
    type: "heatmap",
    z, x, y,
    zmin: 0,
    zmax: 3 * N,
    colorscale: makeDiscreteTripolarColorscale(N),
    customdata: custom,
    hovertemplate:
      "Domain: %{y}<br>Emotion family: %{x}<br># papers: %{customdata.count}<br>NEW KEYs: %{customdata.keys_str}<extra></extra>",
    showscale: false,
    zsmooth: false
  };

  const layout = {
    margin:{l:210,r:10,t:18,b:10},
    height:400,
    xaxis:{side:"top", tickangle:40, automargin:true},
    yaxis:{autorange:"reversed", automargin:true},
    paper_bgcolor:"rgba(0,0,0,0)",
    plot_bgcolor:"rgba(0,0,0,0)",
    font:{color:"rgba(232,238,252,0.95)"}
  };

  Plotly.react("heatmap", [trace], layout, {displaylogo:false, responsive:true}).then(gd => {
    const nRows = y.length;
    const nCols = x.length;
    gd.__squareDims = { nRows, nCols };

    Promise.resolve(syncSquareCells(gd, nRows, nCols)).then(() => {
      syncLegendToPlot(gd);

      if (gd.removeAllListeners) gd.removeAllListeners("plotly_click");
      gd.on("plotly_click", (evt) => {
        const p = evt.points?.[0];
        if (!p) return;

        const domain = p.y;
        const family = p.x;

        if (state.cellFilter && state.cellFilter.domain === domain && state.cellFilter.family === family) {
          state.cellFilter = null;
        } else {
          state.cellFilter = { domain, family };
        }
        refresh();
      });
    });
  });
}

function searchAndSort(keys){
  const meta=DATA.paper_meta;
  const q=normText(state.paperSearch).trim();
  let arr = keys.filter(k => meta[k]);
  if (q){
    arr = arr.filter(k=>{
      const m=meta[k];
      const blob = `${m.title||""} ${m.authors||""} ${m.abstract||""}`.toLowerCase();
      return blob.includes(q);
    });
  }
  if (state.paperSort==="year_desc") arr.sort((a,b)=>(meta[b].year||-1e18)-(meta[a].year||-1e18));
  if (state.paperSort==="year_asc")  arr.sort((a,b)=>(meta[a].year||-1e18)-(meta[b].year||-1e18));
  if (state.paperSort==="title_asc") arr.sort((a,b)=>(meta[a].title||"").localeCompare(meta[b].title||""));
  if (state.paperSort==="title_desc")arr.sort((a,b)=>(meta[b].title||"").localeCompare(meta[a].title||""));
  return arr;
}

function renderPaperList(keys){
  const meta=DATA.paper_meta;
  const list=document.getElementById("paperList");
  list.innerHTML="";
  const arr = searchAndSort(keys);

  for (const k of arr){
    const m=meta[k];
    const title=m.title || "(no title)";
    const year=m.year ? m.year : "";
    const doi=m.doi || "";
    const doiHtml = doi ? `<a href="${escapeHtml(doi)}" target="_blank" rel="noopener">Open via DOI</a>`
                        : `<span style="color:rgba(232,238,252,0.55)">No DOI link</span>`;

    const el=document.createElement("details");
    el.className="paper";
    el.innerHTML = `
      <summary>${escapeHtml(title)}</summary>
      <div class="summaryLine">${escapeHtml(m.authors||"")}${year ? " · " + year : ""}</div>
      <div class="metaLine"><b>Country:</b> ${escapeHtml(m.country||"")}</div>
      <div class="metaLine">${doiHtml}</div>
      <div class="abs"><b>Abstract:</b>\\n${escapeHtml(m.abstract||"")}</div>
    `;
    list.appendChild(el);
  }

  if (arr.length===0){
    list.innerHTML = `<div class="metaLine" style="color:rgba(232,238,252,0.7)">No papers match the current filters.</div>`;
  }
}

function refresh(){
  renderYearChart();
  const filtered = applyFilters(DATA.all_keys);
  document.getElementById("countChip").textContent = `${filtered.length} papers${cellFilterLabel()}`;
  renderHeatmap(filtered);
  renderPaperList(filtered);
}

function init(){
  document.getElementById("yearMin").addEventListener("input", ()=>{ state.yearExact=null; syncYearUI(); refresh(); });
  document.getElementById("yearMax").addEventListener("input", ()=>{ state.yearExact=null; syncYearUI(); refresh(); });
  document.getElementById("resetYears").addEventListener("click", ()=>{
    state.yearExact=null;
    document.getElementById("yearMin").value = DATA.min_year;
    document.getElementById("yearMax").value = DATA.max_year;
    syncYearUI(); refresh();
  });
  document.getElementById("clearYearExact").addEventListener("click", ()=>{ state.yearExact=null; syncYearUI(); refresh(); });
  syncYearUI();

  renderCheckboxList("visList", DATA.vis_values, state.selectedVis, "visSearch");
  renderCheckboxList("datasetList", DATA.dataset_values, state.selectedDataset, "datasetSearch");
  renderCheckboxList("vissrcList", DATA.vissrc_values, state.selectedVissrc, "vissrcSearch");
  renderCheckboxList("interList", DATA.inter_values, state.selectedInter);
  renderCheckboxList("animList", DATA.anim_values, state.selectedAnim);

  document.getElementById("visSearch").addEventListener("input", ()=>renderCheckboxList("visList", DATA.vis_values, state.selectedVis, "visSearch"));
  document.getElementById("datasetSearch").addEventListener("input", ()=>renderCheckboxList("datasetList", DATA.dataset_values, state.selectedDataset, "datasetSearch"));
  document.getElementById("vissrcSearch").addEventListener("input", ()=>renderCheckboxList("vissrcList", DATA.vissrc_values, state.selectedVissrc, "vissrcSearch"));

  document.getElementById("visAll").addEventListener("click", ()=>{ setAll(DATA.vis_values, state.selectedVis); renderCheckboxList("visList", DATA.vis_values, state.selectedVis, "visSearch"); refresh(); });
  document.getElementById("visNone").addEventListener("click", ()=>{ setNone(state.selectedVis); renderCheckboxList("visList", DATA.vis_values, state.selectedVis, "visSearch"); refresh(); });

  document.getElementById("datasetAll").addEventListener("click", ()=>{ setAll(DATA.dataset_values, state.selectedDataset); renderCheckboxList("datasetList", DATA.dataset_values, state.selectedDataset, "datasetSearch"); refresh(); });
  document.getElementById("datasetNone").addEventListener("click", ()=>{ setNone(state.selectedDataset); renderCheckboxList("datasetList", DATA.dataset_values, state.selectedDataset, "datasetSearch"); refresh(); });

  document.getElementById("vissrcAll").addEventListener("click", ()=>{ setAll(DATA.vissrc_values, state.selectedVissrc); renderCheckboxList("vissrcList", DATA.vissrc_values, state.selectedVissrc, "vissrcSearch"); refresh(); });
  document.getElementById("vissrcNone").addEventListener("click", ()=>{ setNone(state.selectedVissrc); renderCheckboxList("vissrcList", DATA.vissrc_values, state.selectedVissrc, "vissrcSearch"); refresh(); });

  document.getElementById("interAll").addEventListener("click", ()=>{ setAll(DATA.inter_values, state.selectedInter); renderCheckboxList("interList", DATA.inter_values, state.selectedInter); refresh(); });
  document.getElementById("interNone").addEventListener("click", ()=>{ setNone(state.selectedInter); renderCheckboxList("interList", DATA.inter_values, state.selectedInter); refresh(); });

  document.getElementById("animAll").addEventListener("click", ()=>{ setAll(DATA.anim_values, state.selectedAnim); renderCheckboxList("animList", DATA.anim_values, state.selectedAnim); refresh(); });
  document.getElementById("animNone").addEventListener("click", ()=>{ setNone(state.selectedAnim); renderCheckboxList("animList", DATA.anim_values, state.selectedAnim); refresh(); });

  document.getElementById("colOrderSel").addEventListener("change", (e)=>{ state.colOrder=e.target.value||"valence"; refresh(); });
  document.getElementById("rowOrderSel").addEventListener("change", (e)=>{ state.rowOrder=e.target.value||"studied_desc"; refresh(); });

  document.getElementById("paperSortSel").addEventListener("change",(e)=>{ state.paperSort=e.target.value||"year_desc"; refresh(); });
  document.getElementById("paperSearch").addEventListener("input",(e)=>{ state.paperSearch=e.target.value||""; refresh(); });
  document.getElementById("clearPaperSearch").addEventListener("click", ()=>{ state.paperSearch=""; document.getElementById("paperSearch").value=""; refresh(); });

  document.getElementById("resetAll").addEventListener("click", ()=>{
    state.yearExact=null;
    document.getElementById("yearMin").value=DATA.min_year;
    document.getElementById("yearMax").value=DATA.max_year;

    state.selectedVis.clear(); state.selectedDataset.clear(); state.selectedVissrc.clear(); state.selectedInter.clear(); state.selectedAnim.clear();
    state.colOrder="valence"; state.rowOrder="studied_desc"; state.paperSort="year_desc"; state.paperSearch=""; state.cellFilter = null;

    document.getElementById("colOrderSel").value="valence";
    document.getElementById("rowOrderSel").value="studied_desc";
    document.getElementById("paperSortSel").value="year_desc";
    document.getElementById("paperSearch").value="";
    document.getElementById("visSearch").value="";
    document.getElementById("datasetSearch").value="";
    document.getElementById("vissrcSearch").value="";
    syncYearUI();
    renderCheckboxList("visList", DATA.vis_values, state.selectedVis, "visSearch");
    renderCheckboxList("datasetList", DATA.dataset_values, state.selectedDataset, "datasetSearch");
    renderCheckboxList("vissrcList", DATA.vissrc_values, state.selectedVissrc, "vissrcSearch");
    renderCheckboxList("interList", DATA.inter_values, state.selectedInter);
    renderCheckboxList("animList", DATA.anim_values, state.selectedAnim);
    refresh();
  });

  document.getElementById("clearCell").addEventListener("click", ()=>{
    state.cellFilter = null;
    refresh();
  });

  renderBandLegend();

window.addEventListener("resize", () => {
  const gd = document.getElementById("heatmap");
  if (!gd) return;

  Plotly.Plots.resize(gd)
    .then(() => {
      const dims = gd.__squareDims || { nRows: DATA.domains.length, nCols: DATA.families.length };
      return syncSquareCells(gd, dims.nRows, dims.nCols);
    })
    .then(() => {
      // Align legend to the bottom of the *tile area* (not the wrapper)
      syncLegendToPlot(gd);
    });
});

refresh();
}

init();
</script>
</body>
</html>
"""

    html = (html
            .replace("__DATA_JSON__", DATA_JSON)
            .replace("__MIN_YEAR__", str(payload["min_year"]))
            .replace("__MAX_YEAR__", str(payload["max_year"])))
    return html


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("xlsx", type=Path, help="Path to the Excel corpus file")
    ap.add_argument("--out", type=Path, default=Path("starbrowser.html"), help="Output HTML file")
    args = ap.parse_args()

    build(args.xlsx, args.out)
