"""Render the two figures this study measured itself, for the report's results section.

Project : CISC3024 AI Assignment #3 (Pattern Recognition, University of Macau)
Author  : AI-generated implementation (Qoder). The student wrote no code.

figure_08 - the growth curves. One panel per feature pair, hold-out accuracy against K for all four
methods, with the official test point of each method's selected configuration drawn as a diamond. The
hold-out and test values come from different splits and are drawn differently on purpose: the curve is
what selection saw, the diamond is what the report concludes from, and a figure that merged them would
restate the mistake the records keep warning about.

figure_09 - the ORL first directions. GO-LDA's first discriminant direction and the classical pencil's
leading eigenvector, both as 112 x 92 images, refitted here from the MVP's own fold 0 with the study's
own solver, so the picture is the fitted object rather than a saved thumbnail.

Both write a manifest entry with the artefact they were built from, and both are re-runnable.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import golda
import orl as orl_mod

ROOT = Path(__file__).resolve().parent.parent
RUNS = ROOT / "runs"
ASSETS = ROOT / "report_assets"
SEED = 20261117
ORL_DELTA = 0.005
METHODS = ["GO-LDA", "classic-ridge-LDA", "classic-shrinkage-LDA", "PCA-then-LDA"]
STYLE = {"GO-LDA": ("#1f4e79", "-o"), "classic-ridge-LDA": ("#c0504d", "--s"),
         "classic-shrinkage-LDA": ("#7f7f7f", "-.^"), "PCA-then-LDA": ("#4f81bd", ":v")}
NAMES = {"cifar100": "CIFAR-100", "tiny_imagenet": "Tiny ImageNet",
         "resnet18": "ResNet-18", "dinov2_vits14": "DINOv2 ViT-S/14"}


def cap_of(pair) -> int:
    """The rank cap C - 1 of a pair, from the matrix diagnostics."""
    diag = json.loads((RUNS / "m2_matrix/diagnostics.json").read_text(encoding="utf-8"))
    return next(p["cap"] for p in diag["per_pair"] if (p["dataset"], p["backbone"]) == pair)


def growth_curve(out: Path) -> dict:
    rows = list(csv.DictReader((RUNS / "m2_matrix/accuracy_rows.csv").open(encoding="utf-8")))
    sel = list(csv.DictReader((RUNS / "m2_matrix/selection.csv").open(encoding="utf-8")))
    pairs = [("cifar100", "resnet18"), ("cifar100", "dinov2_vits14"),
             ("tiny_imagenet", "resnet18"), ("tiny_imagenet", "dinov2_vits14")]
    fig, axes = plt.subplots(2, 2, figsize=(9.2, 6.4), sharex=False)
    caps = {}
    for ax, pair in zip(axes.ravel(), pairs):
        for method in METHODS:
            curve = sorted((int(r["K"]), float(r["accuracy"])) for r in rows
                           if (r["dataset"], r["backbone"], r["method"], r["split"]) ==
                           (*pair, method, "holdout-5%"))
            if not curve:
                continue
            colour, style = STYLE[method]
            ax.plot([k for k, _ in curve], [a for _, a in curve], style, color=colour,
                    markersize=3.4, linewidth=1.2, label=method.replace("-LDA", ""))
            chosen = next(r for r in sel
                          if (r["dataset"], r["backbone"], r["method"]) == (*pair, method))
            ax.scatter([int(chosen["selected_K"])], [float(chosen["test_accuracy"])], marker="D",
                       s=34, color=colour, edgecolor="black", linewidths=0.5, zorder=5)
            caps[pair[0] + pair[1] + method] = (int(chosen["selected_K"]),
                                                float(chosen["test_accuracy"]))
        ax.axvline(x=cap_of(pair), color="black", linestyle=(0, (4, 3)), linewidth=0.9, alpha=0.7)
        ax.annotate(f"cap C-1 = {cap_of(pair)}", (cap_of(pair), axes.ravel()[0].get_ylim()[0]),
                    fontsize=6, rotation=90, va="bottom", ha="right", alpha=0.8)
        ax.set_title(f"{NAMES[pair[0]]} x {NAMES[pair[1]]}", fontsize=9)
        ax.set_xlabel("K (dimensions kept)", fontsize=8)
        ax.set_ylabel("accuracy", fontsize=8)
        ax.tick_params(labelsize=7)
        ax.grid(True, linewidth=0.4, alpha=0.5)
    axes.ravel()[0].legend(fontsize=6.5, loc="lower right", ncol=2, framealpha=0.95)
    fig.text(0.01, 0.008, "lines and dots: 5 % hold-out, each method across the K grid; "
                          "diamonds: official test split at each method's own selected (delta, K). "
                          "Source: runs/m2_matrix/accuracy_rows.csv and selection.csv.", fontsize=6.5)
    fig.tight_layout(rect=(0, 0.028, 1, 1))
    fig.savefig(str(out), dpi=200)
    plt.close(fig)
    return {"selected_points": len(caps)}


def direction_pair(out: Path) -> dict:
    X, y = orl_mod.load_orl()
    folds = orl_mod.stratified_k_fold(y, 10, SEED)
    tr, te = folds[0]
    Xtr, ytr = X[tr], y[tr]
    H, W = orl_mod.IMG_H, orl_mod.IMG_W
    go = golda.go_lda(Xtr, ytr, K=2, delta=ORL_DELTA, route="reduced")
    cl = golda.classic_lda_pencil(Xtr, ytr, delta=ORL_DELTA, route="reduced")
    u_go = np.asarray(go["U"], float)[:, 0]
    u_cl = np.asarray(cl["U"], float)[:, 0]
    cos = abs(float(np.dot(u_go, u_cl) / (np.linalg.norm(u_go) * np.linalg.norm(u_cl))))
    fig, axes = plt.subplots(1, 2, figsize=(6.4, 3.0))
    for ax, vec, title in ((axes[0], u_go, "GO-LDA direction 1"),
                           (axes[1], u_cl, "classic pencil eigenvector 1")):
        grid = vec.reshape(H, W)
        lo, hi = np.percentile(grid, (1, 99))
        ax.imshow(np.clip((grid - lo) / (hi - lo), 0, 1), cmap="gray", interpolation="nearest")
        ax.set_title(title, fontsize=9)
        ax.set_xticks([])
        ax.set_yticks([])
    fig.text(0.01, 0.015, f"Refitted on ORL fold 0 (360 training images, delta = {ORL_DELTA:g}, "
                          f"112 x 92 pixels laid out as the PGM header states). "
                          f"Absolute cosine between the two directions: {cos:.6f}. "
                          f"Solver: src/golda.py, route reduced - the same call the study used.",
             fontsize=6.5)
    fig.tight_layout(rect=(0, 0.075, 1, 1))
    fig.savefig(str(out), dpi=200)
    plt.close(fig)
    return {"abs_cos_first_direction": cos, "fold": 0, "delta": ORL_DELTA, "image": [H, W]}


def main() -> int:
    ASSETS.mkdir(exist_ok=True)
    manifest_path = ASSETS / "figure_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}

    growth = ASSETS / "figure_08.png"
    info = growth_curve(growth)
    manifest["figure_08"] = {
        "source": "runs/m2_matrix/accuracy_rows.csv + selection.csv",
        "page": "rendered from this study's own run tables",
        "report_label": "numbered by a SEQ field in the report, not here",
        "caption_line_2": ("Growth curves on frozen features: hold-out accuracy against K for all four "
                           "methods, with each method's official test point at its own selected "
                           "(delta, K) drawn as a diamond."),
        "selected_points": info["selected_points"]}
    print(f"figure_08: {growth.name} ({info['selected_points']} test points)")

    directions = ASSETS / "figure_09.png"
    info = direction_pair(directions)
    manifest["figure_09"] = {
        "source": "the GO-LDA module and the ORL loader, ORL fold 0 refitted at build time",
        "page": "rendered from a fresh fit",
        "abs_cos_first_direction": info["abs_cos_first_direction"], "image": info["image"],
        "report_label": "numbered by a SEQ field in the report, not here",
        "caption_line_2": ("The first discriminant direction of GO-LDA beside the classical pencil's "
                           "leading eigenvector, both as 112 x 92 images from ORL fold 0 - the identity "
                           "equation (23) promises, seen as a picture.")}
    print(f"figure_09: {directions.name} (abs cosine "
          f"{info['abs_cos_first_direction']:.6f})")

    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
