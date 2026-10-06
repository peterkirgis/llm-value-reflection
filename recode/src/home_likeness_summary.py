"""home_likeness_summary — one simple bar per model: how far, on average, it edits
other providers' documents from the way those providers' own models do.

Peter's request: "the figure which looks at distance from the home provider in
a simple format like these ones" (ts_value_drift_summary / ts_value_drift_round20).

METRIC (reused from recode/src/home_likeness.py by import, not reimplemented)
    Frame, per-edit 6-metric vector, cell profile, reference and L1 distance
    are home_likeness.load_frame / cell_profiles / reference / l1 / analyze.
    Bar = the model's average distance over the three FOREIGN documents it
    edited in cross_edit (home_likeness.analyze(...)["visitor_avg"]).
    Reference line = mean of the home models' leave-one-out distances over all
    four documents (3 + 3 + 2 + 2 = 10 distances).

UNCERTAINTY
    Within-run moving-block bootstrap. Every cross_edit cell (one run per
    model x document) is resampled on its own: its applied, coded edits in
    round order are cut into overlapping contiguous blocks of BLOCK = 5,
    block starts are drawn uniformly with replacement, and blocks are
    concatenated and truncated to the cell's original length. Cell profiles,
    home means and each model's average distance are then recomputed.
    95% percentile interval; P(most home-like) = share of draws in which a
    model has the smallest average distance (ties split evenly).
    B and the seed come from recode/config.yaml (bootstrap.B, seeds.bootstrap).
    One run per cell, so run-to-run variation is not represented: intervals
    are optimistic.

Usage:
    .venv/bin/python recode/src/home_likeness_summary.py
Outputs:
    recode/figures/ts_home_likeness_summary.{png,pdf}
    recode/figures/data/ts_home_likeness_summary.json
    a section at the end of recode/figures/HOME_LIKENESS.md (replaced in place
    on rerun; text above it is never touched). home_likeness.py rewrites
    HOME_LIKENESS.md from scratch, so rerun this script after it.

Paper mode (AAAI LaTeX port):
    .venv/bin/python recode/src/home_likeness_summary.py --paper
Outputs with --paper (nothing under recode/figures or recode/data is written):
    recode/paper/figures/ts_home_likeness_summary.png    (no title, whisker note or footer in the image)
    recode/paper/figures/captions/ts_home_likeness_summary.json   (removed texts, for the LaTeX caption,
                                                                   plus the print size and measured minima)
    recode/paper/figures/data/ts_home_likeness_summary.json       (default sidecar structure plus the same
                                                                   print size and minima)
The paper figure is built at its printed size (full text width, 7.0 in) and
included at 100%, so its font sizes and line widths are printed points: text
>= 9 pt, strokes >= 0.5 pt (AAAI 2027 author kit), Helvetica (Arial if
matplotlib cannot load Helvetica), 300 dpi.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

import numpy as np
import yaml

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import home_likeness as hl  # noqa: E402

ROOT = hl.ROOT
FIG_DIR = hl.FIG_DIR
DATA_DIR = FIG_DIR / "data"
STEM = "ts_home_likeness_summary"
MD_PATH = hl.MD_PATH
MD_MARKER = "## Summary figure: average distance from the home provider (`ts_home_likeness_summary`)"
BLOCK = 5

# --paper: caption-free renders for the AAAI LaTeX port (PNG only; AAAI forbids Type 3 fonts).
PAPER_FIG_DIR = ROOT / "recode" / "paper" / "figures"
PAPER_DATA_DIR = PAPER_FIG_DIR / "data"
PAPER_CAPTION_DIR = PAPER_FIG_DIR / "captions"
# AAAI two-column page: a full-width figure* is 7.0 in, one column 3.33 in. The PNG is
# saved tight with PAPER_PAD_IN and must land in PAPER_WIDTH_RANGE_IN for its layout.
PAPER_LAYOUT = "full"
PAPER_WIDTH_RANGE_IN = {"full": (6.6, 7.0), "column": (3.0, 3.33)}
PAPER_FIGSIZE_IN = (7.0, 3.4)
PAPER_PAD_IN = 0.02
PAPER_DPI = 300
PAPER_MIN_FONT_PT = 9.0
PAPER_MIN_LINEWIDTH_PT = 0.5
PRINT_KEYS = ("layout", "print_width_in", "print_height_in", "min_font_pt", "min_linewidth_pt")

MODEL_COLORS = hl.MODEL_COLORS
MODEL_ORDER = hl.MODEL_ORDER
INK = hl.INK
NOTE_COLOR = hl.NOTE_COLOR

# Committed per-visitor averages (HOME_LIKENESS.md, ensemble column).
COMMITTED_AVG = {
    "Claude Opus 4.7": 0.435, "GPT-5.4 Mini": 0.596, "Claude Haiku 4.5": 0.598,
    "Claude Sonnet 4.6": 0.821, "Grok 4.2": 0.872, "GPT-5.4": 0.894,
    "Gemini 3.1 Pro": 0.921, "Gemini 3 Flash": 0.928, "Grok 4.3": 1.137,
    "GPT-5.5": 1.156,
}

WHISKER_NOTE = "Whiskers: 95% bootstrap interval (blocks of rounds resampled within each run)"
FOOTER = [
    "Distance: how differently a model edits another provider's document than that provider's own models do "
    "(judge score and five conflict metrics), averaged over the three other providers' documents.",
    "Dashed line: typical distance between a provider's own models. Home-like means editing like the developer's "
    "own models, not faithfulness to the document. Cross-edit; three-grader majority-vote codes.",
]

# Sizes of the bar panel. DEFAULT_STYLE is the report render (15 in canvas, shrunk on display);
# PAPER_STYLE is in printed points (figure built at 7.0 in and included at 100%).
DEFAULT_STYLE = {
    "bar_lw": 0.7, "capsize": 4, "error_kw": {"elinewidth": 1.2, "ecolor": INK},
    "value_fs": 12, "ref_lw": 1.4, "ref_fs": 11.5, "ytick_fs": 13, "xtick_fs": 13,
    "xlabel_fs": 14, "xlabel_pad": 8, "grid_kw": {"linestyle": ":", "alpha": 0.4},
}
PAPER_STYLE = {
    "bar_lw": 0.7, "capsize": 2.5, "error_kw": {"elinewidth": 0.8, "capthick": 0.8, "ecolor": INK},
    "value_fs": 9, "ref_lw": 1.0, "ref_fs": 9, "ytick_fs": 9, "xtick_fs": 9,
    "xlabel_fs": 10, "xlabel_pad": 4, "grid_kw": {"linestyle": ":", "alpha": 0.4, "linewidth": 0.6},
}


def log(msg: str) -> None:
    print(f"[home-summary] {msg}", flush=True)


def load_config(path: Path = hl.CONFIG_PATH) -> tuple[int, int]:
    cfg = yaml.safe_load(Path(path).read_text())
    return int(cfg["bootstrap"]["B"]), int(cfg["seeds"]["bootstrap"])


def model_rank(m: str) -> int:
    return MODEL_ORDER.index(m) if m in MODEL_ORDER else len(MODEL_ORDER)


# ---------------------------------------------------------------------------
# Metric (thin wrappers over home_likeness)
# ---------------------------------------------------------------------------

def homes_of(models, doc: str) -> list[str]:
    return [m for m in models if hl.MODEL_FAMILY[m] == hl.DOC_OWNER[doc]]


def distances_from_profiles(profiles: dict) -> dict:
    """{doc: {model: distance}} from a profiles dict, via hl.reference and hl.l1
    (the same computation as hl.analyze)."""
    models = [m for m in MODEL_ORDER if any(k[0] == m for k in profiles)]
    out = {}
    for d in hl.DOC_IDS:
        homes = [m for m in homes_of(models, d) if (m, d) in profiles]
        out[d] = {m: hl.l1(profiles[(m, d)], hl.reference(profiles, d, m, homes))
                  for m in models if (m, d) in profiles}
    return out


def average_foreign(dist: dict) -> dict:
    """model -> mean distance over its foreign documents."""
    acc: dict[str, list[float]] = {}
    for d, per in dist.items():
        for m, v in per.items():
            if hl.MODEL_FAMILY[m] != hl.DOC_OWNER[d]:
                acc.setdefault(m, []).append(v)
    return {m: float(np.mean(v)) for m, v in acc.items()}


def within_family(dist: dict) -> list[float]:
    """Home models' leave-one-out distances over all documents."""
    return [v for d, per in dist.items() for m, v in per.items() if hl.MODEL_FAMILY[m] == hl.DOC_OWNER[d]]


# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------

def cell_arrays(frame) -> dict:
    """(model, doc) -> (n, k) edit vectors in round order (one run per cell)."""
    cells: dict = {}
    for e in frame:
        cells.setdefault((e["model"], e["doc"]), []).append(e)
    out = {}
    for key in sorted(cells, key=lambda k: (model_rank(k[0]), hl.DOC_IDS.index(k[1]))):
        es = sorted(cells[key], key=lambda e: e["round"])
        assert len({e["run_id"] for e in es}) == 1, f"cell {key} spans runs"
        out[key] = np.array([e["vec"] for e in es], float)
    return out


def block_indices(n: int, B: int, rng, block: int = BLOCK) -> np.ndarray:
    """(B, n) indices: moving-block bootstrap of a length-n sequence.

    Block length L = min(block, n); starts uniform on 0..n-L (overlapping
    blocks); ceil(n/L) blocks concatenated and truncated to n.
    """
    L = min(block, n)
    k = -(-n // L)
    starts = rng.integers(0, n - L + 1, size=(B, k))
    idx = (starts[:, :, None] + np.arange(L)[None, None, :]).reshape(B, k * L)
    return idx[:, :n]


def block_bootstrap(frame, B: int, seed: int, block: int = BLOCK, exclude=()) -> dict:
    """Bootstrap draws of per-model average distance and the reference line.

    Cells are resampled in a fixed order (MODEL_ORDER, then DOC_IDS) from one
    default_rng(seed), so results are deterministic for (frame, B, seed).
    Returns {"avg": {model: (B,)}, "reference": (B,)}.
    """
    rng = np.random.default_rng(seed)
    arrays = {k: v for k, v in cell_arrays(frame).items() if k not in exclude}
    draw_profiles = {}
    for key, X in arrays.items():
        idx = block_indices(len(X), B, rng, block)
        draw_profiles[key] = X[idx].mean(axis=1)  # (B, k)
    avg: dict[str, np.ndarray] = {}
    ref = np.empty(B)
    for b in range(B):
        profiles = {k: v[b] for k, v in draw_profiles.items()}
        dist = distances_from_profiles(profiles)
        for m, v in average_foreign(dist).items():
            avg.setdefault(m, np.empty(B))[b] = v
        ref[b] = np.mean(within_family(dist))
    return {"avg": avg, "reference": ref}


def p_most_home_like(draws: dict) -> dict:
    """Share of draws in which each model has the minimum distance (ties split)."""
    models = list(draws)
    mat = np.vstack([draws[m] for m in models])
    is_min = np.isclose(mat, mat.min(axis=0, keepdims=True), rtol=0, atol=1e-12)
    share = (is_min / is_min.sum(axis=0, keepdims=True)).mean(axis=1)
    return {m: float(s) for m, s in zip(models, share)}


def sort_most_home_like(values: dict) -> list[str]:
    return sorted(values, key=lambda m: (values[m], model_rank(m), m))


# ---------------------------------------------------------------------------
# Title rule
# ---------------------------------------------------------------------------

def _join(names: list[str]) -> str:
    if len(names) <= 2:
        return " and ".join(names)
    return ", ".join(names[:-1]) + " and " + names[-1]


def title_rule(order: list[str], p: dict) -> tuple[str, str]:
    """(title, branch). order = most home-like first."""
    top = order[0]
    tail = "Other Providers' Documents Most Like Their Own Models"
    if p.get(top, 0.0) >= 0.95:
        return f"{top} Edits {tail}", "p_top>=0.95"
    leaders = [m for m in order if p.get(m, 0.0) >= 0.05]
    if top not in leaders:
        leaders = [top] + leaders
    if len(leaders) == 1:
        return f"{top} Likely Edits {tail}", "hedged_single"
    return f"{_join(leaders)} Edit {tail}", "hedged_multi"


# ---------------------------------------------------------------------------
# Assembly
# ---------------------------------------------------------------------------

def compute_summary(frame, B: int, seed: int) -> dict:
    res = hl.analyze(frame, hl.ALL_IDX, run_perm=False)
    committed = {m: v["mean"] for m, v in res["visitor_avg"].items()}
    dist = {d: res["per_doc"][d]["distance"] for d in hl.DOC_IDS}
    avg = average_foreign(dist)
    assert set(avg) == set(committed)
    for m in avg:
        assert abs(avg[m] - committed[m]) < 1e-12, (m, avg[m], committed[m])
        assert round(avg[m], 3) == COMMITTED_AVG[m], (m, avg[m], COMMITTED_AVG[m])
    wf = within_family(dist)
    ref = float(np.mean(wf))

    res_x = hl.analyze(frame, hl.ALL_IDX, exclude=(hl.NO_CSAM_CELL,), run_perm=False)
    opus = hl.NO_CSAM_CELL[0]
    opus_excl = res_x["visitor_avg"][opus]

    t0 = time.time()
    boot = block_bootstrap(frame, B, seed)
    log(f"bootstrap B={B} done in {time.time() - t0:.1f}s")
    p = p_most_home_like(boot["avg"])
    order = sort_most_home_like(avg)
    title, branch = title_rule(order, p)
    n_docs = {m: v["n_docs"] for m, v in res["visitor_avg"].items()}
    models = {}
    for m in order:
        lo, hi = np.percentile(boot["avg"][m], [2.5, 97.5])
        models[m] = {"avg_distance": avg[m], "ci95": [float(lo), float(hi)], "p_most_home_like": p[m],
                     "n_foreign_docs": n_docs[m],
                     "per_document": {d: dist[d][m] for d in hl.DOC_IDS
                                      if hl.MODEL_FAMILY[m] != hl.DOC_OWNER[d]}}
    rlo, rhi = np.percentile(boot["reference"], [2.5, 97.5])
    return {
        "order_most_home_like_first": order,
        "models": models,
        "reference_line": {"value": ref, "ci95": [float(rlo), float(rhi)],
                           "range": [min(wf), max(wf)], "n_distances": len(wf),
                           "definition": "mean of the home models' leave-one-out distances over all four documents"},
        "opus_excluding_no_csam": {"avg_distance": opus_excl["mean"], "n_foreign_docs": opus_excl["n_docs"],
                                   "rank_if_substituted": 1 + sum(v < opus_excl["mean"] for k, v in avg.items()
                                                                  if k != opus)},
        "title": title,
        "title_branch": branch,
        "n_frame_edits": len(frame),
        "bootstrap": {"B": B, "seed": seed, "block_length": BLOCK,
                      "scheme": "moving-block bootstrap within each cross_edit run (one run per model x document): "
                                "overlapping contiguous blocks of rounds, starts drawn uniformly with replacement, "
                                "concatenated and truncated to the run's original length",
                      "interval": "percentile 2.5/97.5",
                      "caveat": "one run per cell: run-to-run variation is not represented (optimistic)"},
    }


# ---------------------------------------------------------------------------
# Figure
# ---------------------------------------------------------------------------

def _draw_bars(ax, s: dict, st: dict) -> None:
    """The bar panel (bars, whiskers, value labels, reference line, axes) with the sizes in st."""
    order = s["order_most_home_like_first"]
    ms = s["models"]
    n = len(order)
    vals = np.array([ms[m]["avg_distance"] for m in order])
    lo = np.array([ms[m]["ci95"][0] for m in order])
    hi = np.array([ms[m]["ci95"][1] for m in order])
    ref = s["reference_line"]["value"]

    y = np.arange(n)
    ax.barh(y, vals, xerr=np.vstack([vals - lo, hi - vals]), color=[MODEL_COLORS.get(m, "#999") for m in order],
            edgecolor=INK, linewidth=st["bar_lw"], height=0.65, capsize=st["capsize"],
            error_kw=dict(st["error_kw"]), zorder=2)
    xmax = float(hi.max())
    for yi, v, h in zip(y, vals, hi):
        ax.text(h + xmax * 0.012, yi, f"{v:.2f}", va="center", fontsize=st["value_fs"], color=INK, zorder=4)
    # P(most home-like) stays in the sidecar JSON and HOME_LIKENESS.md (it drives the title rule).
    ax.set_xlim(0, xmax * 1.10)
    ax.axvline(ref, color=INK, lw=st["ref_lw"], ls=(0, (5, 3)), zorder=3)
    ax.text(ref + xmax * 0.008, -0.72, f"typical distance between a provider's own models ({ref:.2f})",
            va="center", ha="left", fontsize=st["ref_fs"], color=INK, style="italic")
    ax.set_yticks(y)
    ax.set_yticklabels(order, fontsize=st["ytick_fs"])
    ax.set_ylim(n - 0.4, -1.15)  # most home-like at the top; headroom for the line label
    ax.tick_params(axis="x", labelsize=st["xtick_fs"])
    ax.set_xlabel("Average distance from the home provider's own models (lower = more home-like)",
                  fontsize=st["xlabel_fs"], labelpad=st["xlabel_pad"])
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="x", **st["grid_kw"])
    ax.set_axisbelow(True)


def plot(s: dict, out_dir: Path = FIG_DIR, stem: str = STEM, paper: bool = False,
         caption_dir: Path | None = None) -> list[Path]:
    """Render the figure. paper=True: see _plot_paper (printed size, no title/notes in the image, PNG only)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    out_dir.mkdir(parents=True, exist_ok=True)
    if paper:
        return _plot_paper(s, stem, out_dir, caption_dir if caption_dir is not None else out_dir / "captions")

    fig, ax = plt.subplots(figsize=(15, 0.55 * len(s["order_most_home_like_first"]) + 3.0))
    _draw_bars(ax, s, DEFAULT_STYLE)
    fig.suptitle(s["title"], fontsize=16, fontweight="bold", y=0.995)
    fig.text(0.995, 0.952, WHISKER_NOTE, ha="right", va="top", fontsize=12, color=NOTE_COLOR, style="italic")
    fig.text(0.5, 0.01, "\n".join(FOOTER), ha="center", va="bottom", fontsize=10.5, color=NOTE_COLOR,
             style="italic", linespacing=1.45)
    fig.tight_layout(rect=(0, 0.085, 1, 0.935))
    paths = []
    for ext in ("pdf", "png"):
        out = out_dir / f"{stem}.{ext}"
        fig.savefig(out, bbox_inches="tight", dpi=300)
        paths.append(out)
        log(f"saved {out}")
    plt.close(fig)
    return paths


# ---------------------------------------------------------------------------
# Paper figure (printed size)
# ---------------------------------------------------------------------------

def _paper_font() -> str:
    """Helvetica if matplotlib can load it, else Arial (Helvetica metrics).

    On macOS matplotlib loads only the regular face of Helvetica.ttc, so the italic
    reference-line label prints upright in paper mode.
    """
    from matplotlib import font_manager
    for family in ("Helvetica", "Arial"):
        try:
            font_manager.findfont(font_manager.FontProperties(family=family), fallback_to_default=False)
            return family
        except ValueError:
            continue
    raise RuntimeError("paper mode needs Helvetica or Arial; matplotlib can load neither")


def print_minima(fig) -> tuple[float, float]:
    """(smallest font size, thinnest stroke) in points over everything drawn in fig.

    Text: visible Text artists with non-empty text. Strokes: Line2D lines and markers (tick
    marks and whisker caps are markers), Patch edges (bars, spines) and Collection edges
    (whisker segments) with width > 0. Ticks the Axis keeps outside the view limits are not
    drawn and are skipped.
    """
    from matplotlib.collections import Collection
    from matplotlib.colors import to_rgba_array
    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch
    from matplotlib.text import Text

    fig.canvas.draw()
    undrawn = set()
    for ax in fig.axes:
        for axis in (ax.xaxis, ax.yaxis):
            a, b = sorted(axis.get_view_interval())
            tol = 1e-9 * max(b - a, 1.0)
            for tick in axis.get_major_ticks() + axis.get_minor_ticks():
                if not a - tol <= tick.get_loc() <= b + tol:
                    undrawn.update(tick.get_children())

    def drawn(artist) -> bool:
        return artist.get_visible() and artist not in undrawn

    no_style = (None, "None", "none", "", " ")
    fonts = [t.get_fontsize() for t in fig.findobj(Text) if drawn(t) and t.get_text().strip()]
    strokes = []
    for ln in fig.findobj(Line2D):
        if not drawn(ln):
            continue
        if ln.get_linestyle() not in no_style and ln.get_linewidth() > 0:
            strokes.append(ln.get_linewidth())
        if ln.get_marker() not in no_style and ln.get_markeredgewidth() > 0:
            strokes.append(ln.get_markeredgewidth())
    for p in fig.findobj(Patch):
        if drawn(p) and p.get_linewidth() > 0 and p.get_edgecolor()[3] > 0:
            strokes.append(p.get_linewidth())
    for c in fig.findobj(Collection):
        if not drawn(c) or not to_rgba_array(c.get_edgecolor())[:, 3].any():
            continue
        strokes += [float(w) for w in np.atleast_1d(c.get_linewidths()) if w > 0]
    return float(min(fonts)), float(min(strokes))


def _plot_paper(s: dict, stem: str, out_dir: Path, caption_dir: Path) -> list[Path]:
    """Paper mode: the bar panel built at its printed width (PAPER_FIGSIZE_IN, saved tight at
    PAPER_DPI) with PAPER_STYLE sizes in Helvetica, so the LaTeX includes it at 100%.

    The headline title, the whisker note and the footer are not drawn; their exact text goes to
    captions/<stem>.json for the LaTeX \\caption{}, with the print size and the measured smallest
    font and stroke. The in-axes reference-line label is kept. Writes <stem>.png only.
    """
    import matplotlib.pyplot as plt
    from PIL import Image

    with plt.rc_context({"font.family": _paper_font(), "font.size": PAPER_MIN_FONT_PT}):
        fig, ax = plt.subplots(figsize=PAPER_FIGSIZE_IN)
        _draw_bars(ax, s, PAPER_STYLE)
        fig.tight_layout(pad=0.3)
        min_font, min_lw = print_minima(fig)
        if min_font < PAPER_MIN_FONT_PT or min_lw < PAPER_MIN_LINEWIDTH_PT:
            plt.close(fig)
            raise ValueError(f"{stem}: smallest font {min_font} pt / stroke {min_lw} pt is below "
                             f"{PAPER_MIN_FONT_PT} / {PAPER_MIN_LINEWIDTH_PT} pt")
        out = out_dir / f"{stem}.png"
        fig.savefig(out, dpi=PAPER_DPI, bbox_inches="tight", pad_inches=PAPER_PAD_IN)
        plt.close(fig)
    log(f"saved {out}")
    with Image.open(out) as im:
        width_px, height_px = im.size
    width, height = width_px / PAPER_DPI, height_px / PAPER_DPI
    w_lo, w_hi = PAPER_WIDTH_RANGE_IN[PAPER_LAYOUT]
    if not w_lo <= width <= w_hi:
        raise ValueError(f"{stem}: printed width {width:.3f} in is outside {w_lo}-{w_hi} in ({PAPER_LAYOUT})")

    # The texts the default render draws, top to bottom: title, whisker note, footer.
    title_raw = s["title"]
    notes_raw = [WHISKER_NOTE, "\n".join(FOOTER)]
    title_lines = title_raw.split("\n")
    caption = {
        "stem": stem,
        "title": " ".join(title_lines),
        "title_lines": title_lines,
        "subtitle": None,
        "notes": [re.sub(r"\s*\n\s*", " ", n) for n in notes_raw],
        "removed_raw": [title_raw, *notes_raw],
        "layout": PAPER_LAYOUT,
        "print_width_in": round(width, 4),
        "print_height_in": round(height, 4),
        "min_font_pt": min_font,
        "min_linewidth_pt": min_lw,
    }
    caption_dir.mkdir(parents=True, exist_ok=True)
    cap_path = caption_dir / f"{stem}.json"
    cap_path.write_text(json.dumps(caption, indent=2, ensure_ascii=False) + "\n")
    log(f"saved {cap_path} (print {width:.3f} x {height:.3f} in; min font {min_font} pt, min stroke {min_lw} pt)")
    return [out, cap_path]


# ---------------------------------------------------------------------------
# Sidecar + markdown section
# ---------------------------------------------------------------------------

def write_sidecar(s: dict, path: Path = DATA_DIR / f"{STEM}.json",
                  figure: str = f"recode/figures/{STEM}.png", print_spec: dict | None = None) -> Path:
    """print_spec (paper mode): the PRINT_KEYS values from the caption JSON, written after "figure"."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "figure": figure,
        **(print_spec or {}),
        "source_analysis": "recode/src/home_likeness.py (functions imported; four-panel ts_home_likeness)",
        "metric": "per model: mean over its three foreign cross_edit documents of the L1 distance between its cell "
                  "profile (judge + five signed conflict scores) and the equal-weight mean of the home models' profiles",
        "codes": "recode/data/codes/ensemble.jsonl (three-grader majority vote)",
        "notes": {"whiskers": WHISKER_NOTE, "footer": FOOTER},
        **s,
    }
    path.write_text(json.dumps(payload, indent=2) + "\n")
    log(f"saved {path}")
    return path


def markdown_section(s: dict) -> str:
    order = s["order_most_home_like_first"]
    ms = s["models"]
    r = s["reference_line"]
    bs = s["bootstrap"]
    ox = s["opus_excluding_no_csam"]
    opus = hl.NO_CSAM_CELL[0]
    L = [MD_MARKER, "",
         f"Figure: `recode/figures/{STEM}.png` / `.pdf`. Sidecar: `recode/figures/data/{STEM}.json`. "
         f"Code: `recode/src/home_likeness_summary.py` (imports the functions above; does not reimplement them).", "",
         f"**Title (computed, branch `{s['title_branch']}`):** {s['title']}", "",
         "### Definition", "",
         "- **Bar** = the model's average distance from the home family across the three *foreign* documents it "
         "edited in cross_edit (the per-visitor average in the table above, ensemble column). Lower = edits other "
         "providers' documents more like those providers' own models do.",
         f"- **Dashed line** = mean of the home models' leave-one-out distances over all four documents "
         f"({r['n_distances']} distances): {r['value']:.3f} (range {r['range'][0]:.3f}–{r['range'][1]:.3f}; "
         f"bootstrap 95% {r['ci95'][0]:.3f}–{r['ci95'][1]:.3f}). The range is not drawn because a band would span "
         "most of the axis.",
         f"- **Whiskers** = 95% percentile interval from a within-run moving-block bootstrap: each cross_edit run "
         f"(one per model × document; visitor and home runs alike) has its applied, coded edits in round order "
         f"resampled as overlapping contiguous blocks of {bs['block_length']} (starts drawn uniformly with "
         "replacement, concatenated, truncated to the run's original length); cell profiles, home means and each "
         f"model's average distance are recomputed. B = {bs['B']:,}, seed = {bs['seed']} "
         "(`recode/config.yaml` bootstrap.B, seeds.bootstrap).",
         "- **P(most home-like)** = share of bootstrap draws in which the model has the smallest average distance "
         "(ties split evenly). Shown for the top model and any model ≥ 0.05.",
         "- **Title rule:** if the top model's P ≥ 0.95 → \"<Model> Edits Other Providers' Documents Most Like "
         "Their Own Models\"; otherwise the models with P ≥ 0.05 are named (\"<A> and <B> Edit …\"; a single "
         "such model gets \"Likely\").", "",
         "### Numbers", "",
         "| Model | Avg distance | 95% CI | P(most home-like) | Per foreign document |",
         "|---|---:|---|---:|---|"]
    for m in order:
        d = ms[m]
        per = "; ".join(f"{hl.DOC_LABEL[k]} {v:.3f}" for k, v in d["per_document"].items())
        L.append(f"| {m} | {d['avg_distance']:.3f} | {d['ci95'][0]:.3f}–{d['ci95'][1]:.3f} | "
                 f"{d['p_most_home_like']:.3f} | {per} |")
    L += ["", "### Caveats", "",
          "- **Optimistic intervals.** There is one run per (model, document) cell, so the block bootstrap only "
          "captures round-to-round variation within that run. It cannot capture run-to-run variation (a second run "
          "of the same model on the same document would differ by more), so the whiskers are too narrow and "
          "P(most home-like) is overconfident.",
          "- **Intervals sit above the bars.** An L1 distance between noisy means is biased upward: resampling "
          "adds noise to every profile, and noise almost always increases the distance. Bootstrap draws are "
          "therefore centred above the point estimate, and several bars lie near the lower end of their "
          "percentile interval. Models with fewer or noisier edits are penalised more in P(most home-like). "
          "Read the whiskers as a rough gauge of spread, not as bias-corrected intervals.",
          f"- **Opus's OpenAI cell is the stripped Model Spec** (`openai_model_spec_no_csam`). Sensitivity: "
          f"{opus}'s average over its other two foreign documents is {ox['avg_distance']:.3f} "
          f"(vs {ms[opus]['avg_distance']:.3f}); it would rank {ox['rank_if_substituted']} of {len(order)}.",
          "- **Home-like ≠ faithful.** The bar measures editing like the developer's own models, not faithfulness "
          "to the document; home models also drift on their own documents.",
          "- The reference line pools home models compared with the *rest* of their family, while bars compare "
          "visitors with the *full* family. By convexity of L1 this pulls bars down relative to the line, so a bar "
          "above the line is a conservative finding, while a bar at or below it ("
          + ", ".join(m for m in order if ms[m]["avg_distance"] <= r["value"] * 1.05)
          + ") partly reflects this asymmetry (see Caveats above).", "",
          "### Regenerate", "", "```",
          ".venv/bin/python recode/src/home_likeness_summary.py",
          ".venv/bin/python -m pytest recode/tests/test_home_likeness_summary.py -q",
          "```", "",
          "`home_likeness.py` rewrites this file from scratch; rerun `home_likeness_summary.py` afterwards to "
          "restore this section.", ""]
    return "\n".join(L)


def write_markdown(s: dict, path: Path = MD_PATH) -> Path:
    text = path.read_text()
    if MD_MARKER in text:
        head = text[:text.index(MD_MARKER)]
    else:
        head = text if text.endswith("\n\n") else text.rstrip("\n") + "\n\n"
    path.write_text(head + markdown_section(s))
    log(f"saved {path}")
    return path


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Average distance from the home provider, one bar per model.")
    parser.add_argument("--paper", action="store_true",
                        help="render for the AAAI paper: no title/whisker note/footer in the image (they go to "
                             f"{PAPER_CAPTION_DIR.relative_to(ROOT)}/), PNG only, written under "
                             f"{PAPER_FIG_DIR.relative_to(ROOT)}/ and nowhere else")
    args = parser.parse_args(argv)
    B, seed = load_config()
    log("loading frame ...")
    frame = hl.load_frame(hl.CODES_DIR / "ensemble.jsonl")
    hl.verify_layout(frame)
    log(f"frame: {len(frame)} edits; layout verified")
    s = compute_summary(frame, B, seed)
    log(f"title: {s['title']} [{s['title_branch']}]")
    log(f"reference line {s['reference_line']['value']:.3f}")
    for m in s["order_most_home_like_first"]:
        d = s["models"][m]
        log(f"  {m:18s} {d['avg_distance']:.3f}  CI {d['ci95'][0]:.3f}-{d['ci95'][1]:.3f}  "
            f"P={d['p_most_home_like']:.3f}")
    if args.paper:
        _, cap_path = plot(s, out_dir=PAPER_FIG_DIR, paper=True, caption_dir=PAPER_CAPTION_DIR)
        cap = json.loads(cap_path.read_text())
        write_sidecar(s, PAPER_DATA_DIR / f"{STEM}.json",
                      figure=f"{PAPER_FIG_DIR.relative_to(ROOT)}/{STEM}.png",
                      print_spec={k: cap[k] for k in PRINT_KEYS})
        return
    plot(s)
    write_sidecar(s)
    write_markdown(s)


if __name__ == "__main__":
    main()
