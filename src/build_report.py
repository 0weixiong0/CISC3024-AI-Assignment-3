"""Build the Assignment 3 report from the approved course template: structure only, no prose yet.

Project : CISC3024 AI Assignment #3 (Pattern Recognition, University of Macau)
Author  : AI-generated implementation (Qoder). The student wrote no code.

Why the template's own paragraphs are copied rather than styles being assigned
-----------------------------------------------------------------------------
`Report Template.docx` defines heading 1 as Calibri Light 16 pt and heading 2 as 20 pt, but its
**example** heading paragraphs additionally carry direct run properties of Times New Roman 12 pt.
Assigning the paragraph style alone therefore produces headings that do not look like the template -
this is the failure that cost Assignment 2 its formatting marks. So the example paragraphs are read
out first and used as prototypes: every paragraph this builder emits is a deep copy of one of them,
with the text replaced. The cover paragraphs and the TOC content control are never touched.

Stage-5 step 1 of `research_records/stage_05_report_plan.md` §7: shells and audits before text.
"""

from __future__ import annotations

import copy
import sys
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "Report Template.docx"
OUT = ROOT / "CISC3024_AI_Assignment_3_Report.docx"

# The approved framework (stage_05_report_plan.md §1) mapped onto the A1/A2 chapter skeleton:
# seven unnumbered top-level sections, References last, no Acknowledgements.
SECTIONS = [
    ("Introduction and Human-AI Workflow", [
        "Assignment scope and the algorithm chosen",
        "Human supervision and AI responsibilities",
    ]),
    ("AI-Assisted Literature Search and Algorithm Selection", [
        "Search protocol and candidate scoring",
        "Screening outcomes and the chosen algorithm",
        "Corrections the search produced",
    ]),
    ("Algorithm Description and Task Adaptation", [
        "GO-LDA's deflated eigensolve",
        "Baselines and the protocol adapted to this study",
        "Hypotheses fixed before implementation",
    ]),
    ("AI-Assisted Implementation and Verification", [
        "Solver routes and numerical safeguards",
        "The parity gate and its checks",
        "Drivers, probes and the front-end exporters",
    ]),
    ("Experimental Settings, Results and Discussion", [
        "Datasets, features and heads",
        "Raw-pixel scale: the pilot",
        "Feature scale: the full matrix",
        "The four controls",
        "What the evidence supports, and what it does not",
    ]),
    ("Interactive Visualisation and Source-Code Availability", [
        "The instrument and what each read-out is computed from",
        "The controls as views",
        "Source code and live pages",
    ]),
    ("Lessons Learned and Conclusion", [
        "What the replication established",
        "What the process taught us",
    ]),
]


def find_prototypes(doc: Document) -> dict:
    """One example paragraph per role, taken from the template's own body."""
    want = {"Heading 1": "h1", "Heading 2": "h2", "Heading 3": "h3",
            "EndNote Bibliography": "reference"}
    proto: dict[str, object] = {}
    for p in doc.paragraphs:
        role = want.get(p.style.name if p.style else "")
        if role and role not in proto and p.text.strip():
            proto[role] = copy.deepcopy(p._element)
        if p.style is None:
            continue
        # The example body text and the two-line exhibit labels are both Normal paragraphs; they are
        # told apart by spacing, which is exactly what the audit's caption regex relies on.
        if p.style.name == "Normal" and p.text.strip():
            spacing = p._element.find(qn("w:pPr"))
            line = None
            if spacing is not None:
                sp = spacing.find(qn("w:spacing"))
                line = sp.get(qn("w:line")) if sp is not None else None
            if line == "480" and "body" not in proto:
                proto["body"] = copy.deepcopy(p._element)
            if line == "360" and p.text.strip() in ("Table 1", "Figure 1") and "caption" not in proto:
                proto["caption"] = copy.deepcopy(p._element)
            if line == "360" and p.text.strip() in ("Table text", "Figure Text") and "caption_text" not in proto:
                proto["caption_text"] = copy.deepcopy(p._element)
    missing = {"h1", "h2", "h3", "body", "caption", "caption_text", "reference"} - set(proto)
    if missing:
        raise SystemExit(f"template prototypes not found: {sorted(missing)}")
    return proto


def element_position(body) -> int:
    """Index of w:sectPr, so new paragraphs stay inside the document body."""
    for i, child in enumerate(body):
        if child.tag == qn("w:sectPr"):
            return i
    return len(body)


def set_text(node, text: str) -> None:
    """Replace a cloned paragraph's runs with one run carrying the new text."""
    runs = node.findall(qn("w:r"))
    for run in runs[1:]:
        node.remove(run)
    first = runs[0]
    for t in first.findall(qn("w:t")):
        first.remove(t)
    from docx.oxml import OxmlElement
    t = OxmlElement("w:t")
    t.text = text
    t.set(qn("xml:space"), "preserve")
    first.append(t)


def main() -> int:
    if not TEMPLATE.is_file():
        print(f"missing template: {TEMPLATE}")
        return 1
    doc = Document(str(TEMPLATE))
    proto = find_prototypes(doc)
    body = doc.element.body

    # Everything after the TOC content control is the template's worked example: drop it, keeping the
    # cover, the TOC field itself and the trailing section properties.
    toc_index = next(i for i, child in enumerate(body) if child.tag == qn("w:sdt"))
    for child in list(body)[toc_index + 1:]:
        if child.tag == qn("w:sectPr"):
            continue
        body.remove(child)

    def add(role: str, text: str) -> None:
        node = copy.deepcopy(proto[role])
        set_text(node, text)
        body.insert(element_position(body), node)

    for title, subs in SECTIONS:
        add("h1", title)
        for sub in subs:
            add("h2", sub)
            add("body", "")
    add("h1", "References")

    doc.save(str(OUT))
    print(f"wrote {OUT}")
    print(f"sections: {len(SECTIONS)} H1, "
          f"{sum(len(s) for _, s in SECTIONS)} H2, plus References")
    print("next: python src/export_pdf.py  (resolves the TOC field), then the two audits")
    return 0


if __name__ == "__main__":
    sys.exit(main())
