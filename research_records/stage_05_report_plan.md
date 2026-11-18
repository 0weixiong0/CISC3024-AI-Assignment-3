# Stage 5 — report framework (for approval before any prose is drafted)

Issued 2026-11-19. Deliverable: a Word report on `Report Template.docx`, submitted via UMMoodle by
**2026-11-23**, Turnitin-checked. This file fixes the skeleton, the evidence behind each section, the
formatting traps and the citation block; the prose is written only after it is approved.

## 1. What the brief requires, and which section answers it

The brief's six numbered items are the report's spine — the outline's stage 5 says the same thing in
different words, so the brief wins where they differ.

| § | Report section | Answers brief item | Built from | Draft budget |
| --- | --- | --- | --- | --- |
| 1 | How the AI found the algorithm | (1) | `stage_01_search_protocol.md` §1–§11 (20 screened candidates, the weights, the 16-row correction table, the wave-1/wave-2 source ledger), `stage_01_candidate_scoring.md` §5 | ~900 words + 1 table |
| 2 | The algorithm | (2) | `research_records/sources/golda_arXiv2305.14568_notes.md` (eq. (23), (37)–(41) verbatim), `wp7` §2 | ~700 words + 2 display equations |
| 3 | How the AI implemented it | (3) | `stage_02_design_and_plan.md` (the nine-step loop, H1–H3 fixed first, the risk table), `stage_03a` §5–§6 (deviations), `stage_04_front_end.md` §1–§3, `webapp/data.js` `commands` | ~1,100 words + 1 code-path table |
| 4 | Experiment settings and results | (4) | `stage_03a` (raw-pixel scale), `stage_03b` §2–§5 and §8–§8.1 (feature scale, the two released controls), `wp7` §3–§7 | ~1,400 words + 4 tables + 2 figures |
| 5 | What we learnt | (5) | `wp7` §8's three sentences, plus the two process lessons in §4 below | ~600 words |
| 6 | Webpage link to the source code | (6) | the live Pages URL and the commits in §3 below | short block, not prose |

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
| ImageNet-C gaussian severity 1 ⇒ σ = 0.08 | Hendrycks & Dietterich 2019, arXiv:1903.12261 + `corruptions.py` | the corruptions table and the code line |

Report figures from our own runs: the growth curve per feature pair (hold-out curves plus test markers,
split-labelled), and the ORL direction images at `K = 1` versus the classic pencil's first direction.

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
* **~4,700 words accepted.** If it runs long, compress §1 and §3 first; **§4 and §5 are not touched.**
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
| Body words | ~2,906 | ~8,011 | ~4,700 |
| AI-use statement | disclaimer sentence inside the workflow section | §1.2 "Human Supervision and AI Responsibilities", opening "The student acted as supervisor and the agent as researcher, implementer and experimenter." | §1, A2's placement with A3's own evidence |
| Link block | "Source code:" + "Live demo:" lines | "The source page is …" + "The live page is …" | A2's wording |
| References | APA 7, `EndNote Bibliography` style, plain paragraphs (no fields), 6 entries | same, 14 entries | APA 7 plain paragraphs, `EndNote Bibliography` |
| Exhibit labels | two typed lines above the object: `Figure N` then the italic description | same (17 figures, 11 tables) | same two-line form — `audit_docx.py`'s caption regex depends on it |
| Equations | — | `wordify_equations.py` abandoned: Word's LaTeX-to-math fires on typing, not on programmatic `BuildUp()`, so command names stayed literal | real Unicode symbols in plain text (μ, Σ, ‖·‖), as accepted for A2 |
| Report in the public repo | no | no | **no** — the docx/pdf are UMMoodle submissions, so they are gitignored |

## 10. Shell status (step 1 of §7, done 2026-11-19)

`src/build_report.py` builds the shell from `Report Template.docx` by cloning the template's own example
paragraphs as formatting prototypes, so the headings carry the direct Times New Roman 12 pt run properties
that the style definitions alone would not give — the trap in §2. The cover and the TOC content control are
untouched; everything after the TOC control is deleted and re-emitted.

* Shell: 7 H1 + 21 H2 + References = 29 headings; 6 pages, 353 words after `src/export_pdf.py` resolved the
  TOC field through a private Word instance.
* `src/audit_docx.py`: **29 headings matched by 29 contents entries** (the stale-entry flags are gone),
  font census `'Times New Roman' 12.0pt: 27`, no Chinese, no jargon, no exhibit-integrity findings.
  Two findings remain and both are expected at this step: the cover's own template placeholders
  (`CISCXXXX YYYY`, `Your NameXXX, Student No: DDxxxxxx`) and "no URL anywhere" — the URL arrives with §6.
* `src/audit_layout.py`: passes (no exhibits yet).
* **Open with the supervisor:** the cover placeholders are his to fill — the ruling says the cover is not
  to be changed, so the name and student number need either to be entered by him in Word or explicitly
  released to this builder. A2 left the same item open.

## 11. What is still open

The three questions this file used to ask are answered in §8 (framework approved, both addresses in the
link block, ~4,700 words with §1/§3 compressing first). What remains:

* **The cover placeholders** (`CISCXXXX YYYY`, `Your NameXXX, Student No: DDxxxxxx`, the date) — the ruling
  says the cover is not to be changed, so these are either filled by him in Word or explicitly released to
  this builder. A2 closed the same item by hand.
* **Figure assets** — the page images listed in §5 still have to be rendered from the paper and the C4
  README, and each one needs a `report_assets/` file plus the two-line label the audit expects.
* **The prose itself** — §2 and §4 first, per §7 step 2.
