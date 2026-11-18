# Stage 02 — Algorithm Description, Design and Implementation Plan

Project: CISC3024 AI Assignment #3 · Date: 2026-11-17
Gate status: **PLAN APPROVED on 2026-11-17 (U007)**, with the supervisor's five pre-work amendments
plus one complexity correction applied throughout this file. Implementation of M0/M1 started on the
same instruction ("改完直接开 M1，不另等一轮审批"); nothing else has been implemented, downloaded or
trained beyond the §7 release.
Approval this plan executes: Stage 1 passed on 2026-11-17 (U006) — Option A (GO-LDA), weights
20/15/25/20/20 unchanged, both evaluation regimes in MVP-first order.
Evidence base: `stage_01_candidate_scoring.md` §4–§6 and `stage_01_search_protocol.md` §8 (V1, V6, V9,
V10). Method loop: `Agent_coding.pptx`, slides 4–11 — Decomposition → Task Description → Preparation
(Plan) → Execution → Supervision → Verification → Result Presentation → Evaluation → Iteration.

---

## 1. Task description (deck slide 7: goal, scope, constraints, input, output, functional requirements)

| Field | Statement |
| --- | --- |
| Goal | Reimplement **GO-LDA** (arXiv:2305.14568, Liu / Cai / Niranjan 2023) from its published equations, and test its claim on image data: that classic multiclass LDA's discriminant directions beyond the first are neither mutually orthogonal nor individually Fisher-maximising, and that a sequential deflated eigensolve fixes this. |
| Scope | Two regimes, in the approved order: (M1) raw-pixel ORL, (M2) frozen-feature CIFAR-100 and Tiny ImageNet. Baselines, cross-validation, a regularisation sweep, and the parity checks in §5. Front end and report are Stages 4–5 and are not in this plan's build scope. |
| Out of scope | No neural-network training (supervisor ruling U002: the algorithm need not be a network); no reproduction of C4's 180-configuration benchmark; no CUB-200 run; no Koo-Fu CLIP / ImageNet-1K; no RSSPCA unless Option C is later revived. **Plain PCA is not a standalone baseline row** — it appears only as the first step of PCA-then-LDA. |
| Constraints | The student writes **no** code — the AI writes 100 % of it (brief). Everything runs locally on this machine (i9-13900H, 32 GB RAM, RTX 4060 Laptop 8 GB, Python 3.12.10, numpy 2.4.6, scikit-learn 1.9.0, torch 2.7.1+cu128 with CUDA available). Deliverables on disk in English. Deadline 2026-11-23; five days remain after this plan. |
| Input | ORL / AT&T Database of Faces: 40 subjects × 10 images, PGM 92 rows × 112 columns, flattened `M = 10,304`, matching the paper's own `C/N/M = 40/400/10304`. Source is the mirror in §7: `cam-orl.co.uk/orl_faces.zip` returns **HTTP 403** (probed 2026-11-17). **`sklearn.datasets.fetch_olivetti_faces` is not used** — it serves a 64 × 64 resample (4,096 dims) and would not match the paper's `M`. Also CIFAR-100 and Tiny ImageNet train/test splits; frozen ResNet-18 (512-d) and DINOv2 ViT-S/14 (384-d) features. |
| Output | `src/` implementation, per-scale feasibility reports (Stage 3 gate), experiment result tables + figures, `webapp/` visualisation, and the evidence trail this file records. |
| Functional requirements | Accuracy per (method, dataset, dimensionality) under a fixed CV protocol; Fisher ratio per direction; pairwise non-orthogonality of classic-LDA directions; sensitivity to the ridge δ; a reproducible seed regime; intermediate states exported so the front end can display them. |

**Evaluation classifier — fixed per regime, not tuned (amendment 2).** Both configurations below were
read from their sources rather than recalled.

| Regime | Classifier | Verified wording of the source |
| --- | --- | --- |
| ORL raw pixels (M1) | **1-NN**, ten-fold cross-validation | GO-LDA paper: "Table II gives the comparison between PCA, classic-LDA and GO-LDA using the k-nearest neighbour classifier (with k set to 1 for simplicity)"; "All the quantitative results with uncertainties in the tables below are estimated by ten-fold cross-validation" |
| CIFAR-100 / Tiny ImageNet (M2) | **L2-regularised logistic regression, LBFGS, `max_iter = 5000`, `C = 1.0`, `StandardScaler` applied after projection**, identical for every method | C4 README, "Classifier" section: "L2-regularized logistic regression (LBFGS, max_iter=5000, C=1.0) with StandardScaler applied after projection. Identical hyperparameters across all methods for fair comparison." |

The scaler is fitted inside each training fold only, after projection, and never on the test fold.

**What each comparison actually is (amendment 2, second half).**
- **Projection methods** — the things that change the space: GO-LDA (ours), classic LDA, PCA-then-LDA,
  shrinkage LDA. Classic LDA's own regularisation is *within* the method and is reported alongside it.
- **Classifier baselines** — the things that change the read-out, run in whatever space they are given:
  **nearest-class-mean** (in the original space it is the no-projection reference; in a discriminant
  subspace it is the closed-form linear read-out that makes "LDA as a classifier" comparable to
  "LDA + 1-NN"), the C4 logistic head, and 1-NN as the paper's head.
- **No-projection reference** — C4's "Full" row: classifier on the unprojected features. This is what
  nearest-class-mean is *not*: NCM is a classifier, and "Full" is a feature regime. Keeping them separate
  is what stops the table from double-counting one baseline under two names.
- Plain PCA — first step of PCA-then-LDA only, never its own row.

**Reference material given to the implementer** (deck slide 9: existing reference / paper / expected
outputs): the GO-LDA paper section holding Algorithm 1 and equations 38–41; `scikit-learn`'s
`LinearDiscriminantAnalysis` as the classic-LDA oracle; C4's README protocol description for the
frozen-feature regime (baseline set, `d = C − 1`, the component sweep values `[5, 10, 20, 40, 60, 80, 99]`);
A2's `src/` layout and audit scripts as the house style.

## 2. Algorithm as specified (what will be implemented)

Classic LDA solves the generalised eigenproblem `S_B u = λ S_W u` and takes the top `C − 1` directions.
GO-LDA instead builds the directions **sequentially**:

1. Form `S_W`, `S_B` from the training class means and scatter matrices; use the regularised
   `S_W' = S_W + δ I` (the paper proposes δ on the order of 5 × 10⁻³ and does not state which value it
   used — so δ becomes a hyper-parameter we sweep and report, not a constant we inherit).
2. Direction 1: solve the ordinary generalised problem and take the eigenvector with the largest
   eigenvalue. This must coincide with classic LDA's first direction.
3. Direction *n* (n ≥ 2): deflate. Partition the already-found directions as `U_{n−1}`, with the
   corresponding quantities `T_{n−1}` and `B_{n−1}`, and solve the **non-symmetric** pencil
   `(S_B − U_{n−1} T_{n−1}⁻¹ B_{n−1}) u = μ S_W' u`; take the largest `μ`. The deflation is what forces
   the new direction to be orthogonal to its predecessors and Fisher-maximising on its own.
4. Stop at the requested dimensionality `K`, which may exceed `C − 1` — the whole point of the method.

Other consequences accepted in advance: a general (non-symmetric) eigensolver is required; eigenvalues
must be sorted by real part with a documented tie rule; and `S_W'` conditioning is checked rather than
assumed invertible.

**Cost: the paper's bound is not the budget (amendment 6).** The paper reports
`O(NM²) + O(M³) + K·O(M²)` against classic LDA's `O(NM²) + 2O(M³)` — same order, cheaper as `M` grows
when `K ≪ M`. That `K·O(M²)` term, however, is a **theoretical** bound that presumes each deflated step
is solved iteratively for its leading eigenvector. A dense `scipy.linalg.eig` on the `M × M` pencil costs
`O(M³)` **per step**, so at ORL's `M = 10,304` one step is ~1.1 × 10¹² flops on a 0.85 GB float64 matrix,
a generalised non-symmetric solve needing several times that again in workspace; 39–50 steps × 10 folds ×
a δ grid is a day of compute, not an MVP. The plan therefore does **not** budget on the bound; it budgets
on the dense arithmetic and buys the cost back with a change of coordinates:

1. **Primary route — exact span reduction (dual coordinates), `r ≤ N − 1`.** `S_W'` has rank ≤ `N − C = 320`
   on an ORL training fold plus the δ ridge, and `S_B` has rank ≤ `C − 1 = 39`, so any direction with
   `μ ≠ 0` lies in the span of the within-class centred data together with the class means — dimension
   ≤ `N − 1 = 359`. Build an orthonormal basis `Q` of that span once (a `M × r` QR, ~10⁹ flops, ~30 MB),
   express the deflated pencil and `S_W'` in those coordinates (`Qᵀ(δI)Q = δI_r` exactly for orthonormal
   `Q`), and run the `K ≤ 50` sequential eigensolves in `r ≤ 359` dimensions. Every `O(M³)` becomes `O(r³)`.
   The reduction is **exact, not approximate** — the pencil is restricted to an invariant span rather than
   truncated — and it is the core implementation change of this project, so it is declared as a deviation
   in the feasibility report and verified by checks 1c, 3c and 3b.
2. **Fallback route — `S_W'⁻¹` plus iterative leading-eigenvector maximisation**, which is the shape the
   paper's own bound describes, used if route 1's equivalence check fails.
3. **The reduction is verified, not assumed** (U008 amendment 2 names the three checks). 1c: reduced route
   equals dense route at δ = 0 on the full-rank fixture. 3c: reduced equals dense on a 200-dimensional
   ORL surrogate where dense arithmetic is affordable. 3b: after each direction is returned, the residual
   of `(S_B − U_{n−1}T_{n−1}⁻¹B_{n−1})u − μ S_W' u` is evaluated in the **full `M`-dimensional space**,
   matrix-free, and reported as a **relative** residual — the scatters carry pixel-squared magnitude, so
   an absolute norm is not interpretable and the unnormalised `‖·‖/‖u‖` form this line first sketched was
   replaced. The threshold is derived from the pencil's own conditioning (`10 · eps · κ` under the
   solver's truncation), with a control arm in check 3b showing the threshold discriminates.
4. Peak memory is capped deliberately: the reduced Gram products are formed in float64 blocks of the
   `360 × 10,304` data matrix, so no `M × M` object is ever materialised for ORL; the dense `M × M` path
   is exercised only at small `M`.

**Falsifiable claims this experiment tests** (stated before implementation, so a null result is a
reportable outcome rather than a failure):

- H1 — at `K = C − 1`, GO-LDA and classic LDA are statistically indistinguishable on ORL (paper: 0.99 ± 0.02
  vs 0.98 ± 0.01 at 39 dims; the same shape on LFW, 0.66 vs 0.66 at Ω4).
- H2 — GO-LDA's gains appear only beyond the rank cap, i.e. at `K > C − 1` (paper's DeepDrid 0.50 at 20
  directions vs LDA 0.27 at 4; BrainTumor 0.59 at 10 vs 0.53 at 3).
- H3 — classic LDA's directions beyond the first violate mutual orthogonality, and GO-LDA's do not;
  both measurable on our own runs, independent of any reported accuracy.

Two scope notes, added 2026-11-17 after the source was re-read in full
(`research_records/sources/golda_arXiv2305.14568_notes.md`) and after M2's cap-gap probe:

- **The paper does not claim parity at `K = C − 1`; it claims GO-LDA is better there** ("GO-LDA
  outperforms the classic-LDA", Sec. VI-B). H1 above is therefore not a restatement of a theorem in
  the paper but a reading of one table row whose two uncertainties overlap. The geometric parity our
  gate measured on ORL (spans agreeing to ~2e-6 degrees) is an empirical property of the small-sample
  regime, where `rank(S_B) = C − 1` exhausts the between-class information inside a span of at most
  `N − 1` dimensions; the recursion's own constraint is Euclidean orthogonality (eq. 37), which
  classic LDA does not impose, so nothing forces the two subspaces to coincide.
- **H1's scope is the paper's face-data rows, and its wording was tightened to say so (U009).** H1 is now
  written "indistinguishable on the paper's face-data rows" — raw pixels, 1-NN, ten-fold, `K = C − 1`, the
  row it was drawn from. M2's frozen-feature cap comparison is reported as a **post-hoc** observation in a
  separate paragraph of `stage_03b` §4, quoting the −6.5-point cap gap on the official test split
  (probes in `runs/m2_matrix/`), and it is explicitly *not* a pre-registered H1′ — the comparison was only
  designed after the numbers were on the table. The reason the cap result reverses between regimes is that
  the *subspaces* differ from direction 3 onward, not that the head prefers one basis (both controls in
  `runs/m2_matrix/probe_cap_gap.json`).

## 3. Decomposition (deck slide 4, step 1)

| WP | Package | Produces | Depends on |
| --- | --- | --- | --- |
| WP1 | Data layer: ORL loader from the §7 mirror + **M0 assertion `400 × 10,304` with each PGM 92 columns × 112 rows**; 10-fold CV splitter frozen before any run; feature extractor for frozen ResNet-18 / DINOv2 on CIFAR-100 and Tiny ImageNet, cached to disk as `.npy` | `src/data/`, `data/` feature caches, a manifest with shapes, sources and checksums | — |
| WP2 | Reference primitives: scatter matrices, classic LDA via `scikit-learn`, ridge-LDA reference at matched δ, nearest-class-mean, PCA (as the first step of PCA-then-LDA), shrinkage LDA, the C4 logistic head | `src/baselines.py` + a fixture table | WP1 (ORL only, for M1) |
| WP3 | **GO-LDA core**: sequential deflated eigensolve, δ ridge, ordering rule, `K > C − 1` support, reduced and dense routes both implemented | `src/golda.py` | WP2 |
| WP4 | **Parity checks** (§5) — gate for everything downstream | `tests/test_parity.py`, printed check report | WP3 |
| WP5 | MVP experiment on ORL: accuracy vs `K`, δ sensitivity, orthogonality and Fisher-ratio diagnostics | `runs/mvp_orl/` + `stage_03a_pilot_feasibility.md` | WP4 |
| WP6 | Feature-space matrix: CIFAR-100 and Tiny ImageNet, both backbones, baseline set + GO-LDA, held-out 5 % for `K` and δ | `runs/full_matrix/` + `stage_03b_full_results.md` | WP5 passed |
| WP7 | Cross-regime synthesis: does the raw-pixel conclusion survive in feature space? Out-of-distribution control | tables + figures for the report | WP6 |
| WP8 | Machine-readable results export for the Stage-4 front end (`webapp/data.js` contract: intermediate states, per-direction diagnostics, plus the growth-curve tables specified in §4's front-end data contract) | `src/export_results.py` | WP6 for the tables, WP7 for the conclusion |

Tracer-bullet order: WP1 → WP2 → WP3 → WP4 → WP5 is the MVP; the plan does not proceed to WP6 until the
parity checks are green and the Stage-3a feasibility report is accepted.

## 4. Plan, milestones, MVP (deck slide 11)

Duration estimates are anchored on the one measured reference this project has: A2's full experiment
matrix took **≈ 2.7 h** on this same GPU. Everything else is extrapolation and is flagged as such; the
first action in WP1 replaces the two extraction estimates with measurements.

| Milestone | Contents | Expected duration | Expected result (stated now) |
| --- | --- | --- | --- |
| M0 | WP1 + WP2 on ORL only | ~10–15 min once the 3.6 MB zip lands | ORL tensors asserted as **400 × 10,304** (PGM 92 columns × 112 rows flattened), 40 subjects × 10 images, source URL and checksum recorded; no `M × M` dense object is built — the span-reduced route of §2 is the default |
| **M1 — MVP** | WP3 + WP4 + WP5, raw-pixel ORL | **1–2 h of compute as budgeted**; the dense arithmetic in §2 is what that budget is really for — `K = 39–50` steps × `O(M³)` at `M = 10,304` would be hours, so the span-reduced route is what makes 1–2 h honest rather than optimistic, and the residual/diff checks in §5 are what make it safe | GO-LDA == classic LDA at `K = 39` within CV noise (H1); orthogonality violation visible in classic LDA and absent in GO-LDA (H3); gains, if any, only for `K > 39` (H2) |
| M1.5 | Feature extraction, one-off | **measured 2026-11-17: 18.2 min for all four pairs** — Tiny ImageNet×R18 4.2, Tiny ImageNet×DINOv2 8.1, CIFAR-100×R18 1.9, CIFAR-100×DINOv2 4.0 min (per-image rates 226–536 img/s, `data/features/manifest.json`) | cached `.npy` (340,000 vectors) + manifest with shapes, sha256 and timings; **under the 45-minute trigger, so both backbones are kept** and no matrix shrink is needed. The one decision the measurement forced: DINOv2 runs at 224×224, not the 518×518 timm registers (386.6 vs 48.5 img/s) |
| M2 — full matrix | WP6, both datasets × 2 backbones × baseline set | **plan said 3–5 h; extrapolated 3.5–4.0 h at launch; measured 2.69 h** for the two sweep invocations (CIFAR-100 4,923 s + Tiny ImageNet 4,748 s — `stage_03b` §2 keeps these per invocation, because `timing.json`'s field holds only the latest one and the 2.69 h excludes the crashed attempt's 26 min). Units: ~1.05 s per deflated GO-LDA direction at M = 512 and 0.31 s at M = 384 (the pencil is M × M whatever N is), one C4 head fit 23.7 s at CIFAR-100/512-d and 58.7 s at Tiny ImageNet/512-d (`runs/m2_matrix/calibration.json`). The phases are the hold-out sweep, one full-train refit per *selected* δ, and CV — the refit and CV phases are what the first estimate missed, and the first launch spent 26 min and then died in the refit phase on a driver bug (`runs/m2_run_stdout.txt`; fixed, and the driver now checkpoints every artefact and has a `--smoke` path that reaches those phases in minutes, `runs/m2_matrix_smoke/`). It ran as two chained invocations (CIFAR-100 with 5-fold CV, Tiny ImageNet without), and a **third** added Tiny's CV: `--cv-only` re-reads each method's selected (δ, K) from `selection.csv` and runs only the folds, so the sweep is not paid for twice — measured **2,625.2 s = 43.8 min** for both Tiny pairs (358 s per fold on ResNet-18, 167 s on DINOv2; fold 1 cost 417 s including the fixed setup). Your U009 ruling corrected the cost I had quoted for it — CIFAR-100's CV measured 2,003 + 490 s = 41.5 min and Tiny's sweep 3,565 s, so Tiny's CV was ≈ 45–60 min rather than the 1–1.5 h I said, and it landed at your number. M2 as a whole is **3.42 h** of productive compute (12,296 s over three invocations), 3.85 h counting the
crashed attempt and **4.00 h (14,400 s) counting the aborted duplicate CV invocation too** — the all-in figure
`stage_03b` §1 reports against this 3–5 h budget. That path also needed a write guard, because merging drops every stored row of a pair it rewrites and a CV-only pass would otherwise have deleted the sweep tables it did not touch (`stage_03b` §2). | a clean (method × dataset × backbone × `K`, δ) accuracy table on the official test split, ± across folds for all four pairs — CIFAR-100's from the sweep, Tiny ImageNet's from the third invocation, `realized_dim` beside every selected `K` because PCA-then-LDA's PCA width is not its discriminant width; C4's published cells stay an external plausibility reference, not a target |
| M3 | WP7 + WP8 | ~1 h | **done 2026-11-18, and the estimate was not needed**: WP7 is `research_records/wp7_cross_regime_synthesis.md` (three regimes side by side, what reproduces vs what is regime-bound, five ruled-out explanations plus the sample/fold control for the feature-regime gap, and the rows-per-class vs cap/M confound — **tested after the fact by the ORL dimension ladder U010 released**, which holds rows per class at 9 while cap/M sweeps 7.6–48.8 % and finds the paired GO-minus-classic gap at **−0.50 / 0.00 / +3.00 / 0.00** points at M = 80/156/256/512, i.e. no effect to attribute; its first run reported a −11.75/−8.25/−0.50/0.00 reversal, which came from a transposed pixel grid in the box-average and is withdrawn (see `stage_03b` §8 and WP7 §6); WP8 is `src/export_results.py` → `webapp/data.js` (305 KiB as re-exported on 2026-11-18; 260 KiB when the milestone closed, one `window.GOLDA_DATA` global so the page opens from `file://`), which carries the growth-curve fields of the data contract above, both δ readings of the cap line, per-pair CV blocks labelled `complete`/`pending`, the ORL per-fold H1 slice, the two probes and the parity gate with its gated/diagnostic split. The exporter refuses to write when a check fails; 34 checks pass (the count grew from 25 as the two released controls and the node-parse gate were added), including "every curve row carries its split" and "test points come only from `selection.csv`". **The out-of-distribution control ran the day after the milestone closed**: U010 chose option A (one fixed corruption at one fixed severity on the CIFAR-100 test images, features re-extracted through the same frozen backbones, the clean-fitted projections and heads re-scored), `src/probe_m2_ood.py` → `runs/m2_matrix/probe_ood.json`, with the ORL dimension ladder released in the same message (§5 below). Both results are in `stage_03b` §8 and WP7 §6–§7. |
| M4 / M5 | Stage 4 front end (**done 2026-11-18**, `stage_04_front_end.md`); repository + Pages (**done 2026-11-18**, live at `https://0weixiong0.github.io/CISC3024-AI-Assignment-3/`); then the Stage-5 Word report | Stage 1's estimate stands: ~4–6 h, of which the report template formatting is the known risk (A2's failure mode) | browser demo of dataset access, intermediate states and outputs (delivered); a live Pages URL plus the commit it points at (delivered: site commit `gh-pages` `a48a97b`; the report re-reads `git rev-parse main` at submission, see `stage_04_front_end.md` §5); then the report built from the stage summaries, citing both |

Calendar against the 2026-11-23 deadline: M0/M1 today (11-17) → M1.5/M2 on 11-18 → M3 11-19 → front end
11-20 → report 11-21/22 with 11-23 held as buffer. The plan has no slack for a fourth candidate, which is
why Option C stays unopened unless you say otherwise.

**The `K` grid, crossing the cap where the hypotheses live (amendment 4).** H2 only means something if
`K > C − 1` is actually run, and every comparison is on the **same folds with the same seeds and the same
classifier** for both methods.

| Regime | `C` | `C − 1` | `K` at or below the cap | `K` beyond the cap | ceiling |
| --- | --- | --- | --- | --- | --- |
| ORL raw pixels | 40 | 39 | 1, 5, 10, 20, 30, **39** | 40, 50 | `min(N − C, M)` ≫ 50 |
| CIFAR-100, ResNet-18 / DINOv2 features | 100 | 99 | 10, 50, **99** | **100**, 128, 256 | feature dimension: 512 (R18) / 384 (DINOv2) |
| Tiny ImageNet, ResNet-18 / DINOv2 features | 200 | 199 | 20, 100, **199** | **200**, 256 | same; 256 ≤ 384 so both backbones reach it |

For `K > C − 1` classic LDA is undefined (its between-class scatter has rank `C − 1`), so the reference
row at those `K` is the no-projection classifier and PCA-then-LDA at the same `K`, and the table says so
instead of leaving the reader to infer it.

**Validation / test discipline.** ORL: 10-fold cross-validation matching the paper's protocol, folds
fixed by seed before any GO-LDA run. Feature-space: hyper-parameters (`K`, δ) chosen on a held-out 5 %
of the *train* split; the official test split is untouched and frozen before the first run; one
out-of-distribution control is added so the conclusion is not tuned to a single pair of datasets. Every
number in the report carries its protocol (fold count, seed, `K`, δ) alongside it.

**Per-scale feasibility reports** (Stage 3 requirement, so you can stop losses): `stage_03a_pilot_feasibility.md`
after M1 and `stage_03b_full_results.md` after M2, each stating what ran, what it cost in wall-clock and
memory, which hypotheses survived, and what the next scale would add.

**Front-end data contract for the beyond-cap growth chart** (added on your U009 ruling: the chart is in,
and its source is the sweep tables rather than the summary table).

| Chart element | Source | Why this source |
| --- | --- | --- |
| Curves — GO-LDA accuracy against `K` | `runs/m2_matrix/accuracy_rows.csv`: the **hold-out** sweep, GO-LDA's rows at its own selected δ across the **full `K` grid**, for all four pairs | a curve needs every grid point; `stage_03b` §3.3 prints only the cap and the largest `K`, which is a summary of the same rows and cannot draw them |
| Single markers — each method's headline accuracy | `runs/m2_matrix/selection.csv`: **official test**, each method at its own selected (δ, `K`) | one point per method per pair, the numbers the report's tables quote |
| Horizontal baseline lines | `accuracy_rows.csv` at each baseline's own selected δ, read at `K = C − 1` — their **cap** values | classic LDA has no basis beyond the cap, so it can only be a line; the cap value is where each baseline is actually strongest |
| Split labels on every element | — | hold-out curves and test points must not read as one series; §3.1 mixes the two splits if they do |

What the chart is for: GO-LDA's own curve does keep rising past `C − 1` on all four pairs, and it still
ends below the baselines' cap lines — the mechanism reproducing and the claim not. Data the two tables
cannot serve (per-fold values behind the ±, for instance — `cv_summary.csv` stores mean, SD, min and max
only) stays out of the front end. `src/export_results.py` (WP8) is what carries these into `webapp/data.js`.

**Form of the front end (U011): a demo, not a second report.** The page is an instrument — pick a regime,
drag `K` across its grid, click a test image — and it shows what the algorithm built rather than restating
what the report says. Four views: **Instrument** (specimen browser; the `K` slider driving the accuracy
curve, the per-direction Fisher ratios, the `U′U` corner of the basis and the selected image's class rank;
and, in the raw-pixel regime, each direction reshaped into an image so H3 is visible instead of asserted),
**Noise control** (the corrupted pixels next to the clean ones, and the four arms' before/after accuracies),
**Dimension ladder** (accuracy and subspace angle against cap / M at fixed classes and fixed rows per
class), and **Tables & receipts** (the report's own numbers with the artefact and checksum behind each).

The chart contract above still governs the growth curve inside the Instrument view — same sources, same
split labels, both δ readings of the cap line. What is new is the layer under it: `src/export_demo.py` →
`webapp/demo.js`, which refits each arm's basis from the same solvers the study used and exports the
specimens' coordinates, the per-direction µ, the 24 × 24 Gram corner, class ranks by `K`, and the ORL
direction images. It is generated data, and the page says which head produced which read-out: accuracies
come from the study's logistic head, the per-image rank from nearest-class-mean, and the two are never
mixed in one number.

## 5. Verification (deck slide 4, step 6) — the checks that do not depend on the paper's numbers

**The δ convention (amendment 3) governs checks 1–2: a ridge makes exact parity disappear.**
`GO-LDA(δ > 0)` is **not** equal to `skikit-learn`'s unregularised LDA, and it is **not** exactly
Foley–Sammon either; `sklearn`'s shrinkage option is a different estimator (covariance shrinkage toward
the identity, not a fixed δ ridge), so it is never used as a parity reference. Therefore:

- **δ = 0 on a deliberately full-rank fixture** (`N ≫ M`, `S_W` genuinely invertible) is compared against
  `scikit-learn`'s classic LDA, and must agree to solver precision. This is the exact-parity check.
- **on real data, both sides carry the same δ**: the reference is a ridge-LDA we build ourselves — the
  first direction of the undeflated pencil `S_B u = λ (S_W + δI) u` — never sklearn at its default, so
  parity tests the deflation and not the regularisation.
- **the binary comparison involves exactly one direction** (`C = 2` ⇒ `C − 1 = 1`), stated as "one
  Foley–Sammon direction" rather than a set: at δ = 0 against `S_W⁻¹(μ₁ − μ₂)`, and at the same δ > 0
  against the ridge form `(S_W + δI)⁻¹(μ₁ − μ₂)`, each reported as a principal angle with its tolerance.

| # | Check | Run at | Reference | Failure means |
| --- | --- | --- | --- | --- |
| 1a | **First-direction parity**: GO-LDA's `u₁` equals the leading eigenvector of the classic pencil | δ = 0 on the full-rank synthetic fixture | an independent dense `scipy.linalg.eig` of `S_B u = λ S_W u` | the eigensolve or the scatter bookkeeping is wrong |
| 1b | **Span inclusion against scikit-learn** | δ = 0, full-rank fixture | `LinearDiscriminantAnalysis(solver='svd')` — its `coef_` rows are a different basis of the same space, so the test is span inclusion, not row equality | the classic side of the comparison is wrong |
| 1c / 3c | **Reduced route == dense route** | δ = 0 on the fixture; δ = 5e-3 on a 200-d ORL surrogate | the same implementation through `route="dense"` | the rank reduction changes the answer |
| 1d | **Same-δ parity against our own ridge-LDA reference** | every δ > 0 | the first direction of the undeflated pencil `S_B u = λ (S_W + δI) u` | the deflation is leaking into direction 1 |
| 1e | **Solver agreement for the same pencil at `K = C − 1` on real data** | ORL fold 0, δ = 5e-3 | `scipy.linalg.eigh` (the pencil is symmetric-definite in reduced coordinates) against the `eig`-based classic reference | the classic side of every comparison is wrong, so the baselines are untrustworthy |
| 2a / 2b | **Binary case: exactly one direction compared** (`C = 2 ⇒ C − 1 = 1`) | δ = 0 against Foley–Sammon `S_W⁻¹(μ₁ − μ₂)`; each δ > 0 against the ridge form `(S_W + δI)⁻¹(μ₁ − μ₂)` | closed-form | the deflation bookkeeping is wrong, since with one direction it must be inert |
| 3 | **Scatter-matrix reconstruction** | δ = 0, full-rank fixture | `scikit-learn`'s public `covariance_` (which pools with `1/N`, not the unbiased `1/(N − C)`), an independent loop for `S_B`, and `S_T = S_W + S_B` | accuracy differences would be unattributable |
| 3b | **Coordinate-reduction residual** (from §2): every direction is certified in full `M`-space by the relative residual of `(S_B − U T⁻¹ B) u − μ S_W' u`, with `S_B`/`S_W'` applied matrix-free | ORL fold 0, δ = 5e-3, `K = 50`, plus the same code on a well-conditioned fixture | the full-space pencil itself | the span assumption is wrong → switch to the `S_W'⁻¹` iterative route |
| 4 | **Measured cost of the two routes** | one ORL fold at `K = 39`, plus dense generalised eig at `M = 400/800/1600` fitted to a power law | the machine | the MVP budget is not what §4 claims |
| 5f (diagnostic) | **GO-LDA's span against classic LDA's at `K = C − 1`** | ORL fold 0, δ = 5e-3 | both arms of the same pencil | *nothing* — it is a measurement about the data, not a correctness test (see the note below the table) |

One reclassification, made on 2026-11-17 after M2, and the most instructive change in this table.
Check 1e used to gate on GO-LDA's first `C − 1` directions spanning the same subspace as classic
LDA's on ORL, in addition to the two classic-arm solvers agreeing. It passed — to 2e-6 degrees — but
re-reading the source shows the constraint the recursion actually imposes is **ordinary Euclidean
orthogonality** (`research_records/sources/golda_arXiv2305.14568_notes.md`, eq. 37 and the Lagrangian
in eq. 42), which classic LDA does not satisfy, so no theorem makes the two spans agree at
`K = C − 1`. M2 then measured them disagreeing from direction 3 onward on CIFAR-100 features (median
principal angle 55.9°, `runs/m2_matrix/probe_cap_gap.json`). A gate that asserts a coincidence of one
dataset fails a correct implementation the first time it runs somewhere else, which is the exact
failure mode §5 exists to prevent: so the span comparison moved to diagnostic **5f**, and 1e keeps
only what is implied. Same measurements, different status — `11/11 gated, 18/18 reported`.

Tolerances are derived, not chosen. A comparison that must be exact is held to `EXACT = 1e-4`
degrees; comparisons involving the trailing, near-degenerate eigenvectors of a `C`-class pencil
carry a Davis–Kahan style bound computed from that very pencil (its eigenvalue gap), and the
`K = C − 1` span comparisons are held to it rather than to a flat constant. The residual check is
held to `10 · eps · κ(A_r)` under the truncation the solver itself uses, because a correct
eigensolve of a pencil of condition number `κ` cannot leave a smaller backward error than
`eps · κ`: on ORL at δ = 5e-3 that is 8.9e-5 against a measured 3.0e-6, and the same code on a
well-conditioned fixture measures 7.6e-16. A control arm feeds check 3b a random span vector with
its own Rayleigh eigenvalue; it scores 1.0 — four orders of magnitude outside the tolerance — which
is what makes the threshold a discriminating one instead of a generous one. The paragraph's own rule
was violated once and caught by the gate rather than by review: when 1e was narrowed on 2026-11-17 it
was given an extra condition, `eig` and `eigh` eigenvalues agreeing to a relative 1e-8, which had been
written down rather than derived — the two solvers differ by 3.2e-7 on this pencil because `S_W` is
near-singular at δ = 5e-3, and the gate closed on a correct implementation. That condition is removed;
the eigenvalue agreement is reported in 1e's detail, and only the gap-derived angle bound gates. The
1.708e-06° it reports was recomputed independently (`principal_angle` on freshly built arms, same fold
and δ) to rule out a stale value in the suite.

Checks that follow from the same table:

1. Diagnostics 5a–5f, each asserted and printed rather than eyeballed: orthogonality of GO-LDA
   directions and the same measurement on classic LDA (5a on a well-conditioned fixture, where the
   paper's non-orthogonality claim is live, and 5b on ORL, where it is not); monotone non-increase
   of the Fisher ratio across GO-LDA directions and its comparison against classic per direction
   (5c); `K > C − 1` reachable only through GO-LDA, with classic LDA's rank cap reported as the
   contrast (5d); and Algorithm 1 rebuilt from equations (38)–(41) with explicit dense scatters,
   dense inverses and a standard non-symmetric generalised eig solve, diffed against the
   span-reduced sequential solver (5e). They are reported, not gated, because they measure the
   paper's claims rather than the implementation's correctness. The plan's original fifth invariant
   — float32 against float64 agreement — is dropped rather than left unmet: the pipeline is
   float64 throughout, so that comparison would probe LAPACK's sensitivity, not anything this
   implementation decides.
2. **Independent external anchor**: C4's published cells (README vs paper differ in 19 of 72 comparable
   cells, so neither set is treated as ground truth; they are used only to sanity-check our baseline
   accuracies to within a few points, and the discrepancy is disclosed in the report).

If check 1 or 2 fails, the implementation is wrong and nothing downstream runs — that is the gate.

## 6. Risks, with the mitigation written into the plan

| Risk | Handling |
| --- | --- |
| `S_W` is singular at raw-pixel scale (`N = 400 < M = 10,304`), so the deflated pencil can blow up | Ridge `S_W + δI` from the start; δ ∈ a small documented grid; report sensitivity rather than quoting a single tuned value; and no exact parity claim is made at δ = 0 on ORL (§5) |
| Non-symmetric eigensolver returns complex or unordered eigenvalues | Sort by real part with an explicit tie rule; assert the discriminant eigenvalues are real to tolerance; document the rule in the code and the report |
| The span-reduced coordinates silently dropping a direction, or the δ ridge not restricting cleanly to the span | The §5 check 3b residual evaluated in full space for every direction, plus a reduced-vs-dense diff at small `M`; fallback is the `S_W'⁻¹` iterative leading-eigenvector route, which does not need the span argument |
| Dense `K × O(M³)` eigensolve at `M = 10,304` (`K = 39–50` steps, ~10¹² flops and 0.85 GB per step) blows the MVP budget | This is the reason for the reduced route (§2 amendment 6); both routes' wall-clock and peak memory are recorded in the M1 feasibility report, so the budget claim is measured afterwards rather than only asserted now |
| Memory: a dense float64 within-class scatter at ORL is ~0.85 GB | Never materialised on the primary route (block-reduced Gram products); the feature-space regimes (512/384-d) are not at risk |
| 1-NN on high-dimensional raw pixels is scale- and distance-sensitive | Distances computed in the projected subspace only (dimension ≤ 50), fold-local scaling documented; ORL's published protocol is 1-NN so no substitution is made |
| Frozen-feature extraction slower than estimated | Measured at M1.5, and if over budget the matrix shrinks to one backbone per dataset with the reduction declared as a deviation (Stage 1 §5 style) |
| H2 fails (no gain beyond the rank cap) | Legitimate, reportable outcome: the report then presents GO-LDA as a geometric correction whose accuracy benefit does not materialise on these data, with H3 as the positive finding — the experiment is not re-specified to rescue the hypothesis |
| Dataset availability / licence | Sources and sizes probed by HTTP today (§7); `cam-orl.co.uk` is 403 so the Cambridge mirror is used; nothing outside the released list is downloaded |
| Time | Deadline buffer is one day; the plan's only compressible item is the feature-space backbone count |

## 7. Downloads — measured sizes and release status (amendment 5; released in U007)

Every size below is a `Content-Length` read from the live server on 2026-11-17, not an estimate.

| Item | Source, probed 2026-11-17 | Measured size | Needed for | Status |
| --- | --- | --- | --- | --- |
| **ORL / AT&T Database of Faces** | `http://www.cam-orl.co.uk/orl_faces.zip` → **HTTP 403**; working mirror `https://www.cl.cam.ac.uk/Research/DTG/attarchive/pub/data/att_faces.zip` → HTTP 200, `application/zip`, whose archive page states "The size of each image is 92x112 pixels" (width × height, i.e. 92 columns by 112 rows — the reading the PGM header itself gives), 40 directories × 10 images | **3,769,022 B ≈ 3.6 MiB** | M1 MVP | **released** |
| CIFAR-100 | `https://www.cs.toronto.edu/~kriz/cifar-100-python.tar.gz` → 200 via `cave.cs.toronto.edu` | 169,001,437 B = 161 MiB | M2 | **released** |
| Tiny ImageNet 200 | `https://cs231n.stanford.edu/tiny-imagenet-200.zip` → HTTP 200, `application/zip`, `Content-Length` **248,100,043 B** | **236.6 MiB ≈ 0.25 GB** — the earlier "several GB" is corrected, so it is worth including | M2 | **released** |
| ResNet-18 (ImageNet-pretrained) | `https://download.pytorch.org/models/resnet18-f37072fd.pth` → 200 | 46,830,571 B = 45 MiB | feature extraction | **released** |
| DINOv2 ViT-S/14 | `https://dl.fbaipublicfiles.com/dinov2/dinov2_vits14/dinov2_vits14_pretrain.pth` → 200 | 88,283,115 B = 84 MiB | feature extraction | weights **released**; see the note below |

Total ≈ 0.5 GB. Tiny ImageNet is therefore kept in M2 rather than traded away, on your instruction.

**DINOv2: resolved in U008 (amendment 4), no open point left.** The concern was real — instantiating the
architecture through `torch.hub.load('facebookresearch/dinov2', …)` fetches that repository's **source
code**, which was not part of the released downloads. The supervisor's answer keeps DINOv2 and removes the
third-party fetch: load `timm` **1.0.29** and use `vit_small_patch14_dinov2.lvd142m` with
`num_classes = 0`, frozen, on 224 × 224 inputs, giving the 384-dimensional embeddings the paper's C4
comparison uses. `timm` is the one new Python package in this project and it is installed on that
instruction, version-pinned; if its weights fail to download or load, the fallback is `torchvision`'s
`vit_b_16` (768-d) and the substitution is written up as a deviation rather than made silently.

**Packages and environment facts, as measured (2026-11-17).** `timm==1.0.29` is installed on U008's
instruction and is the only new package in the project; numpy, scipy, scikit-learn and torch (CUDA) were
already present and cover everything else. Three things turned out to matter and are recorded because they
will otherwise look like silent choices:

1. **The DINOv2 input resolution is a measured decision, not a default.** timm registers
   `vit_small_patch14_dinov2.lvd142m` at 518 × 518 (1,370 tokens); the model is run here at 224 × 224, the
   grid its patch-14 positional embedding resamples to (257 tokens), because on this GPU that is
   **386.6 vs 48.5 img/s** — an eightfold difference that alone decides whether the matrix fits the
   45-minute extraction ceiling. The feature dimension (384) is unchanged.
2. **This shell exports `NO_PROXY` containing `[::1]`, and `httpx` rejects it** (`Invalid port: ':1]'`)
   on every Hub request that `timm` and `torchvision` make. The fix is per-process, not system-wide: run
   the extractor with `NO_PROXY=localhost,127.0.0.1`. A first attempt at DINOv2 loading failed for exactly
   this reason, which is not a weight failure and did not trigger the `vit_b_16` fallback.
3. **CIFAR-100's archive is a Python 2 pickle of a dict**, so it needs `allow_pickle=True` and its keys
   arrive as bytes (`b'data'`, `b'fine_labels'`); the label key is `fine_labels`, not `labels`. It is read
   only from the archive on the released download list, whose size and sha256 go into the feature manifest,
   and the loaded rows are checked against the split counts before use.

## 8. Approval and the amended instructions (2026-11-17, recorded as U007)

The plan is **approved**, and your five pre-work amendments are applied above: ORL source and shape (§1,
§7), the fixed per-regime classifier plus what nearest-class-mean actually is (§1), the δ semantics of the
parity gate (§5), the `K > C − 1` grid with same-fold/same-seed comparison (§4, §5), and the corrected
Tiny ImageNet size with the download released (§7). Two more of your notes are applied: the
`K·O(M²)` term is flagged as the paper's theoretical bound rather than the budget, with the dense-eig
consequence and the fallback spelled out (§2, §6), and plain PCA is demoted to the first step of
PCA-then-LDA rather than a standalone baseline (§1). **Stage-5 order changed by U014 (2026-11-18): the
GitHub repository and Pages site come first, then the Word report** — the report cites the live URL and the
commit it points at, so GitHub/Pages is no longer the final step. U008's "at the final stage" deferral is
superseded. **Executed the same evening under U015**: public repository `0weixiong0/CISC3024-AI-Assignment-3`
with source on `main` and the site on `gh-pages`, live at
`https://0weixiong0.github.io/CISC3024-AI-Assignment-3/`; the exclusions he set (course files, `_rev.py`,
the dialogue record, the pre-fix parity logs) are in §5 of `stage_04_front_end.md`.

M1 ran on your instruction "改完直接开 M1，不另等一轮审批". The parity gate (WP4) passes 11/11 gated
checks and 16/16 overall, and the MVP grid (WP5) cost **17 min 41 s of wall clock against the 1–2 h
budget, peak 2.9 GB**. Its report — `research_records/stage_03a_pilot_feasibility.md`, with artefacts in
`runs/mvp_orl/` — is the next gate. Headline: H1 confirmed (GO-LDA and classic ridge-LDA are identical in
all ten folds at the cap, spans agreeing to ~2e-6 degrees), H2 *not testable at this scale* because every
LDA variant is already at 0.985–0.99 with nine training images per subject, H3 verified as a mechanism
(0.077 versus 3.7e-16 off-diagonality on a well-conditioned fixture) but muted on ORL. Two findings the
plan did not anticipate: delta = 0 is degenerate here (residual 1.48 against a 2.2e-3 bound, accuracy
0.275) and the beyond-cap directions need delta ≥ 1e-4 before they mean anything, which sets the
certified range for every `K > C − 1` claim in M2.
