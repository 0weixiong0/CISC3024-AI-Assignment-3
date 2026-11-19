"""The reference list: APA 7 entries for the works the prose cites, and the in-text forms they answer.

Project : CISC3024 AI Assignment #3 (Pattern Recognition, University of Macau)
Author  : AI-generated implementation (Qoder). The student wrote no code.

Why every entry here can be traced back to a page
--------------------------------------------------
Each entry was read from a record reached under the supervisor's released list of metadata lookups - the arXiv
and Crossref landing pages, the official dataset and repository pages - rather than written from recollection,
and plan section 12 lists the address each entry's authors, title and date came from. Nothing is cited that has
no such record: where section 2 names a journal, it names the venue rather than a work, so the venue has no
entry and claims none. The one entry that rests on an archive rather than a landing page is the Tiny ImageNet
data set, whose URL answers with the 248,100,043 bytes this study actually read.

The same-author pairs are disambiguated with a and b, which APA 7 requires when a paper and the software it
ships are both cited: (Hendrycks & Dietterich, 2019a) is the benchmark paper, (2019b) the corruption code,
and (Kumar et al., 2026a/2026b) the companion paper and its repository.
"""

from __future__ import annotations

# (sort key, in-text form, entry text). Entries are emitted in this order, which is alphabetical by author.
ENTRIES = [
    ("att-2002",
     "AT&T Laboratories Cambridge (2002)",
     "AT&T Laboratories Cambridge. (2002). *The database of faces* [Dataset]. "
     "http://www.cl.cam.ac.uk/research/dtg/attarchive/facedatabase.html"),
    ("bi-2025",
     "Bi et al. (2025)",
     "Bi, P., Chen, M., Du, X., Sohrab, F., & Gabbouj, M. (2025). Double layer robust 2DPCA: "
     "Joint flexible cut norm and adaptive weighted learning for small sample size image "
     "recognition. *IEEE Transactions on Consumer Electronics, 71*(4), 10491-10506. "
     "https://doi.org/10.1109/TCE.2025.3602258"),
    ("harris-2020",
     "Harris et al. (2020)",
     "Harris, C. R., Millman, K. J., van der Walt, S. J., Gommers, R., Virtanen, P., "
     "Cournapeau, D., Wieser, E., Taylor, J., Berg, S., Smith, N. J., Kern, R., Picus, M., "
     "Hoyer, S., van Kerkwijk, M. H., Brett, M., Haldane, A., del Rio, J. F., Wiebe, M., "
     "Peterson, P., ... Oliphant, T. E. (2020). *Array programming with NumPy*. *Nature, "
     "585*(7825), 357-362. https://doi.org/10.1038/s41586-020-2649-2"),
    ("he-2015",
     "He et al. (2015)",
     "He, K., Zhang, X., Ren, S., & Sun, J. (2015). *Deep residual learning for image "
     "recognition* (arXiv:1512.03385) [Preprint]. arXiv. https://arxiv.org/abs/1512.03385"),
    ("hendrycks-2019a",
     "Hendrycks and Dietterich (2019a)",
     "Hendrycks, D., & Dietterich, T. (2019a). Benchmarking neural network robustness to "
     "common corruptions and perturbations. In *International Conference on Learning "
     "Representations*. https://arxiv.org/abs/1903.12261"),
    ("hendrycks-2019b",
     "Hendrycks and Dietterich (2019b)",
     "Hendrycks, D., & Dietterich, T. (2019b). *Robustness* (Version 712bfcd) [Computer "
     "software]. GitHub. https://github.com/hendrycks/robustness"),
    ("krizhevsky-2009",
     "Krizhevsky (2009)",
     "Krizhevsky, A. (2009). *Learning multiple layers of features from tiny images* "
     "[Technical report]. University of Toronto. https://www.cs.toronto.edu/~kriz/cifar.html"),
    ("kumar-2026a",
     "Kumar et al. (2026a)",
     "Kumar, I., Karhana, G., Jasti, S. K., & Lade, A. H. (2026a). *Supervised dimensionality "
     "reduction revisited: Why LDA on frozen CNN features deserves a second look* (Version 2; "
     "arXiv:2604.03928) [Preprint]. arXiv. https://arxiv.org/abs/2604.03928"),
    ("kumar-2026b",
     "Kumar et al. (2026b)",
     "Kumar, I., Karhana, G., Jasti, S. K., & Lade, A. H. (2026b). *lda-image-classification* "
     "(MIT licence) [Computer software]. GitHub. Retrieved November 19, 2026, from "
     "https://github.com/IndarKarhana/lda-image-classification"),
    ("le-2015",
     "Le & Yang (2015)",
     "Le, Y., & Yang, X. (2015). *Tiny ImageNet visual recognition challenge* [Data set]. "
     "Stanford CS231n. https://cs231n.stanford.edu/tiny-imagenet-200.zip"),
    ("liu-2023",
     "Liu et al. (2023)",
     "Liu, J., Cai, X., & Niranjan, M. (2023). *GO-LDA: Generalised optimal linear "
     "discriminant analysis* (arXiv:2305.14568) [Preprint]. arXiv. "
     "https://arxiv.org/abs/2305.14568"),
    ("oquab-2023",
     "Oquab et al. (2023)",
     "Oquab, M., Darcet, T., Moutakanni, T., Vo, H., Szafraniec, M., Khalidov, V., Fernandez, "
     "P., Haziza, D., Massa, F., El-Nouby, A., Assran, M., Ballas, N., Galuba, W., Howes, R., "
     "Huang, P., Li, S., Misra, I., Rabbat, M., Sharma, V., ... Bojanowski, P. (2023). "
     "*DINOv2: Learning robust visual features without supervision* (Version 2; "
     "arXiv:2304.07193) [Preprint]. arXiv. https://arxiv.org/abs/2304.07193"),
    ("paszke-2019",
     "Paszke et al. (2019)",
     "Paszke, A., Gross, S., Massa, F., Lerer, A., Bradbury, J., Chanan, G., Killeen, T., Lin, "
     "Z., Gimelshein, N., Antiga, L., Desmaison, A., Kopf, A., Yang, E., DeVito, Z., Raison, "
     "M., Tejani, A., Chilamkurthy, S., Steiner, B., Fang, L., ... Chintala, S. (2019). "
     "*PyTorch: An imperative style, high-performance deep learning library* "
     "(arXiv:1912.01703) [Preprint]. arXiv. https://arxiv.org/abs/1912.01703"),
    ("pedregosa-2011",
     "Pedregosa et al. (2011)",
     "Pedregosa, F., Varoquaux, G., Gramfort, A., Michel, V., Thirion, B., Grisel, O., "
     "Blondel, M., Prettenhofer, P., Weiss, R., Dubourg, V., Vanderplas, J., Passos, A., "
     "Cournapeau, D., Brucher, M., Perrot, M., & Duchesnay, E. (2011). Scikit-learn: Machine "
     "learning in Python. *Journal of Machine Learning Research, 12*, 2825-2830."),
    ("wang-2025",
     "Wang et al. (2025)",
     "Wang, J., Xie, X., Zhang, L., Li, J., Cai, H., & Feng, Y. (2025). Robust sparse smooth "
     "principal component analysis for face reconstruction and recognition. *PLOS ONE, 20*(5), "
     "e0323281. https://doi.org/10.1371/journal.pone.0323281")
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
    "krizhevsky-2009": "(Krizhevsky, 2009)",
    "att-2002": "(AT&T Laboratories Cambridge, 2002)",
    "harris-2020": "(Harris et al., 2020)",
    "he-2015": "(He et al., 2015)",
    "bi-2025": "(Bi et al., 2025)",
    "oquab-2023": "(Oquab et al., 2023)",
    "paszke-2019": "(Paszke et al., 2019)",
    "pedregosa-2011": "(Pedregosa et al., 2011)",
    "wang-2025": "(Wang et al., 2025)",
    "le-2015": "(Le & Yang, 2015)",
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
