"""M1 / WP5: the raw-pixel ORL MVP experiment (plan section 4).

    python src/run_mvp_orl.py                          # the full grid
    python src/run_mvp_orl.py --folds 3 --delta 5e-3   # a smoke run, same code path

Everything the Stage-3 feasibility report states is produced here rather than retyped:
the accuracy table, the fold-to-fold spread, the paired GO-LDA vs classic-LDA comparison
that H1 and H2 are judged on, the diagnostics H3 is judged on, and the measured wall-clock
and peak memory.  The classifier is fixed per regime (1-NN here, the paper's head) and
nothing is chosen on the test fold.

Artefacts land in runs/mvp_orl/: accuracy_rows.csv, accuracy_summary.csv,
diagnostics.json, timing.json, manifest.json.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import platform
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import baselines as bl                                    # noqa: E402
from golda import (Scatters, classic_lda_pencil, go_lda,  # noqa: E402
                   principal_angle, residual_bound, residuals)
from orl import (IMG_H, IMG_W, M, fixed_split_per_subject,  # noqa: E402
                 load_orl, stratified_k_fold)

SEED = 20261117
N_FOLDS = 10
DELTAS = [0.0, 1e-6, 1e-4, 5e-3, 1e-2, 1e-1]
K_GRID = [1, 5, 10, 20, 30, 39, 40, 50]          # 39 = C - 1, the cap; 40 and 50 cross it
SHRINK_ALPHA = 0.1                               # the second regulariser, never a parity reference
OUT = ROOT / "runs" / "mvp_orl"


def peak_rss_bytes() -> int:
    """Peak resident size of this process (the plan's budget claim is measured, not asserted)."""
    if sys.platform == "win32":
        import ctypes
        from ctypes import wintypes

        class Counter(ctypes.Structure):
            _fields_ = [("cb", wintypes.DWORD),
                        ("PageFaultCount", wintypes.DWORD),
                        ("PeakWorkingSetSize", ctypes.c_size_t),
                        ("WorkingSetSize", ctypes.c_size_t),
                        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                        ("QuotaPagedPoolUsage", ctypes.c_size_t),
                        ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                        ("PagefileUsage", ctypes.c_size_t),
                        ("PeakPagefileUsage", ctypes.c_size_t)]

        # the pseudo-handle must survive as a pointer-sized value, and the API needs its
        # signature declared - without both, GetLastError is 6 (invalid handle) and the
        # struct stays zero, which is how this function first reported 0 MB
        fn = ctypes.windll.kernel32.K32GetProcessMemoryInfo
        fn.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counter), wintypes.DWORD]
        fn.restype = ctypes.c_bool
        counters = Counter()
        counters.cb = ctypes.sizeof(Counter)
        fn(ctypes.c_void_p(-1), ctypes.byref(counters), counters.cb)
        return int(counters.PeakWorkingSetSize)
    import resource                                     # Unix only
    return int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024)


def solve_fold(X_tr, y_tr, delta):
    """Every projection this experiment needs from one training fold at one delta.

    GO-LDA is solved once at the largest K in the grid: its directions are sequential, so
    U[:, :K] is exactly the K-direction solution and the grid costs one eigensolve chain
    per (fold, delta) rather than one per cell.  The two classic pencils each need one
    decomposition, and the PCA directions are computed once and sliced.
    """
    secs = {}
    t0 = time.perf_counter()
    go = go_lda(X_tr, y_tr, K=max(K_GRID), delta=delta, route="reduced")
    secs["go_lda"] = time.perf_counter() - t0
    t0 = time.perf_counter()
    classic = classic_lda_pencil(X_tr, y_tr, delta=delta, route="reduced")
    secs["classic_pencil"] = time.perf_counter() - t0
    t0 = time.perf_counter()
    shrunk = classic_lda_pencil(X_tr, y_tr, shrinkage=SHRINK_ALPHA, route="reduced")
    secs["shrinkage_pencil"] = time.perf_counter() - t0
    t0 = time.perf_counter()
    pc = bl.pca_dirs(X_tr)
    secs["pca_dirs"] = time.perf_counter() - t0
    return {"go": go, "classic": classic, "shrunk": shrunk, "pc": pc, "secs": secs}


def score(basis, X_tr, y_tr, X_te, y_te):
    """Both fixed heads on the same projected fold: 1-NN and nearest-class-mean.

    basis is None for the no-projection reference.  The class means are formed in the
    projected space, not lifted from the original one - NCM in a subspace has to use that
    subspace's means, and the two differ once the projection is not orthonormal-preserving.
    """
    P_tr, P_te = (X_tr, X_te) if basis is None else (X_tr @ basis, X_te @ basis)
    acc_knn = float(np.mean(bl.knn_predict(P_tr, y_tr, P_te, k=1) == y_te))
    classes = np.unique(y_tr)
    means = np.stack([P_tr[y_tr == c].mean(0) for c in classes])
    acc_ncm = float(np.mean(bl.ncm_predict(means, classes, P_te) == y_te))
    return acc_knn, acc_ncm


def main(argv=None):
    ap = argparse.ArgumentParser(description="ORL raw-pixel MVP experiment (WP5)")
    ap.add_argument("--folds", type=int, default=N_FOLDS)
    ap.add_argument("--delta", type=float, default=None, help="run one delta only")
    ap.add_argument("--out", type=str, default=None)
    ap.add_argument("--train-per-subject", type=int, default=None,
                    help="supplementary small-sample regime: one fixed split with this many "
                         "training images per subject instead of the ten-fold CV (U008)")
    ap.add_argument("--probe", action="store_true",
                    help="write fold0_probes.json: same-fold accuracies for the unregularised "
                         "and ridged pencils against scikit-learn's svd solver, the contrast "
                         "section 5 of the feasibility report quotes")
    args = ap.parse_args(argv)

    deltas = [args.delta] if args.delta is not None else list(DELTAS)
    out = Path(args.out or (OUT if args.train_per_subject is None
                            else ROOT / "runs" / "mvp_orl_small_sample"))
    out.mkdir(parents=True, exist_ok=True)

    X, y = load_orl()
    assert X.shape == (400, M) and M == IMG_H * IMG_W == 10304, X.shape
    if args.train_per_subject is None:
        folds = stratified_k_fold(y, N_FOLDS, SEED)[: args.folds]
        protocol = f"main: stratified ten-fold, {400 // N_FOLDS} test image per subject per fold"
    else:
        folds = [fixed_split_per_subject(y, args.train_per_subject)]
        protocol = (f"supplementary: {args.train_per_subject} train / "
                    f"{10 - args.train_per_subject} test images per subject, one fixed split, "
                    "identical for every method - never pooled with the ten-fold main table")
    cap = int(len(np.unique(y)) - 1)
    print(f"ORL {X.shape}, protocol: {protocol}, deltas {deltas}, "
          f"K grid {K_GRID}, rank cap C-1 = {cap}", flush=True)

    if args.probe:
        tr, te = folds[0]
        X_tr, y_tr, X_te, y_te = X[tr], y[tr], X[te], y[te]
        sk = bl.classic_lda_sklearn(X_tr, y_tr, solver="svd")
        probe = {"fold": 0, "seed": SEED, "cap": cap,
                 "head": "1-NN on the 40 test images of fold 0",
                 "note": "single-fold numbers, not comparable to the ten-fold means in "
                         "accuracy_summary.csv; they exist to put the delta = 0 degeneracy, "
                         "the ridged pencil and scikit-learn's null-space route on identical "
                         "data, since sklearn's svd solver takes no delta at all",
                 "sklearn_coef_rows": int(sk.shape[1])}
        for delta in (0.0, 1e-6, 5e-3):
            cl = classic_lda_pencil(X_tr, y_tr, delta=delta, route="reduced")
            go = go_lda(X_tr, y_tr, K=cap, delta=delta, route="reduced")
            ak, an = score(go["U"][:, :cap], X_tr, y_tr, X_te, y_te)
            ckk, _ = score(cl["U"][:, :cap], X_tr, y_tr, X_te, y_te)
            skk, _ = score(sk[:, :cap], X_tr, y_tr, X_te, y_te)
            probe[f"delta_{delta:g}"] = {"go_lda_at_cap": ak,
                                         "go_lda_at_cap_ncm": an,
                                         "classic_pencil_at_cap": ckk,
                                         "sklearn_svd_lda_at_cap": skk}
        (out / "fold0_probes.json").write_text(json.dumps(probe, indent=2), encoding="utf-8")
        print(json.dumps(probe, indent=2), flush=True)
        return 0

    rows, diag = [], []
    timings = {"per_solve": [], "per_fold": []}
    t_start = time.perf_counter()
    for delta in deltas:
        for f, (tr, te) in enumerate(folds):
            t_fold = time.perf_counter()
            X_tr, y_tr, X_te, y_te = X[tr], y[tr], X[te], y[te]
            solved = solve_fold(X_tr, y_tr, delta)
            go, classic, shrunk, pc = (solved["go"], solved["classic"],
                                       solved["shrunk"], solved["pc"])
            timings["per_solve"].append({"delta": delta, "fold": f, **solved["secs"]})

            def add(method, d, K, basis, rule, ak, an):
                for head, acc in (("1-NN", ak), ("NCM", an)):
                    rows.append({"method": method, "delta": d, "K": K,
                                 "realized_dim": M if basis is None else basis.shape[1],
                                 "dim_rule": rule, "head": head, "fold": f,
                                 "accuracy": acc, "train_n": int(len(tr)),
                                 "test_n": int(len(te))})

            # no-projection reference (what C4 calls the "Full" row), same fold, same heads
            ak, an = score(None, X_tr, y_tr, X_te, y_te)
            add("no-projection", "n/a", M, None, "unprojected", ak, an)

            for K in K_GRID:
                ak, an = score(go["U"][:, :K], X_tr, y_tr, X_te, y_te)
                add("GO-LDA", delta, K, go["U"][:, :K], "first K GO-LDA directions", ak, an)
                if K <= cap:
                    ak, an = score(classic["U"][:, :K], X_tr, y_tr, X_te, y_te)
                    add("classic-ridge-LDA", delta, K, classic["U"][:, :K],
                        "K of C-1 pencil eigenvectors", ak, an)
                pl = bl.pca_then_lda(X_tr, y_tr, K, delta if delta else 1e-6, pc_dirs=pc)
                ak, an = score(pl["U"], X_tr, y_tr, X_te, y_te)
                add("PCA-then-LDA", delta, K, pl["U"],
                    f"PCA to {K}, then LDA (realized {pl['realized_dim']}, cap {cap})", ak, an)
            # the shrunken estimator does not depend on delta: one row per fold, labelled so
            if delta == deltas[0]:
                for K in [k for k in K_GRID if k <= cap]:
                    ak, an = score(shrunk["U"][:, :K], X_tr, y_tr, X_te, y_te)
                    add("classic-shrinkage-LDA", "n/a", K, shrunk["U"][:, :K],
                        f"K of C-1 shrunken (alpha={SHRINK_ALPHA:g}) pencil eigenvectors",
                        ak, an)

            if f == 0:
                sc = go["sc"]
                # classic LDA can return fewer than C-1 usable directions when the pencil is
                # singular (delta = 0, and worse in the small-sample regime), so every
                # comparison below is over the directions it actually produced and the count
                # itself is recorded as a measurement
                n_common = min(cap, classic["U"].shape[1])
                fish_c = _fisher(sc, classic["U"][:, :n_common], delta)
                # certify the directions this grid actually uses, at every delta, with the
                # same bound the parity gate applies - delta = 0 goes through a
                # pseudo-inverse, so it is the case that must not be taken on trust
                res = residuals(go)
                tol_res, kappa_res = residual_bound(go["A_r"])
                rel_res = float(res["relative"].max())
                diag.append({
                    "delta": delta, "fold": f, "r": int(go["Q"].shape[1]),
                    "residual_rel_max": rel_res,
                    "residual_tol_eps_kappa": tol_res,
                    "residual_within_bound": bool(rel_res < tol_res),
                    "residual_ratio_to_bound": rel_res / tol_res,
                    "go_max_abs_offdiag": go["max_pairwise_abs_cos"],
                    "go_max_abs_offdiag_at_cap": _offdiag(go["U"][:, :cap]),
                    "classic_max_abs_offdiag": classic["max_pairwise_abs_cos"],
                    "shrunk_max_abs_offdiag": shrunk["max_pairwise_abs_cos"],
                    "span_angle_go_vs_classic_at_cap_deg":
                        principal_angle(go["U"][:, :n_common], classic["U"][:, :n_common]),
                    "classic_directions_produced": int(classic["U"].shape[1]),
                    "fisher_go_first_five": [float(v) for v in go["fisher"][:5]],
                    "fisher_go_monotone": bool(np.all(np.diff(go["fisher"]) <= 1e-9)),
                    "fisher_classic_first_five": [float(v) for v in fish_c[:5]],
                    "fisher_go_ge_classic_within_cap":
                        bool(np.all(go["fisher"][:n_common] >= fish_c * (1 - 1e-3))),
                    "mu_go_at_cap": float(go["mu"][cap - 1]),
                    "mu_go_beyond_cap": [float(v) for v in go["mu"][cap:cap + 2]],
                    "eigenvalue_range": [float(go["mu"].min()), float(go["mu"].max())],
                    "kappa_A_r": kappa_res,
                    "singular_pinv_used": bool(go["singular_pinv"]),
                    "classic_pencil_mu_range": [float(classic["mu"].min()),
                                                float(classic["mu"].max())],
                })
                if delta == 0.0:
                    # the singular case deserves one external control: scikit-learn's svd
                    # solver is a different formulation of unregularised LDA (it projects
                    # onto null(S_W)) rather than a largest-eigenvalue rule on a numerically
                    # singular pencil, so comparing against it says whether our delta = 0
                    # difficulty is inherent to the pencil or an artefact of this code.
                    sk = bl.classic_lda_sklearn(X_tr, y_tr, solver="svd")
                    ak, _an = score(sk[:, :cap], X_tr, y_tr, X_te, y_te)
                    diag[-1]["sklearn_svd_lda_at_cap_1nn"] = ak
                    diag[-1]["sklearn_svd_lda_directions"] = int(sk.shape[1])
            timings["per_fold"].append(
                {"delta": delta, "fold": f, "seconds": time.perf_counter() - t_fold})
            print(f"  delta={delta:g} fold {f}: go_lda {solved['secs']['go_lda']:.1f}s, "
                  f"fold {timings['per_fold'][-1]['seconds']:.1f}s, cumulative "
                  f"{time.perf_counter() - t_start:.0f}s", flush=True)

    total_s = time.perf_counter() - t_start
    peak = peak_rss_bytes()

    # ---- summary -------------------------------------------------------------------
    by_cell: dict[tuple, list[float]] = {}
    for r in rows:
        by_cell.setdefault((r["method"], str(r["delta"]), int(r["K"]), r["head"]),
                           []).append(r["accuracy"])
    summary = []
    for (method, d, K, head), accs in sorted(by_cell.items()):
        a = np.asarray(accs)
        dim = [r["realized_dim"] for r in rows if r["method"] == method
               and str(r["delta"]) == d and r["K"] == K and r["head"] == head][0]
        summary.append({"method": method, "delta": d, "K": K, "head": head,
                        "realized_dim": dim, "n_folds": len(accs),
                        "mean": float(a.mean()),
                        "sd": float(a.std(ddof=1)) if len(accs) > 1 else float("nan"),
                        "min": float(a.min()), "max": float(a.max())})

    def cell(method, d, K, head="1-NN"):
        return np.asarray([r["accuracy"] for r in rows if r["method"] == method
                           and str(r["delta"]) == str(d) and r["K"] == K
                           and r["head"] == head])

    paired = []
    for delta in deltas:
        g39, c39 = cell("GO-LDA", delta, cap), cell("classic-ridge-LDA", delta, cap)
        d = g39 - c39
        full = cell("no-projection", "n/a", M)
        h2 = {}
        for K in [k for k in K_GRID if k > cap]:
            gk = cell("GO-LDA", delta, K)
            h2[f"K={K}"] = {"go_mean": float(gk.mean()),
                            "go_minus_classic_at_cap": float(gk.mean() - c39.mean()),
                            "go_minus_no_projection": float(gk.mean() - full.mean())}
        paired.append({
            "delta": delta,
            "go_at_cap_mean": float(g39.mean()), "go_at_cap_sd": _sd(g39),
            "classic_at_cap_mean": float(c39.mean()),
            "classic_at_cap_sd": _sd(c39),
            "H1_go_minus_classic_paired": {"mean": float(d.mean()),
                                           "sd": _sd(d),
                                           "sem": _sd(d) / np.sqrt(d.size)
                                           if d.size > 1 else float("nan"),
                                           "folds_go_ahead": int((d > 0).sum()),
                                           "folds_classic_ahead": int((d < 0).sum()),
                                           "folds_tied": int((d == 0).sum())},
            "H2_beyond_cap": h2,
        })

    (out / "accuracy_rows.csv").write_text(_csv(rows), encoding="utf-8", newline="")
    (out / "accuracy_summary.csv").write_text(_csv(summary), encoding="utf-8", newline="")
    (out / "diagnostics.json").write_text(json.dumps(
        {"per_fold_delta": diag, "hypotheses": paired, "rank_cap": cap, "seed": SEED,
         "protocol": protocol,
         "k_grid": K_GRID, "deltas": deltas, "shrinkage_alpha": SHRINK_ALPHA,
         "certified_deltas": [d["delta"] for d in diag if d["residual_within_bound"]],
         "uncertified_deltas": [d["delta"] for d in diag if not d["residual_within_bound"]],
         "no_projection_1nn_mean": float(cell("no-projection", "n/a", M).mean())},
        indent=2), encoding="utf-8")
    (out / "timing.json").write_text(json.dumps(
        {"total_wall_clock_s": total_s, "peak_rss_bytes": peak, "peak_rss_mb": peak / 1e6,
         "n_solves": len(timings["per_solve"]),
         "go_lda_s_mean": float(np.mean([t["go_lda"] for t in timings["per_solve"]])),
         "go_lda_s_max": float(np.max([t["go_lda"] for t in timings["per_solve"]])),
         "classic_pencil_s_mean": float(np.mean([t["classic_pencil"] for t in timings["per_solve"]])),
         "shrinkage_pencil_s_mean": float(np.mean([t["shrinkage_pencil"] for t in timings["per_solve"]])),
         "pca_dirs_s_mean": float(np.mean([t["pca_dirs"] for t in timings["per_solve"]])),
         "fold_s_mean": float(np.mean([t["seconds"] for t in timings["per_fold"]])),
         "per_solve": timings["per_solve"], "per_fold": timings["per_fold"]},
        indent=2), encoding="utf-8")
    (out / "manifest.json").write_text(json.dumps({
        "stage": "M1 / WP5 ORL raw-pixel experiment", "seed": SEED,
        "protocol": protocol, "splits": len(folds),
        "train_per_subject": args.train_per_subject,
        "folds_available_if_cv": N_FOLDS, "deltas": deltas, "k_grid": K_GRID,
        "shrinkage_alpha": SHRINK_ALPHA,
        "heads": ["1-NN (paper Table II protocol)", "nearest-class-mean (closed-form read-out)"],
        "dataset": {"name": "ORL / AT&T Database of Faces", "shape": list(X.shape),
                    "image": {"height": IMG_H, "width": IMG_W}, "subjects": 40, "images_per_subject": 10,
                    "source": "https://www.cl.cam.ac.uk/Research/DTG/attarchive/pub/data/att_faces.zip",
                    "local": "data/orl/att_faces.zip",
                    "loader": "src/orl.py (PGM P5 reader, no sklearn)"},
        "code": ["src/orl.py", "src/golda.py", "src/baselines.py", "src/run_mvp_orl.py"],
        "parity_gate": "runs/parity/parity_report.json",
        "python": platform.python_version(), "numpy": np.__version__,
        "rows_written": len(rows), "total_wall_clock_s": total_s,
    }, indent=2), encoding="utf-8")

    print(f"\n{len(rows)} accuracy rows, {len(summary)} summary cells in {total_s:.0f} s; "
          f"peak RSS {peak / 1e6:.0f} MB -> {out}")
    top = [s for s in summary if s["head"] == "1-NN"]
    for s in sorted(top, key=lambda s: -s["mean"])[:8]:
        print(f"  {s['method']:24s} delta={s['delta']:<8s} K={s['K']:<5d} "
              f"dim={s['realized_dim']:<6d} {s['mean']:.4f} +/- {s['sd']:.4f}")
    for h in paired:
        p = h["H1_go_minus_classic_paired"]
        print(f"  H1 delta={h['delta']:g}: GO-LDA {h['go_at_cap_mean']:.4f} vs classic "
              f"{h['classic_at_cap_mean']:.4f}; paired diff {p['mean']:+.4f} "
              f"(sem {p['sem']:.4f}, {p['folds_go_ahead']}/{p['folds_tied']}/"
              f"{p['folds_classic_ahead']} go/tie/classic)")
    return 0


def _sd(a: np.ndarray) -> float:
    """Sample standard deviation, undefined rather than noisy for a single fold."""
    return float(a.std(ddof=1)) if a.size > 1 else float("nan")


def _fisher(sc: Scatters, U: np.ndarray, delta: float) -> np.ndarray:
    return np.asarray([float(u @ sc.apply_SB(u[:, None]).reshape(-1))
                       / max(float(u @ sc.apply_SW(u[:, None], delta).reshape(-1)), 1e-300)
                       for u in U.T])


def _offdiag(U: np.ndarray) -> float:
    G = U.T @ U
    off = np.abs(G - np.diag(np.diag(G)))
    return float(off.max()) if off.size and U.shape[1] > 1 else 0.0


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
