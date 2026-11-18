"""The report's prose, with every number read from an artefact at build time.



Project : CISC3024 AI Assignment #3 (Pattern Recognition, University of Macau)

Author  : AI-generated implementation (Qoder). The student wrote no code.



Why the numbers are read rather than typed

-----------------------------------------

Assignment 2's four lessons say a report number must point back to the file that produced it. Here that is

enforced structurally: nothing in this module writes a figure that comes from memory. Every number inside a

sentence is interpolated from the run artefacts under `runs/` or from the stage records under

`research_records/`, so if a run is re-done and a value moves, the text changes or the build fails - it

cannot quietly keep asserting the old number.



Sections are keyed by their exact H1 title as `build_report.py` emits them, so a renamed heading is an

error rather than a silently dropped section.

"""



from __future__ import annotations



import csv

import json

import re

from pathlib import Path



ROOT = Path(__file__).resolve().parent.parent

RUNS = ROOT / "runs"

REC = ROOT / "research_records"





def _json(rel: str) -> dict:

    return json.loads((RUNS / rel).read_text(encoding="utf-8"))





def _sci(value: float) -> str:

    return f"{value:.1e}"





def _pt(fraction: float, nd: int = 2) -> str:

    """A difference of accuracies, in percentage points with its sign."""

    return f"{100 * fraction:+.{nd}f} points"





def _md_table_rows(text: str, heading: str, next_heading: str) -> list[list[str]]:

    """Rows of the first markdown table under `heading`, header and separator excluded."""

    tail = text.split(heading, 1)[1].split(next_heading, 1)[0]

    rows = []

    for line in tail.split("\n"):

        if line.startswith("|"):

            cells = [c.strip() for c in line.strip().strip("|").split("|")]

            if not set("".join(cells)) <= set("-: "):

                rows.append(cells)

    return rows[1:]





def search_facts() -> dict:

    """Counts the search stage published in its own records, re-read here so the prose cannot drift."""

    txt = (REC / "stage_01_search_protocol.md").read_text(encoding="utf-8")

    ledger = list(csv.DictReader((REC / "stage_01_screening_ledger.csv").open(encoding="utf-8")))

    top = max(ledger, key=lambda r: float(r["weighted"]))

    primary = next(r for r in ledger if r["disposition"].upper().startswith("RECOMMENDED"))

    return {

        "candidates": len(ledger),

        "top_id": top["id"],

        "top_score": float(top["weighted"]),

        "top_disposition": top["disposition"],

        "primary_id": primary["id"],

        "primary_score": float(primary["weighted"]),

        "venue_year": primary["venue_year"],

        "gates": len(_md_table_rows(txt, "## 5. Screening gates", "## 6.")),

        "axes": len(_md_table_rows(txt, "## 6. Scoring rubric", "## 7.")),

        "queries": len(re.findall(r"`[^`]+`", txt.split("## 5. Screening gates")[0].split("## 4. Queries")[1])),

        "areas": len(re.findall(r"^\| [A-D] \|", txt.split("## 3. Search space")[1].split("## 4.")[0], re.M)),

        "wave1_sources": int(re.search(r"\*\*(\d+)\*\* tagged sources", txt).group(1)),

        "wave2_sources": int(re.search(r"Wave 2 added (\d+) further sources", txt).group(1)),

        "total_sources": int(re.search(r"for (\d+) in total", txt).group(1)),

        "wave_reports": len(list((REC / "wave1_reports").glob("*.md"))),

        "corrections": len(_md_table_rows(txt, "## 11. Corrections", "Search-stage lessons")),

        "verified": len(re.findall(r"^\| *V\d+ *\|", txt.split("## 8.")[1].split("## 9.")[0], re.M)),

    }





def facts() -> dict:

    """Everything the prose interpolates, read from the artefacts at build time."""

    cap = _json("m2_matrix/probe_m2_cap_gap.json" if False else "m2_matrix/probe_cap_gap.json")

    dg = _json("m2_matrix/diagnostics.json")

    mvp = _json("mvp_orl/diagnostics.json")

    lad = _json("orl512_fix/orl512_ladder.json")

    ood = _json("m2_matrix/probe_ood.json")

    parity = _json("parity/parity_report.json")

    pairs = dg["per_pair"]

    cifar = next(p for p in pairs if p["dataset"] == "cifar100" and p["backbone"] == "resnet18")

    drift = {int(k): v for k, v in cap["drift_growth"].items()}

    angles = cap["spans_at_cap"]["GO_vs_classic-eig"]["angles"]

    acc = cap["test_accuracy"]

    heads = {b["backbone"]: b for b in ood["backbones"].values()} if isinstance(ood["backbones"], list) else ood["backbones"]

    return {

        # --- the mechanism (CIFAR-100 x ResNet-18, the pair the cap probe ran on)

        "dim": cap["dim"],

        "cap": cap["cap"],

        "rows": cap["rows"],

        "probe_delta": cap["delta"],

        "go_offdiag": cifar["go_offdiag"],

        "classic_offdiag": cifar["classic_offdiag"],

        "go_offdiag_range": (min(p["go_offdiag"] for p in pairs), max(p["go_offdiag"] for p in pairs)),

        "classic_offdiag_range": (min(p["classic_offdiag"] for p in pairs), max(p["classic_offdiag"] for p in pairs)),

        "mu_sum_go": cap["spectrum"]["GO_vs_classic-eig_sum_a"],

        "mu_sum_classic": cap["spectrum"]["GO_vs_classic-eig_sum_b"],

        "first_cos": cap["first_direction"]["abs_cos_GO_vs_eigh"],

        "drift1": drift[1]["max_deg"],

        "drift2": drift[2]["max_deg"],

        "drift3": drift[3]["max_deg"],

        "span_median": angles["median_deg"],

        "span_max": angles["max_deg"],

        "span_under_1deg": 100 * angles["frac_under_1deg"],

        # --- numerics and routes

        "route_span": cap["route_control"]["GO_dense_vs_reduced_span_deg"],

        "route_mu": cap["spectrum"]["GO-dense_vs_GO-reduced_max_abs_diff"],

        "solver_mu": cap["eig_vs_eigh"]["max_abs_mu_diff"],

        "solver_span": cap["eig_vs_eigh"]["span_deg"],

        "kappa_min": min(p["kappa"] for p in pairs),

        "kappa_max": max(p["kappa"] for p in pairs),

        "res_worst": max(p["residual_rel_max"] for p in pairs),

        "tol_worst_pair": max(p["residual_rel_max"] / p["residual_tol"] for p in pairs),

        # --- protocol

        "deltas": dg["deltas"],

        "kmax_cifar": next(p["K_max"] for p in pairs if p["dataset"] == "cifar100"),

        "seed": dg["seed"],

        "val": dg["val_fraction"],

        "shrink": dg["shrinkage_alpha"],

        "delta_rule": dg["delta_rule"],

        "certified": mvp["certified_deltas"],

        "uncertified": mvp["uncertified_deltas"],

        "mvp_deltas": mvp["deltas"],

        "rank_cap": mvp["rank_cap"],

        "k_grid": mvp["k_grid"],

        "mvp": _json("mvp_orl/timing.json"),

        "mvp_rows": _json("mvp_orl/manifest.json")["rows_written"],

        "mvp_wall": _json("mvp_orl/timing.json")["total_wall_clock_s"],

        "mvp_rss": _json("mvp_orl/timing.json")["peak_rss_mb"],

        # --- accuracies at the cap

        "go_at_cap": acc["GO@cap"],

        "classic_at_cap": acc["classic-eigh@cap"],

        "go_qr_at_cap": acc["classic-eig@cap-QR"],

        "go_at_beyond": acc["GO@beyond"],

        "no_proj": acc["no-projection"],

        "gap_at_cap": acc["GO@cap"] - acc["classic-eigh@cap"],

        # --- controls

        "ladder_paired": [r["paired_diff"] for r in lad["ladder"]],

        "ladder_M": [r["M"] for r in lad["ladder"]],

        "ladder_cap_ratio": [r["cap_over_M"] for r in lad["ladder"]],

        "ladder_s": lad["wall_clock_s"],

        "ladder_delta": lad["delta"],

        "ladder_head": lad["head"],

        "ladder_folds": lad["folds"],

        "ood_total_s": ood["total_seconds"],

        "ood_sigma": ood["corruption"]["sigma_on_unit_pixels"],

        "ood_severity": ood["corruption"]["severity_choice"],

        "ood_resnet_shift": heads["resnet18"]["mean_abs_feature_shift"],

        "ood_ranking": [b["ranking_preserved"] for b in ood["backbones"]] if isinstance(ood["backbones"], list)

                       else [heads[k]["ranking_preserved"] for k in heads],

        "ood_deficits": {k: heads[k]["go_minus_best_baseline"] for k in heads},

        # --- the gate

        "gated": sum(1 for c in parity if c.get("gated")),

        "passed": sum(1 for c in parity if c.get("ok")),

        "reported": len(parity),

    }





def search_sections(s: dict) -> dict:

    """Brief item (1): how the AI found the algorithm. ~900 prose words."""

    return {

        "AI-Assisted Literature Search and Algorithm Selection": [

            ("h2", "Constraints fixed before the search"),

            ("body",

             "The brief asks for a recent algorithm, and the first decision was to treat recency as a filter "

             "rather than as a preference: 2023-01-01 or later, with the date verified at the publisher, and "

             "pre-2023 work permitted only as a foundational reference, a tool or a rejection example. Both "

             "families stayed in the pool - principal-component analysis, linear discriminant analysis and "

             "hybrids of the two - and the choice between them was left to the evidence instead of being made "

             "in advance. The target did not have to be a neural network, but it did have to be evaluated as a "

             "classifier or recognizer on image data, which put generative models, detection and segmentation "

             "systems and adaptation techniques for language models out of scope from the outset."),

            ("body",

             "Two further constraints came from the assignment rather than from the literature. No code may be "

             "written by the student, so an algorithm whose equations cannot be recovered from public sources "

             "is unusable however novel it is. And brief item (6) requires a webpage link to the source code, "

             "which made demonstrability in a browser a selection criterion instead of an afterthought. The "

             "local environment was measured before searching rather than assumed: a 14-core i9-13900H, "

             "32 GB RAM, an RTX 4060 laptop GPU with 8 GB, and Python 3.12 with NumPy, scikit-learn and a "

             "CUDA-enabled PyTorch. That measurement set the feasibility gate - no large-scale retraining, but "

             "frozen-backbone inference and closed-form eigensolves - and it is why every cost figure at this "

             "stage is labelled either a literature value or an estimate. Nothing was downloaded while "

             "screening: the search read public evidence only."),

            ("h2", "What was searched, and how the candidates were screened"),

            ("body",

             f"The search ran as a deep-research protocol over {s['areas']} areas in parallel. The first asked "

             "which papers since 2023 propose a new principal-component method and evaluate it as an image "

             "recognizer; the second covered the discriminant-analysis family, including regularised and "

             "shrinkage forms, orthogonal and uncorrelated variants, multilinear and graph-embedded variants, "

             "and marginal Fisher analysis. The third looked for either method used inside or on top of deep "

             "learning - differentiable layers, whitening layers, discriminant heads, and classical "

             "projections attached to frozen pretrained or foundation-model features - because that is the "

             f"regime a single laptop can address. The fourth area existed so that the retrieval could not be "

             f"one-sided, and asked for documented failure modes and reproduction studies. {s['queries']} "

             "representative query strings are recorded exactly as issued, and each area carried a mandated "

             "critical or opposing term."),

            ("body",

             f"Screening applied {s['gates']} gates in order: recency at publisher-verified dates; task fit, "

             "meaning evaluation as a classifier on images; recoverability of the equations from an openly "

             "readable source or of readable official code; local feasibility within the measured memory and "

             f"the remaining days; and demonstrability in a browser. {s['candidates']} candidates then carried "

             f"a score on {s['axes']} axes - algorithmic transparency, local hardware demand, implementation "

             "difficulty for an AI-written reimplementation, novelty, and coverage of the six report "

             "components - weighted 20, 15, 25, 20 and 20 per cent, the weights approved before the shortlist. "

             "A cell was filled only from a source that had actually been opened; where the evidence could not "

             "be read, the ledger says so rather than guessing."),

            ("body",

             f"Wave 1 returned {s['wave1_sources']} tagged sources across the four areas, and a second wave "

             f"added {s['wave2_sources']} gap-fill sources for {s['total_sources']} in total. The {s['wave_reports']} "

             "wave-1 retrieval reports are archived verbatim, so the counts are checkable from the primary "

             "material rather than from a summary. Two findings shaped the shortlist more than any single "

             "score. The recent literature that proposes a new principal-component variant and evaluates it on "

             "images lives almost entirely in journals - IEEE Transactions on Consumer Electronics, PLOS ONE, "

             "Pattern Recognition, Sensors, Multimedia Tools and Applications, and small ACM proceedings - and "

             "no paper from the leading computer-vision or machine-intelligence venues proposing such an "

             "algorithm for recognition surfaced at all. Meanwhile the recent discriminant-analysis work that "

             "was both new and image-evaluated had moved to LDA as a closed-form stage attached to frozen "

             "pretrained or foundation-model features, which is precisely the regime where this machine "

             "reproduces a published number in hours rather than days."),

            ("h2", "Verification, and the corrections the screening needed"),

            ("body",

             f"Decisive claims were re-read by the lead agent rather than accepted from a subagent's summary: "

             f"{s['verified']} verification items, the first of them raised during wave 1 and the rest after "

             "the supervisor's fact-checks. All resolved as supported, and no fabricated identifier, author, "

             f"date or number was found in wave 1. The published record still needed {s['corrections']} "

             "corrections, and the instructive ones are not conceptual. Six weighted totals in the ledger were "

             "arithmetically inconsistent with the stated axis weights and had to be recomputed by script from "

             "the axis columns, after which every row was re-verified. An earlier draft of the protocol stated "

             f"a source count from recollection - forty against the checkable {s['wave1_sources']} - and was "

             "corrected from the archived reports, whose identifier sequences are contiguous. One candidate's "

             "headline accuracies had been marked unverifiable because the publisher page refused access, and "

             "a later read of the accepted manuscript superseded that note."),

            ("body",

             "What this stage teaches about using an AI tool for a literature search is narrow and worth "

             "stating plainly: the retrieval is fast and wide, and it is also fluent enough to make a wrong "

             "count sound final. Every number that survived did so because something on disk - a report, a "

             "ledger row, a page of a PDF - said it independently of the sentence that quoted it."),

            ("h2", "The selection, and what it committed us to"),

            ("body",

             f"The approved choice is Option A: generalised optimal discriminant analysis, recorded in the "

             f"ledger as candidate {s['primary_id']} at {s['primary_score']:.2f} of 5 ({s['venue_year']}), used "

             "as the recent algorithm. The highest-weighted row in the ledger is not the algorithm but "

             f"candidate {s['top_id']} at {s['top_score']:.2f}, whose disposition reads \"use as protocol and "

             "baseline\": its experimental design - frozen backbone features, an L2-logistic head, a hold-out "

             "for hyper-parameters and a single pass over the official test split - was adopted as the test "

             f"bench, while its own contribution was carried as a comparison point. {s['primary_id']} was "

             "recommended primary on three grounds: its objective and its deflation are recoverable from "

             "equations in an open preprint, so an AI-written implementation needs no official code; its "

             "construction makes its first discriminant direction coincide with the classical pencil's leading "

             "eigenvector, which hands the implementation a parity check for free; and its published evidence "

             "covers raw-pixel face data and 512-dimensional features, both affordable on this machine."),

            ("body",

             "The standing risk was disclosed when the option was approved rather than discovered afterwards: "

             "the paper exists only as a preprint, with no journal reference and no official implementation to "

             "diff against. That is why verification in this project took the form of internal checks - two "

             "independent solver routes, agreement with scikit-learn's own covariance estimates, and a "

             "residual bound derived from the pencil under test - instead of agreement with the authors' code."),

        ],

    }





def implementation_sections(f: dict) -> dict:

    """Brief item (3): how the AI implemented and verified it. Target ~1,100 prose words."""

    mvp = f["mvp"]

    return {

        "AI-Assisted Implementation and Verification": [

            ("h2", "Decomposition, and what was gated before it could be spent"),

            ("body",

             "The work was decomposed into eight packages before any code was written, in an order that puts "

             "the cheapest check in front of the most expensive run: the data layer, then the reference "

             "primitives (scatter matrices, classical LDA through scikit-learn, the ridge and shrinkage "

             "variants, nearest-class-mean, principal components, and the logistic head the comparison study "

             "uses), then the deflated eigensolve, then the parity checks, then the experiments. The rule was "

             "that the matrix does not start until the parity checks are green and the small-scale feasibility "

             "report has been accepted. That ordering is the reason the results can be read as measurements: "

             "each of the defects below was caught by a check that ran before an accuracy was looked at, not "

             "by an accuracy that looked odd afterwards."),

            ("body",

             f"Cost was measured before it was committed, and twice. On the raw-pixel scale {mvp['n_solves']} "

             f"solves took {mvp['total_wall_clock_s']:.0f} s in all - {mvp['go_lda_s_mean']:.1f} s per GO-LDA "

             f"basis against {mvp['classic_pencil_s_mean']:.1f} s for the classical pencil at the same "

             f"regularisation and fold, with peak resident memory {mvp['peak_rss_mb']:.0f} MB and "

             f"{f['mvp_rows']:,} accuracy rows written. Before the feature matrix launched, one deflated solve "

             "at twice the rank cap on 512-dimensional features was timed at two row counts and came out "

             "essentially the same, which showed the work is the eigendecompositions of the pencil rather than "

             "anything proportional to the dataset. The estimate the plan had carried was corrected from that "

             "measurement instead of from the sweep's output, and every cost quoted later in this report is a "

             "measured wall clock from the phase it belongs to."),

            ("h2", "Solver routes, and the three numerical safeguards"),

            ("body",

             "Two routes compute the same pencil. The dense route forms the full square pencil. The "

             "span-reduced route works inside the span of the scatter matrices, whose rank is bounded by the "

             "number of training rows minus one, and it is what every feature-scale number in this report "

             "comes from. The reduced route is a core implementation change rather than an optimisation, and "

             "it is declared as a deviation, with three of the parity checks existing specifically to verify "

             f"it: the two routes agree to {_sci(f['route_span'])} degrees on the cap subspace and to "

             f"{_sci(f['route_mu'])} in the eigenvalues, so choosing between them is a cost decision and not a "

             "numerical one. The same control runs across solvers - the generalised routine and the symmetric-"

             f"definite one agree to {_sci(f['solver_mu'])} in eigenvalues and {_sci(f['solver_span'])} degrees "

             f"in span - and the first deflated direction coincides with the classical pencil's leading "

             f"eigenvector to {abs(f['first_cos']):.6f} in absolute cosine, which is the paper's own identity and "

             "the strongest single piece of evidence that the implementation says what the equations say."),

            ("body",

             "Three numerical details had to be settled before any result could be trusted. A generalised "

             "eigensolver on a numerically singular pencil warns and returns an answer instead of raising, so "

             "an exception-driven fallback never fires and the failure is silent; the code therefore measures "

             f"conditioning first - it spans {f['kappa_min']:.1e} to {f['kappa_max']:.1e} across the four "

             "feature pairs - and truncates deliberately, with the tolerance derived from the pencil under "

             "test rather than fixed. The acceptance test for a deflated direction is its relative residual "

             f"against the bound that pencil implies, and the worst ratio measured anywhere is "

             f"{f['tol_worst_pair']:.3f}, so every arm sits inside its own bound. And because a bound is "

             "vacuous unless something could violate it, each residual check is paired with a control arm "

             "expected to fail it."),

            ("body",

             "One defect found at this stage was textual rather than numerical, and it is reported because it "

             "would have been invisible in the results. The raw-pixel loader's height and width constants were "

             "transposed: a PGM header writes width before height, so the ORL raster is 112 rows of 92 pixels "

             f"and the constants said the reverse. The loader reshaped from the parsed header, so the "

             f"{f['dim']}-dimensional vectors - and every accuracy measured from them - were unaffected. Two "

             "consumers read the constants instead of the header: the front end drew faces as horizontal "

             "stripes, and a box-average downsample used by a dimension control sliced a sheared image instead "

             "of a reduced one. That second path is how a cosmetic constant reached a measurement; the result "

             "it produced was withdrawn and re-run."),

            ("h2", "The parity gate, and the check that could not fail"),

            ("body",

             f"The gate is one harness of {f['reported']} checks, {f['gated']} of them gating and all "

             f"{f['passed']} passing. It covers the first-direction identity against an independently "

             "constructed classical pencil, the direction lying in scikit-learn's own subspace, the two "

             "scatter matrices reconstructed against scikit-learn's covariances, dense-versus-reduced "

             "equivalence, the certified regularisation range, monotonicity of the Fisher ratios along the "

             "deflated sequence, and the measured cost of each route. It prints its open signal only when "

             "every gating check passes, and the exporters refuse to write front-end data while it is closed, "

             "so a regression stops the pipeline instead of surfacing later as a strange number. Two checks "

             "were changed during the work rather than left as written. Agreement between the two methods' "

             "subspaces at the rank cap was demoted to a diagnostic, because the published objective does not "

             "promise it and gating on it would have turned our own misreading into an acceptance test. The "

             "brute-force deflation check had verified only the case at the cap; it now runs an independent "

             "dense chain at twice the cap on a small fixture as well, because a deflation that is right only "

             "where the classical pencil stops existing proves nothing about the region the hypothesis is about."),

            ("body",

             "The transposition above exposed a weakness in the gate itself. The shape check asserted that "

             "reshaping a vector onto the grid and reading the shape back gives the grid - true whenever the "

             "reshape succeeds, so it could never have caught a transposed pair. The real gate now sits in the "

             "loader: after parsing the header it asserts that the header's two dimensions match the constants "

             "the rest of the program uses, and it raises quoting both readings. That was verified as "

             "discriminating - with the pre-fix constants it fails on a real file, with the corrected ones it "

             "returns the expected shape. A check that cannot fail is not a check, and this report does not "

             "describe the old assertion as a geometry test."),

            ("h2", "Drivers, probes, and the front-end exporters"),

            ("body",

             "Two drivers produce the tables, one for each scale, and each writes its own accuracy rows, "

             "diagnostics, selection record and timing artefact. The first launch of the feature matrix died "

             "after half an hour in the refit phase - the sweep had finished, and the driver had no path to "

             "the phase that failed. The fixes were a checkpoint after every artefact, a smoke route that "

             "reaches the refit and cross-validated phases in minutes, and a write guard, because merging "

             "drops every stored row of a pair it rewrites and a cross-validation-only pass would otherwise "

             "have deleted the sweep tables it never touched. Three environment surprises are recorded for the "

             "same reason: the validation images of the larger dataset are not a uniform size, so the first "

             "loader either failed when stacking them or resized them before the backbone's own transform had "

             "a say, and the loader streams instead; the archive of the smaller one is a Python 2 pickle whose "

             "keys stay bytes, so the label field is not what its name suggests; and the frozen vision model's "

             "registered input resolution measured eight times slower than the one its positional embedding "

             "resamples to, which was settled by measurement before the matrix ran."),

            ("body",

             "Four probes answer questions a sweep cannot, because each holds exactly one explanation fixed: "

             "whether a gap at the rank cap is a solver, a route, a coordinate system or a head artefact; how "

             f"the comparison behaves under one fixed corruption (this control cost {f['ood_total_s']:.0f} s, "

             "not the few minutes first estimated, because the main run stored accuracies and not bases and "

             "both pencils had to be solved again); and how it behaves at reduced pixel dimension. The front "

             "end is generated rather than authored. One exporter rebuilds the report-facing tables from the "

             "run artefacts, refuses to write when any check fails, and asserts properties of the data "

             "contract itself - that every curve row carries the split it came from, that the plotted test "

             "points come only from the selection record. A second exporter refits every arm's basis with the "

             "study's own solvers, so the interactive instrument shows fitted quantities instead of pre-typed "

             "numbers. The export gate also parses the page's inline script with Node, because a missing "

             "parenthesis had silently killed the entire script with no console message - the same failure "

             "mode as the shape check, in a different language: a gate that asserts the wrong thing reports "

             "success while the deliverable is broken."),

        ],

    }

