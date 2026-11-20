"""P07 step 1: build labelled crops + manifest.

  .venv/Scripts/python.exe product_ingestion/CV/scripts/p07_build_dataset.py --split val
  .venv/Scripts/python.exe product_ingestion/CV/scripts/p07_build_dataset.py --split train

val uses the 1,158 val images (data/fashionpedia/test/). train uses the image subset chosen by
p07_fetch_train_images.py (data/fashionpedia_train/images/, selection in out/p07_attributes/train_selection.json).
"""
import argparse
import collections
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pandas as pd
from p07_common import *  # noqa

ap = argparse.ArgumentParser()
ap.add_argument("--split", required=True, choices=["val", "train"])
a = ap.parse_args()

OUT.mkdir(parents=True, exist_ok=True)
if a.split == "val":
    jp = DATA / "fashionpedia" / "instances_attributes_val2020.json"
    img_dir = DATA / "fashionpedia" / "test"
    d = load_json(jp)
    images = {i["id"]: i for i in d["images"]}
    anns = d["annotations"]
else:
    jp = DATA / "fashionpedia_train" / "instances_attributes_train2020.json"
    img_dir = DATA / "fashionpedia_train" / "images"
    sel = set(json.load(open(OUT / "train_selection.json"))["image_ids"])
    _, _, anns, images = stream_coco(jp, keep_seg_images=sel, only_images=sel,
                                    only_cats=PATTERN_CATS | {SLEEVE_PART, NECK_PART})
    anns = [x for x in anns if x["image_id"] in sel]

by = collections.defaultdict(list)
for x in anns:
    by[x["image_id"]].append(x)
rows = build_crops(images, by, img_dir, a.split, OUT / "crops")
df = pd.DataFrame(rows)
df.to_csv(OUT / f"manifest_{a.split}.csv", index=False)
print(df.groupby(["group", "label"]).size())
print("multi-label garments:", df.groupby("group").multi.sum().to_dict())
