"""Out-of-distribution control (plan section 4's promised one), option A per supervisor U010.

The plan said "one out-of-distribution control is added so the conclusion is not tuned to a single
pair of datasets", and it was never run. Option A is the version that can actually answer that: take
the official CIFAR-100 test images, apply **one** fixed corruption at **one** fixed severity, push
them through the same frozen backbones that produced the cached features, and score the projections
and heads **fitted on clean train** against them.

What the control is allowed to support, and what it is not:

* it tests whether the *ranking* of the four methods survives a distribution shift, which is what the
  plan asked for - not whether GO-LDA becomes competitive under shift;
* the shift is one corruption at one level, chosen below and not tuned: a null result (ranking
  unchanged) is a result, and a result obtained by sweeping severities until one separates the arms
  would not be;
* nothing is refitted on the corrupted features. The scaler and the logistic head come from clean
  train, as does the projection, so a drop in absolute accuracy is the shift and not a mis-specified
  pipeline.

    python src/probe_m2_ood.py                     # both CIFAR-100 backbones
    python src/probe_m2_ood.py --backbone resnet18 --sigma 0.08

Artefact: runs/m2_matrix/probe_ood.json
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

import baselines as bl                                # noqa: E402
import extract_features as ef                     # noqa: E402
import run_m2_matrix as m2                        # noqa: E402

OUT = m2.OUT / "probe_ood.json"
SIGMA = 0.08          # additive Gaussian noise, units of the [0, 1] pixel scale at native 32 x 32
NOISE_KIND = "additive white Gaussian noise, per pixel, per channel"
SEED = m2.SEED        # 20261117, the seed every run in this project uses

# stage_03b section 3.1's official-test numbers, by backbone. Every arm has to reproduce its own
# before the corrupted column is believed: a shifted accuracy only means something next to the
# unshifted number it is a shift of, and if this script's pipeline had drifted the comparison would
# be between two pipelines rather than between clean and corrupted data.
CLEAN_REFERENCE = {
    "resnet18": {"GO-LDA": 0.6478, "classic-ridge-LDA": 0.6699,
                 "classic-shrinkage-LDA": 0.6708, "PCA-then-LDA": 0.6688},
    "dinov2_vits14": {"GO-LDA": 0.8098, "classic-ridge-LDA": 0.8244,
                      "classic-shrinkage-LDA": 0.8240, "PCA-then-LDA": 0.8195},
}


def corrupted_images(X: np.ndarray, sigma: float, seed: int) -> np.ndarray:
    """One fixed noise field over the native uint8 test images, drawn once and shared.

    Drawn once and materialised (30 MB) so both backbones see *identical* corrupted pixels: the
    comparison of interest is across methods at a fixed shift, and two different noise draws would
    put a random term between the two rows being compared.
    """
    rng = np.random.default_rng(seed)
    clean = X.astype(np.float64) / 255.0
    noisy = clean + rng.normal(0.0, sigma, size=clean.shape)
    return np.clip(noisy * 255.0, 0.0, 255.0).astype(np.uint8)


def stream(arr: np.ndarray, labels: np.ndarray):
    for i in range(arr.shape[0]):
        yield Image.fromarray(arr[i]), int(labels[i])


def extract_corrupted(backbone: str, Xc: np.ndarray, y: np.ndarray, batch: int) -> tuple:
    """The cached pipeline, unchanged, applied to the corrupted array."""
    import os
    import torch
    # timm re-resolves the DINOv2 checkpoint through huggingface_hub at build time, and this
    # machine's NO_PROXY contains "[::1]", which httpx cannot parse (InvalidURL: ':1]'). The
    # weights are already in the local cache from M1.5, so offline mode is both the fix and the
    # statement that no download is happening.
    if backbone == "dinov2_vits14":
        os.environ.setdefault("HF_HUB_OFFLINE", "1")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model, tfm, size = ef.build(backbone)
    model = model.to(device)
    dim = ef.probe_dim(model, size, device=device)
    assert dim == ef.BACKBONES[backbone]["dim"], (dim, backbone)
    feats, labels, secs = ef.extract(model, tfm, size, stream(Xc, y), Xc.shape[0],
                                     device, batch, dim, log_every=5000)
    return feats, labels, secs, device, dim


def pair_block(backbone: str, sigma: float, batch: int, verbose: bool = True) -> dict:
    t_start = time.perf_counter()
    loaded = m2.load_cached("cifar100", backbone)
    X_tr, y_tr, X_te, y_te = loaded["train"], loaded["train_y"], loaded["test"], loaded["test_y"]
    Xraw, yraw = ef.Cifar100()._raw["test"]
    if not np.array_equal(yraw, y_te):
        raise SystemExit("test labels from the archive do not match the cached feature labels - "
                         "the two runs would be scoring different orders")
    Xc = corrupted_images(Xraw, sigma, SEED)
    if verbose:
        print(f"{backbone:14s} corrupting {Xc.shape[0]} test images at sigma={sigma}", flush=True)
    Fc, lab_c, secs_ex, device, dim = extract_corrupted(backbone, Xc, y_te, batch)
    if not np.array_equal(lab_c, y_te):
        raise SystemExit("corrupted extraction reordered the test split")
    shift = float(np.mean(np.abs(Fc.astype(np.float64) - X_te.astype(np.float64))))
    if verbose:
        print(f"{backbone:14s} corrupted features extracted in {secs_ex:.0f} s on {device}; "
              f"mean |feature shift| {shift:.4f}", flush=True)

    best = m2.best_from_selection(m2.ROOT / "runs" / "m2_matrix", "cifar100", backbone)
    cap = int(len(np.unique(y_tr)) - 1)
    shared, _ = m2.fit_shared(X_tr, y_tr)
    by_delta: dict[float, list] = {}
    for method, (delta, K, _hold) in best.items():
        by_delta.setdefault(delta, []).append((method, K))

    rows, caches = [], {}
    for delta, items in sorted(by_delta.items()):
        k_max = max(K for _, K in items)
        t0 = time.perf_counter()
        caches[delta], secs = m2.fit_projections(X_tr, y_tr, delta, k_max, shared=shared)
        if verbose:
            print(f"{backbone:14s} delta={delta}: solved for K<={k_max} in "
                  f"{time.perf_counter() - t0:.0f} s", flush=True)
    for method, (delta, K, hold) in sorted(best.items()):
        basis = m2.basis_for(method, K, cap, caches[delta], X_tr, y_tr, delta)
        # one head fit per arm, evaluated on both splits: the head is what makes this expensive, and
        # the whole point is that the SAME clean-fitted head is applied to the shifted features.
        P_tr = X_tr if basis is None else X_tr @ basis
        predict = bl.logistic_head(P_tr, y_tr)
        clean = float(np.mean(predict(X_te if basis is None else X_te @ basis) == y_te))
        corrupt = float(np.mean(predict(Fc if basis is None else Fc @ basis) == y_te))
        rows.append({"method": method, "delta": delta, "K": K,
                     "realized_dim": int(P_tr.shape[1]),
                     "accuracy_clean_test": round(clean, 4),
                     "accuracy_corrupted_test": round(corrupt, 4),
                     "drop": round(corrupt - clean, 4),
                     "holdout_clean": hold,
                     "clean_reference_stage_03b": CLEAN_REFERENCE[backbone][method],
                     "clean_reproduces_reference":
                         abs(clean - CLEAN_REFERENCE[backbone][method]) < 5e-4})
    drift = [r["method"] for r in rows if not r["clean_reproduces_reference"]]
    if drift:
        raise SystemExit(f"{backbone}: the clean-test column does not reproduce stage_03b section "
                         f"3.1 for {drift}; this script would be measuring a different pipeline, so "
                         f"its corrupted column means nothing")
    predict_np = bl.logistic_head(X_tr, y_tr)
    no_proj_clean = float(np.mean(predict_np(X_te) == y_te))
    no_proj_corrupt = float(np.mean(predict_np(Fc) == y_te))

    def rank(key: str) -> list[str]:
        return [r["method"] for r in sorted(rows, key=lambda r: -r[key])]

    go = next(r for r in rows if r["method"] == "GO-LDA")
    base = [r for r in rows if r["method"] != "GO-LDA"]
    best_clean = max(base, key=lambda r: r["accuracy_clean_test"])
    best_corrupt = max(base, key=lambda r: r["accuracy_corrupted_test"])
    return {
        "dataset": "cifar100", "backbone": backbone, "feature_dim": dim,
        "train_rows": int(X_tr.shape[0]), "test_rows": int(X_te.shape[0]), "C": cap + 1,
        "cap": cap,
        "extraction_seconds": round(secs_ex, 1), "device": device,
        "mean_abs_feature_shift": round(shift, 6),
        "arms": rows,
        "no_projection": {"accuracy_clean_test": round(no_proj_clean, 4),
                          "accuracy_corrupted_test": round(no_proj_corrupt, 4),
                          "note": "reference arm: how much of the drop is the shift itself, with no "
                                  "projection in the path"},
        "rank_clean": rank("accuracy_clean_test"),
        "rank_corrupted": rank("accuracy_corrupted_test"),
        "ranking_preserved": rank("accuracy_clean_test") == rank("accuracy_corrupted_test"),
        "go_minus_best_baseline": {
            "clean": round(go["accuracy_clean_test"] - best_clean["accuracy_clean_test"], 4),
            "corrupted": round(go["accuracy_corrupted_test"] - best_corrupt["accuracy_corrupted_test"], 4),
            "best_baseline_clean": best_clean["method"],
            "best_baseline_corrupted": best_corrupt["method"]},
        "seconds": round(time.perf_counter() - t_start, 1),
    }


def payload_for(backbones: dict, sigma: float) -> dict:
    return {
        "question": "does the method ranking survive a distribution shift it was never fitted for "
                    "(plan section 4's out-of-distribution control, option A of U010)",
        "corruption": {"kind": NOISE_KIND, "sigma_on_unit_pixels": sigma,
                       "applied_at": "native 32 x 32 uint8 test images, before the backbone's "
                                     "resize / ToTensor / Normalize",
                       "severity_choice": "one level, fixed here before any arm was scored; the "
                                          "levels were not swept, so a null result stays a null result",
                       "severity_reference": "0.08 is severity 1 of the gaussian corruption in "
                                             "ImageNet-C (Hendrycks & Dietterich 2019, "
                                             "arXiv:1903.12261; corruptions.py uses "
                                             "c = [.08, .12, .18, .26, .38] on images divided by 255, "
                                             "which is the same arithmetic as corrupted_images)",
                       "noise_seed": SEED,
                       "shared_across_backbones": "the same noise field is applied once, so the two "
                                                  "backbone rows differ only in backbone"},
        "protocol": "projections, scalers and logistic heads fitted on CLEAN train exactly as in M2 "
                    "(each method at its own selected delta and K from selection.csv), then evaluated "
                    "on the corrupted test features. Nothing is refitted on the shift.",
        "reference": "the clean-test column reproduces stage_03b section 3.1, which is the check that "
                     "this script's pipeline is the same pipeline that produced the table",
        "backbones": backbones,
        "total_seconds": round(sum(b["seconds"] for b in backbones.values()), 1),
        "written_by": "src/probe_m2_ood.py",
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="cifar100", choices=["cifar100"],
                    help="only CIFAR-100 is wired: the corruption is defined on its native 32 x 32 "
                         "test array, and adding Tiny ImageNet would make the severity ambiguous")
    ap.add_argument("--backbone", default="both", choices=["resnet18", "dinov2_vits14", "both"])
    ap.add_argument("--sigma", type=float, default=SIGMA)
    ap.add_argument("--batch", type=int, default=ef.BATCH)
    ap.add_argument("--out", type=str, default=str(OUT))
    args = ap.parse_args(argv)

    backbones = ([args.backbone] if args.backbone != "both"
                 else ["resnet18", "dinov2_vits14"])
    out_path = Path(args.out)
    # each block is written as it lands, and a previous run's blocks are kept, because the first
    # attempt at this control computed ResNet-18 in twelve minutes and then lost the artefact to a
    # DINOv2 weight-resolution crash on the next line
    blocks = {}
    if out_path.is_file():
        blocks = json.loads(out_path.read_text(encoding="utf-8")).get("backbones", {})
    for b in backbones:
        if b in blocks and blocks[b].get("arms"):
            print(f"{b:14s} reusing the block already in {out_path.name}", flush=True)
            continue
        blocks[b] = pair_block(b, args.sigma, args.batch)
        out_path.write_text(json.dumps(payload_for(blocks, args.sigma), indent=2, default=float),
                            encoding="utf-8")
        print(f"{b:14s} clean rank {blocks[b]['rank_clean']} -> corrupted rank "
              f"{blocks[b]['rank_corrupted']}", flush=True)

    payload = payload_for(blocks, args.sigma)
    payload["sigma_note"] = ("every block in this file was scored at the sigma above; if a block was "
                             "reused from an earlier invocation, its own arms carry the delta and K it "
                             "was fitted at")
    out_path.write_text(json.dumps(payload, indent=2, default=float), encoding="utf-8")
    print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
