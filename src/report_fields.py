"""Word-side machinery for report exhibits: caption fields, cross-reference fields, tables, pictures.

Project : CISC3024 AI Assignment #3 (Pattern Recognition, University of Macau)
Author  : AI-generated implementation (Qoder). The student wrote no code.

The brief's exhibit labels are fields, not typed numbers. A caption carries a `SEQ` field, so inserting an
earlier figure renumbers everything after it, and an in-text mention carries a `REF` field pointing at a
bookmark around that caption, so a reference cannot silently disagree with the object it names. Both fields
carry a cached result, which is what the audit reads and what Word shows before it updates anything.

Tables are written as raw OOXML rather than through the convenience API because the census in
`audit_docx.py` reads run-level fonts: every cell run has to carry Times New Roman and an explicit size, or
the document inherits the template's default and the check stops meaning anything.
"""

from __future__ import annotations

import copy
import re
import struct
from pathlib import Path

from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches

TOKEN = re.compile(r"\{\{(Figure|Table):([a-z0-9_]+)\}\}")

TEXT_WIDTH_IN = 6.0
# The template's text area is 9.0 in tall. An image taller than the area minus its two caption lines cannot
# share a page with them, and Word then leaves the caption alone at the top of a page - the defect
# audit_layout.py's caption checks exist to catch.
MAX_FIGURE_HEIGHT_IN = 8.0 - 1.6

# The height of one rendered exhibit block, in points, added from measurements on the exported page. Word
# does not report these numbers, and the builder needs them before pagination: they are the only way to tell
# whether two figures can share a page, which decides whether the empty middle belongs in the document at all.
# A strut written where the pair does not fit pushes the second figure onto the next page and leaves its
# caption floating 160pt down an empty page, which is the defect audit_layout's first-exhibit rule caught.
TEXT_AREA_PT = 9.0 * 72           # the section properties: 11in page, 1in margins
CAPTION_FIRST_STEP = 32.6         # label top to first description top, as the template's own pair renders
CAPTION_LINE_PITCH = 20.7         # 1.5 spacing on 12pt Times
CAPTION_LINE_HEIGHT = 13.3
PICTURE_OVER_PT = 18.8            # description bottom to image top, measured on page 26
PICTURE_UNDER_PT = 18.5           # image bottom to the next block's top, measured on page 26
PAGE_SLACK_PT = 36.0              # Word keeps this much free below the last thing on a page. Measured, not
                                  # assumed: a 190pt strut ended Figure 5's picture at 723.4 and Word moved the
                                  # figure to the next page, while 150 ended it at 683.4 on the page.


_bookmark_id = [500]


def _el(tag: str, **attrs) -> OxmlElement:
    node = OxmlElement(tag)
    for key, value in attrs.items():
        node.set(qn(f"w:{key}"), str(value))
    return node


def _text_run(proto_run, text: str, italic: bool = False, bold: bool = False, size_half_pt: int | None = None):
    """A run in the prototype's font, with the given text (newlines become hard breaks)."""
    run = copy.deepcopy(proto_run)
    for child in list(run):
        if child.tag != qn("w:rPr"):
            run.remove(child)
    rPr = run.find(qn("w:rPr"))
    if rPr is None:
        rPr = run.makeelement(qn("w:rPr"), {})
        run.insert(0, rPr)
    for tag, on in (("w:i", italic), ("w:iCs", italic), ("w:b", bold), ("w:bCs", bold)):
        if on and rPr.find(qn(tag)) is None:
            rPr.append(_el(tag))
    if size_half_pt is not None:
        for tag in ("w:sz", "w:szCs"):
            existing = rPr.find(qn(tag))
            if existing is not None:
                rPr.remove(existing)
            rPr.append(_el(tag, val=size_half_pt))
    for i, line in enumerate(text.split("\n")):
        if i:
            run.append(_el("w:br"))
        t = _el("w:t")
        t.set(qn("xml:space"), "preserve")
        t.text = line
        run.append(t)
    return run


def _field(proto_run, instr: str, cached: str, bold: bool = False) -> list:
    """A complete begin/instr/separate/cached-result/end field, sized like the text around it.

    The cached result is what shows before Word updates anything and what the audit reads, so it has to carry the
    same emphasis as the label it belongs to: an unbold number inside a bold `Table 7` reads as two different
    objects.
    """
    parts = []
    for kind, content in (("begin", None), ("instr", instr), ("separate", None),
                          ("result", cached), ("end", None)):
        run = copy.deepcopy(proto_run)
        for child in list(run):
            if child.tag != qn("w:rPr"):
                run.remove(child)
        if bold:
            rPr = run.find(qn("w:rPr"))
            if rPr is None:
                rPr = run.makeelement(qn("w:rPr"), {})
                run.insert(0, rPr)
            for tag in ("w:b", "w:bCs"):
                if rPr.find(qn(tag)) is None:
                    rPr.append(_el(tag))
        if kind == "instr":
            node = _el("w:instrText")
            node.set(qn("xml:space"), "preserve")
            node.text = f" {content} "
            run.append(node)
        elif kind == "result":
            t = _el("w:t")
            t.set(qn("xml:space"), "preserve")
            t.text = content
            run.append(t)
        else:
            run.append(_el("w:fldChar", fldCharType=kind))
        parts.append(run)
    return parts


SPLIT = re.compile(r"(\{\{(?:Figure|Table):[a-z0-9_]+\}\})")


def rich_paragraph(proto_el, text: str, refs: dict[str, str]) -> OxmlElement:
    """A body paragraph in which `{{Figure:key}}` / `{{Table:key}}` tokens become REF fields.

    A token naming an exhibit that is never placed raises instead of emitting an empty field: a stale
    reference is exactly the defect the fields exist to prevent, and it must not reach the page.
    """
    el = copy.deepcopy(proto_el)
    runs = [r for r in el.findall(qn("w:r")) if r.find(qn("w:t")) is not None]
    if not runs:
        raise ValueError("paragraph prototype has no text run")
    proto_run = runs[0]
    for run in runs:
        run.getparent().remove(run)
    for part in SPLIT.split(text):
        if not part:
            continue
        match = TOKEN.fullmatch(part)
        if match is None:
            el.append(_text_run(proto_run, part))
            continue
        kind, key = match.group(1).lower(), match.group(2)
        name = f"_Ref_{kind}_{key}"
        if name not in refs:
            raise KeyError(f"the prose cites {part}, but no exhibit with that key is placed")
        for node in _field(proto_run, rf" REF {name} \h ", refs[name]):
            el.append(node)
    return el


def _keep_with_next(paras: list) -> list:
    """Bind the caption lines to the object below them.

    Without keepNext Word leaves a caption at the bottom of a page and pushes the picture to the next one,
    which is both unreadable and a failure of the layout audit's rule that a caption introduces what follows.
    """
    for el in paras:
        pPr = el.find(qn("w:pPr"))
        if pPr is None:
            pPr = OxmlElement("w:pPr")
            el.insert(0, pPr)
        for tag in ("w:keepLines", "w:keepNext"):
            if pPr.find(qn(tag)) is None:
                pPr.append(_el(tag))
    return paras


def styled_paragraph(proto_el, text: str) -> "object":
    """A paragraph from the prototype, with `*asterisked*` spans rendered italic.

    APA 7 italicises titles of reports, software and proceedings, and the audit reads run properties rather
    than trusting that the style does it. The markers are stripped here, so the asterisks never reach the page.
    """
    import copy as _copy

    el = _copy.deepcopy(proto_el)
    runs = [r for r in el.findall(qn("w:r")) if r.find(qn("w:t")) is not None]
    if not runs:
        raise ValueError("paragraph prototype has no text run")
    proto_run = runs[0]
    for run in runs:
        run.getparent().remove(run)
    for i, piece in enumerate(text.split("*")):
        if piece:
            el.append(_text_run(proto_run, piece, italic=bool(i % 2)))
    return el


def _match_template_caption(paragraph) -> None:
    """Put a caption line in the form the template's own caption lines are in.

    Two differences from the body prototype the paragraphs are cloned from. The body carries a half-inch
    first-line indent, and the template's `Table 1` / `Figure Text` lines carry no `w:ind` at all, so cloning
    left every exhibit label half a column right of the prose it introduces. And the body is double-spaced
    (`w:line=480`) while the template sets both caption lines at one and a half (`w:line=360`), which is what
    keeps the label, its description and the exhibit below reading as one block.
    """
    pPr = paragraph.find(qn("w:pPr"))
    if pPr is None:
        return
    for ind in pPr.findall(qn("w:ind")):
        pPr.remove(ind)
    for spacing in pPr.findall(qn("w:spacing")):
        pPr.remove(spacing)
    spacing = _el("w:spacing", line=360, lineRule="auto")
    style = pPr.find(qn("w:pStyle"))
    if style is not None:
        style.addnext(spacing)
    else:
        pPr.insert(0, spacing)


def caption_paragraphs(doc, protos, label: str, instr: str, cached: str, bookmark: str,
                       description: str) -> list:
    """The two lines above an exhibit: `Table N` bold as a labelled SEQ field, then the italic description."""
    label_para = copy.deepcopy(protos["body"])
    proto_run = next(r for r in label_para.findall(qn("w:r")) if r.find(qn("w:t")) is not None)
    for r in [n for n in label_para.findall(qn("w:r")) if n.find(qn("w:t")) is not None]:
        r.getparent().remove(r)
    _bookmark_id[0] += 1
    marker = _bookmark_id[0]
    label_para.append(_text_run(proto_run, f"{label} ", bold=True))
    # The bookmark opens after the label word, not before it, because the prose writes the word itself and
    # then cites: "Table {{Table:screening}}" is a REF whose result has to be the number. Opening the range on
    # the word made the resolved reference "Table 1" inside a sentence that already said "Table", and Word
    # rendered twelve of them as "Table Table 1" - the cached results in the source, which said only the
    # number, hid it until the file was opened and the fields resolved.
    label_para.append(_el("w:bookmarkStart", id=marker, name=bookmark))
    for node in _field(proto_run, instr, cached, bold=True):
        label_para.append(node)
    label_para.append(_el("w:bookmarkEnd", id=marker))

    desc_para = copy.deepcopy(protos["body"])
    desc_run = next(r for r in desc_para.findall(qn("w:r")) if r.find(qn("w:t")) is not None)
    for r in [n for n in desc_para.findall(qn("w:r")) if n.find(qn("w:t")) is not None]:
        r.getparent().remove(r)
    desc_para.append(_text_run(desc_run, description, italic=True))
    _match_template_caption(label_para)
    _match_template_caption(desc_para)
    return _keep_with_next([label_para, desc_para])


def spacer_paragraph(doc, protos):
    """One empty body line, the gap the template and the delivered A2 leave after an exhibit.

    Without it a table's last ruled edge runs straight into the next heading, which is what the supervisor's
    screenshot of Table 1 showed. Whether the gap is wanted depends on the page, not on the source: an exhibit
    that ends a page has nothing after it to separate from, so the caller decides.
    """
    para = copy.deepcopy(protos["body"])
    for r in para.findall(qn("w:r")):
        para.remove(r)
    pPr = para.find(qn("w:pPr"))
    if pPr is not None:
        for ind in pPr.findall(qn("w:ind")):
            pPr.remove(ind)
    return para



def strut_paragraph(doc, protos, points: float):
    """An empty paragraph of an exact height, used to push the second of two figures to the page bottom.

    Word has no bottom anchor for a text-frame paragraph, so the gap is made explicit. The height is a single
    tuned constant in the builder and the rendered geometry is what proves it, page by page, in the audit.
    """
    para = copy.deepcopy(protos["body"])
    for r in para.findall(qn("w:r")):
        para.remove(r)
    pPr = para.find(qn("w:pPr"))
    if pPr is not None:
        for tag in ("ind", "spacing"):
            for node in pPr.findall(qn(f"w:{tag}")):
                pPr.remove(node)
        pPr.append(_el("w:spacing", line=int(round(points * 20)), lineRule="exact"))
    return para

def table_element(protos, header: list[str], rows: list[list[str]], size_half_pt: int = 18) -> OxmlElement:
    """A bordered table in Times New Roman at the given half-point size, header shaded and bold."""
    proto_run = next(r for r in protos["body"].findall(qn("w:r")) if r.find(qn("w:t")) is not None)
    tbl = OxmlElement("w:tbl")
    tblPr = OxmlElement("w:tblPr")
    tblPr.append(_el("w:tblW", w=0, type="auto"))
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        borders.append(_el(f"w:{edge}", val="single", sz="4", space="0", color="000000"))
    tblPr.append(borders)
    tblPr.append(_el("w:tblLayout", type="autofit"))
    tbl.append(tblPr)
    grid = OxmlElement("w:tblGrid")
    width = int(TEXT_WIDTH_IN * 1440 / max(len(header), 1))
    for _ in header:
        grid.append(_el("w:gridCol", w=width))
    tbl.append(grid)

    def add_row(cells, bold: bool, shaded: bool):
        tr = OxmlElement("w:tr")
        trPr = OxmlElement("w:trPr")
        # A cell that wraps over a page turn is unreadable in a two-line-captions report; the audit checks
        # the flag rather than the layout, because the layout is Word's choice.
        trPr.append(_el("w:cantSplit"))
        if bold:
            trPr.append(_el("w:tblHeader"))
        tr.append(trPr)
        for text in cells:
            tc = OxmlElement("w:tc")
            tcPr = OxmlElement("w:tcPr")
            tcPr.append(_el("w:tcW", w=width, type="dxa"))
            if shaded:
                tcPr.append(_el("w:shd", val="clear", color="auto", fill="EFEFEF"))
            tc.append(tcPr)
            para = OxmlElement("w:p")
            pPr = OxmlElement("w:pPr")
            pPr.append(_el("w:spacing", before="20", after="20", line="240", lineRule="auto"))
            # Flush left, because the paragraphs otherwise inherit the template's Normal style, which is
            # justified. Justified suits a six-inch column; in a two-inch cell Word reaches the line end by
            # widening spaces, and the delivered build measured word gaps of 10.7pt (90th percentile 31.6)
            # inside tables against 3.0pt in the prose - the spread-out look that reads as centred text.
            pPr.append(_el("w:jc", val="left"))
            para.append(pPr)
            para.append(_text_run(proto_run, text, bold=bold, size_half_pt=size_half_pt))
            tc.append(para)
            tr.append(tc)
        tbl.append(tr)

    add_row(header, bold=True, shaded=True)
    for row in rows:
        add_row(row, bold=False, shaded=False)
    return tbl


def _figure_size_in(path: Path, dpi: int = 200) -> tuple[float, float]:
    """The size a picture is placed at: its pixel size at the stated dpi, reduced to the block and the page."""
    px_w, px_h = png_size(path)
    width_in, height_in = px_w / dpi, px_h / dpi
    scale = min(TEXT_WIDTH_IN / width_in, MAX_FIGURE_HEIGHT_IN / height_in, 1.0)
    return width_in * scale, height_in * scale


def description_line_count(text: str) -> int:
    """How many lines a caption description takes across the text block, which is what decides a page.

    Measured with the document's own typeface through PIL, falling back to an average character width when the
    font is not installed. The count only feeds the size of an empty middle between two figures, so an error of
    one line costs 20pt of gap; it is the audit that reads the rendered page, not this number, that proves the
    arrangement.
    """
    try:
        from PIL import ImageFont

        font = ImageFont.truetype("times.ttf", 12)
        width = TEXT_WIDTH_IN * 72
        lines, current = 1, ""
        for word in text.split():
            trial = f"{current} {word}".strip()
            if font.getlength(trial) <= width:
                current = trial
            else:
                lines += 1
                current = word
        return lines
    except Exception:
        return max(1, round(len(text) / 72 + 0.5))


def caption_block_pt(description: str) -> float:
    """The two caption lines as the page measures them: label, then the description wrapped at the block."""
    lines = description_line_count(description)
    return CAPTION_FIRST_STEP + CAPTION_LINE_PITCH * (lines - 1) + CAPTION_LINE_HEIGHT


def figure_block_pt(description: str, path: Path, dpi: int = 200) -> float:
    """A figure's whole block: its caption lines, the gap above the picture and the picture itself."""
    _, height_in = _figure_size_in(path, dpi)
    return caption_block_pt(description) + PICTURE_OVER_PT + height_in * 72


def png_size(path: Path) -> tuple[int, int]:
    with path.open("rb") as handle:
        handle.read(16)
        width, height = struct.unpack(">II", handle.read(8))
    return width, height


def figure_paragraph(doc, path: Path, dpi: int = 200):
    """A picture paragraph flush with the text block, scaled to the block and to one page.

    The template's own figure paragraph is left-aligned and carries no space above or below, and its caption
    lines start at that same edge; centring the picture leaves the exhibit attached to neither margin.
    """
    width_in, height_in = _figure_size_in(path, dpi)
    para = doc.add_paragraph()
    para.alignment = WD_ALIGN_PARAGRAPH.LEFT
    pPr = para._p.get_or_add_pPr()
    pPr.append(_el("w:spacing", before=0, after=0))
    para.add_run().add_picture(str(path), width=Inches(width_in))
    return para
