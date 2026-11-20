"""Read-only audit of the deliverable .docx.

Run:  python src/audit_docx.py
Reports stale embedded figures, exhibit-numbering integrity, unresolved cross-references,
text hygiene, repeated words, font drift, table integrity and bibliography filing order. Writes nothing.
"""
from __future__ import annotations

import io
import json
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
        # the earlier form of this rule flagged them. APA 7 also writes a long author list's omission as
        # ", ... Lastname", where the space before the three dots is the style rather than a typo, so that
        # exact sequence is folded away before the check instead of loosening the rule for real typos.
        if re.search(r"\s[.,;](?!\d)", text.replace(", ... ", ",")):
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

    # ---- 8. bibliography filing ---------------------------------------------------------------
    # APA 7 files the whole reference list as one alphabet, letter by letter, and a list assembled by
    # appending a second batch to the first reads as two sorted runs. The source module owns the order
    # this document was built from, so the filing is asserted on the rendered paragraphs instead.
    def filing_key(entry: str) -> tuple:
        """(author, year with its disambiguating letter, remainder), each stripped to lowercase alphanumerics."""
        year = re.search(r"\((\d{4}([a-z]?))\)", entry)
        head, tail = (entry[:year.start()], entry[year.end():]) if year else (entry, "")
        plain = lambda value: re.sub(r"[^a-z0-9]", "", value.lower())
        return plain(head), (year.group(1) if year else ""), plain(tail)

    reference_paragraphs = [p.text.strip() for p in paragraphs if p.style.style_id == "EndNoteBibliography"]
    order = [(i, p.style.style_id, p.text.strip()) for i, p in enumerate(paragraphs)]
    heads = [i for i, _s, text in order if text == "References"]
    entries = [i for i, style, _t in order if style == "EndNoteBibliography"]
    if heads and entries and min(entries) < max(heads):
        flag("references", f"reference entries precede the References heading: entry paragraph "
                           f"{min(entries)} against heading paragraph {max(heads)} - the list must follow "
                           f"its own heading in document order")
    keys = [filing_key(entry) for entry in reference_paragraphs]
    if keys != sorted(keys):
        first_wrong = next(i for i in range(1, len(keys)) if keys[i] < keys[i - 1])
        flag("references", f"reference list is not filed alphabetically as a whole: {first_wrong + 1} of "
                           f"{len(keys)} breaks the order - {reference_paragraphs[first_wrong][:40]!r} "
                           f"follows {reference_paragraphs[first_wrong - 1][:40]!r}")
    print(f"reference entries: {len(reference_paragraphs)}; filing "
          f"{'alphabetical' if keys == sorted(keys) else 'NOT alphabetical'}")

    # U029, second item: a cross-reference bookmark must hold the exhibit's number and nothing else. The
    # prose writes the label word itself ("... is Figure {{Figure:eq37}}") and the REF supplies the number,
    # so a bookmark that also covers the word "Figure" makes Word render "Figure Figure 4" the moment it
    # resolves a field - twelve times over in the delivered build, and invisible in the source because the
    # REF fields there carry only the number as their cached result.
    body = doc.element.body
    starts = {int(node.get(qn("w:id"))): node.get(qn("w:name"))
              for node in body.iter(qn("w:bookmarkStart")) if (node.get(qn("w:name")) or "").startswith("_Ref_")}
    covered: dict[int, str] = {marker: "" for marker in starts}
    open_markers: set[int] = set()
    for node in body.iter():
        if node.tag == qn("w:bookmarkStart") and int(node.get(qn("w:id"))) in starts:
            open_markers.add(int(node.get(qn("w:id"))))
        elif node.tag == qn("w:bookmarkEnd") and int(node.get(qn("w:id"))) in starts:
            open_markers.discard(int(node.get(qn("w:id"))))
        elif node.tag == qn("w:t") and open_markers:
            for marker in open_markers:
                covered[marker] += node.text or ""
    bad = {starts[m]: text for m, text in covered.items() if not re.fullmatch(r"\d+", text)}
    if bad:
        sample = ", ".join(f"{name} holds {text!r}" for name, text in sorted(bad.items())[:3])
        flag("cross-references", f"{len(bad)} of {len(starts)} cross-reference bookmarks do not contain "
                                 f"a bare number, so Word renders the label word twice: {sample}")
    print(f"cross-reference bookmarks: {len(starts)}, each holding "
          f"{'only the number' if not bad else 'MORE THAN the number'}")

    # ---- 9. the cover ---------------------------------------------------------------------------
    # The template's name line is four ASK fields and its date is a real example date, so a fill can fail in
    # three different ways and look finished each time: text written into the field runs disappears the next
    # time Word updates fields, the group template's spare name lines collapse into blank ones, and "06 Apr
    # 2026" stays on the page unnoticed. The values live in a gitignored JSON, so the audit compares against
    # what was released rather than against a copy of it typed here.
    cover_values = ROOT / "report_assets" / "cover_values.json"
    if cover_values.exists():
        released = json.loads(cover_values.read_text(encoding="utf-8"))
        cover_text = " ".join(texts[:12])
        for field in ("title", "byline", "date"):
            for line in str(released.get(field, "")).split(chr(10)):
                if line and line not in cover_text:
                    flag("cover", f"cover field {field!r} did not survive the build: {line!r} is not on the page")
        instructions = [node.text.strip() for node in doc.element.body.iter(qn("w:instrText"))
                        if node.text and re.match(r"\s*(ASK|FORMTEXT|FORMCHECKBOX)\b", node.text)]
        if instructions:
            flag("cover", f"{len(instructions)} prompting field(s) left on the cover, e.g. {instructions[0]!r} "
                          "- Word re-evaluates these on open and renders them empty, so a value written into "
                          "one is not a value on the page")
        if re.search(r"\d{2} [A-Za-z]{3} 2026", cover_text) and released.get("date", "") not in cover_text:
            flag("cover", "a date is on the cover but it is not the released one")
        print(f"cover: checked against the released values ({len(released)} keys)")
    else:
        print("cover: report_assets/cover_values.json absent, nothing to check the cover against")

    # U030: table cells are written flush left on purpose. The paragraphs inside a cell otherwise inherit the
    # template's Normal style, which is justified, and Word reaches the line end by widening spaces - which is
    # what reads as centred text with characters drifting down. The gate reads the property rather than the
    # page, and `audit_layout.reference_render_checks`'s companion measures what actually rendered.
    cell_paragraphs = [paragraph for table in doc.tables for row in table.rows for cell in row.cells
                       for paragraph in cell.paragraphs if cell.text.strip()]
    no_left = [paragraph.text.strip()[:24] for paragraph in cell_paragraphs
               if (lambda el: el is None or el.find(qn("w:jc")) is None
                   or el.find(qn("w:jc")).get(qn("w:val")) != "left")(paragraph._p.find(qn("w:pPr")))]
    if no_left:
        flag("tables", f"{len(no_left)} of {len(cell_paragraphs)} table cell paragraphs do not carry an "
                       f"explicit left alignment, so they inherit the style's justification: "
                       f"{', '.join(repr(t) for t in no_left[:3])}")
    print(f"table cells: {len(cell_paragraphs)}, explicitly left: "
          f"{len(cell_paragraphs) - len(no_left)}")

    print()
    if not FLAGS:
        print("no findings")
    for item in FLAGS:
        print(item)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
