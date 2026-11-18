# CISC3024 AI Assignment 3 — GO-LDA, replicated and stress-tested

**Live front end:** https://0weixiong0.github.io/CISC3024-AI-Assignment-3/

This repository holds the code and the stage records for a replication of **GO-LDA**
(Liu, Cai & Niranjan, *Gradient-based Orthogonal LDA*, arXiv:2305.14568, 2023) — a PCA/LDA-family
classifier whose directions are constrained to be orthogonal in ordinary Euclidean space by sequential
deflation. The algorithm was found, implemented, run and written up with AI tooling end to end, as the
assignment brief requires; no line of code here was hand-written by the student.

What the replication found: the geometry reproduces exactly (the directions are orthogonal to ~1e-14 and
each is more Fisher-efficient than the classic pencil's), but the published accuracy advantage does not
travel. On frozen deep features at the rank cap `K = C − 1`, GO-LDA sits 0.1–2.3 points below the best
LDA baseline on all four dataset × backbone pairs, while in raw-pixel ORL it ties classic LDA because the
two span the same subspace to 2e-6°.

## Layout

| Path | What it is |
| --- | --- |
| `src/golda.py` | the GO-LDA solver: dense pencil route and exact span-reduced route |
| `src/baselines.py` | classic ridge / shrinkage pencil LDA, PCA-then-LDA, heads |
| `src/orl.py` | PGM reader for ORL at native 10,304 dimensions, with the header-geometry assertion |
| `src/run_mvp_orl.py`, `src/run_m2_matrix.py` | the two experiment scales (raw pixels; frozen features) |
| `src/probe_*.py` | the four controls: cap gap, head, out-of-distribution, dimension ladder |
| `src/export_results.py` | regenerates `webapp/data.js` from the run artefacts, refusing to write on any failed check (34 checks) |
| `src/export_demo.py` | refits every arm with the study's own solvers and regenerates `webapp/demo.js` |
| `tests/test_parity.py` | the parity gate: 11 gated checks, 7 diagnostic, plus the M0 data assertions |
| `webapp/` | the front end: `index.html` plus the two generated data layers |
| `research_records/` | the stage reports: search, design and plan, the two feasibility reports, the cross-regime synthesis, the front-end record |
| `runs/` | the small artefacts those records cite: CSV tables, JSON diagnostics, gate logs |

## Reproducing

```bash
python tests/test_parity.py                  # the gate; prints GATE OPEN when 11/11 pass
python src/run_mvp_orl.py                    # ORL raw pixels, the paper's ten-fold 1-NN protocol
python src/run_m2_matrix.py                  # the frozen-feature matrix (needs the datasets, ~2.7 h)
python src/export_results.py                 # regenerate webapp/data.js
python src/export_demo.py                    # regenerate webapp/demo.js (refits every arm, ~34 min)
```

The front end opens from `file://` with no server because both data layers are plain globals. To serve it
locally, `cd webapp && python -m http.server 8000`.

## What is deliberately not here

* **Datasets and cached features** (`data/`, 986 MB) — downloaded under the supervisor's released list from
  the URLs recorded in `research_records/stage_02_design_and_plan.md` §7.
* **Course material** — the assignment PDF, the lecture deck and the Word report template.
* **The dialogue record** — `research_records/conversation_log.md` is a report deliverable submitted
  separately, not public repository content.
* **Superseded parity logs** — `runs/parity/README.md` lists which runs predate the geometry fix and why
  the current citation is `runs/parity/parity_after_readpgm_stdout.txt`.
* **A third-party accepted manuscript** kept locally as a retrieval cache; cite the paper instead.
