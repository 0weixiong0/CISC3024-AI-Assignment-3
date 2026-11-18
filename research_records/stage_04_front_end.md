# Stage 4 — the front end (HTML demo), issued 2026-11-18

Status: **delivered and verified, awaiting the supervisor's acceptance.** Released by U009 item 3
("Stage 4 前端继续"), shaped by U010 item 4 (chart contract and the split-labelled new blocks) and
re-formed by U011 (a demo, not a second report). Files: `webapp/index.html`, `webapp/data.js`,
`webapp/demo.js`, `webapp/demo_meta.json`, generators `src/export_results.py` and `src/export_demo.py`.

## 1. Form, and what the visitor does first

`webapp/index.html` opens on the **Instrument** tab. The first action is to move the `K` slider, or to
click a specimen in the image wall; everything else on that screen responds to those two controls plus
the regime and method chips. Four tabs:

| Tab | The action | What changes |
| --- | --- | --- |
| Instrument | pick regime (ORL raw pixels / CIFAR-100 / Tiny ImageNet × ResNet-18 / DINOv2), pick method, drag `K`, click a specimen row | accuracy readout with its split label, growth curve with the test diamonds, per-direction Fisher ratios µ, the 24 × 24 corner of `U′U`, the two-direction scatter of the specimens, class-rank-by-`K`, and in the raw-pixel regime the directions themselves as pictures (112 × 92) |
| Noise control | toggle clean / corrupted | the same test images with σ = 0.08 gaussian noise, the four arms' before/after bars, the deficit against the best baseline in each column, and what the control does and does not license |
| Dimension ladder | read one chart | accuracy and cap-rank span against cap / M at fixed classes and fixed rows per class, with the withdrawn first run named on the page |
| Tables & receipts | nothing | the report's own tables, the gate counts, the screening ledger, the controls ruled out, and the artefact plus checksum behind each number |

**What is computed where.** The page does not fit anything in the browser: every arm's basis is refitted
by `src/export_demo.py` with the same solvers the study used (`src/golda.py`), and the page exports the
consequences — specimen coordinates, per-direction µ, the Gram corner, class ranks by `K`, the direction
and specimen images, the corrupted thumbnails. A dense eigensolve at M = 10,304 costs ~220 s per direction
in Python (`stage_03a` §7), so in-browser training is not on the table; the interaction is over real
fitted quantities, navigated live, and each read-out says which head produced it (1-NN for the raw-pixel
regime, the C4 logistic head for the feature pairs, nearest-class-mean for the per-specimen rank).

## 2. Gates

* `python src/export_results.py` — **34/34**, refuses to write `data.js` on any failure. Added this
  stage: the two released controls must be present; the OOD control's clean column must reproduce
  `stage_03b` §3.1 arm by arm **read from the artefact**, not from the probe's own claim; severity must be
  labelled "not swept"; the ladder's four rungs must ascend in M at C = 40; and **the page's inline script
  must parse under `node --check`** — a missing parenthesis had silently killed the whole script with no
  console message, which is why that gate exists.
* `python tests/test_parity.py` — **11/11 gated, 18/18 reported**, GATE OPEN. The evidence chain is two
  logs: `runs/parity/parity_rerun_stdout.txt` (03:41, after `tests/test_parity.py` began reading the
  constants) and `runs/parity/parity_after_readpgm_stdout.txt` (after the loader assertion of §3.1 was
  added). `runs/parity_after_orlfix_stdout.txt` (02:58) is **pre-test-fix** — its M0 line still prints the
  old geometry — and is cited nowhere.
* Browser: Playwright at 1440 and 420 px, all four tabs — no `pageerror`, no empty tab, and at 420 px
  `document.documentElement.scrollWidth === 420` (the phone check is measured, not inferred).

## 3. Corrections this stage produced

1. **`src/orl.py` had the image width and height swapped** (`IMG_H, IMG_W = 92, 112`; a PGM header writes
   width first, so ORL is 112 rows × 92 columns). The loader always reshaped from the parsed header, so the
   10,304-d vectors and every measured accuracy are unaffected. Two consumers read the constants: the
   front end's pictures (faces rendered as horizontal stripes) and `src/probe_orl512.py`'s box-average,
   which is why the ORL dimension ladder's first run reported a −11.75 / −8.25 / −0.50 / 0.00 reversal.
   Re-measured after the fix: **−0.50 / 0.00 / +3.00 / 0.00** points, no trend with cap/M; parity at
   M = 512 unchanged. Full write-up in `stage_03b` §8 and `wp7_cross_regime_synthesis.md` §6; the withdrawn
   artefact stays at `runs/orl512/` for provenance. `data/orl/manifest.json` and the two MVP manifests now
   state the geometry as 92 columns × 112 rows (the manifests' `image` field became
   `{height: 112, width: 92}`, with a label-correction note saying no measured value moved), and the
   ladder's `dim_rule` reads "ORL PGM 92 columns x 112 rows flattened".
   **Where the gate actually lives.** `tests/test_parity.py`'s M0 line is a shape-arithmetic assertion —
   `reshape(...).shape == (...)` is true whenever the reshape succeeds, so it can never catch a swapped
   pair, and the report must not describe it as a geometry check. The real gate is now in
   `src/orl.py::_read_pgm`: after parsing the header it asserts `(height, width) == (IMG_H, IMG_W)` and
   raises with both readings in the message. Verified as discriminating: loading a real PGM with the
   pre-fix constants set raises `PGM header says 92 columns x 112 rows, but IMG_H/IMG_W say 92 x 112`,
   while the corrected pair returns `(112, 92)`.
2. **Two CSS cascade bugs broke the phone layout.** `.pane.wide{grid-column:span 2}` and
   `.split2{grid-template-columns:1fr 1fr}` were written *after* `@media(max-width:54rem)`, so at equal
   specificity the mobile overrides lost; the surviving `span 2` created an implicit column that crushed
   the first column to 31 px. Base rules moved above the media queries, `.split2>div` got `min-width:0`,
   and wide tables are wrapped in `.tw` horizontal scrollers after each draw.
3. **The noise tab printed `NaN`** for the GO-LDA-minus-best-baseline deficit because `ood_block()` did not
   pass that field through. It now shows −2.30 → −0.51 (shrinkage → ridge) on ResNet-18 and −1.46 → −2.59
   (ridge → shrinkage) on DINOv2, matching `stage_03b` §8.1, and names which baseline is best in each column.
4. **The direction caption said "near-orthogonal, not equal"** while showing ORL, where the two arms span
   the same subspace to 2e-6°. It now branches on the exported span.

## 4. Cost ledger for Stage 5

Every row is a measured wall clock with the place it lives in. **Rule carried over from U009: quote a cost
from the measured seconds of that phase, never from an extrapolation of a different phase.**

| Work | Measured | Where the number lives |
| --- | --- | --- |
| ORL raw-pixel MVP | **1,061 s = 17 min 41 s**, peak RSS 2,901 MB, **2,880 per-fold rows** written (7 δ values including `n/a`, 9 `K` values including 10,304) | `runs/mvp_orl/timing.json`, `runs/mvp_orl/accuracy_rows.csv`, `manifest.json` `rows_written` |
| ORL supplementary, 4 train / 6 test per subject | **42.5 s** | `runs/mvp_orl_small_sample/timing.json` |
| Frozen feature extraction, all four pairs (M1.5) | **18.2 min** — ResNet-18 Tiny 4.2 / CIFAR 1.9 min, DINOv2 Tiny 8.1 / CIFAR 4.0 min | `data/features/manifest.json`, `stage_02` §7 |
| M2 sweep + refit, CIFAR-100 both backbones | 4,923 s | `runs/m2_cifar_stdout.txt` |
| M2 sweep + refit, Tiny ImageNet both backbones | 4,748 s | `runs/m2_tiny_stdout.txt`, `timing.json` |
| M2 Tiny ImageNet 5-fold CV (invocation 3) | 2,625.2 s = 43.8 min | `runs/m2_matrix/manifest.json` |
| **M2 all-in** | productive **12,296 s = 3.42 h**; **4.00 h** counting the crashed attempt (~1,570 s) and the aborted duplicate CV process (~530 s) | `stage_03b` §2 |
| Cap-gap probe | not recorded as a single field; per-arm fit seconds are in the artefact (GO at cap 9.9 s, classic-eig 3.9 s) | `runs/m2_matrix/probe_cap_gap.json` |
| Head-control probe | not recorded as a single field | `runs/m2_matrix/probe_head_control.json` |
| **Out-of-distribution control (U010 option A)** | **915 s = 15.3 min**. Main components 709 s — re-solving the pencils 266 + 241 s at ResNet-18/512 and 91 + 49 s at DINOv2/384, plus 19 + 43 s of feature re-extraction; the remaining **206 s is not itemised** in the artefact (image loading, scoring and head fits) | `runs/m2_matrix/probe_ood.json` `total_seconds` |
| ORL dimension ladder, first run (**withdrawn**, transposed pixel grid) | 427 s | `runs/orl512/orl512_ladder.json` |
| ORL dimension ladder, corrected re-run | **392.4 s** | `runs/orl512_fix/orl512_ladder.json` |
| Demo export, full (five blocks refitted + static controls) | 2,039.4 s = 34 min | `runs/demo_export_stdout.txt` |
| Demo export, one block repaired (`--pairs orl`) | 9–13 s | `webapp/demo_meta.json` |
| Parity gate | **89 s** (the supervisor's 03:41 re-run, `runs/parity/parity_rerun_stdout.txt`) and **121 s** (the run after the loader assertion, `runs/parity/parity_after_readpgm_stdout.txt`, start-to-last-write measured); `parity_report.json` carries no per-check seconds, so no phase split is claimed | `runs/parity/parity_report.json` |

**The OOD control's cost must be carried as 15.3 min (915 s) in the report.** The "~3 min" figure that
appeared in WP7 §7 and in U010's ruling was my estimate and it was wrong: it assumed the fitted projections
could be reused, but M2 stored accuracies rather than bases, so both pairs' pencils had to be re-solved.
The estimate may be mentioned only as that correction, never as the cost.

## 5. Repository and Pages (U014 order change, U015 exclusions)

Brief item (6) is delivered: **https://0weixiong0.github.io/CISC3024-AI-Assignment-3/** — the same four
tabs, served from the `gh-pages` branch.

| What | Value |
| --- | --- |
| Repository | `0weixiong0/CISC3024-AI-Assignment-3`, **public** (U015) |
| Source branch | `main`. The code the report cites is the initial commit **`e43edfa`** — 131 files, every solver, driver, probe and gate. The documentation commits that follow (`23e5216` README, `5bcd940` parity citation, `fbb0982` and `60260f3` counts and wording — **through `60260f3`**) are history rather than citations, and nothing outside this table points at them; the commit carrying this very sentence is later than `60260f3` by construction, which is exactly why the rule below reads HEAD at submission instead of pinning it here. **The rule is scoped to the Stage-5 report only:** the report cites the live URL, the site tree `a48a97b`, the code commit `e43edfa`, and `main`'s HEAD read with `git rev-parse main` at submission time — because a record cannot carry the hash of the commit that carries it |
| Site branch | `gh-pages`, HEAD `a48a97bf324bc9416240587d65405b7733377f5f` — `index.html`, `data.js`, `demo.js`, `demo_meta.json` at the root |
| Tracked | **132 files** in `main` at `60260f3` — `runs/` 97, `research_records/` 15, `src/` 12, `webapp/` 4, `tests/` 1, root 3 (`README.md`, `.gitignore`, `.gitattributes`). **154 tree entries** if directories are counted too (`git ls-tree -r -t`): `runs/` 111, `research_records/` 18, `src/` 12, `webapp/` 4, `tests/` 1, root 8 — the extra 22 are directories, not files. The initial commit `e43edfa` held 131 files / 153 entries; the README made it 132 / 154. Largest blob 4.5 MB (`webapp/demo.js`) |
| Not tracked (U015) | course files (`AIassign3.pdf`, `Agent_coding.pptx`, `Report Template.docx`), `_rev.py`, `research_records/conversation_log.md`, `runs/conversation_log_backup_before_dedup.md`, `data/` (986 MB) |
| Also excluded, with the reason on disk | the three pre-fix parity logs and a third-party accepted manuscript — see `runs/parity/README.md` and the README's closing section |

Live-site verification, not a local render: Playwright against the URL reports both globals present, five
demo blocks, `static = ood,ladder`, the ORL read-out "13 / 40", the noise / ladder / tables tabs non-empty,
and zero `pageerror`.

The dialogue record stays a **report deliverable** submitted with the Word file rather than repository
content, so Stage 5 must attach it and the report must not link to it inside the public repository.

## 6. What Stage 5 draws from this stage

Brief item (4) experiment settings and results → `stage_03b` §3–§5 and §8.1, `wp7` §3–§7. Brief item (5)
what we learnt → `wp7` §8's three sentences plus `wp7` §6's withdrawal, which is the strongest single lesson
in the project: a constant that "only affects the pictures" was also feeding a measurement. Brief item (3)
how the AI implemented it → this file §1–§3 and the command list in `webapp/data.js` `commands`. Brief item
(6) the webpage link → **delivered**, `https://0weixiong0.github.io/CISC3024-AI-Assignment-3/` (§5 above);
the report cites that URL together with the `main` commit it points at, and attaches the dialogue record
itself rather than linking to it in the public repository.
