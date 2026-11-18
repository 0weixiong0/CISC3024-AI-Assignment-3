"""Demo data for the Stage-4 front end: `webapp/demo.js` -> `window.GOLDA_DEMO`.

This is not `src/export_results.py` (WP8). That exporter publishes the *report's* tables and refuses to
write when a check fails; this one publishes what a person in a browser can poke at: real specimens, the
directions the algorithm actually built, the Gram matrix of a basis, the Fisher ratio per direction, and
where a chosen image's class ranks as the subspace grows. Both read the same artefacts or refit the same
fitted objects; neither invents a number.

What is precomputed, and why so small:

* **specimens** - a class-stratified subsample of the *official test* rows with their thumbnail, so the
  page can show what is being classified instead of a bar chart of it;
* **per-direction readouts** - Fisher ratio `mu_k` and the off-diagonal mass of `U'U` at each grid `K`,
  which is H3's quantity measured on the basis the demo is drawing;
* **projections** - the specimens' coordinates in the first two directions of each arm, plus their
  nearest-class-mean rank in the first `K` directions. The rank is the readout that moves with `K`; the
  first two coordinates do not, because a prefix-ordered basis adds directions without rotating the
  earlier ones, and the page says that instead of faking motion;
* **ORL direction images** - the only place a discriminant direction is a picture, so the page can show
  GO-LDA's direction 7 next to classic LDA's.

Accuracy per (`K`, delta, split) is copied from `runs/m2_matrix/accuracy_rows.csv` and `cv_summary.csv`,
never recomputed with a different head than the study used.

    python src/export_demo.py                          # ORL + all four feature pairs
    python src/export_demo.py --pairs orl              # one block while iterating on the page
    python src/export_demo.py --specimens 120

Artefacts: webapp/demo.js, webapp/demo_meta.json
"""

from __future__ import annotations

import argparse
import base64
import csv
import io
import json
import sys
import time
import zipfile
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import baselines as bl                                # noqa: E402
import extract_features as ef                         # noqa: E402
import golda                                          # noqa: E402
import orl as orl_mod                                 # noqa: E402
import run_m2_matrix as m2                           # noqa: E402

num = m2.num if hasattr(m2, "num") else (lambda v: None if v in (None, "", "n/a") else float(v))

OUT_JS = ROOT / "webapp" / "demo.js"
OUT_META = ROOT / "webapp" / "demo_meta.json"
SEED = m2.SEED
N_SPECIMENS = 240
ORL_DIRECTIONS_AS_IMAGE = 40
QUANT = 4
ORL_K_GRID = (1, 5, 10, 20, 30, 39, 40, 50)
ORL_DELTA = 0.005          # the ridge the MVP's arms were selected at on fold 0's training rows


# ---------------------------------------------------------------- small helpers
def png_data_url(arr: np.ndarray, mode: str = "RGB") -> str:
    img = Image.fromarray(np.ascontiguousarray(arr.astype(np.uint8)), mode=mode)
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def stratified_rows(y: np.ndarray, n: int, rng: np.random.Generator) -> np.ndarray:
    """`n` rows spread over the classes, so nobody concludes anything from a class that is absent."""
    per = max(1, int(round(n / len(np.unique(y)))))
    take: list[int] = []
    for c in np.unique(y):
        idx = np.flatnonzero(y == c)
        take.extend(rng.choice(idx, size=min(per, len(idx)), replace=False).tolist())
    out = np.array(sorted(take[:n]), dtype=int)
    return out


def gram_offdiag(U: np.ndarray) -> float:
    if U.shape[1] < 2:
        return 0.0
    g = U.T @ U
    return float(np.max(np.abs(g - np.diag(np.diag(g)))))


def first_two(P: np.ndarray) -> np.ndarray:
    k = min(2, P.shape[1])
    out = np.zeros((P.shape[0], 2), dtype=np.float64)
    out[:, :k] = P[:, :k]
    return out


def ncm_rank(P_fit: np.ndarray, y_fit: np.ndarray, P_ev: np.ndarray, y_ev: np.ndarray,
             classes: np.ndarray) -> list[int]:
    """1-based rank of the true class among the nearest-class-mean distances."""
    means = np.stack([P_fit[y_fit == c].mean(axis=0) for c in classes])
    d = ((P_ev[:, None, :] - means[None, :, :]) ** 2).sum(axis=2)
    order = np.argsort(d, axis=1)
    rank = np.empty(len(y_ev), dtype=int)
    for row, c in enumerate(y_ev):
        rank[row] = int(np.flatnonzero(order[row] == c)[0]) + 1
    return rank.tolist()


def maybe_float(v):
    """The summary CSVs write n/a where an arm has no hyper-parameter to report."""
    if v in (None, "", "n/a"):
        return None
    return float(v)


GRAM_N = 24          # U'U is shown as a GRAM_N x GRAM_N block: enough to see the off-diagonal


def gram_block(U: np.ndarray, k: int = GRAM_N) -> list[list[float]]:
    """The first k x k corner of U'U: identity for an orthogonal basis, smeared for classic LDA's."""
    Uk = U[:, :min(k, U.shape[1])]
    g = (Uk.T @ Uk) if Uk.shape[1] else np.zeros((0, 0))
    out = [[round(float(v), 3) for v in row] for row in g]
    pad = [[0.0] * k for _ in range(k - len(out))] if len(out) < k else []
    return [row + [0.0] * (k - len(row)) for row in out] + pad


def q2(P: np.ndarray) -> list[list[float]]:
    return [[round(float(a), QUANT), round(float(b), QUANT)] for a, b in first_two(P)]


# ---------------------------------------------------------------- accuracy lookups
def accuracy_index(dataset: str, backbone: str) -> dict:
    """(method, delta, K) -> the study's own numbers, copied from the run tables, never recomputed.

    `accuracy_rows.csv` is long: one row per (method, delta, K, split). `cv_summary.csv` is keyed on the
    *selection*, so the fold statistics exist only at each method's own selected (delta, K) and stay None
    elsewhere - a demo that implied CV coverage at every K would be lying about the grid.
    """
    out: dict[tuple, dict] = {}
    with (m2.OUT / "accuracy_rows.csv").open(encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r["dataset"] != dataset or r["backbone"] != backbone:
                continue
            key = (r["method"], maybe_float(r["delta"]), int(r["K"]))
            cell = out.setdefault(key, {})
            split, value = r["split"], maybe_float(r["accuracy"])
            if split in ("holdout-5%", "holdout"):
                cell["holdout"] = value
            elif split in ("official-test", "test"):
                cell["test"] = value
            else:
                cell.setdefault("other_splits", {})[split] = value
    # the official-test score exists only where the protocol spent it: at each method's own selection
    with (m2.OUT / "selection.csv").open(encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r["dataset"] != dataset or r["backbone"] != backbone:
                continue
            key = (r["method"], maybe_float(r["selected_delta"]), int(r["selected_K"]))
            cell = out.setdefault(key, {})
            cell["test"] = maybe_float(r["test_accuracy"])
            cell["holdout"] = maybe_float(r["holdout_accuracy"]) or cell.get("holdout")
            cell["at_selection"] = True
            cell["realized_dim"] = maybe_float(r["realized_dim"])
    p = m2.OUT / "cv_summary.csv"
    if p.is_file():
        with p.open(encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                if r["dataset"] != dataset or r["backbone"] != backbone:
                    continue
                key = (r["method"], maybe_float(r["selected_delta"]), int(r["selected_K"]))
                out.setdefault(key, {}).update(
                    {"cv_mean": maybe_float(r["mean"]), "cv_sd": maybe_float(r["sd"]),
                     "cv_min": maybe_float(r["min"]), "cv_max": maybe_float(r["max"]),
                     "cv_folds": int(num(r["folds"]) or 0)})
    return out


def k_grid_for(dataset: str, backbone: str) -> list[int]:
    ks = {k[2] for k in accuracy_index(dataset, backbone)}
    return sorted(ks)


# ---------------------------------------------------------------- feature pairs
def feature_pair_block(dataset: str, backbone: str, specimens: int, log) -> dict:
    t_start = time.perf_counter()
    loaded = m2.load_cached(dataset, backbone)
    X_tr, y_tr, X_te, y_te = loaded["train"], loaded["train_y"], loaded["test"], loaded["test_y"]
    best = m2.best_from_selection(m2.OUT, dataset, backbone)
    cap = int(len(np.unique(y_tr)) - 1)
    classes = np.unique(y_tr)
    acc = accuracy_index(dataset, backbone)
    k_grid = k_grid_for(dataset, backbone)
    log(f"  {dataset}/{backbone}: {len(k_grid)} K values {k_grid}, "
        f"{len(acc)} (method, delta, K) cells, "
        f"{sum(1 for v in acc.values() if v.get('test') is not None)} with a test score")

    rng = np.random.default_rng(SEED)
    sel = stratified_rows(y_te, specimens, rng)
    Xs, ys = X_te[sel], y_te[sel]

    shared, _ = m2.fit_shared(X_tr, y_tr)
    # solve each delta group to the top of the K grid, not merely to the selected K: the demo draws
    # every grid point, and a row labelled K = 512 measured on a 256-column basis would be a silent lie
    # Only GO-LDA is solved direction by direction, so only the delta group that carries GO-LDA needs
    # the top of the K grid. The classic arms stop at the cap on their own, and asking their group for
    # K = 512 would spend ten minutes of deflations on prefixes nothing reads.
    k_top = max(k_grid)
    by_delta: dict[float, int] = {}
    for method, (delta, K, _h) in best.items():
        need = k_top if method == "GO-LDA" else min(k_top, cap)
        by_delta[delta] = max(by_delta.get(delta, 0), need, K)
    caches = {}
    for delta, k_max in sorted(by_delta.items()):
        t0 = time.perf_counter()
        caches[delta], _ = m2.fit_projections(X_tr, y_tr, delta, k_max, shared=shared)
        log(f"  {dataset}/{backbone}: bases at delta={delta} solved in {time.perf_counter() - t0:.0f} s")

    arms = {}
    for method, (delta, K_sel, _h) in sorted(best.items()):
        cache = caches[delta]
        identity = method == "no-projection"
        if identity:
            U_full = np.eye(X_tr.shape[1])
        elif method == "PCA-then-LDA":
            U_full = None          # its basis is a function of K, so it is solved inside the loop
        else:
            want_k = max(k_grid) if method == "GO-LDA" else cap
            U_full = m2.basis_for(method, want_k, cap, cache, X_tr, y_tr, delta)
        mu_key = {"GO-LDA": "go", "classic-ridge-LDA": "classic",
                  "classic-shrinkage-LDA": "shrunk"}.get(method)
        mu = list(np.asarray(cache[mu_key]["mu"], dtype=float)) if mu_key else []
        per_k, ranks = [], []
        for K in k_grid:
            if identity:
                Uk = np.eye(X_tr.shape[1])
            elif U_full is None:
                Uk = m2.basis_for(method, K, cap, cache, X_tr, y_tr, delta)
            else:
                Uk = U_full[:, :min(K, U_full.shape[1])]
            P_fit = X_tr @ Uk
            P_ev = Xs @ Uk
            got = acc.get((method, delta, K), {})
            per_k.append({"K": K, "dim": int(Uk.shape[1]),
                          "offdiag": round(gram_offdiag(Uk), 10),
                          "holdout": got.get("holdout"), "test": got.get("test"),
                          "cv_mean": got.get("cv_mean"), "cv_sd": got.get("cv_sd"),
                          "cv_min": got.get("cv_min"), "cv_max": got.get("cv_max"),
                          "cv_folds": got.get("cv_folds"),
                          "at_selection": bool(got.get("at_selection")),
                          "realized_dim": got.get("realized_dim")})
            ranks.append({"K": K, "rank": ncm_rank(P_fit, y_tr, P_ev, ys, classes)})
            if K == k_grid[0]:
                xy = q2(P_ev)
        arms[method] = {
            "selected_delta": delta, "selected_K": K_sel, "identity": identity,
            "fisher_mu": [round(float(v), 6) for v in mu],
            "at_K": per_k, "ncm_rank_by_K": ranks, "xy_first_two": xy,
            # PCA-then-LDA's basis is a function of K, so U_full is None outside the loop
            "gram_at_selected_K": gram_block(U_full if U_full is not None else
                                             m2.basis_for(method, K_sel, cap, cache, X_tr, y_tr, delta),
                                             GRAM_N),
        }
    secs = time.perf_counter() - t_start
    log(f"  {dataset}/{backbone}: arms built in {secs:.0f} s")
    return {
        "regime": "frozen features", "dataset": dataset, "backbone": backbone,
        "C": int(len(classes)), "cap": cap, "feature_dim": int(X_tr.shape[1]),
        "k_grid": k_grid, "arms": arms, "seconds": round(secs, 1),
        "specimens": feature_specimens(dataset, sel, ys, log),
        "noisy_specimens": noisy_thumbnails(dataset, sel, ys, log),
        "class_names": class_names(dataset),
        "heads": {"accuracy": "L2 logistic, the study's head",
                  "rank": "nearest class mean, this readout only"},
    }


def feature_specimens(dataset: str, idx: np.ndarray, ys: np.ndarray, log) -> list[dict]:
    """Thumbnails of the subsampled test rows, straight from the released archives."""
    arrs = None
    try:
        if dataset == "cifar100":
            X, _ = ef.Cifar100()._raw["test"]
            arrs = X[idx]
        else:
            src = ef.TinyImageNet()
            pos = {int(v): n for n, v in enumerate(idx)}
            arrs = [None] * len(idx)
            with zipfile.ZipFile(src.path) as zf:
                for n, (name, _label) in enumerate(src._index["test"]):
                    if n in pos and arrs[pos[n]] is None:
                        with Image.open(io.BytesIO(zf.read(name))) as im:
                            arrs[pos[n]] = np.asarray(
                                im.convert("RGB").resize((32, 32), Image.LANCZOS))
                    if all(a is not None for a in arrs):
                        break
    except Exception as exc:
        log(f"  {dataset}: thumbnails unavailable ({type(exc).__name__}: {exc}); labels only")
        arrs = None
    if arrs is None:
        return [{"i": int(i), "y": int(v), "img": None} for i, v in zip(idx, ys)]
    return [{"i": int(i), "y": int(v), "img": png_data_url(a)} for i, v, a in zip(idx, ys, arrs)]




def class_names(dataset: str) -> list[str] | None:
    """CIFAR-100's own fine-label names, read from the released archive; Tiny ImageNet ships synset
    ids, which are not readable, so its specimens stay numbered rather than inventing words."""
    if dataset != "cifar100":
        return None
    try:
        import tarfile
        with tarfile.open(ef.Cifar100.path, "r:gz") as tf:
            base = tf.getnames()[0]
            obj = np.load(io.BytesIO(tf.extractfile(f"{base}/meta").read()),
                          allow_pickle=True, encoding="bytes")
            meta = obj.item() if isinstance(obj, np.ndarray) and obj.shape == () else obj
            meta = {(k.decode() if isinstance(k, bytes) else k): v for k, v in meta.items()}
            names = [n.decode() if isinstance(n, bytes) else str(n) for n in meta["fine_label_names"]]
            return names if len(names) == 100 else None
    except Exception:
        return None


def noisy_thumbnails(dataset: str, idx: np.ndarray, ys: np.ndarray, log, how_many: int = 12) -> list[dict]:
    """The out-of-distribution control's pixels, for the demo's before/after slider.

    Same sigma, same seed, same function as `src/probe_m2_ood.py`, so what the page shows is the image
    the measured accuracy was earned on rather than a decorative approximation of it.
    """
    if dataset != "cifar100":
        return []
    try:
        import probe_m2_ood as ood
        X, _ = ef.Cifar100()._raw["test"]
        Xc = ood.corrupted_images(X, ood.SIGMA, ood.SEED)
        take = idx[:how_many]
        return [{"i": int(i), "y": int(ys[np.flatnonzero(idx == i)[0]]),
                 "sigma": ood.SIGMA, "img": png_data_url(Xc[i])} for i in take]
    except Exception as exc:
        log(f"  {dataset}: noisy thumbnails skipped ({type(exc).__name__}: {exc})")
        return []


# ---------------------------------------------------------------- ORL: directions are pictures
def orl_block(fold: int, log) -> dict:
    t_start = time.perf_counter()
    X, y = orl_mod.load_orl()
    folds = orl_mod.stratified_k_fold(y, 10, SEED)
    tr, te = folds[fold]
    Xtr, ytr, Xte, yte = X[tr], y[tr], X[te], y[te]
    classes = np.unique(ytr)
    cap = len(classes) - 1
    H, W = orl_mod.IMG_H, orl_mod.IMG_W
    n_dir = ORL_DIRECTIONS_AS_IMAGE

    go = golda.go_lda(Xtr, ytr, K=n_dir, delta=ORL_DELTA, route="reduced")
    log(f"  orl: GO-LDA {n_dir} directions in {time.perf_counter() - t_start:.0f} s")
    cl = golda.classic_lda_pencil(Xtr, ytr, delta=ORL_DELTA, route="reduced")
    shrunk = golda.classic_lda_pencil(Xtr, ytr, delta=0.0, route="reduced", shrinkage=0.1)
    U = {"GO-LDA": np.asarray(go["U"], float),
         "classic-ridge-LDA": np.asarray(cl["U"], float),
         "classic-shrinkage-LDA": np.asarray(shrunk["U"], float)}

    acc = orl_accuracy()
    arms = {}
    for name, Uf in U.items():
        per_k = [{"K": K, "dim": int(min(K, Uf.shape[1])),
                  "capped": bool(K > Uf.shape[1]),
                  "offdiag": round(gram_offdiag(Uf[:, :min(K, Uf.shape[1])]), 10),
                  **orl_lookup(acc, name, K, ORL_DELTA)}
                 for K in ORL_K_GRID]
        Pfit1 = Xtr @ Uf[:, :1]
        arms[name] = {
            "selected_delta": ORL_DELTA if name != "classic-shrinkage-LDA" else 0.0,
            "fisher_mu": [round(float(v), 6) for v in np.asarray(
                {"GO-LDA": go, "classic-ridge-LDA": cl, "classic-shrinkage-LDA": shrunk}[name]["mu"],
                dtype=float)],
            "at_K": per_k,
            "ncm_rank_by_K": [{"K": r["K"], "dim": r["dim"],
                               "rank": ncm_rank(Xtr @ Uf[:, :r["dim"]], ytr,
                                                Xte @ Uf[:, :r["dim"]], yte, classes)}
                              for r in per_k],
            "xy_first_two": q2(Xte @ Uf),
            "gram_at_selected_K": gram_block(Uf, GRAM_N),
        }
    span = golda.principal_angle(U["GO-LDA"][:, :cap], U["classic-ridge-LDA"][:, :cap])
    secs = time.perf_counter() - t_start
    log(f"  orl: block built in {secs:.0f} s (span at cap {span:.3g} deg)")
    return {
        "regime": "raw pixels", "dataset": "orl", "C": len(classes), "cap": cap,
        "feature_dim": int(X.shape[1]), "image": [H, W], "k_grid": list(ORL_K_GRID),
        "arms": arms, "seconds": round(secs, 1), "fold": fold, "delta": ORL_DELTA,
        "span_at_cap_deg": round(float(span), 6),
        "direction_images": {name: [png_data_url(_as_gray(Uf[:, k], H, W), "L")
                                    for k in range(min(n_dir, Uf.shape[1]))]
                             for name, Uf in U.items()},
        "specimens": [{"i": int(i), "y": int(v), "img": png_data_url(Xte[i].reshape(H, W), "L")}
                      for i, v in enumerate(yte)],
        "heads": {"accuracy": "1-NN, the paper's Table II protocol",
                  "rank": "nearest class mean, this readout only"},
        "note": f"fitted on the {len(tr)} training images of fold {fold} of the MVP's own ten-fold "
                f"schedule; the {len(te)} held-out images are the specimens",
    }


def _as_gray(v: np.ndarray, h: int, w: int) -> np.ndarray:
    a = v.reshape(h, w).astype(np.float64)
    lo, hi = a.min(), a.max()
    if hi - lo < 1e-12:
        return np.zeros((h, w), dtype=np.uint8)
    return ((a - lo) / (hi - lo) * 255.0).astype(np.uint8)


def orl_accuracy() -> list[dict]:
    p = ROOT / "runs" / "mvp_orl" / "accuracy_summary.csv"
    with p.open(encoding="utf-8") as fh:
        return [r for r in csv.DictReader(fh)]


def orl_lookup(rows: list[dict], method: str, K: int, delta: float) -> dict:
    hits = [r for r in rows if r["method"] == method and int(r["K"]) == K
            and maybe_float(r["delta"]) == delta and r.get("head", "1-NN").startswith("1-NN")]
    if not hits:
        return {"cv_mean": None, "cv_sd": None, "cv_min": None, "cv_max": None, "delta": None}
    r = hits[0]
    return {"cv_mean": maybe_float(r["mean"]), "cv_sd": maybe_float(r["sd"]),
            "cv_min": maybe_float(r["min"]), "cv_max": maybe_float(r["max"]),
            "delta": maybe_float(r["delta"]), "head": r.get("head")}


# ---------------------------------------------------------------- static readouts from artefacts
def static_blocks(log) -> dict:
    """The two U010 controls and the export gate, passed through so the demo can show its receipts."""
    out = {}
    p = m2.OUT / "probe_ood.json"
    if p.is_file():
        raw = json.loads(p.read_text(encoding="utf-8"))
        out["ood"] = {"split": "official test under one fixed corruption",
                      "corruption": raw.get("corruption"), "protocol": raw.get("protocol"),
                      "backbones": {b: {"arms": [{k: a[k] for k in
                                                  ("method", "accuracy_clean_test",
                                                   "accuracy_corrupted_test", "drop", "K", "delta")}
                                                 for a in blk["arms"]],
                                        "no_projection": blk.get("no_projection"),
                                        "rank_clean": blk.get("rank_clean"),
                                        "rank_corrupted": blk.get("rank_corrupted"),
                                        "ranking_preserved": blk.get("ranking_preserved"),
                                        "go_minus_best_baseline": blk.get("go_minus_best_baseline"),
                                        "mean_abs_feature_shift": blk.get("mean_abs_feature_shift")}
                                    for b, blk in raw.get("backbones", {}).items()}}
        log("  ood control carried into the demo")
    # runs/orl512/ was box-averaged on a transposed pixel grid (IMG_H/IMG_W were swapped in
    # src/orl.py); runs/orl512_fix/ is the same ladder re-measured after that fix.
    q = ROOT / "runs" / "orl512_fix" / "orl512_ladder.json"
    if q.is_file():
        raw = json.loads(q.read_text(encoding="utf-8"))
        out["ladder"] = {"split": "ORL raw pixels, ten folds, 1-NN", "question": raw.get("question"),
                         "rungs": raw.get("ladder"),
                         "feature_regime_reference": raw.get("feature_regime_reference"),
                         "full_dimension_reference": raw.get("full_dimension_reference"),
                         "source": q.relative_to(ROOT).as_posix(), "dim_rule": raw.get("dim_rule"),
                         "wall_clock_s": raw.get("wall_clock_s")}
        log("  orl ladder carried into the demo")
    return out


def load_existing(out: Path) -> dict:
    """A partial run (--pairs orl) repairs one block; it must not throw the others away."""
    if not out.is_file():
        return {}
    import re
    m = re.search(r"window\.GOLDA_DEMO = (\{.*\});?\s*$", out.read_text(encoding="utf-8"), re.S)
    try:
        return json.loads(m.group(1)) if m else {}
    except json.JSONDecodeError:
        return {}


def dump(payload: dict, out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("/* generated by src/export_demo.py - demo data; regenerate, do not edit */\n"
                   "window.GOLDA_DEMO = "
                   + json.dumps(payload, ensure_ascii=False, separators=(",", ":"), default=float)
                   + ";\n", encoding="utf-8", newline="\n")


# ---------------------------------------------------------------- main
def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pairs", default="orl," + ",".join(
        f"{d}__{b}" for d in ("cifar100", "tiny_imagenet")
        for b in ("resnet18", "dinov2_vits14")))
    ap.add_argument("--specimens", type=int, default=N_SPECIMENS)
    ap.add_argument("--orl-fold", type=int, default=0)
    ap.add_argument("--out", default=str(OUT_JS))
    ap.add_argument("--meta", default=str(OUT_META))
    ap.add_argument("--fresh", action="store_true",
                    help="ignore any existing demo.js instead of merging blocks into it")
    args = ap.parse_args(argv)

    def log(*a):
        print(*a, flush=True)

    payload = {
        "title": "GO-LDA, live: build the subspace and watch what it is worth",
        "seed": SEED, "written_by": "src/export_demo.py",
        "protocol": {
            "selection": "5 % hold-out of train chooses (delta, K); the official test split is scored "
                         "once per method after refitting on all of train",
            "study_head": "L2 logistic regression in the C4 configuration - every number labelled "
                          "holdout / test / cv",
            "demo_rank": "nearest class mean - the per-specimen rank readout only",
        },
        "blocks": {},
    }
    t0 = time.perf_counter()
    out = Path(args.out)
    if not args.fresh:
        prev = load_existing(out)
        for k, v in (prev.get("blocks") or {}).items():
            payload["blocks"].setdefault(k, v)     # blocks built this run win
    for key in [p.strip() for p in args.pairs.split(",") if p.strip()]:
        if key == "orl":
            payload["blocks"]["orl"] = orl_block(args.orl_fold, log)
        else:
            ds, bb = key.split("__")
            payload["blocks"][key] = feature_pair_block(ds, bb, args.specimens, log)
        # write after every block: this run refits for tens of minutes, and a crash on the last
        # pair should not be allowed to throw away the pairs that already landed
        dump(payload, out)
        log(f"  checkpoint: {len(payload['blocks'])} block(s) in {out.name}")
    payload["static"] = static_blocks(log)
    payload["total_seconds"] = round(time.perf_counter() - t0, 1)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("/* generated by src/export_demo.py - demo data; regenerate, do not edit */\n"
                   "window.GOLDA_DEMO = "
                   + json.dumps(payload, ensure_ascii=False, separators=(",", ":"), default=float)
                   + ";\n", encoding="utf-8", newline="\n")
    Path(args.meta).write_text(json.dumps({
        "written_by": "src/export_demo.py", "total_seconds": payload["total_seconds"], "seed": SEED,
        "specimens_per_pair": args.specimens, "orl_fold": args.orl_fold,
        "bytes": out.stat().st_size,
        "blocks": {k: {"seconds": v.get("seconds"), "arms": sorted(v.get("arms", {})),
                       "k_grid": v.get("k_grid"), "cap": v.get("cap"),
                       "feature_dim": v.get("feature_dim"),
                       "specimens": len(v.get("specimens", []))}
                   for k, v in payload["blocks"].items()},
    }, indent=2), encoding="utf-8")
    print(f"\nwrote {out} ({out.stat().st_size / 1024 / 1024:.2f} MiB) in {payload['total_seconds']} s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
