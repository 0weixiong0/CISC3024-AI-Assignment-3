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


def _field(proto_run, instr: str, cached: str) -> list:
    """A complete begin/instr/separate/cached-result/end field, sized like the text around it."""
    parts = []
    for kind, content in (("begin", None), ("instr", instr), ("separate", None),
                          ("result", cached), ("end", None)):
        run = copy.deepcopy(proto_run)
        for child in list(run):
            if child.tag != qn("w:rPr"):
                run.remove(child)
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


def caption_paragraphs(doc, protos, label: str, instr: str, cached: str, bookmark: str,
                       description: str) -> list:
    """The two lines above an exhibit: `Table N` as a labelled SEQ field, then the italic description."""
    label_para = copy.deepcopy(protos["body"])
    proto_run = next(r for r in label_para.findall(qn("w:r")) if r.find(qn("w:t")) is not None)
    for r in [n for n in label_para.findall(qn("w:r")) if n.find(qn("w:t")) is not None]:
        r.getparent().remove(r)
    _bookmark_id[0] += 1
    marker = _bookmark_id[0]
    label_para.append(_el("w:bookmarkStart", id=marker, name=bookmark))
    label_para.append(_text_run(proto_run, f"{label} "))
    for node in _field(proto_run, instr, cached):
        label_para.append(node)
    label_para.append(_el("w:bookmarkEnd", id=marker))

    desc_para = copy.deepcopy(protos["body"])
    desc_run = next(r for r in desc_para.findall(qn("w:r")) if r.find(qn("w:t")) is not None)
    for r in [n for n in desc_para.findall(qn("w:r")) if n.find(qn("w:t")) is not None]:
        r.getparent().remove(r)
    desc_para.append(_text_run(desc_run, description, italic=True))
    return _keep_with_next([label_para, desc_para])


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
            para.append(pPr)
            para.append(_text_run(proto_run, text, bold=bold, size_half_pt=size_half_pt))
            tc.append(para)
            tr.append(tc)
        tbl.append(tr)

    add_row(header, bold=True, shaded=True)
    for row in rows:
        add_row(row, bold=False, shaded=False)
    return tbl


def png_size(path: Path) -> tuple[int, int]:
    with path.open("rb") as handle:
        handle.read(16)
        width, height = struct.unpack(">II", handle.read(8))
    return width, height


def figure_paragraph(doc, path: Path, dpi: int = 200):
    """A centred picture paragraph, scaled to the text block and to one page."""
    px_w, px_h = png_size(path)
    width_in, height_in = px_w / dpi, px_h / dpi
    scale = min(TEXT_WIDTH_IN / width_in, MAX_FIGURE_HEIGHT_IN / height_in, 1.0)
    para = doc.add_paragraph()
    para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    para.add_run().add_picture(str(path), width=Inches(width_in * scale))
    return para
