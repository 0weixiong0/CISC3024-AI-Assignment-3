"""Build the assignment-3 Word report: structure, prose, and Word-side field updates.

Project : CISC3024 AI Assignment #3 (Pattern Recognition, University of Macau)
Author  : AI-generated implementation (Qoder). The student wrote no code.

Input   : Report Template.docx (the official template, never modified), the run artefacts under runs/, and the
          gitignored report_assets/cover_values.json carrying the student's name, number and date.
Output  : CISC3024_AI_Assignment_3_Report.docx

The template's own example paragraphs are used as prototypes for every new paragraph: that is deliberate,
because the template's Heading 1/2 styles are formatted in Calibri Light 16/20 pt. The prototype headings
carry Times New Roman 12pt directly, so style assignment alone leaves the headings looking nothing like the
template's own text.

Why the numbers are not written here
-----------------------------------
`report_content.py` reads every figure from the run artefacts at build time, so this file cannot state a
number that the runs do not support. Sections whose prose is not yet drafted are emitted as an empty shell
so that the structure is reviewable before the text is written.
"""

from __future__ import annotations

import copy
import json
import re
import sys
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn
from docx.table import Table
from docx.text.paragraph import Paragraph

import report_content as rc

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "Report Template.docx"
OUT_DOCX = ROOT / "CISC3024_AI_Assignment_3_Report.docx"
COVER_VALUES = ROOT / "report_assets" / "cover_values.json"

TITLE = ("CISC3024 Assignment 3: Apply a Principal Component Analysis or Linear Discriminant "
         "Analysis Algorithm in Computer Vision or Pattern Recognition")

# The seven content sections, in report order. Sections whose prose has not been drafted yet emit H2s only
# (drafted=False: skeleton), the drafted ones emit H2 + body blocks via `insert_prose`.
SECTIONS = [
    ("Introduction and Human-AI Workflow",
     ["AI use and responsibility", "What this report covers and how it is ordered"], False),
    ("AI-Assisted Literature Search and Algorithm Selection", [], True),
    ("Algorithm Description and Task Adaptation",
     ["GO-LDA's deflated eigensolve", "Baselines and the protocol adapted to this study",
      "Hypotheses fixed before implementation"], False),
    ("AI-Assisted Implementation and Verification", [], True),
    ("Experimental Settings, Results and Discussion",
     ["Datasets, features and the evaluation protocol", "Small-scale feasibility run",
      "Main results and the hypothesis verdicts",
      "Two controls: fixed corruption and reduced pixel dimension",
      "Interpretation, limits and the negative result"], False),
    ("Interactive Visualisation and Source-Code Availability",
     ["The live demo and what the visitor does", "The repository and the Pages site",
      "Citation block for brief item (6)"], False),
    ("Lessons Learned and Conclusion",
     ["What the study concluded", "What the AI collaboration taught us"], False),
    ("References", [], False),
]

# Sections whose prose comes from `report_content.py`.
DRAFTED = {t for t, _, drafted in SECTIONS if drafted}

PLACEHOLDER = re.compile(r"CISCXXXX|DDxxxxxx|YYYY/MM/DD|Your NameXXX|\[T[AB1]\]")


def _para_text(el) -> str:
    out = []
    for node in el.iter():
        if node.tag == qn("w:t") and node.text:
            out.append(node.text)
        elif node.tag in (qn("w:br"), qn("w:cr")):
            out.append("\n")
    return "".join(out)


def _runs(el):
    return [r for r in el.findall(qn("w:r")) if r.find(qn("w:t")) is not None]


def _set_text(el, text: str):
    runs = _runs(el)
    if not runs:
        raise ValueError("paragraph prototype has no text run to carry the replacement")
    target = runs[0]
    for k in target.findall(qn("w:t")) + target.findall(qn("w:br")):
        target.remove(k)
    for i, line in enumerate(text.split("\n")):
        if i:
            target.append(target.makeelement(qn("w:br"), {}))
        t = target.makeelement(qn("w:t"), {})
        t.set(qn("xml:space"), "preserve")
        t.text = line
        target.append(t)
    for r in runs[1:]:
        r.getparent().remove(r)


class Builder:
    def __init__(self, doc, protos):
        self.doc, self.protos = doc, protos
        self.h1 = {}

    # -- skeleton ------------------------------------------------------------
    @classmethod
    def new(cls):
        doc = Document(str(TEMPLATE))
        protos = {}
        want = {"h1": "Heading 1", "h2": "Heading 2", "body": "Normal", "reference": "EndNote Bibliography"}
        for para in doc.paragraphs:
            el = para._p
            if el.getparent() is None or not _runs(el):
                continue
            name = (para.style.name or "") if para.style is not None else ""
            text = _para_text(el).strip()
            for k, style in want.items():
                if k in protos or not name.endswith(style):
                    continue
                if k in ("h1", "h2") and not text:
                    continue
                if k == "body" and text not in ("Put your text here.", "Text.", "text.", "text", "Text"):
                    continue
                protos[k] = el
            if len(protos) == len(want):
                break
        missing = [k for k in want if k not in protos]
        if missing:
            raise SystemExit(f"template prototypes not found: {missing}")

        for el in protos.values():
            el.getparent().remove(el)

        body = doc.element.body
        sdts = body.findall(qn("w:sdt"))
        if not sdts:
            raise SystemExit("template has no w:sdt (the TOC content control); refusing to guess the cut")
        tail = body.find(qn("w:sectPr"))
        past = False
        for el in list(body):
            if el is sdts[-1]:
                past = True
                continue
            if past and el is not tail:
                body.remove(el)

        builder = cls(doc, protos)
        for title, subs, drafted in SECTIONS:
            proto = protos["reference"] if title == "References" else protos["h1"]
            el = copy.deepcopy(proto)
            _set_text(el, title)
            if tail is not None:
                tail.addprevious(el)
            else:
                body.append(el)
            builder.h1[title] = el
            prev = el
            for sub in subs:
                e2 = copy.deepcopy(protos["h2"])
                _set_text(e2, sub)
                prev.addnext(e2)
                prev = e2
        return builder

    # -- content -------------------------------------------------------------
    def blocks(self) -> dict:
        """H1 title -> list of (kind, text) blocks for drafted sections."""
        return {
            **rc.search_sections(rc.search_facts()),
            **rc.implementation_sections(rc.facts()),
        }

    def insert_prose(self) -> list[str]:
        """Insert drafted-section blocks under the heading, in report order."""
        content = self.blocks()
        written = []
        for i, (title, _, drafted) in enumerate(SECTIONS):
            if not drafted or title not in content:
                continue
            anchor = None
            for nxt, _, _d in SECTIONS[i + 1:]:
                if nxt in self.h1:
                    anchor = self.h1[nxt]
                    break
            if anchor is None:
                raise SystemExit(f"anchor not found for section {title}")
            for kind, text in content[title]:
                proto = self.protos["h2" if kind == "h2" else "body"]
                el = copy.deepcopy(proto)
                _set_text(el, text)
                anchor.addprevious(el)
                written.append(f"{title}: {text.splitlines()[0][:44]}")
        return written

    def fill_cover(self, cover: dict | None = None) -> list[str]:
        """Write the student's values onto the template's cover; a no-op until the JSON exists."""
        if cover is None and COVER_VALUES.exists():
            cover = json.loads(COVER_VALUES.read_text(encoding="utf-8"))
        if not cover:
            return []
        mapping = {
            "CISCXXXX YYYY": TITLE,
            "Your NameXXX, Student No: DDxxxxxx": cover.get("byline", ""),
            "YYYY/MM/DD": cover.get("date", ""),
        }
        done = []
        for para in self.doc.paragraphs:
            text, hit = para.text, False
            for token, value in mapping.items():
                if value and token in text:
                    text = text.replace(token, value)
                    hit = True
                    done.append(token)
            if hit:
                _set_text(para._p, text)
        return done

    def update_toc_and_fields(self) -> None:
        try:
            import win32com.client
        except ImportError:
            print("note: pywin32 absent; TOC/field update skipped (run src/export_pdf.py)")
            return
        app = win32com.client.DispatchEx("Word.Application")
        app.Visible = False
        try:
            d = app.Documents.Open(str(OUT_DOCX))
            d.Fields.Update()
            d.Save()
            d.Close()
        finally:
            app.Quit()

    def summarize(self) -> dict:
        paras = [Paragraph(el, self.doc) for el in self.doc.element.body.findall(qn("w:p"))]
        prose_words = sum(len(_para_text(p._p).split()) for p in paras
                          if p.style is not None and not p.style.name.startswith("Heading"))
        heads = [(p.style.name, _para_text(p._p)) for p in paras
                 if p.style is not None and p.style.name.startswith("Heading")]
        tables = [Table(t, self.doc) for t in self.doc.element.body.findall(qn("w:tbl"))]
        return {

            "paragraphs": len(paras),
            "prose_words": prose_words,
            "headings": len(heads),
            "tables": len(tables),
            "h1": [t for s, t in heads if s.endswith("Heading 1")],
            "h2": [t for s, t in heads if s.endswith("Heading 2")],
        }

    def save(self) -> Path:
        self.doc.save(str(OUT_DOCX))
        return OUT_DOCX


def main() -> int:
    builder = Builder.new()
    cover = builder.fill_cover()
    prose = builder.insert_prose()
    path = builder.save()
    stats = builder.summarize()
    print(f"built {path.name}: {stats['headings']} headings ({len(stats['h1'])} H1 / "
          f"{len(stats['h2'])} H2), {stats['tables']} tables, {stats['prose_words']} prose words")
    print(f"cover fields filled: {len(cover)}"
          f"{'  (pending: report_assets/cover_values.json absent)' if not cover else ''}")
    print(f"prose blocks inserted: {len(prose)}")
    for h1 in stats["h1"]:
        print("  H1:", h1)
    tokens = [t for t in stats["h1"] + stats["h2"] if PLACEHOLDER.search(t)]
    print("placeholder tokens still on the page:", tokens or "none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
