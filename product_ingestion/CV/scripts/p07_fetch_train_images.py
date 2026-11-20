"""P07: choose a class-balanced subset of Fashionpedia TRAIN images and fetch only those from the official
train2020.zip using HTTP range requests (no 3.3 GB download).

  .venv/Scripts/python.exe product_ingestion/CV/scripts/p07_fetch_train_images.py --budget 9000
"""
import argparse
import collections
import io
import json
import random
import sys
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parent))
from p07_common import *  # noqa

URL = "https://s3.amazonaws.com/ifashionist-dataset/images/train2020.zip"
ap = argparse.ArgumentParser()
ap.add_argument("--budget", type=int, default=9000)
ap.add_argument("--plain_frac", type=float, default=0.25, help="share of budget spent on plain/common-only images")
ap.add_argument("--select_only", action="store_true")
a = ap.parse_args()
random.seed(0)

OUT.mkdir(parents=True, exist_ok=True)
jp = DATA / "fashionpedia_train" / "instances_attributes_train2020.json"
sel_path = OUT / "train_selection.json"

if not sel_path.exists():
    _, _, anns, images = stream_coco(jp, keep_seg_images=None)
    by = collections.defaultdict(list)
    for x in anns:
        by[x["image_id"]].append(x)
    print("train images", len(images), "annotations", len(anns))
    rare, common = [], []
    cnt = collections.Counter()
    for iid, aa in by.items():
        rare_flag = False
        labs = []
        for g in aa:
            if g["category_id"] in PATTERN_CATS and not g.get("iscrowd"):
                lab = garment_pattern_label(g)
                if lab and not lab[2]:
                    labs.append(("pattern", lab[1]))
                    if lab[1] != "plain":
                        rare_flag = True
            if g["category_id"] == SLEEVE_PART:
                for t in g["attribute_ids"]:
                    if t in SLEEVE_FINE:
                        labs.append(("sleeve_part", SLEEVE_FINE[t]))
                        if SLEEVE_FINE[t] != "long":
                            rare_flag = True
            if g["category_id"] == NECK_PART:
                f = [NECK_FINE[t] for t in g["attribute_ids"] if t in NECK_FINE]
                if len(f) == 1 and f[0] in NECK_MERGE:
                    labs.append(("neckline", NECK_MERGE[f[0]]))
                    if NECK_MERGE[f[0]] != "round_crew":
                        rare_flag = True
        if not labs:
            continue
        # keep only images that have an upper/dress garment (so crops exist)
        if not any(g["category_id"] in PATTERN_CATS for g in aa):
            continue
        (rare if rare_flag else common).append(iid)
        for l in labs:
            cnt[l] += 1
    print("candidate images: rare", len(rare), "common", len(common))
    n_common = int(a.budget * a.plain_frac)
    n_rare = a.budget - n_common
    # prioritise images with text/graphic/other/sleeveless, then random
    prio = []
    for iid in rare:
        s = 0
        for g in by[iid]:
            if g["category_id"] in PATTERN_CATS:
                lab = garment_pattern_label(g)
                if lab and not lab[2] and lab[1] in ("text", "graphic", "other", "dot", "abstract", "check", "geometric"):
                    s += 2
            if g["category_id"] == SLEEVE_PART and any(t == 156 for t in g["attribute_ids"]):
                s += 2
            if g["category_id"] == NECK_PART and any(t in (179, 194, 196, 197, 198, 199, 187) for t in g["attribute_ids"]):
                s += 1
        prio.append((-s, random.random(), iid))
    prio.sort()
    chosen = [i for _, _, i in prio[:n_rare]]
    random.shuffle(common)
    chosen += common[:n_common]
    sel = {"image_ids": sorted(chosen), "files": {str(i): images[i]["file_name"] for i in chosen},
           "label_counts_before_selection": {f"{k[0]}:{k[1]}": v for k, v in cnt.items()}}
    json.dump(sel, open(sel_path, "w"))
    print("selected", len(chosen))
else:
    sel = json.load(open(sel_path))

if a.select_only:
    sys.exit(0)


class RangeFile(io.RawIOBase):
    def __init__(self, url):
        self.url, self.pos = url, 0
        req = urllib.request.Request(url, method="HEAD")
        self.size = int(urllib.request.urlopen(req).headers["Content-Length"])

    def seekable(self):
        return True

    def readable(self):
        return True

    def tell(self):
        return self.pos

    def seek(self, off, whence=0):
        self.pos = off if whence == 0 else self.pos + off if whence == 1 else self.size + off
        return self.pos

    _buf_start, _buf = -1, b""
    min_fetch = 262144

    def read(self, n=-1):
        if n < 0:
            n = self.size - self.pos
        n = min(n, self.size - self.pos)
        if n <= 0:
            return b""
        b0, buf = self._buf_start, self._buf
        if not (b0 >= 0 and b0 <= self.pos and self.pos + n <= b0 + len(buf)):
            want = max(n, self.min_fetch)
            end = min(self.size - 1, self.pos + want - 1)
            req = urllib.request.Request(self.url, headers={"Range": f"bytes={self.pos}-{end}"})
            buf = urllib.request.urlopen(req, timeout=60).read()
            self._buf_start, self._buf, b0 = self.pos, buf, self.pos
        data = buf[self.pos - b0:self.pos - b0 + n]
        self.pos += len(data)
        return data

    def readinto(self, b):
        d = self.read(len(b))
        b[:len(d)] = d
        return len(d)


dst = DATA / "fashionpedia_train" / "images"
dst.mkdir(parents=True, exist_ok=True)
zf = zipfile.ZipFile(RangeFile(URL))
infos = {Path(i.filename).name: i for i in zf.infolist() if not i.is_dir()}
print("zip members", len(infos))
todo = [f for f in sel["files"].values() if not (dst / f).exists()]
print("to fetch", len(todo))
tot = sum(infos[f].compress_size for f in todo if f in infos)
print("approx MB", tot / 1e6)


import threading
_tl = threading.local()


def fetch(fn):
    info = infos[fn]
    try:
        if not hasattr(_tl, "rf"):
            _tl.rf = RangeFile(URL)
            _tl.rf.min_fetch = 1
        _tl.rf.seek(info.header_offset)
        # read the local header and the data using the shared central-directory info
        z = _tl.z if hasattr(_tl, "z") else None
        _tl.rf.min_fetch = info.compress_size + 400
        hdr = _tl.rf.read(30)
        nlen = int.from_bytes(hdr[26:28], "little")
        elen = int.from_bytes(hdr[28:30], "little")
        _tl.rf.read(nlen + elen)
        raw = _tl.rf.read(info.compress_size)
        import zlib
        data = raw if info.compress_type == 0 else zlib.decompress(raw, -15)
        (dst / fn).write_bytes(data)
        return 1
    except Exception as e:  # noqa: BLE001
        return str(e)


with ThreadPoolExecutor(16) as ex:
    res = list(ex.map(fetch, [f for f in todo if f in infos]))
print("ok", sum(r == 1 for r in res), "failed", [r for r in res if r != 1][:5])
