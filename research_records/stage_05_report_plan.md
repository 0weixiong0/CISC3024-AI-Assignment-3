# Stage 5 — report framework (for approval before any prose is drafted)

Issued 2026-11-19. Deliverable: a Word report on `Report Template.docx`, submitted via UMMoodle by
**2026-11-23**, Turnitin-checked. This file fixes the skeleton, the evidence behind each section, the
formatting traps and the citation block; the prose is written only after it is approved.

## 1. What the brief requires, and which section answers it

The brief's six numbered items are the report's spine — the outline's stage 5 says the same thing in
different words, so the brief wins where they differ. **Seven sections, not six (U018 reconciliation):**
the shell built in §10 has seven content H1 because A1 and A2 both open with an Introduction, and U017
put the AI-use and responsibility statement there. Introduction is therefore a section of its own that
answers no single brief item; the six items map onto sections 2–7.

| Report section | Answers | Built from | Draft budget (prose words, see §9) |
| --- | --- | --- | --- |
| 1. Introduction and Human-AI Workflow | the outline's stage-5 framing, plus U017's AI-responsibility placement | `stage_00_preflight.md`, `stage_02_design_and_plan.md` §1–§4, `stage_04_front_end.md` §1 | ~350 |
| 2. AI-Assisted Literature Search and Algorithm Selection | brief (1) | `stage_01_search_protocol.md` §1–§11 (20 screened candidates, the weights, the 16-row correction table, the wave-1/wave-2 source ledger), `stage_01_candidate_scoring.md` §5 | ~900 + 1 table |
| 3. Algorithm Description and Task Adaptation | brief (2) | `research_records/sources/golda_arXiv2305.14568_notes.md` (eq. (23), (37)–(41) verbatim), `wp7` §2 | ~700 + 2 display equations |
| 4. AI-Assisted Implementation and Verification | brief (3) | `stage_02_design_and_plan.md` (the nine-step loop, H1–H3 fixed first, the risk table), `stage_03a` §5–§6 (deviations), `stage_04_front_end.md` §1–§3, `webapp/data.js` `commands` | ~1,100 + 1 code-path table |
| 5. Experimental Settings, Results and Discussion | brief (4) | `stage_03a` (raw-pixel scale), `stage_03b` §2–§5 and §8–§8.1 (feature scale, the two released controls), `wp7` §3–§7 | ~1,400 + 4 tables + 2 figures |
| 6. Interactive Visualisation and Source-Code Availability | brief (5) framing and (6) | `stage_04_front_end.md` §1–§3, the live URL and the commits in §3 below | ~250 + the link block |
| 7. Lessons Learned and Conclusion | brief (5) | `wp7` §8's three sentences, plus the two process lessons in §4 below | ~600 |
| References | APA 7 | the entries in `stage_01_search_protocol.md` and the sources cited above | 14–16 entries |

Total ≈ **5,300 prose words** including the Introduction. **The ceiling is 5,900 prose words (U021):**
the brief sets no page or word limit, so 4,700 was this project's own number, and U021 restates it as
5,900 — the 5,017 already drafted plus §6 and §7 at 850, leaving 33 words of headroom, about 6,400 by
Word's counter against A2's delivered 9,593 in 54 pages. **Trim order stays as U020 restated U017:**
compress §1 and §3 first, §2's 234-word overage is optional, and **§4 and §5 are not touched** — the
sentence that put §4 next in line is withdrawn because it contradicted the ruling it summarised.

## 2. Formatting requirements, with the traps already known

* **Cover page unchanged** — every placeholder on the template's first page stays exactly as shipped.
* **TOC and heading formatting identical to A1/A2** — but the template trap applies: assigning the
  paragraph style is not enough, because the template's own example headings carry **direct run
  formatting** (Times New Roman 12 pt) that overrides the style definitions (Calibri Light 16/20 pt).
  So each heading gets the style **and** the direct run properties, then `document.xml` is re-read to
  confirm. The style ids and the untouched placeholders are inventoried in `stage_00_preflight.md`.
* **APA 7** for in-text citations and the reference list, with the template's `EndNoteBibliography`
  paragraph style for entries.
* Verification is scripted, not eyeballed: `src/audit_docx.py`, `src/audit_layout.py`,
  `src/apply_word_fixes.py`, `src/wordify_equations.py` are reused from A2, which is where A2's
  formatting failures were caught. A2's lesson is that the report format, not the content, was the
  weak deliverable — so the audit runs after every editing pass, not once at the end.
* Prose goes through the anti-slop writing pipeline (one engine plus the project's own overrides), and
  the no-self-rating / no-AI-tell rules apply to the wording.

## 3. The citation block for brief item (6)

| Object | Value |
| --- | --- |
| Live front end | `https://0weixiong0.github.io/CISC3024-AI-Assignment-3/` |
| Public repository | `https://github.com/0weixiong0/CISC3024-AI-Assignment-3` |
| Site tree | `gh-pages` `a48a97b` |
| Code commit | `e43edfa` (131 files: every solver, driver, probe and gate) |
| `main` HEAD | **read with `git rev-parse main` at submission time** and written in then — a record cannot name the commit carrying it |
| Published set | 132 files / 154 tree entries at `60260f3` (the two units are the same tree; 22 entries are directories) |
| Dialogue record | attached to the submission as a separate file; the public repository deliberately does not contain `research_records/conversation_log.md` |

## 4. The two lessons §5 carries, stated as evidence rather than as morals

1. **A constant that looked like a rendering detail was feeding a measurement.** `IMG_H`/`IMG_W` were
   swapped, which left every accuracy untouched (the loader reshaped from the parsed header) yet made the
   ORL dimension ladder box-average a sheared raster. Its first reading — a −11.75 / −8.25 / −0.50 / 0.00
   reversal that "broke" the rows-per-class versus cap/M confound — was withdrawn after the fix and the
   corrected run (**−0.50 / 0.00 / +3.00 / 0.00**) removed the effect the claim rested on. The report
   presents this as the strongest process finding: the gate that should have caught it was a tautology
   (`reshape(...).shape == (...)`), and the real gate is now the header assertion in `_read_pgm`.
2. **The published advantage did not survive the move out of the paper's regime, and the honest framing is
   scope, not refutation.** H3 (orthogonality) reproduces to ~1e-14 and classic LDA's directions do not
   (0.19–0.25); H2's mechanism reproduces (GO's own curve rises past `C − 1`) while its claim does not; the
   paper's own 512-dimensional evidence is 4- and 5-class rows, so `C = 100/200` sits outside it.
   Tiny × DINOv2 is worded as "the five-fold ranges overlap almost entirely", never as a fourth
   indistinguishable pair, because `cv_summary.csv` stores only mean/SD/min/max.

## 5. Figures, and the page-image rule for anything cited by page number

Every claim that quotes a page of the paper carries that page's rendered image as a figure or appendix
item (the supervisor's standing rule). The list is fixed now so the drafting does not discover it later:

| Claim to be cited | Source | Page image needed |
| --- | --- | --- |
| eq. (37) constrains ordinary Euclidean orthogonality | arXiv:2305.14568v1 | the page carrying eq. (37) |
| Sec. VI-B claims GO-LDA outperforms classic LDA at `Ω4 = C − 1` | same | that page |
| Table II rows quoted (ORL, LFW, BrainTumor, DeepDrid) | same | the Table II page |
| README-vs-paper cell differences (14 of 18 PCA, 19 of 72 overall) | C4 repository README + paper Tables I/II/III | both, side by side for at least one disputed cell |
| ImageNet-C gaussian severity 1 ⇒ σ = 0.08 | Hendrycks & Dietterich 2019, arXiv:1903.12261 + `corruptions.py` | the corruptions table and the code line — **the paper carries no σ-versus-severity table** (read from the downloaded PDF: its only "Gaussian Noise" numbers are mCE percentages), so `figure_04` renders p4, the paper's own description of the corruption, and the code line stays outstanding until `corruptions.py` is released |

**Delivered 2026-11-19** (U019 release of the three sources). `src/render_page_images.py` writes six PNGs
at 200 dpi into `report_assets/` plus `figure_manifest.json`, which records for each figure the source file,
the page, the region clipped and the two caption lines the builder will place above it:

| Figure | From | What it shows |
| --- | --- | --- |
| figure_01 | GO-LDA p6, full page | equations (37) **and (38)** - the Euclidean-orthogonality constraint and the deflated pencil that answers it |
| figure_02 | GO-LDA p11, full page | the accuracy claim ahead of Table 2. **Caption corrected after U020:** the page says the GO-LDA directions "achieve significantly better results than that of the classic-LDA", and the "after the third direction" clause belongs to the *separate* comparison against PCA's principal directions - the first draft of the caption merged the two |
| figure_03 | GO-LDA p12, caption + table crop | Table 2, the nine-data-set subspace MCA rows including ORL 40/400/10304 at Ω39 and Ω50 |
| figure_04 | ImageNet-C p4, full page | "Common Corruptions. The first corruption type is Gaussian noise." - the description page is the right evidence for using that corruption type; the σ number itself is figure_07, not this page |
| figure_05 | C4 paper p6, caption + table crop | Table I, CIFAR-100 per backbone - the paper side of the diff (PCA row 65.07 / 69.28 / 64.62 / 69.77 / 76.66 / 80.60). **d = 99 carries an exception the caption must keep:** the table's own note says all reduction methods project to d = 99 *except* RDA and RDA+SMD, which use 99 + k |
| figure_06 | cached `c4_README.md`, lines 77-83 rendered with their own line numbers | the README side of the same six configurations (PCA row 65.07 / 69.14 / 64.65 / 69.77 / 78.05 / 81.55). **19 of 72 is the overall count across all three dataset tables**, not the CIFAR-100 table shown here, where the disagreement is 4 of 6 PCA cells plus 2 DSB cells |
| figure_07 | `corruptions.py` lines 122-126, pinned at commit `712bfcd` of `github.com/hendrycks/robustness` (path `ImageNet-C/imagenet_c/imagenet_c/corruptions.py`, blob `f0bf2d4`) | the severity list `c = [.08, .12, 0.18, 0.26, 0.38][severity - 1]` - where σ = 0.08 for severity 1 actually comes from, since the paper has no σ-versus-severity table |

The four disagreeing cells are readable across figures 05 and 06 without re-typing them. Sources live in
`research_records/retrieval_cache/`, which `.gitignore` now covers as a directory - the previous rule named
only the DLR manuscript, so a `git add -A` would have published the three newly released PDFs and the
README. **One discrepancy to settle:** `research_records/retrieval_cache/rsspca_plosone2025_table3.png` is
still tracked from an earlier commit, so ignoring the directory does not remove it from the published set;
deleting it from `main` is the supervisor's call, not a silent change.

Report figures from our own runs: the growth curve per feature pair (hold-out curves plus test markers,
split-labelled), and the ORL direction images at `K = 1` versus the classic pencil's first direction.

### Exhibits as built (step 3, 2026-11-20)

Numbering is a Word SEQ field on the caption, assigned by `src/build_report.py` in the order
`src/report_exhibits.py` places the exhibits, and every in-text mention is a REF field to a bookmark around that
caption. The manifest's own `report_label` says explicitly that the asset names carry no report number.

| Report label | Asset or source | Section and heading it sits under |
| --- | --- | --- |
| Figure 1 | figure_01.png, GO-LDA p6 (equations 37 and 38) | §3, GO-LDA's deflated eigensolve |
| Figure 2 | figure_03.png, GO-LDA p12 (Table 2, the face-data rows) | §3, Baselines and the protocol adapted to this study |
| Figure 3 | figure_02.png, GO-LDA p11 (the accuracy claim) | §3, Hypotheses fixed before implementation |
| Figure 4 | figure_05.png, C4 paper p6 (Table I) | §5, Datasets, features and the evaluation protocol |
| Figure 5 | figure_06.png, C4 README lines 75-82 | §5, same heading |
| Figure 6 | figure_09.png, own run: ORL fold-0 first directions | §5, Small-scale feasibility run |
| Figure 7 | figure_08.png, own run: growth curves and test points | §5, Main results and the hypothesis verdicts |
| Figure 8 | figure_04.png, ImageNet-C p4 (the Gaussian description) | §5, Two controls |
| Figure 9 | figure_07.png, corruption source lines 122-126 at commit 712bfcd | §5, Two controls |
| Table 1 | experiment settings per regime, from the two diagnostics files | §5, Datasets, features and the evaluation protocol |
| Table 2 | test accuracy, selection and five-fold spread, from selection.csv and cv_summary.csv | §5, Main results |
| Table 3 | the corruption control arm by arm, from probe_ood.json | §5, Two controls |
| Table 4 | the pixel-dimension ladder, from orl512_ladder.json | §5, Two controls |

Three layout rules came out of the first pass and are now enforced by the build rather than by hand: caption
paragraphs carry keepNext so a caption cannot be left behind by its object; table captions carry a page break so
a table cannot start in the middle of a page and split its first row; and figures are capped at 6.4 in tall,
which is the template's 9.0 in text area less the room two caption lines need. Table captions run to a third
line naming the artefact the rows were read from - a deliberate deviation from the two-line form U018 set for
the figures, because a table with no source named is a table nobody can re-derive.

## 6. Cost table

Lifted from `stage_04_front_end.md` §4 unchanged, including the rule that the OOD control's cost is
**915 s = 15.3 min** (main components 709 s, remaining 206 s not itemised) and that the earlier "~3 min"
estimate appears only as the correction, never as the cost.

## 7. Order of work once this is approved

1. Build the section shells in the template with the real styles and direct run properties, then run the
   audit scripts before any text exists.
2. Draft §2 and §4 first (the two sections whose content is already fixed by the records), then §1, §3, §5.
3. Insert tables and figures with numbered captions and cross-references as fields, not typed numbers.
4. Write the APA 7 reference list; run the bibliography check (every in-text citation has an entry and
   every entry is cited).
5. Attach the dialogue record; re-read `git rev-parse main` and write the submission-time commit into §3.
6. Final pass: the audit scripts, the brief-item coverage check against this table, and a Turnitin-aware
   read of the wording.

## 8. Rulings recorded (U017, 2026-11-19) — framework approved

* **Framework passes** as written.
* **§6 link block follows A2's form — both addresses**, in A2's own wording pattern:
  "The source page is `https://github.com/0weixiong0/CISC3024-AI-Assignment-3`" and
  "The live page is `https://0weixiong0.github.io/CISC3024-AI-Assignment-3/`".
* **~4,700 words accepted.** If it runs long, compress §1 and §3 first; **§4 and §5 are not touched.** (The number, not the trim order, was superseded by U021: the ceiling is now 5,900 prose words.)
* **A2's four lessons are execution rules, not advice** — see §2 and §5 above, and §7 below:
  `audit_docx.py` and `audit_layout.py` run after *every* editing pass; layout is judged by reading the
  exported PDF; every number points back to an artefact; anything cited by paper page number carries that
  page's rendered image.
* **The front end is linked, not copied** — the report points at the live instrument and does not
  reproduce its tables or read-outs as report content.
* **No Acknowledgements section** (and neither A1 nor A2 has one, so this matches the precedent as well as
  the ruling). The AI-use and responsibility statement goes in **§1**.

## 9. The A1/A2 baseline this report is built to

Measured from the two delivered documents, not from memory:

| Item | A1 | A2 | A3 follows |
| --- | --- | --- | --- |
| File at project root | `CISC3024_AI_Assignment_1_Report.docx` + same-name PDF (25 pp) | `CISC3024_AI_Assignment_2_Report.docx` + PDF (54 pp) | `CISC3024_AI_Assignment_3_Report.docx` + PDF |
| Structure | cover → TOC (Heading 1) → 7 unnumbered H1 → References | same skeleton | same, mapped in §1 |
| Body words | see the unit table below | see the unit table below | 5,900 prose words over sections 1–7, captions counted separately |
| AI-use statement | disclaimer sentence inside the workflow section | §1.2 "Human Supervision and AI Responsibilities", opening "The student acted as supervisor and the agent as researcher, implementer and experimenter." | §1, A2's placement with A3's own evidence |
| Link block | "Source code:" + "Live demo:" lines | "The source page is …" + "The live page is …" | A2's wording |
| References | APA 7, `EndNote Bibliography` style, plain paragraphs (no fields), 6 entries | same, 14 entries | APA 7 plain paragraphs, `EndNote Bibliography` |
| Exhibit labels | two typed lines above the object: `Figure N` then the italic description | same (17 figures, 11 tables) | same two-line form — `audit_docx.py`'s caption regex depends on it |
| Equations | — | `wordify_equations.py` abandoned: Word's LaTeX-to-math fires on typing, not on programmatic `BuildUp()`, so command names stayed literal | real Unicode symbols in plain text (μ, Σ, ‖·‖), as accepted for A2 |
| Report in the public repo | no | no | **no** — the docx/pdf are UMMoodle submissions, so they are gitignored |

**Word counts in four units, all measured on 2026-11-19 rather than quoted from memory** (U018). The
figures this file first carried — ~2,906 for A1 and ~8,011 for A2 — were labelled "body words" but did not
match any of the four measurements below, so they are withdrawn.

| Unit | How it is counted | A1 | A2 | A3, after step 3 (2026-11-20) |
| --- | --- | --- | --- | --- |
| Word's own count | COM `ComputeStatistics(wdStatisticWords)` on the docx | 3,474 | 9,593 | 8,085 |
| PDF full-text words | pymupdf over the exported PDF - includes tables, the contents page and the cover | 3,528 | 9,792 | 8,085 |
| docx paragraph words | `python-docx`, every paragraph in `doc.paragraphs`, tables excluded | 3,088 | 8,221 | 7,052 |
| **prose words** | the unit A2's own record used (`stage_05_report_feasibility.md` §4), **excluding exhibit captions** | 3,024 | 8,286 | **6,478** |
| exhibit caption words | the two or three lines above each table and figure, counted apart because they are labels, not argument | - | - | 391 |
| table words alone | `python-docx` over table cells | 187 | 1,107 | 817 |

The A3 column was re-measured on the 2026-11-20 build, which is the first build with exhibits: 40 PDF pages,
31 headings (8 H1 including References, 23 H2), 4 tables, 9 figures, and §1 through §7 all drafted. The prose
figure is now taken with the caption lines excluded, because step 3 made them a large block of text that is
not argument: 13 captions carry 391 words, and Word's own counter, which sees everything, reads 8,085.

**The ceiling question is open again.** U021 set 5,900 prose words from the arithmetic 5,017 drafted + 850 for
§6/§7 = 5,867. Step 3 then added the C4 comparison paragraph U020 asked for, and §6/§7 came in over their
budget. The drafted prose, measured section by section on this build: §1 300, §2 1,134, §3 742, §4 1,428, §5
1,743, §6 317, §7 780 - **6,444 words**, and 6,478 as the builder reports it because the unit counts the 34
words of the cover line as well. That is 578 over the ceiling, and the three additions since U021's arithmetic
account for it exactly: §6/§7 at 1,097 against a budget of 850 (+247), the C4 paragraph (200), and the thirteen
sentences that cite the exhibits (130: §3 gained 56 words, §5 74).

A2 shipped 8,286 prose words over 54 pages, so the report is not long in absolute terms; what is out of date is
the number rather than the text. Either the ceiling moves to about 6,500, or the trim runs on §1 and §3, which
together are 1,042 words and would have to lose more than half of both, with §2's 234-word overage taken as
well. Nothing was trimmed on this pass: U021 said §4 and §5 are not touched, and did not authorise cutting §1
and §3 down that far to hit a figure that predates the exhibits. See §11.

**The 5,900 budget is in prose words**, because that is the unit A2's record reported and it is the closest
to "text the reader reads" — it excludes tables, the contents page and the cover. The observed ratios are
Word count ≈ 1.15 × prose words (A1 3,474/3,024 = 1.149; A2 9,593/8,286 = 1.158) and PDF full-text ≈ 1.18 ×
prose words, so the target corresponds to roughly **5,400 by Word's counter** and about 30–35 pages at A2's
density. `src/export_pdf.py` prints Word's count on every build, so the check is mechanical rather than a
guess, and the pass that reports the unit always names it.

## 10. Shell status (step 1 of §7, done 2026-11-19) and step 2 (done the same day)

`src/build_report.py` builds the shell from `Report Template.docx` by cloning the template's own example
paragraphs as formatting prototypes, so the headings carry the direct Times New Roman 12 pt run properties
that the style definitions alone would not give — the trap in §2. The cover and the TOC content control are
untouched; everything after the TOC control is deleted and re-emitted.

* Shell: 7 content H1 + 21 H2 + References = 29 headings; 6 pages, 353 words after `src/export_pdf.py`
  resolved the TOC field through a private Word instance. **Corrected in the U019 round:** the References
  heading had been emitted from the template's `EndNote Bibliography` prototype, so it was not a heading at
  all and the built document had no References section - the audit's "29 headings matched by 29 contents
  entries" only proved the contents page agreed with itself, not that the section list was covered.
  References now uses the Heading 1 prototype; the bibliography prototype is reserved for the entries
  themselves, which are step 4.
* `src/audit_docx.py`: 31 headings matched by 31 contents entries (8 H1 including References, 23 H2), and
  the font census is now `'Times New Roman' 12.0pt: 52` with **no size-less runs**. The 25 "Times New Roman,
  no size" entries the U018 pass reported were runs that inherit their size from the style rather than
  carrying it, and Word re-splits runs when it resolves fields, so `explicit_sizes()` writes the resolved
  value back - in the builder and again after field resolution in `src/export_pdf.py` (88 runs on this
  build). Nothing on the page moved; the census is now a check that can fail. No Chinese, no jargon, no
  exhibit-integrity findings.
  Two findings remain and both are expected at this step: the cover's own template placeholders
  (`CISCXXXX YYYY`, `Your NameXXX, Student No: DDxxxxxx`) and "no URL anywhere" — the URL arrives with §6.
* `src/audit_layout.py`: passes (no exhibits yet). **Extended in the U020 round**, because it had no
  opinion about the contents page: `toc_checks()` now finds the pages carrying dot-leader lines and the
  page where the first section heading starts, and fails if they are the same page or if the body starts
  before the last contents page. On this build it reports `contents pages: [2, 3]  first section page: 4`.
  The underlying fault was real and the audit was blind to it: with 31 resolved entries the contents ran
  onto page 3 and §1 began underneath its last entry. The fix is `w:pageBreakBefore` on the first content
  H1 rather than a break paragraph after the content control - the paragraph version was counted by
  `audit_docx` as a 32nd contents entry, which is how the mismatch surfaced.
* **Cover fill (U018 item 1).** `Builder.fill_cover()` reads `report_assets/cover_values.json` —
  gitignored, so the values the supervisor supplies never enter the repository. It is inert while the file
  is absent; the audit's placeholder finding is the visible signal that the values are still outstanding.

**Step 2 of §7 — §2 and §4 drafted (U019), then §1, §3 and §5 (U020). §6 and §7 are still shells, and step 3 also owes §5's two own-run figures, not only
the seven page images.** The prose lives in `src/report_content.py` in two functions
(`search_sections` for §2, `implementation_sections` for §4), keyed by the builder's exact H1 titles; every
digit in the sentences is interpolated at build time from the run artefacts (`probe_cap_gap.json`,
`diagnostics.json`, the MVP `timing/manifest/diagnostics`, `probe_ood.json`,
`orl512_fix/orl512_ladder.json`, `parity_report.json`) and from the stage records (the ledger row count,
the gate and rubric table rows, the wave counts, the corrections count). Drafted prose, per section: §1 **300**
(~350), §2 **1,134** (~900, trimmable), §3 **686** (~700), §4 **1,428** (~1,100, not to be trimmed per
U017/U020), §5 **1,469** (~1,400, not to be trimmed). The built document: 8 H1 / 23 H2 = 31 headings,
22 PDF pages, Word 5,450, prose 5,017. Both audits re-ran on that pass: `audit_docx` matched 30 headings to 30 TOC entries with no
font/jargon/exhibit findings; `audit_layout` passed (no exhibits yet). The remaining findings are the
expected ones: cover placeholders pending the values (U018 item 1), no URL until §6, no tables until step
3 of §7.

## 10.1 Step 3, delivered 2026-11-20

Four tables and nine figures are in the document with field-numbered captions and field cross-references; §6 and
§7 are drafted; the C4 comparison paragraph U020 asked for is in §5 with both of its pages. The build reports 40
PDF pages, 8,085 words by Word's counter, 6,478 prose words excluding captions, 817 table words, 391 caption
words, 31 headings and 31 contents entries. `audit_docx` finds one issue, the expected one: the cover still
carries the template's placeholders because the values have not arrived. `audit_layout` passes every check,
including TOC pagination, the caption-adjacency rules and exhibit image placement. Two provenance corrections
came out of wiring the exhibits: the README figure's line numbers were being derived from an offset across a
blank line, so the picker now carries each line's own number (the block is lines 75-82, not 77-83), and the
figure manifest no longer claims report numbers for itself.

## 11. What is still open

* **Cover values** - the student's name, student number and date. `src/build_report.py` fills them from
  `report_assets/cover_values.json` the moment that file exists; nothing else waits on it.
* **The 578-word overage** (§9) - either the ceiling moves to about 6,500 prose words, or §1 and §3 are cut to
  roughly half their length with §2's 234 taken as well. U021's 5,900 was arithmetic on a draft that did not yet
  contain §6/§7, the C4 paragraph, the citation sentences or any captions. Awaiting a ruling; nothing was cut
  unilaterally.
* **Two tables this pass did not build** - plan §1 also budgets one table in §2 (the candidate scoring table) and
  a code-path table in §4. U021 named "four tables", which is §5's count, so those two are still open. Both can
  be read from artefacts already on disk: §2's from `stage_01_candidate_scoring.md` §5, §4's from the module list
  in `stage_02_design_and_plan.md`.
* **Trim of §2's 234-word overage** - optional under U021, and now entangled with the ceiling question above.
* **Final read-through** - the brief-item coverage check against §2 of this plan, and a Turnitin-aware pass on
  §6/§7, which have not been read as prose yet.
