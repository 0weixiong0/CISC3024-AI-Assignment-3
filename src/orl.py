"""ORL / AT&T Database of Faces loader.

Reads the native PGM images (112 rows x 92 columns) from the Cambridge mirror
archive, so the flattened feature dimension is M = 10,304 as used by
arXiv:2305.14568 (C/N/M = 40/400/10304).  scikit-learn's fetch_olivetti_faces is
deliberately not used: it ships a 64 x 64 resample (4,096 dims).
"""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

import numpy as np

# The PGM header writes width before height ("92 112"), so a row of the raster is 92 pixels.
IMG_H, IMG_W = 112, 92
M = IMG_H * IMG_W
N_TOTAL, N_CLASSES, N_PER_CLASS = 400, 40, 10

DEFAULT_ZIP = Path(__file__).resolve().parents[1] / "data" / "orl" / "att_faces.zip"


def _read_pgm(buf: bytes) -> np.ndarray:
    """Minimal binary PGM (P5) reader: header tokens then raw greys."""
    stream = io.BytesIO(buf)
    token = b""
    while True:
        ch = stream.read(1)
        if ch == b"#":
            stream.readline()
            continue
        token += ch
        if ch in (b" ", b"\n", b"\t"):
            break
    if token.strip() != b"P5":
        raise ValueError(f"expected P5 PGM, got {token!r}")

    dims: list[int] = []
    while len(dims) < 3:
        word = b""
        while True:
            ch = stream.read(1)
            if ch == b"":
                raise ValueError("truncated PGM header")
            if ch == b"#":
                stream.readline()
                continue
            word += ch
            if ch in (b" ", b"\n", b"\t"):
                break
        dims.append(int(word.strip()))
    width, height, _maxval = dims
    if (height, width) != (IMG_H, IMG_W):
        raise ValueError(
            f"PGM header says {width} columns x {height} rows, but IMG_H/IMG_W say "
            f"{IMG_H} x {IMG_W} - the raster would be reshaped on the wrong grid")

    pixels = np.frombuffer(stream.read(width * height), dtype=np.uint8)
    if pixels.size != width * height:
        raise ValueError(f"PGM body short: {pixels.size} != {width * height}")
    return pixels.reshape(height, width)


def load_orl(zip_path: Path = DEFAULT_ZIP) -> tuple[np.ndarray, np.ndarray]:
    """Return (X, y): X is float64 (400, 10304) in 0..255, y is subject label 0..39."""
    zf = zipfile.ZipFile(zip_path)
    rows: list[np.ndarray] = []
    labels: list[int] = []
    for name in sorted(zf.namelist()):
        parts = [p for p in name.replace("\\", "/").split("/") if p]
        if len(parts) < 2 or not parts[-1].endswith(".pgm"):
            continue
        subject = parts[-2]
        if not subject.lower().startswith("s"):
            continue
        rows.append(_read_pgm(zf.read(name)).astype(np.float64).ravel())
        labels.append(int(subject[1:]) - 1)
    X = np.asarray(rows, dtype=np.float64)
    y = np.asarray(labels, dtype=np.int64)

    assert X.shape == (N_TOTAL, M), f"ORL shape {X.shape}, expected {(N_TOTAL, M)}"
    assert y.min() == 0 and y.max() == N_CLASSES - 1, "ORL labels are not 0..39"
    counts = np.bincount(y, minlength=N_CLASSES)
    assert (counts == N_PER_CLASS).all(), f"ORL per-subject counts wrong: {counts}"
    for i in range(N_CLASSES):
        one = X[y == i][0]
        assert one.size == IMG_H * IMG_W
    return X, y


def stratified_k_fold(y: np.ndarray, k: int, seed: int) -> list[tuple[np.ndarray, np.ndarray]]:
    """Deterministic per-class fold assignment; identical partitions for every method."""
    rng = np.random.default_rng(seed)
    test_idx: list[np.ndarray] = [np.empty(0, dtype=np.int64) for _ in range(k)]
    for cls in np.unique(y):
        idx = np.where(y == cls)[0]
        idx = rng.permutation(idx)
        for f, part in enumerate(np.array_split(idx, k)):
            test_idx[f] = np.concatenate([test_idx[f], part])
    folds = []
    all_idx = np.arange(y.size)
    for f in range(k):
        te = np.sort(test_idx[f])
        tr = np.setdiff1d(all_idx, te)
        folds.append((tr, te))
    assert sum(len(te) for _, te in folds) == y.size
    return folds


def fixed_split_per_subject(y: np.ndarray, n_train: int) -> tuple[np.ndarray, np.ndarray]:
    """One deterministic split: the first n_train images of every subject train the rest.

    Used for the supplementary small-sample regime (U008), where the point is that
    `M = 10,304` outruns `N` badly.  It is a single fixed split rather than ten folds
    because taking a cross-validation average over nine images per subject while training on
    four would mix two different protocols; the same split is used by every method, so the
    comparison stays paired.
    """
    tr, te = [], []
    for cls in np.unique(y):
        idx = np.where(y == cls)[0]
        if idx.size <= n_train:
            raise ValueError(f"subject {cls} has {idx.size} images, cannot hold out {n_train}")
        tr.extend(idx[:n_train])
        te.extend(idx[n_train:])
    return np.sort(np.asarray(tr, dtype=np.int64)), np.sort(np.asarray(te, dtype=np.int64))
