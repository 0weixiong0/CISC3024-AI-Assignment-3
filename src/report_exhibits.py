"""The report's four tables and nine figures: what each says, where it sits, and what cites it.

Project : CISC3024 AI Assignment #3 (Pattern Recognition, University of Macau)
Author  : AI-generated implementation (Qoder). The student wrote no code.

Tables are built from the same run artefacts the prose quotes, so a re-run moves the table with it. Figures
are the rendered assets in `report_assets/`, whose manifest records the page or the fit behind each one; the
caption line here is the manifest line, kept in one place so the two cannot drift.

Placement is by H2: an exhibit is emitted after the last paragraph of the heading it is anchored to, which is
the heading whose prose cites it. `PLACEMENT` is the order the reader meets them in, and the SEQ fields in the
captions number themselves from that order.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUNS = ROOT / "runs"
ASSETS = ROOT / "report_assets"

NAMES = {"cifar100": "CIFAR-100", "tiny_imagenet": "Tiny ImageNet"}
BACK = {"resnet18": "ResNet-18", "dinov2_vits14": "DINOv2 ViT-S/14"}
PAIRS = [("cifar100", "resnet18"), ("cifar100", "dinov2_vits14"),
         ("tiny_imagenet", "resnet18"), ("tiny_imagenet", "dinov2_vits14")]
# Split sizes come from the loader that built the feature caches (src/extract_features.py:101 and :150),
# which is the only place the two numbers are written down.
SPLITS = {"cifar100": (50_000, 10_000), "tiny_imagenet": (100_000, 10_000)}

ARMS = ["GO-LDA", "classic-ridge-LDA", "classic-shrinkage-LDA", "PCA-then-LDA"]
SHORT = {"GO-LDA": "GO-LDA", "classic-ridge-LDA": "ridge LDA",
         "classic-shrinkage-LDA": "shrinkage LDA", "PCA-then-LDA": "PCA-then-LDA"}


def _csv(rel: str) -> list[dict]:
    return list(csv.DictReader((RUNS / rel).open(encoding="utf-8")))


def _json(rel: str) -> dict:
    return json.loads((RUNS / rel).read_text(encoding="utf-8"))


def _pair_name(pair) -> str:
    return f"{NAMES[pair[0]]} x {BACK[pair[1]]}"


def _grid(values) -> str:
    return ", ".join(f"{v:g}" for v in values)


def _pt(delta: float, nd: int = 2) -> str:
    return f"{100 * delta:+.{nd}f}"


# --------------------------------------------------------------------------- tables
def build_settings() -> tuple[list[str], list[list[str]]]:
    """One row per fitted regime: the data, the head, and the grids the hold-out searched."""
    dg = _json("m2_matrix/diagnostics.json")
    mvp = _json("mvp_orl/diagnostics.json")
    dims = {b["backbone"]: b["feature_dim"]
            for b in _json("m2_matrix/probe_ood.json")["backbones"].values()}
    per_pair = {p["dataset"] + p["backbone"]: p for p in dg["per_pair"]}
    header = ["Regime", "Data", "Fit rows", "Classes / cap", "Feature dim", "Head",
              "delta grid", "K grid"]
    rows = [["Raw pixels", "ORL (AT&T faces), 400 images", "360 per fold (9 per class), 40 test",
             f"40 / {mvp['rank_cap']}", "10,304", "1-NN, the paper's face-data head",
             _grid(mvp["deltas"]), _grid(mvp["k_grid"])] ]
    for pair in PAIRS:
        p = per_pair[pair[0] + pair[1]]
        rows.append(["Frozen features", _pair_name(pair), f"{SPLITS[pair[0]][0]:,} train ({100 * dg['val_fraction']:.0f} per cent held out for "
                     f"selection), {SPLITS[pair[0]][1]:,} test",
                     f"{p['cap'] + 1} / {p['cap']}", str(dims[pair[1]]),
                     "L2 logistic (LBFGS, max_iter 5000, C = 1.0) on standardised features",
                     _grid(dg["deltas"]), _grid(dg["k_grid"][pair[0]])])
    return header, rows


def build_results() -> tuple[list[str], list[list[str]]]:
    """Official test accuracy at each method's own selection, with the five-fold spread beside it."""
    sel = {(r["dataset"], r["backbone"], r["method"]): r for r in _csv("m2_matrix/selection.csv")}
    cv = {(r["dataset"], r["backbone"], r["method"]): r for r in _csv("m2_matrix/cv_summary.csv")}
    header = ["Pair", "Method", "Selected delta / K", "Test accuracy", "Five-fold mean +/- SD",
              "Fold range", "Separated from GO-LDA?"]
    rows = []
    for pair in PAIRS:
        go = cv[(*pair, "GO-LDA")]
        for arm in ARMS:
            s, c = sel[(*pair, arm)], cv[(*pair, arm)]
            if arm == "GO-LDA":
                verdict = "reference"
            else:
                verdict = ("yes - its worst fold beats GO-LDA's best"
                           if float(c["min"]) > float(go["max"]) else "no - the ranges overlap")
            rows.append([_pair_name(pair), SHORT[arm],
                         f"{float(s['selected_delta']):g} / {s['selected_K']} (dim {s['realized_dim']})",
                         f"{float(s['test_accuracy']):.4f}",
                         f"{float(c['mean']):.4f} +/- {float(c['sd']):.4f}",
                         f"{float(c['min']):.4f} - {float(c['max']):.4f}", verdict])
    return header, rows


def build_corruption() -> tuple[list[str], list[list[str]]]:
    """The fixed Gaussian corruption re-scored with the clean-fitted arms; nothing refitted."""
    ood = _json("m2_matrix/probe_ood.json")
    sigma = ood["corruption"]["sigma_on_unit_pixels"]
    header = [f"Backbone (sigma = {sigma:g})", "Row", "Clean test", "Corrupted test",
              "Change", "Selected delta / K"]
    rows = []
    for key in ("resnet18", "dinov2_vits14"):
        block = ood["backbones"][key]
        for arm in block["arms"]:
            rows.append([BACK[key], f"{SHORT[arm['method']]} (dim {arm['realized_dim']})",
                         f"{arm['accuracy_clean_test']:.4f}", f"{arm['accuracy_corrupted_test']:.4f}",
                         f"{_pt(arm['drop'])} pts",
                         f"{float(arm['delta']):g} / {arm['K']}"])
        d = block["go_minus_best_baseline"]
        rows.append([BACK[key],
                     "GO-LDA minus best baseline (" + SHORT[d['best_baseline_clean']] + " clean, "
                     + SHORT[d['best_baseline_corrupted']] + " corrupted)",
                     f"{100 * d['clean']:+.2f} pts", f"{100 * d['corrupted']:+.2f} pts",
                     f"{100 * (d['corrupted'] - d['clean']):+.2f} pts", "deficit, not accuracy"])
    return header, rows


def build_ladder() -> tuple[list[str], list[list[str]]]:
    """ORL at reduced pixel dimension: classes and rows per class fixed, M shrunk fourfold."""
    lad = _json("orl512_fix/orl512_ladder.json")
    header = ["Raster", "Feature dim M", "Cap share of M", "GO-LDA", "Ridge LDA",
              "Paired difference in points", "Subspace angle in degrees"]
    rows = []
    for r in lad["ladder"]:
        rung = next(x for x in lad["rungs"] if x["rung"]["M"] == r["M"])["rung"]
        rows.append([f"{rung['width']} x {rung['height']}", f"{r['M']:,}",
                     f"{100 * r['cap_over_M']:.1f} per cent", f"{r['go']:.4f}", f"{r['classic']:.4f}",
                     _pt(r["paired_diff"]), f"{r['span_deg']:.1f}"])
    return header, rows


# --------------------------------------------------------------------------- figures
def _manifest() -> dict:
    return json.loads((ASSETS / "figure_manifest.json").read_text(encoding="utf-8"))


# --------------------------------------------------------------------------- registry
def build_screening() -> tuple[list[str], list[list[str]]]:
    """The screening ledger as kept: every candidate, the gates it did not clear, its score, its fate.

    The ledger records PASS, PARTIAL, FAIL and UNKNOWN per gate, and those four are not the same finding: a
    PARTIAL means the evidence was reached but not completely, and an UNKNOWN means the date could not be read
    at all. Collapsing them into "failed" would misstate the record, so each verdict is carried through.
    """
    rows_in = list(csv.DictReader(
        (ROOT / "research_records" / "stage_01_screening_ledger.csv").open(encoding="utf-8")))
    names = {"g1_recency": "recency", "g2_image_task": "image task", "g3_recoverable": "full text",
             "g4_local_feasible": "local cost", "g5_browser_demo": "demo"}
    header = ["ID", "Algorithm", "Family", "Published", "Weighted score of 5",
              "Gates not cleared", "Disposition"]
    rows = []
    for r in rows_in:
        uncleared = [f"{label}: {r[key]}" for key, label in names.items()
                     if r[key].strip().upper() != "PASS"]
        outcome = "all five cleared" if not uncleared else "; ".join(uncleared)
        disposition = (r["disposition"].replace("RECOMMENDED (primary)", "selected as the primary")
                       .replace("RECOMMENDED", "selected").replace("REJECTED on", "rejected")
                       .replace("SHORTLIST", "runner-up"))
        for code, label in (("G1", "recency"), ("G2", "image task"), ("G3", "full text"),
                            ("G4", "local cost"), ("G5", "demo")):
            disposition = disposition.replace(code, label)
        rows.append([r["id"], r["algorithm"], r["family"], r["venue_year"], r["weighted"], outcome,
                    disposition])
    return header, rows


# key -> (caption above the table, builder). Captions name the artefact the rows were read from, so a reader
# can re-derive any cell.
TABLES = {
    "screening": ("The screening ledger as kept: all twenty candidates, any gate each one did not clear "
                  "(PASS, PARTIAL, FAIL and UNKNOWN are different findings and are not collapsed), the "
                  "weighted score, and the disposition. Source: "
                  "research_records/stage_01_screening_ledger.csv.", build_screening),
    "settings": ("Experiment settings for the two regimes: the data each arm was fitted on, its head, and "
                 "the grids the hold-out searched. Sources: runs/mvp_orl/diagnostics.json and "
                 "runs/m2_matrix/diagnostics.json.", build_settings),
    "results": ("Official test accuracy at each method's own selected (delta, K), beside the five-fold "
                "spread of the same configuration, with the fold-range verdict against GO-LDA. Sources: "
                "runs/m2_matrix/selection.csv and runs/m2_matrix/cv_summary.csv.", build_results),
    "corruption": ("The first control: one fixed additive Gaussian corruption on the test images, with the "
                   "projections, scalers and heads fitted on clean data and re-scored without refitting. "
                   "Source: runs/m2_matrix/probe_ood.json.", build_corruption),
    "ladder": ("The second control: classes and rows per class held fixed while the pixel dimension "
               "shrinks, over ten folds at each rung. Source: runs/orl512_fix/orl512_ladder.json.",
               build_ladder),
}

# key -> asset name. The caption line is read from report_assets/figure_manifest.json, which is what the
# renderer wrote when it drew the picture, so the two cannot drift apart.
FIGURES = {
    "c4_paper": "figure_05", "c4_readme": "figure_06", "eq37": "figure_01", "table2": "figure_03",
    "claim": "figure_02", "directions": "figure_09", "growth": "figure_08", "gaussian": "figure_04",
    "sigma_code": "figure_07",
}

# (H1, H2) -> exhibit keys, in the order the reader meets them. Each anchor is the heading whose prose cites
# the exhibit, and the exhibit is emitted after that heading's last paragraph.
PLACEMENT: list[tuple[tuple[str, str], list[str]]] = [
    (("AI-Assisted Literature Search and Algorithm Selection",
      "What was searched, and how the candidates were screened"), ["screening"]),
    (("Algorithm Description and Task Adaptation", "GO-LDA's deflated eigensolve"), ["eq37"]),
    (("Algorithm Description and Task Adaptation", "Baselines and the protocol adapted to this study"),
     ["table2"]),
    (("Algorithm Description and Task Adaptation", "Hypotheses fixed before implementation"), ["claim"]),
    (("Experimental Settings, Results and Discussion", "Datasets, features and the evaluation protocol"),
     ["settings", "c4_paper", "c4_readme"]),
    (("Experimental Settings, Results and Discussion", "Small-scale feasibility run"), ["directions"]),
    (("Experimental Settings, Results and Discussion", "Main results and the hypothesis verdicts"),
     ["growth", "results"]),
    (("Experimental Settings, Results and Discussion",
      "Two controls: fixed corruption and reduced pixel dimension"),
     ["gaussian", "sigma_code", "corruption", "ladder"]),
]


def figure_asset(key: str) -> Path:
    return ASSETS / f"{FIGURES[key]}.png"


def figure_caption(key: str) -> str:
    return _manifest()[FIGURES[key]]["caption_line_2"]
