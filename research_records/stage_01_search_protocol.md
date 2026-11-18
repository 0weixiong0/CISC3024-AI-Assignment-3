# Stage 01 — Literature Search Protocol, Executed Queries and Verification Record

Project: CISC3024 AI Assignment #3 · Started 2026-11-16, wave 2 on 2026-11-17 · Language: English
Skill used: `deep-research` (already installed locally — no download or installation was needed, so
no installation approval was required; the supervisor's instruction to use it for the search stage is
recorded in `conversation_log.md` as U001, and his four scope rulings as U002). Depth: **deep**.

Status: **Stage-1 gate PASSED — the supervisor approved Option A on 2026-11-17 (U006)**, keeping the
five axis weights at 20/15/25/20/20 and approving both evaluation regimes, raw-pixel ORL as the MVP
before the CIFAR-100 / Tiny ImageNet frozen-feature matrix. Wave 1 retrieval complete (52 sources, whose
four subagent reports are archived verbatim in `research_records/wave1_reports/`), lead-agent
verification of the five decisive sources complete, wave 2 gap-fill **merged on 2026-11-17** (20 further
sources). Nothing in this stage was downloaded as a project dependency, installed, implemented or
trained; two read-only evidence files sit in `retrieval_cache/` and are listed in
`stage_01_candidate_scoring.md` §7.

---

## 1. Research question

Which algorithm published **2023 or later** in the PCA or LDA family is genuinely applied to computer
vision or pattern recognition, and offers the best defensible combination of algorithmic
transparency, local feasibility on an RTX 4060 8 GB laptop, ease of AI reimplementation without
official code, novelty, and coverage of the six mandatory report components — inside a window that
ends 2026-11-23?

## 2. Constraints fixed before searching

- **Recency is a hard filter, not a preference.** The brief says "a recent … algorithm". Primary
  window 2023–2026 (supervisor's ruling U002). Pre-2023 work may appear only as a foundational
  reference, a tool, or a rejection example, and is labelled as such everywhere in this project.
- **Both families are in the pool** — PCA-only, LDA-only and PCA+LDA hybrids — and the choice between
  them is made on the evidence, not in advance (U002).
- **The target need not be a neural network** (U002). It must, however, be evaluated as a
  classifier or recognizer on image data. Generative models, detection/segmentation systems and
  LLM-adaptation techniques are out of scope.
- The student may not write code; all implementation is AI-generated. An algorithm whose equations
  cannot be recovered from public sources is therefore unusable no matter how novel.
- **No dataset, weight, package or repository was downloaded during screening.** Web research read
  public evidence only.
- Component (6) of the brief requires a **webpage link** to the source code. The supervisor accepts
  that this will be a GitHub Pages demo, deferred to the final stage (U002). Hosting is therefore a
  selection criterion, not an afterthought: a candidate that cannot be demonstrated in a browser is
  penalised on the "ease of scoring" axis.
- Local resources measured on 2026-11-16: i9-13900H (14 cores / 20 threads), 32 GB RAM, RTX 4060
  Laptop GPU 8 GB, Python 3.12.10, numpy 2.4.6, scikit-learn 1.9.0, torch 2.7.1+cu128 with CUDA
  available. No candidate has been benchmarked locally, so **every cost figure in this stage is a
  literature value or an explicitly labelled estimate** — see the honesty rule in §6.

## 3. Search space (four areas)

| # | Area | Sub-questions |
| --- | --- | --- |
| A | PCA-family algorithms for image classification/recognition, 2023+ | Which 2023+ papers propose a new PCA variant (2DPCA/tensor, kernel, sparse, robust, probabilistic) evaluated as an image recognizer? On which datasets, with what accuracy, and is code released? |
| B | LDA / discriminant-analysis family, 2023+ | Which 2023+ papers propose a new LDA variant (regularised/shrinkage, orthogonal/uncorrelated, multilinear, graph-embedded, marginal) or a new use of discriminant analysis on image data? Same evidence questions. |
| C | PCA/LDA inside or on top of deep learning, 2023+ | Differentiable PCA/LDA layers, whitening layers, LDA heads, and classical projections attached to frozen pretrained or foundation-model features. Which of these are cheap enough to reproduce locally? |
| D | Critical and reproducibility evidence | Documented failure modes (small-sample-size singularity, the C−1 rank cap, sensitivity to regularisation, overlapping-class criticism), where classical heads are still competitive, existing library support, and the real reproduction cost. |

## 4. Queries executed

Wave 1 (four parallel retrieval subagents, one per area). Representative terms, as issued:

- `2DPCA image classification 2024`, `novel PCA variant face recognition 2024 2025`,
  `sparse PCA image recognition pattern recognition 2024`,
  `robust principal component analysis classification 2024`,
  `probabilistic PCA deep feature classification 2023`, `PCA small sample size high dimensional
  image classification 2024`, `Pattern Recognition journal PCA 2024 image`
- `linear discriminant analysis image classification 2024`,
  `regularized LDA high dimensional small sample 2024`,
  `uncorrelated orthogonal LDA 2023 2024`, `multilinear tensor LDA image recognition 2024`,
  `marginal Fisher analysis LDA variant 2023`, `LDA few-shot classification 2024 2025`,
  `CLIP embeddings linear discriminant analysis classification 2024`,
  `discriminant analysis foundation model features image recognition 2025`
- `differentiable PCA layer neural network 2024`,
  `differentiable linear discriminant analysis layer 2023 2024`,
  `whitening layer batch normalization decorrelation 2024 image classification`,
  `neural network embedded PCA LDA 2024`, `LDA head pretrained vision transformer features 2024`,
  `DINOv2 features linear discriminant analysis classification 2025`,
  `subspace learning deep features recognition 2024`
- `curse of dimensionality linear discriminant analysis criticism`,
  `small sample size problem LDA face recognition solution 2024`,
  `classical baselines competitive pretrained features linear classifier 2024`,
  `nearest class mean few-shot linear probes 2024`,
  `scikit-learn LinearDiscriminantAnalysis shrinkage solver documentation`,
  `covariance estimation high dimensional 32GB RAM tractable`

Each area also carried a mandated critical/opposing term so the retrieval could not be one-sided
(area D exists for that purpose).

## 5. Screening gates, applied in order

| Gate | Rule | Effect |
| --- | --- | --- |
| G1 recency | Algorithm published 2023-01-01 or later; venue/paper date verified at the publisher | 2022 bilateral-2DPCA fusion, 2021 Neurocomputing 2DPCA survey, 2018 Decorrelated BN, 2021 Stochastic Whitening BN, 2018 Max-Mahalanobis LDA, 2016 DeepLDA, 1989 RDA, 2004 dual-space LDA → foundational/baseline only |
| G2 task | Evaluated as a classifier/recognizer on image data | randomised-PCA-for-SVM study (arXiv:2403.09117), LDA-GO (arXiv:2506.06845), ConvexLDA (arXiv:2503.13623), spiked-covariance SRLDA (arXiv:2210.03859) → out of scope or downgraded |
| G3 recoverability | Equations recoverable from an openly readable source, or official code readable | paywalled IEEE TCE / ScienceDirect / ACM entries kept but flagged; a candidate cannot enter the top recommendation while its experimental section is unread |
| G4 local feasibility | Trainable or reproducible within 8 GB VRAM / 32 GB RAM and the remaining days | ImageNet-scale retraining excluded; frozen-backbone inference and closed-form eigensolves included |
| G5 demonstrability | Can be shown in a browser for component (6) | penalises methods whose only artefact is a MATLAB figure |

## 6. Scoring rubric

Five axes, each scored 1–5, higher is better for the student. The weights are my proposal and are
open to the supervisor's edit before the shortlist is approved.

| Axis | What a 5 means | What a 1 means | Weight |
| --- | --- | --- | --- |
| Algorithm complexity | closed-form or a short iterative procedure, fully explainable in the report | opaque, or requires retraining a large backbone | 20 % |
| Local hardware demand | CPU or single-GPU inference only, minutes | multi-hour/multi-GPU, or exceeds 8 GB VRAM | 15 % |
| Implementation difficulty (AI-written, no student code) | equations recoverable from an open paper and verifiable against a reference implementation | paywalled maths, or a MATLAB port with no way to check parity | 25 % |
| Novelty | 2024–2026, peer-reviewed, with a claim that is genuinely new | incremental tweak, or unreviewed preprint by unknown authors | 20 % |
| Ease of scoring | hits all six brief components, produces a clean experiment table and a browser demo | thin experimental section, or a dataset whose licence blocks a public demo | 20 % |

**Honesty rule applied throughout:** a cell is filled only from a source that was actually opened.
`not verified` means the lead agent or a subagent could not read the evidence, and it is written as
such rather than being guessed.

## 7. Wave 1 result

**52** tagged sources returned across the four areas (numbering [1]–[14], [20]–[30], [40]–[51],
[60]–[74] = 14 + 11 + 12 + 15). The four wave-1 subagent reports are archived verbatim under
`research_records/wave1_reports/` (extracted from the session transcript on 2026-11-17), so the count
is checkable from the primary material rather than from memory: the files carry 14, 11, 12 and 15
numbered entries respectively, and the identifier sequences are contiguous — the three identifiers an
automated line scan missed ([2], [9], [62]) were each confirmed present by hand.
Wave 2 added 20 further sources, [80]–[84], [90]–[95] and [100]–[108], for 72 in total. An earlier
draft of this file stated "40 tagged sources", which was a recollection rather than a count and is
superseded.

Two findings that shape the whole shortlist:

1. **The 2023+ "new PCA variant" literature that is evaluated on images lives almost entirely in
   journals, not in the top CV venues** — IEEE Transactions on Consumer Electronics, PLOS ONE,
   Pattern Recognition, Sensors, Multimedia Tools and Applications, small ACM proceedings. No
   2023+ CVPR/ICCV/ECCV/NeurIPS/ICML or TPAMI/TIP/IJCV paper proposing a new PCA algorithm for image
   recognition surfaced in these searches. That is itself reportable evidence for component (1).
2. **The 2023+ LDA activity that is both recent and image-evaluated has shifted to LDA as a
   closed-form stage attached to frozen pretrained or foundation-model features**, which is exactly
   the regime where this laptop can reproduce a paper's numbers within hours rather than days.

## 8. Lead-agent verification of the decisive claims

Per project policy, the numbers that drive the recommendation were re-opened by the lead agent rather
than taken from a subagent's summary. V1–V5 (wave 1) all resolved **SUPPORTED**; no fabricated
identifier, author, date or number was found in wave 1. V6–V9 were added on 2026-11-17 after the
supervisor's fact-check (recorded as U003), and V6–V9 are what overturned four statements in the
first draft of the stage-1 documents. V10 was added the same day after the supervisor's second
fact-check (U004), which corrected the C4 table-diff count and the claim that the mismatches were
confined to the PCA rows.

| # | Claim under test | Source opened | Rating |
| --- | --- | --- | --- |
| V1 | GO-LDA exists: arXiv:2305.14568, J. Liu / X. Cai / M. Niranjan, submitted 23 May 2023, cs.CV, CC BY 4.0, claiming classic multiclass LDA's generalised eigenvectors are neither orthogonal nor Fisher-maximising beyond the first direction | `arxiv.org/abs/2305.14568` | SUPPORTED |
| V2 | arXiv:2604.03928 exists: "Supervised Dimensionality Reduction Revisited: Why LDA on Frozen CNN Features Deserves a Second Look", Kumar/Karhana/Jasti/Lade, v1 5 Apr 2026 / v2 10 May 2026, 11 pages, 10 strategies × 6 frozen backbones × CIFAR-100 / Tiny ImageNet / CUB-200-2011, LDA better in 11/12 coarse configs (up to +4.5 pp, 48–87 % dimensionality cut), worse on all CUB configs, code link in the Comments field | `arxiv.org/abs/2604.03928` | SUPPORTED |
| V3 | The official repository exists and is MIT-licensed, 16 commits, Python 3.11+, with `data/ experiments/ features/ results/ scripts/`, and its README carries the per-backbone accuracy tables (e.g. CIFAR-100 ResNet-18 Full 62.85 → LDA 66.97; DINOv2 80.72 → 82.37) and "~5 min per backbone" extraction cost | `github.com/IndarKarhana/lda-image-classification` | SUPPORTED |
| V4 | Koo-Fu CLIP exists: arXiv:2602.01127, Suchanek/Janouskova/Vasatko/Matas, 1 Feb 2026, closed-form Fukunaga-Koontz LDA on CLIP embeddings, ImageNet-1K top-1 75.1 % → 79.1 %, 10–12× compression, **no code link on the arXiv page**, licence CC BY-NC-SA 4.0 | `arxiv.org/abs/2602.01127` | SUPPORTED |
| V5 | RSSPCA exists and is peer-reviewed: PLOS ONE 20(5):e0323281, published 27 May 2025, Wang/Xie/Zhang/Li/Cai/Feng, Laplacian smoothness added to robust sparse PCA, solved by Minorization-Maximization, six face databases, data and code released at `github.com/yuzhounh/RSSPCA` | `journals.plos.org/plosone/article?id=10.1371/journal.pone.0323281` | SUPPORTED |
| V6 | GO-LDA's benchmark scope and the numbers quoted in the recommendation: twenty benchmark data sets (eleven UCI ML repository, five KEEL imbalanced, two face — LFW and ORL — two medical — BrainTumor and DeepDrid); Table II reports "five different UCI problems, two face recognition and two medical problems"; the medical sets are pushed through a pre-trained ResNet-18 into a fixed 512-d representation; `C/N/M` = LFW 5/1140/1850, ORL 40/400/10304, BrainTumor 4/800/512, DeepDrid 5/662/512; LFW classic-LDA 0.66 ± 0.02 on Ω4 vs GO-LDA 0.66 ± 0.02 on Ω4 and 0.74 ± 0.04 on Ω10; ORL LDA 0.98 ± 0.01 on Ω39 vs GO-LDA 0.99 ± 0.02 on Ω39 | `ar5iv.labs.arxiv.org/html/2305.14568`, read by the lead agent on 2026-11-17 | SUPPORTED |
| V7 | DLR-2DPCA's headline accuracies — CMU PIE 82.71, GTSRB 74.24, MNIST 85.57, and 83.85 for the 2DPCA-2-L_p baseline that beats it — plus 12-page length, training times 1.13–1.56 and convergence within ten iterations | accepted manuscript PDF cached at `retrieval_cache/dlr_2dpca_tce2025_accepted_manuscript.pdf`, text extracted and each figure counted by the lead agent | SUPPORTED — supersedes the wave-1 "HTTP 403, not verified" note |
| V8 | RSSPCA per-configuration running times: classification 17.52 s (FEI) to 629.08 s (AR), reconstruction 8.85 s (FEI) to 167.41 s (ORL); hardware = four workstations, dual 20-core 2.20 GHz Intel Xeon each, 256 GB RAM, ~40 parallel MATLAB sessions | PLOS ONE figure asset for `pone.0323281.t003` (4500 × 3544 PNG) downloaded and read by the lead agent, cached at `retrieval_cache/rsspca_plosone2025_table3.png` — **local-only evidence: the publisher figure asset is not redistributed from the public repository** | SUPPORTED — supersedes the mixed "8.85–629.08 s" range |
| V9 | C4 repository and table internals: `data/cub200.py` auto-downloads `CUB_200_2011.tgz` from `data.caltech.edu/records/65de6-vp158`; `scripts/run_benchmark_fast.sh` sets `DATASETS="cifar100 tiny_imagenet cub200"`; `experiments/run_component_sweep.py` has `COMPONENT_VALUES = [5, 10, 20, 40, 60, 80, 99]`; README line 200 reads "Component sweep: d = C−1 confirmed optimal"; paper §III-B reads "d = C − 1 dimensional features (99 for CIFAR-100, 199 for Tiny ImageNet)" | GitHub raw files, repository tree via `gh api`, and `arxiv.org/html/2604.03928v2`, all opened by the lead agent on 2026-11-17 | SUPPORTED for the repo facts; **REFUTED** the two first-draft cautions ("no CUB-200 loader", "README says d = 100") |
| V10 | C4's README versus arXiv v2 tables, diffed cell by cell over **all three** dataset tables (Tables I–III = CIFAR-100, Tiny ImageNet, CUB-200-2011; captions confirmed in the HTML text layer): **14 of 18 PCA cells differ** — CIFAR-100 4, Tiny ImageNet 4, CUB-200 all 6 (README 55.16/56.93/56.27/74.06/73.47/85.80 vs paper 55.35/54.71/58.08/73.33/72.01/85.62); the four agreeing PCA cells are CIFAR-100 ResNet-18 65.07 and EfficientNet-B0 69.77, Tiny ImageNet MobileNetV3 61.94 and DINOv2 79.83; **every `Full` and `Classical LDA` cell agrees** (36 of 36); beyond PCA, the README `DSB` row differs in 5 cells (CIFAR-100 ResNet-50 72.52/72.64 and ViT 79.10/79.06; Tiny ImageNet ResNet-50 75.18/75.16, EfficientNet 72.12/72.11, DINOv2 79.54/79.00) while the README CUB `Best reduced` row **agrees in all 6 cells** once it is read for what it is — a per-column maximum over the paper's `RDA`/`DSB`/`RDA+SMD` rows, not a fourth method: that maximum is 59.39/61.06/60.75/76.82/74.51/86.30, and the DINOv2 86.30 comes from `RDA` rather than from `RDA+SMD` at 86.16; the paper's own `Gap (Full − Best Reduced)` row (3.50/3.40/2.26/1.23/1.21/1.43) reproduces exactly as `Full` minus that column maximum, which confirms it. **Total: 19 of 72 comparable cells disagree** | README from the repository raw file and `arxiv.org/html/2604.03928v2`, both opened by the lead agent on 2026-11-17 and compared by script | SUPPORTED — corrects the "8 of 12" count and refutes the first-draft claim that the inconsistency is confined to the PCA rows; the U005 round then corrected one entry of this row itself, the CUB `Best reduced` cell, which is a derived row and agrees |

What the first pass could **not** verify, and what still stands after V6–V10:

- ~~DLR-2DPCA's experimental section is unreachable (IEEE paywall, HTTP 403 on the only open
  manuscript copy found), so its numbers are not verified.~~ **Closed by V7** — an accepted manuscript
  was obtained and text-verified, and §10 rates the claim High.
- ~~The per-database accuracy tables of GO-LDA were read by a subagent only.~~ **Closed by V6** for the
  rows the recommendation actually quotes (LFW, ORL, BrainTumor, DeepDrid and the Table II scope). What
  remains is narrower than the original caveat: the numbers still come from **one** source with no
  independent replication anywhere found, and the paper is internally inconsistent about the BrainTumor
  sample count (Table II `N = 800`, the setting text 592 + 148).
- **Still open:** the RSSPCA running-time and accuracy cells come from a table the journal publishes as
  an image, so they were read from the figure (V8), not from a machine-readable text layer; and the
  GO-LDA LFW row does not state whether `M = 1850` is raw pixels or an embedding, so we cannot tell what
  representation that dataset used.

## 9. Wave 2 — gap-fill targets (merged 2026-11-17)

| Target | Question |
| --- | --- |
| GO-LDA | Can the algorithm and its image-experiment tables be recovered from the openly readable HTML? What is the cost of the sequential eigensolve, what happens when the within-class scatter is singular, and has the paper been published or reproduced by anyone? |
| arXiv:2604.03928 | What exactly are RDA / DSB / RDA+SMD algorithmically, are the authors' claims of novelty defensible, is the study peer-reviewed, and can the repository actually be reproduced locally given the CUB-200 licence? |
| RSSPCA and DLR-2DPCA | Are the RSSPCA equations and the Laplacian construction recoverable from the open PLOS ONE text; what are the per-database numbers; is one (c₁,c₂) configuration laptop-scale; what do the GPL-3.0 MATLAB code and the face-database terms of use imply for a public demo; and can any open copy of DLR-2DPCA be read at all? |

## 10. Triangulation and confidence

Wave 2 merged on 2026-11-17 (sources [80]–[84], [90]–[95], [100]–[108]). Confidence by claim class:

| Claim | Confidence | Basis |
| --- | --- | --- |
| GO-LDA exists, is 2023-05, arXiv-only, has no official code, and its algorithm is fully recoverable from Algorithm 1 | **High** | lead agent opened the abs page; wave-2 agent read the open HTML end to end and quoted the equations, the cost analysis and the singularity remedy; absence of code confirmed by grep over the full text plus a repository search; the lead agent re-opened the ar5iv HTML on 2026-11-17 and read the dataset paragraph and Table II scope (V6) |
| GO-LDA's reported per-dataset accuracies (ORL 0.99 ± 0.02 vs LDA 0.98 ± 0.01; LFW 0.66 ± 0.02 at Ω4 = C−1 rising to 0.74 ± 0.04 at Ω10 vs LDA 0.66 ± 0.02; DeepDrid 0.50 vs 0.27; BrainTumor 0.59 vs 0.53) | **Medium** | single source (the paper's own tables); first read by a subagent, then re-read by the lead agent for exactly the rows the recommendation quotes (V6); no independent replication found anywhere; the paper is internally inconsistent about the BrainTumor sample count (Table II says 800, the setting text says 592 + 148), and the LFW row does not state whether M = 1850 is raw pixels or an embedding |
| C4 is an unreviewed preprint whose self-proposed new components are recompositions of textbook scatter algebra | **High** | lead agent opened the arXiv page and the repository; wave-2 agent read the method section, the GitHub API metadata and the Semantic Scholar record; on 2026-11-17 the lead agent opened `data/cub200.py`, `scripts/run_benchmark_fast.sh` and `experiments/run_component_sweep.py` and diffed the README tables against the arXiv v2 HTML tables cell by cell over all three dataset tables (V9, V10) — which **refuted** two cautions carried in the first draft: the repository does ship a CUB-200 loader, and the projection dimension is `d = C − 1` in both the paper and the README, and which quantified the README/paper disagreement at 14 of 18 PCA cells |
| RSSPCA is peer-reviewed 2025, ships MATLAB code and the six face matrices, and one configuration is laptop-scale | **High** | lead agent opened the article page and read the abstract, the data-availability statement and the hardware paragraph; wave-2 agent read sections 3–4; the lead agent additionally downloaded the Table 3 figure and read its running-time columns on 2026-11-17 (V8), giving classification 17.52–629.08 s and reconstruction 8.85–167.41 s |
| DLR-2DPCA's datasets and accuracies (CMU PIE 82.71, GTSRB 74.24, MNIST 85.57, and 83.85 for the 2DPCA-2-L_p baseline that beats it) | **High** | the accepted manuscript was downloaded and text-verified by the lead agent; each figure occurs exactly once in the 12-page file — cached in `retrieval_cache/` |
| CUB-200-2011 is CC-BY on the DOI-issuing CaltechDATA record, 1.2 GB | **High** | lead agent opened the record and read the Rights/License field |
| No 2023+ top-venue classical PCA/LDA image-classification algorithm exists in the searched venues | **Medium** | two focused sweeps returned a clean negative; a negative result cannot be triangulated the usual way, so it is reported as a finding with its method attached |
| Every cost figure attributed to our own machine | **Low until measured** | nothing has been run locally; §2 states this explicitly |

Contradictions deliberately kept as findings rather than resolved: (i) C4's README versus paper tables
— **14 of the 18 PCA cells differ** (4 of 6 on CIFAR-100, 4 of 6 on Tiny ImageNet, 6 of 6 on CUB-200),
and five DSB cells also disagree, while all 36 `Full` and `Classical LDA` cells and all six CUB
`Best reduced` cells agree (19 of 72 comparable cells in total); values tabulated in
`stage_01_candidate_scoring.md` §3; (ii) RSSPCA winning on four of six databases but losing on two;
(iii) GO-LDA's large gains only beyond the `C − 1` rank cap, while at the cap itself both face sets are
inside noise (ORL 0.99 vs 0.98 at Ω39, LFW 0.66 vs 0.66 at Ω4); (iv) the supervisor's outline calling
the target a neural network while the brief asks for a PCA/LDA algorithm — ruled in U002 as "need not
be a neural network".

The scored shortlist, the rejection reasons for all 20 records, and the recommendation are in
`stage_01_candidate_scoring.md` and `stage_01_screening_ledger.csv`.

## 11. Corrections made after the supervisor's fact-checks (U003, U004 and U005, 2026-11-17)

The supervisor returned a list of factual and arithmetic errors in the first draft of the three
stage-1 documents. Each item below was re-checked against the source before being written into these
files; the verification rows are V6–V10 in §8. This table is kept because report component (1) is
about *how* the AI found and corrected the material, not only about what it found. Rows 1–13 came from
the supervisor's first fact-check (U003); rows 14–16 were added in the second and third rounds
(U004 and U005): row 14 tabulates the U003 status-unification item that had been left out of this table,
row 15 is an error the lead agent caught while doing the U004 diff, and row 16 corrects an entry of row
15 itself — a derived summary row compared against the wrong method row. Row 6 was rewritten in the U004 round because the count it
recorded was itself still wrong.

| # | Statement in the first draft | What the check found | Raised by | Corrected in |
| --- | --- | --- | --- | --- |
| 1 | `weighted` values for C8 2.85, C16 3.05, C17 2.75, C18 2.75, C19 2.95, C20 3.05 | Six arithmetic slips against the stated 20/15/25/20/20 weights; recomputed by script from the axis columns (C8 3.10, C16 2.90, C17 2.85, C18 2.85, C19 2.85, C20 3.10) and all 20 rows re-verified — no residual mismatch | supervisor | `stage_01_screening_ledger.csv` |
| 2 | "13 further records" in the scoring table | 20 records minus the six shown individually = **14** (C6 plus C8–C20); the 2.55–3.10 range still holds after item 1 | supervisor | `stage_01_candidate_scoring.md` §2 |
| 3 | "40 tagged sources" in §7 | The four wave-1 ranges are contiguous and sum to **52**; the three identifiers an automated scan missed ([2], [9], [62]) were confirmed present by hand. Wave 2 adds 20 more ([80]–[84], [90]–[95], [100]–[108]) = 72. The four wave-1 reports were archived under `research_records/wave1_reports/` in the U004 round, so the 14/11/12/15 split is checkable from the primary material rather than from the ranges alone | supervisor | `stage_01_search_protocol.md` §7, status line |
| 4 | "C4 contains no CUB-200 loader although six of eighteen configurations are CUB results" | **Refuted.** `data/cub200.py` auto-downloads `CUB_200_2011.tgz` from the CaltechDATA record `65de6-vp158`; `scripts/run_benchmark_fast.sh` sets `DATASETS="cifar100 tiny_imagenet cub200"` | supervisor | scoring §3, ledger C4 |
| 5 | "paper says CIFAR-100 d=99 while the README says d=100" | **No such conflict exists.** Paper §III-B: "d = C − 1 dimensional features (99 for CIFAR-100, 199 for Tiny ImageNet)"; README line 200: "Component sweep: d = C − 1 confirmed optimal"; `run_component_sweep.py`: `COMPONENT_VALUES = [5, 10, 20, 40, 60, 80, 99]` | supervisor | scoring §3, ledger C4 |
| 6 | "and two PCA accuracy figures [disagree]" | Cell-by-cell diff over **all three** dataset tables: **14 of 18** PCA cells differ — CIFAR-100 R50 69.14/69.28, MobileNetV3 64.65/64.62, ViT-B/16 78.05/76.66, DINOv2 81.55/80.60; Tiny ImageNet R18 64.32/64.50, R50 73.32/73.45, EfficientNet-B0 71.97/71.75, ViT-B/16 81.44/80.68; CUB-200 **all six** (README 55.16/56.93/56.27/74.06/73.47/85.80 vs paper 55.35/54.71/58.08/73.33/72.01/85.62) (README/paper). Four cells agree: CIFAR-100 ResNet-18 65.07 and EfficientNet-B0 69.77, Tiny ImageNet MobileNetV3 61.94 and DINOv2 79.83. The count recorded after U003 ("8 of 12") was itself incomplete — CUB-200 had not been diffed | supervisor (U003, re-corrected in U004) | scoring §3 (sentence, table, "other four", "only eight"), ledger C4, §8 V10, §10 (i) |
| 7 | GO-LDA evidence described as "raw-pixel ORL plus ResNet-18 features on two medical sets"; LFW absent | The paper's twenty benchmark sets include **two face sets, LFW and ORL**; Table II covers nine (five UCI problems, two face, two medical). LFW `5/1140/1850`: LDA 0.66 ± 0.02 on Ω4, GO-LDA 0.66 ± 0.02 on Ω4 and **0.74 ± 0.04 on Ω10** — a second instance of the same-shape result the recommendation rests on | supervisor | scoring §4 (item 3 and the expectations paragraph), ledger C1, §10 rows |
| 8 | "one (η₁, η₂) configuration takes 8.85–629.08 s" | Two different columns of Table 3 were merged. RSSPCA **classification** 17.52–629.08 s; **reconstruction** 8.85–167.41 s; hardware is four workstations with dual 20-core 2.20 GHz Xeons and 256 GB RAM each, ~40 parallel MATLAB sessions | supervisor | scoring §5, ledger C2, §8 V8 |
| 9 | "openly licensed articles" | "Openly **accessible**" is what was actually established; the accepted manuscript's re-use terms were not checked | supervisor | scoring §7 |
| 10 | C16 "rejected pending year verification" | Two grounds, not one: the year is unresolved **and** the full text was unobtainable in this window | supervisor | ledger C16, scoring §7 |
| 11 | `retrieval_cache/table3.png` described as a DLR-2DPCA figure | **Self-caught while doing item 8:** the file is byte-identical (md5 `ab3eb107…`) to the PLOS ONE asset for `pone.0323281.t003`, i.e. the RSSPCA Table 3. Renamed `rsspca_plosone2025_table3.png`; the duplicate was deleted, so the cache holds two files, not three | lead agent | scoring §7, ledger C2 |
| 12 | "Those rows carry `not verified` in the ledger" | The ledger records the level actually reached (abstract only / landing page only / search snippet only), not the literal string `not verified` | lead agent | scoring §7 |
| 13 | "the ~441-point (η₁, η₂) grid sweep" | Confirmed at exactly 21 × 21 = 441 by the supervisor reading `main.m`; the tilde was removed and the source noted | supervisor (verification) | scoring §5, ledger C2 |
| 14 | Protocol status line "wave 2 in progress" together with a §8 row that still read "DLR-2DPCA not verified (HTTP 403)", while §10 and the ledger already rated those claims High | The three statements described the same files at three different times. Unified to: wave 2 **merged on 2026-11-17**; the accepted manuscript obtained and text-verified (V7), which supersedes the 403 note; §8 opening, the §8 caveat list, the §9 heading and the §10 lead-in now agree | supervisor | `stage_01_search_protocol.md` status line, §8, §9, §10 |
| 15 | "The eight mismatched cells are therefore the only documented internal inconsistency, and they are confined to the PCA rows" | **Self-caught while diffing CUB-200 for item 6.** Not confined to PCA: the README `DSB` row differs from the paper in 5 cells (CIFAR-100 ResNet-50 72.52/72.64 and ViT 79.10/79.06; Tiny ImageNet ResNet-50 75.18/75.16, EfficientNet 72.12/72.11, DINOv2 79.54/79.00) What does hold is that `Full` and `Classical LDA` agree in all 36 cells. A third item recorded in that same draft — the CUB `Best reduced` cell against the paper's `RDA+SMD` row — was not a mismatch but a wrong-row comparison: `Best reduced` is the per-column maximum over `RDA`/`DSB`/`RDA+SMD`, so all six of its cells agree, and the total is 19 of 72, not 20 | lead agent (mismatch), supervisor (wrong-row comparison) | scoring §3, §8 V10, §10 (i), row 16 below |
| 16 | Part of row 15: "the README CUB `Best reduced` row differs from the paper's `RDA+SMD` row in 1 cell (DINOv2 86.30/86.16)", and the 20-cell total derived from it | `Best reduced` is not a fourth method but a derived summary row — the per-column maximum over `RDA`, `DSB` and `RDA+SMD`. That maximum is 59.39/61.06/60.75/76.82/74.51/86.30, which equals the README in all six cells, so the DINOv2 86.30 comes from `RDA` and there is no mismatch there. Cross-check: the paper's own `Gap (Full − Best Reduced)` row prints 1.43 for DINOv2 and 87.73 − 86.30 = 1.43, which cannot be reproduced from 86.16. The non-matching total is **19 of 72** (14 PCA + 5 DSB) and exactly **one** non-PCA row is affected | supervisor (U005) | scoring §3 and §7, ledger C4, §8 V10, §10 (i) |

**What did not change:** the Option A recommendation, the ranking of the six scored candidates, the
five axis weights, the 2023 recency floor, and every gate decision. Items 4, 5 and 8 removed
objections to C4 and to Option B rather than adding any; item 7 strengthened the main hypothesis;
items 6 and 15 made the C4 record *less* reliable, not more, but both concern internal inconsistencies
in a benchmark study we use only as a protocol source, so the recommendation is unaffected; item 16 went
the other way — it removed an objection to C4, and it was an error in my own comparison rather than in the paper.
The pattern is worth recording for report component (5): three of the errors were subagent-read table
cells asserted at a precision the lead agent had not re-opened, one was an arithmetic slip the rubric
made easy to hide, and two more (items 6 and 15) were counts that the lead agent's own first
re-verification got wrong because it stopped at the two datasets it had already looked at, and one (item 16)
was a comparison made against the wrong row of the same table — which is
why the weighted column is now recomputed by script and every table diff is run over all three dataset
tables rather than the convenient two.

