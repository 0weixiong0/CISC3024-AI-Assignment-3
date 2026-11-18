"""Baselines and the two fixed evaluation heads.

Roles are the ones the approved plan assigns: classic LDA (ridge or shrunken) /
PCA-then-LDA are projection methods; plain PCA is used only as the first step of
PCA-then-LDA and as the reference row where K exceeds the C-1 rank cap;
nearest-class-mean is a classifier, not a projection; ORL is scored with 1-NN (the
paper's head) and the feature regimes with C4's logistic head.
"""

from __future__ import annotations

import numpy as np
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from golda import classic_lda_pencil


def pca_dirs(X: np.ndarray) -> np.ndarray:
    """Principal directions of the centred training data, M x min(N-1, M), strongest first.

    Computed once per fold and sliced, because PCA-then-LDA is evaluated at several K.
    """
    return np.linalg.svd(X - X.mean(0), full_matrices=False)[2].T


def classic_lda_sklearn(X, y, solver="svd", shrinkage=None) -> np.ndarray:
    """scikit-learn's classic LDA, returning its discriminant directions as columns.

    sklearn stores coef_ as (C-1, M); this returns the (M, C-1) orientation the rest of
    the codebase uses, so a projection is always X @ directions.  Its rows are not ordered
    by eigenvalue, which is why the parity gate compares spans rather than slicing this.
    """
    kwargs = {"solver": solver}
    if shrinkage is not None:
        kwargs["shrinkage"] = shrinkage
    lda = LinearDiscriminantAnalysis(**kwargs).fit(X, y)
    return lda.coef_.T


def pca_then_lda(X_tr, y_tr, k_pca: int, delta: float, pc_dirs: np.ndarray | None = None) -> dict:
    """C4's reduction order: PCA to k_pca dimensions, then classic LDA inside that subspace.

    The inner LDA is our own ordered pencil, not sklearn's unordered `coef_`, so cutting it
    at K is a real dimension reduction.  Directions come back lifted to the original
    M-dimensional space.  Centering the data only translates the projected coordinates,
    which leaves both the scatters and the distance-based heads unchanged, so the projection
    is applied without the training mean.
    """
    basis = pca_dirs(X_tr)[:, :k_pca] if pc_dirs is None else pc_dirs[:, :k_pca]
    model = classic_lda_pencil(X_tr @ basis, y_tr, delta=delta, route="reduced")
    return {"U": basis @ model["U"], "mu": model["mu"],
            "realized_dim": int(model["U"].shape[1])}


def ncm_predict(means, classes, Q) -> np.ndarray:
    """Nearest-class-mean read-out; `means` must be formed in the same space as `Q`."""
    d = ((Q[:, None, :] - means[None, :, :]) ** 2).sum(-1)
    return classes[np.argmin(d, axis=1)]


def knn_predict(Xtr_p, ytr, Qte_p, k: int = 1, chunk_rows: int = 8) -> np.ndarray:
    """Exact k-NN, evaluated a few queries at a time; k = 1 is the paper's ORL head.

    Chunking is not an approximation: each query row goes through the same expression as
    the unchunked form, so the predictions are identical while the peak temporary shrinks
    from n_query x n_train x D to chunk_rows x n_train x D.  At ORL raw-pixel scale that was
    the difference between 221 MB and 2.6 GB of measured peak RSS, and the feature regimes
    have more queries per fold, so this is the form M2 runs on.
    """
    out = np.empty(Qte_p.shape[0], dtype=ytr.dtype)
    for s in range(0, Qte_p.shape[0], chunk_rows):
        block = Qte_p[s:s + chunk_rows]
        d = ((block[:, None, :] - Xtr_p[None, :, :]) ** 2).sum(-1)
        order = np.argsort(d, axis=1)[:, :k]
        votes = ytr[order]
        for i, row in enumerate(votes):
            vals, counts = np.unique(row, return_counts=True)
            out[s + i] = vals[np.argmax(counts)]
    return out


def logistic_head(Xtr_p, ytr):
    """C4's head: L2 logistic regression, LBFGS, max_iter=5000, C=1.0,
    StandardScaler fitted on the training fold only, applied after projection.

    Returns a predict callable so the scaler can never be refitted on test data by
    accident at the call site.
    """
    scaler = StandardScaler().fit(Xtr_p)
    clf = LogisticRegression(solver="lbfgs", max_iter=5000, C=1.0)
    clf.fit(scaler.transform(Xtr_p), ytr)
    return lambda Q: clf.predict(scaler.transform(Q))
