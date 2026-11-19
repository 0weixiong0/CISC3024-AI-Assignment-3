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
| 2. AI-Assisted Literature Search and Algorithm Selection (the screening table is built) | brief (1) | `stage_01_search_protocol.md` §1–§11 (20 screened candidates, the weights, the 16-row correction table, the wave-1/wave-2 source ledger), `stage_01_candidate_scoring.md` §5 | ~900 + 1 table |
| 3. Algorithm Description and Task Adaptation | brief (2) | `research_records/sources/golda_arXiv2305.14568_notes.md` (eq. (23), (37)–(41) verbatim), `wp7` §2 | ~700 + 2 display equations |
| 4. AI-Assisted Implementation and Verification (no code-path table: U022 withdrew it, the prose covers brief (3)) | brief (3) | `stage_02_design_and_plan.md` (the nine-step loop, H1–H3 fixed first, the risk table), `stage_03a` §5–§6 (deviations), `stage_04_front_end.md` §1–§3, `webapp/data.js` `commands` | ~1,100 + no table |
| 5. Experimental Settings, Results and Discussion | brief (4) | `stage_03a` (raw-pixel scale), `stage_03b` §2–§5 and §8–§8.1 (feature scale, the two released controls), `wp7` §3–§7 | ~1,400 + 4 tables + 2 figures |
| 6. Interactive Visualisation and Source-Code Availability | brief (5) framing and (6) | `stage_04_front_end.md` §1–§3, the live URL and the commits in §3 below | ~250 + the link block |
| 7. Lessons Learned and Conclusion | brief (5) | `wp7` §8's three sentences, plus the two process lessons in §4 below | ~600 |
| References | APA 7 | the entries in `stage_01_search_protocol.md` and the sources cited above | 14–16 entries |

Total ≈ **5,300 prose words** including the Introduction. **The ceiling is 6,500 prose words (U022, replacing U021's 5,900):**
the brief sets no page or word limit, so 4,700 was this project's own number. U021 moved it to 5,900 and U022
to **6,500 prose words**, measured with exhibit captions and table cells counted separately, and U022 ruled that
this is the last restatement: if the report runs over again the trim runs on **§2, §6 and §7 first, and §4 and
§5 are not touched**. A2 delivered 8,286 prose words over 54 pages, so 6,500 is not a high ceiling - about 6,900
by Word's counter. The earlier sentence that put §4 next in line for trimming is withdrawn, because it
contradicted the ruling it claimed to summarise.

## 2. Formatting requirements, with the traps already known

* **A blank line after an exhibit, except when the page ends there** (U028, 2026-11-20). The supervisor's
  screenshot showed Table 1's last ruled edge running into the bold H2 under it, and the rule he set is a gap
  after a table or figure *unless nothing follows it on that page*. An empty body line is written after each
  exhibit block, which renders 46.1 to 46.3pt from the exhibit's bottom edge to the next line, and it is
  suppressed when the block that follows carries its own `w:pageBreakBefore`. Both halves of the rule took a
  wrong version first: writing the gap unconditionally stranded it at the *top* of the following page, and
  deciding "page-final" from the source rather than the page cannot work, because pagination is Word's
  decision. So the gap is asserted on the rendered page, where `exhibit_gap_checks()` measures it and where a
  page that opens more than 2pt below the text top is reported as a stranded separator.
* **Caption lines are 1.5-spaced, as the template's own caption pair is** (U028). The body prototype the
  captions were cloned from is double-spaced (`w:line=480`); the template's `Table 1` / `Table text` pair is
  `w:line=360`, and exported through Word it renders the label at y=72.5 over the description at y=105.1.
  Those two numbers are the gate's constants - 32.6pt from label to description, 20.7pt between wrapped
  description lines - because the arithmetic of 1.5 on 12pt Times gives 20.7 for the first step too, and the
  template does not render that way.
* **Exhibit labels are bold** (U028): `Figure 1` and `Table 1` render in `TimesNewRomanPS-BoldMT`, including
  the SEQ field that carries the number, so a bold label never shows a plain digit beside it. Tables needed
  no change: they already ran flush with the text edge at x=90.3 to x=521.9, full block width; the character
  drops the supervisor saw are column widths taken from the caption's wording rather than from the cells, and
  that is a separate decision, not one made silently here.
* **Two figures on one page hold that page to themselves** (U028): the first at the top, the second at the
  bottom, the middle deliberately empty. The size of the empty middle is arithmetic, not tuning. A figure block
  is its caption lines (45.9pt plus 20.7pt for each extra wrapped description line, counted with the document's
  own typeface), 18.8pt above the picture, and the picture at the height `figure_paragraph` places it at; two
  blocks and a gap fit the 648pt text area only when their total leaves room, with 36pt reserved because a
  190pt gap in the trial put Figure 5's picture at 723.4 and Word moved the figure to the next page. So
  Figure 4 and Figure 5 share page 26 with a written gap of 151.4pt - the pair measures 442.4pt against the
  593pt available - while Figure 8 and Figure 9, whose blocks come to 703.7pt, get no gap at all and Word breaks
  between them. Writing the gap anyway was what left Figure 9's caption 162pt down an otherwise empty page 35.
* **Exhibits sit flush with the text block** (U027, 2026-11-20). The template's own caption lines carry no
  `w:ind` and its figure paragraph is left-aligned with no space above or below, while its body prose is indented
  half an inch. Cloning the body prototype for captions therefore pushed all fourteen exhibit labels half a column
  right, and centring the pictures left them attached to neither margin. Labels, descriptions and pictures now all
  start at the text edge, x=90 in the rendered page.
* **References opens its own page** (U027): `w:pageBreakBefore` on the heading. Section 7 used to run to mid-page
  42 and leave the heading with three entries squeezed in above it. The break is carried by the heading rather than
  by a separate paragraph, because a break paragraph reads as another contents entry to `audit_docx`.
* **Cover carries the student's own values** (U026, superseding the rule that the placeholders stay as
  shipped): course line and report line, name with student number, and the submission date, read from
  `report_assets/cover_values.json`, which is gitignored. The name line is four Word `ASK` fields in this
  template, so the fill deletes them and writes literal text — writing into a field leaves the value in the XML
  and off the page.
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
item (the supervisor's standing rule). The A1/A2 skeleton this report follows has no appendix, so every one of
them landed as a numbered figure: five clips of PDF pages (which carry the clipped region as well as the source
and page), two text renders of the companion README and the pinned corruption code (which record line ranges
instead of a region, because they were drawn rather than clipped), and two plots from this study's own run tables
(which record the artefact or the fresh fit behind them). All nine are listed with those fields in
`report_assets/figure_manifest.json`. The list is fixed now so the drafting does not discover it later:

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
| Table 1 | the screening ledger: 20 candidates, gates not cleared, weighted score, disposition | §2, What was searched, and how the candidates were screened |
| Table 2 | experiment settings per regime, from the two diagnostics files | §5, Datasets, features and the evaluation protocol |
| Table 3 | test accuracy, selection and five-fold spread, from selection.csv and cv_summary.csv | §5, Main results |
| Table 4 | the corruption control arm by arm, from probe_ood.json | §5, Two controls |
| Table 5 | the pixel-dimension ladder, from orl512_ladder.json | §5, Two controls |

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

## 8. Rulings recorded (U017 2026-11-19, U022 2026-11-20) — framework approved

* **Framework passes** as written.
* **§6 link block follows A2's form — both addresses**, in A2's own wording pattern:
  "The source page is `https://github.com/0weixiong0/CISC3024-AI-Assignment-3`" and
  "The live page is `https://0weixiong0.github.io/CISC3024-AI-Assignment-3/`".
* **~4,700 words accepted.** If it runs long, compress §1 and §3 first; **§4 and §5 are not touched.** (The number, not the trim order, has since been superseded twice: U021 moved it to 5,900 and U022 to 6,500, and U022 also moved the first place the knife falls, from §1/§3 to §2/§6/§7.)
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
| Body words | see the unit table below | see the unit table below | 6,500 prose words over sections 1–7, captions and table cells counted separately |
| AI-use statement | disclaimer sentence inside the workflow section | §1.2 "Human Supervision and AI Responsibilities", opening "The student acted as supervisor and the agent as researcher, implementer and experimenter." | §1, A2's placement with A3's own evidence |
| Link block | "Source code:" + "Live demo:" lines | "The source page is …" + "The live page is …" | A2's wording |
| References | APA 7, `EndNote Bibliography` style, plain paragraphs (no fields), 6 entries | same, 15 entries, one alphabet | APA 7 plain paragraphs, `EndNote Bibliography` |
| Exhibit labels | two typed lines above the object: `Figure N` then the italic description | same (17 figures, 11 tables) | same two-line form — `audit_docx.py`'s caption regex depends on it |
| Equations | — | `wordify_equations.py` abandoned: Word's LaTeX-to-math fires on typing, not on programmatic `BuildUp()`, so command names stayed literal | real Unicode symbols in plain text (μ, Σ, ‖·‖), as accepted for A2 |
| Report in the public repo | no | no | **no** — the docx/pdf are UMMoodle submissions, so they are gitignored |

**Word counts in four units, all measured on 2026-11-19 rather than quoted from memory** (U018). The
figures this file first carried — ~2,906 for A1 and ~8,011 for A2 — were labelled "body words" but did not
match any of the four measurements below, so they are withdrawn.

| Unit | How it is counted | A1 | A2 | A3, after step 3 (2026-11-20) |
| --- | --- | --- | --- | --- |
| Word's own count | COM `ComputeStatistics(wdStatisticWords)` on the docx | 3,474 | 9,593 | 9,021 |
| PDF full-text words | pymupdf over the exported PDF - includes tables, the contents page and the cover | 3,528 | 9,792 | 9,187 |
| docx paragraph words | `python-docx`, every paragraph in `doc.paragraphs`, tables excluded | 3,088 | 8,221 | 7,561 |
| **prose words** | the unit A2's own record used (`stage_05_report_feasibility.md` §4), **excluding exhibit captions and the reference list** | 3,024 | 8,286 | **6,494** |
| exhibit caption words | the two or three lines above each table and figure, counted apart because they are labels, not argument | - | - | 428 |
| table words alone | `python-docx` over table cells (5 tables, 415 cells; the 817 figure U022 corrected was words, not cells) | 187 | 1,107 | 1,243 |

The A3 column was re-measured on the 2026-11-20 U027 build, which carries exhibits, a 15-entry reference list
filed as one alphabet, and a cover filled with the student's own values: 45 PDF pages, 31 headings (8 H1
including References, 23 H2), 5 tables, 9 figures, and §1 through §7 all drafted. The prose figure is taken with
the caption lines excluded, because step 3 made them a large block of text that is not argument: 14 captions carry
428 words, and Word's own counter, which sees everything, reads 9,021 against 9,187 from the PDF text layer.
The prose unit also contains the 30 words of the cover block, which is where it has always been; filling the cover
from U026's values moved the figure by four words, placeholders to values, and nothing in the sections changed.

**The ceiling question is closed (U022).** It was reopened on this plan's own arithmetic: U021's 5,900 came
from 5,017 drafted + 850 for §6/§7, and step 3 then added the C4 comparison paragraph (200 words), thirteen
sentences citing the exhibits (130), and §6/§7 came in at 1,117 against 850. The supervisor's ruling is that the
brief sets no limit, A2 shipped 8,286 prose words over 54 pages, and 6,500 is not a high ceiling - so the number
moves and this is the last time it moves. The overage was then paid for inside §2's own budget rather than by
touching §4 or §5: the screening citation costs 15 words and two clauses of §2's wave paragraph were compressed
by 16, which left the drafted prose at the ceiling exactly. Step 4 then moved the same way: the six in-text
citations cost 28 words, and 28 were cut back inside §6 and §7, so **the drafted prose is 6,500 words with no
headroom**. The U025 round spent seven words on the Tiny ImageNet citation and took nine back
in §6 and §7; U026 filled the cover, which moved the figure by four more words because the cover sits inside this
unit, so the drafted prose is now **6,494** against 6,500 - six words of headroom, with the caption, reference and
cell counts recorded below. Exhibit captions (428 words), the reference list (456 words over 15 entries) and
table cells (1,243 words) stay outside the unit, because they are labels and read-outs rather than argument.

**The 6,500 budget is in prose words**, because that is the unit A2's record reported and it is the closest
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
  Two findings remained at this step and both were expected: the cover's own template placeholders
  (`CISCXXXX YYYY`, `Your NameXXX, Student No: DDxxxxxx`), closed by U026 on 2026-11-20, and "no URL anywhere" —
  the URL arrived with §6.
* `src/audit_layout.py`: passes (no exhibits yet). **Extended in the U020 round**, because it had no
  opinion about the contents page: `toc_checks()` now finds the pages carrying dot-leader lines and the
  page where the first section heading starts, and fails if they are the same page or if the body starts
  before the last contents page. On this build it reports `contents pages: [2, 3]  first section page: 4`.
  The underlying fault was real and the audit was blind to it: with 31 resolved entries the contents ran
  onto page 3 and §1 began underneath its last entry. The fix is `w:pageBreakBefore` on the first content
  H1 rather than a break paragraph after the content control - the paragraph version was counted by
  `audit_docx` as a 32nd contents entry, which is how the mismatch surfaced.
* **Cover fill (U018 item 1, values released by U026 on 2026-11-20).** `Builder.fill_cover()` reads
  `report_assets/cover_values.json` — gitignored, so the values the supervisor supplies never enter the
  repository. It was inert while that file was absent; the cover is now filled from it. Paragraphs are matched
  by role rather than by literal token text, because the template splits each token across runs ("C" + "ISC" +
  "XXXX") and builds the name line from ASK fields; the date paragraph carries a real example date ("06 Apr
  2026") instead of a token, so it would never have surfaced as stale. The file properties are written in the
  same pass, because the template ships with somebody else's name in `author`. Two gates hold the result:
  `audit_docx` compares the built paragraphs with the released JSON and fails if a prompting field survives,
  and `audit_layout` compares page 1 of the exported PDF with the same JSON, which is the check that catches a
  value present in the XML and absent from the page. Both were run against a tampered byline to prove they fire.

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
expected ones: cover placeholders pending the values (U018 item 1, since released by U026), no URL until §6,
no tables until step 3 of §7.

## 10.1 Step 3, delivered 2026-11-20

Five tables and nine figures are in the document with field-numbered captions and field cross-references; §6 and
§7 are drafted; the C4 comparison paragraph U020 asked for is in §5 with both of its pages. The U025 round brought
the reference list to 15 entries, sorted as one alphabet, and added the Tiny ImageNet citation to §5. The build
reports 45 PDF pages, 9,021 words by Word's own counter (9,187 from the PDF text layer) and 7,561 docx paragraph words, with 6,494 prose words excluding
captions and the reference list, 428 caption words, 456 reference words over 15 entries, and 1,243 table words across
415 cells in 5 tables, plus 9 figures, 31 headings and 31 contents entries. Steps 4 and 5 added the reference list (5 entries, each
cited), the brief-item coverage map (§12) and the prose pass over §6/§7 (§13); three gates came with them and steps 4
and 5, one that re-checks every citation and entry on the rendered text, one that bands the rendered body word count,
and one added in the U025 round that files the whole bibliography as a single alphabet. The fifth table is §2's screening ledger, which U022 released after the four in §5 were accepted; §4's
code-path table is withdrawn, because U022 ruled that its prose already covers brief item (3).

`audit_docx` found one issue, the expected one at that step: the cover still
carried the template's placeholders, released and filled two rounds later (U026). `audit_layout` passes every check,
including TOC pagination, the caption-adjacency rules and exhibit image placement. Two provenance corrections
came out of wiring the exhibits: the README figure's line numbers were being derived from an offset across a
blank line, so the picker now carries each line's own number (the block is lines 75-82, not 77-83), and the
figure manifest no longer claims report numbers for itself.

**The U028 round added three rendered checks and proved all four against tampered copies** (a copy of the built
docx, broken on purpose, exported and audited; nothing below survives on disk, the files were deleted after the
run). Removing the bold from Figure 3's label gave `page 17: the label 'Figure 3' is not bold
(['TimesNewRomanPSMT'])`; deleting the blank line under Table 1's last row gave `page 9: an exhibit ends at 524.1
and the next line starts 34.3pt below it`; setting Table 2's caption pair back to the body's double spacing gave
both `description starts 39.6pt under the label` and `description lines advance 27.6pt`; shrinking the written gap
from 151.4pt to 20pt gave `page 26 holds two figures but only 38.6pt separates them` and `its second figure ends
166.6pt above the text bottom`. The page-top rule needed no tampering to prove: it fired on the live build, on the
stranded gap above Figure 9, before the geometry fix removed the cause. None of this moved a count - the build after
the changes is the same 45 pages, 9,021 words by Word's counter, 9,187 from the PDF text layer, 7,561 docx paragraph
words, 6,494 prose words, 428 caption words, 456 reference words over 15 entries and 1,243 table words over 415
cells, because a gap, a line-spacing value and a bold flag carry no words.

## 12. Brief-item coverage, measured on the 2026-11-20 build (step 4)

Pages are where each H1 starts in the exported PDF, read from the rendered file rather than from the outline.

| Brief item | Where it is answered | Pages |
| --- | --- | --- |
| (1) Recent PCA/LDA algorithm found with an AI tool, and why it was chosen | §2, with the screening ledger as Table 1 | 5-10 |
| (2) What the algorithm does and how it was adapted to the task | §3 | 11-17 |
| (3) How it was implemented and verified with AI assistance | §4 | 18-22 |
| (4) Experimental settings, results, and discussion | §5, Tables 2-5 and Figures 4-9 | 23-37 |
| (5) What was learned from using the AI tool | §7 (and §1 states the division of labour) | 39-41 |
| (6) Source-code availability, as a webpage link | §6's citation block: the repository line and the Pages line, each on its own line | 38 |
| No-code and AI-use statement (the brief's prohibition, and the outline's disclosure) | §1, "AI use and responsibility" | 4 |

Section starts, for reference: §1 p4, §2 p5, §3 p11, §4 p18, §5 p23, §6 p38, §7 p39, References p43 to p45
(the bibliography opens its own page from U027; the break moved it one page later and the entries run to p45). Contents
occupies pages 2-3, and the body begins on page 4 under the page-break rule recorded in §10.

### Bibliography: 15 entries, filed as one alphabet, each one traced to a record

Every entry was transcribed from a source record rather than written from memory, and the two long-author
entries follow APA 7's rule for more than twenty names (first nineteen, ellipsis, last author). The list is sorted
as a whole, letter by letter through the surnames, which is what APA 7 filing means; `src/audit_docx.py` now
asserts that on the rendered paragraphs, because a list built by appending a released batch to an accepted one
reads as two sorted runs rather than one.

| Entry | In-text | Where the metadata came from |
| --- | --- | --- |
| Face database | (AT&T Laboratories Cambridge, 2002), §5 | the distributor's official page, fetched 2026-11-20 |
| DLR-2DPCA (Bi et al. 2025) | (Bi et al., 2025), §2 | Crossref registered metadata: the IEEE page renders nothing to a fetch, and the cached accepted manuscript has no author block in its text layer |
| NumPy (Harris et al. 2020) | (Harris et al., 2020), §2 | Nature DOI, read through the Crossref record |
| ResNet (He et al. 2015) | (He et al., 2015), §5 | arXiv listing, cross-checked against the arXiv API |
| ImageNet-C benchmark (Hendrycks & Dietterich 2019) | (Hendrycks & Dietterich, 2019a), §5 | cached PDF, ICLR 2019 header |
| The pinned corruption code | (Hendrycks & Dietterich, 2019b), §5 | commit 712bfcd, recorded in the figure manifest |
| CIFAR technical report (Krizhevsky 2009) | (Krizhevsky, 2009), §5 | the dataset's official page, fetched 2026-11-20 |
| Comparison study (Kumar et al. 2026) | (Kumar et al., 2026a), §5 | cached PDF title page |
| Its repository README | (Kumar et al., 2026b), §5 | cached README |
| Tiny ImageNet (Le & Yang 2015) | (Le & Yang, 2015), §5 | the CS231n 2015 course-report PDF, whose title block names Ya Le (Department of Statistics) and Xuan Yang (Department of Electrical Engineering); the entry's own address is the dataset archive, which answers 200 with 248,100,043 bytes, `application/zip`, `Last-Modified: Mon, 09 Feb 2015` |
| GO-LDA (Liu, Cai & Niranjan 2023) | (Liu et al., 2023), §2 and §3 | cached PDF title page |
| DINOv2 (Oquab et al. 2023) | (Oquab et al., 2023), §5 | arXiv listing, cross-checked against the arXiv API |
| PyTorch (Paszke et al. 2019) | (Paszke et al., 2019), §2 | arXiv listing, cross-checked against the arXiv API |
| scikit-learn (Pedregosa et al. 2011) | (Pedregosa et al., 2011), §2 | the JMLR page (volume 12, 2825-2830); the page prints no DOI |
| RSSPCA (Wang et al. 2025) | (Wang et al., 2025), §2 | PLOS ONE page and its own citation line, plus the Crossref record |

**The Tiny ImageNet gap is closed, and the two accounts of it are now one.** What the plan said - and what was
true - is that §5 names the data set descriptively, "Tiny ImageNet (200 classes, 100,000)", with no entry and
no in-text citation. The chat note that it was absent from the prose altogether was the wrong version of that
sentence, and it is withdrawn here. U025 released the citation on condition that the locator be the dataset
archive rather than the 404 landing page, so the entry points at `https://cs231n.stanford.edu/tiny-imagenet-200.zip`.
Two judgment calls came with it. The corporate, undated form the plan had sketched - "Stanford University,
(n.d.)" - was dropped once the primary record turned up, because a dated, authored source outranks a guess with
no date; and the entry is typed **[Data set]** rather than as the course report, since what the study read is the
archive, while the report is the description that carries the two names.

**Nothing inside the archive cites it.** Its 120,609 entries are `train/`, `val/` and `test/` with no README, no
`.tex` and no `leivo.tar.gz`, which is also why the comment in `src/extract_features.py` about a `leivo.tar.gz`
holding `reference_tex/tinyimagenet.tex` does not describe the archive this study downloaded.

Two provenance notes a marker could reasonably ask about. The DLR-2DPCA entry is registered publisher metadata
(Crossref), not a rendered IEEE page, so its page range and issue come from the deposit rather than from the
publisher's HTML. The scikit-learn entry carries no DOI because the JMLR page does not print one.

`src/build_report.py` refuses to build if an entry is uncited or a citation has no entry, and
`src/audit_layout.py` re-checks both directions on the rendered text, because Word wraps a long citation across
a line and a plain string search would then miss it.

## 11. What is still open

* **Cover** - closed on 2026-11-20 (U026). The three values arrived, went into `report_assets/cover_values.json`
  (gitignored, so they stay out of the repository), and the build fills the cover from them: LI WAI HONG,
  UC425821, dated 21 Nov 2026 because he does not expect to hand it in before then. `audit_docx`'s placeholder
  finding is gone; the file has no findings at all now.
* **Final read-through** - done on 2026-11-20: the coverage map is §12, and the prose pass over §6 and §7 is
  §13. Outside those two sections only words were touched, per U023. The §6 splice it left behind - "the three audit
  the three audit scripts" - was found in the U025 round while paying for the citation, which is the second time a
  defect of that shape surfaced only because a script read the assembled text rather than a person reading the page.
* **Tiny ImageNet citation** - closed on 2026-11-20. §12 has the record: the entry is Le and Yang (2015), typed
  [Data set], addressed to the archive rather than to the 404 landing page, and its seven words are paid for
  inside §6 and §7, which gave up nine.
* **Trim** - closed by U022 and paid by U023: the ceiling is 6,500 prose words and the drafted prose is
  6,494 after the U025 round spent seven words on the Tiny ImageNet citation, took nine back out of §6 and §7,
  and U026 replaced the cover's 34 words of placeholder text with the 30 words of real values. Six words of
  headroom. Any further addition has to pay for itself inside §2, §6 or §7, the way the citation sentences and
  the prose pass did.
* **Table column widths** - open, and deliberately not acted on (U028, 2026-11-20). The instruction was
  "tables could go left-aligned, because centring pushes some characters down to the next line". The first half
  is already true and measured: all five tables run from x=90.3 to x=521.9 inside a text column of 90.0 to 522.0,
  so nothing is centred. The second half is not a centring effect: `table_element` gives every column
  6.0in divided by the number of columns, so a header like "Gates not cleared" in Table 1 wraps because it was
  allotted one-seventh of the line. Widening the narrow columns and shrinking the wide ones would fix the
  wrapping, but it re-lays all five tables, can move pages, and would need both audits and the package re-run -
  so it waits for a word from the supervisor rather than being done on the side of an instruction that asked
  for something else.
* **Submission package** - assembled 2026-11-20 (U026). `submission/` holds the report docx, the report pdf and
  the dialogue record as markdown, each byte-identical to the file it was copied from;
  `CISC3024_AI_Assignment_3_submission.zip` carries those three and nothing else. Both are gitignored, along with
  the report files themselves, because the submission is not repository content. Uploading it is the supervisor's
  act, and `git rev-parse main` is still to be written into §3 at that moment.
* **Cover** - closed by U026: `report_assets/cover_values.json` exists, the cover fills from it, and the two
  cover gates (one on the docx, one on page 1 of the rendered PDF) are what say so.
