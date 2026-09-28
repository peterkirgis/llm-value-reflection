"""Tests for recode/src/report_figures.py (vendored report generator) and
recode/src/restyle_drift_figures.py (house-style drift figures).

What is proved here:
  1. Runtime guard: nothing can be written into reports/figures (or any other
     read-only tree), via assert_safe_out_dir, render_all, _save, or the
     drift restyler.
  2. Vendoring is faithful: the vendored constants equal reports/generate_figures.py
     (parsed with ast, never imported), and every function/constant not listed
     as a deviation has an identical AST to reports/generate_judge_beneficiary_figures.py.
  3. The adapter builds items in the original schema: on v1.jsonl it reproduces
     results/iterative_edit/judge_beneficiary_coded_gemma.json item-for-item.
  4. Rendering the v1 codes through the vendored generator reproduces the
     ORIGINAL plotted data: the original generator (loaded from its source file
     with a stand-in `generate_figures` module whose _save only captures — it
     never writes) is run on the original coded JSON, and its plotted values
     are compared with the vendored sidecars for 9 figures. For the same
     figures the rendered PNGs are pixel-identical to reports/figures/*.png.
  5. Titles in the committed outputs equal the audited decision table.
"""

from __future__ import annotations

import ast
import json
import math
import sys
import types
from pathlib import Path

import matplotlib
import numpy as np
import pytest

import report_figures as rf
import restyle_drift_figures as rd

REPO = rf.PROJECT_ROOT
ORIG_GEN = REPO / "reports" / "generate_judge_beneficiary_figures.py"
ORIG_BASE = REPO / "reports" / "generate_figures.py"
ORIG_JSON = REPO / "results" / "iterative_edit" / "judge_beneficiary_coded_gemma.json"
REPORT_FIGS = REPO / "reports" / "figures"
V1_CODES = rf.RECODE_ROOT / "data" / "codes" / "v1.jsonl"
FIG_DIR = rf.RECODE_ROOT / "figures"

# figure-function batches rendered in the parity tests (stems in comments)
PARITY_FUNCS = ["judge_drift",          # ts_judge_drift_by_provider
                "judge_cross_edit",     # ts_judge_cross_edit
                "beneficiary_panels",   # ts_beneficiary_panels
                "beneficiary_drift"]    # ts_drift_<code> x6
PARITY_STEMS = (["ts_judge_drift_by_provider", "ts_judge_cross_edit", "ts_beneficiary_panels"]
                + [f"ts_drift_{p['code']}" for p in rf.BENEFICIARY_PANELS])
ALL_STEMS = (["ts_judge_drift_by_provider", "ts_judge_cross_edit",
              "ts_judge_cross_edit_edit_level", "ts_claude_conditions", "ts_beneficiary_panels"]
             + [f"ts_drift_{p['code']}" for p in rf.BENEFICIARY_PANELS]
             + [f"ts_{p['code']}_{m}_edit_level" for p in rf.BENEFICIARY_PANELS
                for m in ("cross_edit", "self")])


def _listing(path: Path):
    return sorted((p.name, p.stat().st_size, p.stat().st_mtime_ns) for p in path.iterdir())


# ---------------------------------------------------------------------------
# 1. runtime guard
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("tree", ["reports/figures", "reports", "docs", "results/iterative_edit",
                                  "experiments", "src/valconv"])
def test_guard_refuses_read_only_trees(tree):
    with pytest.raises(RuntimeError, match="read-only"):
        rf.assert_safe_out_dir(REPO / tree)


def test_guard_allows_recode_figures(tmp_path):
    assert rf.assert_safe_out_dir(FIG_DIR) == FIG_DIR.resolve()
    assert rf.assert_safe_out_dir(tmp_path) == tmp_path.resolve()


def test_render_all_and_save_never_write_reports_figures(monkeypatch):
    before = _listing(REPORT_FIGS)
    items = rf.load_coded(V1_CODES)[:50]
    with pytest.raises(RuntimeError, match="read-only"):
        rf.render_all(items, "v1", out_dir=REPORT_FIGS)
    # even if someone points the module global at reports/figures, _save refuses
    monkeypatch.setattr(rf, "OUT_DIR", REPORT_FIGS)
    fig = matplotlib.pyplot.figure()
    with pytest.raises(RuntimeError, match="read-only"):
        rf._save(fig, "ts_guard_probe")
    matplotlib.pyplot.close(fig)
    with pytest.raises(RuntimeError, match="read-only"):
        rd.render("v1", "constitution", REPORT_FIGS, rd.load_summary("v1"))
    assert _listing(REPORT_FIGS) == before


def test_default_out_dir_is_recode_figures():
    assert rf.OUT_DIR == FIG_DIR
    assert rf.CODED_PATH.name == "ensemble.jsonl"


# ---------------------------------------------------------------------------
# 2. vendoring is faithful
# ---------------------------------------------------------------------------

def _module_ast(path: Path) -> dict:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    nodes = {}
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            nodes[node.name] = node
        elif isinstance(node, ast.Assign) and len(node.targets) == 1 \
                and isinstance(node.targets[0], ast.Name):
            nodes[node.targets[0].id] = node
    return nodes


def test_vendored_constants_equal_generate_figures_source():
    orig = _module_ast(ORIG_BASE)
    for name in ("MODEL_COLORS", "MODEL_ORDER", "FAMILY_TO_MODELS"):
        assert ast.literal_eval(orig[name].value) == getattr(rf, name), name


# functions whose bodies carry a `# RECODE:` deviation (D1, D3, D4, D5)
DEVIATING = {"load_coded", "fig_judge_drift", "fig_judge_cross_edit",
             "fig_judge_cross_edit_edit_level", "_edit_level_measure_fig",
             "fig_claude_conditions", "fig_beneficiary_panels", "_draw_drift_lines",
             "fig_beneficiary_drift", "PROJECT_ROOT", "CODED_PATH"}


def test_non_deviating_code_is_verbatim():
    orig = _module_ast(ORIG_GEN)
    vend = _module_ast(Path(rf.__file__))
    checked = 0
    for name, node in orig.items():
        if name in DEVIATING:
            continue
        assert name in vend, f"{name} missing from vendored module"
        assert ast.dump(node) == ast.dump(vend[name]), f"{name} differs from the original"
        checked += 1
    assert checked >= 25  # constants + helpers + the 4 uncalled figure functions


# ---------------------------------------------------------------------------
# 3. adapter
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def original_items():
    return json.loads(ORIG_JSON.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def v1_items():
    return rf.load_coded(V1_CODES)


def test_adapter_field_set_matches_original_schema(original_items, v1_items):
    orig_keys = {frozenset(i) for i in original_items}
    assert orig_keys == {frozenset(i) for i in v1_items}
    ens = rf.load_coded()
    assert {frozenset(i) for i in ens} == orig_keys
    orig_coding_keys = {frozenset(i["coding"]) for i in original_items}
    assert {frozenset(i["coding"]) for i in ens} == orig_coding_keys
    assert len(ens) == 2582


def test_adapter_reproduces_v1_items_exactly(original_items, v1_items):
    assert len(v1_items) == len(original_items) == 2580
    by_id = {i["id"]: i for i in original_items}
    assert set(by_id) == {i["id"] for i in v1_items}
    for item in v1_items:
        assert item == by_id[item["id"]], item["id"]


# ---------------------------------------------------------------------------
# 4. v1 parity: vendored sidecars == original generator's plotted data
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def v1_render(tmp_path_factory, v1_items):
    out = tmp_path_factory.mktemp("v1_render")
    rf.render_all(v1_items, "v1", out_dir=out, only=PARITY_FUNCS + ["claude_conditions"])
    return out


@pytest.fixture(scope="module")
def original_plotted():
    """Run the ORIGINAL generator's functions on the ORIGINAL coded JSON.

    A stand-in `generate_figures` module supplies the constants and a _save
    that only captures the figure's plotted data — the real
    reports/generate_figures.py is never imported and nothing is written."""
    captured = {}
    fake = types.ModuleType("generate_figures")
    fake.MODEL_COLORS = dict(rf.MODEL_COLORS)
    fake.MODEL_ORDER = list(rf.MODEL_ORDER)
    fake.FAMILY_TO_MODELS = {k: list(v) for k, v in rf.FAMILY_TO_MODELS.items()}

    def capture_save(fig, stem):
        fig.canvas.draw()  # the vendored _save extracts after savefig (drawn)
        captured[stem] = rf.extract_plotted(fig)
        matplotlib.pyplot.close(fig)

    fake._save = capture_save
    saved = sys.modules.get("generate_figures")
    sys.modules["generate_figures"] = fake
    try:
        # compile + exec by hand: importlib's loader would write a .pyc into
        # reports/__pycache__, and reports/ is read-only.
        mod = types.ModuleType("orig_jb_figures")
        mod.__file__ = str(ORIG_GEN)
        exec(compile(ORIG_GEN.read_text(encoding="utf-8"), str(ORIG_GEN), "exec"), mod.__dict__)
        items = mod.load_coded()
        mod.fig_judge_drift(items)
        mod.fig_judge_cross_edit(items)
        mod.fig_beneficiary_panels(items)
        mod.fig_beneficiary_drift(items)
    finally:
        if saved is None:
            sys.modules.pop("generate_figures", None)
        else:
            sys.modules["generate_figures"] = saved
    return captured


def _assert_close(a, b, path="$"):
    if isinstance(a, dict):
        assert isinstance(b, dict) and set(a) == set(b), f"{path}: keys {set(a) ^ set(b)}"
        for k in a:
            _assert_close(a[k], b[k], f"{path}.{k}")
    elif isinstance(a, list):
        assert isinstance(b, list) and len(a) == len(b), f"{path}: length {len(a)} != {len(b)}"
        for i, (x, y) in enumerate(zip(a, b)):
            _assert_close(x, y, f"{path}[{i}]")
    elif isinstance(a, float) or isinstance(b, float):
        assert a is not None and b is not None and math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-9), \
            f"{path}: {a} != {b}"
    else:
        assert a == b, f"{path}: {a!r} != {b!r}"


@pytest.mark.parametrize("stem", PARITY_STEMS)
def test_v1_sidecar_reproduces_original_plotted_data(stem, v1_render, original_plotted):
    sidecar = json.loads((v1_render / "data" / f"{stem}.json").read_text(encoding="utf-8"))
    assert sidecar["codes_label"] == "v1"
    # JSON round-trip the original capture so types compare like-for-like
    original = json.loads(json.dumps(original_plotted[stem]))
    _assert_close(sidecar["plotted"], original)
    # and the plotted data are non-trivial
    axes = sidecar["plotted"]["axes"]
    assert any(ax["lines"] or ax["bars"] for ax in axes)


def test_v1_judge_drift_sidecar_numbers(v1_render):
    """Spot-check against the report's published legend n and a known line end."""
    side = json.loads((v1_render / "data" / "ts_judge_drift_by_provider.json").read_text())
    legends = [t for ax in side["plotted"]["axes"] for t in (ax["legend"] or [])]
    assert "Claude Opus 4.7 (n=14)" in legends and "Grok 4.2 (n=9)" in legends
    lines = {ln["label"]: ln for ax in side["plotted"]["axes"] for ln in ax["lines"]}
    assert lines["Claude Opus 4.7 (n=14)"]["y"][-1] == pytest.approx(60 / 14)
    assert lines["Grok 4.3 (n=9)"]["y"][-1] == pytest.approx(-12.0)


def test_v1_claude_conditions_keeps_original_xlim(v1_render):
    side = json.loads((v1_render / "data" / "ts_claude_conditions.json").read_text())
    assert side["plotted"]["axes"][0]["xlim"] == [-0.2, 0.95]


@pytest.mark.skipif(matplotlib.__version__ != "3.10.8",
                    reason="pixel parity pinned to the report's matplotlib 3.10.8")
@pytest.mark.parametrize("stem", PARITY_STEMS)
def test_v1_png_pixel_identical_to_report(stem, v1_render):
    import matplotlib.image as mimg

    ours = mimg.imread(v1_render / f"{stem}.png")
    theirs = mimg.imread(REPORT_FIGS / f"{stem}.png")
    assert ours.shape == theirs.shape
    assert np.array_equal(ours, theirs)
    assert (v1_render / f"{stem}.pdf").stat().st_size > 0


# ---------------------------------------------------------------------------
# 5. committed outputs: titles, highlights, drift restyle
# ---------------------------------------------------------------------------

def _decisions():
    return rf.load_title_decisions()


@pytest.mark.parametrize("stem", ALL_STEMS)
def test_committed_ts_figures_use_audited_titles(stem):
    side_path = FIG_DIR / "data" / f"{stem}.json"
    assert (FIG_DIR / f"{stem}.png").exists() and (FIG_DIR / f"{stem}.pdf").exists()
    side = json.loads(side_path.read_text(encoding="utf-8"))
    decision = _decisions()[(stem, "ensemble")]
    assert side["codes_label"] == "ensemble"
    assert side["title_used"] == decision["new_title"]
    assert side["verdict"] == decision["verdict"]
    plotted = side["plotted"]
    shown = [plotted["suptitle"]] + [ax["title"] for ax in plotted["axes"]]
    assert decision["new_title"] in shown


def test_committed_highlights_follow_decisions():
    for panel in rf.BENEFICIARY_PANELS:
        stem = f"ts_drift_{panel['code']}"
        side = json.loads((FIG_DIR / "data" / f"{stem}.json").read_text(encoding="utf-8"))
        expected = _decisions()[(stem, "ensemble")].get("highlights", rf.DRIFT_HIGHLIGHTS[panel["code"]])
        assert side["highlights_used"] == expected
        labelled = {t["text"] for t in side["plotted"]["axes"][1]["texts"]}
        assert set(expected) <= labelled


def test_ensemble_judge_drift_supports_kept_title():
    """KEEP verdict sanity: all Claude line ends > 0, all others < 0."""
    side = json.loads((FIG_DIR / "data" / "ts_judge_drift_by_provider.json").read_text())
    ends = {ln["label"].split(" (n=")[0]: ln["y"][-1]
            for ax in side["plotted"]["axes"] for ln in ax["lines"]}
    assert len(ends) == 10
    for model, end in ends.items():
        assert (end > 0) == model.startswith("Claude"), (model, end)


def test_all_decisions_are_rendered():
    for (figure, label) in _decisions():
        stem = figure if figure.startswith("ts_") else f"{figure}_{label}"
        assert (FIG_DIR / f"{stem}.png").exists(), stem


@pytest.mark.parametrize("label", rd.LABELS)
@pytest.mark.parametrize("doc_type", rd.DOC_TYPES)
def test_committed_drift_figures(label, doc_type):
    stem = f"drift_{doc_type}_{label}"
    assert (FIG_DIR / f"{stem}.png").exists() and (FIG_DIR / f"{stem}.pdf").exists()
    side = json.loads((FIG_DIR / "data" / f"{stem}.json").read_text(encoding="utf-8"))
    decision = _decisions()[(f"drift_{doc_type}", label)]
    assert side["title_used"] == decision["new_title"] == side["plotted"]["suptitle"]
    summary = rd.load_summary(label)
    assert side["B"] == summary["B"] == 2000 and side["seed"] == summary["seed"]
    notes = side["plotted"]["fig_texts"]
    assert any("95% cluster-bootstrap percentile interval of the mean" in t for t in notes)
    assert not any("±1 SD" in t for t in notes)
    assert any(rd.STRATUM_TEXT[doc_type] in t and rd.LABEL_TEXT[label] in t for t in notes)
    # four provider panels, lines/bands == committed bootstrap summary
    axes = side["plotted"]["axes"]
    assert [ax["title"] for ax in axes] == list(rf.FAMILY_TO_MODELS)
    for ax, (family, models) in zip(axes, rf.FAMILY_TO_MODELS.items()):
        for line, fill, model in zip(ax["lines"], ax["fills"], models):
            s = summary["models"][model][doc_type]
            assert line["label"] == f"{model} (n={s['K_chains']})"
            assert line["color"] == rf.MODEL_COLORS[model] and line["linewidth"] == 2.4
            assert line["y"] == pytest.approx([0.0] + s["drift"]["point"])
            assert fill["y1"] == pytest.approx([0.0] + s["drift"]["lo"])
            assert fill["y2"] == pytest.approx([0.0] + s["drift"]["hi"])


@pytest.mark.parametrize("doc_type", rd.DOC_TYPES)
def test_unsuffixed_drift_aliases_are_v1(doc_type):
    for ext in ("png", "pdf"):
        alias = (FIG_DIR / f"drift_{doc_type}.{ext}").read_bytes()
        assert alias == (FIG_DIR / f"drift_{doc_type}_v1.{ext}").read_bytes()


def test_drift_title_lookup_is_strict():
    with pytest.raises(KeyError):
        rd.drift_title("constitution", "e2_para1")
    title, verdict = rd.drift_title("system_prompt", "ensemble")
    assert verdict == "CONTRADICTED" and "GPT-5.4" in title


def test_restyle_render_to_tmp(tmp_path):
    written = rd.render("ensemble", "system_prompt", tmp_path, rd.load_summary("ensemble"))
    names = {p.name for p in written}
    assert {"drift_system_prompt_ensemble.png", "drift_system_prompt_ensemble.pdf",
            "drift_system_prompt_ensemble.json"} <= names
