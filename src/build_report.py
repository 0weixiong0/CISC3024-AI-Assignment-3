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
import report_references as ref
import report_sections67 as r67
import report_exhibits as rex
import report_fields as rf

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "Report Template.docx"
OUT_DOCX = ROOT / "CISC3024_AI_Assignment_3_Report.docx"
COVER_VALUES = ROOT / "report_assets" / "cover_values.json"

TITLE = ("CISC3024 Assignment 3: Apply a Principal Component Analysis or Linear Discriminant "
         "Analysis Algorithm in Computer Vision or Pattern Recognition")

# The seven content sections, in report order. Sections whose prose has not been drafted yet emit H2s only
# (drafted=False: skeleton), the drafted ones emit H2 + body blocks via `insert_prose`.
SECTIONS = [
    ("Introduction and Human-AI Workflow", [], True),
    ("AI-Assisted Literature Search and Algorithm Selection", [], True),
    ("Algorithm Description and Task Adaptation", [], True),
    ("AI-Assisted Implementation and Verification", [], True),
    ("Experimental Settings, Results and Discussion", [], True),
    ("Interactive Visualisation and Source-Code Availability", [], True),
    ("Lessons Learned and Conclusion", [], True),
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


def _style_sizes(doc) -> dict:
    """Half-point size per style name, resolved through based_on and docDefaults."""
    styles = doc.styles.element
    direct, by_name = {}, {}
    for st in styles.findall(qn("w:style")):
        name_el = st.find(qn("w:name"))
        if name_el is None:
            continue
        name = name_el.get(qn("w:val"))
        by_name[name] = st
        rPr = st.find(qn("w:rPr"))
        sz = rPr.find(qn("w:sz")) if rPr is not None else None
        direct[name] = int(sz.get(qn("w:val"))) if sz is not None else None
    base = 24
    defaults = styles.find(qn("w:docDefaults"))
    if defaults is not None:
        rPrDefault = defaults.find(qn("w:rPrDefault"))
        rPr = rPrDefault.find(qn("w:rPr")) if rPrDefault is not None else None
        sz = rPr.find(qn("w:sz")) if rPr is not None else None
        if sz is not None:
            base = int(sz.get(qn("w:val")))

    def resolve(name, seen=()):
        if not name or name in seen:
            return base
        if direct.get(name):
            return direct[name]
        st = by_name.get(name)
        based = st.find(qn("w:basedOn")) if st is not None else None
        return resolve(based.get(qn("w:val")) if based is not None else None, seen + (name,))

    return {name: resolve(name) for name in by_name}


def explicit_sizes(doc) -> int:
    """Write each run's already-resolved size into the run, so the font census has no None entries.

    The template's example paragraphs inherit their size from the style instead of carrying it, and Word
    re-splits runs when it resolves fields, so the audit reads a run as "Times New Roman, no size" even
    though it renders at 12 pt. Recording the resolved value changes nothing on the page and turns the
    census into a check that can actually fail.
    """
    sizes = _style_sizes(doc)
    written = 0
    for para in doc.paragraphs:
        size = sizes.get((para.style.name or "") if para.style is not None else "Normal", 24)
        for run in para._p.iter(qn("w:r")):
            rPr = run.find(qn("w:rPr"))
            if rPr is None:
                rPr = run.makeelement(qn("w:rPr"), {})
                run.insert(0, rPr)
            if rPr.find(qn("w:sz")) is not None:
                continue
            for tag in ("w:sz", "w:szCs"):
                rPr.append(rPr.makeelement(qn(tag), {qn("w:val"): str(size)}))
                written += 1
    return written


class Builder:
    def __init__(self, doc, protos):
        self.doc, self.protos = doc, protos
        self.h1 = {}
        self.last: dict[tuple[str, str | None], object] = {}
        self.numbers, self.refs = self._number_exhibits()

    @staticmethod
    def _number_exhibits() -> tuple[dict[str, int], dict[str, str]]:
        """Assign Figure/Table numbers in the order PLACEMENT puts the exhibits on the page.

        The caption carries a SEQ field, so Word renumbers these itself when fields update; the cached result
        and the REF fields are written from this pass so the document is already correct before anything is
        updated, and so the audit can read the numbers without Word.
        """
        numbers, refs, figure, table = {}, {}, 0, 0
        for _anchor, keys in rex.PLACEMENT:
            for key in keys:
                if key in rex.TABLES:
                    table += 1
                    numbers[key], refs["_Ref_table_" + key] = table, str(table)
                else:
                    figure += 1
                    numbers[key], refs["_Ref_figure_" + key] = figure, str(figure)
        return numbers, refs

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
            el = copy.deepcopy(protos["h1"])
            _set_text(el, title)
            if not builder.h1:
                # The contents field is resolved by Word and runs longer than its own page, so the first
                # section would otherwise start underneath its last entry. pageBreakBefore is carried by
                # the heading itself, which keeps the contents region a single block for the audit.
                pPr = el.get_or_add_pPr()
                pPr.append(pPr.makeelement(qn("w:pageBreakBefore"), {}))
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

    def make_sizes_explicit(self) -> int:
        """Give every run the size it already resolves to, so the font census has no None entries."""
        return explicit_sizes(self.doc)

    # -- content -------------------------------------------------------------
    def blocks(self) -> dict:
        """H1 title -> list of (kind, text) blocks for drafted sections."""
        return {
            **rc.intro_sections(),
            **rc.search_sections(rc.search_facts()),
            **rc.algorithm_sections(rc.facts()),
            **rc.implementation_sections(rc.facts()),
            **rc.results_sections(rc.results_facts()),
            **r67.visualisation_sections(),
            **r67.lessons_sections(rc.facts(), rc.results_facts()),
        }

    def insert_prose(self) -> list[str]:
        """Insert drafted-section blocks under the heading, in report order, tracking where each H2 ends."""
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
            current_h2 = None
            for kind, text in content[title]:
                if kind == "h2":
                    current_h2 = text
                proto = self.protos["h2" if kind == "h2" else "body"]
                if kind == "h2":
                    el = copy.deepcopy(proto)
                    _set_text(el, text)
                else:
                    el = rf.rich_paragraph(proto, text, self.refs)
                anchor.addprevious(el)
                self.last[(title, current_h2)] = el
                written.append(f"{title}: {text.splitlines()[0][:44]}")
        return written

    def place_exhibits(self) -> list[str]:
        """Emit each exhibit after the last paragraph of the heading whose prose cites it.

        The anchor is the heading's final paragraph, recorded while the prose went in, so an exhibit can never
        drift away from the claim it supports when the text around it is edited: if the heading disappears the
        build stops instead of dropping the exhibit silently.
        """
        placed = []
        self.caption_words = 0
        for (h1, h2), keys in rex.PLACEMENT:
            cursor = self.last.get((h1, h2))
            if cursor is None:
                raise SystemExit(f"exhibit anchor not found: {h1} / {h2}")
            for key in keys:
                if key in rex.TABLES:
                    caption, builder = rex.TABLES[key]
                    elements = rf.caption_paragraphs(
                        self.doc, self.protos, "Table", r" SEQ Table \* ARABIC ",
                        str(self.numbers[key]), "_Ref_table_" + key, caption)
                    # A table that does not fit under its caption is stranded the same way a picture is, and
                    # the caption pair is too short to hold a page for itself: tables start on a new page.
                    pPr = elements[0].get_or_add_pPr()
                    pPr.append(pPr.makeelement(qn("w:pageBreakBefore"), {}))
                    elements.append(rf.table_element(self.protos, *builder()))
                else:
                    elements = rf.caption_paragraphs(
                        self.doc, self.protos, "Figure", r" SEQ Figure \* ARABIC ",
                        str(self.numbers[key]), "_Ref_figure_" + key, rex.figure_caption(key))
                    elements.append(rf.figure_paragraph(self.doc, rex.figure_asset(key))._p)
                for el in elements:
                    cursor.addnext(el)
                    cursor = el
                self.caption_words += sum(len(_para_text(el).split()) for el in elements[:2])
                placed.append(f"{key} = {self.numbers[key]}")
        return placed

    def insert_references(self) -> int:
        """Emit the APA 7 list under the References heading, and check it against the prose.

        The check runs on the assembled text rather than on the source files, so a citation that was reworded
        away, or an entry that no longer answers anything, stops the build. Works whose bibliographic record is
        not on disk are absent from both sides of that pair, and plan section 12 records them as a release
        request instead of writing author initials from memory.
        """
        anchor = self.h1["References"]
        tail = anchor.getnext()
        for text in ref.entries():
            el = copy.deepcopy(self.protos["reference"])
            _set_text(el, text)
            anchor.addprevious(el)
            anchor = el
        prose = " ".join(_para_text(el) for el in self.doc.element.body.findall(qn("w:p")))
        problems = ref.check(prose)
        if problems:
            raise SystemExit("reference list and prose disagree: " + "; ".join(problems))
        return len(ref.entries())

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
        # The prose unit is the argument the reader reads: headings, exhibit captions and the reference list
        # are counted apart, because a citation that grows longer must not read as an essay that grew longer.
        excluded = ("Heading", "EndNote Bibliography")
        prose_words = sum(len(_para_text(p._p).split()) for p in paras
                          if p.style is not None and not any(p.style.name.startswith(e) for e in excluded))
        heads = [(p.style.name, _para_text(p._p)) for p in paras
                 if p.style is not None and p.style.name.startswith("Heading")]
        tables = [Table(t, self.doc) for t in self.doc.element.body.findall(qn("w:tbl"))]
        return {

            "paragraphs": len(paras),
            "prose_words": prose_words,
            "headings": len(heads),
            "tables": len(tables),
            "figures": len(self.doc.inline_shapes) - 1,  # the template's cover logo is the tenth shape
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
    exhibits = builder.place_exhibits()
    entries = builder.insert_references()
    sized = builder.make_sizes_explicit()
    path = builder.save()
    stats = builder.summarize()
    print(f"built {path.name}: {stats['headings']} headings ({len(stats['h1'])} H1 / "
          f"{len(stats['h2'])} H2), {stats['tables']} tables, {stats['figures']} figures, "
          f"{stats['prose_words']} prose words")
    print("exhibit numbering: " + ", ".join(exhibits))
    print(f"reference entries: {entries}, each one cited in the text")
    print(f"prose without exhibit captions: {stats['prose_words'] - builder.caption_words}, "
          f"caption words: {builder.caption_words}")
    print(f"cover fields filled: {len(cover)}"
          f"{'  (pending: report_assets/cover_values.json absent)' if not cover else ''}")
    print(f"prose blocks inserted: {len(prose)}, run sizes made explicit: {sized}")
    for h1 in stats["h1"]:
        print("  H1:", h1)
    tokens = [t for t in stats["h1"] + stats["h2"] if PLACEHOLDER.search(t)]
    print("placeholder tokens still on the page:", tokens or "none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
