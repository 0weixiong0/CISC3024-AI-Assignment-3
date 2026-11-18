"""Is the feature-regime reversal about the representation, or about how much of the space the cap takes?

WP7 section 5 ends with an admission: across the three regimes already measured, `rows per class`,
`cap / M` and `M / N` all changed **together**, so nothing on disk separates

  (a) the rank cap occupying a fifth to a half of the space instead of a fifth of one percent,
  (b) fewer rows than dimensions (an ill-conditioned pencil) versus many more,
  (c) deep features versus raw pixels.

Supervisor's U010 releases this control to break the collinearity, and one image-size knob does all
three at once: take ORL's pixels, keep the 40 classes, the ten folds, the 1-NN head and delta = 5e-3
fixed, and box-average the image down through a ladder of dimensions. Each rung moves cap/M (7.6 % to
49 %, which brackets the feature regime's 19-52 %) and, past M = 360, flips M/N from "more dimensions
than rows" to "more rows than dimensions" - while rows per class stays at 9 and the representation
stays the same photograph of the same 40 people.

Reading the result, before it exists:

* if the GO-versus-classic agreement at the cap survives down to cap/M ~ 49 % and only breaks when
  M < N, the reversal is about **conditioning of the pencil**, and WP7's framing becomes quantitative;
* if it breaks while M is still above N, it is the **ratio**;
* if it never breaks anywhere on this ladder, then neither variable is sufficient on its own and the
  difference is (c), the representation itself - which is the honest thing to say, because then no
  experiment on ORL could have shown it.

Two guards, both learned the hard way in this project:

* the angle is reported with its `1 - sv_min` defect, because a span of ~1.5e-6 degrees is the
  numerical floor (sqrt-eps quantum), not a measurement of agreement - and this suite has already
  produced one scare where a fold's floor value collided digit-for-digit with an unrelated check's;
* a wall-clock budget stops at a rung boundary and reports what completed. Rungs are solved cheapest
  first so a timeout costs the least informative point, not the most.

    python src/probe_orl512.py --budget-s 600
    python src/probe_orl512.py --grids 10x8

Artefact: runs/orl512/orl512_ladder.json
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import baselines as bl                      # noqa: E402
import orl                                  # noqa: E402
from golda import classic_lda_pencil, go_lda, principal_angle   # noqa: E402

OUT = ROOT / "runs" / "orl512"
SEED = 20261117            # the seed every other run in this project uses
FOLDS = 10                 # the paper's protocol, and stage_03a's
DELTA = 5e-3               # the paper's own suggested ridge, also GO-LDA's pick on 3 of 4 feature pairs
SHRINK_ALPHA = 0.1         # the M2 grid's shrinkage arm, unchanged
# Width x height, cheapest last: 80 -> 156 -> 256 -> 512 dimensions.
GRIDS = "10x8,13x12,16x16,32x16"


def downsample(X: np.ndarray, width: int, height: int) -> np.ndarray:
    """Box-average each flattened 10,304-pixel vector down to width x height pixels.

    PIL's BOX filter averages every source pixel contributing to a target pixel exactly once, which
    is a fixed linear map - label-blind, class-blind and identical for every fold and method, so it
    cannot leak test information into the projection any more than taking a subset of pixels could.
    Values stay on the loader's 0..255 scale.
    """
    n = X.shape[0]
    img = np.rint(X.reshape(n, orl.IMG_H, orl.IMG_W)).astype(np.uint8)
    out = np.empty((n, width * height), dtype=np.float64)
    for i in range(n):
        small = Image.fromarray(img[i], mode="L").resize((width, height), Image.BOX)
        out[i] = np.asarray(small, dtype=np.float64).ravel()
    return out


def knn_accuracy(basis, X_tr, y_tr, X_te, y_te) -> tuple[float, int]:
    P_tr = X_tr if basis is None else X_tr @ basis
    P_te = X_te if basis is None else X_te @ basis
    pred = bl.knn_predict(P_tr, y_tr, P_te, k=1)
    return float(np.mean(pred == y_te)), P_tr.shape[1]


def span_defect(A: np.ndarray, B: np.ndarray) -> tuple[float, float]:
    """(largest principal angle in degrees, 1 - smallest singular value of Q_A^T Q_B).

    The second number is what makes the first interpretable: agreement at the level of
    `1 - sv_min ~ 1e-16` is a sqrt-eps floor, and reading the angle alone has already produced a
    false alarm in this project when two unrelated comparisons landed on the same floor quantum.
    """
    qa = np.linalg.qr(np.asarray(A, dtype=np.float64))[0]
    qb = np.linalg.qr(np.asarray(B, dtype=np.float64))[0]
    s = np.linalg.svd(qa.T @ qb, compute_uv=False)
    return principal_angle(A, B), float(1.0 - s.min())


def one_rung(Xr: np.ndarray, y: np.ndarray, folds, cap: int, budget_left: float,
             log) -> tuple[dict, bool]:
    """Ten folds at one dimension; returns the rung's block and whether the budget is spent."""
    per_fold, stopped = [], False
    t_rung = time.perf_counter()
    for f, (tr, te) in enumerate(folds, start=1):
        go = go_lda(Xr[tr], y[tr], K=cap, delta=DELTA, route="dense")
        classic = classic_lda_pencil(Xr[tr], y[tr], delta=DELTA, route="dense")
        shrunk = classic_lda_pencil(Xr[tr], y[tr], shrinkage=SHRINK_ALPHA, route="dense")
        pl = bl.pca_then_lda(Xr[tr], y[tr], cap, DELTA, pc_dirs=bl.pca_dirs(Xr[tr]))
        arms = {"GO-LDA": go["U"][:, :cap], "classic-ridge-LDA": classic["U"][:, :cap],
                "classic-shrinkage-LDA": shrunk["U"][:, :cap], "PCA-then-LDA": pl["U"],
                "no-projection": None}
        row = {"fold": f - 1}
        for name, basis in arms.items():
            row[name] = knn_accuracy(basis, Xr[tr], y[tr], Xr[te], y[te])[0]
        row["go_minus_classic"] = row["GO-LDA"] - row["classic-ridge-LDA"]
        row["span_go_vs_classic_deg"], row["defect_go_vs_classic"] = span_defect(
            arms["GO-LDA"], arms["classic-ridge-LDA"])
        # a pair that genuinely differs, measured on the same fold, so the floor has a scale beside it
        row["span_go_vs_shrunk_deg"], row["defect_go_vs_shrunk"] = span_defect(
            arms["GO-LDA"], arms["classic-shrinkage-LDA"])
        per_fold.append(row)
        log(f"    fold {f}/{len(folds)}: GO {row['GO-LDA']:.4f}  classic {row['classic-ridge-LDA']:.4f}"
            f"  diff {row['go_minus_classic']:+.4f}  span {row['span_go_vs_classic_deg']:.3e} deg "
            f"(defect {row['defect_go_vs_classic']:.2e}; control pair "
            f"{row['span_go_vs_shrunk_deg']:.1f} deg)  {time.perf_counter() - t_rung:.0f} s")
        if time.perf_counter() - t_rung > budget_left and f < len(folds):
            stopped = True
            log(f"    budget spent after fold {f} of this rung; stopping here")
            break

    def summary(key: str) -> dict:
        vals = np.array([r[key] for r in per_fold], dtype=np.float64)
        return {"mean": round(float(vals.mean()), 6), "sd": round(float(vals.std(ddof=1)), 6),
                "min": round(float(vals.min()), 6), "max": round(float(vals.max()), 6)}

    diffs = np.array([r["go_minus_classic"] for r in per_fold], dtype=np.float64)
    defects = np.array([r["defect_go_vs_classic"] for r in per_fold], dtype=np.float64)
    return {
        "per_fold": per_fold,
        "folds_completed": len(per_fold),
        "arms_at_cap": {
            k: summary(k) for k in ("GO-LDA", "classic-ridge-LDA", "classic-shrinkage-LDA",
                                    "PCA-then-LDA", "no-projection")},
        "paired_go_minus_classic": summary("go_minus_classic"),
        "folds_go_ahead": int(np.sum(diffs > 0)),
        "folds_classic_ahead": int(np.sum(diffs < 0)),
        "folds_tied": int(np.sum(diffs == 0)),
        "span_go_vs_classic_deg": summary("span_go_vs_classic_deg"),
        "defect_go_vs_classic": {"mean": float(defects.mean()), "max": float(defects.max()),
                                 "floor_scale": float(np.finfo(np.float64).eps * 8)},
        "span_go_vs_shrunk_deg": summary("span_go_vs_shrunk_deg"),
        "rung_seconds": round(time.perf_counter() - t_rung, 1),
        "stopped_by_budget": stopped,
    }, stopped


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--budget-s", type=float, default=600.0,
                    help="stop after the current fold once this much wall clock has been spent")
    ap.add_argument("--folds", type=int, default=FOLDS)
    ap.add_argument("--grids", type=str, default=GRIDS, help="comma-separated WxH list")
    ap.add_argument("--out", type=str, default=str(OUT))
    args = ap.parse_args(argv)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    def log(msg: str) -> None:
        print(msg, flush=True)

    t0 = time.perf_counter()
    X, y = orl.load_orl()
    cap, n_train = orl.N_CLASSES - 1, int(round((args.folds - 1) / args.folds * orl.N_TOTAL))
    log(f"ORL: N = {X.shape[0]}, M_full = {X.shape[1]}, C = {orl.N_CLASSES}, cap = {cap}, "
        f"folds = {args.folds}, delta = {DELTA}, head = 1-NN, seed = {SEED}")
    log(f"reference at full 10,304 dimensions (stage_03a section 4): both arms 0.9850 at the cap, "
        f"paired difference 0.0000 on 10/10 folds, span ~2e-6 deg")

    rungs, stopped = [], False
    for spec in args.grids.split(","):
        width, height = (int(v) for v in spec.lower().split("x"))
        m = width * height
        if m <= cap:
            raise SystemExit(f"{spec}: M = {m} cannot hold {cap} discriminant directions")
        Xr = downsample(X, width, height)
        log(f"  rung M = {m} ({width} x {height}): cap/M = {100.0 * cap / m:.1f} %, "
            f"M/N_train = {m / n_train:.2f}, rows/class at fit = {n_train // orl.N_CLASSES}")
        block, stopped = one_rung(Xr, y, orl.stratified_k_fold(y, args.folds, SEED), cap,
                                  args.budget_s - (time.perf_counter() - t0), log)
        block["rung"] = {"width": width, "height": height, "M": m,
                         "cap_over_M": round(cap / m, 4), "M_over_N_train": round(m / n_train, 3),
                         "rows_per_class_at_fit": n_train // orl.N_CLASSES}
        rungs.append(block)
        log(f"  rung M = {m}: paired GO-classic {block['paired_go_minus_classic']['mean']:+.5f} "
            f"({block['folds_go_ahead']} ahead / {block['folds_classic_ahead']} behind / "
            f"{block['folds_tied']} tied), span {block['span_go_vs_classic_deg']['mean']:.3e} deg, "
            f"{block['rung_seconds']:.0f} s")
        if stopped:
            break
        if time.perf_counter() - t0 > args.budget_s:
            log("  budget spent between rungs; stopping")
            break

    payload = {
        "question": "which of cap/M, M/N and the representation decides whether GO-LDA agrees with "
                    "classic LDA at the rank cap (WP7 section 5 confound)",
        "released_by": "supervisor U010, item 2 (ORL at reduced pixel dimension, same C and folds)",
        "dim_rule": f"ORL PGM {orl.IMG_W} columns x {orl.IMG_H} rows flattened (M = {X.shape[1]}) box-averaged "
                    f"(PIL Image.BOX) to each rung's W x H; a fixed linear, label-blind map applied "
                    f"identically to every method, fold and split",
        "delta": DELTA, "shrinkage_alpha": SHRINK_ALPHA, "head": "1-NN exact (paper's Table II protocol)",
        "folds": args.folds, "seed": SEED, "cap": cap, "C": orl.N_CLASSES,
        "n_train_per_fold": n_train, "route": "dense",
        "budget_s": args.budget_s, "wall_clock_s": round(time.perf_counter() - t0, 1),
        "stopped_early": stopped,
        "rungs": rungs,
        "ladder": [{"M": b["rung"]["M"], "cap_over_M": b["rung"]["cap_over_M"],
                    "M_over_N_train": b["rung"]["M_over_N_train"],
                    "go": b["arms_at_cap"]["GO-LDA"]["mean"],
                    "classic": b["arms_at_cap"]["classic-ridge-LDA"]["mean"],
                    "shrunk": b["arms_at_cap"]["classic-shrinkage-LDA"]["mean"],
                    "pca": b["arms_at_cap"]["PCA-then-LDA"]["mean"],
                    "no_proj": b["arms_at_cap"]["no-projection"]["mean"],
                    "paired_diff": b["paired_go_minus_classic"]["mean"],
                    "span_deg": b["span_go_vs_classic_deg"]["mean"],
                    "span_defect": b["defect_go_vs_classic"]["mean"],
                    "control_span_deg": b["span_go_vs_shrunk_deg"]["mean"]} for b in rungs],
        "feature_regime_reference": {
            "cap_over_M": [0.193, 0.258, 0.389, 0.518],
            "paired_gap_at_cap_holdout": -0.0656,
            "paired_gap_at_cap_test": -0.0654,
            "span_deg_at_cap": 89.8,
            "source": "runs/m2_matrix/accuracy_rows.csv (delta pinned for both arms), "
                      "probe_cap_gap.json, probe_head_control.json"},
        "full_dimension_reference": {
            "M": int(X.shape[1]), "cap_over_M": round(cap / X.shape[1], 6),
            "go_at_cap": 0.985, "classic_at_cap": 0.985, "paired_difference": 0.0,
            "span_deg": "1.5e-6 to 2.1e-6",
            "source": "runs/mvp_orl/diagnostics.json, stage_03a section 4 (quoted, not recomputed)"},
    }
    (out / "orl512_ladder.json").write_text(json.dumps(payload, indent=2, default=float),
                                            encoding="utf-8")
    log(f"\nladder: {json.dumps(payload['ladder'], indent=2)}")
    log(f"wrote {out / 'orl512_ladder.json'} in {payload['wall_clock_s']:.0f} s "
        f"({'stopped by budget' if stopped else 'all rungs completed'})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
