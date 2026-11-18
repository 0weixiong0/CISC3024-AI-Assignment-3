"""M1.5: frozen-backbone feature extraction for the feature-space regime (plan WP1).

    python src/extract_features.py --throughput-only --dataset tiny_imagenet --backbone resnet18
    python src/extract_features.py --dataset cifar100 --backbone dinov2_vits14

Both backbones are frozen, in eval mode, and see ImageNet-normalised inputs at 224 x 224, which
is the resolution their own weights document; `num_classes = 0` / removing the fc means we take
the representation *before* the classifier head, so the 512-d ResNet-18 and 384-d DINOv2 vectors
are the ones C4's backbone columns describe.

Images are **streamed**, never stacked into one uint8 array: Tiny ImageNet's validation images
have mixed native sizes (64 x 64 train, anything up to 424 x 240 for val), so stacking either
fails or quietly resizes them before the backbone's own transform gets to choose. Peak memory is
then one batch, and each image goes through exactly the resize the backbone was trained with.

Nothing here is assumed. Images per second are measured on a calibration batch before anything is
committed, every extraction's wall-clock and the loader's own time are recorded, and both land in
`data/features/manifest.json` with shapes and checksums, because the plan's M1.5 row says the
extraction estimate is "to be measured, not assumed" and the supervisor's rule is that over 45 min
total means the matrix drops to one backbone per dataset and says so.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import itertools
import json
import tarfile
import time
import zipfile
from pathlib import Path

import numpy as np
import torch
from PIL import Image
from torchvision import transforms

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
FEAT = DATA / "features"

IMAGENET_MEAN = (0.485, 0.456, 0.406)
IMAGENET_STD = (0.229, 0.224, 0.225)
BATCH = 128

BACKBONES = {
    # torchvision's IMAGENET1K_V1 weights are the file the plan released and verified:
    # https://download.pytorch.org/models/resnet18-f37072fd.pth, 46,830,571 B, HTTP 200.
    "resnet18": {"source": "torchvision ResNet18_Weights.IMAGENET1K_V1",
                 "dim": 512, "where": "average-pool output before the 1000-way fc",
                 "img_size": 224},
    # U008 amendment 4: timm 1.0.29 keeps DINOv2 without fetching a third-party repository.
    # timm registers this checkpoint at 518 x 518 (1,370 tokens); it is run here at the 224 x 224
    # grid its patch-14 positional embedding resamples to (257 tokens), which measured 386.6 vs
    # 48.5 img/s on this GPU - an eightfold difference that decides whether the whole matrix fits
    # the 45-minute extraction ceiling. The choice is declared, and so is the alternative.
    "dinov2_vits14": {"source": "timm vit_small_patch14_dinov2.lvd142m, num_classes=0",
                      "dim": 384, "where": "CLS token output of the frozen ViT-S/14",
                      "img_size": 224, "timm_registered_input": "518 x 518"},
}


def build(name: str):
    """Frozen inference model plus the transform its own weights were trained with."""
    size = BACKBONES[name]["img_size"]
    tfm = transforms.Compose([transforms.Resize((size, size)),
                              transforms.ToTensor(),
                              transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD)])
    if name == "resnet18":
        from torchvision.models import ResNet18_Weights, resnet18
        model = resnet18(weights=ResNet18_Weights.IMAGENET1K_V1)
        model.fc = torch.nn.Identity()
        model.eval()
    elif name == "dinov2_vits14":
        import timm
        model = timm.create_model("vit_small_patch14_dinov2.lvd142m",
                                  pretrained=True, num_classes=0, img_size=size)
        model.eval()
    else:
        raise ValueError(f"unknown backbone {name!r}")
    for p in model.parameters():
        p.requires_grad_(False)    # frozen: no gradient, no fine-tuning, inference only
    return model, tfm, size


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


class Cifar100:
    """The released tarball, read once per split; 32 x 32 uint8 native."""

    path = DATA / "cifar100" / "cifar-100-python.tar.gz"
    url = "https://www.cs.toronto.edu/~kriz/cifar-100-python.tar.gz"
    counts = {"train": 50000, "test": 10000}

    def __init__(self):
        if not self.path.exists():
            raise FileNotFoundError(f"{self.path} missing - downloads follow the supervisor's list")
        self._raw = {}
        with tarfile.open(self.path, "r:gz") as tf:
            base = tf.getnames()[0]
            for split, key in (("train", "train"), ("test", "test")):
                blob = io.BytesIO(tf.extractfile(f"{base}/{key}").read())
                obj = np.load(blob, allow_pickle=True, encoding="bytes")
                # allow_pickle is unavoidable here: Kriz's CIFAR-100 archive is a pickled
                # Python dict, not an array file. It is read only from the archive on the
                # supervisor's released download list, whose byte size and sha256 are written
                # into the manifest, and the loaded rows are then checked against the split
                # counts before anything is used.
                raw = obj.item() if isinstance(obj, np.ndarray) and obj.shape == () else obj
                # the archive is a Python 2 pickle: read with encoding="bytes" every key stays
                # bytes, so the dictionary is normalised once instead of indexed twice
                meta = {(k.decode() if isinstance(k, bytes) else k): v for k, v in raw.items()}
                X = np.asarray(meta["data"], dtype=np.uint8)
                y = np.asarray(meta["fine_labels"], dtype=np.int64)   # CIFAR-100, not "labels"
                self._raw[split] = (X.reshape(X.shape[0], 3, 32, 32).transpose(0, 2, 3, 1), y)

    def stream(self, split: str):
        X, y = self._raw[split]
        for i in range(X.shape[0]):
            yield Image.fromarray(X[i]), int(y[i])

    def provenance(self):
        return {"archive": str(self.path), "bytes": self.path.stat().st_size,
                "sha256": sha256(self.path), "url": self.url,
                "native_size": "32 x 32 RGB", "classes": 100,
                "labels": "the archive's fine_labels key (0-99); coarse_labels is present "
                          "and unused"}


class TinyImageNet:
    """The released CS231n zip, streamed straight out of the archive.

    Train labels come from the folder names, and validation labels from
    `val/val_annotations.txt` (tab-separated: image, synset, then a bbox), both mapped onto one
    integer space by sorting the 200 synset folder names. `words.txt` is a synset-to-English
    phrase table (`n00001740<TAB>entity`), not an id list, so it is read for nothing and skipped.
    Val images keep their native mixed sizes because the backbone's transform does the resizing.
    """

    path = DATA / "tiny_imagenet" / "tiny-imagenet-200.zip"
    url = "https://cs231n.stanford.edu/tiny-imagenet-200.zip"
    counts = {"train": 100000, "test": 10000}

    def __init__(self):
        if not self.path.exists():
            raise FileNotFoundError(f"{self.path} missing - downloads follow the supervisor's list")
        with zipfile.ZipFile(self.path) as zf:
            folders = sorted({n.split("/")[2] for n in zf.namelist()
                              if n.startswith("tiny-imagenet-200/train/") and n.endswith(".JPEG")})
            label_of = {name: i for i, name in enumerate(folders)}
            if len(label_of) != 200:
                raise RuntimeError(f"expected 200 train synsets, found {len(label_of)}")
            val_ann = {}
            for ln in zf.read("tiny-imagenet-200/val/val_annotations.txt").decode().splitlines():
                cols = ln.split("\t")
                if len(cols) >= 2:
                    val_ann[cols[0]] = label_of[cols[1]]
            train_names = sorted(n for n in zf.namelist()
                                 if n.startswith("tiny-imagenet-200/train/")
                                 and n.endswith(".JPEG"))
            val_names = sorted(n for n in zf.namelist()
                               if n.startswith("tiny-imagenet-200/val/images/")
                               and n.endswith(".JPEG"))
            self._index = {"train": [(n, label_of[n.split("/")[2]]) for n in train_names],
                           "test": [(n, val_ann[n.split("/")[-1]]) for n in val_names]}

    def stream(self, split: str):
        with zipfile.ZipFile(self.path) as zf:
            for name, label in self._index[split]:
                with Image.open(io.BytesIO(zf.read(name))) as im:
                    yield im.convert("RGB"), label

    def provenance(self):
        return {"archive": str(self.path), "bytes": self.path.stat().st_size,
                "sha256": sha256(self.path), "url": self.url,
                "native_size": "train 64 x 64; val mixed (up to 424 x 240), streamed unstacked",
                "classes": 200,
                "labels": "integer ids 0-199 from the sorted train synset folder names; "
                          "val/val_annotations.txt mapped onto the same table"}


DATASETS = {"cifar100": Cifar100, "tiny_imagenet": TinyImageNet}


@torch.no_grad()
def extract(model, tfm, size, stream, n, device, batch, dim, log_every=10000):
    """Frozen forward pass over a stream of PIL images -> (n, dim) float32, one batch resident."""
    out = np.empty((n, dim), dtype=np.float32)
    labels = np.empty(n, dtype=np.int64)
    buf, lab, pos = [], [], 0
    t0 = time.perf_counter()
    for im, label in itertools.islice(stream, n):
        buf.append(tfm(im))
        lab.append(label)
        if len(buf) == batch:
            x = torch.stack(buf).to(device)
            out[pos:pos + len(buf)] = model(x).float().cpu().numpy()
            labels[pos:pos + len(buf)] = lab
            pos += len(buf)
            buf, lab = [], []
            if log_every and pos % log_every < batch:
                el = time.perf_counter() - t0
                print(f"    {pos}/{n} images, {pos / el:.1f} img/s, {el:.0f} s elapsed",
                      flush=True)
    if buf:
        x = torch.stack(buf).to(device)
        out[pos:pos + len(buf)] = model(x).float().cpu().numpy()
        labels[pos:pos + len(buf)] = lab
        pos += len(buf)
    if pos != n:
        raise RuntimeError(f"stream yielded {pos} images, manifest says {n}")
    return out, labels, time.perf_counter() - t0


def probe_dim(model, size, device=None):
    with torch.no_grad():
        x = torch.zeros(1, 3, size, size)
        if device is not None:
            x = x.to(device)
        return int(model(x).shape[1])


def main(argv=None):
    ap = argparse.ArgumentParser(description="frozen feature extraction (M1.5)")
    ap.add_argument("--dataset", default="cifar100", choices=sorted(DATASETS))
    ap.add_argument("--backbone", default="resnet18", choices=sorted(BACKBONES))
    ap.add_argument("--throughput-only", action="store_true",
                    help="calibrate images/second on 512 images and exit")
    ap.add_argument("--batch", type=int, default=BATCH)
    ap.add_argument("--splits", default="train,test")
    args = ap.parse_args(argv)

    FEAT.mkdir(parents=True, exist_ok=True)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model, tfm, size = build(args.backbone)
    model = model.to(device)
    model.eval()
    dim = probe_dim(model, size, device)
    assert dim == BACKBONES[args.backbone]["dim"], (dim, args.backbone)
    src = BACKBONES[args.backbone]["source"] + (
        f", timm registered input {BACKBONES[args.backbone].get('timm_registered_input')}"
        if "timm_registered_input" in BACKBONES[args.backbone] else "")
    print(f"{args.backbone}: {src} -> {dim}-d at {size}x{size} on {device}", flush=True)

    data = DATASETS[args.dataset]()
    n_cal = min(512, data.counts["train"])
    t0 = time.perf_counter()
    _, _, t_cal = extract(model, tfm, size, data.stream("train"), n_cal, device,
                          args.batch, dim, log_every=0)
    rate = n_cal / t_cal
    cal = {"images": n_cal, "seconds": t_cal, "img_per_s": rate,
           "projected_train_seconds": rate and data.counts["train"] / rate,
           "note": "calibration reads the first images of the train split, so it includes the "
                   "decode and resize cost the full run pays"}
    mins = (data.counts["train"] + data.counts["test"]) / rate / 60
    print(f"calibration: {n_cal} images in {t_cal:.1f} s = {rate:.1f} img/s; "
          f"both splits would take {mins:.1f} min", flush=True)
    if args.throughput_only:
        print(json.dumps({"dataset": args.dataset, "backbone": args.backbone,
                          "counts": data.counts, "calibration": cal,
                          "ceiling_check": {"limit_minutes": 45,
                                            "this_pair_minutes": round(mins, 1)}}, indent=2))
        return 0

    record = {"dataset": args.dataset, "backbone": args.backbone, "model": src,
              "dim": dim, "input": f"{size}x{size} ImageNet-normalised", "batch": args.batch,
              "device": device, "frozen": True, "precision": "float32, no autocast",
              "source_archive": data.provenance(),
              "calibration": cal, "splits": {}}
    for split in [s.strip() for s in args.splits.split(",")]:
        feats, labels, secs = extract(model, tfm, size, data.stream(split),
                                      data.counts[split], device, args.batch, dim)
        npy = FEAT / f"{args.dataset}_{args.backbone}_{split}.npy"
        lp = FEAT / f"{args.dataset}_{args.backbone}_{split}_y.npy"
        np.save(npy, feats)
        np.save(lp, labels)
        record["splits"][split] = {"features": npy.name, "shape": list(feats.shape),
                                   "dtype": "float32", "labels": lp.name,
                                   "classes": int(len(np.unique(labels))),
                                   "seconds": secs, "img_per_s": feats.shape[0] / secs,
                                   "sha256": sha256(npy),
                                   "feature_min": float(feats.min()),
                                   "feature_max": float(feats.max())}
        print(f"  {split}: {feats.shape} in {secs:.1f} s ({feats.shape[0] / secs:.1f} img/s) "
              f"-> {npy.name}", flush=True)
    record["total_seconds"] = sum(s["seconds"] for s in record["splits"].values())

    index = FEAT / "manifest.json"
    entries = json.loads(index.read_text(encoding="utf-8")) if index.exists() else []
    entries = [e for e in entries if not (e["dataset"] == args.dataset
                                          and e["backbone"] == args.backbone)]
    entries.append(record)
    index.write_text(json.dumps(entries, indent=2), encoding="utf-8")
    all_minutes = sum(e["total_seconds"] for e in entries) / 60
    print(f"total for this pair {record['total_seconds'] / 60:.1f} min; all cached extractions "
          f"{all_minutes:.1f} min; manifest: {index}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
