"""Read-only audit of the deliverable .docx.

Run:  python src/audit_docx.py
Reports stale embedded figures, exhibit-numbering integrity, unresolved cross-references,
text hygiene, repeated words, font drift and table integrity. Writes nothing.
"""
from __future__ import annotations

import io
import re
import sys
from collections import Counter
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
DOCX = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "CISC3024_AI_Assignment_3_Report.docx"
ASSETS = ROOT / "report_assets"

CAPTION = re.compile(r"^(Figure|Table)\s+(\d+)$")
FLAGS: list[str] = []


def flag(group: str, detail: str) -> None:
    FLAGS.append(f"[{group}] {detail}")


def main() -> int:
    if not DOCX.exists():
        print(f"missing {DOCX}", file=sys.stderr)
        return 1
    doc = Document(str(DOCX))
    paragraphs = doc.paragraphs
    texts = [p.text.strip() for p in paragraphs]

    # ---- 1. embedded figures vs the files on disk -------------------------------------------
    # Word re-encodes and downsamples pasted pictures, so a byte or pixel comparison is useless.
    # Classify each embedded picture by its nearest neighbour among the assets on disk, measured
    # as mean absolute difference on a small grayscale thumbnail.
    def grey(blob: bytes, width: int = 480):
        image = Image.open(io.BytesIO(blob)).convert("L")
        return image.resize((width, max(1, round(width * image.size[1] / image.size[0]))))

    def distance(a: bytes, b: bytes) -> float:
        left, right = grey(a), grey(b)
        right = right.resize(left.size)          # a differing aspect ratio costs real difference here
        return sum(abs(x - y) for x, y in zip(left.tobytes(), right.tobytes())) / \
            (left.size[0] * left.size[1])

    on_disk = {f.name: f.read_bytes() for f in ASSETS.glob("figure_*.png")}
    rels = doc.part.rels
    embedded: list[tuple[int, str]] = []
    current = 0
    for paragraph, text in zip(paragraphs, texts):
        match = CAPTION.fullmatch(text)
        if match and match.group(1) == "Figure":
            current = int(match.group(2))
        for blip in paragraph._p.iter(qn("a:blip")):
            rid = blip.get(qn("r:embed"))
            if rid is None or rid not in rels:
                flag("images", f"figure {current or '?'}: relationship {rid} is missing")
                continue
            blob = rels[rid].target_part.blob
            if current == 0:
                continue                      # cover artwork, precedes the first caption
            scores = sorted(((distance(blob, data), name) for name, data in on_disk.items()))
            best, name = scores[0]
            embedded.append((current, name if best < 4.0 else f"NEAREST {name} ({best:.1f})"))
            if best >= 4.0:
                flag("images", f"Figure {current}: no asset on disk resembles the embedded picture "
                               f"(nearest {name}, difference {best:.1f}) — an older drawing is pasted")
    numbers = [n for n, _ in embedded]
    if numbers != list(range(1, len(numbers) + 1)):
        flag("images", f"figure/image pairing out of order: {numbers}")
    print(f"embedded images: {len(embedded)}")
    for number, name in embedded:
        print(f"  Figure {number:>2} -> {name}")

    # ---- 2. exhibit numbering and references -------------------------------------------------
    figure_numbers = [int(CAPTION.fullmatch(t).group(2)) for t in texts
                      if CAPTION.fullmatch(t) and CAPTION.fullmatch(t).group(1) == "Figure"]
    table_numbers = [int(CAPTION.fullmatch(t).group(2)) for t in texts
                     if CAPTION.fullmatch(t) and CAPTION.fullmatch(t).group(1) == "Table"]
    for kind, found in (("Figure", figure_numbers), ("Table", table_numbers)):
        if found != list(range(1, len(found) + 1)):
            flag("numbering", f"{kind} captions are not 1..N in document order: {found}")
        for value, count in Counter(found).items():
            if count > 1:
                flag("numbering", f"{kind} {value} captioned {count} times")
    print(f"captions: {len(figure_numbers)} figures, {len(table_numbers)} tables")

    body = " ".join(texts)
    for kind, found in (("Figure", figure_numbers), ("Table", table_numbers)):
        cited = {int(n) for n in re.findall(rf"\b{kind}\s+(\d+)\b", body)}
        for value in sorted(cited - set(found)):
            flag("numbering", f"{kind} {value} is cited but never captioned")
        for value in sorted(set(found) - cited):
            flag("numbering", f"{kind} {value} is never cited in the text")
    for pattern in (r"\[\[", r"\?\?", r"\bTBD\b", r"\bXXX\b", r"\blorem\b"):
        for hit in re.finditer(pattern, body, re.I):
            start = max(0, hit.start() - 45)
            flag("placeholders", f"{pattern!r} near: ...{body[start:hit.end() + 45]}...")
            break

    # ---- 3. text hygiene ---------------------------------------------------------------------
    # ``paragraph.text`` drops inline equations, so whitespace is only judged where there is no
    # equation object in the paragraph.
    M_NS = "{http://schemas.openxmlformats.org/officeDocument/2006/math}"
    chinese = [t for t in texts if re.search(r"[\u4e00-\u9fff]", t)]
    if chinese:
        flag("language", f"{len(chinese)} paragraph(s) contain Chinese characters, e.g. "
                         f"{chinese[0][:80]!r}")
    for value, count in Counter(texts).items():
        if count > 1 and value and CAPTION.fullmatch(value):
            flag("hygiene", f"caption text repeated {count}x: {value!r}")
    for index, (paragraph, text) in enumerate(zip(paragraphs, texts), start=12):
        if paragraph._p.findall(f".//{M_NS}oMath"):
            continue
        if re.search(r"\b(\w+)\s+\1\b", text):
            flag("hygiene", f"repeated word in paragraph {index}: "
                            f"{re.search(r'\b(\w+)\s+\1\b', text).group(0)!r} in {text[:70]!r}")
        if re.search(r"\S  +\S", text):
            flag("hygiene", f"double space in paragraph {index}: {text[:70]!r}")
        # A space before . , or ; is a typo, except when the punctuation starts a decimal: quoted
        # source lines such as `c = [.08, .12, 0.18, 0.26, 0.38][severity - 1]` are legitimate text and
        # the earlier form of this rule flagged them.
        if re.search(r"\s[.,;](?!\d)", text):
            flag("hygiene", f"space before punctuation in paragraph {index}: {text[:70]!r}")
    internal = [term for term in ("D-1", "option b", "Gate 0", "Gate 1", "Gate 2", "Gate 3", "Gate 4",
                                  "Gate 5", "milestone", "SECTION_")
                if re.search(rf"\b{re.escape(term)}\b", body)]
    for term in internal:
        hit = re.search(rf".{{0,70}}\b{re.escape(term)}\b.{{0,70}}", body)
        flag("jargon", f"{term!r} still in the text: ...{hit.group(0)}...")
    for term in ("Section 1", "Section 2", "Section 3", "Section 4", "Section 5", "Section 6",
                 "Section 7"):
        if term in body:
            flag("jargon", f"bare numbered section reference {term!r} — headings are unnumbered")

    # ---- 4. fonts ----------------------------------------------------------------------------
    def resolved_family(paragraph, run) -> str | None:
        """The face a run actually renders in: run, then the style chain, then None (theme)."""
        if run.font.name:
            return run.font.name
        style = paragraph.style
        for _ in range(6):
            if style is None:
                break
            if style.font.name:
                return style.font.name
            style = getattr(style, "base_style", None)
        return None

    faces: Counter = Counter()
    for paragraph in paragraphs[12:]:
        for run in paragraph.runs:
            if run.text.strip():
                faces[(resolved_family(paragraph, run),
                       run.font.size.pt if run.font.size else None)] += 1
    print("resolved (face, size) for body runs:")
    for (face, size), count in sorted(faces.items(), key=lambda kv: -kv[1])[:12]:
        print(f"  {face!r} {size}pt: {count}")
    unexpected = {face for face, _ in faces if face not in ("Times New Roman", "Consolas", None)}
    if unexpected:
        flag("fonts", f"faces outside the declared pair: {sorted(unexpected)}")
    if None in {face for face, _ in faces}:
        print("  (runs with face=None inherit the document default; the PDF span audit covers those)")

    # ---- 5. tables ---------------------------------------------------------------------------
    for t_index, table in enumerate(doc.tables, start=1):
        properties = table.rows[0]._tr.trPr
        header = properties is not None and properties.find(qn("w:tblHeader")) is not None
        if not header:
            flag("tables", f"table {t_index}: header row does not repeat")
        for r_index, row in enumerate(table.rows):
            row_properties = row._tr.trPr
            split = row_properties is not None and row_properties.find(qn("w:cantSplit")) is None
            if split:
                flag("tables", f"table {t_index} row {r_index}: rows may split across pages")
        widths = {len(row.cells) for row in table.rows}
        if len(widths) > 1:
            flag("tables", f"table {t_index}: ragged row widths {sorted(widths)}")
    print(f"tables: {len(doc.tables)}")

    # ---- 6. headings vs TOC ------------------------------------------------------------------
    # Word keeps the rebuilt contents list inside a content control, which python-docx does not
    # expose through ``document.paragraphs``, so walk the raw body instead.
    def para_text(element) -> str:
        return "".join(node.text or "" for node in element.iter(qn("w:t")))

    walk = list(doc.element.body.iter(qn("w:p")))
    rendered = [para_text(p) for p in walk]

    def style_of(element) -> str:
        properties = element.find(qn("w:pPr"))
        if properties is None:
            return ""
        found = properties.find(qn("w:pStyle"))
        return (found.get(qn("w:val")) or "").lower() if found is not None else ""

    styles = [style_of(p) for p in walk]
    field_at = next((i for i, p in enumerate(walk)
                     if any("TOC" in (node.text or "") for node in p.iter(qn("w:instrText")))), None)
    headings = [p.text.strip() for p in paragraphs if p.style.name.startswith("Heading")]
    if field_at is None:
        flag("toc", "no table-of-contents field found in the document")
    else:
        # the body heading itself, not its twin in the contents list: the first paragraph after the
        # field that both matches the text and carries a heading style
        # the body heading itself, not its twin in the contents list: this template names heading
        # styles "1"/"2"/"3" and the contents entries "TOC1"/"TOC2"/"TOC3"
        boundary = next((i for i in range(field_at + 1, len(rendered))
                         if rendered[i].strip() == headings[0] and not styles[i].startswith("toc")),
                        len(rendered))
        toc_region = " ".join(rendered[field_at:boundary])   # the field begin shares its paragraph
        # with the first entry, so that paragraph is part of the contents, not before it
        for heading in headings:
            if " ".join(heading.split()) not in " ".join(toc_region.split()):
                flag("toc", f"heading absent from the contents page: {heading[:70]!r}")
        print(f"headings: {len(headings)}, contents entries scanned: {boundary - field_at - 1}")

    # ---- 7. the brief's own requirements ------------------------------------------------------
    if not re.search(r"https?://", body):
        flag("brief", "no URL anywhere in the document — the brief asks for the source-code web link")
    words = sum(len(t.split()) for t in texts)
    print(f"body words (paragraph text only): {words:,}")

    print()
    if not FLAGS:
        print("no findings")
    for item in FLAGS:
        print(item)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
