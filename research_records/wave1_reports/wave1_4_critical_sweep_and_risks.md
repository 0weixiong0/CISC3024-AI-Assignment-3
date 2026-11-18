# Wave-1 subagent report: critical sweep: evaluation regimes, baselines, risks

Archived 2026-11-17 from the coding-session transcript (`fe7103b0-1f40-4383-a4a4-cb5759e0179d.jsonl`, tool_use_id `call_2538160a907248458628ced5`, returned 2026-11-16T16:00:07.084Z).
Source numbering assigned in this report: [60]-[74] (15 numbered sources). Body below is the subagent output verbatim.

---

## Area Takeaway

The dominant risk is choosing a 2023+ PCA/LDA variant whose selling point is beating other classical methods on raw pixels: that literature openly acknowledges LDA's structural weaknesses (small-sample-size singularity, rank cap at C−1, sensitivity to regularization, poor behavior on heavily mixed real image data), so a laptop reproduction on natural images will likely show the variant losing to a trivial linear probe on frozen foundation features, which weakens the "lessons learned" section if not planned for. The safer frame is to benchmark the reimplemented 2023+ method on both raw pixels (where the SSS problem is real and demonstrable) and frozen pretrained features (where classical pipelines are genuinely competitive per CLIP/DINOv2-era evidence), since the hardware is a non-issue: covariance matrices at CIFAR scale are tens of megabytes, and scikit-learn 1.9 already ships shrinkage-LDA, so from-scratch work is feasible in a week. On integrity, Turnitin's own blog and 2024–2025 studies confirm AI-detector false positives are common, but paraphrase-plus-citation remains the only defensible quoting practice; per-source detector thresholds are not publicly documented.

## Findings

- **Failure modes:**
  - The 2024 review by Qu et al. (Processes 12(7):1382) states classical LDA "has three primary drawbacks, i.e., small sample size problem, sensitivity to ..." (quote truncated by paywall; the third item almost certainly covers the singularity/scatter-matrix issue). Tier 1, but I could verify only the snippet, not the full list — treat the exact wording with caution [60].
  - Lamarr Institute's 2023 explainer (updated 2025) is an explicitly skeptical source: "Too few data points can lead to overfitting... outliers can fundamentally distort results," and "LDA does not work well if the centers of different classes overlap or their data points are heavily mixed" — precisely the CIFAR/natural-image regime. It also warns reduction "always involves some loss of information" [61].
  - The small-sample-size (SSS) problem — within-class scatter matrix singular when d > n — is the canonical criticism, documented across two decades: "it often suffers from the small sample size" (dual-space LDA, CVPR 2004) [71] and in regularization overviews (Lu & Platani) [72]. Friedman's classic RDA paper shows unregularized LDA "appears to completely collapse" at small N while regularized variants degrade gracefully — direct evidence of sensitivity to the regularization choice [70].
  - Curse-of-dimensionality framing is still the motivation in current work (Latent LDA, Pattern Recognition 2024: dimension reduction needed "to mitigate the 'curse of dimensionality'") [74].
  - Gap: I found no 2023+ paper with a literal "Fisherface is dead" claim; the strongest available statement is the Lamarr limitations section plus the implicit abandonment of pixel-space LDA by the 2023+ foundation-model literature [61][64]. A dedicated "Fisherface vs CNN on modern benchmarks" head-to-head from 2023+ was not located — do not claim one exists.

- **Where classical methods still win:**
  - Linear probes on frozen features are a recognized, publishable evaluation protocol: CLIP's supplementary evidence reports "Fitting a linear classifier on CLIP's features outperforms using the Noisy Student EfficientNet-L2 on 21 out of 27 datasets" [63].
  - DINOv2 (2023, v2 2024) explicitly positions frozen general features that "work across image distributions and tasks without finetuning" and "surpass the best available all-purpose features, OpenCLIP... on most of the benchmarks at image and pixel levels" — meaning simple heads on good features is the reference bar any PCA/LDA variant will be compared against [64].
  - Nearest-class-mean/centroid on large-multimodal-model features is still an active 2025 baseline (ICCV 2025 compares class-centroid to KNN and linear probing) [65]; few-shot linear probing improvements are reported in 2024 sensor literature [66].
  - Where it breaks: these wins are all on **pretrained features**, not raw pixels; on raw CIFAR-10 pixels, PCA/LDA-era accuracy (~low-40s/%-range for eigenface-style pipelines) is far below the linear-probe bar above frozen features — but I could NOT retrieve published, citable numbers for LDA specifically on CIFAR-10/Flowers-102 in this pass. Do not invent numbers; the student should measure them.

- **Existing library support:**
  - scikit-learn 1.9.1 `LinearDiscriminantAnalysis`: solvers `'svd'` ("Does not compute the covariance matrix, therefore this solver is recommended for data with a large number of features"), `'lsqr'`, `'eigen'`; `shrinkage='auto'` uses "automatic shrinkage using the Ledoit-Wolf lemma" but "shrinkage works only with 'lsqr' and 'eigen' solvers"; a `covariance_estimator` parameter accepts custom shrunk estimators (sklearn.covariance also ships LedoitWolf, OAS, ShrunkCovariance, GraphicalLasso); `n_components` is capped at "min(n_classes - 1, n_features)" — the rank limit is enforced by the library itself. sklearn is BSD-3-Clause, so citing/using it as a baseline is unproblematic [62].
  - `sklearn.decomposition.PCA` (svd_solver options incl. randomized/full) and `IncrementalPCA` cover the PCA side; `sklearn.neighbors.NearestCentroid` gives the nearest-class-mean baseline.
  - PyTorch exposes `torch.pca_lowrank` / `torch.svd_lowrank` (randomized low-rank PCA) and `torch.linalg.svd`; I confirmed the docs URL (now at docs.pytorch.org) but the fetch stopped at a 301 redirect, so exact wording of the docstring is unverified this session — treat signature details (`q`, `center`, `niter`) as high-confidence general knowledge, not quoted evidence [73].
  - Implication: a "from-scratch" reimplementation of a 2023+ variant is mostly assembly of eigendecomposition + shrinkage + cross-validation glue; licensing risk lies in copying the authors' official code (check each repo's LICENSE before reuse; many CV papers publish under permissive or non-commercial licenses), not in the math.

- **Reproduction cost facts:**
  - Computed (arithmetic, not measured): full covariance at CIFAR-10 raw-pixel scale is 3072×3072 float64 ≈ 75 MB per matrix; DINOv2 ViT-B features give 768² ≈ 4.7 MB. 32 GB RAM is tractable up to roughly d ≈ 60,000 for a single float64 matrix — memory is never the binding constraint here; the SSS problem (n ≪ d) is.
  - Computed: holding all 50k CIFAR-10 images as float64 raw pixels is ~1.2 GB; as 768-dim features ~0.3 GB.
  - Estimated (explicitly NOT measured): one exact SVD of the 50k×3072 matrix on an i9-13900H is on the order of seconds-to-minutes; feature extraction with a frozen ViT-B on an RTX 4060 fits easily in 8 GB VRAM. No source in this pass reported timings; the student should measure and report these as their own numbers (good "experiment settings" material).
  - Dataset download sizes: commonly stated figures (CIFAR-10 ≈ 170 MB, Tiny-ImageNet ≈ 250 MB, Fashion-MNIST ≈ 30 MB, STL-10 ≈ 2.6 GB, Flowers-102 ≈ 1.2 GB) were NOT verified against official pages within this budget — flag all as unverified estimates.
  - Turnitin/AI-report hygiene: Turnitin's own blog discusses false positives in its AI detection [67]; a 2025 peer-reviewed evaluation states "AI detectors often misclassify human writing as AI-generated and vice versa" [68]; a law-library guide notes reported false-positive rates "vary widely" despite Turnitin's claimed <1% [69]. Practical read: detector scores are unreliable, so the durable protection is genuine paraphrase + citation and original measured results; no credible source here specifies a safe similarity percentage.

- **Unfilled gaps:**
  - No verified 2023+ head-to-head "LDA/Fisherface is obsolete vs deep learning" paper with raw-pixel benchmark numbers; the criticism exists only as scattered limitation statements ([60][61][70–72]) and implicit evidence ([63][64]).
  - MDPI review full text (403-blocked): the third "primary drawback" of classical LDA could not be confirmed verbatim.
  - torch.pca_lowrank docstring details unconfirmed (redirect blocked the second fetch).
  - Dataset download sizes and any measured PCA/LDA runtimes on 2023+ laptop hardware: not sourced; all figures above are labeled computed/estimated accordingly.
  - Turnitin similarity-threshold policy of the student's institution: unknowable from public sources.

## Sources

[60] Qu et al. — A Comprehensive Review on Discriminant Analysis (Processes 12(7):1382, MDPI, 2024) — https://www.mdpi.com/2227-9717/12/7/1382 — accessed 2026-11-16 — Tier: 1 (snippet only; full-text fetch returned 403)
Summary: 2024 review of discriminant analysis variants; enumerates LDA's classical drawbacks including the small sample size problem. Cited 86 times per search metadata.
Key quote: "The classical linear discriminant analysis (LDA) algorithm has three primary drawbacks, i.e., small sample size problem, sensitivity to..."

[61] F. Gawellek (Lamarr Institute) — Linear discriminant analysis (LDA) — https://lamarr-institute.org/blog/lda-dimension-reduction/ — published 2023-04-19, mod. 2025-09-05, accessed 2026-11-16 — Tier: 2
Summary: Research-institute explainer with an explicit "Limits and restrictions" section; skeptical source #1. States LDA fails on overlapping/mixed class clusters and is outlier-sensitive.
Key quotes: "Too few data points can lead to overfitting... outliers can fundamentally distort results."; "LDA does not work well if the centers of different classes overlap or their data points are heavily mixed."

[62] scikit-learn developers — LinearDiscriminantAnalysis — scikit-learn 1.9.1 documentation — https://scikit-learn.org/stable/modules/generated/sklearn.discriminant_analysis.LinearDiscriminantAnalysis.html — accessed 2026-11-16 — Tier: 1
Summary: Official docs: three solvers, Ledoit-Wolf auto-shrinkage (lsqr/eigen only), custom covariance estimators, C−1 rank cap. Matches the student's sklearn 1.9 environment; BSD-licensed.
Key quotes: "'svd'... Does not compute the covariance matrix, therefore this solver is recommended for data with a large number of features."; "shrinkage works only with 'lsqr' and 'eigen' solvers."; "n_components (<= min(n_classes - 1, n_features))".

[63] Radford et al. — CLIP supplementary, "A. Linear-probe evaluation" (ICML 2021) — https://proceedings.mlr.press/v139/radford21a/radford21a-supp.pdf — accessed 2026-11-16 — Tier: 1
Summary: Standard evidence that a linear classifier on frozen pretrained features beats fine-tuned SOTA CNNs on most transfer benchmarks. Pre-2023 but foundational; still the citation used by 2023+ work.
Key quote: "Fitting a linear classifier on CLIP's features outperforms using the Noisy Student EfficientNet-L2 on 21 out of 27 datasets."

[64] Oquab et al. — DINOv2: Learning Robust Visual Features without Supervision — https://arxiv.org/abs/2304.07193 — v1 2023-04-14, v2 2024-02-02, accessed 2026-11-16 — Tier: 1
Summary: Meta AI foundation-model paper; establishes no-finetuning frozen-feature evaluation as the modern norm against which any classical head must be judged in 2023+.
Key quote: features "work across image distributions and tasks without finetuning"; models "surpass the best available all-purpose features, OpenCLIP... on most of the benchmarks at image and pixel levels."

[65] Mitra et al. — Enhancing Few-Shot Vision-Language Classification with Large Multimodal Model Features (ICCV 2025) — https://openaccess.thecvf.com/content/ICCV2025/papers/Mitra_Enhancing_Few-Shot_Vision-Language_Classification_with_Large_Multimodal_Model_Features_ICCV_2025_paper.pdf — accessed 2026-11-16 — Tier: 1
Summary: 2025 peer-reviewed evidence that class-centroid (nearest-class-mean) classification on frozen large-model features remains a live, compared-to baseline alongside KNN and linear probing.
Key quote: "we compare our class centroid classification approach to k-nearest neighbors (KNN) and linear probing."

[66] Kato et al. — Proto-Adapter: Efficient Training-Free CLIP-Adapter for Few-Shot Learning (Sensors 24(11):3624, 2024) — https://www.mdpi.com/1424-8220/24/11/3624 — accessed 2026-11-16 — Tier: 1
Summary: Reports that "linear probing with few-shot data can improve classification performance" on CLIP features; supports the "simple heads are competitive" claim in 2023+ literature.

[67] Turnitin — Understanding false positives in Turnitin AI detection — https://www.turnitin.com/blog/understanding-false-positives-within-our-ai-writing-detection-capabilities — 2023-03-16, accessed 2026-11-16 — Tier: 2 (vendor primary source; self-interested)
Summary: Turnitin's own acknowledgment that its AI-writing detector produces false positives and guidance on handling them. Useful for arguing detector scores are not decisive evidence.

[68] Deep, P.D. et al. — Evaluating the Effectiveness and Ethical Implications of AI Detectors (Information 16(10):905, MDPI, 2025) — https://www.mdpi.com/2078-2489/16/10/905 — accessed 2026-11-16 — Tier: 1
Summary: Peer-reviewed 2025 evaluation of AI detectors including false-positive/false-negative behavior.
Key quote: "AI detectors often misclassify human writing as AI-generated and vice versa."

[69] USD Law Library — Generative AI Detection Tools: The Problems with AI Detectors — https://lawlibguides.sandiego.edu/c.php?g=1443311&p=10721367 — accessed 2026-11-16 — Tier: 2
Summary: Aggregates studies of detector error rates; notes Turnitin previously claimed "<1%" false-positive rate "though a later study" disputes it.

[70] J. Friedman — Regularized Discriminant Analysis (JASA 1989; PKU-hosted PDF) — https://math.pku.edu.cn/teachers/ganr/course/pr/paper/regularized%20discriminant%20analysis.pdf — accessed 2026-11-16 — Tier: 1 (classic, pre-2023)
Summary: The origin citation for shrinkage-regularized DA and for LDA collapse in small samples.
Key quote: "When the sample size is reduced to N = 19 the performance of RDA seems to be degraded surprisingly little, whereas LDA appears to completely collapse."

[71] X.-S. Wang, X. Tang — Dual-space linear discriminant analysis for face recognition (CVPR 2004) — https://www.ee.cuhk.edu.hk/~xgwang/papers/wangTcvpr04_dualspace.pdf — accessed 2026-11-16 — Tier: 1 (classic, pre-2023)
Summary: Canonical statement of LDA's SSS pathology in face recognition, motivating a whole sub-literature of fixes.
Key quote: LDA "often suffers from the small sample size" problem.

[72] J. Lu, K.N. Platani et al. — Regularized Discriminant Analysis for the Small Sample Size Problem (Pattern Recognit. Lett.) — https://www.dsp.toronto.edu/juwei/Publication/RD_QDA_PRL.pdf — accessed 2026-11-16 — Tier: 1
Summary: Shows regularization as the standard remedy for SSS; also documents that QDA needs n ≫ d, reinforcing dimension ceilings.

[73] PyTorch team — torch.pca_lowrank — https://docs.pytorch.org/docs/stable/generated/torch.pca_lowrank.html — accessed 2026-11-16 — Tier: 1 (URL verified via redirect; docstring body not captured this session)
Summary: Built-in randomized low-rank PCA (params q, center, niter per standard API). Flagged: exact wording unverified — re-fetch before quoting in the report.

[74] J. Zhou et al. — Latent Linear Discriminant Analysis for feature extraction (Pattern Recognition, 2024) — https://www.sciencedirect.com/science/article/abs/pii/S0031320323009159 — accessed 2026-11-16 — Tier: 1
Summary: Evidence LDA research is still active in top venues in 2024, motivated by the curse of dimensionality; useful both as a candidate-style citation and as proof the "classical = dead" narrative is overstated.