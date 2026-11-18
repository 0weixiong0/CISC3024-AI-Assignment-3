# GO-LDA source notes - verbatim passages the implementation and the hypotheses rest on

Source: Jiahui Liu, Xiaohao Cai, Mahesan Niranjan, "GO-LDA: Generalised Optimal Linear Discriminant
Analysis", arXiv:2305.14568v1 [cs.CV], submitted 23 May 2023, CC BY 4.0.
<https://arxiv.org/abs/2305.14568> - HTML rendering <https://arxiv.org/html/2305.14568v1>.
Fetched and transcribed 2026-11-17 (WebFetch of the arXiv HTML page). Equation numbers are the
paper's; the LaTeX below is transcribed from the rendered page, symbols normalised to the
notation used in `src/golda.py`.

Why this file exists: `src/golda.py` implements Algorithm 1, and the fidelity of that
implementation is a claim in the report. It should be checkable against the source without
re-deriving it from memory, and the parity/superiority wording of the paper's own claims should
be quotable.

---

## 1. The classical baseline, as the paper states it (Sec. IV-B)

> "Multiclass LDA seeks discriminant directions maximising R(.) ... which, utilising the
> Rayleigh-Ritz quotient approach, can be simplified as
> max_v v^T S_B v, s.t. v^T S_W v = 1" (11)

> "S_B v = lambda S_W v" (14) - "which is known as the generalised eigenvalue problem"

> "Since the ranks of S_W and S_B are (M - C) and (C - 1) respectively, the generalised eigenvalue
> problem (14) has maximum of (C - 1) non-zero eigenvalues."

> "A small perturbation can be adopted to deal with the singularity of S_W [36], which is replaced
> by e.g. S_W <- S_W + delta I" (15) "where I is the identity matrix and delta (e.g.
> delta = 5 x 10^-3) is a relatively small value such that S_W is non-singular."

Note on our ridge: eq. (15) is exactly the `delta` used in `Scatters.apply_SW` / `dense_SW`, and
the paper's own suggested value is 5e-3, which is our scan's second grid point.

> "only the first discriminant direction v_1 maximises the Fisher criterion R(v) ... The remainder
> of the discriminant directions, i.e. v_i, i = 2, ..., C-1, are just the eigenvectors of the
> generalised eigenvalue problem (14), rather than meeting/maximising the Fisher criterion"

Theorem IV.1 (eqs. 16-21) is the paper's non-orthogonality statement for classic LDA: if
v_j^T S_W^-1 S_B v_i != v_j^T (S_W^-1 S_B)^T v_i then v_i is not orthogonal to v_j. This is what
our H3 tests.

## 2. Algorithm 1 - the sequential construction (Sec. V-B, Theorem V.2)

The optimisation the n-th direction solves (37):

    max_u  R(u) = (u^T S_B u) / (u^T S_W u)
    s.t.   u perp u_1 perp ... perp u_{n-1}

and the recursion it is equivalent to (38):

    (S_B - U_{n-1} T_{n-1}^{-1} B_{n-1}) u = mu S_W u

with

    U_{n-1} = (u_1 ... u_{n-1})                                        (39)

    B_{n-1} = [ u_1^T S_W^{-1} S_B ; ... ; u_{n-1}^T S_W^{-1} S_B ]    (40)  ((n-1) x M)

    T_{n-1}[i, j] = u_i^T S_W^{-1} u_j,  1 <= i, j <= n-1              (41)

u_n is the eigenvector of (38) for its largest eigenvalue, and that eigenvalue equals the Fisher
ratio of u_n (eqs. 51-53).

Three points that the implementation and the report both depend on:

1. **The constraint in (37) is ordinary Euclidean orthogonality** (`u perp u_i`), and the
   Lagrangian (42) is written with plain `beta_i u^T u_i` - not `u^T S_W u_i`. So GO-LDA's
   directions are mutually orthonormal in the Euclidean metric while classic LDA's are not. That
   is the whole content of the paper's Fig. 1 and of our H3, and it means **the two methods'
   first C-1 directions span different subspaces unless they coincide by accident.**
2. Eq. (23): `u_1 = v_1`. The first direction is shared with classic LDA. Any disagreement must
   start at direction 2 or later.
3. The recursion is a *left* deflation: `S_B - U T^{-1} B` multiplies u, then the pencil is
   generalised against S_W. `src/golda.py:go_lda` forms `Mleft = B_r - Ucoef @ solve(T, Bn)` with
   `Bn = Wcoef.T @ B_r` and `Wcoef = A_r^{-1} Ucoef`, i.e. `U (U^T A^{-1} U)^{-1} U^T A^{-1} B_r`,
   which is (38)-(41) with S_W replaced by the ridged S_W' = S_W + delta I. `deflated_sides()`
   re-derives both sides of the same equation to certify the residuals, and the parity gate's
   check 5e re-derives the recursion by brute force on a dense fixture.

## 3. What the paper claims about accuracy (Sec. VI-B, before Table II)

> "Let Omega_l denote the discriminant subspace formed by the first l principle/discriminant
> directions of PCA, classic-LDA or GO-LDA. Therefore, for PCA and GO-LDA, l is the dimensionality
> of Omega_l and can be as large as M, while for the classic-LDA, l can only be as large as
> (C - 1)"

> "All the quantitative results with uncertainties in the tables below are estimated by ten-fold
> cross-validation."

> "Table II gives the comparison between PCA, classic-LDA and GO-LDA using the k-nearest neighbour
> classifier (with k set to 1 for simplicity)"

> "For the results on the discriminant subspace Omega_{C-1}, apart from a single outlier (i.e.,
> results on the ForestTypeMapping data set with discriminant subspace Omega_3), the performance of
> the classic-LDA and GO-LDA outperforms PCA dramatically, and **GO-LDA outperforms the
> classic-LDA**."

> "For the results on the discriminant subspace Omega_l where l > C-1 ... GO-LDA achieves better
> results than PCA for all the cases ... In particular, we find that when more discriminant
> directions are used, GO-LDA's discriminant ability increases **in six of the nine problems**,
> sometimes substantially e.g. see the case of the DeepDrid problem."

Reading that our hypotheses have to respect:

- The paper claims **superiority**, not parity, at K = C - 1. Our H1 was scoped to the ORL row
  (where the two published numbers overlap: 0.99 +/- 0.02 against 0.98 +/- 0.01), and stage 2 §4
  words it as "statistically indistinguishable on ORL", which is a reading of that row rather than
  a theorem the paper states.
- The beyond-cap claim is explicitly hedged: six of nine problems, and the comparison drawn in the
  text at l > C - 1 is against **PCA**, not against classic LDA (which has no such l).
- Table II's classifier is **1-NN**. M2 scores with C4's penalised logistic head, which is a
  protocol difference we introduced deliberately (supervisor's ruling U007) and must therefore
  control for; see `src/probe_m2_head.py`.

## 4. Table II rows this project quotes

| Data | C/N/M | Method | on Omega_{C-1} | beyond the cap |
| --- | --- | --- | --- | --- |
| ORL | 40/400/10304 | PCA | 0.78 +/- 0.02 (Omega_39) | 0.97 +/- 0.02 (Omega_50) |
| ORL | 40/400/10304 | classic-LDA | 0.98 +/- 0.01 (Omega_39) | N/A |
| ORL | 40/400/10304 | GO-LDA | 0.99 +/- 0.02 (Omega_39) | 0.99 +/- 0.01 (Omega_50) |
| BrainTumor | 4/800/512 | PCA | 0.38 +/- 0.01 (Omega_3) | 0.39 +/- 0.01 (Omega_4) |
| BrainTumor | 4/800/512 | classic-LDA | 0.53 +/- 0.02 (Omega_3) | N/A |
| BrainTumor | 4/800/512 | GO-LDA | 0.57 +/- 0.01 (Omega_3) | 0.59 +/- 0.02 (Omega_10) |
| DeepDrid | 5/662/512 | PCA | 0.27 +/- 0.01 (Omega_4) | 0.44 +/- 0.05 (Omega_20) |
| DeepDrid | 5/662/512 | classic-LDA | 0.27 +/- 0.04 (Omega_4) | N/A |
| DeepDrid | 5/662/512 | GO-LDA | 0.29 +/- 0.04 (Omega_4) | 0.50 +/- 0.05 (Omega_20) |

The only two 512-dimensional feature-space rows the paper has are BrainTumor (C = 4) and DeepDrid
(C = 5): their caps are 3 and 4 directions inside a 512-dimensional space, so "beyond the cap"
means up to 128x more directions. Our M2 regime has C = 100 and C = 200 against 512 and 384
features, where the cap already consumes 19-52 % of the space and beyond-cap means 1.3-2.6x. The
paper's evidence does not cover the regime we test, which is a scope statement the report needs.
