"""Render the page images the report cites by page number into report_assets/.

Project : CISC3024 AI Assignment #3 (Pattern Recognition, University of Macau)
Author  : AI-generated implementation (Qoder). The student wrote no code.

Standing rule (U018/U019): every claim that quotes a page of someone else's paper carries that page's
rendered image. `research_records/retrieval_cache/` holds the sources (gitignored, downloaded under the
supervisor's release); `report_assets/` holds the rendered figures (also gitignored). Captions are two
lines - the exhibit number, then the italic description - because `audit_docx.py`'s caption regex expects
that shape.

Each render records what it came from - source file, page, and the region clipped - so a figure can be
reproduced or challenged from the artefact rather than from memory.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "research_records" / "retrieval_cache"
ASSETS = ROOT / "report_assets"
DPI = 200

GOLDA = "golda_arxiv2305.14568v1.pdf"
IMC = "imagenetc_arxiv1903.12261.pdf"
C4 = "c4_arxiv2604.03928v2.pdf"

# name, source, page, region, caption
PAGES = [
    ("figure_01", GOLDA, 6, "full",
     "GO-LDA equations (37) and (38): each new direction maximises the Fisher ratio subject to ordinary "
     "Euclidean orthogonality to the directions already accepted, and is the eigenvector of the deflated "
     "pencil that follows from that constraint."),
    ("figure_02", GOLDA, 11, "full",
     "The same paper's accuracy claim ahead of Table 2: the GO-LDA directions achieve significantly better "
     "results than classic-LDA's, and after the third direction they also beat PCA's principal directions."),
    ("figure_03", GOLDA, 12, ("table", "TABLE 2"),
     "GO-LDA Table 2: subspace accuracies by mean classification accuracy on nine data sets, the row set "
     "this study reproduces on ORL."),
    ("figure_04", IMC, 4, "full",
     "ImageNet-C's own description of the Gaussian-noise corruption this study's control used; the opening "
     "sentence of Common Corruptions names it as the first corruption type."),
    ("figure_05", C4, 6, ("table", "TABLE I"),
     "The companion study's Table I: CIFAR-100 accuracy per frozen backbone at d = 99 for every reduction "
     "except its own RDA and RDA+SMD, which the caption says use 99 + k - the paper side of the "
     "README-versus-paper diff."),
    ("figure_06", None, None, "readme",
     "The companion repository's README table for the same CIFAR-100 configurations, the other side of the "
     "cell-by-cell diff whose overall count is 19 of 72 across all three dataset tables."),
]

# The code line the sigma value rests on: the released ImageNet-C reference implementation.
CORRUPTIONS = "imagenetc_corruptions.py"
CODE = {
    "name": "figure_07",
    "file": CORRUPTIONS,
    "lines": (122, 126),
    "repo": "github.com/hendrycks/robustness",
    "path": "ImageNet-C/imagenet_c/imagenet_c/corruptions.py",
    "commit": "712bfcd18ba1159df5f7ed46f4e6cae611bfe60e",
    "blob_sha": "f0bf2d495dc9514e8e6f800d1d2a753f781f9dd8",
    "caption": "The reference implementation's gaussian_noise: the severity list opens at 0.08 on unit "
               "pixels, which is the sigma this study's single fixed corruption used.",
}


def clip_caption(page: pymupdf.Page, label: str) -> pymupdf.Rect:
    """The caption line plus the contiguous block group below it - tables are not detected reliably."""
    blocks = sorted(page.get_text("blocks"), key=lambda b: b[1])
    start = next((i for i, b in enumerate(blocks) if b[4].strip().startswith(label)), None)
    if start is None:
        raise SystemExit(f"caption {label!r} not found on page {page.number + 1}")
    group, x0, x1, y0, y1 = [blocks[start]], None, None, None, None
    for b in blocks[start:]:
        if b is not blocks[start]:
            if b[4].strip().upper().startswith(("TABLE", "Fig.")) or (b[1] - y1) > 26:
                break
        group.append(b)
        x0 = b[0] if x0 is None else min(x0, b[0])
        x1 = b[2] if x1 is None else max(x1, b[2])
        y0 = b[1] if y0 is None else min(y0, b[1])
        y1 = b[3] if y1 is None else max(y1, b[3])
    return pymupdf.Rect(max(0, x0 - 6), max(0, y0 - 6), min(page.rect.x1, x1 + 6), min(page.rect.y1, y1 + 8))


def pick_readme_table(lines: list[str]) -> list[tuple[int, str]]:
    """The README's CIFAR-100 accuracy table, with the heading above it kept attached.

    The block is found by the cell this study diffed rather than by a hard-coded range, so a README edit that
    moves the table moves the figure with it. Line numbers are carried per row rather than derived from an
    offset: the heading and the table are separated by a blank line, and a derived offset would misstate both.
    """
    i = 0
    while i < len(lines):
        if not lines[i].lstrip().startswith("|"):
            i += 1
            continue
        j = i
        while j < len(lines) and lines[j].lstrip().startswith("|"):
            j += 1
        block = [(k + 1, lines[k]) for k in range(i, j)]
        if any("65.07" in t for _n, t in block):
            for k in range(i - 1, max(-1, i - 8), -1):
                if lines[k].startswith("#"):
                    return [(k + 1, lines[k]), (None, ""), *block] if k + 2 < i else [(k + 1, lines[k]), *block]
            return block
        i = j
    raise SystemExit("c4_README.md has no CIFAR-100 accuracy table (no 65.07 cell)")


def render_readme(out: Path) -> dict:
    """Render the README table as text on a page, with the raw file's own line numbers."""
    lines = (CACHE / "c4_README.md").read_text(encoding="utf-8").split(chr(10))
    block = pick_readme_table(lines)
    shown = [n for n, _t in block if n]
    doc = pymupdf.open()
    page = doc.new_page(width=880, height=70 * len(block) + 90)
    page.insert_text((28, 40), "github.com/IndarKarhana/lda-image-classification - README.md, retrieved 2026-11-19",
                     fontsize=11, fontname="helv")
    y = 68
    for number, text in block:
        label = f"{number:>4}" if number else "    "
        page.insert_text((28, y), f"{label}  {text[:118]}", fontsize=9, fontname="cour")
        y += 14
    tmp = out.with_suffix(".tmp.pdf")
    tmp.write_bytes(doc.convert_to_pdf())
    doc.close()
    rendered = pymupdf.open(str(tmp))
    # Clip to the drawn area: the page is sized generously, and a figure that is 90 % blank wastes
    # report space when it is placed.
    bottom = 78 + 14 * len(block)
    rendered[0].get_pixmap(dpi=DPI, clip=pymupdf.Rect(18, 26, 862, bottom)).save(str(out))
    rendered.close()
    tmp.unlink()
    return {"first_line": min(shown), "last_line": max(shown), "rows": len(block)}


def render_code(out: Path) -> dict:
    """Render the pinned corruption file's gaussian_noise lines, with their own line numbers."""
    lines = (CACHE / CODE["file"]).read_text(encoding="utf-8").split("\n")
    first, last = CODE["lines"]
    block = lines[first - 1:last]
    doc = pymupdf.open()
    page = doc.new_page(width=880, height=70 * len(block) + 90)
    page.insert_text((28, 40), f"{CODE['repo']} - {CODE['path']}", fontsize=11, fontname="helv")
    page.insert_text((28, 56), f"pinned at commit {CODE['commit']}, blob sha256-less git sha "
                              f"{CODE['blob_sha']}", fontsize=9, fontname="helv")
    y = 84
    for offset, text in enumerate(block):
        page.insert_text((28, y), f"{first + offset:>4}  {text[:118]}", fontsize=9, fontname="cour")
        y += 14
    tmp = out.with_suffix(".tmp.pdf")
    tmp.write_bytes(doc.convert_to_pdf())
    doc.close()
    rendered = pymupdf.open(str(tmp))
    rendered[0].get_pixmap(dpi=DPI, clip=pymupdf.Rect(18, 26, 862, 96 + 14 * len(block))).save(str(out))
    rendered.close()
    tmp.unlink()
    return {"first_line": first, "last_line": last, "block": block}


def main() -> int:
    ASSETS.mkdir(exist_ok=True)
    # Merge, not overwrite: src/render_own_figures.py appends its own entries to this file, and a full rewrite
    # here would silently delete them; entries are removed by deleting the PNG and its key, not by re-running.
    manifest_path = ASSETS / "figure_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    for name, source, page_number, region, caption in PAGES:
        out = ASSETS / f"{name}.png"
        if source is None:
            info = render_readme(out)
            manifest[name] = {"source": "research_records/retrieval_cache/c4_README.md",
                              "page": f"rendered text, README lines {info['first_line']}-{info['last_line']} (the heading line and the table rows; the blank between them is not counted)",
                              "rows": info["rows"], "report_label": "numbered by a SEQ field in the report, not here",
                              "caption_line_2": caption, "dpi": DPI}
            print(f"{name}: README lines {info['first_line']}-{info['last_line']} -> {out.name}")
            continue
        with pymupdf.open(CACHE / source) as doc:
            page = doc[page_number - 1]
            clip = page.rect if region == "full" else clip_caption(page, region[1])
            pix = page.get_pixmap(dpi=DPI, clip=clip)
            pix.save(str(out))
        manifest[name] = {"source": f"research_records/retrieval_cache/{source}", "page": page_number,
                          "region": [round(v, 1) for v in clip],
                          "report_label": "numbered by a SEQ field in the report, not here",
                          "caption_line_2": caption, "dpi": DPI}
        print(f"{name}: {source} p{page_number} clip {[round(v,1) for v in clip]} -> "
              f"{out.name} {pix.width}x{pix.height}px")
    code_out = ASSETS / f"{CODE['name']}.png"
    info = render_code(code_out)
    manifest[CODE["name"]] = {
        "source": f"research_records/retrieval_cache/{CODE['file']}",
        "page": f"rendered text, lines {info['first_line']}-{info['last_line']}",
        "repository": CODE["repo"], "path": CODE["path"], "commit": CODE["commit"],
        "blob_sha": CODE["blob_sha"], "quoted": info["block"],
        "report_label": "numbered by a SEQ field in the report, not here", "caption_line_2": CODE["caption"],
        "dpi": DPI,
    }
    (ASSETS / "figure_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1, sort_keys=True),
                                                 encoding="utf-8")
    print(f"{CODE['name']}: {CODE['file']} lines {info['first_line']}-{info['last_line']} "
          f"@ {CODE['commit'][:8]} -> {code_out.name}")
    print("manifest:", ASSETS / "figure_manifest.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
