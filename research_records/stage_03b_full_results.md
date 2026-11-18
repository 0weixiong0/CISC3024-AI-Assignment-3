# Stage 3b — M2 full-scale results (frozen features), and what they say about the three hypotheses

Status: **complete, awaiting the supervisor's acceptance.** Scale: the full experiment matrix on the
frozen-feature regime (WP6). This is the second of the two per-scale reports the brief asks for;
`stage_03a_pilot_feasibility.md` is the first (raw-pixel ORL).

Everything below is read back out of the artefacts listed in §1, not from run memory. Absolute paths
are relative to `D:\claude\workspace\CISC3024 AI Assignment 3`.

Headline: **the replication is negative, and it is negative for a reason we can point at.** On frozen
features GO-LDA trails every LDA baseline on all four (dataset, backbone) pairs, under the C4 logistic
head *and* under the paper's own 1-NN (§6). Its beyond-cap growth — the mechanism the paper is built on
— reproduces on every pair, and on one pair it is worth +4.9 points, but it starts from too low a level
to reach the baselines at the cap (§3). The gap opens at **direction 3**: the first direction is
identical to classic LDA's, and from the third the sequential construction spans a visibly different
subspace (§5). That is behaviour, not a bug — we checked the route, the solver, the classifier and the
source (§5, §6, §7).

## 1. What ran, and where the numbers live

| Item | Value |
| --- | --- |
| Driver | `src/run_m2_matrix.py` (three result-producing invocations, 2026-11-17 and 11-18, plus one that crashed) |
| Logs | `runs/m2_cifar_stdout.txt` (4,923 s), `runs/m2_tiny_stdout.txt` (4,748 s), `runs/m2_tiny_cv_stdout.txt` (2,625 s) — 12,296 s = **3.42 h** of productive compute; §2 keeps the account per invocation |
| Tables | `runs/m2_matrix/accuracy_rows.csv` (276 rows), `selection.csv` (16), `cv_summary.csv` (16) |
| Machine-read proof | `runs/m2_matrix/diagnostics.json`, `timing.json`, `manifest.json`, `progress.json` |
| Cost calibration that sized the run | `runs/m2_matrix/calibration.json` |
| Cap-gap probe | `src/probe_m2_cap_gap.py` → `runs/m2_matrix/probe_cap_gap.json`, log `runs/m2_probe_capgap_stdout.txt` |
| Head control | `src/probe_m2_head.py` → `runs/m2_matrix/probe_head_control.json`, log `runs/m2_probe_head_stdout.txt` |
| Features | `data/features/` (M1.5, four pairs, manifest `data/features/manifest.json`) |
| Head | C4's: L2 logistic, LBFGS, max_iter 5000, C = 1.0, StandardScaler fitted on the fitting split only |
| Selection | 5 % stratified hold-out of train (seed 20261117); official test split scored once per method after refitting on all of train |
| δ grid | {1e-4, 5e-3, 1e-2, 1e-1} — certified range only (§8, and `stage_03a` §5.2) |
| K grid | CIFAR-100 {10, 50, 99, 100, 128, 256}; Tiny ImageNet {20, 100, 199, 200, 256}; caps 99 and 199 |

Row-count arithmetic, checked rather than assumed: 4 δ × 6 K × 4 methods = 96 CIFAR cells minus the 24
where a classic arm has no basis beyond the cap, plus 1 no-projection row = **73 per pair**; the Tiny
grid gives 4 × 5 × 4 − 16 + 1 = **65 per pair**; 2 × 73 + 2 × 65 = 276. `selection.csv` is 4 methods ×
4 pairs = 16; `cv_summary.csv` is 4 methods × 4 pairs = 16, the eight Tiny ImageNet rows arriving with
invocation 3 (§2).

`realized_dim` is reported beside every selected `K` because they are not the same number: PCA-then-LDA
can be selected at K = 256 and still project to 99 coordinates, since its discriminant space cannot
exceed C − 1 whatever the PCA stage keeps. Where this report says "at dimension d", it means
`realized_dim`.

## 2. Cost, measured

**How to add these numbers up, because no single field on disk holds the total.** M2 produced results in
**three** invocations (plus one attempt that crashed before it wrote anything), and `timing.json` was
written by the schema each one used at the time:

| # | What it did | Wall clock | Where that number lives |
| --- | --- | --- | --- |
| attempt 1 (crashed) | all four δ of the hold-out sweep, died in the refit phase | ~1,570 s (26 min), **wasted**, wrote nothing but `calibration.json` | `runs/m2_run_stdout.txt` |
| invocation 1 | CIFAR-100, both backbones: sweep + refit + 5-fold CV | 4,923 s | `runs/m2_cifar_stdout.txt` (the file `timing.json` was overwritten by invocation 2, so this one survives only in the stdout) |
| invocation 2 | Tiny ImageNet, both backbones: sweep + refit, no CV | 4,748 s | `runs/m2_tiny_stdout.txt`, and `timing.json`'s `total_wall_clock_s` = 4,748.1 s (the only per-invocation total still in that file) |
| invocation 3 | Tiny ImageNet, both backbones: CV only, against the stored selection | **2,625.2 s = 43.8 min** | `manifest.json`'s `total_wall_clock_s_this_invocation`, cross-checked against `cv_summary.csv`'s `cv_phase_seconds` (1,788.4 + 837.2 = 2,625.6 ✓) |

So: **the two sweeps are 2.69 h** (9,671 s), **all productive compute including the CV is 3.42 h**
(12,296 s), and **counting the two wasted invocations it is 4.00 h** — 13,866 s with the crashed
attempt's ~1,570 s, and 14,400 s ≈ 4.00 h with the aborted duplicate CV invocation's ~530 s as well
(started 23:51:38, killed just after 00:00 — declared in A009's item 3; it truncated `runs/m2_tiny_cv_stdout.txt`,
which is why progress for that phase is judged from `progress.json` and the artefacts, not the stdout).
Both waste terms are compute spent and
thrown away, so the honest all-in figure against your 3–5 h budget is **4.0 h**, not 3.42 h. Reading only
`timing.json` would have said 4,748 s, and reading only the two sweep stdouts would have said 2.69 h with
the CV missing; both are per invocation, which is why this table exists. The
driver now keeps an `invocations_completed` ledger in `timing.json` so the next invocation appends its own
row rather than overwriting the last one (added after this report's first version, which is why the four
rows above had to be reconstructed from four different places).

The CV invocation cost what you predicted and not what I said: **43.8 min against the 45–50 min your
arithmetic gave**, and against the 1–1.5 h I quoted. Per fold it was 358 s on Tiny × ResNet-18
(1,788.4 / 5) and 167 s on Tiny × DINOv2 (837.2 / 5), i.e. the `--cv-only` route pays the solve cost once
per fold and δ-group rather than once per method.

The run was sized from `calibration.json` plus the crashed first attempt, and the prediction is worth
recording because it was wrong twice in the same direction — every extrapolation from unit costs has
come in over the actual time.

| Phase | CIFAR-100 × ResNet-18 | CIFAR-100 × DINOv2 | Tiny × ResNet-18 | Tiny × DINOv2 |
| --- | --- | --- | --- | --- |
| hold-out scan (4 δ) | 1,201 s | 507 s | 2,142 s | 1,423 s |
| refit + official-test scoring | 2 distinct selected δ | 2 | 2 | 2 |
| 5-fold CV | 2,003 s | 490 s | 1,788 s (invocation 3) | 837 s (invocation 3) |

The refit phase is cheaper than the plan assumed: after selection each pair needed only two distinct
δ, and the solves stop at the longest *selected* K rather than the longest grid point. That is most of
why the 2.69 h of sweeps came in under the 3.5–4.0 h predicted from unit costs, the rest being that CV
grouped by fold and δ needs one solve per fold, not one per method. Note what the two figures cover: the
3.5–4.0 h extrapolation was for the sweep phases, and CV came on top as a separate invocation (§1), so
the two are not the same quantity — the all-in compute is 4.00 h, which is inside the plan's 3–5 h and
outside the 3.5–4.0 h prediction once the waste is counted.

Unit costs the above rests on: one deflated GO-LDA direction costs ~1.05 s at M = 512 and 0.31 s at
M = 384, essentially independent of N (the pencil is M × M whatever the row count — Tiny measured
387 s at 95,000 rows against 462 s at 5,000), and one C4 head fit costs 23.7 s at CIFAR-100/512-d and
58.7 s at Tiny ImageNet/512-d. Two of the four fixes made after the first launch were cost fixes
(`fit_shared`, and CV grouped by fold and δ so one solve serves every method that selected that δ);
the third and fourth were correctness and durability — see `stage_03a` §10 for the crash itself.

## 3. Results

### 3.1 Official test split, each method at its own selected (δ, K)

**What each column is, because two different splits appear in this section and mixing them changes the
conclusion.** The four method columns are **official test** accuracies from `selection.csv`, each method
at the (δ, K) it selected on the hold-out; "best baseline" below means the best of the three LDA
baselines **on the test split**. The `no projection` column is a **hold-out** value — it is stored only
in `accuracy_rows.csv`, never in `selection.csv` — so compare it with §3.3, not with the columns to its
left. §3.3 is entirely hold-out, with δ pinned to GO-LDA's own choice.

| Pair | GO-LDA | classic-ridge | classic-shrinkage | PCA-then-LDA | no projection |
| --- | --- | --- | --- | --- | --- |
| CIFAR-100 × ResNet-18 | **0.6478** (δ 5e-3, K 256) | 0.6699 (1e-4, 99) | 0.6708 (1e-4, 99) | 0.6688 (1e-4, 256→99) | 0.6308 |
| CIFAR-100 × DINOv2 | **0.8098** (5e-3, 128) | 0.8244 (5e-3, 99) | 0.8240 (1e-4, 99) | 0.8195 (1e-4, 256→99) | 0.8088 |
| Tiny ImageNet × ResNet-18 | **0.6333** (1e-2, 256) | 0.6439 (1e-2, 199) | 0.6498 (1e-4, 199) | 0.6520 (1e-4, 256→199) | 0.5938 |
| Tiny ImageNet × DINOv2 | **0.7948** (5e-3, 200) | 0.7930 (1e-4, 199) | 0.7950 (1e-4, 100) | 0.7962 (1e-4, 100) | 0.7844 |

GO-LDA is last among the four projection methods on three pairs, and third of four on the fourth
(Tiny × DINOv2, where it does beat classic-ridge by 0.2 points but stays behind shrinkage and
PCA-then-LDA). Deficits against the best baseline: −2.3, −1.5, −1.9, −0.1 points — and that last one is a
0.7-point five-fold loss against PCA-then-LDA seen next to a near-tie against ridge, which is why §3.2 and
not this table carries the wording for Tiny × DINOv2. The no-projection
column is a **hold-out** number, not a test number: it is stored only in `accuracy_rows.csv`, which is
also where its CIFAR-100 × DINOv2 and Tiny values come from, so it can be compared with the §3.3 table
but not read against the test columns beside it. Where both exist on the same footing, projection does
pay: CIFAR-100 × ResNet-18 test 0.6282 unprojected (`probe_head_control.json`) against 0.6478 for
GO-LDA @ 256 and 0.6699 for classic @ 99.

### 3.2 Fold-to-fold spread, all four pairs, 5 folds on the selected configuration

Each pair's four methods are scored on the same five folds at the (δ, K) each one selected on the
hold-out; CIFAR-100's rows came from the sweep, Tiny ImageNet's from invocation 3 (§2).

| Pair | GO-LDA | classic-ridge | classic-shrinkage | PCA-then-LDA |
| --- | --- | --- | --- | --- |
| CIFAR-100 × ResNet-18 | 0.6385 ± 0.0046 | 0.6636 ± 0.0056 | **0.6671 ± 0.0042** | 0.6605 ± 0.0039 |
| CIFAR-100 × DINOv2 | 0.7996 ± 0.0063 | **0.8113 ± 0.0061** | 0.8118 ± 0.0065 | 0.8095 ± 0.0068 |
| Tiny × ResNet-18 | 0.6131 ± 0.0023 | 0.6275 ± 0.0025 | **0.6323 ± 0.0024** | 0.6317 ± 0.0021 |
| Tiny × DINOv2 | 0.7883 ± 0.0016 | 0.7882 ± 0.0013 | 0.7929 ± 0.0013 | **0.7953 ± 0.0007** |

**What the fold ranges separate.** The strongest statement the stored summary allows is whether one
method's best fold reaches another's worst:

| Pair | GO's range | ridge | shrinkage | PCA-then-LDA | separated from all three? |
| --- | --- | --- | --- | --- | --- |
| CIFAR-100 × ResNet-18 | 0.6326–0.6445 | 0.6588–0.6733 | 0.6609–0.6726 | 0.6566–0.6655 | **yes** |
| Tiny × ResNet-18 | 0.6114–0.6171 | 0.6239–0.6308 | 0.6291–0.6352 | 0.6288–0.6341 | **yes** |
| CIFAR-100 × DINOv2 | 0.7944–0.8100 | 0.8042–0.8200 | 0.8045–0.8219 | 0.8035–0.8205 | no — GO's best fold (0.8100) is above ridge's worst (0.8042) |
| Tiny × DINOv2 | 0.7869–0.7902 | 0.7865–0.7901 | 0.7920–0.7949 | 0.7944–0.7961 | no — but see below |

So the disjoint-range claim is a **ResNet-18** claim, on both datasets. The DINOv2 rows deserve the more
careful reading, and Tiny × DINOv2 is the pair you flagged as the one where the ± is the only evidence:

* against **classic-ridge LDA** the **five-fold ranges overlap almost entirely**: means 0.7883 against
  0.7882, ranges 0.7869–0.7902 against 0.7865–0.7901, the two differing only at their ends, on the pair
  whose fold spread is the narrowest in the matrix (SD 0.0013–0.0016). No stronger word is available:
  `cv_summary.csv` stores mean / SD / min / max per cell and five folds do not license a test either way,
  so this is a statement about overlap and not a statistical claim.
* against **PCA-then-LDA**, the best baseline on that pair, the ranges **are** disjoint: GO's best fold
  0.7902 against PCA's worst 0.7944, a mean gap of 0.70 points. So the −0.1-point near-tie in §3.1's
  single-split test numbers is not noise — but the single split understates the gap five-fold, which is
  the reason to quote the CV spread next to it rather than instead of it.
* against shrinkage (0.7929) the gap is 0.46 points and the ranges are disjoint as well.

The wording this pair gets is fixed, because both readings are true at once and only one of them is about
the best baseline: **the close one is only one of the three baselines.** Verbatim, as ruled: *"The
single-split test gap of −0.1 points is against PCA-then-LDA and understates the five-fold 0.70-point gap;
GO-LDA only ties ridge on the CV (0.7883 vs 0.7882) and is +0.2 against ridge on the test."* So the report
does not say this pair is indistinguishable from the baselines, and it does not say the fourth pair
reproduces H1 either — the fourth pair's near-tie is against ridge on two of the three splits, and it is a
0.7-point loss against the baseline that wins there.

Two properties of the numbers themselves are worth recording before anyone over-reads them.
`cv_summary.csv` stores mean, SD, min and max over folds, **not** the per-fold values, so no sign-per-fold
claim is available anywhere in this report; and five folds make the ± a rough scale estimate, not a test —
the gaps above are reported as range separations, which is what a 5-fold summary can actually support.

### 3.3 The paired reading — **hold-out** split, all methods at GO-LDA's own δ

Per-method selection is what the brief's protocol asks for, but it invites the question "did GO-LDA
lose because it picked a bad δ?". It did not. Holding δ at the value GO-LDA itself selected, on the
same hold-out split, same seed, same head — `accuracy_rows.csv` filtered to one δ:

CIFAR-100 × ResNet-18, δ = 5e-3:

| K | GO-LDA | classic-ridge | classic-shrinkage | PCA-then-LDA |
| --- | --- | --- | --- | --- |
| 10 | 0.2568 | 0.3512 | 0.3688 | 0.3372 |
| 50 | 0.5148 | 0.6236 | 0.6340 | 0.6080 |
| 99 (= cap) | 0.5976 | **0.6624** | 0.6632 | 0.6512 |
| 100 | 0.5952 | — | — | 0.6484 |
| 128 | 0.6236 | — | — | 0.6524 |
| 256 | 0.6468 | — | — | **0.6684** |

The same paired reading summarised for all four pairs (CIFAR-100 × ResNet-18 is the grid above). All
columns are **hold-out** cells at **GO-LDA's own δ**, so the baseline column is strictly paired, and the
two right-hand pairs of columns distinguish the K a method *selects* from the K the grid *ends* at:

| Pair | δ | GO at cap | best baseline at cap, same δ | GO at selected K | gain cap → selected | GO at grid-end K | gain cap → grid end |
| --- | --- | --- | --- | --- | --- | --- | --- |
| CIFAR-100 × ResNet-18 | 5e-3 | 0.5976 | 0.6632 (shrinkage) | 0.6468 (K 256) | **+0.0492** | 0.6468 (K 256) | +0.0492 |
| CIFAR-100 × DINOv2 | 5e-3 | 0.8080 | 0.8260 (ridge) | 0.8184 (K 128) | +0.0104 | 0.8164 (K 256) | +0.0084 |
| Tiny × ResNet-18 | 1e-2 | 0.6268 | 0.6480 (shrinkage) | 0.6330 (K 256) | +0.0062 | 0.6330 (K 256) | +0.0062 |
| Tiny × DINOv2 | 5e-3 | 0.7970 | 0.7984 (PCA-then-LDA) | 0.7988 (K 200) | +0.0018 | 0.7930 (K 256) | −0.0040 |

Two corrections this table carries from the first version, both of the kind you asked to be labelled:
the "best baseline at cap" cell for Tiny × DINOv2 read 0.8012, which is PCA-then-LDA's **K = 100** cell —
one row *below* the cap, not at it; the same-δ value at K = 199 is 0.7984. And the column headed "GO at
max K" was really "GO at its **selected** K": on both DINOv2 pairs the selected K is short of the grid end
(128 and 200 against 256), and the curve is *lower* at 256 than at the selected point, so "the curve keeps
rising" is true only over the segment the protocol actually uses — which is a point about selection, not
about the algorithm.

## 4. Which hypotheses survived

**H1 — indistinguishable on the paper's face-data rows.** H1 is drawn from the paper's face-data rows
and says GO-LDA and classic LDA are statistically indistinguishable *there*, at K = C − 1;
`stage_03a` §4 confirmed it (per-fold difference exactly 0 in 10/10 folds, spans to ~2e-6°). The
wording is deliberately narrower than "the two algorithms agree". §7 records why: the source's own claim
at Ω_{C−1} is *superiority*, and eq. (37)'s constraint is ordinary Euclidean orthogonality, so span
agreement was never a theorem — what we measured on ORL is a property of that dataset and regime. H1
therefore makes no claim about frozen features, which are reported separately and as post-hoc below.

*Post-hoc, and labelled as such.* On frozen features the same comparison inverts by **−6.5 points** at
the cap on CIFAR-100 × ResNet-18: GO@99 0.6045 against classic-LDA@99 0.6699, both on the **official
test** split, fitted on all of train, δ = 5e-3 for both arms (`runs/m2_matrix/probe_head_control.json`,
cross-checked against `probe_cap_gap.json`). This is not a refutation of H1 — H1's scope was the paper's
face-data rows and it holds there — and it is not a prediction that was stated in advance for this
regime. It is reported as a post-hoc observation, not as a new pre-registered hypothesis, because the
comparison was only designed after the numbers were on the table. §5 and §7 explain the geometry, and §7
records that the paper's own claim at Ω_{C−1} is *superiority*, not parity, so nothing in the source is
contradicted by what we measured.

**H2 — mechanism confirmed on every pair; the accuracy claim does not replicate here.** GO-LDA's own
curve rises past C − 1 on all four pairs, over the segment from the cap to the K each method selects
(+4.9, +1.0, +0.6, +0.2 points at δ = 5e-3, 5e-3, 1e-2, 5e-3). It is not monotone to the end of the grid:
on both DINOv2 pairs the curve is lower at K = 256 than at the selected point (0.8184 → 0.8164 on CIFAR-100,
0.7988 → 0.7930 on Tiny ImageNet, §3.3), so what reproduces is the paper's mechanism — the rank cap is not
an information limit, and a sequential construction does extract something from beyond it — rather than an
unbounded improvement. What does not replicate is the conclusion the paper draws from that. On these data the extra directions close part of a gap the
baseline never had to open, and even the largest gain (CIFAR-100 × ResNet-18, K = 256 against classic
at 99, both at GO-LDA's own δ) lands **1.6 points short on the hold-out** (§3.3: 0.6468 against ridge-classic's
0.6624 at the cap, and against shrinkage-LDA's 0.6632 it is 1.64 short, so the size of the shortfall
depends on which baseline is the reference)
— the same pair on the **official test** split, each method at its own selection, is **2.3 points** short
(§3.1: 0.6478 against the best baseline's 0.6708). The two numbers are not alternatives for one slot;
they are measured on different splits and both are quoted, per your U009 correction.

**Which endpoint reaches the cap line, stated per split and per δ convention.** The claim has to be
qualified twice, because a first version of it was too strong:

* on the **hold-out** split, GO-LDA at its selected `K` is short of the best baseline's cap value on all
  four pairs by −1.64 / −0.76 / −1.50 / **−0.06** points (CIFAR × ResNet-18, CIFAR × DINOv2, Tiny × ResNet-18,
  Tiny × DINOv2, each baseline read at its own δ);
* with the cap line re-drawn at **GO-LDA's own δ** (§3.3, the paired reading), Tiny × DINOv2 is the one
  pair that crosses it: 0.7988 at `K` = 200 against 0.7984 at `K` = 199, **+0.04 points**. The other three
  stay short on that reading too (−1.64, −0.76, −1.50), because for them the two δ conventions give the same
  cap value;
* at the **end of the `K` grid** (`K` = 256) all four pairs are short on both readings, and on the
  **official test** split and in the **five-fold CV** all four are short with no exception.

So the honest sentence is not "the curve never reaches the cap line" and not "it reaches it on one pair":
it is that the endpoint crosses the line only once, only on the hold-out, only by 0.04 points, and only
under the δ convention that pins the baselines to GO-LDA's ridge. The paper's beyond-cap evidence is from problems whose caps are 3–4
directions inside a 512-dimensional space (BrainTumor C = 4, DeepDrid C = 5, quoted verbatim in
`research_records/sources/golda_arXiv2305.14568_notes.md` §4); our caps are 99 and 199 inside 512 and
384. Our regime is outside its evidence, and this report says so rather than claiming a refutation of
its own numbers.

**H3 — confirmed, and it is the cleanest result in the project.** `diagnostics.json` records the
largest off-diagonal |uᵢᵀu_j| for each arm at the selected δ:

| Pair | GO-LDA | classic-ridge | classic-shrinkage |
| --- | --- | --- | --- |
| CIFAR-100 × ResNet-18 | 2.99e-14 | 2.04e-01 | 2.04e-01 |
| CIFAR-100 × DINOv2 | 1.02e-07 | 2.39e-01 | 1.97e-01 |
| Tiny × ResNet-18 | 1.25e-14 | 1.86e-01 | 1.75e-01 |
| Tiny × DINOv2 | 2.83e-08 | 2.52e-01 | 1.79e-01 |

Classic LDA's directions are not orthogonal — never have been, at any scale — and GO-LDA's are, by
construction. The residual certification travels with it: every direction satisfies the full-space
deflated pencil to a relative residual inside the `10 · eps · κ` bound derived from that pencil (worst
1.66e-09 against a tolerance of 1.04e-06; κ spans 3.8e2 to 4.7e8), Fisher ratios are monotone in all
four pairs, and the beyond-cap eigenvalues stay positive and decreasing (e.g. CIFAR-100 × ResNet-18:
μ₉₉ = 0.4573, then 0.4463, 0.4410, 0.4384). The method does what the paper says it does. It just does
not win.

## 5. Why the gap opens at direction 3

The `span_at_cap_deg` field in `diagnostics.json` reads 89–90° for all four pairs. One number at 90°
is easy to misread in either direction, so `src/probe_m2_cap_gap.py` took the whole principal-angle
spectrum on CIFAR-100 × ResNet-18 (δ = 5e-3, fit on all of train, `probe_cap_gap.json`):

| GO's first m vs classic's first m | max angle | median angle | μ_GO at m | μ_classic at m |
| --- | --- | --- | --- | --- |
| m = 1 | 0.0000° | 0.0000° | 3.42944 | 3.42944 |
| m = 2 | 0.1171° | 0.0586° | 3.23310 | 3.23309 |
| m = 3 | 61.2850° | 0.0597° | 2.77938 | 2.60270 |
| m = 10 | 89.2413° | 75.1733° | 2.01147 | 1.13240 |
| m = 99 | 89.8438° | 55.9378° | 0.45729 | 0.02257 |

Read with eq. (23) of the paper — *u₁ = v₁*, the first direction is shared — this is a coherent
picture: direction 1 agrees exactly (|cos| = 1.000000), direction 2 still nearly so, and from
direction 3 the two constructions are doing different things. From there the μ columns carry the
story. GO-LDA's third direction has a *larger* Fisher ratio than classic's third eigenvector
(2.779 against 2.603), and the sum over the first 99 is 103.99 against classic's 45.63. Every GO
direction really is individually more discriminative, exactly as Theorem V.2 promises — and the
subspace they build together classifies worse under both heads (§6). Individually optimal directions
do not add up to an optimal subspace, which is the most interesting thing this project found and
the one the report should lead its "what we learnt" section with.

Three alternative explanations were tested and rejected, all in `probe_cap_gap.json`:

| Candidate | Control | Result |
| --- | --- | --- |
| The classic arm's solver is wrong (`eig` on a symmetric-definite pencil) | solve the same pencil with `scipy.linalg.eigh`, the right tool for it | eigenvalues agree to 1.24e-14, subspaces to 1.91e-06° |
| M2 measured a route artefact (dense vs span-reduced) | solve GO-LDA both routes on the same data and δ | μ agree to 1.07e-14, spans to 2.09e-06°, both score 0.6045 |
| The head prefers one coordinate system (classic's basis is non-orthogonal, GO's is orthonormal) | QR-orthonormalise every basis and re-score | gap moves from −0.0654 to −0.0649; GO 0.6045 → 0.6045, classic 0.6699 → 0.6694 |

One number in that table deserves a caveat so nobody misreads it the way I nearly did: the route
control's element-wise `max_abs_U_diff` is 0.859, which looks like disagreement. It is a sign
convention per column — eigenvectors are defined up to ±1 — and the metrics that are invariant to it
(μ agreement, principal angles, accuracy) all say the two routes agree.

## 6. The classifier is not the explanation either

Table II of the paper uses 1-NN; this project was told to use C4's L2 logistic head for the
feature regime (supervisor's ruling U007). `src/probe_m2_head.py` scores *the same bases* under three
heads on CIFAR-100 × ResNet-18, fitted on all of train and evaluated on the official test split:

| Arm | dim | C4 logistic | 1-NN, raw coordinates | 1-NN, standardised |
| --- | --- | --- | --- | --- |
| no projection | 512 | 0.6282 | 0.5542 | 0.5577 |
| GO-LDA @ 50 | 50 | 0.5184 | 0.3660 | 0.3714 |
| GO-LDA @ 99 | 99 | 0.6045 | 0.4603 | 0.4655 |
| GO-LDA @ 256 | 256 | 0.6478 | 0.5355 | 0.5358 |
| classic-LDA @ 99 | 99 | **0.6699** | **0.5707** | 0.5403 |
| PCA @ 99 | 99 | 0.6508 | 0.5407 | 0.5077 |
| PCA @ 256 | 256 | 0.6481 | 0.5550 | 0.4395 |

GO-LDA minus classic-LDA at the cap is **−6.5 points with the logistic head, −11.0 with 1-NN on the
coordinates as they come out of the basis, −7.5 with 1-NN after standardisation.** The deficit is
larger under the paper's own classifier, not smaller, so the negative result is not a protocol
artefact. GO's beyond-cap growth is also larger under 1-NN (+7.5 points from K = 99 to 256 against
+4.3 under the logistic head) — same shape, different scale.

Two secondary readings from the same table, both worth a sentence in the report. First, in this
regime *projection is mostly a loss under 1-NN*: the unprojected 512-dimensional features beat every
99-dimensional projection except classic LDA's, which is a different balance from raw-pixel ORL, where
projection is what makes 1-NN work at all. Second, 1-NN's verdict depends on whether the projected
coordinates are standardised first (PCA @ 256 falls from 0.5550 to 0.4395 when they are), which is a
protocol choice the paper does not state — we report both rather than pick the flattering one.

## 7. Fidelity of the implementation to the source, and one correction to our own framing

The paper had been read in conversation but never archived, so on 2026-11-17 it was fetched again and
the passages the implementation and the hypotheses rest on were transcribed verbatim into
`research_records/sources/golda_arXiv2305.14568_notes.md` (arXiv:2305.14568v1, HTML rendering, with
fetch timestamp).

- The recursion in `src/golda.py:go_lda` builds `Mleft = B_r − U (Uᵀ A⁻¹ U)⁻¹ Uᵀ A⁻¹ B_r`, which is
  eq. (38) with (39)–(41) transcribed exactly, against the ridged `S_W' = S_W + δI` of eq. (15) — and
  the paper's own suggested δ is 5e-3, which is the second point of our grid. The implementation was
  not misread.
- The constraint in eq. (37) is **ordinary Euclidean orthogonality** (`u ⟂ u_i`; the Lagrangian in
  eq. (42) uses `β_i uᵀu_i`, not `uᵀ S_W u_i`). So the two methods construct different objects and
  **no parity at K = C − 1 is stated or proved anywhere in the source**; what Sec. VI-B claims at
  Ω_{C−1} is that "GO-LDA outperforms the classic-LDA". Our H1 wording survives only because it was
  written as a claim about ORL's published row, but the looser "parity" phrasing used in speech and in
  `stage_03a` §4 was ours. Corrected in `stage_03a` §4 and `stage_02` §4.
- Consequence for the verification suite, and the one thing from this stage that changes how the
  project is checked: gate check 1e used to require GO-LDA's first C − 1 directions and classic LDA's
  to span the same subspace on ORL fold 0. That assertion passed — but it passed on a coincidence of
  the small-sample regime, and the moment it ran on the feature data it would have failed a *correct*
  implementation. `tests/test_parity.py` now gates only on what is implied (the two solvers of the
  same pencil agreeing, `a_ce < tol` where `tol` comes from that pencil's spectral gap) and the
  GO-vs-classic span comparison is reported as diagnostic **5f**. Same measurements, different status:
  **11/11 gated, 18/18 reported, `GATE OPEN`**. The gate citation for this record is the final log,
  `runs/parity/parity_after_readpgm_stdout.txt` (2026-11-18 23:15, 121 s, same counts, and its M0 line
  prints the corrected geometry); `runs/parity/parity_rerun_stdout.txt` (2026-11-18 03:41, 89 s) is the
  equivalent run before the loader assertion. The 2026-11-17 09:29 log that this sentence originally cited
  is **pre-geometry-fix** and is not cited — see `runs/parity/README.md` for the status of every parity log.
- Narrowing 1e immediately produced a second lesson, in the other direction. The first version of the
  narrowed check also required `eig` and `eigh` to agree on *eigenvalues* to a relative 1e-8 — a
  threshold written down rather than derived. The two solvers differ by 3.2e-7 on this pencil, because
  `S_W` is near-singular at δ = 5e-3, and the gate closed on a correct implementation of its own new
  criterion. The condition is gone; the agreement is still printed in the check's detail. And because
  1e's angle (1.708e-06°) collided to four digits with one reported by check 5e on an unrelated
  fixture, it was recomputed standalone from freshly built arms — same value, so no stale state in the
  suite, and the collision is what you get when two `eig`-versus-`eigh` comparisons land in the same
  1e-6° band.

## 8. Deviations and protocol choices, M2

| Deviation / choice | Reason, and what it costs |
| --- | --- |
| Tiny ImageNet's fold-to-fold ± arrived in a separate invocation, not with the sweep | The first pass ran Tiny with `--cv 0` because a cost estimate put its CV past the 3–5 h ceiling. That estimate was wrong and you corrected it in U009; the measurement came in at your number: invocation 3 cost **2,625.2 s = 43.8 min** (358 s per fold on Tiny × ResNet-18, 167 s on Tiny × DINOv2), against the 1–1.5 h I quoted and the 45–50 min you derived. It used `--cv-only`, which re-reads the stored selection instead of re-paying the sweep, and its write set was restricted to `cv_summary.csv` (§2). All four pairs now carry a ± ; nothing about the sweep tables changed, which is the check that the guard works. |
| The fold-range separation is a backbone-dependent claim | §3.2 states it pair by pair: GO-LDA's range is disjoint from all three baselines on the two ResNet-18 pairs, and overlaps **classic-ridge's** on both DINOv2 pairs — on Tiny × DINOv2 its five-fold range overlaps ridge's almost entirely (0.7883 against 0.7882), 1.17 points below it on CIFAR × DINOv2. Against the *best* baseline on Tiny × DINOv2 the ranges are disjoint (0.7902 against PCA-then-LDA's worst fold 0.7944). The earlier draft's "~5σ separation on CIFAR-100" was a ResNet-18 statement wearing a dataset name; corrected per your U009 correction 2. |
| Each method selects its own (δ, K) on the hold-out | C4's protocol, and the plan's. It is also the most favourable reading available to GO-LDA, which is why §3.3 repeats the comparison with δ pinned to GO-LDA's own choice. |
| Only certified δ (≥ 1e-4) in the grid | Supervisor's ruling U008, resting on `stage_03a` §5.2: below that the beyond-cap directions are not trustworthy on real data. |
| 1-NN in the head control uses exact brute-force search (`sklearn`), not `baselines.knn_predict` | The latter forms the full pairwise difference tensor, which is fine at ORL's 360 reference rows and needs 0.8 GB per block at 50,000. Same distances, same answers; the ORL main table is untouched. |
| Dense route for both datasets | At M = 512/384 with N ≫ M the dense pencil is both the cheap and the exact option; the span-reduced route exists for ORL's 10,304 dimensions. §5 shows the two agree to 2e-6° on this data, so nothing in the table depends on the choice. |
| DINOv2 at 224 × 224 | Measured 386.6 against 48.5 img/s at the 518 timm registers for this checkpoint; declared in `stage_02` §7 and `stage_03a` §10. |
| Selection scored on a 5 % hold-out rather than a fold-structured inner CV | Cheaper by design (the refit and CV phases are what the budget cannot cover twice), and the official test split is never used to choose. Costs a noisier selection: 2,500 CIFAR validation rows put ~±1 point on any single cell. |
| **The out-of-distribution control the plan promised has now been run** (U010, option A) | `src/probe_m2_ood.py` → `runs/m2_matrix/probe_ood.json`. CIFAR-100's official 10,000 test images get **one** corruption at **one** severity — additive white Gaussian noise, σ = 0.08 on the [0, 1] pixel scale, which is severity 1 of ImageNet-C's gaussian family (Hendrycks & Dietterich 2019, arXiv:1903.12261; its `corruptions.py` uses c = [.08, .12, .18, .26, .38] on images divided by 255, the same arithmetic). One noise field is drawn from seed 20261117 and applied before the backbone's resize/ToTensor/Normalize, so both backbones see identical pixels; features are re-extracted through the same frozen models; projections, scalers and heads come from **clean** train at each method's own selected (δ, K) and nothing is refitted on the shift. Severity was fixed before any arm was scored and was not swept. **Measured cost: 915 s = 15.3 min, not the ~3 min I estimated** — the estimate assumed the fitted projections could be reused, and M2 stored accuracies rather than bases, so both pairs' pencils had to be re-solved (266 + 241 s at ResNet-18/512, 91 + 49 s at DINOv2/384) on top of 19 + 43 s of extraction. The gate worked as designed: every arm's clean column reproduces §3.1 (8/8, max drift 0.0000), which is what licenses reading the corrupted column as a shift rather than as a second pipeline. Result below. |
| The ORL dimension ladder was added outside the plan, on your release (U010 item 2) — **and its first reading was wrong** | `src/probe_orl512.py` → `runs/orl512_fix/orl512_ladder.json`, **392 s = 6.5 min** against your ten-minute ceiling, no new downloads. It holds `C = 40` and nine rows per class fixed while box-averaging the pixels to M = 80/156/256/512, so cap/M sweeps 48.8 % → 7.6 %. The paired GO-minus-classic gap at the cap is **−0.50 / 0.00 / +3.00 / 0.00** points: no trend with cap/M, and the largest rung difference favours GO-LDA. The cap-rank span still goes from ~89° to the numerical floor at M = 512 (2e-6°, defect 4.2e-16, control pair 62°), so the parity result is unchanged. `wp7_cross_regime_synthesis.md` §6 carries the table, the reason the first run reversed, and the collinearity that remains (cap/M against M/N, now moot because there is no effect to attribute). |
| **Correction, found while building the front end on 2026-11-18** | `src/orl.py` declared `IMG_H, IMG_W = 92, 112`, but a PGM header writes width before height, so the ORL images are 112 rows of 92 pixels. The flattened vectors were always correct — the loader reshaped with the parsed header, not with the constants — so every accuracy in this record, the MVP, M2, the parity suite and the OOD control are unaffected. Two consumers did read the constants: the ladder's box-average, which is why its first run (`runs/orl512/`, 427 s) reported a −11.75 / −8.25 / −0.50 / 0.00 reversal that was a property of the sheared raster, and the demo's direction/specimen pictures, which rendered as stripes. The constants are fixed, the ladder re-released above, the withdrawn run kept on disk for provenance, and the front end rebuilt from the corrected geometry. |

### 8.1 What the control found (`runs/m2_matrix/probe_ood.json`)

Both columns are the **official CIFAR-100 test split**, 10,000 rows, chance 1 %. The left column is §3.1's
number reproduced by this script, the right column is the same fitted projection and head applied to
noisy pixels.

| Backbone | arm | δ / K | clean | corrupted | change |
| --- | --- | --- | --- | --- | --- |
| ResNet-18 | classic-shrinkage-LDA | 1e-4 / 99 | 0.6708 | 0.1521 | −51.87 pt |
| ResNet-18 | classic-ridge-LDA | 1e-4 / 99 | 0.6699 | 0.1550 | −51.49 pt |
| ResNet-18 | PCA-then-LDA | 1e-4 / 256→99 | 0.6688 | 0.1522 | −51.66 pt |
| ResNet-18 | **GO-LDA** | 5e-3 / 256 | 0.6478 | **0.1499** | −49.79 pt |
| ResNet-18 | no projection | — | 0.6282 | 0.1239 | −50.43 pt |
| DINOv2 | classic-ridge-LDA | 5e-3 / 99 | 0.8244 | 0.4401 | −38.43 pt |
| DINOv2 | classic-shrinkage-LDA | 1e-4 / 99 | 0.8240 | 0.4453 | −37.87 pt |
| DINOv2 | PCA-then-LDA | 1e-4 / 256→99 | 0.8195 | 0.4448 | −37.47 pt |
| DINOv2 | **GO-LDA** | 5e-3 / 128 | 0.8098 | **0.4194** | −39.04 pt |
| DINOv2 | no projection | — | 0.8074 | 0.3973 | −41.01 pt |

Four readings, in the order the evidence supports them:

1. **GO-LDA is last on both backbones after the shift.** That is what the plan wanted the control for: the
   conclusion is not an artefact of the two clean pairs we happened to pick. Mean absolute feature shift
   0.535 (ResNet-18/512) and 1.777 (DINOv2/384), so both backbones really did see different data.
2. **The ordering *among the three baselines* is not stable.** ResNet-18 goes shrinkage > ridge > PCA to
   ridge > PCA > shrinkage, and DINOv2 goes ridge > shrinkage > PCA to shrinkage > PCA > ridge, so
   `ranking_preserved` is **false** overall and the report does not claim that the four-way order survived.
   What survived is the one comparison the study is about.
3. **The size of GO-LDA's deficit moves in opposite directions on the two backbones:** −2.30 → −0.51 points
   on ResNet-18 and −1.46 → −2.59 points on DINOv2. Under a shift this severe the arms compress toward a
   common failure on ResNet-18 and stay separated on DINOv2, so no claim of the form "δ points more robust"
   is available from one severity.
4. **Most of the fall is the corruption, not the projection**: with no projection at all, accuracy falls
   from 0.6282 to 0.1239 and from 0.8074 to 0.3973. Every projected arm ends above that, clean or shifted.

What the control deliberately does not do: sweep severities. One level was fixed before scoring, a null
would have been reported as a null, and a separation manufactured by trying σ until the arms split would
not have been evidence of anything.

## 9. External plausibility, not a target

C4's published cells are a second pair of eyes on the *feature extraction and head*, not on GO-LDA.
Ours are single-seed (20261117) where C4 reports 5-seed means, and their ResNet-18/DINOv2 pipelines
are their own, so order of magnitude is the honest comparison (`stage_01_candidate_scoring.md` §3 for
the full README-versus-paper diff that these numbers come from):

| Cell | C4 published | ours, same features |
| --- | --- | --- |
| CIFAR-100 × ResNet-18, PCA row | 65.07 (README and paper agree) | PCA-then-LDA 66.88 (test), no-projection 63.08 (hold-out) |
| CIFAR-100 × DINOv2 ViT-S/14, PCA row | 81.55 README / 80.60 paper | 81.95 (test), no-projection 80.88 (hold-out) |
| Tiny ImageNet × ResNet-18, PCA row | 64.32 README / 64.50 paper | 65.20 (test), no-projection 59.38 (hold-out) |
| Tiny ImageNet × DINOv2, PCA row | 79.83 (agreeing cell) | 79.62 (test), no-projection 78.44 (hold-out) |

The split is marked because the two are not interchangeable at this precision: the no-projection arm was
only ever scored on the hold-out (`selection.csv` has no row for it, since it has nothing to select).

Every projected cell lands within ~1.5 points of the published one except Tiny × ResNet-18 without
projection, which is 5 points low — consistent with their pipeline using a differently-trained ResNet-18,
and not a flag about ours, since the *projected* cell for the same pair agrees to 0.7 points.

## 10. Rulings received, and what this stage still asks

Three questions went up with the first draft — whether Tiny ImageNet's CV was worth its compute, how H1
should read once the feature regime reverses, and what the front end has to show. U009 settled all three;
U010 then accepted this report and the M3 work, ruled on the three items this section used to ask about,
and sent five text corrections. They are recorded below as decisions rather than open asks.

### 10.1 Settled by U009

1. **Tiny ImageNet's CV — run it, and it landed at your number.** Your correction (CIFAR-100's CV measured
   2,003 + 490 s = 41.5 min, Tiny's sweep 3,565 s, so the missing phase was ~45–50 min rather than the
   1–1.5 h I quoted) was right and the measured cost is **2,625.2 s = 43.8 min** (§1, §2, §8). It ran in the
   background and did not block M3. All four pairs now carry a fold spread, and §3.2 states which pairs'
   ranges separate.
2. **H1's wording — restated, no H1′.** §4 now reads "indistinguishable on the paper's face-data rows", and
   the feature-regime reversal is a separate paragraph explicitly labelled post-hoc, quoting the −6.5-point
   cap difference on the official test split from the probes. It is deliberately not called a pre-registered
   hypothesis.
3. **Front end — the growth curve is in, with the data source you specified.** Curves come from
   `accuracy_rows.csv`: GO-LDA's accuracy against K over the **full grid at its selected δ**, for all four
   pairs, on the **hold-out** split; single markers come from `selection.csv`, being each method's
   **test** accuracy at its own selection. §3.3's summary rows are a condensation of the same cells and
   are not what the chart is drawn from. The three baselines are horizontal lines at their **cap** values,
   and the legend separates hold-out curves from test points. The contract is written into `stage_02` §4
   ("Front-end data contract") with §3's WP8 row pointing at it, and `src/export_results.py` emits exactly
   those fields into `webapp/data.js`, including both δ readings of the cap line so the chart cannot
   silently mix them.
4. **Framing of the cap result — received, though not one of the three.** "Individually optimal directions,
   worse subspace" was a proposal of mine that you agreed with in passing, so it is listed here rather than
   counted as a ruling: each of GO-LDA's directions really does carry a larger Fisher ratio (μ summed over
   the first 99: 104.0 against classic's 45.6, §5), and the subspace they span classifies worse than classic
   LDA's at the same rank (§3.3, §6). The report does not say the paper is wrong. The scope argument travels
   with it: the paper's 512-dimensional evidence is BrainTumor (C = 4) and DeepDrid (C = 5) only, so
   C = 100 and C = 200 against 512/384 dimensions are outside its evidence, not inside its predictions.

### 10.2 Settled by U010

5. **The §3.2 wording, with the statistical claim downgraded.** You accepted the sentence but replaced
   "statistically indistinguishable" with **"five-fold ranges overlap almost entirely"**, because
   `cv_summary.csv` stores only mean / SD / min / max and five folds cannot support a test either way, and
   you required this addition verbatim: "The single-split test gap of −0.1 points is against PCA-then-LDA
   and understates the five-fold 0.70-point gap; GO-LDA only ties ridge on the CV (0.7883 vs 0.7882) and is
   +0.2 against ridge on the test." §3.2 carries both, §3.1 points at §3.2 for the per-baseline breakdown,
   "the close one is only one of the three baselines" is kept, and nowhere does the report call the fourth
   pair indistinguishable.
6. **Out-of-distribution control — option A.** One fixed corruption at one fixed severity on the CIFAR-100
   test images, features re-extracted through the same frozen backbones, projections and heads scored as
   fitted on clean train. B was rejected because it yields no accuracy statement, C because §5's
   anti-over-generalisation sentence stays. Result in §8's OOD row and WP7 §7; the ORL M ≈ 512 control
   approved with it is in WP7 §6.
7. **Five text corrections, applied.** (i) §4's H2 line no longer claims the endpoint never reaches the
   baselines' cap value — on hold-out it *exceeds* it on Tiny × DINOv2 by 0.04 points (selected K = 200
   0.7988 against PCA-then-LDA at K = 199 0.7984); the other three pairs fall short there, and the grid-end
   K = 256 and all four test and CV readings fall short. WP7 §3 carries the same correction. (ii) WP7 §5's
   "rank is the same on every pair" is now "below the best baseline on every pair, fourth on three and
   third on Tiny × DINOv2". (iii) WP7's count is stated as five explanations plus the sample/fold control —
   six controls, matching its table. (iv) the cost total is the all-in **4.00 h** (3.42 h productive +
   ~26 min crashed + ~9 min aborted duplicate), and §1/§2/§3.2/§8 use one numbering scheme: the two sweeps
   are invocations 1–2, the CV-only run is invocation 3, and the crashed and aborted processes are named as
   waste rather than numbered. (v) this section's opening attributes the three questions as above.

### 10.3 What this stage still asks

Nothing blocks Stage 4. The remaining work is the front end itself (`webapp/index.html` over `data.js`),
the Word report on `Report Template.docx`, and the GitHub repository plus Pages link — whose order U014
reversed on 2026-11-18: repository and Pages first, then the report, which will cite the live URL and the
commit it points at. One thing to expect from option A: it can come back null — a corruption whose severity
does not separate the four arms is a legitimate outcome of the control, and it gets reported as one rather
than tuned until it separates.

