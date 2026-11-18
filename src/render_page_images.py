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
     "GO-LDA equation (37): each new direction maximises the Fisher ratio subject to ordinary Euclidean "
     "orthogonality to the directions already accepted."),
    ("figure_02", GOLDA, 11, "full",
     "The same paper's accuracy claim ahead of Table II: after the third direction the GO-LDA directions "
     "achieve significantly better results than classic-LDA's."),
    ("figure_03", GOLDA, 12, ("table", "TABLE 2"),
     "GO-LDA Table 2: subspace accuracies by mean classification accuracy on nine data sets, the row set "
     "this study reproduces on ORL."),
    ("figure_04", IMC, 4, "full",
     "ImageNet-C's own description of the Gaussian-noise corruption this study's control used. The paper "
     "gives no sigma-versus-severity table, so the sigma = 0.08 (severity 1) value rests on the reference "
     "implementation's code, which is not in the released download set."),
    ("figure_05", C4, 6, ("table", "TABLE I"),
     "The companion study's Table I: CIFAR-100 accuracy per frozen backbone at d = 99, the paper side of "
     "the README-versus-paper diff."),
    ("figure_06", None, None, "readme",
     "The companion repository's README table for the same CIFAR-100 configurations, the other side of the "
     "19-of-72-cell disagreement."),
]


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


def pick_readme_table(lines: list[str]) -> tuple[int, list[str]]:
    """The README's CIFAR-100 accuracy table: the block carrying the cells this study diffed."""
    tables, i = [], 0
    while i < len(lines):
        if lines[i].lstrip().startswith("|"):
            j = i
            while j < len(lines) and lines[j].lstrip().startswith("|"):
                j += 1
            tables.append((i, lines[i:j]))
            i = j
        else:
            i += 1
    if not tables:
        raise SystemExit("no markdown table found in c4_README.md")
    for start, block in tables:
        if "65.07" in "\n".join(block):
            heading = ""
            for k in range(start - 1, max(-1, start - 8), -1):
                if lines[k].startswith("#"):
                    heading = lines[k].lstrip("# ").strip()
                    break
            return start, ([heading] if heading else []) + block
    raise SystemExit("c4_README.md has no CIFAR-100 accuracy table (no 65.07 cell)")


def render_readme(out: Path) -> dict:
    """Render the README table as text on a page, with the raw file's own line numbers."""
    lines = (CACHE / "c4_README.md").read_text(encoding="utf-8").split("\n")
    start, block = pick_readme_table(lines)
    doc = pymupdf.open()
    page = doc.new_page(width=880, height=70 * len(block) + 90)
    page.insert_text((28, 40), "github.com/IndarKarhana/lda-image-classification - README.md, retrieved 2026-11-19",
                     fontsize=11, fontname="helv")
    y = 68
    for offset, text in enumerate(block):
        page.insert_text((28, y), f"{start + offset + 1:>4}  {text[:118]}", fontsize=9, fontname="cour")
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
    return {"first_line": start + 1, "last_line": start + len(block), "rows": len(block)}


def main() -> int:
    ASSETS.mkdir(exist_ok=True)
    manifest = {}
    for name, source, page_number, region, caption in PAGES:
        out = ASSETS / f"{name}.png"
        if source is None:
            info = render_readme(out)
            manifest[name] = {"source": "research_records/retrieval_cache/c4_README.md",
                              "page": f"rendered text, README lines {info['first_line']}-{info['last_line']}",
                              "rows": info["rows"], "caption_line_1": name.replace("figure_", "Figure "),
                              "caption_line_2": caption, "dpi": DPI}
            print(f"{name}: README lines {info['first_line']}-{info['last_line']} -> {out.name}")
            continue
        with pymupdf.open(CACHE / source) as doc:
            page = doc[page_number - 1]
            clip = page.rect if region == "full" else clip_caption(page, region[1])
            pix = page.get_pixmap(dpi=DPI, clip=clip)
            pix.save(str(out))
        manifest[name] = {"source": f"research_records/retrieval_cache/{source}", "page": page_number,
                          "region": [round(v, 1) for v in clip], "caption_line_1": name.replace("figure_", "Figure "),
                          "caption_line_2": caption, "dpi": DPI}
        print(f"{name}: {source} p{page_number} clip {[round(v,1) for v in clip]} -> "
              f"{out.name} {pix.width}x{pix.height}px")
    (ASSETS / "figure_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1),
                                                 encoding="utf-8")
    print("manifest:", ASSETS / "figure_manifest.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
