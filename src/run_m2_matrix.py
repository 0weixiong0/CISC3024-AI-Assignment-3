"""M2 / WP6: the frozen-feature experiment matrix (plan section 4).

    python src/run_m2_matrix.py --dataset cifar100 --backbone resnet18
    python src/run_m2_matrix.py                     # every cached (dataset, backbone) pair

Protocol, fixed before the first run and inherited from the sources rather than invented:

* the head is C4's - L2 logistic regression, LBFGS, max_iter 5000, C = 1.0, with a
  StandardScaler fitted on the fitting split only and applied after projection;
* `K` and `delta` are selected on a held-out 5 % of the train split, and the official test
  split is scored once per method with the projection refitted on all of train - the test
  split is never used to choose anything;
* `delta` is restricted to the certified range measured at M1 (delta >= 1e-4), because the
  beyond-cap directions are not trustworthy below it;
* `K` reaches past `C - 1` on every row, which is where H2 lives.

At these feature dimensions (512 and 384) `M` is small and `N` is large, so the dense route
is the cheap and exact one; the span-reduced route is what raw-pixel ORL needed and stays the
default there. The residual certification runs on whichever route is used.

Artefacts land in runs/m2_matrix/: accuracy_rows.csv, selection.csv, cv_summary.csv,
diagnostics.json, timing.json, manifest.json.
"""

from __future__ import annotations

import argparse
import csv
import datetime
import io
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
FEAT = ROOT / "data" / "features"
OUT = ROOT / "runs" / "m2_matrix"
sys.path.insert(0, str(ROOT / "src"))

import baselines as bl                                    # noqa: E402
from golda import (Scatters, classic_lda_pencil, go_lda,  # noqa: E402
                   principal_angle, residual_bound, residuals)

SEED = 20261117
VAL_FRACTION = 0.05
# One id per process, used as the key of this invocation's row in timing.json's ledger: checkpoints
# inside an invocation rewrite that row rather than appending a duplicate.
STARTED_UTC = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
DELTAS = [1e-4, 5e-3, 1e-2, 1e-1]          # certified range only (M1 section 5)
K_GRID = {"cifar100": [10, 50, 99, 100, 128, 256],
          "tiny_imagenet": [20, 100, 199, 200, 256]}
SHRINK_ALPHA = 0.1
METHODS = ("GO-LDA", "classic-ridge-LDA", "classic-shrinkage-LDA", "PCA-then-LDA")


def load_cached(dataset: str, backbone: str) -> dict:
    """Train/test features and labels from the M1.5 cache, checked against its manifest."""
    index = json.loads((FEAT / "manifest.json").read_text(encoding="utf-8"))
    rec = next((e for e in index if e["dataset"] == dataset and e["backbone"] == backbone), None)
    if rec is None:
        raise FileNotFoundError(f"{dataset}/{backbone} is not in {FEAT / 'manifest.json'} - "
                                f"run src/extract_features.py first")
    out = {}
    for split in ("train", "test"):
        s = rec["splits"][split]
        out[split] = np.load(FEAT / s["features"])
        out[split + "_y"] = np.load(FEAT / s["labels"])
        assert out[split].shape == tuple(s["shape"]), (split, out[split].shape, s["shape"])
    return {"rec": rec, **out}


def val_split(X, y, fraction: float, seed: int):
    """One stratified hold-out of the train split, used only for choosing K and delta."""
    rng = np.random.default_rng(seed)
    keep, val = [], []
    for cls in np.unique(y):
        idx = np.where(y == cls)[0]
        idx = rng.permutation(idx)
        n_val = max(1, int(round(fraction * idx.size)))
        val.extend(idx[:n_val])
        keep.extend(idx[n_val:])
    return np.sort(np.asarray(keep)), np.sort(np.asarray(val))


def stratified_folds(y, k: int, seed: int):
    """Deterministic per-class folds over an arbitrary label vector (the ORL splitter is
    dataset-specific; this one is the same idea with a generic input)."""
    rng = np.random.default_rng(seed)
    test_idx = [np.empty(0, dtype=np.int64) for _ in range(k)]
    for cls in np.unique(y):
        idx = rng.permutation(np.where(y == cls)[0])
        for f, part in enumerate(np.array_split(idx, k)):
            test_idx[f] = np.concatenate([test_idx[f], part])
    all_idx = np.arange(y.size)
    folds = []
    for f in range(k):
        ev = np.sort(test_idx[f])
        folds.append((np.setdiff1d(all_idx, ev), ev))
    assert sum(len(ev) for _, ev in folds) == y.size
    return folds


def _sd(a: np.ndarray) -> float:
    return float(a.std(ddof=1)) if a.size > 1 else float("nan")


def fit_shared(X_tr, y_tr):
    """The two delta-independent fits, solved once per split instead of once per delta.

    The crash this is guarding against is silent: `classic_lda_pencil` ignores `delta` when
    `shrinkage` is set, and PCA never sees it, so refitting them inside the delta loop repeats
    work for a bit-identical answer.  Measured, the repetition is cheap rather than expensive -
    the classic pencil is one eigendecomposition sliced, not K of them, so this whole pair costs
    2.6 s on a 47,500 x 512 split and the hoist buys ~8 s per scan.  It is kept because it also
    removes two held copies of the scatter state per delta, and because the timing table is then
    honest about which seconds belong to delta and which do not.
    """
    secs = {}
    t0 = time.perf_counter()
    shrunk = classic_lda_pencil(X_tr, y_tr, shrinkage=SHRINK_ALPHA, route="dense")
    secs["shrunk"] = time.perf_counter() - t0
    t0 = time.perf_counter()
    pc = bl.pca_dirs(X_tr)
    secs["pca"] = time.perf_counter() - t0
    return {"shrunk": shrunk, "pc": pc}, secs


def fit_projections(X_tr, y_tr, delta: float, k_max: int, shared=None):
    """The delta-dependent bases for one split, solved once and sliced per K.

    GO-LDA is solved at the largest K the split's grid needs; its directions are ordered by
    eigenvalue, so a prefix is the same solution the method would return at that K.  The ridge
    pencil takes `k_max` too but stops at C - 1 by construction, which is the point being
    measured.  `shared` carries the delta-independent parts when the caller solves several
    deltas on the same split.
    """
    cache, secs = dict(shared or {}), {}
    t0 = time.perf_counter()
    cache["go"] = go_lda(X_tr, y_tr, K=k_max, delta=delta, route="dense")
    secs["go_lda"] = time.perf_counter() - t0
    t0 = time.perf_counter()
    cache["classic"] = classic_lda_pencil(X_tr, y_tr, delta=delta, route="dense")
    secs["classic"] = time.perf_counter() - t0
    if shared is None:
        extra, extra_secs = fit_shared(X_tr, y_tr)
        cache.update(extra)
        secs.update(extra_secs)
    return cache, secs


def basis_for(method: str, K: int, cap: int, cache: dict, X_tr, y_tr, delta):
    if method == "GO-LDA":
        return cache["go"]["U"][:, :K]
    if method == "classic-ridge-LDA":
        return None if K > cap else cache["classic"]["U"][:, :K]
    if method == "classic-shrinkage-LDA":
        return None if K > cap else cache["shrunk"]["U"][:, :K]
    if method == "PCA-then-LDA":
        pl = bl.pca_then_lda(X_tr, y_tr, K, delta, pc_dirs=cache["pc"])
        return pl["U"]
    if method == "no-projection":
        return None
    raise ValueError(method)


def logistic_score(basis, X_fit, y_fit, X_eval, y_eval):
    """C4's head on the projected space; basis None means the unprojected features."""
    P_fit = X_fit if basis is None else X_fit @ basis
    P_eval = X_eval if basis is None else X_eval @ basis
    predict = bl.logistic_head(P_fit, y_fit)
    return float(np.mean(predict(P_eval) == y_eval)), P_fit.shape[1]


def fit_cv_cache(X_tr, y_tr, delta, items, shared=None):
    """Only the bases the methods in `items` actually read, for one (fold, delta).

    `fit_projections` solves every arm because the hold-out sweep needs every arm; in CV a group
    can be methods that never look at the deflated pencil, and one unwanted GO-LDA solve at the
    grid's maximum K costs more than the folds it is being wasted inside.  Measured on the first
    CV pass, that waste was most of its time: CIFAR-100 x ResNet-18 spent 2,003 s, of which the
    groups needing only the ridge pencil, the shrinkage arm or PCA accounted for the larger part.
    The answer is unchanged - GO-LDA's directions are ordered by eigenvalue, so a prefix is what
    the method would have returned - which is the same argument the sweep already relies on.
    """
    cache, secs = dict(shared or {}), {}
    go_ks = [K for m, K in items if m == "GO-LDA"]
    if go_ks:
        t0 = time.perf_counter()
        cache["go"] = go_lda(X_tr, y_tr, K=max(go_ks), delta=delta, route="dense")
        secs["go_lda"] = time.perf_counter() - t0
    if any(m == "classic-ridge-LDA" for m, _ in items):
        t0 = time.perf_counter()
        cache["classic"] = classic_lda_pencil(X_tr, y_tr, delta=delta, route="dense")
        secs["classic"] = time.perf_counter() - t0
    if shared is None and any(m in ("classic-shrinkage-LDA", "PCA-then-LDA")
                              for m, _ in items):
        extra, extra_secs = fit_shared(X_tr, y_tr)
        cache.update(extra)
        secs.update(extra_secs)
    return cache, secs


def calibrate(loaded, dataset, backbone):
    """Time one of everything this sweep needs, so its size is chosen on measurements.

    The logistic head is refitted per (method, delta, K) cell, so a single fit's cost times
    the number of cells is the whole run; that is the number worth knowing before starting,
    not after.
    """
    X_tr, y_tr = loaded["train"], loaded["train_y"]
    C = int(len(np.unique(y_tr)))
    cap = C - 1
    dim = loaded["rec"]["dim"]
    fit_idx, val_idx = val_split(X_tr, y_tr, VAL_FRACTION, SEED)
    X_fit, y_fit = X_tr[fit_idx], y_tr[fit_idx]
    X_val, y_val = X_tr[val_idx], y_tr[val_idx]
    out = {"dataset": dataset, "backbone": backbone, "rows_fit": int(X_fit.shape[0]),
           "rows_val": int(X_val.shape[0]), "dim": dim, "cap": cap, "cells": {}}
    for rows in (5000, X_fit.shape[0]):
        Xs, ys = X_fit[:rows], y_fit[:rows]
        t0 = time.perf_counter()
        go = go_lda(Xs, ys, K=min(2 * cap, dim), delta=5e-3, route="dense")
        t_go = time.perf_counter() - t0
        out["cells"][f"solve_rows_{rows}"] = {"seconds": t_go, "K": int(go["U"].shape[1])}
        print(f"  solve {go['U'].shape[1]} directions on {rows} rows: {t_go:.1f} s", flush=True)
    for K in (cap, 50, dim):
        if K > dim:
            continue
        P = X_fit[:, :K]
        t0 = time.perf_counter()
        predict = bl.logistic_head(P, y_fit)
        t_fit = time.perf_counter() - t0
        acc = float(np.mean(predict(X_val[:, :K]) == y_val))
        out["cells"][f"logistic_dim_{K}"] = {"seconds": t_fit, "holdout_accuracy": acc}
        print(f"  logistic fit at dim {K}: {t_fit:.1f} s, holdout {acc:.4f}", flush=True)
    n_cells = len(DELTAS) * len(K_GRID[dataset]) * 4
    per_fit = np.mean([v["seconds"] for k, v in out["cells"].items()
                       if k.startswith("logistic_dim")])
    out["projected_head_seconds"] = n_cells * per_fit
    out["projected_total_hours"] = out["projected_head_seconds"] / 3600
    print(f"  {n_cells} head fits at ~{per_fit:.1f} s = "
          f"{out['projected_head_seconds'] / 3600:.2f} h of head time alone", flush=True)
    return out


def merge_existing(path: Path, key_fields: tuple[str, ...], running: list[tuple], payload):
    """Keep the rows of pairs that are not being rewritten by this run.

    M2 is sized so that it runs one dataset at a time (the two datasets need different cross-
    validation budgets), and each invocation would otherwise overwrite the other's table. Rows are
    matched on dataset and backbone, never on the fields a re-run is meant to refresh.
    """
    if not path.exists():
        return payload
    if path.suffix == ".json":
        old = json.loads(path.read_text(encoding="utf-8"))
        keep = [e for e in old.get(key_fields[0], [])
                if (e.get("dataset"), e.get("backbone")) not in running]
        merged = dict(old)
        merged[key_fields[0]] = keep + payload[key_fields[0]]
        return merged
    keep = [r for r in csv.DictReader(path.open(encoding="utf-8"))
            if (r["dataset"], r["backbone"]) not in running]
    return keep + payload


def write_artefacts(out: Path, running, agg, args, pairs, t_start: float, stage: str,
                    mode: str = "full"):
    """Rewrite every artefact from the in-memory tables at each checkpoint.

    The first M2 attempt threw away 26 min of solves by crashing in its last phase, when only
    the end-of-run writer had ever touched the disk.  `merge_existing` keys on
    (dataset, backbone), so re-writing mid-pair replaces that pair's rows instead of
    duplicating them, and the in-memory `agg` lists are never replaced by the merged result.

    A table this invocation holds no rows for is left alone rather than rewritten.  That is not
    decoration: merging drops every stored row of a pair it is replacing, so a `--cv-only` pass -
    which computes no scan, selection or diagnostic rows at all - would otherwise delete the scan
    whose fold spread it is adding.
    """
    total_s = time.perf_counter() - t_start
    touched = {k: any((r["dataset"], r["backbone"]) in running for r in v)
               for k, v in agg.items()}
    written = {}
    for name, key in (("rows", "accuracy_rows.csv"), ("sel_rows", "selection.csv"),
                      ("cv_rows", "cv_summary.csv")):
        if not touched[name]:
            continue
        payload = merge_existing(out / key, ("dataset", "backbone"), running, agg[name])
        (out / key).write_text(_csv(payload), encoding="utf-8", newline="")
        written[name] = len(payload)
    if touched["diag"]:
        diag = merge_existing(out / "diagnostics.json", ("per_pair",), running,
                              {"per_pair": agg["diag"]})["per_pair"]
        (out / "diagnostics.json").write_text(_dumps(
            {"per_pair": diag, "seed": SEED, "val_fraction": VAL_FRACTION, "deltas": DELTAS,
             "k_grid": K_GRID, "shrinkage_alpha": SHRINK_ALPHA,
             "delta_rule": "certified range from M1: delta >= 1e-4 only, so every beyond-cap row "
                           "is a row whose numerics were checked"}, indent=2), encoding="utf-8")
    # timing.json is the one ledger every invocation writes, including a --cv-only pass that writes no
    # per-fit rows at all: the wall-clock question "what did M2 cost" is answered per invocation, so an
    # invocation that leaves no trace in this file is the bug that made section 2 of stage_03b necessary.
    timing_path = out / "timing.json"
    stored = json.loads(timing_path.read_text(encoding="utf-8")) if timing_path.is_file() else {}
    per_fit = (merge_existing(timing_path, ("per_fit",), running,
                              {"per_fit": agg["timings"]})["per_fit"]
               if touched["timings"] else stored.get("per_fit", []))
    ledger = [e for e in stored.get("invocations_completed", []) if e.get("id") != STARTED_UTC]
    if "invocations_completed" not in stored and "total_wall_clock_s" in stored:
        # The first two invocations wrote a single total under the old schema. Carry that reading
        # forward instead of letting the new file pretend the sweep never happened.
        ledger.append({"id": "pre-ledger", "mode": "sweep, invocation unknown",
                       "wall_clock_s": round(stored["total_wall_clock_s"], 3),
                       "provenance": "carried over from timing.json's total_wall_clock_s, which the "
                                     "pre-ledger driver wrote once per invocation (it recorded the "
                                     "Tiny ImageNet sweep; the CIFAR-100 figure is in its stdout)"})
    ledger.append({"id": STARTED_UTC, "mode": mode, "cv_folds": args.cv,
                   "pairs": [list(p) for p in pairs],
                   "wall_clock_s": round(total_s, 3), "tables_written": dict(written)})
    ledger.sort(key=lambda e: e["id"])
    timing_path.write_text(_dumps({
        "per_fit": per_fit,
        "wall_clock_convention": "no field here is a total for the whole of M2. Each invocation appends "
                                 "to invocations_completed with its own wall_clock_s; sum them (or read "
                                 "the driver stdouts in invocation_logs) for a whole-matrix figure. The "
                                 "crashed first attempt is wasted compute and is counted separately, in "
                                 "stage_03b section 2.",
        "invocation_logs": {"sweep cifar100": "runs/m2_cifar_stdout.txt",
                            "sweep tiny_imagenet": "runs/m2_tiny_stdout.txt",
                            "cv-only tiny_imagenet": "runs/m2_tiny_cv_stdout.txt"},
        "invocations_completed": ledger,
        "total_wall_clock_s_this_invocation": round(total_s, 3),
    }, indent=2), encoding="utf-8")
    (out / "manifest.json").write_text(_dumps({
        "stage": "M2 / WP6 frozen-feature matrix", "seed": SEED, "mode": mode,
        "pairs": list(pairs), "cv_folds_for_these_pairs": args.cv,
        "calibration": "runs/m2_matrix/calibration.json",
        "route": "dense (M = 512 or 384, N >> M): the span-reduced route is exact but solves a "
                 "deflated pencil sequentially, which costs K eigendecompositions of an M x M "
                 "pencil either way, so at these dimensions dense has no numerical downside",
        "head": "L2 logistic regression, LBFGS, max_iter=5000, C=1.0, StandardScaler fitted on "
                "the fitting split only (C4's configuration)",
        "selection": f"5 % stratified hold-out of train (seed {SEED}); official test split used "
                     "once per method after refitting on all of train",
        "feature_cache": str(FEAT / "manifest.json"), "deltas": DELTAS, "k_grid": K_GRID,
        "tables_written_this_invocation": written,
        "total_wall_clock_s_this_invocation": total_s}, indent=2), encoding="utf-8")
    (out / "progress.json").write_text(_dumps(
        {"stage": stage, "mode": mode, "elapsed_s": round(total_s, 1),
         "rows_in_memory": {k: len(v) for k, v in agg.items()},
         "pairs_this_invocation": [list(p) for p in pairs], "cv_folds": args.cv},
        indent=2), encoding="utf-8")
    return total_s


def best_from_selection(out: Path, dataset: str, backbone: str) -> dict:
    """Rebuild each method's selected (delta, K, hold-out) from a finished run.

    `--cv-only` needs exactly this and nothing else from the scan, and the scan is the expensive
    part: re-deriving two fold schedules' worth of selection by re-solving 45,000-row pencils
    would cost more than the cross-validation it is there to add.
    """
    path = out / "selection.csv"
    if not path.exists():
        raise SystemExit(f"--cv-only needs {path}; run the full sweep first")
    best = {}
    for r in csv.DictReader(path.open(encoding="utf-8")):
        if (r["dataset"], r["backbone"]) != (dataset, backbone):
            continue
        best[r["method"]] = (float(r["selected_delta"]), int(r["selected_K"]),
                             float(r["holdout_accuracy"]))
    if not best:
        raise SystemExit(f"no stored selection for {dataset}/{backbone} in {path}")
    return best


def main(argv=None):
    ap = argparse.ArgumentParser(description="frozen-feature experiment matrix (WP6)")
    ap.add_argument("--dataset", default=None, choices=["cifar100", "tiny_imagenet"])
    ap.add_argument("--backbone", default=None,
                    choices=["resnet18", "dinov2_vits14"])
    ap.add_argument("--out", type=str, default=str(OUT))
    ap.add_argument("--calibrate", action="store_true",
                    help="time the solve and the head, print the projected cost, run nothing else")
    ap.add_argument("--cv", type=int, default=0,
                    help="also run this many stratified CV folds on train for each method's "
                         "selected configuration (the plan's +/- across folds); 0 skips it")
    ap.add_argument("--smoke", type=int, default=0,
                    help="subsample each split to this many rows per class and still run every "
                         "phase - selection, full-train refit, CV and the artefact writers. The "
                         "first M2 attempt died in a phase no smoke run had ever reached, so this "
                         "is the cheap way to reach it; its numbers are not reportable.")
    ap.add_argument("--cv-only", action="store_true",
                    help="skip the hold-out sweep and the full-train refit and cross-validate the "
                         "configurations already in selection.csv. Adds the fold spread to pairs "
                         "that were swept with --cv 0 without paying for the sweep twice.")
    args = ap.parse_args(argv)
    if args.cv_only and not args.cv:
        raise SystemExit("--cv-only asks for cross-validation but --cv 0 declines to run it")
    if args.cv == 1:
        raise SystemExit("--cv 1 leaves every row in the evaluation fold and nothing to fit on; "
                         "use --cv 0 to skip cross-validation or at least 2 folds")
    mode = "cv-only" if args.cv_only else "full"

    index = json.loads((FEAT / "manifest.json").read_text(encoding="utf-8"))
    pairs = [(e["dataset"], e["backbone"]) for e in index
             if (args.dataset is None or e["dataset"] == args.dataset)
             and (args.backbone is None or e["backbone"] == args.backbone)]
    if not pairs:
        raise SystemExit(f"no cached pair matches {args.dataset}/{args.backbone}")
    if args.calibrate:
        report = []
        for dataset, backbone in pairs:
            loaded = load_cached(dataset, backbone)
            report.append(calibrate(loaded, dataset, backbone))
        out = Path(args.out)
        out.mkdir(parents=True, exist_ok=True)
        (out / "calibration.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"calibration written to {out / 'calibration.json'}")
        return 0

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    agg = {"rows": [], "sel_rows": [], "cv_rows": [], "diag": [], "timings": []}
    rows, sel_rows, cv_rows, diag, timings = (agg["rows"], agg["sel_rows"], agg["cv_rows"],
                                              agg["diag"], agg["timings"])
    running = list(pairs)
    t_start = time.perf_counter()
    for dataset, backbone in pairs:
        loaded = load_cached(dataset, backbone)
        rec = loaded["rec"]
        X_tr_all, y_tr_all = loaded["train"], loaded["train_y"]
        X_te, y_te = loaded["test"], loaded["test_y"]
        C = int(len(np.unique(y_tr_all)))
        cap = C - 1
        k_grid = [k for k in K_GRID[dataset] if k <= min(rec["dim"], X_tr_all.shape[0] - 1)]
        print(f"{dataset}/{backbone}: train {X_tr_all.shape}, test {X_te.shape}, "
              f"C={C}, cap={cap}, K={k_grid}, dim={rec['dim']}", flush=True)
        if cap not in k_grid:
            k_grid = sorted(set(k_grid) | {cap})
        fit_idx, val_idx = val_split(X_tr_all, y_tr_all, VAL_FRACTION, SEED)
        X_fit, y_fit = X_tr_all[fit_idx], y_tr_all[fit_idx]
        X_val, y_val = X_tr_all[val_idx], y_tr_all[val_idx]

        best = best_from_selection(out, dataset, backbone) if args.cv_only else {}
        scan_deltas = () if args.cv_only else DELTAS
        if args.cv_only:
            print(f"{dataset}/{backbone}: CV-only against the stored selection - "
                  f"{sorted(best)} at {sorted({(d, k) for d, k, _ in best.values()})}",
                  flush=True)
        # None rather than an empty dict: fit_projections reads shared as "no cache", so the
        # shrinkage arm and PCA are solved per delta - which is what the CV arms need, since
        # classic-shrinkage-LDA and PCA-then-LDA both read them out of the same cache.
        shared_fit, shared_secs = (None, {}) if args.cv_only else fit_shared(X_fit, y_fit)
        if shared_secs:
            print(f"  delta-independent fits on the hold-out split: "
                  f"{sum(shared_secs.values()):.1f} s, once for all four deltas", flush=True)
        for delta in scan_deltas:
            t0 = time.perf_counter()
            cache, secs = fit_projections(X_fit, y_fit, delta, max(k_grid), shared=shared_fit)
            for K in k_grid:
                for method in ("GO-LDA", "classic-ridge-LDA", "classic-shrinkage-LDA",
                               "PCA-then-LDA"):
                    basis = basis_for(method, K, cap, cache, X_fit, y_fit, delta)
                    if basis is None and method != "no-projection":
                        continue
                    va, dim_eval = logistic_score(basis, X_fit, y_fit, X_val, y_val)
                    rows.append({"dataset": dataset, "backbone": backbone, "method": method,
                                 "delta": delta, "K": K, "realized_dim": dim_eval,
                                 "split": "holdout-5%", "accuracy": va})
                    # (delta, K, holdout): the selection is a triple, and reading the first two
                    # off a nested pair hands a tuple to the solver where a scalar belongs
                    if va > best.get(method, (None, None, -np.inf))[2]:
                        best[method] = (delta, K, va)
            # the no-projection reference has no K and no delta: one row per dataset/backbone
            if delta == DELTAS[0]:
                va, dim_eval = logistic_score(None, X_fit, y_fit, X_val, y_val)
                rows.append({"dataset": dataset, "backbone": backbone,
                             "method": "no-projection", "delta": "n/a", "K": rec["dim"],
                             "realized_dim": dim_eval, "split": "holdout-5%", "accuracy": va})
            timings.append({"dataset": dataset, "backbone": backbone, "delta": delta,
                            "mode": "holdout-scan", "fit_split_rows": int(X_fit.shape[0]),
                            "solve_seconds": secs, "shared_solve_seconds_solved_once": shared_secs,
                            "delta_wall_clock_s": time.perf_counter() - t0})
            print(f"  delta={delta:g}: ridge + deflated pencils in {sum(secs.values()):.1f} s; "
                  f"cumulative {time.perf_counter() - t_start:.0f} s", flush=True)
            write_artefacts(out, running, agg, args, pairs, t_start,
                            f"hold-out scan {dataset}/{backbone} delta={delta:g}", mode)

        # score the selected configuration on the official test split, refitted on all of train.
        # One refit per selected delta, not per method, because several methods pick the same one.
        # The solve is as long as the longest selected K, not as long as the grid: after selection
        # the shorter directions are not read, and each one costs a full pencil decomposition.
        # Under --cv-only this whole phase is already on disk, and re-running it to learn nothing
        # would cost about as much as the cross-validation being added.
        refit_items = [] if args.cv_only else sorted(best.items())
        if refit_items:
            need = max(K for _, K, _ in best.values())
            shared_all, shared_all_secs = (fit_shared(X_tr_all, y_tr_all)
                                           if len({d for d, _, _ in best.values()}) > 1
                                           else (None, {}))
        full_cache: dict[float, tuple[dict, dict]] = {}
        for method, (delta, K, holdout) in refit_items:
            if delta not in full_cache:
                t0 = time.perf_counter()
                full_cache[delta] = fit_projections(X_tr_all, y_tr_all, delta, need,
                                                    shared=shared_all)
                full_cache[delta][1]["wall_clock_s"] = time.perf_counter() - t0
            full, secs_full = full_cache[delta]
            basis = basis_for(method, K, cap, full, X_tr_all, y_tr_all, delta)
            te, dim_eval = logistic_score(basis, X_tr_all, y_tr_all, X_te, y_te)
            sel_rows.append({"dataset": dataset, "backbone": backbone, "method": method,
                             "selected_delta": delta, "selected_K": K,
                             "realized_dim": dim_eval,
                             "holdout_accuracy": holdout,
                             "test_accuracy": te})
            res = residuals(full["go"]) if method == "GO-LDA" else None
            if res is not None:
                tol, kappa = residual_bound(full["go"]["A_r"])
                diag.append({"dataset": dataset, "backbone": backbone, "delta": delta,
                             "K_max": int(full["go"]["U"].shape[1]), "cap": cap,
                             "rows": int(X_tr_all.shape[0]),
                             "go_offdiag": full["go"]["max_pairwise_abs_cos"],
                             "classic_offdiag": full["classic"]["max_pairwise_abs_cos"],
                             "shrunk_offdiag": full["shrunk"]["max_pairwise_abs_cos"],
                             "span_at_cap_deg": principal_angle(
                                 full["go"]["U"][:, :cap], full["classic"]["U"][:, :cap]),
                             "residual_rel_max": float(res["relative"].max()),
                             "residual_tol": tol, "kappa": kappa,
                             "residual_within_bound": bool(float(res["relative"].max()) < tol),
                             "fisher_monotone": bool(np.all(np.diff(full["go"]["fisher"]) <= 1e-9)),
                             "mu_at_cap": float(full["go"]["mu"][cap - 1]),
                             "mu_beyond_cap_first_three":
                                 [float(v) for v in full["go"]["mu"][cap:cap + 3]]})
            timings.append({"dataset": dataset, "backbone": backbone, "mode": "full-train-refit",
                            "method": method, "delta": delta, "K": K,
                            "solve_seconds": secs_full})
            print(f"  test {method}: delta={delta:g} K={K} dim={dim_eval} -> {te:.4f}",
                  flush=True)

        write_artefacts(out, running, agg, args, pairs, t_start,
                        f"test-split scoring {dataset}/{backbone}", mode)

        # Fold outer, delta inner: one solve per (fold, delta) serves every method that picked that
        # delta, and fit_cv_cache solves only the arms that group actually reads - a group of
        # ridge / shrinkage / PCA-then-LDA has no reason to pay for a deflated pencil.
        if args.cv:
            by_delta: dict[float, list] = {}
            for method, (delta, K, holdout) in best.items():
                by_delta.setdefault(delta, []).append((method, K))
            accs = {m: [] for m in best}
            t_cv = time.perf_counter()
            for f, (tr, ev) in enumerate(stratified_folds(y_tr_all, args.cv, SEED)):
                X_f, y_f, X_e, y_e = X_tr_all[tr], y_tr_all[tr], X_tr_all[ev], y_tr_all[ev]
                shared_cv, _ = (fit_shared(X_f, y_f)
                                if len(by_delta) > 1 and len(best) > 1 else (None, {}))
                for delta, items in sorted(by_delta.items()):
                    cache = fit_cv_cache(X_f, y_f, delta, items, shared=shared_cv)[0]
                    for method, K in items:
                        basis = basis_for(method, K, cap, cache, X_f, y_f, delta)
                        if basis is None and method != "no-projection":
                            continue
                        accs[method].append(logistic_score(basis, X_f, y_f, X_e, y_e)[0])
                print(f"  cv fold {f + 1}/{args.cv}: {time.perf_counter() - t_cv:.0f} s "
                      f"cumulative", flush=True)
                write_artefacts(out, running, agg, args, pairs, t_start,
                                f"cross-validation {dataset}/{backbone} fold {f + 1}", mode)
            for method, (delta, K, holdout) in sorted(best.items()):
                a = np.asarray(accs[method])
                if a.size == 0:
                    continue
                cv_rows.append({"dataset": dataset, "backbone": backbone, "method": method,
                                "selected_delta": delta, "selected_K": K,
                                "folds": int(a.size), "mean": float(a.mean()),
                                "sd": _sd(a), "min": float(a.min()), "max": float(a.max()),
                                "cv_phase_seconds": time.perf_counter() - t_cv})
                print(f"  cv {method}: {a.mean():.4f} +/- {_sd(a):.4f} over {a.size} folds",
                      flush=True)

    total_s = write_artefacts(out, running, agg, args, pairs, t_start, "final", mode)
    print(f"\n{len(agg['rows'])} rows, {len(agg['sel_rows'])} selected cells in {total_s:.0f} s "
          f"-> {out}")
    return 0


def _dumps(obj, indent=None) -> str:
    """numpy scalars reach the JSON writers through the diagnostics, and a failure here would
    cost the run its artefacts rather than its numbers."""
    return json.dumps(obj, indent=indent, default=float)


def _csv(rows) -> str:
    if not rows:
        return ""
    cols: list[str] = []
    for r in rows:
        for k in r:
            if k not in cols:
                cols.append(k)
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=cols, extrasaction="ignore")
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue()


if __name__ == "__main__":
    raise SystemExit(main())
