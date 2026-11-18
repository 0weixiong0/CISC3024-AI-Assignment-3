# Stage 00 — Pre-flight: Brief, Environment, Policy and Template Audit

Project: CISC3024 AI Assignment #3 · Date: 2026-11-16 · Language: English
Purpose: fix the facts that every later stage depends on, before any searching or coding begins.

---

## 1. The brief, as read from the file

`D:\claude\workspace\CISC3024 AI Assignment 3\AIassign3.pdf` — one page, dated November 2026.
Verbatim requirements:

- "AI Assignment # 3 aims to find a **recent PCA/LDA algorithm** with application to computer vision
  and pattern recognition."
- "You are expected to use an AI tool or agent to do everything for you, including, but not limited
  to, algorithm searching, programming, and even report writing."
- "A report in Word or PDF format should be submitted online via UMMoodle **next week** and will go
  through a **Turnitin** similarity check."
- The report "should contain detailed steps on how you did this assignment, including (1) how AI
  finds the algorithm, (2) algorithm description, (3) how AI implements the algorithm, (4) experiment
  settings and results, (5) what you have learnt from this AI assignment, and (6) **a webpage link of
  your source codes**."
- "Note: **You are NOT allowed to write any code by yourself!**"

## 2. Divergences between the supervisor's outline and the brief, and his rulings

| # | Divergence | Supervisor's ruling (U002, 2026-11-16) |
| --- | --- | --- |
| D1 | Brief says "a recent PCA/LDA algorithm" — singular, PCA **or** LDA; the outline said "PCA **and** LDA" | Accept both families (PCA-only, LDA-only, hybrid) into the pool; decide from the evidence after the search |
| D2 | Brief's "recent" carries no year bound | Hard floor **2023-01-01** |
| D3 | The outline calls the target a "neural network" throughout; PCA/LDA are classical linear subspace methods | "不一定是神经网络" — it need not be a neural network; a genuine CV / pattern-recognition application is the requirement |
| D4 | Brief component (6) asks for a webpage **link**; the outline's stage 4 described a local HTML page | Will be a GitHub Pages demo; deferred to the final stage |
| D5 | Brief lists six report components; the outline lists five stages | Mapping adopted: stage 1 → (1), stage 2 → (2), stage 3 → (3)+(4), stage 4 → (6), stage 5 → (5) |
| D6 | Brief forbids the student writing any code, which inverts the rule used in his CISC3029 coursework | The AI writes 100 % of the code here; his role is supervision and approval only |

Deadline taken from the supervisor, not the PDF: **submission before 2026-11-23**.

## 3. Environment measured, not assumed

Measured on 2026-11-16 through the local shell:

| Item | Value |
| --- | --- |
| CPU | 13th Gen Intel Core i9-13900H, 14 cores / 20 logical processors |
| RAM | 33,968,410,624 bytes ≈ 31.6 GiB |
| GPU | NVIDIA GeForce RTX 4060 Laptop GPU (8 GB class), plus Intel Iris Xe and a GameViewer virtual display |
| Python | 3.12.10 |
| numpy / scikit-learn | 2.4.6 / 1.9.0 |
| torch | 2.7.1+cu128, `torch.cuda.is_available() == True` |

Reference point for all duration claims: Assignment #2 ran a 5-configuration × 3-seed matrix in
**2.7 h** on this same GPU. Any candidate that needs more than a few GPU-hours is therefore
infeasible inside the remaining window.

## 4. Skills selected for each stage

| Stage | Skill | State | Approval |
| --- | --- | --- | --- |
| 1 Search | `deep-research` | already installed locally — nothing was downloaded or installed | named by the supervisor in U001 as the search-stage skill |
| 2 Design/plan | `Plan` agent role + `Agent_coding.pptx` eight-step loop | local | — |
| 3 Implementation | plain tooling; `tdd` if a verification harness is wanted | local | to be asked if a new install is needed |
| 4 Frontend | `frontend-design` / `ui-ux-pro-max` if wanted | local | will be asked before installing anything |
| 5 Report | `office-docx:docx` (Word) or `latex-document-skill` | local | he prefers Word first (U001 item 5) |

No skill installation has been requested or performed in this stage.

## 5. `Agent_coding.pptx` — the decomposition the plan must follow

Extracted from `D:\claude\workspace\CISC3024 AI Assignment 3\Agent_coding.pptx` (15 slides) on
2026-11-16. The lecture defines the agent-coding loop as:

**Decomposition → Task Description → Preparation (Plan) → Execution → Supervision → Verification →
(Result) Presentation → Evaluation → Iteration.**

- *Task Description* must state **Goal, Scope, Constraints, Input, Output, Functional Requirements**,
  and "should be clear and precise" — slide 8 gives the cautionary example that a bare "LeNet"
  instruction is ambiguous (28×28 + ReLU + max pooling versus the 1998 LeNet-5 at 32×32 with scaled
  tanh and average pooling), so an under-specified task description is where agents go wrong.
- *Preparation (Plan)*: self-defined or AI-generated then human-refined, with implementation/technical
  details, **set milestones**, and a **minimum viable product (MVP)**.
- The efficient way to describe a task (slide 9) is to point at an **existing reference** — a web
  search result, a paper or documentation — and state the expected outputs, then iterate on the
  agent's understanding with human feedback. For this assignment the reference is the chosen paper
  itself, which is why the recoverability gate G3 in `stage_01_search_protocol.md` matters.

The Stage-2 plan will be written against this skeleton, with an explicit MVP milestone before the
full experiment matrix.

## 6. Report template audit — the Assignment #2 formatting trap, found before it can repeat

Read directly from `D:\claude\workspace\CISC3024 AI Assignment 3\Report Template.docx`
(`word/styles.xml` + `word/document.xml`) on 2026-11-16. 31 styles defined.

| Style id | Name | Declared font / size |
| --- | --- | --- |
| `a` | Normal | Times New Roman / 12 pt |
| `1` | heading 1 | Calibri Light / 16 pt |
| `2` | heading 2 | (theme font) Light / 20 pt |
| `3` | heading 3 | 16 pt bold |
| `a4` | Title | Arial / 20 pt bold |
| `a3` | Subtitle | Arial / 14 pt bold |
| `ad` | Table Grid | — |
| `TOC`, `TOC1`, `TOC2`, `TOC3` | TOC Heading, toc 1–3 | — |
| `EndNoteBibliography` | EndNote Bibliography | — |

**The trap, and it is exactly the failure mode reported for Assignment #2:** the template's own
example headings apply style `1`, `2` and `3` **and then override them with direct run formatting of
Times New Roman at 12 pt** (`<w:sz w:val="24"/>` with `w:ascii="Times New Roman"` inside the paragraph
run properties). A generator that only assigns the paragraph style produces Calibri Light 16/20 pt
headings and looks nothing like the template. The rule for stage 5 is therefore:

> Assign the paragraph style **and** write the direct run properties (Times New Roman, 12 pt) on the
> heading text, then verify by reading `document.xml` back — not by trusting the style assignment.

Other template facts to honour: the cover lines are `University of Macau` / `Faculty of Information
Science and Computing` / `Department of Computer Science` (style `a3`), the report title placeholder
`CISCXXXX YYYYXXX Report` (style `a4`), the author lines in custom styles `Author` and `Dept`
including `Your NameXXX, Student No: DDxxxxxxCYYYYYYXXX…` and the date line `06 Apr 2026`. Those
placeholders belong to the student and are not touched. Captions and reference-list conventions carry
over from Assignment #1: plain `Normal` caption paragraphs above the object containing only
"Figure N"/"Table N", `Table Grid` tables, and the `EndNote Bibliography` style for the reference
list — now with APA 7 in-text citations per the supervisor's instruction.

## 7. Reusable assets from Assignment #2

`D:\claude\workspace\CISC3024 AI Assignment 2\src\` contains `audit_docx.py`, `audit_layout.py`,
`apply_word_fixes.py`, `wordify_equations.py`, `build_report.py`, `export_pdf.py` and
`capture_webapp.py`. These were written to fix precisely the formatting problem in §6. They are
**reference material for stage 5, not code to copy blindly** — the stage-5 plan must state which of
them are reused and which are rewritten, because the report is a graded deliverable of this
assignment and the code in this repository must be written by the AI agent in this session.
