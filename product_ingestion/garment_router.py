"""
Garment Router — CLIP-Based View Selection & Classification

Uses CLIP ViT-B/32 zero-shot classification to determine which images
in a set of 1–10 garment photos represent front, back, or side views,
and discards irrelevant images.

Part of the T-Shirt Appearance Extraction Pipeline for CLO3D.
"""

import os
import sys
import json
import shutil
import argparse
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import List, Tuple, Dict, Optional

import numpy as np
from PIL import Image

try:
    import torch
    from transformers import CLIPProcessor, CLIPModel
    HAS_CLIP = True
except ImportError:
    HAS_CLIP = False
    print("Warning: torch / transformers not installed. CLIP routing disabled.")


# ─────────────────────────────────────────────────────────────
#  Data classes
# ─────────────────────────────────────────────────────────────

@dataclass
class ViewScore:
    """Scores for a single image across all view labels."""
    filename: str
    filepath: str
    front: float = 0.0
    back: float = 0.0
    side: float = 0.0
    irrelevant: float = 0.0
    assigned_view: str = "irrelevant"
    confidence: float = 0.0


@dataclass
class RoutingResult:
    """Result from the garment router."""
    front_images: List[str] = field(default_factory=list)
    back_images: List[str] = field(default_factory=list)
    side_images: List[str] = field(default_factory=list)
    discarded: List[str] = field(default_factory=list)
    all_scores: List[ViewScore] = field(default_factory=list)
    best_front: Optional[str] = None
    best_back: Optional[str] = None


# ─────────────────────────────────────────────────────────────
#  Garment Router
# ─────────────────────────────────────────────────────────────

class GarmentRouter:
    """
    Classifies garment photos into front / back / side / irrelevant
    using CLIP ViT-B/32 zero-shot classification.
    """

    SUPPORTED_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tiff"}

    VIEW_PROMPTS = {
        "front": "a photo of the front of a t-shirt",
        "back": "a photo of the back of a t-shirt",
        "side": "a photo of the side of a t-shirt",
        "irrelevant": "a photo that is not of a t-shirt garment",
    }

    IRRELEVANT_THRESHOLD = 0.35   # discard if irrelevant score > this
    CONFIDENCE_FLOOR     = 0.30   # minimum score to accept a view

    def __init__(self, model_name: str = "openai/clip-vit-base-patch32"):
        self.model_name = model_name
        self._model = None
        self._processor = None

    # ── Lazy model loading ───────────────────────────────────
    def _load_model(self):
        if self._model is not None:
            return
        if not HAS_CLIP:
            raise RuntimeError(
                "CLIP dependencies not installed.\n"
                "Run: pip install torch torchvision transformers"
            )
        print(f"  Loading CLIP model: {self.model_name} …")
        self._model = CLIPModel.from_pretrained(self.model_name)
        self._processor = CLIPProcessor.from_pretrained(self.model_name)
        self._model.eval()
        print("  ✓ Model loaded")

    # ── Core classification ──────────────────────────────────
    def classify_image(self, image_path: str) -> ViewScore:
        """Classify a single image into a view category."""
        self._load_model()

        image = Image.open(image_path).convert("RGB")
        labels = list(self.VIEW_PROMPTS.keys())
        prompts = list(self.VIEW_PROMPTS.values())

        inputs = self._processor(
            text=prompts,
            images=image,
            return_tensors="pt",
            padding=True,
        )
        with torch.no_grad():
            outputs = self._model(**inputs)
            logits = outputs.logits_per_image[0]
            probs = torch.softmax(logits, dim=-1).cpu().numpy()

        scores = {label: float(prob) for label, prob in zip(labels, probs)}

        # Decide best view
        best_label = max(scores, key=scores.get)
        confidence = scores[best_label]

        # Override to irrelevant if below confidence floor or irrelevant is dominant
        if scores["irrelevant"] > self.IRRELEVANT_THRESHOLD:
            best_label = "irrelevant"
            confidence = scores["irrelevant"]

        return ViewScore(
            filename=Path(image_path).name,
            filepath=str(image_path),
            front=scores["front"],
            back=scores["back"],
            side=scores["side"],
            irrelevant=scores["irrelevant"],
            assigned_view=best_label,
            confidence=confidence,
        )

    # ── Batch routing ────────────────────────────────────────
    def route_images(
        self,
        input_dir: str,
        output_dir: Optional[str] = None,
    ) -> RoutingResult:
        """
        Route 1–10 images from *input_dir* into view categories.

        Selection policy:
          • Keep the best-scoring image per view (front, back, side)
          • Discard images classified as irrelevant

        If *output_dir* is given, copies are made as:
            front_img.<ext>   back_img.<ext>   side_img.<ext>
        """
        input_path = Path(input_dir)
        if not input_path.is_dir():
            raise FileNotFoundError(f"Input directory not found: {input_dir}")

        # Collect valid image files
        image_files = sorted([
            f for f in input_path.iterdir()
            if f.is_file() and f.suffix.lower() in self.SUPPORTED_EXTS
        ])

        if not image_files:
            raise FileNotFoundError(f"No images found in {input_dir}")
        if len(image_files) > 10:
            print(f"  ⚠️  {len(image_files)} images found — using first 10")
            image_files = image_files[:10]

        print(f"\n🔍 GARMENT ROUTER")
        print(f"   Images: {len(image_files)} in {input_dir}")

        # Classify each image
        all_scores: List[ViewScore] = []
        for img in image_files:
            score = self.classify_image(str(img))
            all_scores.append(score)
            print(
                f"   {score.filename:30s}  "
                f"F={score.front:.3f}  B={score.back:.3f}  "
                f"S={score.side:.3f}  X={score.irrelevant:.3f}  "
                f"→ {score.assigned_view.upper()} ({score.confidence:.1%})"
            )

        # Group by assigned view
        result = RoutingResult(all_scores=all_scores)
        for score in all_scores:
            if score.assigned_view == "front":
                result.front_images.append(score.filepath)
            elif score.assigned_view == "back":
                result.back_images.append(score.filepath)
            elif score.assigned_view == "side":
                result.side_images.append(score.filepath)
            else:
                result.discarded.append(score.filepath)

        # Best per view: highest score in each category
        front_candidates = sorted(all_scores, key=lambda s: s.front, reverse=True)
        back_candidates = sorted(all_scores, key=lambda s: s.back, reverse=True)

        if front_candidates and front_candidates[0].front >= self.CONFIDENCE_FLOOR:
            result.best_front = front_candidates[0].filepath
        if back_candidates and back_candidates[0].back >= self.CONFIDENCE_FLOOR:
            result.best_back = back_candidates[0].filepath

        # Copy files to output directory
        if output_dir:
            out = Path(output_dir)
            out.mkdir(parents=True, exist_ok=True)

            if result.best_front:
                ext = Path(result.best_front).suffix
                dst = out / f"front_img{ext}"
                shutil.copy2(result.best_front, dst)
                result.best_front = str(dst)
                print(f"   ✓ front_img{ext}")

            if result.best_back:
                ext = Path(result.best_back).suffix
                dst = out / f"back_img{ext}"
                shutil.copy2(result.best_back, dst)
                result.best_back = str(dst)
                print(f"   ✓ back_img{ext}")

            for i, side_path in enumerate(result.side_images):
                ext = Path(side_path).suffix
                dst = out / f"side_img_{i+1}{ext}"
                shutil.copy2(side_path, dst)
                print(f"   ✓ side_img_{i+1}{ext}")

            # Save routing metadata
            meta = {
                "best_front": result.best_front,
                "best_back": result.best_back,
                "num_images": len(image_files),
                "discarded": len(result.discarded),
                "scores": [asdict(s) for s in all_scores],
            }
            with open(out / "routing_result.json", "w") as f:
                json.dump(meta, f, indent=2)

        print(f"\n   Summary: {len(result.front_images)} front, "
              f"{len(result.back_images)} back, "
              f"{len(result.side_images)} side, "
              f"{len(result.discarded)} discarded")

        return result


# ─────────────────────────────────────────────────────────────
#  CLI
# ─────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Route garment images into front/back/side using CLIP",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python garment_router.py input_images/ -o output/routed
  python garment_router.py photos/ -o output/routed --model openai/clip-vit-base-patch16
        """,
    )
    parser.add_argument("input_dir", help="Directory containing garment images (1–10)")
    parser.add_argument("-o", "--output", help="Output directory", default="output/routed")
    parser.add_argument(
        "--model", default="openai/clip-vit-base-patch32",
        help="HuggingFace CLIP model name (default: openai/clip-vit-base-patch32)",
    )

    args = parser.parse_args()

    router = GarmentRouter(model_name=args.model)
    result = router.route_images(args.input_dir, args.output)

    if result.best_front:
        print(f"\n🎯 Best front image: {result.best_front}")
    else:
        print("\n⚠️  No front view image detected")

    if result.best_back:
        print(f"🎯 Best back image:  {result.best_back}")
    else:
        print("⚠️  No back view image detected")


if __name__ == "__main__":
    main()
