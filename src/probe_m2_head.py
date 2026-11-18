"""Does GO-LDA's deficit at the cap survive the paper's own classifier?

M2 scores every method with C4's penalised logistic head, which is the protocol this project
was told to use (supervisor's ruling U007).  The paper's Table II uses 1-NN.  Those two heads
are not equivalent on a projected space: the logistic arm StandardScalers and then pays an L2
penalty in the coordinates the basis happens to produce, while 1-NN only cares about distances.
So before the report says "GO-LDA loses on frozen features", the same bases have to be scored
with the classifier the claim was made with.

One solve per basis, two heads, on the same splits as `selection.csv`: fit on all of train,
evaluate on the official test split.  Nothing here enters the accuracy table; it is the control
arm for interpreting it.  1-NN is computed with an exact brute-force search (sklearn), not with
`baselines.knn_predict`: that helper forms the full pairwise difference tensor, which is fine at
ORL's 360 reference rows and would need 0.8 GB per block at 50,000.

    python src/probe_m2_head.py --dataset cifar100 --backbone resnet18 --delta 0.005
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
from sklearn.neighbors import NearestNeighbors

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import baselines as bl                                    # noqa: E402
import run_m2_matrix as m2                                # noqa: E402
from golda import classic_lda_pencil, go_lda              # noqa: E402

OUT = ROOT / "runs" / "m2_matrix" / "probe_head_control.json"


def knn1_score(basis, X_fit, y_fit, X_eval, y_eval, scale: bool):
    """1-NN in the projected space.  `scale` matters and is not a detail: GO-LDA's columns are
    unit-Euclidean-norm directions whose projected variances differ a lot, so scaling the
    coordinates before measuring distances changes which neighbour is nearest.  The paper states
    neither, so both are reported; the logistic arm always sees the scaled space (C4's recipe)."""
    P_fit = X_fit if basis is None else X_fit @ basis
    P_eval = X_eval if basis is None else X_eval @ basis
    if scale:
        mu, sd = P_fit.mean(axis=0), P_fit.std(axis=0)
        sd = np.where(sd > 1e-12, sd, 1.0)
        P_fit, P_eval = (P_fit - mu) / sd, (P_eval - mu) / sd
    nn = NearestNeighbors(n_neighbors=1, algorithm="brute", metric="euclidean", n_jobs=-1)
    nn.fit(P_fit)
    idx = nn.kneighbors(P_eval, n_neighbors=1, return_distance=False)[:, 0]
    return float(np.mean(y_fit[idx] == y_eval)), P_fit.shape[1]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="cifar100", choices=["cifar100", "tiny_imagenet"])
    ap.add_argument("--backbone", default="resnet18", choices=["resnet18", "dinov2_vits14"])
    ap.add_argument("--delta", type=float, default=5e-3)
    ap.add_argument("--out", type=str, default=str(OUT))
    args = ap.parse_args(argv)

    loaded = m2.load_cached(args.dataset, args.backbone)
    X_tr, y_tr, X_te, y_te = (loaded["train"], loaded["train_y"], loaded["test"], loaded["test_y"])
    cap = int(len(np.unique(y_tr))) - 1
    dim = X_tr.shape[1]
    ks = [k for k in (50, cap, cap + 1, min(2 * cap, dim), min(256, dim)) if k <= dim]
    ks = sorted(set(ks))
    print(f"{args.dataset}/{args.backbone}: train {X_tr.shape} test {X_te.shape} cap={cap} "
          f"K={ks} delta={args.delta:g}", flush=True)

    t0 = time.perf_counter()
    go = go_lda(X_tr, y_tr, K=max(ks), delta=args.delta, route="dense")
    print(f"  GO-LDA solved in {time.perf_counter() - t0:.0f} s", flush=True)
    cl = classic_lda_pencil(X_tr, y_tr, delta=args.delta, route="dense")
    pc = bl.pca_dirs(X_tr)

    arms = {"no-projection": None}
    for k in ks:
        arms[f"GO-LDA@{k}"] = go["U"][:, :k]
    # the comparators only need to exist where the comparison is claimed: at the cap for classic
    # (which has nothing beyond it) and at the cap for PCA (whose beyond-cap arm the GO sweep
    # already covers through the grid)
    if cap <= cl["U"].shape[1]:
        arms[f"classic-LDA@{cap}"] = cl["U"][:, :cap]
    if cap <= pc.shape[1]:
        arms[f"PCA@{cap}"] = pc[:, :cap]
    for k in ks:
        if k > cap and k <= pc.shape[1]:
            arms[f"PCA@{k}"] = pc[:, :k]

    rows = []
    for name, basis in arms.items():
        rec = {"arm": name, "dim": None}
        t1 = time.perf_counter()
        rec["logistic"], rec["dim"] = m2.logistic_score(basis, X_tr, y_tr, X_te, y_te)
        rec["logistic_s"] = round(time.perf_counter() - t1, 1)
        t1 = time.perf_counter()
        rec["knn1_raw"], _ = knn1_score(basis, X_tr, y_tr, X_te, y_te, scale=False)
        rec["knn1_raw_s"] = round(time.perf_counter() - t1, 1)
        t1 = time.perf_counter()
        rec["knn1_scaled"], _ = knn1_score(basis, X_tr, y_tr, X_te, y_te, scale=True)
        rec["knn1_scaled_s"] = round(time.perf_counter() - t1, 1)
        rows.append(rec)
        print(f"  {name:18s} dim {rec['dim']:>4}  logistic {rec['logistic']:.4f}  "
              f"1-NN raw {rec['knn1_raw']:.4f}  1-NN scaled {rec['knn1_scaled']:.4f}", flush=True)

    by = {r["arm"]: r for r in rows}
    heads = ("logistic", "knn1_raw", "knn1_scaled")
    verdict = {}
    for k in ks:
        g = by.get(f"GO-LDA@{k}")
        if g is None:
            continue
        for other in ("classic-LDA", "PCA"):
            o = by.get(f"{other}@{k}")
            if o:
                verdict[f"GO-LDA@{k}_minus_{other}@{k}"] = {
                    h: round(g[h] - o[h], 4) for h in heads}
    out = {"pair": [args.dataset, args.backbone], "delta": args.delta, "cap": cap, "dim": dim,
           "fit": "all of train", "eval": "official test split",
           "heads": {"logistic": "C4's: L2 logistic LBFGS max_iter 5000 C=1.0 + StandardScaler",
                     "knn1_raw": "paper's Table II classifier: 1-NN Euclidean on the projected "
                                 "space as it comes out of the basis",
                     "knn1_scaled": "same, after per-coordinate standardisation (the scaler C4's "
                                    "head uses)"},
           "rows": rows, "differences": verdict}
    Path(args.out).write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"\nwrote {args.out}")
    for key, v in verdict.items():
        print(f"  {key:34s} " + "  ".join(f"{h} {v[h]:+.4f}" for h in heads))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
