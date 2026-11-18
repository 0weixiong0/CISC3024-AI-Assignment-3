"""Why does GO-LDA trail classic LDA by ~6 points at K = C - 1 on frozen features?

Two explanations look identical in the accuracy table and are not the same claim:

* the two methods span **different subspaces**, so the cap-parity result measured on raw-pixel
  ORL does not carry over; or
* they span the **same** subspace in different coordinates, and C4's head - StandardScaler plus
  an L2 penalty - is not invariant to a change of basis, so the gap belongs to the classifier.

The probe separates them by scoring the same span in both bases (raw and QR-orthonormalised),
and reports the whole principal-angle spectrum rather than the largest angle alone: the
diagnostics' `span_at_cap_deg` is the largest angle, and with an eigenvalue gap of ~2 % at the
cap in a 512-dimensional space a single near-orthogonal boundary direction is expected even
when the subspaces agree.

    python src/probe_m2_cap_gap.py --dataset cifar100 --backbone resnet18 --delta 0.005

Writes runs/m2_matrix/probe_cap_gap.json.  Diagnostic only: nothing here enters the
accuracy table, and its numbers are single-split hold-out values, not report-level results.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy import linalg

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import baselines as bl                                    # noqa: E402
import run_m2_matrix as m2                                # noqa: E402
from golda import (Scatters, classic_lda_pencil, go_lda,  # noqa: E402
                   principal_angle)

OUT = ROOT / "runs" / "m2_matrix" / "probe_cap_gap.json"


def angle_spectrum(A, B):
    """All principal angles between the spans, so a single boundary direction cannot be read as
    total disagreement (or as agreement)."""
    qa = linalg.qr(np.asarray(A, dtype=np.float64), mode="economic")[0]
    qb = linalg.qr(np.asarray(B, dtype=np.float64), mode="economic")[0]
    s = np.clip(np.linalg.svd(qa.T @ qb, compute_uv=False), -1.0, 1.0)
    th = np.sort(np.degrees(np.arccos(s)))[::-1]
    return {"n_angles": int(th.size), "median_deg": float(np.median(th)),
            "p90_deg": float(np.percentile(th, 90)), "max_deg": float(th[0]),
            "frac_under_1deg": float(np.mean(th < 1.0)),
            "worst_five_deg": [round(float(v), 4) for v in th[:5]]}


def eigh_classic(X, y, delta):
    """The same pencil solved the numerically right way: S_B u = mu S_W' u with S_W' symmetric
    positive definite is symmetric-definite, so `eigh` applies and the eigenpairs are real by
    construction.  This is the reference for whether `eig`-based classic directions are sound."""
    sc = Scatters(X, y)
    B_r, A_r = sc.dense_SB(), sc.dense_SW(delta)
    vals, vecs = linalg.eigh(B_r, A_r)
    order = np.argsort(vals)[::-1][:sc.C - 1]
    U = np.column_stack([vecs[:, j] / np.linalg.norm(vecs[:, j]) for j in order])
    return np.asarray(vals[order], dtype=np.float64), U, sc


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="cifar100", choices=["cifar100", "tiny_imagenet"])
    ap.add_argument("--backbone", default="resnet18", choices=["resnet18", "dinov2_vits14"])
    ap.add_argument("--delta", type=float, default=5e-3,
                    help="the delta GO-LDA selected for this pair on the hold-out")
    ap.add_argument("--out", type=str, default=str(OUT))
    args = ap.parse_args(argv)

    loaded = m2.load_cached(args.dataset, args.backbone)
    X_tr, y_tr = loaded["train"], loaded["train_y"]
    X_te, y_te = loaded["test"], loaded["test_y"]
    cap = int(len(np.unique(y_tr))) - 1
    dim = X_tr.shape[1]
    k_beyond = min(256, dim)
    print(f"{args.dataset}/{args.backbone}: cap={cap} dim={dim} delta={args.delta:g} "
          f"solving GO to K={k_beyond}", flush=True)

    t0 = time.perf_counter()
    go = go_lda(X_tr, y_tr, K=k_beyond, delta=args.delta, route="dense")
    print(f"  GO-LDA (dense) solved in {time.perf_counter() - t0:.0f} s", flush=True)
    t0 = time.perf_counter()
    go_red = go_lda(X_tr, y_tr, K=cap, delta=args.delta, route="reduced")
    print(f"  GO-LDA (reduced) solved in {time.perf_counter() - t0:.0f} s "
          f"- the route control: the two must agree or M2 is measuring an implementation",
          flush=True)
    cl = classic_lda_pencil(X_tr, y_tr, delta=args.delta, route="dense")
    mu_eigh, U_eigh, _sc = eigh_classic(X_tr, y_tr, args.delta)
    print(f"  classic pencils done ({cl['U'].shape[1]} directions from eig, "
          f"{U_eigh.shape[1]} from eigh)", flush=True)

    def qr(U):
        return linalg.qr(np.ascontiguousarray(U, dtype=np.float64), mode="economic")[0]

    def spectrum(name, mu_a, mu_b):
        """Compare two mu lists as multisets: if the recursion extracts the same eigenpairs the
        sorted values agree, whatever the per-index correspondence looks like."""
        a, b = np.sort(np.asarray(mu_a, float))[::-1], np.sort(np.asarray(mu_b, float))[::-1]
        n = min(a.size, b.size)
        return {f"{name}_n": int(n),
                f"{name}_max_abs_diff": float(np.abs(a[:n] - b[:n]).max()),
                f"{name}_rel_diff_at_cap": float(abs(a[n - 1] - b[n - 1]) / abs(b[n - 1])),
                f"{name}_sum_a": float(a.sum()), f"{name}_sum_b": float(b.sum())}

    # every arm is scored through the same head on the same splits, so a difference is a
    # difference in coordinates or in span and nothing else
    arms = {
        "GO@cap": go["U"][:, :cap],
        "GO@cap-QR": qr(go["U"][:, :cap]),
        "GO-reduced@cap": go_red["U"],
        "GO-reduced@cap-QR": qr(go_red["U"]),
        "classic-eig@cap": cl["U"][:, :cap],
        "classic-eig@cap-QR": qr(cl["U"][:, :cap]),
        "classic-eigh@cap": U_eigh[:, :cap],
        "classic-eigh@cap-QR": qr(U_eigh[:, :cap]),
        "GO@beyond": go["U"][:, :k_beyond],
        "GO@beyond-QR": qr(go["U"][:, :k_beyond]),
        "no-projection": None,
    }
    scores, secs = {}, {}
    for name, basis in arms.items():
        t1 = time.perf_counter()
        acc, realized = m2.logistic_score(basis, X_tr, y_tr, X_te, y_te)
        scores[name] = acc
        secs[name] = round(time.perf_counter() - t1, 1)
        print(f"  {name:22s} test {acc:.4f}  (dim {realized}, {secs[name]} s)", flush=True)

    mu = np.asarray(go["mu"], dtype=np.float64)
    cl_mu = np.asarray(cl["mu"], dtype=np.float64)
    n_mu = min(cl_mu.size, mu_eigh.size)
    mu_agreement = float(np.abs(cl_mu[:n_mu] - mu_eigh[:n_mu]).max())
    report = {
        "pair": [args.dataset, args.backbone], "delta": args.delta, "cap": cap, "dim": dim,
        "k_beyond": k_beyond, "rows": int(X_tr.shape[0]),
        "note": "single full-train fit, official test split; diagnostic, not a table cell",
        "test_accuracy": scores, "head_seconds": secs,
        "eigen_gap_at_cap": {
            "go_mu_at_cap": float(mu[cap - 1]),
            "go_mu_beyond_first": float(mu[cap]) if mu.size > cap else None,
            "relative_gap": float((mu[cap - 1] - mu[cap]) / mu[cap - 1]) if mu.size > cap else None,
        },
        "spectrum": {
            **spectrum("GO_vs_classic-eig", mu[:cap], cl_mu),
            **spectrum("GO_vs_classic-eigh", mu[:cap], mu_eigh),
            **spectrum("GO-dense_vs_GO-reduced", mu[:cap], np.asarray(go_red["mu"], float)),
        },
        "route_control": {
            "GO_dense_vs_reduced_span_deg": principal_angle(go["U"][:, :cap], go_red["U"]),
            "GO_dense_vs_reduced_max_abs_U_diff":
                float(np.abs(go["U"][:, :cap] - go_red["U"]).max()),
        },
        "drift_growth": {
            str(m): {"max_deg": principal_angle(go["U"][:, :m], U_eigh[:, :m]),
                     "median_deg": float(np.median(np.degrees(np.arccos(np.clip(
                         np.linalg.svd(linalg.qr(go["U"][:, :m], mode="economic")[0].T
                                       @ linalg.qr(U_eigh[:, :m], mode="economic")[0],
                         compute_uv=False), -1.0, 1.0))))),
                     "mu_go": float(mu[m - 1]), "mu_classic": float(mu_eigh[m - 1])}
            for m in (1, 2, 3, 5, 10, 25, 50, 75, 99) if m <= cap and m <= U_eigh.shape[1]
        },
        "first_direction": {
            "abs_cos_GO_vs_eigh": float(abs(float(go["U"][:, 0] @ U_eigh[:, 0]))),
            "abs_cos_GO_vs_eig": float(abs(float(go["U"][:, 0] @ cl["U"][:, 0]))),
            "abs_cos_eig_vs_eigh": float(abs(float(cl["U"][:, 0] @ U_eigh[:, 0]))),
        },
        "eig_vs_eigh": {
            "n_eig": int(cl_mu.size), "n_eigh": int(mu_eigh.size),
            "max_abs_mu_diff": mu_agreement,
            "span_deg": principal_angle(cl["U"], U_eigh),
            "angles": angle_spectrum(cl["U"], U_eigh),
        },
        "spans_at_cap": {
            "GO_vs_classic-eig": {"max_deg": principal_angle(go["U"][:, :cap], cl["U"][:, :cap]),
                                  "angles": angle_spectrum(go["U"][:, :cap], cl["U"][:, :cap])},
            "GO_vs_classic-eigh": {"max_deg": principal_angle(go["U"][:, :cap], U_eigh),
                                   "angles": angle_spectrum(go["U"][:, :cap], U_eigh)},
        },
        "basis_orthogonality": {
            name: float(np.abs(basis.T @ basis
                               - np.eye(basis.shape[1])).max(initial=0.0)
                        if basis is not None else 0.0)
            for name, basis in arms.items() if basis is not None
        },
    }
    Path(args.out).write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nwrote {args.out}")
    print("\ndrift: span of GO's first m directions against classic's first m (eigh)")
    print(f"  {'m':>4} {'max_deg':>10} {'median_deg':>11} {'mu_GO':>10} {'mu_classic':>11}")
    for m, v in sorted(report["drift_growth"].items(), key=lambda kv: int(kv[0])):
        print(f"  {m:>4} {v['max_deg']:>10.4f} {v['median_deg']:>11.4f} "
              f"{v['mu_go']:>10.5f} {v['mu_classic']:>11.5f}")
    print("\nsorted-multiset mu comparison:", json.dumps(report["spectrum"], indent=None))
    print("route control:", json.dumps(report["route_control"]))
    print("first direction:", json.dumps(report["first_direction"]))
    gap = scores["GO@cap"] - scores["classic-eigh@cap"]
    qr_gap = scores["GO@cap-QR"] - scores["classic-eigh@cap-QR"]
    print(f"raw gap GO-classic {gap:+.4f}; after QR on both {qr_gap:+.4f}")
    print("if the QR gap collapses, the headline gap is the head's basis dependence, not a span "
          "difference")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
