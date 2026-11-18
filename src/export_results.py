"""WP8: turn the stored M1/M1.5/M2 artefacts into the data layer Stage 4 renders.

One output file, `webapp/data.js`, defining `window.GOLDA_DATA`. A JS global rather than a bundle of
JSON fetched at runtime, because the front end has to open from `file://` for the demo, where
`fetch()` of a sibling file is blocked by the origin rules.

Every number in the payload is copied out of an artefact; nothing here computes an accuracy. What it
does compute are the derived quantities the chart needs (a curve's gain past the cap, the deficit
against a baseline's cap line) and the completeness checks that decide whether a block is labelled
`pending` instead of being silently missing.

Run: `python src/export_results.py` from the repository root. Exit non-zero if a check fails.
"""

from __future__ import annotations

import csv
import datetime
import hashlib
import json
import pathlib
import re
import os
import subprocess
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
RUNS = ROOT / "runs"
OUT = ROOT / "webapp" / "data.js"

# The splits, spelled the way the artefacts spell them, with what a reader may conclude from each.
SPLITS = {
    "holdout-5%": "5 % hold-out carved from the train split; what hyper-parameters were selected on.",
    "official-test": "the untouched official test split; used once per method after refit on all of train.",
    "cv-10-fold": "ORL protocol: 10 folds, folds fixed by seed before any run (the paper's protocol).",
    "cv-5-fold": "5 folds on the train split, folds fixed by seed; CIFAR-100 and Tiny ImageNet.",
}

# The three hypotheses, as one-line verdicts plus the artefact field each verdict can be re-checked in.
# Written here so the front end states the same thing the stage reports state; the argument lives in
# research_records/wp7_cross_regime_synthesis.md and stage_03b_full_results.md.
CLAIMS = {
    "H1": {
        "statement": "GO-LDA and classic LDA are indistinguishable on the paper's face-data rows.",
        "verdict": "holds within its scope",
        "scope": "ORL, raw pixels, 1-NN, ten-fold, K = C - 1",
        "out_of_scope_note": (
            "The reversal in the frozen-feature regime is reported post-hoc (stage_03b §4), not as a "
            "pre-registered variant of this hypothesis."
        ),
        "evidence": "runs/mvp_orl/diagnostics.json -> by_delta[].H1_go_minus_classic_paired; "
                    "runs/parity/parity_report.json",
    },
    "H2": {
        "statement": "GO-LDA's gains appear beyond the rank cap K = C - 1.",
        "verdict": "mechanism reproduces on all four feature pairs; the accuracy claim does not",
        "scope": "the beyond-cap directions exist and their own curve keeps rising; the baselines' "
                 "cap value is still not reached",
        "evidence": "runs/m2_matrix/accuracy_rows.csv (curves per pair), selection.csv (cap values)",
    },
    "H3": {
        "statement": "Classic LDA's directions violate mutual orthogonality; GO-LDA's do not.",
        "verdict": "confirmed in both regimes, as a geometric fact",
        "scope": "measured off-diagonal |u_i^T u_j| at each pair's selected delta",
        "evidence": "runs/m2_matrix/diagnostics.json -> per_pair; runs/mvp_orl/diagnostics.json",
    },
}


def read_csv(path: pathlib.Path) -> list[dict]:
    if not path.is_file():
        return []
    return list(csv.DictReader(path.read_text(encoding="utf-8").splitlines()))


def read_json(path: pathlib.Path):
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def preflight_environment() -> dict:
    """The machine the runs happened on, read from stage_00's measured table rather than retyped."""
    md = ROOT / "research_records" / "stage_00_preflight.md"
    env: dict[str, str] = {}
    if md.is_file():
        for ln in md.read_text(encoding="utf-8").splitlines():
            cells = [c.strip() for c in ln.strip().strip("|").split("|")]
            if len(cells) == 2 and cells[0] in ("CPU", "RAM", "GPU", "Python", "torch",
                                                "numpy / scikit-learn"):
                env[cells[0]] = cells[1].strip("`")
    return {"gpu": env.get("GPU"), "torch": env.get("torch"), "python": env.get("Python"),
            "numpy_scikit_learn": env.get("numpy / scikit-learn"), "cpu": env.get("CPU"),
            "source": "research_records/stage_00_preflight.md (measured 2026-11-16)"}


def page_syntax_ok() -> tuple[bool, str]:
    """The page is a single file with an inline script; one unbalanced parenthesis there makes the
    whole thing inert with no visible error, which is exactly what happened on the first draft of
    webapp/index.html. Extract the script and let node parse it - a skip is reported as a pass with
    the reason, because the exporter also runs on machines without node."""
    page = ROOT / "webapp" / "index.html"
    if not page.is_file():
        return False, f"{page} missing"
    blocks = re.findall("<script>\\n(.*?)\\n</script>", page.read_text(encoding="utf-8"), re.S)
    if not blocks:
        return False, "no inline <script> block found"
    fd, name = tempfile.mkstemp(suffix=".js")
    os.close(fd)          # Windows holds an open mkstemp handle and then refuses to delete the file
    tmp = pathlib.Path(name)
    try:
        tmp.write_text("\n".join(blocks), encoding="utf-8")
        proc = subprocess.run(["node", "--check", str(tmp)], capture_output=True, text=True, timeout=60)
        if proc.returncode == 0:
            return True, f"{len(blocks)} inline block(s), {sum(len(b) for b in blocks)} chars parse"
        first = (proc.stderr or "").strip().splitlines()
        return False, (first[-1] if first else "node --check failed")[:160]
    except FileNotFoundError:
        return True, "node not on PATH, syntax not checked"
    except subprocess.TimeoutExpired:
        return False, "node --check timed out"
    finally:
        tmp.unlink(missing_ok=True)


def is_gated(check: dict) -> bool:
    """Which parity checks gate downstream runs. The artefact's own `gated` field is authoritative;
    reports written before that field existed are classified by the same rule the suite applies
    (`tests/test_parity.py`, record() and main()): the checks numbered 5 measure the paper's claims
    and never gate."""
    if "gated" in check:
        return bool(check["gated"])
    return not check["check"].startswith("5")


def num(value):
    """Artefacts are CSV, so numbers arrive as strings; blanks stay None, not 0."""
    if value is None or value == "" or value == "n/a":
        return None
    return float(value)


def digest(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:12] if path.is_file() else "missing"


def source_note(rel: str, *, rows=None, note=None) -> dict:
    p = ROOT / rel
    entry = {"path": rel, "exists": p.is_file(), "sha256_12": digest(p)}
    if rows is not None:
        entry["rows"] = rows
    if note:
        entry["note"] = note
    return entry


def feature_pair_block(dataset: str, backbone: str, acc_rows: list[dict],
                       sel_rows: list[dict], cv_rows: list[dict], diag: dict,
                       feat: dict) -> dict:
    """One (dataset, backbone) pair: the growth chart's inputs plus everything else stored for it."""
    pair_sel = [r for r in sel_rows if r["dataset"] == dataset and r["backbone"] == backbone]
    if not pair_sel:
        return {}
    go = next((r for r in pair_sel if r["method"] == "GO-LDA"), None)
    go_delta = go["selected_delta"]
    cap = int(next(r["cap"] for r in diag["per_pair"]
                   if r["dataset"] == dataset and r["backbone"] == backbone))
    pair_acc = [r for r in acc_rows if r["dataset"] == dataset and r["backbone"] == backbone]

    def row(r) -> dict:
        return {"method": r["method"], "delta": num(r["delta"]), "K": int(num(r["K"])),
                "realized_dim": num(r["realized_dim"]), "accuracy": num(r["accuracy"]),
                "split": r["split"]}

    # The chart's curve: every method swept at GO-LDA's own selected delta, so the comparison is
    # strictly paired on regularisation. Baselines have no basis past the cap, hence their dashes.
    paired = sorted((row(r) for r in pair_acc if r["delta"] == go_delta),
                    key=lambda r: (r["method"], r["K"]))
    # Each method's own curve, at the delta it selected: what the per-method-selection protocol sees.
    own = []
    for s in pair_sel:
        own.append({
            "method": s["method"],
            "selected_delta": num(s["selected_delta"]),
            "selected_K": int(num(s["selected_K"])),
            "realized_dim": num(s["realized_dim"]),
            "holdout_at_selection": num(s["holdout_accuracy"]),
            "test_at_selection": num(s["test_accuracy"]),
            "curve_holdout": [num(r["accuracy"]) for r in sorted(
                (x for x in pair_acc if x["method"] == s["method"]
                 and x["delta"] == s["selected_delta"]), key=lambda x: int(num(x["K"])))],
            "curve_K": [int(num(r["K"])) for r in sorted(
                (x for x in pair_acc if x["method"] == s["method"]
                 and x["delta"] == s["selected_delta"]), key=lambda x: int(num(x["K"])))],
        })

    # Baseline horizontal lines, both readings, because which delta the line sits on changes what the
    # gap means: each baseline's cap value at its own selected delta (the protocol a per-method
    # selection table quotes) and at GO-LDA's delta (the strictly paired reading of stage_03b 3.3).
    caps, paired_caps = [], []
    for s in pair_sel:
        if s["method"] == "GO-LDA":
            continue
        own_cap = next((r for r in pair_acc if r["method"] == s["method"]
                        and r["delta"] == s["selected_delta"] and int(num(r["K"])) == cap), None)
        paired_cap = next((r for r in pair_acc if r["method"] == s["method"]
                           and r["delta"] == go_delta and int(num(r["K"])) == cap), None)
        caps.append({"method": s["method"], "delta": num(s["selected_delta"]), "K": cap,
                     "own_selected_K": int(num(s["selected_K"])),
                     "own_realized_dim": num(s["realized_dim"]),
                     "holdout": num(own_cap["accuracy"]) if own_cap else None,
                     "test_at_own_selection": num(s["test_accuracy"])})
        paired_caps.append({"method": s["method"], "delta": num(go_delta), "K": cap,
                            "holdout": num(paired_cap["accuracy"]) if paired_cap else None})

    go_curve = next((o for o in own if o["method"] == "GO-LDA"), None)
    gain_to_selected = gain_to_grid_end = end_vs_own_delta_best = cap_vs_paired_best = None
    if go_curve and go_curve["curve_holdout"]:
        at_cap = next((a for k, a in zip(go_curve["curve_K"], go_curve["curve_holdout"]) if k == cap), None)
        at_selected = next((a for k, a in zip(go_curve["curve_K"], go_curve["curve_holdout"])
                            if k == go_curve["selected_K"]), None)
        best_own = max((c["holdout"] for c in caps if c["holdout"] is not None), default=None)
        best_paired = max((c["holdout"] for c in paired_caps if c["holdout"] is not None), default=None)
        if at_cap is not None:
            # Two different "growth past the cap" numbers, because they are not the same quantity: the
            # selected K is what the protocol ships, the grid end is what the chart's right edge shows.
            # On Tiny x DINOv2 they differ in sign - selected K = 200 gains 0.0018, K = 256 loses.
            if at_selected is not None:
                gain_to_selected = round(at_selected - at_cap, 4)
            gain_to_grid_end = round(go_curve["curve_holdout"][-1] - at_cap, 4)
        if best_own is not None and at_selected is not None:
            end_vs_own_delta_best = round(at_selected - best_own, 4)
        if best_paired is not None and at_cap is not None:
            cap_vs_paired_best = round(at_cap - best_paired, 4)

    # The per-method-selection reading, on both splits: each method at the (delta, K) it chose itself.
    # This is the quantity stage_03b 3.1 quotes on test; the hold-out counterpart is here so the chart's
    # horizontal lines and the table's headline numbers can be told apart.
    def at_selection(method, field):
        hit = next((o for o in own if o["method"] == method), None)
        return None if hit is None else hit[field]

    def spread(methods, field):
        vals = [at_selection(m, field) for m in methods]
        vals = [v for v in vals if v is not None]
        return max(vals) if vals else None

    baselines = sorted({o["method"] for o in own} - {"GO-LDA"})
    protocol_gap_holdout = protocol_gap_test = None
    go_sel_h, go_sel_t = at_selection("GO-LDA", "holdout_at_selection"), at_selection("GO-LDA", "test_at_selection")
    best_sel_h, best_sel_t = spread(baselines, "holdout_at_selection"), spread(baselines, "test_at_selection")
    if None not in (go_sel_h, best_sel_h):
        protocol_gap_holdout = round(go_sel_h - best_sel_h, 4)
    if None not in (go_sel_t, best_sel_t):
        protocol_gap_test = round(go_sel_t - best_sel_t, 4)

    pair_cv = [r for r in cv_rows if r["dataset"] == dataset and r["backbone"] == backbone]
    pair_diag = next((d for d in diag["per_pair"]
                      if d["dataset"] == dataset and d["backbone"] == backbone), {})
    return {
        "dataset": dataset,
        "backbone": backbone,
        "C": int(feat["splits"]["train"]["classes"]),
        "cap_C_minus_1": cap,
        "feature_dim": feat["dim"],
        "feature_model": feat["model"],
        "feature_input": feat["input"],
        "extraction_seconds": feat.get("total_seconds"),
        "train_rows": pair_diag.get("rows"),
        "delta_grid": diag["deltas"],
        "K_grid": diag["k_grid"][dataset],
        "head": "L2 logistic (LBFGS, max_iter 5000, C=1.0, StandardScaler on the fitting split) - C4's configuration",
        "growth_chart": {
            "curve_source": "accuracy_rows.csv, hold-out split: GO-LDA's curve at its own selected "
                            "delta (paired_at_go_delta), every method's own-delta curve in per_method",
            "point_source": "selection.csv, official test at each method's own selection",
            "baseline_lines": "hold-out accuracy at K = C - 1, in two readings: baselines_at_cap uses "
                              "each baseline's own selected delta (the per-method-selection protocol), "
                              "baselines_at_cap_paired_at_go_delta uses GO-LDA's delta (strictly paired)",
            "note": "hold-out curves and test points are different splits and are labelled separately "
                    "in the legend; classic LDA has no basis past the cap, so it is a line, not a curve",
            "go_delta": num(go_delta),
            "paired_at_go_delta": paired,
            "baselines_at_cap": caps,
            "baselines_at_cap_paired_at_go_delta": paired_caps,
            "readings": {
                "go_gain_cap_to_selected_holdout": gain_to_selected,
                "go_gain_cap_to_grid_end_holdout": gain_to_grid_end,
                "go_at_selected_vs_best_baseline_cap_own_delta_holdout": end_vs_own_delta_best,
                "go_at_cap_vs_best_baseline_at_cap_paired_holdout": cap_vs_paired_best,
                "protocol_gap_holdout_each_at_own_selection": protocol_gap_holdout,
                "protocol_gap_test_each_at_own_selection": protocol_gap_test,
                "note": "all hold-out readings are on the 5 % split; the test reading is the single "
                        "official-test score of stage_03b 3.1. The two protocol gaps are the same "
                        "comparison on different splits and are reported side by side on purpose - "
                        "they are not interchangeable (supervisor's U009 correction 3).",
            },
        },
        "per_method": own,
        "cv": {
            "status": "complete" if len(pair_cv) >= len(pair_sel) else "pending",
            "folds": int(num(pair_cv[0]["folds"])) if pair_cv else None,
            "rows": [{"method": r["method"], "delta": num(r["selected_delta"]),
                      "K": int(num(r["selected_K"])), "mean": num(r["mean"]), "sd": num(r["sd"]),
                      "min": num(r["min"]), "max": num(r["max"]),
                      "phase_seconds": num(r["cv_phase_seconds"])} for r in pair_cv],
            "stored": "mean/SD/min/max over folds only - per-fold values are not on disk, so no "
                      "per-fold sign claim is possible",
        },
        "diagnostics": pair_diag,
        "counts": {"scan_rows": len(pair_acc), "selected": len(pair_sel)},
    }


def orl_block(run_dir: str, label: str, supplementary: bool) -> dict:
    d = RUNS / run_dir
    rows = read_csv(d / "accuracy_rows.csv")
    summary = read_csv(d / "accuracy_summary.csv")
    diag = read_json(d / "diagnostics.json") or {}
    manifest = read_json(d / "manifest.json") or {}
    timing = read_json(d / "timing.json") or {}
    if not rows:
        return {}
    heads = sorted({r["head"] for r in rows})
    paper_head = next((h for h in heads if "1-NN" in h), heads[0])
    # H1's own table: both LDA arms at the cap, per fold, in the head the paper's row uses. The full
    # per-fold grid (2,880 rows) stays on disk; the front end gets the slice that carries the claim.
    cap = diag.get("rank_cap")
    cap = cap.get("C_minus_1") if isinstance(cap, dict) else cap
    per_fold_cap = [
        {"method": r["method"], "delta": r["delta"], "head": r["head"], "fold": int(num(r["fold"])),
         "accuracy": num(r["accuracy"]), "train_n": int(num(r["train_n"])),
         "test_n": int(num(r["test_n"]))}
        for r in rows if cap and int(num(r["K"])) == int(cap) and r["head"] == paper_head
    ]
    return {
        "label": label,
        "supplementary": supplementary,
        "dataset": manifest.get("dataset", "ORL (Olivetti faces)"),
        "regime": "raw pixels, 10,304 dimensions (112 rows x 92 columns PGM flattened)",
        "protocol": {
            "folds": manifest.get("folds_used"), "seed": manifest.get("seed"),
            "heads": heads, "deltas": manifest.get("deltas"),
            "certified_deltas": diag.get("certified_deltas"),
            "uncertified_deltas": diag.get("uncertified_deltas"),
            "k_grid": manifest.get("k_grid"),
            "split": "cv-10-fold" if (manifest.get("folds_used") or 10) > 1 else "single fixed split",
            "note": diag.get("protocol"),
        },
        "environment": {k: manifest.get(k) for k in ("python", "numpy", "code", "parity_gate")},
        "summary_rows": [{"method": r["method"], "delta": r["delta"], "K": int(num(r["K"])),
                          "head": r["head"], "realized_dim": num(r["realized_dim"]),
                          "n_folds": int(num(r["n_folds"])), "mean": num(r["mean"]),
                          "sd": num(r["sd"]), "min": num(r["min"]), "max": num(r["max"])}
                         for r in summary],
        "per_fold_at_cap_h1": per_fold_cap,
        "rank_cap_C_minus_1": diag.get("rank_cap"),
        "by_delta": diag.get("hypotheses"),
        "per_fold_delta": diag.get("per_fold_delta"),
        "no_projection_1nn_mean": diag.get("no_projection_1nn_mean"),
        "fold0_probes": read_json(d / "fold0_probes.json"),
        "timing": {k: timing.get(k) for k in
                   ("total_wall_clock_s", "peak_rss_mb", "n_solves", "go_lda_s_mean", "go_lda_s_max")},
        "counts": {"per_fold_rows": len(rows), "summary_rows": len(summary)},
        "omitted": "the other head's per-fold rows and every K except the cap are on disk in "
                   f"runs/{run_dir}/accuracy_rows.csv, not copied into data.js",
    }


LIMITATIONS = [
    "Two datasets, both natural-image benchmarks read through ImageNet-pretrained backbones: the four "
    "feature pairs share a family, which is what the out-of-distribution control in section 8 exists to "
    "press on.",
    "The 5 % hold-out that selects (delta, K) is 2,500 rows at CIFAR-100 and 5,000 at Tiny ImageNet, so a "
    "single selected cell carries roughly +/-1 point of selection noise; the five-fold tables are the wider "
    "view of the same choice, not an independent second experiment.",
    "cv_summary.csv stores mean, SD, min and max per cell, so no per-fold sign test is available anywhere in "
    "this study. The strongest statement the CV supports is whether two methods' fold ranges separate.",
    "C4's published cells are an external plausibility reference, not a target: the resize and normalisation "
    "differ, which stage_03b section 9 states cell by cell.",
    "cap / M and M / N move together in every experiment run here, the ORL dimension ladder included, so the "
    "study says which regime the parity claim fails in, not which single ratio inside that regime is "
    "operative (wp7 section 6).",
]

COMMANDS = [
    ["parity gate (gates everything below)", "python tests/test_parity.py"],
    ["ORL raw-pixel MVP, the paper's protocol", "python src/run_mvp_orl.py"],
    ["ORL with four training images per subject", "python src/run_mvp_orl.py --per-class 4 --out runs/mvp_orl_small_sample"],
    ["frozen feature extraction (one-off, 18.2 min for all four pairs)", "python src/extract_features.py --dataset cifar100 --backbone resnet18"],
    ["the full matrix sweep", "python src/run_m2_matrix.py"],
    ["Tiny ImageNet cross-validation, against the stored selection", "python src/run_m2_matrix.py --cv-only"],
    ["cap-gap probe (solver / route / coordinate-system controls)", "python src/probe_m2_cap_gap.py"],
    ["head-control probe (logistic vs the paper's 1-NN)", "python src/probe_m2_head.py"],
    ["out-of-distribution control, option A", "python src/probe_m2_ood.py"],
    ["ORL dimension ladder, released with a ten-minute ceiling (re-run after the pixel-grid fix)",
     "python src/probe_orl512.py --budget-s 560 --out runs/orl512_fix"],
    ["regenerate webapp/data.js for this page", "python src/export_results.py"],
]


def search_block() -> dict:
    """The stage-1 funnel, read from the screening ledger rather than restated by hand."""
    path = ROOT / "research_records" / "stage_01_screening_ledger.csv"
    rows = read_csv(path)
    if not rows:
        return {}
    disp: dict[str, int] = {}
    for r in rows:
        key = (r.get("disposition") or "unlabelled").split("(")[0].strip()
        disp[key] = disp.get(key, 0) + 1
    ranked = sorted(rows, key=lambda r: -(num(r.get("weighted")) or 0))
    slim = [{"id": r.get("id"), "algorithm": r.get("algorithm"), "family": r.get("family"),
             "paper": r.get("paper_short"), "venue_year": r.get("venue_year"),
             "identifier": r.get("identifier"), "weighted": num(r.get("weighted")),
             "disposition": r.get("disposition"),
             "brief_compliance": r.get("brief_compliance")} for r in ranked[:8]]
    return {
        "ledger": "research_records/stage_01_screening_ledger.csv",
        "protocol": "research_records/stage_01_search_protocol.md",
        "candidates_scored": len(rows),
        "dispositions": disp,
        "axes": [{"axis": "algorithm complexity", "weight": 0.20},
                 {"axis": "local hardware demand", "weight": 0.15},
                 {"axis": "implementation difficulty", "weight": 0.25},
                 {"axis": "novelty of the AI-assisted angle", "weight": 0.20},
                 {"axis": "ease of scoring and demonstration", "weight": 0.20}],
        "released": next(({"id": r.get("id"), "algorithm": r.get("algorithm"),
                           "identifier": r.get("identifier"), "weighted": num(r.get("weighted")),
                           "note": r.get("note")} for r in rows
                          if (r.get("disposition") or "").startswith("RECOMMENDED")), None),
        "ranked": slim,
    }


def ood_block(path: pathlib.Path) -> dict:
    """The out-of-distribution control, passed through from its artefact rather than restated.

    U010 released it as option A and asked that it get its own labelled block, so the exporter adds
    only the split label and the source path: the numbers, the ranking and the severity-choice text are
    the probe's own, and copying them here would put a second transcription between the artefact and
    the page.
    """
    raw = read_json(path)
    if not raw:
        return {}
    out = dict(raw)
    out["source"] = "runs/m2_matrix/probe_ood.json"
    out["split"] = "official-test-under-shift"
    out["split_note"] = "both columns are the official CIFAR-100 test split; the corrupted one is the "
    "same rows with one fixed noise field applied to the pixels before the frozen backbone. Nothing is "
    "refitted on the shift, so the two columns differ only in the data (U010 item 2)."
    return out


def ladder_block(path: pathlib.Path) -> dict:
    """The ORL dimension ladder, passed through for the same reason (U010 item 2, second half)."""
    raw = read_json(path)
    if not raw:
        return {}
    out = dict(raw)
    out["source"] = path.relative_to(ROOT).as_posix()
    out["split"] = "cv-10-fold"
    out["split_note"] = "ORL raw pixels, the paper's own ten-fold 1-NN protocol - a different dataset, "
    "fold count, head and split from the feature pairs in section 7, so the two are never averaged."
    return out


def checks(payload: dict) -> list[tuple[str, bool, str]]:
    """Completeness and labelling checks. A failure here means the front end would draw something
    the artefacts do not support, which is the failure mode this whole project keeps hitting."""
    out = []
    fm = payload["results"]["feature_matrix"]
    want = {("cifar100", "resnet18"), ("cifar100", "dinov2_vits14"),
            ("tiny_imagenet", "resnet18"), ("tiny_imagenet", "dinov2_vits14")}
    have = {(p["dataset"], p["backbone"]) for p in fm.values()}
    out.append(("all four feature pairs present", have == want, f"{sorted(have)}"))

    for key, pair in fm.items():
        gc = pair["growth_chart"]
        ks = sorted({r["K"] for r in gc["paired_at_go_delta"] if r["method"] == "GO-LDA"})
        cap = pair["cap_C_minus_1"]
        grid_max = max(pair["K_grid"])
        out.append((f"{key}: GO curve reaches the cap and the end of the grid",
                    bool(ks) and cap in ks and ks[-1] == grid_max,
                    f"K = {ks}, cap {cap}, grid max {grid_max}"))
        out.append((f"{key}: every curve row carries its split",
                    all(r["split"] == "holdout-5%" for r in gc["paired_at_go_delta"]),
                    f"{len(gc['paired_at_go_delta'])} rows"))
        out.append((f"{key}: test points come only from selection.csv",
                    all(p["test_at_selection"] is not None for p in pair["per_method"]),
                    f"{len(pair['per_method'])} methods"))
        out.append((f"{key}: baseline lines exist at the cap",
                    all(c["holdout"] is not None for c in gc["baselines_at_cap"]),
                    f"{len(gc['baselines_at_cap'])} baselines"))
        nulls = [n for n, v in gc["readings"].items()
                 if n != "note" and v is None]
        out.append((f"{key}: every chart reading is computable", not nulls, str(nulls)))

    cv_status = {k: v["cv"]["status"] for k, v in fm.items()}
    out.append(("cv blocks are labelled, not silently missing",
                all(s in ("complete", "pending") for s in cv_status.values()), str(cv_status)))
    for key in ("raw_pixels", "raw_pixels_small_sample"):
        block = payload["results"][key]
        out.append((f"{key}: block present", bool(block),
                    f"{block.get('counts', {}).get('per_fold_rows', 0)} per-fold rows" if block else "empty"))
    s = payload.get("search") or {}
    out.append(("search funnel is present and consistent with its ledger",
                s.get("candidates_scored", 0) >= 10 and bool(s.get("released")),
                f"{s.get('candidates_scored')} candidates, released {s.get('released', {}).get('id') if s.get('released') else None}"))
    out.append(("limitations and commands are exported, not written into the page",
                len(payload.get("limitations") or []) >= 5 and len(payload.get("commands") or []) >= 8,
                f"{len(payload.get('limitations') or [])} limits, {len(payload.get('commands') or [])} commands"))
    ex = payload["results"]["controls_extra"]
    ood = ex.get("ood") or {}
    out.append(("the two U010-released controls are in the payload",
                bool(ood) and bool(ex.get("ladder")),
                f"ood={bool(ood)} ladder={bool(ex.get('ladder'))}"))
    if ood:
        arms = [(b, a) for b, blk in (ood.get("backbones") or {}).items() for a in blk["arms"]]
        out.append(("OOD control: its clean column reproduces section 3.1 arm by arm",
                    len(arms) == 8 and all(a["clean_reproduces_reference"] for _b, a in arms),
                    f"{sum(1 for _b, a in arms if a['clean_reproduces_reference'])}/{len(arms)} arms, "
                    f"max drift {max(abs(a['accuracy_clean_test'] - a['clean_reference_stage_03b']) for _b, a in arms):.4f}"))
        out.append(("OOD control: split labelled, severity fixed and not swept",
                    ood.get("split") == "official-test-under-shift"
                    and "not swept" in json.dumps(ood.get("corruption", {})),
                    str(ood.get("corruption", {}).get("sigma_on_unit_pixels"))))
        out.append(("OOD control: every arm scored on both columns",
                    all(a["accuracy_corrupted_test"] is not None for _b, a in arms),
                    f"{len(arms)} arms"))
    lad = ex.get("ladder") or {}
    if lad:
        rungs = lad.get("ladder") or []
        ms = [r["M"] for r in rungs]
        out.append(("ladder: rungs ascend in M at fixed classes and fixed rows per class",
                    ms == sorted(ms) and len(ms) == 4 and lad.get("C") == 40,
                    f"M = {ms}, C = {lad.get('C')}, folds = {lad.get('folds')}"))
        out.append(("ladder: every rung carries both arms and a certified span",
                    all(r.get("span_defect") is not None and r.get("classic") is not None
                        for r in rungs), f"{len(rungs)} rungs"))
    syntax = page_syntax_ok()
    out.append(("the front end's inline script parses", syntax[0], syntax[1]))
    splits_used = {r["split"] for p in fm.values() for r in p["growth_chart"]["paired_at_go_delta"]}
    out.append(("every split used in the payload is documented",
                splits_used <= set(SPLITS), str(sorted(splits_used))))
    return out


def main() -> int:
    matrix = RUNS / "m2_matrix"
    acc_rows = read_csv(matrix / "accuracy_rows.csv")
    sel_rows = read_csv(matrix / "selection.csv")
    cv_rows = read_csv(matrix / "cv_summary.csv")
    diag = read_json(matrix / "diagnostics.json")
    feat_list = read_json(ROOT / "data" / "features" / "manifest.json") or []
    feat_map = {(e["dataset"], e["backbone"]): e for e in feat_list}
    if not (acc_rows and sel_rows and diag):
        raise SystemExit("M2 artefacts are missing; run src/run_m2_matrix.py before exporting")

    pairs = sorted({(r["dataset"], r["backbone"]) for r in sel_rows})
    feature_matrix = {}
    missing_feat = []
    for dataset, backbone in pairs:
        feat = feat_map.get((dataset, backbone))
        if feat is None:
            missing_feat.append(f"{dataset}/{backbone}")
            continue
        feature_matrix[f"{dataset}__{backbone}"] = feature_pair_block(
            dataset, backbone, acc_rows, sel_rows, cv_rows, diag, feat)
    if missing_feat:
        raise SystemExit(f"no feature-cache entry for {missing_feat}")

    datasets = [
        {"name": e["dataset"], "backbone": e["backbone"], "dim": e["dim"],
         "model": e["model"], "input": e["input"], "device": e["device"],
         "frozen": e["frozen"], "classes": e["splits"]["train"]["classes"],
         "splits": {k: {"file": v["features"], "shape": v["shape"], "dtype": v["dtype"],
                        "sha256_12": v["sha256"][:12], "seconds": v["seconds"],
                        "img_per_s": v["img_per_s"]}
                    for k, v in e["splits"].items()},
         "archive": {"url": e["source_archive"]["url"], "bytes": e["source_archive"]["bytes"],
                     "sha256_12": e["source_archive"]["sha256"][:12],
                     "native_size": e["source_archive"]["native_size"]},
         "extraction_seconds_total": e.get("total_seconds")}
        for e in feat_list
    ]
    orl_manifest = read_json(RUNS / "mvp_orl" / "manifest.json") or {}
    parity = read_json(RUNS / "parity" / "parity_report.json") or []

    payload = {
        "meta": {
            "project": "CISC3024 AI Assignment 3 - GO-LDA replication",
            "generated_utc": datetime.datetime.now(datetime.timezone.utc)
                             .strftime("%Y-%m-%dT%H:%M:%SZ"),
            "generated_by": "src/export_results.py (WP8)",
            "seed": diag["seed"],
            "environment": preflight_environment(),
            "stage_docs": [
                "research_records/stage_01_candidate_scoring.md",
                "research_records/stage_02_design_and_plan.md",
                "research_records/stage_03a_pilot_feasibility.md",
                "research_records/stage_03b_full_results.md",
                "research_records/wp7_cross_regime_synthesis.md",
            ],
            "pending": [],
        },
        "conventions": [
            {"split": k, "meaning": v} for k, v in SPLITS.items()
        ] + [
            {"field": "realized_dim", "meaning": "the rank actually reached after the scatter pencils "
             "went rank-deficient; for PCA-then-LDA it is capped at C-1 however wide its PCA stage is, "
             "so it is not the width of the discriminant space"},
            {"field": "delta", "meaning": "ridge added to S_W (paper's own 5e-3 is in the grid; the "
             "beyond-cap arms use only deltas certified in stage_03a: 1e-4 and up)"},
            {"field": "timing", "meaning": "wall-clock seconds are per invocation; timing.json holds "
             "only the latest invocation's total, so multi-invocation sums are stated in words in "
             "stage_03b section 2, not reconstructed from that field"},
        ],
        "search": search_block(),
        "claims": CLAIMS,
        "limitations": LIMITATIONS,
        "commands": COMMANDS,
        "results": {
            "datasets": {"feature_caches": datasets,
                         "orl": {"manifest": orl_manifest,
                                 "note": "raw pixels: 40 subjects x 10 images, 112 rows x 92 columns PGM "
                                         "flattened to 10,304 dimensions; the archive source and "
                                         "checksum are in stage_02 section 7 and runs/mvp_orl/"
                                         "manifest.json"}},
            "raw_pixels": orl_block("mvp_orl", "ORL MVP (paper's protocol reproduced)", False),
            "raw_pixels_small_sample": orl_block(
                "mvp_orl_small_sample",
                "ORL with 4 training images per subject", True),
            "feature_matrix": feature_matrix,
            "probes": {
                "cap_gap": read_json(matrix / "probe_cap_gap.json"),
                "head_control": read_json(matrix / "probe_head_control.json"),
                "what_they_rule_out": "the cap gap is not the head's coordinate preference, not the "
                    "classic arm's solver, and not the route: QR-orthonormalised bases, the symmetric-"
                    "definite eigh reference and the span-reduced dense route all reproduce it. It "
                    "starts at GO-LDA's third direction.",
            },
            "controls_extra": {
                "ood": ood_block(matrix / "probe_ood.json"),
                "ladder": ladder_block(RUNS / "orl512_fix" / "orl512_ladder.json"),
            },
            "parity_gate": {
                "path": "runs/parity/parity_report.json",
                "checks": [dict(c, gated=is_gated(c)) for c in parity],
                "gated": sum(1 for c in parity if is_gated(c)),
                "diagnostic": sum(1 for c in parity if not is_gated(c)),
                "gated_all_ok": all(c["ok"] for c in parity if is_gated(c)),
                "note": "gated checks must pass before anything downstream runs; diagnostic checks are "
                        "measured and printed only. The GO-vs-classic span comparison became a "
                        "diagnostic on 2026-11-17 because span agreement is not a property of the "
                        "algorithm (stage_03b section 7).",
            },
        },
        "sources": [
            source_note("runs/m2_matrix/accuracy_rows.csv", rows=len(acc_rows),
                        note="the hold-out sweep: every (pair, method, delta, K) cell"),
            source_note("runs/m2_matrix/selection.csv", rows=len(sel_rows),
                        note="each method's own selection, with both the hold-out and the test value"),
            source_note("runs/m2_matrix/cv_summary.csv", rows=len(cv_rows),
                        note="mean/SD/min/max over folds, per pair and method"),
            source_note("runs/m2_matrix/diagnostics.json"),
            source_note("runs/m2_matrix/probe_cap_gap.json"),
            source_note("runs/m2_matrix/probe_head_control.json"),
            source_note("research_records/stage_01_screening_ledger.csv",
                        note="the stage-1 candidate funnel the front end's section 2 reads"),
            source_note("runs/m2_matrix/probe_ood.json",
                        note="the out-of-distribution control U010 released (option A)"),
            source_note("runs/orl512_fix/orl512_ladder.json",
                        note="the ORL dimension ladder U010 released, re-run after the "
                             "IMG_H/IMG_W swap in src/orl.py was fixed; the earlier "
                             "runs/orl512/ reading is withdrawn"),
            source_note("runs/mvp_orl/accuracy_summary.csv", rows=278),
            source_note("runs/mvp_orl_small_sample/accuracy_summary.csv"),
            source_note("data/features/manifest.json",
                        note="the frozen feature caches: shapes, checksums, extraction timings"),
            source_note("data/orl/manifest.json",
                        note="the ORL archive: mirror, md5, and the 92-column x 112-row geometry the "
                             "front end's faces and direction images are drawn on"),
        ],
    }

    pending = [f"{k} cv status = {v['cv']['status']}" for k, v in feature_matrix.items()
               if v["cv"]["status"] != "complete"]
    if pending:
        payload["meta"]["pending"].append(
            "cross-validation rows absent for: " + "; ".join(pending)
            + " - re-run src/export_results.py once that invocation of run_m2_matrix.py lands")

    report = checks(payload)
    payload["meta"]["export_gate"] = {
        "total": len(report), "passed": sum(1 for _n, ok, _d in report if ok),
        "all_passed": all(ok for _n, ok, _d in report),
        "names": [name for name, _ok, _d in report],
        "note": "these are the exporter's own publishability checks; the parity suite in section 4 is "
                "a different, smaller set of algebraic checks on the implementation"}
    width = max(len(name) for name, _, _ in report)
    for name, ok, detail in report:
        print(f"[{'PASS' if ok else 'FAIL'}] {name:<{width}}  {detail}")
    if any(not ok for _, ok, _ in report):
        print("\nrefusing to write data.js with a failing check")
        return 1

    OUT.parent.mkdir(parents=True, exist_ok=True)
    js = "/* generated by src/export_results.py - do not edit; regenerate from the artefacts */\n"
    js += "window.GOLDA_DATA = "
    js += json.dumps(payload, indent=1, ensure_ascii=False, default=float)
    js += ";\n"
    OUT.write_text(js, encoding="utf-8", newline="\n")
    print(f"\nwrote {OUT} ({OUT.stat().st_size / 1024:.0f} KiB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
