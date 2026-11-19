"""The reference list: APA 7 entries for the works the prose cites, and the in-text forms they answer.

Project : CISC3024 AI Assignment #3 (Pattern Recognition, University of Macau)
Author  : AI-generated implementation (Qoder). The student wrote no code.

Why this list is short, and why that is stated rather than papered over
----------------------------------------------------------------------
Every entry here was read from a source that is on disk in `research_records/retrieval_cache/`, so the author
names, titles and dates are transcriptions rather than recollections. The works the study *uses* but does not
*argue about* - the two image data sets, the two frozen backbones, the numerical libraries, and the two
runner-up candidates in the screening ledger - have no bibliographic record on disk, and their author initials
cannot be written from memory into an APA list. They are therefore absent from both the list and the prose,
and plan section 12 records them as a release request rather than inventing them.

The two same-author pairs are disambiguated with a and b, which APA 7 requires when a paper and the software it
ships are both cited: (Hendrycks & Dietterich, 2019a) is the benchmark paper, (2019b) the corruption code.
"""

from __future__ import annotations

# (sort key, in-text form, entry text). Entries are emitted in this order, which is alphabetical by author.
ENTRIES = [
    ("hendrycks-2019a",
     "Hendrycks and Dietterich (2019a)",
     "Hendrycks, D., & Dietterich, T. (2019). Benchmarking neural network robustness to common corruptions "
     "and perturbations. In International Conference on Learning Representations. "
     "https://arxiv.org/abs/1903.12261"),
    ("hendrycks-2019b",
     "Hendrycks and Dietterich (2019b)",
     "Hendrycks, D., & Dietterich, T. (2019). Robustness (Commitment 712bfcd) [Computer software]. GitHub. "
     "https://github.com/hendrycks/robustness"),
    ("kumar-2026a",
     "Kumar et al. (2026a)",
     "Kumar, I., Karhana, G., Jasti, S. K., & Lade, A. H. (2026). Supervised dimensionality reduction "
     "revisited: Why LDA on frozen CNN features deserves a second look (Version 2; arXiv:2604.03928) "
     "[Preprint]. arXiv. https://arxiv.org/abs/2604.03928"),
    ("kumar-2026b",
     "Kumar et al. (2026b)",
     "Kumar, I., Karhana, G., Jasti, S. K., & Lade, A. H. (2026). lda-image-classification (MIT licence) "
     "[Computer software]. GitHub. Retrieved November 19, 2026, from "
     "https://github.com/IndarKarhana/lda-image-classification"),
    ("liu-2023",
     "Liu et al. (2023)",
     "Liu, J., Cai, X., & Niranjan, M. (2023). GO-LDA: Generalised optimal linear discriminant analysis "
     "(arXiv:2305.14568) [Preprint]. arXiv. https://arxiv.org/abs/2305.14568"),
]


# The in-text form each entry must appear under. The build checks the assembled document for these strings,
# so an entry that stops being cited, or a citation whose entry is removed, fails the build rather than the
# examiner's eye.
IN_TEXT = {
    "hendrycks-2019a": "(Hendrycks & Dietterich, 2019a)",
    "hendrycks-2019b": "(Hendrycks & Dietterich, 2019b)",
    "kumar-2026a": "(Kumar et al., 2026a)",
    "kumar-2026b": "(Kumar et al., 2026b)",
    "liu-2023": "(Liu et al., 2023)",
}


def entries() -> list[str]:
    return [text for _key, _form, text in ENTRIES]


def check(prose: str) -> list[str]:
    """Return one complaint per entry that is not cited, or per citation form with no entry."""
    problems = []
    for key, _form, _text in ENTRIES:
        if IN_TEXT[key] not in prose:
            problems.append(f"entry {key} is not cited in the text")
    for key, form in IN_TEXT.items():
        if form in prose and key not in {k for k, _f, _t in ENTRIES}:
            problems.append(f"in-text citation {form} has no entry")
    return problems
