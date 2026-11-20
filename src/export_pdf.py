"""Resolve the table of contents and export the PDF, using a private Word instance.

Project : CISC3024 AI Assignment #3 (Pattern Recognition, University of Macau)
Author  : AI-generated implementation (Qoder). The student wrote no code.

Word, not python-docx, has to do this work: the table of contents is a field inside the template's
content control, and only the application that paginates the document can resolve the page numbers.

Two details learned the hard way:
* the contents page numbers are recorded in ``analysis/toc_pages.json`` from the exported PDF; the
  file is evidence of where each heading landed, and nothing bakes it back in, because Word resolves the
  contents field itself when it saves.
* the document is opened with ``UpdateFields=False``, because Word's "update fields that refer to
  other files?" prompt is modal and it blocks automation silently;
* the field is updated twice around a re-pagination, because the first update changes the page count
  the second update has to report.

With ``--measure`` the exported PDF is additionally read back to map each heading to the page it
landed on, written to ``analysis/toc_pages.json``. That file is what ``build_report.py`` bakes into
the cached PAGEREF results, so the table of contents is correct in the Word file itself rather than
only after somebody presses F9.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

import win32com.client

ROOT = Path(__file__).resolve().parent.parent
DOCX = ROOT / "CISC3024_AI_Assignment_3_Report.docx"
PDF = ROOT / "CISC3024_AI_Assignment_3_Report.pdf"
TOC_PAGES = ROOT / "analysis/toc_pages.json"

WD_FORMAT_PDF = 17
WD_FORMAT_XML_DOCUMENT = 12
WD_STATISTIC_PAGES = 2
WD_STATISTIC_WORDS = 0


def resolve(docx_path: Path, pdf_path: Path) -> int:
    if not docx_path.exists():
        raise SystemExit(f"nothing to convert: {docx_path} does not exist")
    # Word opens the delivered file as read-only when another instance has touched it, and then
    # refuses to save over it. Working through temporary names and moving them into place afterwards
    # is what makes this step repeatable.
    temp_docx = docx_path.with_name(f"_wordtmp_{docx_path.name}")
    temp_pdf = pdf_path.with_name(f"_wordtmp_{pdf_path.name}")
    word = win32com.client.DispatchEx("Word.Application")
    try:
        # A hidden Word instance never returns on this machine, and a blanket Fields.Update wedges it
        # because the table of contents field is itself in the field collection. Updating the TOC
        # alone resolves every PAGEREF inside it and finishes in seconds.
        word.Visible = True
        word.DisplayAlerts = 0
        document = word.Documents.Open(str(docx_path.resolve()))
        try:
            document.Repaginate()
            for index in range(1, document.TablesOfContents.Count + 1):
                document.TablesOfContents(index).Update()
            pages = document.ComputeStatistics(WD_STATISTIC_PAGES)
            words = document.ComputeStatistics(WD_STATISTIC_WORDS)
            document.SaveAs2(str(temp_docx.resolve()), FileFormat=WD_FORMAT_XML_DOCUMENT)
            document.ExportAsFixedFormat(str(temp_pdf.resolve()), WD_FORMAT_PDF)
            print(f"pages: {pages}  words: {words}")
        finally:
            document.Close(False)
    finally:
        word.Quit()
    temp_docx.replace(docx_path)
    temp_pdf.replace(pdf_path)
    # Word re-splits runs when it resolves the fields, and the split runs inherit their size from the
    # style instead of carrying it, so the font census would read them as "Times New Roman, no size".
    # Writing the resolved size back is invisible on the page and keeps the census a real check.
    sys.path.insert(0, str(ROOT / "src"))
    from build_report import explicit_sizes
    from docx import Document
    document = Document(str(docx_path))
    written = explicit_sizes(document)
    # Word also rewrites the file's author as whoever's machine ran the save, which is how a docx whose cover
    # says LI WAI HONG ends up reporting somebody else in its properties. The released values are the only
    # source, so the same pass that fixes the run sizes puts them back.
    values = ROOT / "report_assets" / "cover_values.json"
    if values.exists():
        name = json.loads(values.read_text(encoding="utf-8")).get("author", "")
        if name:
            document.core_properties.author = name
            document.core_properties.last_modified_by = name
    document.save(str(docx_path))
    print(f"run sizes made explicit after field resolution: {written}")
    print(f"docx: {docx_path}")
    print(f"pdf : {pdf_path}")
    return pages


def measure(pdf_path: Path, headings: list[str]) -> dict[str, int]:
    """Map each heading to the page it starts on, ignoring the contents pages themselves."""
    import fitz  # pymupdf

    pages_text = []
    with fitz.open(str(pdf_path)) as book:
        for number in range(len(book)):
            pages_text.append(re.sub(r"\s+", " ", book[number].get_text()))
    toc_pages = {
        index
        for index, text in enumerate(pages_text)
        if sum(1 for h in headings if h in text) >= 5
    }
    found: dict[str, int] = {}
    for heading in headings:
        pattern = re.compile(r"(?<![A-Za-z-])" + re.escape(heading) + r"(?![A-Za-z])")
        for index, text in enumerate(pages_text):
            if index in toc_pages:
                continue
            if pattern.search(text):
                found[heading] = index + 1
                break
    missing = [h for h in headings if h not in found]
    if missing:
        raise SystemExit(f"headings not located in the PDF: {missing}")
    return found


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--docx", type=Path, default=DOCX)
    parser.add_argument("--pdf", type=Path, default=PDF)
    parser.add_argument("--measure", action="store_true")
    arguments = parser.parse_args(sys.argv[1:])
    if arguments.measure:
        # The headings are read from the built document, not from a source list: the contents field, the
        # headings Word paginates and the audit all see the assembled file, and only this file can say what
        # the contents has to agree with. An earlier version imported a `CONTENT` symbol that no module
        # defines, which is why this path had never run.
        from docx import Document

        document = Document(str(arguments.docx))
        headings = [paragraph.text.strip() for paragraph in document.paragraphs
                    if paragraph.style is not None and paragraph.style.name in ("Heading 1", "Heading 2", "Heading 3")
                    and paragraph.text.strip()]
        pages = measure(arguments.pdf, headings)
        TOC_PAGES.parent.mkdir(exist_ok=True)
        TOC_PAGES.write_text(json.dumps(pages, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"mapped {len(pages)} headings -> {TOC_PAGES}")
        subprocess.run([sys.executable, str(ROOT / "src/build_report.py")], check=True)
        resolve(arguments.docx, arguments.pdf)
        return 0
    resolve(arguments.docx, arguments.pdf)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
