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

# The smallest gap worth writing between two figures, in points. The gap itself comes from the block heights
# (`report_fields.figure_block_pt`) and the text area, so it is whatever the page has left; below this size
# there is no empty middle to speak of, and the pair is left to run one under the other.
FIGURE_PAGE_STRUT_MIN_PT = 40.0

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

def _starts_new_page(el) -> bool:
    """Whether the element after an exhibit block already begins a page.

    The blank line that separates an exhibit from what follows is only wanted when something does follow on the
    same page. If the next paragraph carries its own page break, the blank would end up at the top of the new
    page instead of under the exhibit, which is the case U028 excluded.
    """
    if el is None or el.tag != qn("w:p"):
        return False
    pPr = el.find(qn("w:pPr"))
    return pPr is not None and pPr.find(qn("w:pageBreakBefore")) is not None


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


def _set_plain_text(el, text: str):
    """Replace a whole paragraph with literal lines, deleting any field it contained.

    The template's cover name is not text: it is four `ASK` fields (one AuthorName, three StudentNo) that Word
    fills by prompting the person who opens the file. Writing into such a paragraph leaves the field instructions
    alive, so the value disappears the next time Word updates fields, which is exactly what the first filled cover
    did - the examiner's export rendered an empty name line. A submission carries literal values, so the fields
    and their bookmarks come out and the text goes in, in the paragraph's own formatting.
    """
    for child in list(el):
        if child.tag != qn("w:pPr"):
            el.remove(child)
    run = el.makeelement(qn("w:r"), {})
    rpr = run.makeelement(qn("w:rPr"), {})
    lang = rpr.makeelement(qn("w:lang"), {})
    lang.set(qn("w:val"), "en-GB")
    rpr.append(lang)
    run.append(rpr)
    for i, line in enumerate(text.split("\n")):
        if i:
            run.append(run.makeelement(qn("w:br"), {}))
        t = run.makeelement(qn("w:t"), {})
        t.set(qn("xml:space"), "preserve")
        t.text = line
        run.append(t)
    el.find(qn("w:pPr")).addnext(run)


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
            if title == "References":
                # U027: the bibliography opens its own page. Section 7 ran to mid-page 42 and left the heading
                # with three entries squeezed in under it. The break is carried by the heading for the reason
                # given just above - a separate break paragraph reads as another contents entry to the audit.
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

        U028 asked for the gap an exhibit needs on both sides. A blank body line goes in after every exhibit
        block, because a table's ruled edge running straight into the next heading is what the supervisor's
        screenshot of Table 1 showed - except where the element that follows already starts a new page, where
        the blank would sit at the top of that page instead. Two figures sharing a page get a strut rather than a
        blank line: the first stays at the top, the second is pushed to the bottom, and the middle is deliberately
        empty, which is the arrangement U028 asked for and `audit_layout` now measures.

        U031 removed the same kind of waste on the other side: a table whose caption follows a picture no longer
        starts a page just because tables used to. The two block heights plus the gap are compared with the text
        area, and Table 4's 423.9pt fits in what Figure 9 leaves, so page 35 now carries both.
        """
        placed = []
        self.caption_words = 0
        self.struts = []
        self.fits = []
        for (h1, h2), keys in rex.PLACEMENT:
            cursor = self.last.get((h1, h2))
            if cursor is None:
                raise SystemExit(f"exhibit anchor not found: {h1} / {h2}")
            following = cursor.getnext()          # whatever the block will end up in front of
            for index, key in enumerate(keys):
                if key in rex.TABLES:
                    caption, builder = rex.TABLES[key]
                    elements = rf.caption_paragraphs(
                        self.doc, self.protos, "Table", r" SEQ Table \* ARABIC ",
                        str(self.numbers[key]), "_Ref_table_" + key, caption)
                    # U022 gave every table caption a page break, because a table whose rows do not fit under its
                    # caption is stranded the same way a picture is and the caption pair alone cannot hold a page.
                    # U031 measured what that cost: Table 4 needs 423.9pt of the 444.4pt Figure 9 leaves on its
                    # page, and the break spent the rest of the page. A table whose caption follows a picture in
                    # the same block now breaks only when the measured blocks say it must; a table following a
                    # table, or one whose own caption anchors the block, still starts a page.
                    if index and keys[index - 1] not in rex.TABLES:
                        previous = keys[index - 1]
                        room = (rf.TEXT_AREA_PT - rf.EXHIBIT_GAP_PT - rf.TABLE_FLOOR_PT
                                - rf.figure_block_pt(rex.figure_caption(previous), rex.figure_asset(previous))
                                - rex.TABLE_BLOCK_PT[key])
                        if room < 0:
                            pPr = elements[0].get_or_add_pPr()
                            pPr.append(pPr.makeelement(qn("w:pageBreakBefore"), {}))
                    else:
                        room = None
                        pPr = elements[0].get_or_add_pPr()
                        pPr.append(pPr.makeelement(qn("w:pageBreakBefore"), {}))
                    self.fits.append((key, keys[index - 1] if room is not None else "-", room))
                    elements.append(rf.table_element(self.protos, *builder()))
                    is_figure = False
                else:
                    elements = rf.caption_paragraphs(
                        self.doc, self.protos, "Figure", r" SEQ Figure \* ARABIC ",
                        str(self.numbers[key]), "_Ref_figure_" + key, rex.figure_caption(key))
                    elements.append(rf.figure_paragraph(self.doc, rex.figure_asset(key))._p)
                    is_figure = True
                if index and not _starts_new_page(elements[0]):
                    previous = keys[index - 1]
                    previous_is_figure = previous not in rex.TABLES
                    if is_figure and previous_is_figure:
                        # Two figures on one page hold the page to themselves: the first at the top, the second
                        # at the bottom, the middle empty (U028). Whether that is possible is arithmetic, not
                        # pagination: the two blocks plus the gap have to fit the text area, and when they do
                        # not, no gap is written and Word moves the second figure to the top of the next page.
                        # Writing a gap anyway is what left Figure 9's caption 160pt down an empty page.
                        gap = (rf.TEXT_AREA_PT - rf.PAGE_SLACK_PT - rf.PICTURE_UNDER_PT
                               - rf.figure_block_pt(rex.figure_caption(previous), rex.figure_asset(previous))
                               - rf.figure_block_pt(rex.figure_caption(key), rex.figure_asset(key)))
                        if gap >= FIGURE_PAGE_STRUT_MIN_PT:
                            separator = rf.strut_paragraph(self.doc, self.protos, gap)
                            cursor.addnext(separator)
                            cursor = separator
                            self.struts.append((previous, key, round(gap, 1)))
                    else:
                        separator = rf.spacer_paragraph(self.doc, self.protos)
                        cursor.addnext(separator)
                        cursor = separator
                for el in elements:
                    cursor.addnext(el)
                    cursor = el
                self.caption_words += sum(len(_para_text(el).split()) for el in elements[:2])
                placed.append(f"{key} = {self.numbers[key]}")
            if not _starts_new_page(following):
                cursor.addnext(rf.spacer_paragraph(self.doc, self.protos))
        return placed

    def insert_references(self) -> int:
        """Emit the APA 7 list after the References heading, and check it against the prose.

        addnext, not addprevious: the first build put the list at the end of section 7 and left the heading
        alone on its own page, which the page-count audit only noticed because the heading and its entries
        landed two pages apart.
        

        The check runs on the assembled text rather than on the source files, so a citation that was reworded
        away, or an entry that no longer answers anything, stops the build. Works whose bibliographic record is
        not on disk are absent from both sides of that pair, and plan section 12 records them as a release
        request instead of writing author initials from memory.
        """
        cursor = self.h1["References"]
        for text in ref.entries():
            el = rf.styled_paragraph(self.protos["reference"], text)
            cursor.addnext(el)
            cursor = el
        prose = " ".join(_para_text(el) for el in self.doc.element.body.findall(qn("w:p")))
        problems = ref.check(prose)
        if problems:
            raise SystemExit("reference list and prose disagree: " + "; ".join(problems))
        return len(ref.entries())

    def fill_cover(self, cover: dict | None = None) -> list[str]:
        """Write the student's values onto the template's cover; a no-op until the JSON exists.

        Matched by paragraph role rather than by literal placeholder text, because the template splits each token
        across runs ("C" + "ISC" + "XXXX") and builds the name line out of ASK fields, so all three lines are
        replaced whole. The name block is three identical lines for a three-person group; one student means one
        line, not three blanks under it. The date needs the same treatment because the template carries a real
        example date, "06 Apr 2026", rather than a token: nothing would mark it stale if it were left behind.
        """
        if cover is None and COVER_VALUES.exists():
            cover = json.loads(COVER_VALUES.read_text(encoding="utf-8"))
        if not cover:
            return []
        done = []
        for para in self.doc.paragraphs[:12]:
            text = para.text
            if "CISCXXXX" in text:
                new = cover.get("title", "")
            elif "Your Name" in text or "ASK" in text:
                new = cover.get("byline", "")
            elif re.fullmatch(r"\s*\d{2} [A-Za-z]{3} \d{4}\s*", text or " "):
                new = cover.get("date", "")
            else:
                continue
            if new and new != text:
                _set_plain_text(para._p, new)
                done.append(new.split(chr(10))[0])
        if cover.get("author"):
            # the template carries another person's name in its file properties, and a submission checker
            # reads those as readily as the cover
            self.doc.core_properties.author = cover["author"]
            self.doc.core_properties.last_modified_by = cover["author"]
            self.doc.core_properties.title = TITLE
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
    print("figure pairs held on one page, gap written: "
          + (", ".join(f"{a}+{b}={points}pt" for a, b, points in builder.struts) or "none"))
    print("tables after a picture, room left in the text area (negative starts a new page): "
          + (", ".join(f"{key} after {previous}: {room:+.1f}pt"
                       for key, previous, room in builder.fits if room is not None) or "none"))
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
