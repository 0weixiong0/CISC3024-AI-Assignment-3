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
             "The front end is one static page with four tabs, and nothing on it is fitted in the browser: "
             "every quantity it shows was computed by the same code the study ran and then written into the "
             "page. The first tab is an instrument. Pick a regime and a method, drag K, or click a row of "
             "faces, and the accuracy read-out, the growth curve, the per-direction Fisher ratios, the "
             "orthogonality corner of the accepted basis, the scatter of the specimens in two dimensions and "
             "the class ranks by K all move together; in the raw-pixel regime the discriminant directions "
             "themselves appear as pictures at the raster's own size. The second tab replays the corruption "
             "control arm by arm, the third plots the pixel-dimension ladder, and the fourth lists the run "
             "tables beside the artefact each number came from. Every read-out carries the split it belongs "
             "to, because the hold-out and test readings of one configuration differ by several points and "
             "the page would otherwise invite the comparison this report refuses to draw."),
            ("h2", "The repository and the Pages site"),
            ("body",
             "Both are public. The repository holds the project's modules, including the three audit "
             "scripts and the parity test, the front-end assets, the run tables and diagnostics as csv and "
             "json, the stage records and the requirements file. The Pages site is built from that same "
             "repository, so the demo an examiner opens is generated from the artefacts this report quotes "
             "rather than from a copy of them. The dialogue record travels with the submission as a separate "
             "attachment and is not linked from the public page."),
            ("h2", "Citation block for brief item (6)"),
            ("body",
             "The sentence the brief asks for, in the form it is submitted, with each address on a line of "
             "its own so that copying it cannot pick up a line break:"),
            ("body", f"All codes and the raw experiment logs can be found at {repo}."),
            ("body", f"The published demo, generated from those same logs, is at {pages}"),
            ("body",
             "The algorithm's own implementation by its authors, and the two comparison sources this study "
             "follows, are listed in the references with their repository addresses."),
        ],
    }


def lessons_sections(f: dict, r: dict) -> dict:
    """Section 7: what the study concluded and what the collaboration taught us. About 600 prose words."""
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
             f"two routes and two solvers that agree to within {_sci(f['solver_span'])} degrees of subspace "
             "angle. That part of the paper is right, and it survived every check that was built for it."),
            ("body",
             "Its published advantage did not survive the move out of the paper's regime. On frozen deep "
             f"features GO-LDA finishes below the best classical baseline in all four pairs - by {deficits} "
             f"- and the gap is widest where the head is weakest, {knn} points under the nearest-neighbour "
             "classifier that the face rows use. Going past the rank cap buys back accuracy the baselines "
             "already hold: the curve rises with K, as the mechanism predicts, and never reaches the cap "
             "value of a classical arm. A negative result of that size is not one run; it is the matrix, two "
             "released controls, a head sweep and a ten-fold reading of the same configurations."),
            ("body",
             "The lesson is about evidence rather than about the algorithm. Parity at the cap belongs to the "
             "raw-pixel corner of the design, where the cap is a fraction of a per cent of the space and "
             "nine images per class make the within-class scatter so degenerate that deflation has almost "
             f"nothing to remove. Shrinking the pixel dimension at fixed classes found no trend to explain "
             f"that away: the paired difference against the ridge pencil was {ladder} points. What the paper "
             "measured where the cap is small does not transfer to where it is large, and the honest way to "
             "find that out is to look for the precondition of the coincidence instead of assuming a "
             "theorem. For a reader who wants Euclidean-orthogonal directions the practical conclusion is "
             "that the construction is sound and cheap, and that its accuracy in a feature regime has to be "
             "measured rather than inherited."),
            ("h2", "What the AI collaboration taught us"),
            ("body",
             "The division of labour was fixed before it started and it held. The AI tool searched and "
             "scored the literature, designed and wrote every line of the implementation and the audits, ran "
             "the experiments, drafted the figures, the tables and this text, and built the page. The "
             "student set the constraints, ruled on every question the tool could not settle from the brief, "
             "and approved each download and each release. Thirteen rulings and sixteen "
             "recorded corrections are in the appendix ledger, which is the evidence for that sentence."),
            ("body",
             "What the collaboration got wrong is the more useful part of the record, because every failure "
             "was caught by a check rather than by reading. The first drift measure compared the new "
             "construction against itself and reported no divergence, which was arithmetically true and "
             "substantively nothing; the corrected comparison put the first divergence at the third "
             "direction. A probe that reported a classical basis as orthogonal to fourteen decimal places "
             "had measured a different object from the one its label claimed. The sharpest case was a "
             "self-written gate that accepted a first direction identical to the classical one to one "
             "decimal place and then read that as evidence for the hypothesis it existed to test; the remedy "
             "was an arm that must fail the same assertion, and the tolerance is now reported rather than "
             "assumed. A withdrawn run, in which transposed loader constants made a reduction look like a "
             "reversal, was found only because the numbers were checked against the raster they came from."),
            ("body",
             "Three habits carried the rest of the way. Gate the artefact and not the claim: every number in "
             "this report is read from a file when the document is built, so a table that disagrees with a "
             "run stops the build. Keep provenance beside the asset: each figure records the page or the fit "
             "it was drawn from, which is what let four wrong captions be corrected in one pass. And run the "
             "audit before reporting, because the two most persistent defects were invisible on the page - a "
             "heading the contents field listed although the document did not have it, and runs carrying a "
             "font with no recorded size. The tool is fast at producing text and slow to doubt it, and almost "
             "every correction in the ledger began with someone asking what a number would have to be for "
             "the sentence to be false."),
        ],
    }
