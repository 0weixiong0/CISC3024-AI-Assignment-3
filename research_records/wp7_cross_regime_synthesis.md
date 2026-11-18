# WP7 — Cross-regime synthesis: what survived the move from pixels to features

Written 2026-11-18, after M2's three invocations landed and before Stage 4. This is the argument the
report's "what we learnt" section is built from; the numbers are copied from
`stage_03a_pilot_feasibility.md` (raw pixels), `stage_03b_full_results.md` (frozen features) and the
artefacts they name. Nothing here is a new measurement — where a number is needed it is quoted with the
split it came from.

## 1. The question, stated so it can be answered

The brief asks us to reproduce a published algorithm with AI tooling and report what we learnt. The paper
(GO-LDA, arXiv:2305.14568v1) reports its evidence on face data in raw pixels (ORL, LFW) and on deep
features at 512 dimensions for 4- and 5-class problems. Those are two very different regimes, and the
paper never compares them. We ran the same implementation in three regimes, so the cross-regime question
is the sharpest one this project can answer:

**Which of GO-LDA's properties are properties of the algorithm, and which are properties of the regime
the paper happened to measure them in?**

## 2. The three regimes side by side

| | ORL main | ORL small-sample (supplementary) | Frozen features (4 pairs) |
| --- | --- | --- | --- |
| Representation | raw pixels, M = 10,304 | raw pixels, M = 10,304 | ResNet-18 512-d / DINOv2 ViT-S/14 384-d |
| Classes `C` / cap `C − 1` | 40 / 39 | 40 / 39 | 100 / 99 and 200 / 199 |
| Cap as a share of the space | 0.38 % | 0.38 % | 19.3 %, 25.8 %, 38.9 %, 51.8 % |
| Train rows | 360 per fold (9/subject) | 160 (4/subject), single split | 50,000 (CIFAR-100) / 100,000 (Tiny ImageNet) |
| Rows per class at fit time | 9 | 4 | 500 |
| Head | 1-NN (paper's Table II) | 1-NN | C4's L2 logistic, LBFGS 5000, C = 1.0, post-projection scaler |
| Hyper-parameter choice | δ grid, K grid | δ grid, K grid | 5 % hold-out selects both, test used once |
| `S_W` conditioning | rank-deficient by construction (M = 10,304 against 360 rows); the certified δ ≥ 1e-4 range exists because below it the beyond-cap directions were not trustworthy | same, and worse: at δ = 0 only **28** usable directions survive where C − 1 = 39 | well-conditioned after the ridge: measured κ_eff 3.8e2 (Tiny × ResNet-18) to 4.7e8 (CIFAR × DINOv2), residuals inside the `10 · eps · κ` bound in all four pairs |

The two axes that change together and matter most are **cap/M** (the rank cap goes from negligible to
about half the space) and **rows per class** (9 → 4 → 500). §6 returns to which of them the evidence
actually distinguishes.

## 3. Verdict per hypothesis, by regime

| | ORL main | ORL small-sample | Frozen features |
| --- | --- | --- | --- |
| **H1** — indistinguishable on the paper's face-data rows | **holds**: at the cap both arms 0.9850, paired difference exactly 0.0000 on 10/10 folds, spans agreeing to 1.5–2.1e-6° | **holds**: both arms 0.9042 at the cap on the single split (160 train / 240 test) | **fails, and this was not a prediction**: at the cap, GO-LDA is 6.5 points behind classic LDA (test, δ pinned for both arms; `probe_head_control.json`) |
| **H2** — gains beyond the cap | **holds**: 0.9850 at cap → 0.9875 (K = 40) → 0.9900 (K = 50); also above no-projection 0.9750 | **fails**: 0.9042 → 0.9000 → 0.8917, consistently at every δ ≥ 1e-4 | **mechanism holds, claim fails**: the curve rises past the cap on all four pairs (+4.9 / +1.0 / +0.6 / +0.2 points to its selected K) and on the two DINOv2 pairs turns back down by K = 256; on the official test split and in the five-fold CV the endpoint never reaches the baselines' cap value (deficits −2.3 / −1.5 / −1.9 / −0.1 points, test), and on the hold-out it falls short on all four pairs (−1.64 / −0.76 / −1.50 / −0.06 points, each baseline at its own δ). One reading crosses: Tiny × DINOv2 at `K` = 200 (0.7988) against the cap line re-drawn at GO-LDA's own δ (0.7984), i.e. +0.04 points — hold-out only, one pair, and δ-convention dependent (`stage_03b` §4, §3.3) |
| **H3** — orthogonality of the directions | **holds**: GO's off-diagonal |uᵢᵀu_j| ~1e-14, classic's 0.19–0.25 | **holds** | **holds** on all four pairs (GO 2.8e-8 … 3.0e-14; classic 0.17–0.25) |

Read as a whole: **H3 is the algorithm's own property and travels perfectly. H1 and H2 do not.** The one
thing GO-LDA guarantees by construction — Euclidean-orthogonal, Fisher-monotone directions — reproduces
everywhere we looked. Everything that was an *empirical advantage* in the paper's regime is regime-bound.

## 4. What reproduces everywhere, and is therefore the algorithm

* Sequential deflation yields positive, decreasing eigenvalues beyond the cap (`mu_beyond_cap_first_three`
  in `diagnostics.json`, all four feature pairs; §4 of `stage_03b`).
* Fisher ratios monotone in every direction, in every regime (`fisher_monotone` true in 4/4 pairs, plus
  check 5c on ORL).
* Each GO direction carries a *larger individual* Fisher ratio than the corresponding classic direction:
  the μ sum over the first 99 directions is 104.0 against classic's 45.6 (`probe_cap_gap.json`). This is
  the paper's stated mechanism, and it is real in our runs.
* Every direction satisfies the full-space deflated pencil to a relative residual inside the
  `10 · eps · κ` bound (worst 1.66e-9 against a 1.04e-6 tolerance), and the dense and span-reduced routes
  agree to 2.1e-6°. So none of the above is an artefact of how we solved it.

## 5. What does not reproduce, and what was ruled out as the reason

The feature-regime cap gap (−6.5 points) survived every control we could build without new data —
**five candidate explanations plus the sample/fold control, six rows in the table below**:

| Candidate explanation | Control | Result |
| --- | --- | --- |
| The solver for the classic arm | `eig` vs symmetric-definite `eigh` | eigenvalues to 1.2e-14, spans to 1.9e-6° — not the solver |
| Our route (dense vs span-reduced) | same data, same δ | μ to 1.1e-14, span to 2.1e-6°, same accuracy 0.6045 — not the implementation |
| The head preferring one coordinate system | QR-orthonormalise both bases | −6.54 → −6.49 points — not a rotation of the axes |
| The head itself | C4 logistic / paper's 1-NN raw / 1-NN standardised | −6.5 / −11.0 / −7.5 points — the paper's own classifier is *harder* on GO-LDA |
| Regularisation chosen differently | δ pinned to GO-LDA's own value for all arms (§3.3) | gap unchanged at 6.56 points (hold-out, at the cap) |
| Sample size or fold structure | 5-fold CV on all four pairs (§3.2) | GO-LDA stays **below the best baseline on every pair** — fourth on three of them, third on Tiny × DINOv2, where it beats ridge-regularised classic LDA and loses to PCA-then-LDA and shrinkage-LDA. Its fold range is disjoint from all three baselines on the two ResNet-18 pairs and overlaps classic-ridge's on both DINOv2 pairs |

What is left is geometric. Divergence starts at **direction 3**: direction 1 is identical to classic LDA's
(|cos| = 1.000000), direction 2's span differs by 0.117°, direction 3 by 61°, and the median principal
angle over the first 99 pairs is 55.9°. Because eq. (37) constrains each new direction to be
*Euclidean*-orthogonal to its predecessors while classic LDA's directions are only
*S_W*-conjugate in the pencil sense, the two constructions are not chasing the same object — and on ORL
the deflation is nearly inert inside the cap (parity check 5b), which is why the same two constructions
happen to land on one subspace there.

**That is the finding to state in the report**: parity at the cap was never a theorem of the paper. It is
what happens in a regime where the cap is 0.38 % of the space and nine images per class make `S_W` so
degenerate that deflation has nothing to remove. Widen the cap to a fifth or a half of the space, fit on
500 well-conditioned rows per class, and the two subspaces part company from the third direction onward.

## 6. What we could not settle, and what the ORL dimension ladder changed

Rows-per-class and cap/M moved together across the three regimes, so the evidence in §5 did **not**
separate "the features are better conditioned" from "the cap occupies too much of the space". The cheap
control that was supposed to break that confound is ORL raw pixels at a *reduced* dimension — same C = 40,
so cap/M rises as M falls, while rows per class stays exactly where the MVP put it. Supervisor U010 released
it (item 2, with a 10-minute ceiling). The first run of it is **withdrawn**: `src/orl.py` had `IMG_H` and
`IMG_W` swapped, so `src/probe_orl512.py`'s box-average laid the 10,304-pixel raster out as 92 rows of 112
when the PGM is 112 rows of 92, and every rung's features came from a sheared image rather than a downsampled
one. The re-run (`src/probe_orl512.py` → `runs/orl512_fix/orl512_ladder.json`, **392 s**, inside the ceiling)
gives a different answer, and the honest summary is that **the control came back negative: a high cap/M in raw
pixels does not by itself produce the deficit, so this ladder neither breaks the confound nor supports the
ratio explanation.**

`runs/orl512_fix/orl512_ladder.json`: ten folds, 1-NN head (the paper's own Table II protocol), δ = 5e-3 on
both pencil arms, K = cap = 39, pixels box-averaged to each rung's W × H by a fixed label-blind linear map
applied identically to every method, fold and split.

| Rung | cap / M | M / N_train | rows/class | GO-LDA | ridge classic | shrinkage | PCA-then-LDA | no projection | GO − classic (paired) | span at cap |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 10 × 8 (M = 80) | 48.8 % | 0.22 | 9 | 0.9850 | 0.9900 | 0.9900 | 0.9850 | 0.9875 | **−0.50 pt** (2 ahead / 3 behind / 5 tied) | 88.5° |
| 13 × 12 (156) | 25.0 % | 0.43 | 9 | 0.9850 | 0.9850 | 0.9900 | 0.9875 | 0.9850 | **0.00** (2 / 2 / 6) | 89.1° |
| 16 × 16 (256) | 15.2 % | 0.71 | 9 | 0.9750 | 0.9450 | 0.9875 | 0.9875 | 0.9825 | **+3.00** (5 / 0 / 5) | 88.8° |
| 32 × 16 (512) | 7.6 % | 1.42 | 9 | 0.9575 | 0.9575 | 0.9850 | 0.9850 | 0.9800 | **0.00** (0 / 0 / 10) | 2e-6° (defect 4e-16) |
| native 112 × 92 (10,304) | 0.38 % | 28.6 | 9 | 0.9850 | 0.9850 | — | — | — | **0.00** (10/10, §4 quoted) | ≈2e-6° |

Three things come out of the corrected run, and the first is a withdrawal.

1. **The reversal is gone.** The withdrawn run reported −11.75, −8.25, −0.50, 0.00 points in step with cap/M;
   the corrected run reports −0.50, 0.00, +3.00, 0.00 — no monotone trend, and the largest rung difference
   goes the *other* way. So the earlier "the reversal tracks the ratio" sentence was a property of the
   reshape bug, not of GO-LDA. What the ratio explanation now has is a negative control: at cap/M = 48.8 %
   in raw pixels the two pencil arms are within half a point of each other, where the feature regime at
   cap/M = 19–52 % is 6.5 points apart. High cap/M is therefore not sufficient for the deficit.
2. **Parity at M = 512 is exact, and that part survived the bug.** At M = 512 the two arms tie on all ten
   folds *and* their cap-rank subspaces coincide to 2e-6° with a certification defect of 4.2e-16 — the
   numerical floor, against a control pair on the same folds at 62°. The same agreement holds at the native
   10,304 dimensions (§4), so parity is a property of the pencil at K = C − 1, independent of M.
3. **The ladder has little power at these rungs.** All five arms stay inside a 4.5-point band
   (0.9450–0.9900) and no-projection never falls below 0.9825, so box-averaging to 80 pixels barely changes
   the difficulty of ORL. A control that compresses every method against the ceiling cannot rank them, which
   is why the rungs show nothing to attribute — this is a limit of the design, not evidence of equality in
   general.

**What the negative result does to §5's five explanations.** It does not clear the ratio explanation so much
as remove its support: the ladder was the only evidence that cap/M alone could produce the gap, and that
evidence was the reshape artefact. §5's feature-side explanations — conditioning of the within-class scatter,
rows per class, the head — are back in play, and the honest position is that the deficit is currently
established only in the feature regime, with no controlled account of why it appears there. The collinearity
inside the ladder is also still unresolved, and now moot: cap/M and M/N_train are both functions of M at
fixed C and N, so they move together, but with no effect at any rung there is nothing for either of them to
explain. Splitting them would need N varied at fixed M — class subsets of ORL at 32 × 16, or the feature
pairs subsampled to equalise rows per class — which is a new experiment rather than a re-read, and is not in
the plan or the released list. §5's conclusion stays stated so that it holds whichever of the two ratios is
operative: the parity claim fails in regimes where the cap is a large fraction of the space *and* the fit is
comparatively data-poor, and it holds where both are small.

## 7. The control the plan promised: what it was, and what it found

Plan §4 committed to "one out-of-distribution control is added so the conclusion is not tuned to a single
pair of datasets". U010 chose option A and it ran on 2026-11-18: `src/probe_m2_ood.py` →
`runs/m2_matrix/probe_ood.json`, **915 s = 15.3 min** measured (my estimate was ~3 min; it assumed the
fitted projections could be reused, but M2 stored accuracies rather than bases, so both pairs' pencils were
re-solved). CIFAR-100's official test images get one corruption at one severity — additive white Gaussian
noise at σ = 0.08 on the [0, 1] pixel scale, which is severity 1 of ImageNet-C's gaussian family
(Hendrycks & Dietterich 2019, arXiv:1903.12261) — applied to the native 32 × 32 pixels before the frozen
backbone's own resize and normalisation, one noise field shared by both backbones, seed 20261117.
Projections, scalers and heads come from clean train at each method's own selected (δ, K); nothing is
refitted on the shift; the severity was not swept. The script refuses to publish its corrupted column unless
each arm's clean column reproduces `stage_03b` §3.1, and 8/8 arms did, to 0.0000.

| | ResNet-18/512 | DINOv2/384 |
| --- | --- | --- |
| clean order (§3.1) | shrinkage 0.6708 > ridge 0.6699 > PCA 0.6688 > **GO-LDA 0.6478** | ridge 0.8244 > shrinkage 0.8240 > PCA 0.8195 > **GO-LDA 0.8098** |
| corrupted order | ridge 0.1550 > PCA 0.1522 > shrinkage 0.1521 > **GO-LDA 0.1499** | shrinkage 0.4453 > PCA 0.4448 > ridge 0.4401 > **GO-LDA 0.4194** |
| drop, all arms | −49.8 to −51.9 points | −37.5 to −39.0 points |
| GO-LDA minus best baseline | −2.30 → **−0.51** points | −1.46 → **−2.59** points |
| no-projection reference | 0.6282 → 0.1239 | 0.8074 → 0.3973 |

So the control does what it was for: **GO-LDA is last of the four on both backbones after a shift it was
never fitted for**, which is the reading the plan was worried might be an artefact of the pairs we chose.
It also bounds what may be claimed. The order *among the three baselines* reshuffles on both backbones, so
`ranking_preserved` is false and the report says the study's own comparison survived, not the four-way
ranking. And the deficit's size moves opposite ways on the two backbones (−2.30 → −0.51 and −1.46 → −2.59),
so one severity supports no robustness ranking of the form "δ points more robust" — at this level the arms
compress toward a common failure on ResNet-18 and stay separated on DINOv2. Most of the collapse is the
corruption itself: the no-projection arm loses 41–50 points too, and every projected arm still ends above
it in both columns.

This replaces §5's earlier caveat that "both datasets share a family": they still do, but the conclusion is
now known to survive a distribution shift inside that family, which is a stronger position than two clean
pairs alone. It is not a cross-domain test — no medical, sketch, or low-resolution domain was touched, and
the severity was fixed in advance rather than profiled.

## 8. What the report's "what we learnt" section should say

Three sentences, in this order, because the second is what makes the first honest:

1. Using AI tooling end to end, we reproduced a recent PCA/LDA-family algorithm and its published
   mechanism exactly: the directions are orthogonal, individually more discriminative, and certified
   against an independent reconstruction of the full-space pencil.
2. Its *published advantage* did not survive the move out of the paper's regime: at the rank cap on frozen
   deep features GO-LDA is 6.5 points behind classic LDA, and going past the cap buys back less than the
   baselines already have — a negative replication we established with six controls — five candidate explanations plus the
   sample/fold control — rather than one run.
3. The lesson is about evidence, not about the algorithm: the paper's own 512-dimensional rows are 4- and
   5-class problems, and ORL's parity is a small-sample coincidence; a claim measured where the rank cap is
   under 1 % of the feature space does not transfer to where it is 19–52 %, and the honest way to find that
   out is to look for the coincidence's precondition rather than to assume the theorem.

## 9. Artefacts this synthesis reads

* `runs/mvp_orl/` — 2,880 per-fold rows, 278 summary rows, `diagnostics.json`, `fold0_probes.json`.
* `runs/mvp_orl_small_sample/` — 288 rows, same schema, supplementary and never pooled.
* `runs/m2_matrix/` — `accuracy_rows.csv` (276), `selection.csv` (16), `cv_summary.csv` (16 rows over all
  four pairs, three invocations), `diagnostics.json`, `probe_cap_gap.json`, `probe_head_control.json`,
  `timing.json` (per-invocation ledger).
* `runs/parity/parity_report.json` — 11 gated checks, 18 reported.
* `runs/orl512_fix/orl512_ladder.json` — §6's ladder, 392 s, ten folds × four rungs.
  `runs/orl512/orl512_ladder.json` is the same probe before the `IMG_H`/`IMG_W` fix: kept for provenance,
  and its reversal is quoted nowhere else in this record.
* `runs/m2_matrix/probe_ood.json` — §7's out-of-distribution control, 915 s.
* `research_records/sources/golda_arXiv2305.14568_notes.md` — the verbatim equations and claims.
