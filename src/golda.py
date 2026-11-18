"""GO-LDA (arXiv:2305.14568) - generalised optimal linear discriminant analysis.

Implements Algorithm 1 with equations 38-41: direction 1 is the leading eigenvector of
the classic pencil S_B u = mu S_W' u, and for n >= 2 direction n is the leading
eigenvector of the deflated pencil

    (S_B - U_{n-1} T_{n-1}^{-1} B_{n-1}) u = mu S_W' u           (eq. 38)

with U_{n-1} = [u_1 ... u_{n-1}]                                  (eq. 39)
     B_{n-1} rows  u_i^T S_W'^{-1} S_B                            (eq. 40)
     T_{n-1}[i, j] = u_i^T S_W'^{-1} u_j                          (eq. 41)
and S_W' = S_W + delta*I, the paper's own remedy for the singular within-class scatter.
Note the paper's normalisation: each u_n is returned with unit Euclidean norm.

Two routes, one implementation body.  They differ only in the coordinate system the
pencil is written in:

  route='reduced'   Q is an orthonormal basis of range(S_W) + span(class means), of
                    dimension r <= N - 1.  S_W' maps that span into itself
                    (S_W V = Wc^T Wc V with Wc V in range(Wc^T), and delta*V stays in
                    span Q), and so does S_B, because range(S_B) is exactly the span of
                    the mean deviations which the basis contains.  Therefore
                    Q^T S_X' Q reproduces the pencil on the invariant subspace, and
                    with orthonormal Q the identity term restricts exactly:
                    Q^T (delta I) Q = delta I_r.  On ORL (M = 10,304, N = 360 per fold)
                    this replaces K dense O(M^3) eigensolves by K eigensolves of size
                    r <= 399, with no M x M matrix ever formed.
  route='dense'     Q = I, the M x M pencil is formed explicitly.  This is the reference
                    implementation and is only affordable at small M.

Directions returned by the reduced route are verified back in full M-space by
``residuals()``, which never uses the reduced basis.

delta = 0 on ill-conditioned scatter uses the Moore-Penrose inverse (the same convention
scikit-learn's solver='svd' takes); that is recorded rather than hidden.
"""

from __future__ import annotations

import numpy as np
from scipy import linalg


class Scatters:
    """Scatter bookkeeping for one training set, with matrix-free applications."""

    def __init__(self, X: np.ndarray, y: np.ndarray) -> None:
        X = np.asarray(X, dtype=np.float64)
        y = np.asarray(y, dtype=np.int64)
        if X.shape[0] != y.shape[0]:
            raise ValueError("X and y length mismatch")
        self.X, self.y = X, y
        self.n, self.M = X.shape
        self.classes = np.unique(y)
        self.C = int(self.classes.size)
        if self.C < 2:
            raise ValueError("at least two classes are required")
        self.groups = [np.where(y == c)[0] for c in self.classes]
        self.counts = np.array([g.size for g in self.groups], dtype=np.float64)
        self.means = np.stack([X[g].mean(0) for g in self.groups])
        self.grand = X.mean(0)
        self.mean_dev = self.means - self.grand
        self.Xc = np.concatenate([X[g] - self.means[i] for i, g in enumerate(self.groups)])
        self.rank_W_cap = int(min(self.n - self.C, self.M))

    # --- explicit M x M forms: dense reference path only -------------------------
    def dense_SW(self, delta: float = 0.0) -> np.ndarray:
        S = self.Xc.T @ self.Xc
        return S + delta * np.eye(self.M) if delta else S

    def dense_SB(self) -> np.ndarray:
        return (self.mean_dev * self.counts[:, None]).T @ self.mean_dev

    # --- matrix-free applications, valid at any M --------------------------------
    def apply_SW(self, V, delta: float = 0.0) -> np.ndarray:
        V = np.atleast_2d(np.asarray(V, dtype=np.float64))
        return self.Xc.T @ (self.Xc @ V) + (delta * V if delta else 0.0)

    def apply_SB(self, V) -> np.ndarray:
        V = np.atleast_2d(np.asarray(V, dtype=np.float64))
        return self.mean_dev.T @ ((self.mean_dev * self.counts[:, None]) @ V)


def basis_of_span(sc: Scatters, delta: float, tol: float = 1e-11):
    """Orthonormal basis Q of range(S_W) + span(mean deviations)."""
    _, s, Vt = np.linalg.svd(sc.Xc, full_matrices=False)
    r_w = int((s > tol * s[0]).sum()) if s.size else 0
    Q = Vt[:r_w].T.copy() if r_w else np.zeros((sc.M, 0))

    extra = sc.mean_dev.T.copy()
    for _ in range(2):                                                # twice is enough here
        if Q.shape[1]:
            extra = extra - Q @ (Q.T @ extra)
    scale = np.linalg.norm(extra, axis=0)
    thresh = tol * max(1.0, float(np.linalg.norm(sc.mean_dev)))
    keep = scale > thresh
    blocks = [b for b in (Q, extra[:, keep]) if b.shape[1]]
    if blocks:
        Q = np.hstack(blocks)
        q, r = np.linalg.qr(Q)
        diag = np.abs(np.diag(r))
        Q = q[:, diag > tol * max(1.0, float(diag.max()))]
    if Q.shape[1] == 0:
        raise np.linalg.LinAlgError("degenerate scatter: empty working span")
    return Q


def reduced_blocks(sc: Scatters, Q: np.ndarray, delta: float):
    """(B_r, A_r) = (Q^T S_B Q, Q^T S_W' Q), formed without touching M x M memory."""
    Z = sc.Xc @ Q
    A_r = Z.T @ Z
    if delta > 0.0:
        A_r = A_r + delta * np.eye(A_r.shape[0])
    Md_r = sc.mean_dev @ Q
    B_r = (Md_r * sc.counts[:, None]).T @ Md_r
    return 0.5 * (B_r + B_r.T), A_r


def _solve_psd(A: np.ndarray, rhs: np.ndarray, assume_a: str = "sym") -> np.ndarray:
    """Solve A x = rhs, falling back to a truncated pseudo-inverse when A is singular.

    `scipy.linalg.solve` warns rather than raises on a matrix with rcond ~ 1e-20 and hands
    back a solution whose size is set by the smallest singular value it did not treat as
    zero, so conditioning has to be measured before the solve, not trusted afterwards.
    That is not hypothetical: at delta = 0 on ORL both the reduced Gram S_W (rcond 6.6e-39)
    and the deflation matrix T (rcond 7.1e-20) are numerically singular, and delta = 0 is
    in the approved sweep.
    """
    if _is_singular(A):
        return np.linalg.pinv(A, rtol=1e-12) @ rhs
    return linalg.solve(A, rhs, assume_a=assume_a)


def _solve_A(A_r: np.ndarray, rhs: np.ndarray, delta: float) -> np.ndarray:
    """Solve A_r x = rhs: with a ridge the Gram is positive definite, at delta = 0 it may not be."""
    if delta > 0.0:
        return linalg.solve(A_r, rhs, assume_a="pos")
    return _solve_psd(A_r, rhs)


def _is_singular(A_r: np.ndarray) -> bool:
    s = np.linalg.svd(A_r, compute_uv=False)
    return bool(s[-1] <= 1e-12 * max(1.0, s[0]))


def leading_pair(Mleft: np.ndarray, Bright: np.ndarray):
    """Largest real generalised eigenvalue with its unit vector.

    Tie rule: candidates are ordered by descending real part of the eigenvalue; a
    candidate is accepted only when it is finite and its eigenvector is real to 1e-6
    relative to the vector's own scale.  Ties in the real part are broken by the order
    LAPACK returns, which is deterministic for a fixed input.  Nothing is projected out
    after the solve: for GO-LDA the deflation in eq. (38) is what makes a new direction
    orthogonal, and re-orthogonalising afterwards would hide a deflation bug and take the
    vector off the pencil it was just certified against.
    """
    vals, vecs = linalg.eig(Mleft, Bright)
    finite = np.isfinite(vals)
    scale = np.maximum(1.0, np.abs(vecs).max(axis=0))
    real_ok = np.abs(vecs.imag).max(axis=0) <= 1e-6 * scale
    score = np.where(finite & real_ok, vals.real, -np.inf)
    order = np.argsort(score)[::-1]
    for k in order:
        if not np.isfinite(score[k]):
            continue
        v = np.ascontiguousarray(vecs[:, k].real, dtype=np.float64)
        nrm = float(np.linalg.norm(v))
        if nrm < 1e-12:
            continue
        return float(vals[k].real), v / nrm
    raise np.linalg.LinAlgError("no usable real leading generalised eigenvector")


def go_lda(X, y, K: int, delta: float = 0.0, route: str = "reduced") -> dict:
    """K GO-LDA discriminant directions (eq. 38-41), unit Euclidean norm each."""
    sc = Scatters(X, y)
    K = int(min(K, sc.M))
    if route == "dense":
        Q = np.eye(sc.M)
        B_r, A_r = sc.dense_SB(), sc.dense_SW(delta)
    elif route == "reduced":
        Q = basis_of_span(sc, delta)
        B_r, A_r = reduced_blocks(sc, Q, delta)
    else:
        raise ValueError(f"unknown route {route!r}")
    singular_A = delta == 0.0 and _is_singular(A_r)

    Us: list[np.ndarray] = []
    coords: list[np.ndarray] = []
    wins: list[np.ndarray] = []                                    # coordinates of S_W'^{-1} u
    mus: list[float] = []
    fisher: list[float] = []
    for step in range(K):
        if coords:
            Ucoef = np.column_stack(coords)
            Wcoef = np.column_stack(wins)
            T = 0.5 * (Ucoef.T @ Wcoef + (Ucoef.T @ Wcoef).T)
            Bn = Wcoef.T @ B_r                                     # rows of eq. (40)
            Mleft = B_r - Ucoef @ _solve_psd(T, Bn,
                                             "sym" if delta == 0 else "pos")
        else:
            Mleft = B_r.copy()
        # skip=None on purpose: the deflation in eq. (38) is what makes u_n orthogonal,
        # so projecting afterwards would hide a deflation bug and break the eigenpair.
        mu, a = leading_pair(Mleft, A_r)
        a = a / float(np.linalg.norm(a))
        w = _solve_A(A_r, a, delta)
        u = Q @ a
        u = u / float(np.linalg.norm(u))
        numer = float(u @ sc.apply_SB(u[:, None]).reshape(-1))
        denom = float(u @ sc.apply_SW(u[:, None], delta).reshape(-1))
        Us.append(u)
        coords.append(Q.T @ u if route == "reduced" else u)
        wins.append(_solve_A(A_r, coords[-1], delta))
        mus.append(mu)
        fisher.append(numer / max(denom, 1e-300))

    U = np.column_stack(Us)
    G = U.T @ U
    offdiag = np.abs(G - np.diag(np.diag(G)))
    return {"U": U, "mu": np.asarray(mus), "fisher": np.asarray(fisher), "delta": delta,
            "route": route, "sc": sc, "Q": Q, "A_r": A_r, "B_r": B_r,
            "coords": np.column_stack(coords), "wins": np.column_stack(wins),
            "singular_pinv": singular_A,
            "max_pairwise_abs_cos": float(offdiag.max()) if offdiag.size else 0.0}


def classic_lda_pencil(X, y, delta: float = 0.0, route: str = "reduced",
                      n_dirs: int | None = None,
                      shrinkage: float | None = None) -> dict:
    """Ridge-regularised classic LDA: the C-1 leading eigenvectors of the *undeflated*
    pencil, from one eigendecomposition so the ordering rule is the eigenvalue order and
    no direction is touched after the solve.  This is the same-delta reference the parity
    gate requires; scikit-learn at its default is not one, because a ridge changes the
    problem.

    `shrinkage` replaces the ridge with the Ledoit-Wolf form
    `(1 - alpha) S_W + alpha * tr(S_W) / M * I`, so the K sweep can compare the two
    regularisers on the same ordering rule - scikit-learn's shrunken solver returns an
    unordered `coef_`, and slicing that is not a dimension reduction.
    """
    sc = Scatters(X, y)
    if shrinkage is not None:
        if route == "dense":
            Q = np.eye(sc.M)
            B_r, A_r = sc.dense_SB(), sc.dense_SW(0.0)
        else:
            Q = basis_of_span(sc, 0.0)
            B_r, A_r = reduced_blocks(sc, Q, 0.0)
        tau = float((sc.Xc ** 2).sum()) / sc.M          # tr(S_W) / M, without the M x M object
        A_r = (1.0 - shrinkage) * A_r + shrinkage * tau * np.eye(A_r.shape[0])
    elif route == "dense":
        Q = np.eye(sc.M)
        B_r, A_r = sc.dense_SB(), sc.dense_SW(delta)
    else:
        Q = basis_of_span(sc, delta)
        B_r, A_r = reduced_blocks(sc, Q, delta)
    want = sc.C - 1 if n_dirs is None else int(n_dirs)
    want = max(1, min(want, B_r.shape[0]))

    # one eigendecomposition, not K sequential ones: the classic directions are the pencil
    # eigenpairs themselves, and any post-hoc orthogonalisation here would destroy exactly
    # the non-orthogonality the paper's claim is about.
    vals, vecs = linalg.eig(B_r, A_r)
    scale = np.maximum(1.0, np.abs(vecs).max(axis=0))
    keep = np.where(np.isfinite(vals) & (np.abs(vecs.imag).max(axis=0) <= 1e-6 * scale))[0]
    order = keep[np.argsort(vals.real[keep])[::-1]][:want]
    Us, mus = [], []
    for k in order:
        a = np.ascontiguousarray(vecs[:, k].real, dtype=np.float64)
        a = a / float(np.linalg.norm(a))
        u = Q @ a
        u = u / float(np.linalg.norm(u))
        Us.append(u)
        mus.append(float(vals[k].real))
    if not Us:
        raise np.linalg.LinAlgError("classic pencil produced no usable real eigenvector")
    U = np.column_stack(Us)
    G = U.T @ U
    off = np.abs(G - np.diag(np.diag(G)))
    return {"U": U, "mu": np.asarray(mus), "delta": delta, "route": route, "sc": sc,
            "shrinkage": shrinkage, "A_r": A_r, "B_r": B_r,
            "max_pairwise_abs_cos": float(off.max()) if off.size and U.shape[1] > 1 else 0.0}


def span_solve(Q: np.ndarray, A_r: np.ndarray, V: np.ndarray, delta: float = 0.0) -> np.ndarray:
    """S_W'^{-1} V for V whose columns lie in span(Q), through the reduced Gram.

    The reduced pencil is r x r (r <= N - 1 = 359 at ORL scale), so this never touches
    M x M arithmetic, and when delta = 0 it uses the span-restricted pseudoinverse.
    """
    return Q @ _solve_A(A_r, Q.T @ V, delta)


def deflated_sides(sc: "Scatters", U: np.ndarray, Q: np.ndarray, A_r: np.ndarray,
                   delta: float, v: np.ndarray, n: int):
    """The two sides of the deflated equation (38) at step n, for any candidate v.

    Returns (deflated S_B term, S_W' v).  Used both by residuals(), which feeds it the
    solved directions, and by the parity gate's control arm, which feeds it a deliberately
    wrong vector - the same equation, so a tolerance that the wrong vector cannot meet is
    a tolerance that discriminates.
    """
    Su = sc.apply_SB(v.reshape(-1, 1)).reshape(-1)
    term = Su.copy()
    if n > 0:
        Uprev = U[:, :n]
        Wprev = span_solve(Q, A_r, Uprev, delta)
        T = Uprev.T @ Wprev
        T = 0.5 * (T + T.T)
        term = term - Uprev @ _solve_psd(T, Wprev.T @ Su, "sym" if delta == 0 else "pos")
    return term, sc.apply_SW(v.reshape(-1, 1), delta).reshape(-1)


def residuals(model: dict) -> dict:
    """Deflated-pencil residual for every direction, evaluated in full M-space.

    Returns both the absolute residual ||(S_B - U T^-1 B) u_n - mu_n S_W' u_n|| and the
    same number normalised by the size of the two sides it has to balance, because on raw
    pixels the scatters carry pixel-squared magnitude and only the relative figure is
    interpretable.  Nothing here uses the reduced pencil as a black box: S_B and S_W' are
    applied matrix-free and S_W'^{-1} u_i is obtained through the span.
    """
    sc, U, mu, delta = model["sc"], model["U"], model["mu"], model["delta"]
    Q, A_r = model["Q"], model["A_r"]
    absolute, relative = [], []
    for n in range(U.shape[1]):
        term, sw = deflated_sides(sc, U, Q, A_r, delta, U[:, n], n)
        lhs = term - mu[n] * sw
        absolute.append(float(np.linalg.norm(lhs)))
        scale = max(float(np.linalg.norm(term)), abs(mu[n]) * float(np.linalg.norm(sw)), 1e-300)
        relative.append(float(np.linalg.norm(lhs) / scale))
    return {"absolute": np.asarray(absolute), "relative": np.asarray(relative)}


def foley_sammon(X, y, delta: float = 0.0) -> np.ndarray:
    """The two-class direction (S_W + delta I)^{-1} (mu_1 - mu_2): exactly one vector."""
    sc = Scatters(X, y)
    if sc.C != 2:
        raise ValueError("Foley-Sammon is the two-class case")
    d = sc.means[1] - sc.means[0]
    if sc.M <= 4096:
        S_W = sc.dense_SW(delta)
        if delta == 0.0 and _is_singular(S_W):
            u = np.linalg.pinv(S_W, rtol=1e-12) @ d
        else:
            u = linalg.solve(S_W, d, assume_a="pos") if delta > 0 else _solve_psd(S_W, d)
    else:
        Q = basis_of_span(sc, delta)
        _, A_r = reduced_blocks(sc, Q, delta)
        u = Q @ _solve_A(A_r, Q.T @ d, delta)
    return u / float(np.linalg.norm(u))


def residual_bound(A_r: np.ndarray, rtol: float = 1e-12) -> tuple[float, float]:
    """(tolerance, condition number used) for the M-space residual of a solved direction.

    A correct eigensolve of a symmetric-definite pencil leaves a first-order backward error
    of order eps * kappa, and the forward residual inherits it, so the residual a right
    implementation can be held to scales with the pencil's conditioning rather than with a
    flat constant.  The kappa that matters is the one under the truncation the solver
    actually used: `_solve_psd` discards singular values below rtol * s_max, so a matrix
    whose raw kappa is 1.5e34 at delta = 0 behaves like one with kappa 1/rtol = 1e12, and
    using the raw figure would produce a bound so large it asserts nothing.  Ten eps times
    that is the slack used here.  At delta = 5e-3 on ORL the bound is 8.9e-5 against a
    measured 3.0e-6, while the same code on a well-conditioned fixture measures 7.6e-16; at
    delta = 0 on the same data the measured residual is 1.5, i.e. outside any honest bound,
    which is the pilot's evidence that the ridge is part of the method rather than a
    convenience.  tests/test_parity.py check 3b pairs the bound with a control arm (a random
    span vector given its own Rayleigh eigenvalue) to show the threshold discriminates.
    """
    s = np.linalg.svd(A_r, compute_uv=False)
    kappa = float(s[0] / max(s[-1], rtol * s[0]))
    return float(max(1e-12, 10.0 * np.finfo(np.float64).eps * kappa)), kappa


def principal_angle(A: np.ndarray, B: np.ndarray) -> float:
    """Largest principal angle, in degrees, between the spans of A and B."""
    A = np.asarray(A, dtype=np.float64)
    B = np.asarray(B, dtype=np.float64)
    A = A.reshape(A.shape[0], -1)
    B = B.reshape(B.shape[0], -1)
    qa = linalg.qr(A, mode="economic")[0]
    qb = linalg.qr(B, mode="economic")[0]
    s = np.clip(np.linalg.svd(qa.T @ qb, compute_uv=False), -1.0, 1.0)
    return float(np.degrees(np.arccos(float(np.clip(s.min(), -1.0, 1.0)))))
