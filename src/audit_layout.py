"""Check the built report against the layout rule the supervisor set.

Project : CISC3024 AI Assignment #3 (Pattern Recognition, University of Macau)
Author  : AI-generated implementation (Qoder). The student wrote no code.

The rule: a page holds at most two exhibits, each anchored to the top or the bottom of the page, and
no exhibit block is ever split from its caption or across a page boundary.

The audit reads the exported PDF, not the source document, because pagination is only known after
Word has laid the page out. Every check is anchored on the caption label line ("Figure 7", "Table 3")
rather than on a keyword search, which previously produced false positives from header words such as
"Configuration" that also appear in prose and in the table of contents.
"""

from __future__ import annotations

import re
import sys
from collections import Counter
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parent.parent
PDF = ROOT / "CISC3024_AI_Assignment_3_Report.pdf"
TOP_LIMIT = 200      # a first exhibit on a page must start above this y
BOTTOM_LIMIT = 320   # a second exhibit on the same page must start below this y
PAGE_BOTTOM = 700    # nothing may start below this and still be on the page
# The caption pair as the template itself renders it: "Table 1" at y=72.5 over "Table text" at y=105.1, and
# wrapped description lines 20.7pt apart, which is 1.5 spacing on 12pt Times. Read from the template exported
# through Word, not assumed, because the template's pair is also 32.6 rather than the 20.7 the arithmetic gives.
TEMPLATE_CAPTION_STEP = 32.6
TEMPLATE_CAPTION_PITCH = 20.7
BAND_LOW = 7800      # rendered body words, see word_band_checks
BAND_HIGH = 9200     # the ceiling on the prose unit itself lives in src/build_report.py

# The contents field is resolved by Word, so its length is not known when the document is written. If it
# runs onto the next page the body starts under its last entry, which is a layout fault the exhibit checks
# cannot see. Dot leaders are the signature: prose never has them.
TOC_LINE = re.compile(r"\.{5,}\s*\d+\s*$")
FIRST_SECTION = "Introduction and Human-AI Workflow"


def toc_checks(pages) -> list[str]:
    """Return findings when the contents and the first section share a page."""
    problems = []
    toc_pages = [n for n, page in enumerate(pages, start=1)
                 if sum(1 for line in page.get_text().splitlines() if TOC_LINE.search(line.strip())) >= 3]
    body_page = next((n for n, page in enumerate(pages, start=1)
                      if TOC_LINE.search("") is None and _starts_section(page)), None)
    if not toc_pages:
        return ["no contents page detected - the field is unresolved, so the check cannot run"]
    if body_page is None:
        return [f"the first section ({FIRST_SECTION!r}) was not found as a heading line"]
    if body_page in toc_pages:
        problems.append(f"page {body_page} carries both contents entries and the first section heading")
    if body_page < max(toc_pages):
        problems.append(f"body starts on page {body_page}, before the last contents page {max(toc_pages)}")
    print(f"contents pages: {toc_pages}   first section page: {body_page}")
    return problems


def _starts_section(page) -> bool:
    for block in page.get_text("dict")["blocks"]:
        if block["type"] != 0:
            continue
        for line in block["lines"]:
            text = "".join(span["text"] for span in line["spans"]).strip()
            if text == FIRST_SECTION and line["bbox"][1] < 200:
                return True
    return False


def labels_on(page) -> list[tuple[str, int]]:
    """Caption labels on a page, with the y of the label line itself.

    Read from the text geometry rather than from search_for, because a phrase like "Table 1" also
    occurs inside prose and the search would return the wrong line.
    """
    found = []
    for block in page.get_text("dict")["blocks"]:
        if block["type"] != 0:
            continue
        for line in block["lines"]:
            text = "".join(span["text"] for span in line["spans"]).strip()
            match = re.fullmatch(r"(Figure|Table)\s+(\d+)", text)
            if match:
                found.append((f"{match.group(1)} {match.group(2)}", round(line["bbox"][1])))
    return found


def reference_checks(pages) -> list[str]:
    """Every APA entry and every in-text form must survive the round trip to the rendered page.

    The build refuses to write a document whose list and prose disagree, but that check reads the docx element
    tree. Word re-wraps text when it paginates, and a citation split across a line is invisible to a plain
    search yet obvious to an examiner, so the same pair is asserted here on extracted text with whitespace
    collapsed.
    """
    import report_references as ref

    text = " ".join(" ".join(page.get_text().split()) for page in pages)
    problems = []
    for key, _narrative, entry in ref.ENTRIES:
        form = ref.IN_TEXT[key]
        if " ".join(form.split()) not in text:
            problems.append("in-text citation never renders: " + form)
        head = " ".join(entry.replace("*", "").split())[:40]
        if head not in text:
            problems.append("reference entry never renders: " + entry[:40])
    return problems


def cover_checks(pages) -> list[str]:
    """Page one must carry the released cover values, and no template token may survive anywhere.

    The docx audit checks the same strings in the element tree; this checks them where they are read. The
    distinction matters because the template's name line is built from Word ASK fields: text placed inside one
    is present in the XML and absent from the page, and the first filled cover did exactly that. The released
    values live in a gitignored JSON, so this reads them instead of restating them.
    """
    import json

    values = ROOT / "report_assets" / "cover_values.json"
    if not values.exists() or not pages:
        return []
    released = json.loads(values.read_text(encoding="utf-8"))
    first = " ".join(pages[0].get_text().split())
    problems = []
    for field in ("title", "byline", "date"):
        for line in str(released.get(field, "")).split(chr(10)):
            if line and " ".join(line.split()) not in first:
                problems.append(f"cover {field} never renders on page 1: {line!r}")
    body = " ".join(" ".join(page.get_text().split()) for page in pages)
    for token in ("CISCXXXX", "DDxxxxxx", "CYYYYYY", "Your Name", "Please enter your"):
        if token in body:
            problems.append(f"template token still on the page: {token!r}")
    return problems


def geometry_checks(pages) -> list[str]:
    """Exhibits sit flush with the text block, and the bibliography opens its own page.

    Two faults the text checks cannot see. A caption can carry the body paragraph's half-inch first-line indent
    and still read correctly in every string search, which is what the first exhibit pass did - the labels were
    half a column right of the prose. And a picture can be centred while the template's own figure paragraph is
    left-aligned, which makes the exhibit look attached to neither margin. The picture rule is a partial net on
    its own: an image scaled to the full text width sits at the margin whether it is centred or left, so only the
    narrower ones move, and the caption rule is what catches the indent on every exhibit. Both are measured here
    against the
    page's own text edge rather than against a typed number: the margin comes from where the long prose lines on
    that page start.

    The References rule is U026's: the heading has to open a page. It used to sit mid-page under the last
    paragraph of section 7, so a reader met three entries before meeting the heading.
    """
    problems = []
    # The text edge is taken once for the document, from every long rendered line below the heading band. It
    # cannot be taken page by page: a page holding an indented caption and two lines of indented description has
    # those lines as its longest text, so the faulty indent becomes the reference and the page looks compliant.
    spans = [round(s["bbox"][0], 1) for page in pages for b in page.get_text("dict")["blocks"] if b["type"] == 0
             for l in b["lines"] for s in l["spans"] if len(s["text"].strip()) > 40 and s["bbox"][0] < 200]
    if not spans:
        return ["no body text found to measure the exhibits against"]
    left = Counter(spans).most_common(1)[0][0]
    print(f"text block left edge, measured across the document: x={left}")
    for number, page in enumerate(pages, start=1):
        blocks = page.get_text("dict")["blocks"]
        for b in blocks:
            if b["type"] != 0:
                continue
            for line in b["lines"]:
                text = "".join(s["text"] for s in line["spans"]).strip()
                if re.fullmatch(r"(Figure|Table)\s+\d+", text):
                    x = round(line["bbox"][0], 1)
                    if abs(x - left) > 1.0:
                        problems.append(f"{text} on page {number} starts at x={x}, indented from the "
                                        f"text edge at x={left}")
        for b in blocks:
            if b["type"] == 1 and number > 1:          # page 1 carries the template's own centred logo
                x0, x1 = round(b["bbox"][0], 1), round(b["bbox"][2], 1)
                if abs(x0 - left) > 1.0:
                    problems.append(f"the figure on page {number} starts at x={x0}, not flush with the "
                                    f"text edge at x={left} (it runs to {x1})")

    head_page = None
    for number, page in enumerate(pages, start=1):
        for b in page.get_text("dict")["blocks"]:
            if b["type"] != 0:
                continue
            for line in b["lines"]:
                if "".join(s["text"] for s in line["spans"]).strip() == "References":
                    head_page = number if head_page is None else min(head_page, number)
    if head_page is None:
        problems.append("no References heading found in the rendered document")
        return problems

    lines = [
        "".join(s["text"] for s in line["spans"]).strip()
        for b in pages[head_page - 1].get_text("dict")["blocks"] if b["type"] == 0
        for line in b["lines"]
    ]
    content = [t for t in lines if t and not re.fullmatch(r"\d+", t)]
    if content and content[0] != "References":
        problems.append(f"References does not open page {head_page}: {content[0][:48]!r} renders above it")
    # The order of entries and heading is asserted structurally in audit_docx, where paragraph sequence is
    # exact; a substring test here matched the prose citation "(AT&T Laboratories Cambridge, 2002)" in section 5
    # and reported it as an entry sitting before the heading.
    return problems


def _rows(page) -> list[tuple[float, float, str, set]]:
    """Text rows on a page: top, bottom, joined text, and the fonts that render it.

    Rows are rebuilt from rendered lines rather than taken from the block structure, because Word's PDF output
    puts a caption label in one block and its description in another, and a paragraph that merely starts with
    the word "Table" is otherwise indistinguishable from the caption of Table N.
    """
    buckets: dict[float, dict] = {}
    for block in page.get_text("dict")["blocks"]:
        if block["type"] != 0:
            continue
        for line in block["lines"]:
            text = " ".join(span["text"] for span in line["spans"] if span["text"].strip()).strip()
            if not text:
                continue
            key = round(line["bbox"][1], 1)
            row = buckets.setdefault(key, {"bottom": line["bbox"][1], "parts": [], "fonts": set()})
            row["bottom"] = max(row["bottom"], line["bbox"][3])
            row["parts"].append((line["bbox"][0], text))
            row["fonts"].update(span["font"] for span in line["spans"] if span["text"].strip())
    return [(y, row["bottom"], " ".join(t for _, t in sorted(row["parts"])), row["fonts"])
            for y, row in sorted(buckets.items())]


def caption_typography_checks(pages) -> list[str]:
    """The caption block must look the way the template's own caption pair looks.

    Three properties U028 named, each measured on the rendered page: the label is bold, the label-to-description
    step and the wrapped-description line pitch are the template's 1.5-spaced values rather than the body's
    double spacing, and the description is italic. The three constants were read off `Report Template.docx`
    exported through Word - the template's "Table 1" / "Table text" pair renders at the same 72.5 and 105.1 -
    so the check compares against the template rather than against a preference.
    """
    problems = []
    for number, page in enumerate(pages, start=1):
        if number == 1:
            continue
        rows = _rows(page)
        for index, (y, bottom, text, fonts) in enumerate(rows):
            match = re.fullmatch(r"(Figure|Table)\s+\d+", text)
            if not match:
                continue
            if not all("Bold" in font for font in fonts):
                problems.append(f"page {number}: the label {text!r} is not bold ({sorted(fonts)})")
            following = [row for row in rows[index + 1:index + 4] if row[2]]
            if not following:
                problems.append(f"page {number}: {text} has no description line under the label")
                continue
            step = round(following[0][0] - y, 1)
            if abs(step - TEMPLATE_CAPTION_STEP) > 1.5:
                problems.append(f"page {number}: {text}'s description starts {step}pt under the label, "
                                f"the template's caption pair measures {TEMPLATE_CAPTION_STEP}pt")
            if not all("Italic" in font for font in following[0][3]):
                problems.append(f"page {number}: {text}'s description is not italic ({sorted(following[0][3])})")
            previous = following[0][0]
            for row in following[1:]:
                if not all("Italic" in font for font in row[3]):
                    break        # the description ended; whatever follows is the exhibit or the prose
                pitch = round(row[0] - previous, 1)
                if abs(pitch - TEMPLATE_CAPTION_PITCH) > 1.2:
                    problems.append(f"page {number}: {text}'s description lines advance {pitch}pt, "
                                    f"1.5 spacing is {TEMPLATE_CAPTION_PITCH}pt")
                previous = row[0]
    return problems


def reference_render_checks(pages) -> list[str]:
    """Nothing in the U029 shape of the defect may reach the rendered text.

    Two failures produced the doubled labels the supervisor saw. A REF whose bookmark covers the label word
    resolves to "Figure 4" inside a sentence that already says "Figure". A citation token written inside an
    f-string collapses to single braces, never reaches the REF builder, and prints literally as
    "{Figure:eq37}". The first was in twelve places of the delivered build and the second in two, and neither
    was visible in the source document, where both forms look correct - so the check belongs on the page.
    """
    text = "\n".join(page.get_text() for page in pages)
    problems = []
    for doubled in re.finditer(r"\b(Figure|Table)\s+\1\b", text):
        problems.append(f"rendered text repeats an exhibit label: {text[doubled.start():doubled.start() + 24]!r}")
    for stray in re.finditer(r"\{+(?:Figure|Table):[a-z0-9_]+\}+", text):
        problems.append(f"an unresolved cross-reference token reached the page: {stray.group(0)!r}")
    return problems


def toc_page_checks(pages) -> list[str]:
    """Every page number the contents prints must be the page the heading is actually on.

    Word resolves the contents field when it saves, so a stale entry is a property of the file rather than of
    the build. Renaming a heading moves nothing on its own, but it re-flows the document, and the U029 round
    changed a section title: this is what says the contents kept up.
    """
    contents = [n for n, page in enumerate(pages, start=1)
                if sum(1 for line in page.get_text().splitlines() if TOC_LINE.search(line.strip())) >= 3]
    if not contents:
        return ["no contents page found, so the printed page numbers cannot be checked"]
    entries = []
    for number in contents:
        for line in pages[number - 1].get_text().splitlines():
            match = re.match(r"^(.{4,}?)\s*\.{3,}\s*(\d+)\s*$", line.strip())
            if match:
                entries.append((" ".join(match.group(1).split()), int(match.group(2)), number))
    problems = []
    rendered = []
    for number, page in enumerate(pages, start=1):
        if number in contents:
            continue
        lines = {" ".join(span["text"] for span in line["spans"]).strip()
                 for block in page.get_text("dict")["blocks"] if block["type"] == 0
                 for line in block["lines"]}
        rendered.append((number, lines))
    for title, printed, _on_page in entries:
        actual = next((number for number, lines in rendered if title in lines), None)
        if actual is None:
            problems.append(f"contents entry {title[:44]!r} (printed page {printed}) has no heading "
                            f"on any body page")
        elif actual != printed:
            problems.append(f"contents says {title[:44]!r} is on page {printed}, it renders on page {actual}")
    print(f"contents entries checked against their headings: {len(entries)}")
    return problems


def exhibit_gap_checks(pages) -> list[str]:
    """A blank line after an exhibit when the page continues, and none when it does not (U028).

    The gap is asserted where it is read, because whether one is wanted depends on Word's pagination, not on
    the source: the same spacer paragraph that separates Table 1 from the heading under it would sit at the top
    of the following page if that heading had broken there instead. Both halves are checked - the measured
    distance from the exhibit's bottom edge to the next row, and the top of every page, which catches a gap
    stranded where it does not belong.
    """
    problems = []
    for number, page in enumerate(pages, start=1):
        if number == 1:
            continue
        rows = [row for row in _rows(page) if row[0] > 55 and not row[2].isdigit()]
        images = [b["bbox"] for b in page.get_text("dict")["blocks"]
                  if b["type"] == 1 and b["bbox"][0] < 100]
        bottoms = [b[3] for b in images] + [t.bbox[3] for t in page.find_tables().tables]
        for bottom in bottoms:
            following = [row for row in rows if row[0] > bottom + 1]
            if not following:
                continue                      # nothing after it on this page, which is the excluded case
            gap = round(following[0][0] - bottom, 1)
            if len(images) == 2 and re.fullmatch(r"(Figure|Table)\s+\d+", following[0][2]):
                if gap < 100:                 # the deliberate empty middle of a two-figure page
                    problems.append(f"page {number} holds two figures but only {gap}pt separates them")
                continue
            if not 44.0 <= gap <= 48.0:
                problems.append(f"page {number}: an exhibit ends at {bottom:.1f} and the next line starts "
                                f"{gap}pt below it; the blank line after an exhibit measures 46pt")
        if rows and rows[0][0] - 72.5 > 2.0:
            problems.append(f"page {number} opens {rows[0][0] - 72.5:.1f}pt below the text top with "
                            f"{rows[0][2][:40]!r}: a separator has been stranded at the top of the page")
        if len(images) == 2:
            # A two-figure page holds nothing else. Caption descriptions are excluded by their italic runs:
            # without that the check read Figure 4's own caption as prose sitting above the pair and reported
            # the page it was written to protect as broken.
            prose = [row for row in rows
                     if not re.fullmatch(r"(Figure|Table)\s+\d+", row[2])
                     and not all("Italic" in font for font in row[3])
                     and row[1] < images[0][1] - 1]
            if prose:
                problems.append(f"page {number} is meant to hold two figures only, but prose renders above "
                                f"them: {prose[0][2][:40]!r}")
            shortfall = round(720.0 - images[1][3], 1)
            if shortfall > 45:
                problems.append(f"page {number}: its second figure ends {shortfall}pt above the text bottom, "
                                f"so it is not sitting at the foot of the page")
    return problems


def word_band_checks(pages) -> list[str]:
    """A rendered sanity band around the prose figure the builder measures exactly.

    The ceiling itself is 6,500 prose words, enforced in src/build_report.py, which knows which paragraphs are
    headings, exhibit captions and reference entries. The audit cannot recompute that unit from a page: table
    cells and caption descriptions are indistinguishable from prose once they are rendered. So this asserts the
    weaker thing it can see - that the whole rendered body, contents page and section titles excluded, sits
    inside a band around the current 8,811. The band is wide on purpose; it is a drift detector for a section
    appearing or disappearing, not a second opinion on the ceiling.
    """
    from build_report import SECTIONS

    titles = {t for t, _subs, _drafted in SECTIONS}
    body = []
    for page in pages:
        for line in page.get_text().splitlines():
            words = line.split()
            if not words or (len(words) == 1 and words[0].isdigit()) or TOC_LINE.search(line):
                continue
            if " ".join(words) in titles:
                continue
            if words[0] in ("Figure", "Table") and len(words) == 2 and words[1].isdigit():
                continue
            body.append(" ".join(words))
    count = len(" ".join(body).split())
    if not BAND_LOW <= count <= BAND_HIGH:
        return [f"rendered body words {count} outside the {BAND_LOW}-{BAND_HIGH} band"]
    print(f"rendered body words (headings, contents and caption labels excluded): {count}")
    return []


def main(pdf: Path) -> int:
    with pymupdf.open(str(pdf)) as book:
        pages = [book[n] for n in range(book.page_count)]
        total = book.page_count
        problems: list[str] = []
        positions: dict[str, int] = {}
        per_page: dict[int, list[tuple[str, int]]] = {}
        for number, page in enumerate(pages, start=1):
            found = labels_on(page)
            if found:
                per_page[number] = found
            for label, y in found:
                if label in positions:
                    problems.append(
                        f"{label} appears on page {positions[label]} and again on {number}"
                    )
                positions[label] = number

        for number, found in per_page.items():
            if len(found) > 2:
                problems.append(f"page {number} holds {len(found)} exhibits: {[f[0] for f in found]}")
            for index, (label, y) in enumerate(found):
                if y > PAGE_BOTTOM:
                    problems.append(f"{label} starts at y={y} on page {number}, below the text block")
                if index == 0 and y > TOP_LIMIT:
                    problems.append(
                        f"{label} is the first exhibit on page {number} but starts at y={y}"
                    )
                if index == 1 and y < BOTTOM_LIMIT:
                    problems.append(
                        f"{label} is the second exhibit on page {number} at y={y}, not bottomed"
                    )

        # The contents field is resolved by Word, so this is checked on the rendered pages.
        problems += toc_checks(pages)
        problems += toc_page_checks(pages)
        problems += reference_checks(pages)
        problems += reference_render_checks(pages)
        problems += cover_checks(pages)
        problems += geometry_checks(pages)
        problems += caption_typography_checks(pages)
        problems += exhibit_gap_checks(pages)
        problems += word_band_checks(pages)

        # A figure must be on the page that carries its caption.
        for number, page in enumerate(pages, start=1):
            images = [b["bbox"] for b in page.get_text("dict")["blocks"] if b["type"] == 1]
            for label, _y in per_page.get(number, []):
                if label.startswith("Figure") and not images:
                    problems.append(f"{label} has no image on page {number}")

    print(f"pdf pages: {total}")
    print(f"exhibit captions found: {len(positions)}")
    for number in sorted(per_page):
        print(f"  p{number:>3}: " + ", ".join(f"{l} @y={y}" for l, y in per_page[number]))
    if problems:
        print("\nPROBLEMS:")
        for problem in problems:
            print("  -", problem)
        return 1
    print("\nlayout checks passed")
    return 0


if __name__ == "__main__":
    argument = Path(sys.argv[1]) if len(sys.argv) > 1 else PDF
    raise SystemExit(main(argument))
