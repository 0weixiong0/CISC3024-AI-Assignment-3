"""Sections 6 and 7 of the report: the public page, and what the study and the collaboration left behind.

Project : CISC3024 AI Assignment #3 (Pattern Recognition, University of Macau)
Author  : AI-generated implementation (Qoder). The student wrote no code.

Split out of `report_content.py` only because that file is already the longest module in the project. The
numbers here come from the same fact dictionaries as every other section, so a re-run moves this text with the
rest: nothing in these two sections is typed by hand except the two public addresses and the wording.
"""

from __future__ import annotations


def _sci(value: float) -> str:
    return f"{value:.1e}"


def _pt(fraction: float) -> str:
    return f"{100 * fraction:+.2f}"


def visualisation_sections() -> dict:
    """Section 6: the demo, what is public, and the sentence the brief asks for. About 250 prose words."""
    repo = "https://github.com/0weixiong0/CISC3024-AI-Assignment-3"
    pages = "https://0weixiong0.github.io/CISC3024-AI-Assignment-3/"
    return {
        "Interactive Visualisation and Source-Code Availability": [
            ("h2", "The live demo and what the visitor does"),
            ("body",
             "The front end is one static page with four tabs, and nothing on it is fitted in the browser. "
             "What the visitor sees was computed by the code the study ran and written into the page as data. The first tab is an instrument: pick a regime and method, drag K, or click a row of "
             "faces, and the accuracy read-out moves with the growth curve, the per-direction Fisher ratios, "
             "the orthogonality corner of the accepted basis, the specimen scatter and the class ranks by K. "
             "In the raw-pixel regime the directions themselves appear as pictures at the raster's own size. The second tab replays the corruption control arm by arm, the third plots "
             "the pixel-dimension ladder, and the fourth lists the run tables beside the artefact each number "
             "came from. Every read-out names its split, because hold-out and test readings of one "
             "configuration differ by several points and a page that hides which is which invites the "
             "comparison this report refuses to draw."),
            ("h2", "The repository and the Pages site"),
            ("body",
             "Both are public. The repository holds the project's modules, the three audit "
             "scripts and the parity test, the front-end assets, the run tables and diagnostics as "
             "json, the stage records and the requirements file. The Pages site is built from that same "
             "repository, so the demo an examiner opens is generated from the artefacts this report quotes "
             "rather than from a copy. The dialogue record travels with the submission as a separate "
             "attachment, not on the public page."),
            ("h2", "Source Code and Live Demo"),
            ("body", f"The source page is {repo}."),
            ("body", f"The live page is {pages}"),
            ("body",
             "The algorithm's own implementation by its authors, and the two comparison sources this study "
             "follows, are listed in the references with their repository addresses."),
        ],
    }


def lessons_sections(f: dict, r: dict) -> dict:
    """Section 7: what the study concluded, and what directing the work taught the student. About 750 prose words."""
    deficits = ", ".join(f"{_pt(-v)} points" for v in r["deficit"].values())
    ladder = ", ".join(f"M = {m} at {_pt(d)}" for m, _share, d in r["ladder"])
    knn = _pt(r["head_gap"]["knn1_raw"])
    return {
        "Lessons Learned and Conclusion": [
            ("h2", "What the study concluded"),
            ("body",
             "Three things, in the order that makes the second honest. Using AI tooling end to end, the "
             "study reproduced a recent member of the linear-discriminant family and the mechanism it "
             "claims: the accepted directions are orthogonal in the ordinary sense to "
             f"{_sci(f['go_offdiag'])}, each one is individually the more discriminative direction, and the "
             "construction was certified against an independent reconstruction of the full-space pencil, by "
             f"two routes and two solvers agreeing to within {_sci(f['solver_span'])} degrees of subspace "
             "angle. That part of the paper is right, and it survived every check built for it."),
            ("body",
             "Its published advantage did not survive the move out of the paper's regime. On frozen deep "
             f"features GO-LDA finishes below the best classical baseline in all four pairs - by {deficits} "
             f"- and the gap is widest where the head is weakest, {knn} points under the nearest-neighbour "
             "classifier the face rows use. Going past the rank cap buys back accuracy the baselines "
             "already hold: the curve rises with K, as the mechanism predicts, and never reaches the cap "
             "value of a classical arm. The negative result does not rest on a single run: it is the matrix, two "
             "released controls, a head sweep and a ten-fold reading of the same configurations."),
            ("body",
             "The lesson is about evidence, not about the algorithm. Parity at the cap belongs to the "
             "raw-pixel corner of the design, where the cap is a fraction of a per cent of the space and "
             "nine images per class make the within-class scatter so degenerate that deflation has almost "
             f"nothing to remove. Shrinking the pixel dimension at fixed classes found no trend to explain "
             f"that away: the paired difference against the ridge pencil was {ladder}. What the paper "
             "measured where the cap is small does not transfer to where it is large, and the honest way to "
             "find that out is to look for the coincidence's precondition instead of assuming a "
             "theorem. The construction is sound and cheap; its accuracy in a "
             "feature regime still has to be measured, not taken from the paper."),
            ("h2", "Lessons in Directing and Checking AI"),
            ("body",
             "The lessons are best read in the order the rulings were made. The first is that an instruction "
             "earns its place only if someone else can check it afterwards: the constraints that held were "
             "written that way before the search - a recency floor for the candidates, the classifier used in "
             f"each regime, the δ convention the parity gate is judged under, the K grid a hypothesis about "
             "going past the rank cap needs. What came back for correction was the looser form of the same "
             f"intention: a control cost quoted as about three minutes when the run took {r['ood_s']:.0f} s, "
             f"and a grid described by its nominal size when the file on disk holds {r['mvp_rows']:,} rows."),
            ("body",
             "The second lesson is that a check which cannot fail is not evidence. The geometry assertion in "
             "the parity harness compared a reshaped array with the shape it had just been reshaped to, which "
             "is true whenever the reshape does not raise. The ruling named it tautological and moved the real "
             "gate into the PGM reader, where the parsed header is compared with the constants the loader uses, "
             "adding that the report must not call the old print a geometry check. With those constants set "
             "back to the superseded pair the reader refuses the file, which is what the assertion lacked."),
            ("body",
             "The third lesson is that reading still does work the machinery does not. Three defects in the "
             "report's own week reached the tooling by eye first: a caption field that printed its label word "
             "twice, table cells that looked centred because they had inherited the template's justification "
             "without saying so, an exhibit that took a fifth of its page and left the rest empty. Each became "
             "a gate afterwards, so the audit now measures what was only noticed. The arithmetic defects went "
             "the other way - a drift measure comparing a construction against itself, a probe measuring a "
             "different object than its label named, a run whose pictures were sheared by two transposed loader "
             "constants - caught inside the pipeline, one of them after it had moved a conclusion."),
            ("body",
             "What carries forward is a shape of working rather than a technique. The form of the deliverable "
             "was paid for twice: the front end came out as a second report, which is what he had objected to "
             "in Assignment 2, in his words it only got fixed late. The prose ceiling is 6,500 words, set once, "
             "with the sections taking the first cut named in advance. And the dialogue record is kept as the "
             "work happens, which is why a ruling from early November can still be quoted here."),
        ],
    }
