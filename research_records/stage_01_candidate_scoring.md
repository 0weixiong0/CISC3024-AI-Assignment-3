# Stage 01 — Candidate Scoring, Shortlist and Recommendation

Project: CISC3024 AI Assignment #3 · Date: 2026-11-17 (search opened 2026-11-16)
Gate status: **APPROVED on 2026-11-17 (U006)** — Option A (GO-LDA as the algorithm,
arXiv:2604.03928 as the test protocol only), axis weights unchanged at 20/15/25/20/20, and **both**
evaluation regimes in MVP-first order: raw-pixel ORL first, then CIFAR-100 / Tiny ImageNet frozen
features. Nothing had been implemented, downloaded or trained at the point of approval; that begins in
Stage 2, once the plan is approved.
Protocol, gates and verification log: `stage_01_search_protocol.md`. Full ledger including rejected
items and the reason for each rejection: `stage_01_screening_ledger.csv` (20 records).

---

## 1. How the candidates were scored

Five axes with the weights proposed in the protocol, confirmed unchanged by the supervisor on
2026-11-17 (U006):

| Axis | Weight | 5 means | 1 means |
| --- | --- | --- | --- |
| Algorithm complexity | 20 % | closed-form or short iterative procedure, fully explainable in the report | opaque, or needs a large backbone retrained |
| Local hardware demand | 15 % | CPU or single-GPU inference only, minutes | multi-hour/multi-GPU, or exceeds 8 GB VRAM |
| Implementation difficulty (AI-written, student writes none) | 25 % | equations recoverable from an open source **and** checkable against a reference | paywalled maths, or a port with no way to verify parity |
| Novelty | 20 % | 2024–2026, peer-reviewed, with a genuinely new claim | incremental tweak, or unreviewed preprint of unknown standing |
| Ease of scoring | 20 % | hits all six brief components, yields a clean experiment table and a browser demo | thin experimental section, or licence blocks a public demo |

Implementation difficulty carries the largest weight because the brief forbids the student writing
any code: an algorithm the agent cannot faithfully reconstruct and cannot verify is a dead end
regardless of how interesting it is.

## 2. Result

| Rank | id | Algorithm | Family | 2023+ | Weighted | Verdict |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | C4 | LDA on frozen CNN features (+ RDA/DSB) | LDA | 2026-04 | **4.20** | shortlist, but **not** eligible as "the algorithm" — see §3 |
| 2 | C1 | **GO-LDA** | LDA | 2023-05 | **3.95** | **recommended primary** |
| 3 | C2 | RSSPCA | PCA | 2025-05 | 3.75 | shortlist, PCA-side alternative |
| 4 | C3 | DLR-2DPCA | PCA | 2025-11 | 3.50 | shortlist, strongest journal, no code |
| 5 | C7 | PCA layer in a CNN + PCA-Grad-CAM | PCA | 2025-08 | 3.30 | companion technique for the front end |
| 6 | C5 | Koo-Fu CLIP | LDA | 2026-02 | 3.25 | rejected on hardware (ImageNet-1K) |
| — | C6, C8–C20 | 14 further records | both | — | 2.55–3.10 | rejected, reason recorded per row in the ledger |

## 3. Why the highest-scoring record is not the recommendation

C4 scores best on the axes precisely because it is a **benchmark study rather than an algorithm**:
its experimental machinery is a frozen backbone plus textbook LDA, which is trivially cheap to
reproduce. But the brief asks the AI to "find a recent PCA/LDA **algorithm**". Read at face value,
C4's contribution is the 180-configuration empirical finding, and its three self-proposed components
are recompositions:

- **RDA** = LDA projection, then append *k* PCA components of the LDA residual.
- **DSB** = two rounds of LDA refit with misclassified samples up-weighted ("inspired by boosting").
- **RDA+SMD** = re-solve LDA with the closest class-pair margins up-weighted.

The paper itself concludes that "plain LDA offers the best accuracy-cost tradeoff". Building the
assignment on C4 would mean presenting textbook LDA as "the recent algorithm", which is the reading
a marker is most likely to challenge. C4's real value to us is as the **evaluation protocol and
baseline set** — and it is used that way in the recommended design below.

Two further cautions about C4, both from evidence we opened. First, it is an unreviewed arXiv preprint
by self-described independent researchers with one Semantic Scholar citation and a two-star
repository. Second, its README tables and its paper tables disagree in **fourteen of the eighteen PCA
cells** — all three dataset tables were diffed cell by cell (arXiv v2 Tables I–III, README
"Results (Selected — 5-seed means)"; lead-agent diff, 2026-11-17):

| Dataset | Backbone | README | Paper |
| --- | --- | --- | --- |
| CIFAR-100 | ResNet-50 | 69.14 | 69.28 |
| CIFAR-100 | MobileNetV3-Small | 64.65 | 64.62 |
| CIFAR-100 | ViT-B/16 | 78.05 | 76.66 |
| CIFAR-100 | DINOv2 ViT-S/14 | 81.55 | 80.60 |
| Tiny ImageNet | ResNet-18 | 64.32 | 64.50 |
| Tiny ImageNet | ResNet-50 | 73.32 | 73.45 |
| Tiny ImageNet | EfficientNet-B0 | 71.97 | 71.75 |
| Tiny ImageNet | ViT-B/16 | 81.44 | 80.68 |
| CUB-200 | ResNet-18 | 55.16 | 55.35 |
| CUB-200 | ResNet-50 | 56.93 | 54.71 |
| CUB-200 | MobileNetV3-Small | 56.27 | 58.08 |
| CUB-200 | EfficientNet-B0 | 74.06 | 73.33 |
| CUB-200 | ViT-B/16 | 73.47 | 72.01 |
| CUB-200 | DINOv2 ViT-S/14 | 85.80 | 85.62 |

Four PCA cells agree (CIFAR-100 ResNet-18 65.07 and EfficientNet-B0 69.77; Tiny ImageNet MobileNetV3
61.94 and DINOv2 79.83); CUB-200 contributes none, because all six of its PCA cells differ. The `Full`
and `Classical LDA` rows are the control on the diff: all 36 cells in those two rows match exactly.

The disagreement is not confined to PCA — **one further non-PCA mismatch** is real: the README `DSB`
row differs from the paper in 5 cells (CIFAR-100 ResNet-50 72.52/72.64 and ViT-B/16 79.10/79.06;
Tiny ImageNet ResNet-50 75.18/75.16, EfficientNet-B0 72.12/72.11, DINOv2 79.54/79.00).

A second non-PCA difference recorded in the previous draft of this section — the README's CUB
`Best reduced` DINOv2 cell, 86.30 against the paper's `RDA+SMD` at 86.16 — was **a wrong-row comparison
on my part and is withdrawn** (supervisor's check, 2026-11-17). `Best reduced` is not a fourth method:
it is a per-column maximum over the paper's three "Ours" rows, and taking that maximum reproduces all
six README cells exactly — 59.39 / 61.06 / 60.75 / 76.82 / 74.51 / 86.30 — with the DINOv2 value coming
from RDA (86.30) rather than from RDA+SMD (86.16). The paper's own `Gap (Full − Best Reduced)` row
(3.50 / 3.40 / 2.26 / 1.23 / 1.21 / 1.43) is precisely `Full` minus that column maximum, which
confirms the reading independently. All six CUB `Best reduced` cells therefore agree.

So **19 of the 72 comparable README cells do not match the paper** — 14 in the PCA rows and 5 in the
DSB rows — and the earlier statement in this file that the mismatch was confined to the PCA rows was
wrong.

Two earlier cautions recorded in the first draft of this file have been **withdrawn after checking the
sources**: the projection dimension is not a
paper-versus-README conflict — paper §III-B says "All methods except Full produce d = C − 1
dimensional features (99 for CIFAR-100, 199 for Tiny ImageNet)", README line 200 says "Component
sweep: d = C − 1 confirmed optimal", and `experiments/run_component_sweep.py` sweeps
`COMPONENT_VALUES = [5, 10, 20, 40, 60, 80, 99]`; and the repository is not missing a CUB loader —
`data/cub200.py` auto-downloads `CUB_200_2011.tgz` from the CaltechDATA record
`65de6-vp158`, and `scripts/run_benchmark_fast.sh` runs `cub200` together with `cifar100` and
`tiny_imagenet`. The mismatched cells are therefore the only documented internal
inconsistency, and they are concentrated in the PCA rows. That is a reason to cite C4 carefully, not to
build on it.

## 4. Recommendation — Option A: GO-LDA as the algorithm, C4's protocol as the test bench

**GO-LDA** (arXiv:2305.14568, Liu, Cai and Niranjan, University of Southampton, submitted 23 May 2023)
claims that in multiclass LDA the generalised-eigenvalue solution yields, beyond the first direction,
discriminant axes that are **neither mutually orthogonal nor individually Fisher-maximising** — and
that this has gone unremarked for decades. It then derives a sequential procedure that deflates the
problem at each step so every new direction is orthogonal to the previous ones and maximises the
Fisher criterion on its own.

Why it fits this assignment:

1. **It is genuinely an algorithm, and the claim is checkable by computation.** The whole method is
   Algorithm 1 with equations 38–41: form the scatter matrices, take the leading generalised
   eigenvector, then at step *n* solve the deflated pencil
   `(S_B − U_{n−1} T_{n−1}^{−1} B_{n−1}) u = μ S_W u` and take the largest `μ`. Nothing in the brief
   requires a neural network (supervisor ruling U002), and a claim about the geometry of the
   discriminant subspace is something our own run can confirm or refute.
2. **Cost is a non-issue.** The paper's own analysis gives `O(NM²) + O(M³) + K·O(M²)` against
   `O(NM²) + 2O(M³)` for classic LDA — same order, and cheaper as *M* grows when `K ≪ M`. On our
   machine the raw-pixel case (ORL: 400 samples, 10,304 dimensions) is the heavy end, about 0.85 GB
   for the dense within-class scatter matrix; the feature-space cases (512-d) are seconds.
3. **It needs no dataset download to be meaningful.** The paper evaluates on twenty benchmark data
   sets (eleven UCI ML repository, five KEEL imbalanced, two face — LFW and ORL — and two medical —
   BrainTumor and DeepDrid); Table II reports nine of them, "five different UCI problems, two face
   recognition and two medical problems". Its image evidence is raw-pixel ORL (`C/N/M = 40/400/10304`,
   i.e. 112 × 92 pixels), LFW (`5/1140/1850`, whose input representation the paper does not state in
   the part we read) and ResNet-18 512-dimensional features for the two medical sets
   (`BrainTumor 4/800/512`, `DeepDrid 5/662/512`). We can reproduce the raw-pixel regime with ORL and
   add a frozen-feature regime (CIFAR-100, Tiny ImageNet) using C4's protocol as the reference — which
   is exactly the two-regime structure the stage-1 critical sweep said a classical method must be
   judged in.
4. **The student writes no code and the AI's work is verifiable.** There is no official
   implementation, so nothing is copied; and because the first GO-LDA direction must coincide with
   classic LDA's first direction, and the binary case must coincide with Foley–Sammon, we get two
   **independent parity checks** that do not depend on the paper's own numbers.
5. **It gives the front end something real to show**: the projection distributions along each
   discriminant direction, the Fisher ratio per direction, and the orthogonality violation in classic
   LDA made visible — which is the "inspect intermediate states" requirement in the outline's stage 4.

**Honest expectations, stated before implementation.** On ORL the reported margin is
0.99 ± 0.02 for GO-LDA against 0.98 ± 0.01 for classic LDA at 39 dimensions — inside noise. The
substantial reported gains appear only when the subspace is allowed to go deeper than the
classic `C − 1` rank cap (DeepDrid 0.50 ± 0.05 at 20 directions versus 0.27 ± 0.04 for LDA at four;
BrainTumor 0.59 ± 0.02 at ten directions versus 0.53 ± 0.02 at three). LFW, the paper's second face
set (`C = 5`, so `C − 1 = 4`), has exactly the same shape: classic LDA 0.66 ± 0.02 on Ω4 and GO-LDA
0.66 ± 0.02 on Ω4 — indistinguishable at the rank cap — with GO-LDA reaching 0.74 ± 0.04 only on Ω10.
So the primary hypothesis our
experiment must test is **"GO-LDA's advantage comes from going beyond C−1, not from beating LDA at
the same dimensionality"** — and a null result on the second part is a legitimate, reportable
outcome, not a failure. Two further known defects to handle: the within-class scatter is singular at
ORL scale so the reimplementation must include the ridge term `S_W + δI` (the paper suggests
δ ≈ 5 × 10⁻³ but does not report which value it used) and we must report sensitivity to δ; and the
deflated pencil is non-symmetric, so a general eigensolver is required rather than a symmetric one.

**Standing risk to disclose in the report:** GO-LDA is arXiv v1 only — no journal reference, no
citations we could confirm as independent replications, and its content also appears as a chapter of
a Southampton PhD thesis. It is a recent algorithm, but not a peer-reviewed one.

## 5. Alternatives, with their costs

**Option B — RSSPCA (PLOS ONE 2025), if you prefer a PCA algorithm.** Peer-reviewed, open access,
official GPL-3.0 MATLAB **and** the six face databases shipped as pre-extracted `.mat` matrices, so
there is no consent-restricted download and there is a reference implementation to parity-test
against. Per-configuration cost, read from the Table 3 figure on 2026-11-17, is **17.52–629.08 s for
the classification run** (FEI 17.52 → AR 629.08) and 8.85–167.41 s for the reconstruction run, on the
authors' hardware — four workstations, each with dual 20-core 2.20 GHz Intel Xeon CPUs and 256 GB RAM,
running ~40 MATLAB sessions in parallel — so one configuration is laptop-scale. Costs: every equation in the journal HTML is an image, so the MATLAB
file is effectively the specification — which raises a clean-room question we would have to answer
deliberately (reimplement from the paper and use the code only as behavioural reference); the
441-point (η₁, η₂) grid sweep — 21 × 21 values, as confirmed in `main.m` — is not reproducible in the
window and must be reduced and declared as
a deviation; and the method loses to RSMPCA on two of the six databases, with accuracies in the
0.37–0.88 range on face sets that a marker may consider a dated benchmark.

**Option C — GO-LDA *and* RSSPCA, cross-compared.** Reads strongest in the report (a supervised
versus unsupervised contrast, a feature-space versus raw-pixel contrast, and a peer-reviewed versus
preprint contrast) and satisfies the outline's invitation to cross-compare datasets and techniques.
Cost: roughly double the implementation and verification work inside six remaining days. I would
only take this if you accept that the front end and the report get compressed into 21–22 November.

**What I am not recommending:** C5 (Koo-Fu CLIP) despite the highest novelty score, because
reproducing its ImageNet-1K claim needs 1.28M images and an approved ImageNet account; and C3
(DLR-2DPCA) as a primary, because it has no code anywhere and its own table shows it losing to a
2DPCA baseline on CMU PIE — although its accepted manuscript is now cached locally
(`research_records/retrieval_cache/dlr_2dpca_tce2025_accepted_manuscript.pdf`, text-verified: 12 pages,
and all four of its claimed figures appear in the file) so it can be revived at no research cost.

## 6. Preview of the Stage-2 plan (Option A approved — this is now the brief Stage 2 executes)

Rough shape, to be written up against the `Agent_coding.pptx` loop with milestones and an MVP. The
approval fixes the regime order: **MVP = raw-pixel ORL first**, then the frozen-feature matrix
(CIFAR-100 / Tiny ImageNet) built on top of it, each scale closing with its own feasibility report:

| Item | Proposal |
| --- | --- |
| Algorithm | GO-LDA sequential deflated eigensolve, reimplemented from equations; classic LDA, PCA-then-LDA, shrinkage LDA and nearest-class-mean as baselines |
| Training set | ORL train folds (raw pixels) and the CIFAR-100 / Tiny ImageNet train splits through frozen ResNet-18 and DINOv2 features |
| Validation set | 10-fold cross-validation on ORL (matching the paper's protocol) and a held-out 5 % of the feature-space train split for `K` and `δ` |
| Test set | the untouched official test split, frozen before any GO-LDA run, plus one out-of-distribution control |
| Expected duration | MVP (ORL + parity checks) about 1–2 h; full matrix about 3–5 h of compute, most of it one-off feature extraction |
| Expected result | GO-LDA matches classic LDA at `K = C − 1` and beats it for `K > C − 1`; the orthogonality violation is measurable on our own runs |
| Verification | three independent checks: first direction equals classic LDA's; binary case equals Foley–Sammon; scatter-matrix reconstruction against `scikit-learn` |

## 7. Limits of this search, stated plainly

- The bibliographic record and the repository/abstract-level claims for the five decisive sources were
  opened **by the lead agent**. The per-table numbers for GO-LDA, RSSPCA and the C4 method
  definitions were read by wave-2 subagents from open full texts and are marked as such in the
  ledger. On 2026-11-17 the lead agent additionally (i) text-verified the DLR-2DPCA accepted
  manuscript from the cached PDF, (ii) re-opened the GO-LDA paper on ar5iv and read the dataset
  paragraph, the Table II scope sentence and the LFW/ORL/BrainTumor/DeepDrid `C/N/M` and accuracy
  cells, (iii) downloaded the PLOS ONE RSSPCA Table 3 figure and read its running-time columns, and
  (iv) listed the C4 repository file tree and opened `data/cub200.py`,
  `scripts/run_benchmark_fast.sh` and `experiments/run_component_sweep.py`, and diffed the C4 README
  tables against the arXiv v2 HTML tables cell by cell over **all three** dataset tables (CIFAR-100,
  Tiny ImageNet, CUB-200); that diff is what took the disagreeing-PCA-cell count from "8 of 12" to
  **14 of 18** and exposed one further non-PCA mismatch (the README `DSB` row). A second non-PCA
  difference the same diff appeared to expose — the CUB `Best reduced` cell — was a wrong-row comparison
  on my part and was withdrawn after the supervisor's next check (U005). Items (ii)–(iv) overturned four
  statements in the first draft of this file: the missing-CUB-loader caution, the 99-versus-100
  dimension caution, the count of disagreeing PCA cells, and the mixed
  reconstruction/classification running time for RSSPCA. The count of disagreeing PCA cells was
  corrected twice — first to 8 of 12, then to 14 of 18 — because the first re-check stopped at the two
  datasets already looked at. The full correction history, with who raised each item, is tabulated in
  `stage_01_search_protocol.md` §11.
- Two focused sweeps found **no** 2023+ paper at CVPR/ICCV/ECCV/NeurIPS/ICML/TPAMI/TIP/IJCV that
  proposes a classical PCA or LDA algorithm benchmarked as an image classifier. The active venues are
  IEEE TCE, PLOS ONE, Pattern Recognition, Neurocomputing, MDPI journals and small ACM proceedings.
  That negative result is itself evidence for report component (1).
- Paywalls blocked the experimental sections of C9, C10, C11, C12, C14 and C15, and C16's full text
  could not be obtained at all. Those rows record the level actually reached — abstract only, landing
  page only, search snippet only — rather than estimated numbers.
- C16 (an AAAI graph-embedding marginal-Fisher paper) was rejected on two counts: its year could not
  be confirmed **and its full text was unobtainable in this window**. If it turns out to be AAAI 2025
  it becomes a serious candidate and this ledger should be reopened.
- **Evidence inventory.** `research_records/` holds the three stage-1 files;
  `research_records/retrieval_cache/` the two read-only publisher files described in the next bullet;
  and `research_records/wave1_reports/` the four wave-1 subagent reports, archived verbatim on
  2026-11-17 and recovered from the session transcript (`wave1_1_pca_variants_image_recognizer.md`,
  sources [1]–[14]; `wave1_2_lda_for_cv.md`, [20]–[30];
  `wave1_3_pca_lda_in_deep_learning.md`, [40]–[51]; `wave1_4_critical_sweep_and_risks.md`, [60]–[74]).
  They had not been saved when wave 1 closed, which is why the 52-source count could not be audited
  earlier; with them on disk the 14 + 11 + 12 + 15 split is checkable from the primary material.
- No dataset, weight, package or repository was downloaded. The two files in
  `research_records/retrieval_cache/` are an **openly accessible** article and an article figure: the
  DLR-2DPCA author accepted manuscript (`dlr_2dpca_tce2025_accepted_manuscript.pdf`) and the PLOS ONE
  RSSPCA Table 3 figure (`rsspca_plosone2025_table3.png`), kept as read-only evidence for this stage and **local-only**: it was untracked on 2026-11-19 so the public repository no longer carries the publisher's asset, while the working copy stays on disk for re-verification.
  That figure had been cached earlier as `table3.png` and described in this file as a DLR figure; on
  2026-11-17 it was matched byte for byte against the PLOS ONE asset for `pone.0323281.t003`
  (md5 `ab3eb10721d2ee0ab45a23971dde0c17`), so it is the RSSPCA table and the duplicate was deleted.
  "Openly accessible" rather than "openly licensed" is the accurate description: the accepted
  manuscript is a publisher self-archiving version whose re-use terms were not checked, so it is cited
  as evidence and not redistributed as an asset.

## 8. Approval answers received (2026-11-17, recorded as U006)

1. **Option A approved** — GO-LDA as "the recent algorithm", arXiv:2604.03928 used only as the
   evaluation protocol and baseline set. Options B and C are not taken.
2. **Weights confirmed as proposed** — 20 % algorithm complexity / 15 % local hardware demand /
   25 % implementation difficulty / 20 % novelty / 20 % ease of scoring. Nothing in §1 or in the
   ledger's `weighted` column changes.
3. **Both regimes approved, MVP first** — raw-pixel ORL as the small-scale implementation and test, then
   the CIFAR-100 / Tiny ImageNet frozen-feature matrix, with a feasibility report per scale.
4. Note for later: component (6) will need a GitHub repository and Pages site for this assignment, so
   I will need your go-ahead to create `CISC3024-AI-Assignment-3` in the final stage — the `gh` CLI is
   already authenticated on this machine.
