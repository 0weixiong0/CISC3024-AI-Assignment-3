"""Parity gate for the GO-LDA implementation (plan section 5).

Checks 1-4 gate Stage 3: if any of them fails, the implementation is wrong and nothing
downstream runs.  Check 5 is a diagnostic - it measures the paper's claims, so it is
reported, not used as a correctness test.  Runs in about five minutes.

One reclassification, made after M2 (2026-11-17): check 1e used to require GO-LDA's first
C - 1 directions and classic LDA's to span the same subspace on ORL, in addition to the two
classic-arm solvers agreeing.  The span agreement is real on ORL but it is not implied by the
algorithm - eq. (37) of the source constrains each new direction to be Euclidean-orthogonal,
which classic LDA is not - and M2 measured the two diverging from direction 3 onward on
CIFAR-100 features.  So 1e now gates only on solver agreement for the same pencil, and the
span comparison moved to diagnostic 5f.  See check_1e_orl_pencil_routes for the reasoning.

Tolerance policy, stated rather than assumed.  A comparison that must be exact (the first
direction against an independent eigensolve; reduced against dense) is held to EXACT
degrees.  Comparisons that involve the trailing, near-degenerate eigenvectors of a
C-class pencil carry a Davis-Kahan style bound computed from that very pencil, because
those directions are ill-conditioned by construction and a flat tolerance would either
pass a wrong implementation or fail a right one.  Residuals of the deflated M-space
equation are held to 10 eps kappa(A_r) - the first-order backward error of the eigensolve
that produced them - which on ORL at delta = 5e-3 is 8.9e-5, not a flat 1e-8; check 3b
pairs that bound with a control arm (a random span vector given its own Rayleigh
eigenvalue) so the threshold is shown to discriminate rather than merely to be large.
Every measured value, its tolerance and the bound it came from are printed and written to
runs/parity/parity_report.json.

    python tests/test_parity.py
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy import linalg
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from baselines import classic_lda_sklearn          # noqa: E402
from golda import (Scatters, basis_of_span, classic_lda_pencil, deflated_sides,  # noqa: E402
                   foley_sammon, go_lda, principal_angle, reduced_blocks,
                   residual_bound, residuals)
from orl import IMG_H, IMG_W, load_orl, stratified_k_fold  # noqa: E402

SEED = 20261117
DELTA_GRID = [0.0, 1e-6, 1e-4, 5e-3, 1e-2, 1e-1]
EXACT = 1e-4          # degrees; a real algorithmic error shows up as degrees, not 1e-4 deg
RESULTS: list[dict] = []


def record(name, ok, detail):
    # The gate's own classification, written into the artefact so consumers do not have to re-derive
    # it from the label: the suite's decision is in main(), and checks numbered 5 are diagnostics.
    RESULTS.append({"check": name, "ok": bool(ok), "detail": detail,
                    "gated": not name.startswith("5")})
    print(f"[{'PASS' if ok else 'FAIL'}] {name}\n       {detail}", flush=True)


def eig_gap(B_r: np.ndarray, A_r: np.ndarray, n_dir: int) -> float:
    vals = linalg.eig(B_r, A_r, right=False)
    keep = np.isfinite(vals) & (np.abs(vals.imag) < 1e-8 * np.maximum(1.0, np.abs(vals.real)))
    real = np.sort(vals.real[keep])[::-1]
    used = real[: max(n_dir, 2)]
    used = used[used > 0]
    if used.size < 2:
        return float(used[-1]) if used.size else float(real[-1])
    gaps = np.abs(np.diff(used))
    return float(gaps[gaps > 0].min()) if gaps.any() else float(used[-1])


def adaptive_tol(B_r: np.ndarray, A_r: np.ndarray, n_dir: int) -> tuple[float, float]:
    """(tolerance in degrees, eigenvalue gap it was derived from)."""
    gap = eig_gap(B_r, A_r, n_dir)
    scale = float(np.linalg.norm(B_r, 2)) + abs(float(np.linalg.norm(A_r, 2))) * max(gap, 1.0)
    tol = float(np.degrees(np.finfo(np.float64).eps * 100.0 * scale / max(gap, 1e-300)))
    return float(max(EXACT, tol)), gap


def control_residual(model: dict, n: int, seed: int) -> float:
    """Relative residual of eq (38) at step n for a RANDOM vector in the span.

    The wrong vector is given the best possible eigenvalue (its Rayleigh quotient), so this
    is the most favourable residual a wrong direction can produce; it is the control arm
    that says whether check 3b's tolerance actually discriminates.
    """
    sc, U, Q, A_r, delta = model["sc"], model["U"], model["Q"], model["A_r"], model["delta"]
    rng = np.random.default_rng(seed)
    v = Q @ rng.normal(size=(Q.shape[1], 1)).ravel()
    v = v / float(np.linalg.norm(v))
    term, sw = deflated_sides(sc, U, Q, A_r, delta, v, n)
    mu_v = float(term @ sw / max(sw @ sw, 1e-300))
    lhs = term - mu_v * sw
    return float(np.linalg.norm(lhs)
                 / max(float(np.linalg.norm(term)), abs(mu_v) * float(np.linalg.norm(sw)), 1e-300))


def gaussian_fixture(n_per_class=80, m=40, c=6, seed=SEED):
    rng = np.random.default_rng(seed)
    X, y = [], []
    for k in range(c):
        mu = rng.normal(0, 3.0, size=m) + (3.0 * k / c)
        X.append(rng.normal(mu, 1.0, size=(n_per_class, m)))
        y.append(np.full(n_per_class, k))
    return np.vstack(X), np.concatenate(y)


def check_1_first_direction():
    X, y = gaussian_fixture()
    C = int(len(np.unique(y)))
    sc = Scatters(X, y)
    go = go_lda(X, y, K=C - 1, delta=0.0, route="reduced")
    B_r0, A_r0 = reduced_blocks(sc, basis_of_span(sc, 0.0), 0.0)
    tol0, gap0 = adaptive_tol(B_r0, A_r0, C - 1)

    vals, vecs = linalg.eig(sc.dense_SB(), sc.dense_SW())
    top = int(np.argmax(vals.real))
    ref = np.ascontiguousarray(vecs[:, top].real)
    ref /= np.linalg.norm(ref)
    ang_a = principal_angle(go["U"][:, :1], ref[:, None])
    record("1a first direction == leading eigenvector of the classic pencil (delta=0, full rank)",
           ang_a < EXACT,
           f"N={sc.n} M={sc.M} C={C}; principal angle {ang_a:.3e} deg against an "
           f"independent dense linalg.eig of S_B u = lambda S_W u (tolerance {EXACT:g} deg); "
           f"that eigenvalue {vals.real[top]:.6f}")

    sk = classic_lda_sklearn(X, y, solver="svd")
    ang_b = principal_angle(go["U"][:, :1], sk)
    ang_c = principal_angle(classic_lda_pencil(X, y, delta=0.0, route="reduced")["U"], sk)
    record("1b first direction lies in scikit-learn's classic-LDA subspace",
           ang_b < tol0 and ang_c < tol0,
           f"sklearn's coef_ rows are a different basis of the same space, so the test is "
           f"span inclusion, not row equality. GO-LDA direction 1 vs that span "
           f"{ang_b:.3e} deg; our own C-1 classic directions vs the same span "
           f"{ang_c:.3e} deg (tolerance {tol0:.3e} deg from gap {gap0:.3e})")

    dense = go_lda(X, y, K=C - 1, delta=0.0, route="dense")
    ang1b = principal_angle(go["U"][:, :1], dense["U"][:, :1])
    ang_span_b = principal_angle(go["U"], dense["U"])
    record("1c reduced route == dense route (delta=0, same fixture)",
           ang1b < EXACT and ang_span_b < tol0,
           f"first direction {ang1b:.3e} deg (tolerance {EXACT:g} deg); span over "
           f"{C - 1} directions {ang_span_b:.3e} deg (tolerance {tol0:.3e} deg)")

    lines, worst, worst_tol = [], 0.0, 0.0
    for delta in [d for d in DELTA_GRID if d > 0]:
        Q = basis_of_span(sc, delta)
        B_r, A_r = reduced_blocks(sc, Q, delta)
        g = go_lda(X, y, K=1, delta=delta, route="reduced")["U"][:, 0]
        c_ref = classic_lda_pencil(X, y, delta=delta, route="reduced")["U"][:, 0]
        a = principal_angle(g[:, None], c_ref[:, None])
        t, gap = adaptive_tol(B_r, A_r, 1)
        worst, worst_tol = max(worst, a), max(worst_tol, t)
        lines.append(f"delta={delta:g}: {a:.2e}/{t:.2e} deg (gap {gap:.2e})")
    record("1d same-delta parity against our own ridge-LDA reference", worst <= worst_tol,
           "GO-LDA direction 1 must equal the first direction of the undeflated ridge "
           "pencil at matched delta; sklearn's unregularised solver is NOT a valid "
           "reference once delta > 0, which is why this reference is ours. "
           + " | ".join(lines) + f" ; worst {worst:.2e} deg")


def check_1e_orl_pencil_routes(X_tr, y_tr):
    """The three ways this suite solves the K = C-1 pencil must agree on real data.

    scipy.linalg.eigh (symmetric-definite, what the pencil actually is), scipy.linalg.eig
    through the eig-based classic reference, and the sequential deflated solve of GO-LDA.
    This is the plan's §5 check (a) plus the eigh agreement of §4 M1, run where both are
    affordable: the reduced pencil is r x r, so a symmetric eigendecomposition costs
    milliseconds and never the M x M arithmetic the dense route would.
    """
    sc = Scatters(X_tr, y_tr)
    delta = 5e-3
    Q = basis_of_span(sc, delta)
    B_r, A_r = reduced_blocks(sc, Q, delta)
    w, v = linalg.eigh(B_r, A_r)
    order = np.argsort(w)[::-1][: sc.C - 1]
    U_eigh = Q @ v[:, order]
    U_eigh = U_eigh / np.linalg.norm(U_eigh, axis=0, keepdims=True)
    c_model = classic_lda_pencil(X_tr, y_tr, delta=delta, route="reduced")
    c_ref, c_mu = c_model["U"], c_model["mu"]
    g = go_lda(X_tr, y_tr, K=sc.C - 1, delta=delta, route="reduced")["U"]
    tol, gap = adaptive_tol(B_r, A_r, sc.C - 1)
    a_ce = principal_angle(c_ref, U_eigh)
    a_ge = principal_angle(g, U_eigh)
    a_gc = principal_angle(g, c_ref)
    w_top = np.sort(w)[::-1][: sc.C - 1]
    ev_rel = float(np.abs(w_top - np.sort(c_mu)[::-1]).max()
                   / max(np.abs(w_top).max(), 1e-300))
    # Gated on the angle criterion alone.  An earlier revision of this line also required the two
    # solvers' eigenvalues to agree to a relative 1e-8, which closed the gate on a correct
    # implementation: `eig` and `eigh` disagree by 3.2e-07 relative here, which is what a
    # near-singular S_W at delta = 5e-3 costs, and the threshold had been written down rather than
    # derived.  `tol` comes from the spectral gap of this very pencil, so it is the assertion that
    # can discriminate; eigenvalue agreement is reported beside it.
    record("1e ORL fold 0, K = C-1: the two classic-arm solvers (eig, eigh) agree",
           a_ce < tol,
           f"r = {Q.shape[1]}, delta = {delta:g}, tolerance {tol:.3e} deg from gap "
           f"{gap:.3e}; classic(eig) vs classic(eigh) {a_ce:.3e} deg, and their eigenvalues "
           f"agree to a relative {ev_rel:.3e} over {sc.C - 1} of them, spanning "
           f"{w_top.min():.3e}..{w_top.max():.3e}")
    # GO-LDA against classic LDA is deliberately NOT gated here. This suite used to require the
    # three spans to agree, and on ORL they do - to 2e-6 degrees - but re-reading the source
    # (research_records/sources/golda_arXiv2305.14568_notes.md, eq. 37) shows the recursion's
    # constraint is ordinary Euclidean orthogonality, which classic LDA does not impose, so no
    # theorem makes the two agree at K = C - 1. M2 then measured them disagreeing from direction 3
    # onward on CIFAR-100 features (runs/m2_matrix/probe_cap_gap.json, median principal angle
    # 55.9 deg). Gating on that agreement would have failed a correct implementation the first
    # time it ran on new data, which is the failure mode this suite is supposed to prevent.
    # It stays observable, as a diagnostic under 5f.
    record("5f ORL fold 0, K = C-1: GO-LDA's span against classic LDA's (measured, not asserted)",
           a_ge < tol and a_gc < tol,
           f"GO-LDA vs classic(eigh) {a_ge:.3e} deg, GO-LDA vs classic(eig) {a_gc:.3e} deg "
           f"against the same tolerance {tol:.3e} deg - H1 holds in this regime; it is a "
           f"property of the data, and it is reported in stage_03a section 4 rather than used "
           f"as a correctness test")


def check_2_binary_foley_sammon():
    X, y = gaussian_fixture(n_per_class=120, m=30, c=2)
    sc = Scatters(X, y)
    u_fs = foley_sammon(X, y, delta=0.0)
    go = go_lda(X, y, K=1, delta=0.0, route="reduced")["U"][:, 0]
    a0 = principal_angle(go[:, None], u_fs[:, None])
    record("2a binary case at delta=0: exactly one direction compared, vs Foley-Sammon",
           a0 < EXACT,
           f"N={sc.n} M={sc.M} C=2; principal angle {a0:.3e} deg; directions compared = 1 "
           f"(C-1 = 1, so there is nothing else to compare, and with no second step the "
           f"deflation has to be inert here)")

    lines, worst, worst_tol = [], 0.0, 0.0
    for delta in [d for d in DELTA_GRID if d > 0]:
        u_ridge = linalg.solve(sc.dense_SW(delta), sc.means[1] - sc.means[0], assume_a="pos")
        u_ridge /= np.linalg.norm(u_ridge)
        g = go_lda(X, y, K=1, delta=delta, route="reduced")["U"][:, 0]
        a = principal_angle(g[:, None], u_ridge[:, None])
        B_r, A_r = reduced_blocks(sc, basis_of_span(sc, delta), delta)
        t, _gap = adaptive_tol(B_r, A_r, 1)
        worst, worst_tol = max(worst, a), max(worst_tol, t)
        lines.append(f"delta={delta:g}: {a:.2e}/{t:.2e} deg")
    record("2b binary case at matched delta > 0 vs the ridge Foley-Sammon form",
           worst <= worst_tol,
           "reference is (S_W + delta I)^-1 (mu1 - mu2), one direction, never the "
           "unregularised Foley-Sammon vector; " + " | ".join(lines)
           + f" ; worst {worst:.2e} deg")


def check_3_scatter_reconstruction():
    X, y = gaussian_fixture(n_per_class=60, m=25, c=5)
    sc = Scatters(X, y)
    est = LinearDiscriminantAnalysis(solver="eigen").fit(X, y)
    S_W, S_B = sc.dense_SW(), sc.dense_SB()

    d_sw = float(np.abs(S_W / sc.n - est.covariance_).max())
    d_sw_alt = float(np.abs(S_W / (sc.n - sc.C) - est.covariance_).max())

    S_B_loop = np.zeros((sc.M, sc.M))
    for i, g in enumerate(sc.groups):                       # independent code path
        dev = sc.means[i] - sc.grand
        S_B_loop += sc.counts[i] * np.outer(dev, dev)
    d_sb = float(np.abs(S_B_loop - S_B).max())

    centred = X - X.mean(0)
    total = centred.T @ centred
    d_id = float(np.abs((S_W + S_B) - total).max()) / max(float(np.abs(total).max()), 1e-300)
    tr_sb = float(np.trace(S_B))
    tr_ref = float(sum(sc.counts[i] * float((sc.means[i] - sc.grand) @ (sc.means[i] - sc.grand))
                       for i in range(sc.C)))
    record("3 scatter reconstruction: within-class vs scikit-learn's public covariance_, "
           "between-class vs an independent loop, and S_T = S_W + S_B",
           d_sw < 1e-12 and d_sb < 1e-12 and d_id < 1e-12 and abs(tr_sb - tr_ref) < 1e-10,
           f"max|S_W/N - covariance_| = {d_sw:.3e} - that is sklearn's pooling convention; "
           f"the unbiased S_W/(N-C) misses it by {d_sw_alt:.3e}. "
           f"max|S_B vectorised - S_B loop| = {d_sb:.3e}; relative |S_T-(S_W+S_B)| = "
           f"{d_id:.3e}; trace identity |diff| = {abs(tr_sb - tr_ref):.3e}")


def check_3b_coordinate_reduction(X_tr, y_tr):
    model = go_lda(X_tr, y_tr, K=50, delta=5e-3, route="reduced")
    res = residuals(model)
    tol_rel, kappa = residual_bound(model["A_r"])
    worst = float(res["relative"].max())

    # the identical check on a well-conditioned fixture, so the ORL figure is read against
    # what the same code achieves when the pencil is not ill-conditioned
    Xf, yf = gaussian_fixture(n_per_class=60, m=25, c=5)
    mf = go_lda(Xf, yf, K=4, delta=5e-3, route="reduced")
    worst_f = float(residuals(mf)["relative"].max())
    tol_f, kappa_f = residual_bound(mf["A_r"])

    controls = [control_residual(model, n, 0) for n in (0, 25, 49)]
    worst_ctrl = float(min(controls))
    record("3b span-reduced directions satisfy the full M-space pencil (ORL, fold 0)",
           worst < tol_rel and worst_f < tol_f and worst_ctrl > 100.0 * tol_rel,
           f"r = {model['Q'].shape[1]} of M = {X_tr.shape[1]}; worst RELATIVE residual over "
           f"K = {model['U'].shape[1]} directions = {worst:.3e} against eps * kappa tolerance "
           f"{tol_rel:.3e} (kappa(A_r) = {kappa:.3e} under the solver's own rtol = 1e-12 "
           f"truncation); the same code on a well-conditioned fixture gives {worst_f:.3e} "
           f"against {tol_f:.3e} (kappa = {kappa_f:.3e}). Control "
           f"arm - a random span vector with its own Rayleigh eigenvalue - scores "
           f"{worst_ctrl:.3e}, {worst_ctrl / tol_rel:.1f}x the tolerance, so the threshold "
           f"discriminates. Worst absolute residual {float(res['absolute'].max()):.3e} in "
           f"pixel-squared units, which is why the relative figure is what the gate reads; "
           f"eigenvalues {model['mu'].min():.3e}..{model['mu'].max():.3e}; S_B and S_W' are "
           f"applied matrix-free and S_W'^-1 only through the span, never the reduced pencil")

    rng = np.random.default_rng(0)
    P = rng.normal(size=(X_tr.shape[1], 200)) / np.sqrt(X_tr.shape[1])
    Xp = X_tr @ P
    sc_p = Scatters(Xp, y_tr)
    dense = go_lda(Xp, y_tr, K=8, delta=5e-3, route="dense")
    red = go_lda(Xp, y_tr, K=8, delta=5e-3, route="reduced")
    B_r3, A_r3 = reduced_blocks(sc_p, basis_of_span(sc_p, 5e-3), 5e-3)
    tol3, gap3 = adaptive_tol(B_r3, A_r3, 8)
    a1 = principal_angle(dense["U"][:, :1], red["U"][:, :1])
    asp = principal_angle(dense["U"], red["U"])
    record("3c reduced vs dense on a 200-dimensional ORL surrogate",
           a1 < EXACT and asp < tol3,
           f"first direction {a1:.3e} deg, span over 8 directions {asp:.3e} deg "
           f"(tolerance {tol3:.3e} deg from gap {gap3:.3e}) - the equivalence test the rank "
           f"reduction rests on, run where dense arithmetic is affordable")


def check_4_route_cost(X_tr, y_tr):
    t_red = time.perf_counter()
    go_lda(X_tr, y_tr, K=39, delta=5e-3, route="reduced")
    t_red = time.perf_counter() - t_red
    rows = []
    for m in (400, 800, 1600):
        rng = np.random.default_rng(1)
        A = rng.normal(size=(m, m))
        A = 0.5 * (A + A.T)
        B = rng.normal(size=(m, m))
        B = B @ B.T + m * np.eye(m)
        t0 = time.perf_counter()
        linalg.eig(A, B)
        rows.append((m, time.perf_counter() - t0))
    p = np.polyfit(np.log([r[0] for r in rows]), np.log([r[1] for r in rows]), 1)
    est_step = float(np.exp(np.polyval(p, np.log(10304))))
    record("4 measured cost of the two routes at ORL scale", t_red < 120 and est_step > 60,
           f"reduced route, K=39 on one fold: {t_red:.2f} s; dense generalised eig at "
           f"M=400/800/1600: {rows[0][1]:.2f}/{rows[1][1]:.2f}/{rows[2][1]:.2f} s, fitted "
           f"exponent {p[0]:.2f}, extrapolated {est_step:.0f} s for ONE dense step at "
           f"M=10,304 (~{est_step * 39 / 3600:.1f} h per fold per delta on the dense route) "
           f"- the measurement behind the plan's rank-reduced choice and its 1-2 h MVP ceiling")


def _offdiag(U: np.ndarray) -> float:
    G = U.T @ U
    off = np.abs(G - np.diag(np.diag(G)))
    return float(off.max()) if off.size and U.shape[1] > 1 else 0.0


def check_5_invariants(X_tr, y_tr):
    delta = 5e-3
    g = go_lda(X_tr, y_tr, K=50, delta=delta, route="reduced")
    c_model = classic_lda_pencil(X_tr, y_tr, delta=delta, route="reduced")
    c, c_mu = c_model["U"], c_model["mu"]
    tol_span, _gap = adaptive_tol(g["B_r"], g["A_r"], c.shape[1])

    Xf, yf = gaussian_fixture()
    gf = go_lda(Xf, yf, K=5, delta=delta, route="reduced")
    cf_model = classic_lda_pencil(Xf, yf, delta=delta, route="reduced")
    cf = cf_model["U"]
    off_gf, off_cf = _offdiag(gf["U"]), _offdiag(cf)
    fish_gf, fish_cf = gf["fisher"], _fisher(cf_model["sc"], cf, delta)
    record("5a (diagnostic) the paper's orthogonality claim, measured where it is visible",
           off_gf < 1e-12 and off_cf > 1e-3 and bool(np.all(fish_gf >= fish_cf * (1 - 1e-6))),
           f"well-conditioned fixture N={gf['sc'].n} M={gf['sc'].M} C=6, K=5: max |u_i^T u_j| "
           f"over i!=j is {off_cf:.4f} for classic LDA (non-orthogonal, as the paper claims) "
           f"and {off_gf:.3e} for GO-LDA (orthogonal, enforced by the deflation and not by any "
           f"post-hoc projection - the code never re-orthogonalises a solved vector). Per-"
           f"direction Fisher ratios: GO-LDA {np.round(fish_gf, 3).tolist()} vs classic "
           f"{np.round(fish_cf, 3).tolist()}, so GO-LDA is >= classic in every direction.")

    off_g, off_c = _offdiag(g["U"][:, :c.shape[1]]), _offdiag(c)
    tol_res, kappa = residual_bound(g["A_r"])
    record("5b (diagnostic) on ORL the deflation is nearly inert within the cap, and why",
           off_g < 10.0 * tol_res,
           f"max |u_i^T u_j| over the first C-1 = {c.shape[1]} directions: classic LDA "
           f"{off_c:.3e}, GO-LDA {off_g:.3e} (tolerance {10.0 * tol_res:.3e} = 100 eps kappa, "
           f"kappa(A_r) = {kappa:.3e}). Classic LDA's ORL directions are already Euclidean-"
           f"orthogonal to that order, so the eq (40)-(41) correction has almost nothing to "
           f"remove: the spans of the first {c.shape[1]} directions of each differ by "
           f"{principal_angle(g['U'][:, :c.shape[1]], c):.3e} deg (tolerance {tol_span:.3e}) "
           f"and the orthogonality difference that H3 predicts is not a live effect on this "
           f"dataset - it is reported as measured, not as the paper phrases it")

    fisher = g["fisher"]
    mono = bool(np.all(np.diff(fisher) <= 1e-9))
    fish_orl_c = _fisher(c_model["sc"], c, delta)
    record("5c (diagnostic) Fisher ratio non-increasing across GO-LDA directions", mono,
           f"first five {np.round(fisher[:5], 4).tolist()}; K=39 {fisher[38]:.4f}; "
           f"K=50 {fisher[-1]:.4e}; classic-LDA ratios on the same data "
           f"{np.round(fish_orl_c, 4).tolist()[:3]}... - on ORL the two agree to the "
           f"conditioning noise (relative differences of order {tol_res:.1e}), which is what "
           f"5b explains, whereas 5a shows the separation is real on data that needs it")

    above = g["mu"][39:]
    record("5d (diagnostic) directions beyond the C-1 rank cap carry positive eigenvalues",
           bool(np.all(above > 0)),
           f"eigenvalues at K=40..50: min {above.min():.4e}, max {above.max():.4e}; classic "
           f"LDA has no such direction to offer (its 39th eigenvalue is "
           f"{c_mu[-1]:.3e} and it has no 40th)")


def _fisher(sc: Scatters, U: np.ndarray, delta: float) -> np.ndarray:
    out = []
    for u in U.T:
        num = float(u @ sc.apply_SB(u[:, None]).reshape(-1))
        den = float(u @ sc.apply_SW(u[:, None], delta).reshape(-1))
        out.append(num / max(den, 1e-300))
    return np.asarray(out)


def check_5e_bruteforce_deflation(delta: float = 5e-3):
    """Algorithm 1 rebuilt from eqs (38)-(41) with explicit dense matrices and np.linalg.inv.

    Deliberately shares no code with src/golda.py: dense scatters, dense inverses, and a
    standard non-symmetric generalised eig solve of the deflated pencil at every step.  It
    is the independent-implementation cross-check the plan's section 5 item (b) asks for,
    run at the cap AND beyond it (U008 amendment 1): beyond the cap the only rule that
    picks a direction is "largest eigenvalue of the deflated pencil", so that selection
    needs a reference that is not the same code making the choice.
    """
    Xf, yf = gaussian_fixture(n_per_class=40, m=24, c=5)
    sc = Scatters(Xf, yf)
    S_B, S_W = sc.dense_SB(), sc.dense_SW(delta)
    S_W_inv = np.linalg.inv(S_W)
    B_r, A_r = reduced_blocks(sc, basis_of_span(sc, delta), delta)
    cap = sc.C - 1
    for K in (cap, 2 * cap):
        red = go_lda(Xf, yf, K=K, delta=delta, route="reduced")
        tol, gap = adaptive_tol(B_r, A_r, 1)
        Us, lines, worst, mu_diff, mus_dense = [], [], 0.0, [], []
        for n in range(K):
            if n == 0:
                D = S_B
            else:
                Uprev = np.column_stack(Us)
                T = Uprev.T @ (S_W_inv @ Uprev)
                Bm = Uprev.T @ (S_W_inv @ S_B)
                D = S_B - Uprev @ (np.linalg.inv(T) @ Bm)
            vals, vecs = linalg.eig(D, S_W)
            k = int(np.argmax(vals.real))
            u = vecs[:, k].real / float(np.linalg.norm(vecs[:, k].real))
            Us.append(u)
            mu_n = float(vals[k].real)
            mus_dense.append(mu_n)
            a = principal_angle(u[:, None], red["U"][:, n][:, None])
            worst = max(worst, a)
            mu_diff.append(abs(mu_n - red["mu"][n]) / max(abs(mu_n), 1e-300))
            lines.append(f"n={n + 1}: {a:.2e} deg (mu {mu_n:.6g})")
        record(f"5e (diagnostic) brute-force dense deflation == the span-reduced solver, "
               f"K = {K} ({'at' if K == cap else 'beyond'} the C-1 = {cap} cap)",
               worst < tol and max(mu_diff) < 1e-6,
               f"N={sc.n} M={sc.M} C=5, K={K}, delta={delta:g}: " + " | ".join(lines)
               + f" ; worst {worst:.3e} deg against tolerance {tol:.3e} deg from gap "
               f"{gap:.3e}; eigenvalues agree to a relative {max(mu_diff):.3e}; first three "
               f"dense mus {[round(v, 6) for v in mus_dense[:3]]} vs first three reduced-route "
               f"mus {[round(v, 6) for v in red['mu'][:3].tolist()]}")


def main():
    X, y = load_orl()
    tr, _ = stratified_k_fold(y, 10, SEED)[0]
    y_tr = y[tr]
    shape_ok = X.shape == (400, 10304)
    per_class_ok = all(int((y == i).sum()) == 10 for i in range(40))
    reshape_ok = X[0].reshape(IMG_H, IMG_W).shape == (IMG_H, IMG_W)
    print(f"ORL loaded: X {X.shape}, fold-0 training rows {len(tr)}, test rows {400 - len(tr)}")
    print(f"M0 assertions: 400 x 10,304 = {'OK' if shape_ok else 'FAIL'}; "
          f"per-image {IMG_H} rows x {IMG_W} columns = {'OK' if reshape_ok else 'FAIL'}; "
          f"40 subjects x 10 images = {'OK' if per_class_ok else 'FAIL'}")
    print(f"pixel range {X.min():.0f}..{X.max():.0f}; 9 train / 1 test per subject\n")
    if not (shape_ok and per_class_ok and reshape_ok):
        print("M0 FAILED - stop")
        return 1

    check_1_first_direction()
    check_1e_orl_pencil_routes(X[tr], y_tr)
    check_2_binary_foley_sammon()
    check_3_scatter_reconstruction()
    check_3b_coordinate_reduction(X[tr], y_tr)
    check_4_route_cost(X[tr], y_tr)
    check_5_invariants(X[tr], y_tr)
    check_5e_bruteforce_deflation()

    out = ROOT / "runs" / "parity"
    out.mkdir(parents=True, exist_ok=True)
    (out / "parity_report.json").write_text(json.dumps(RESULTS, indent=2), encoding="utf-8")
    gated = [r for r in RESULTS if r["gated"]]
    failed = [r for r in gated if not r["ok"]]
    print(f"\n{len(gated) - len(failed)}/{len(gated)} gated checks passed "
          f"({sum(1 for r in RESULTS if r['ok'])}/{len(RESULTS)} overall); report: "
          f"{out / 'parity_report.json'}")
    if failed:
        for r in failed:
            print("  FAILED:", r["check"], "|", r["detail"])
        print("\nGATE CLOSED: fix the implementation before any Stage-3 run")
        return 1
    print("\nGATE OPEN: Stage-3 MVP may proceed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
