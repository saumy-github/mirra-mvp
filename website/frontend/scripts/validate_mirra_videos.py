#!/usr/bin/env python3
"""Validate the complete, production Mirra website-video delivery.

The validator is deliberately independent of the React content manifest. This
keeps a missing or mistyped asset from being hidden by the same mistake in both
the UI code and the validation code.
"""

from __future__ import annotations

import argparse
import hashlib
import struct
import sys
from dataclasses import dataclass, field
from pathlib import Path

try:
    import cv2
except ImportError as exc:  # pragma: no cover - environment-dependent failure
    print(f"ERROR: OpenCV is required (import cv2 failed: {exc})", file=sys.stderr)
    raise SystemExit(2) from exc


@dataclass(frozen=True)
class VideoSpec:
    stem: str
    width: int
    height: int
    duration: float


@dataclass
class ValidationResult:
    spec: VideoSpec
    path: Path
    width: int = 0
    height: int = 0
    fps: float = 0.0
    frames: int = 0
    duration: float = 0.0
    codec: str = "----"
    sha256: str = ""
    poster_mae: float | None = None
    faststart: bool = False
    errors: list[str] = field(default_factory=list)


SPECS: tuple[VideoSpec, ...] = (
    VideoSpec("s01-hero-garment-rail", 1280, 720, 6.0),
    VideoSpec("s02-hero-structured-jacket", 1280, 720, 6.0),
    VideoSpec("s03-hero-satin-drape", 1280, 720, 6.0),
    VideoSpec("s04-hero-product-page-entry", 1280, 720, 6.0),
    VideoSpec("s05-hero-fluid-garment", 1280, 720, 6.0),
    VideoSpec("s06-hero-knit-drape", 1280, 720, 6.0),
    VideoSpec("s07-hero-avatar-view", 1280, 720, 6.0),
    VideoSpec("s08-hero-outerwear", 1280, 720, 6.0),
    VideoSpec("s09-hero-size-choice", 1280, 720, 6.0),
    VideoSpec("s10-hero-body-representation", 1280, 720, 6.0),
    VideoSpec("s11-hero-seam-to-interface", 1280, 720, 6.0),
    VideoSpec("s12-hero-browser-continuity", 1280, 720, 6.0),
    VideoSpec("s13-hero-confident-parcel", 1280, 720, 6.0),
    VideoSpec("s14-outcome-fit-decision", 1600, 900, 8.0),
    VideoSpec("s15-outcome-one-size", 1600, 900, 8.0),
    VideoSpec("s16-outcome-retained-margin", 1600, 900, 8.0),
    VideoSpec("s17-feature-one-button", 1200, 1000, 6.0),
    VideoSpec("s18-feature-existing-catalogue", 1200, 1000, 7.0),
    VideoSpec("s19-feature-realistic-drape", 1200, 1000, 9.0),
    VideoSpec("s20-feature-in-browser", 1200, 1000, 8.0),
    VideoSpec("s21-feature-brand-owned", 1200, 1000, 7.0),
    VideoSpec("s22-feature-seven-day-launch", 1200, 1000, 8.0),
    VideoSpec("s23-proof-structured-jacket", 1280, 720, 6.0),
    VideoSpec("s24-proof-fluid-dress", 1280, 720, 6.0),
    VideoSpec("s25-proof-knit-top", 1280, 720, 6.0),
    VideoSpec("s26-proof-trouser-fit", 1280, 720, 6.0),
    VideoSpec("s27-proof-outerwear-layering", 1280, 720, 6.0),
)

H264_FOURCCS = {"avc1", "avc3", "h264", "x264"}
EXPECTED_FPS = 24.0
FPS_TOLERANCE = 0.15
DURATION_TOLERANCE = 0.15
POSTER_MAE_THRESHOLD = 18.0


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def decode_fourcc(value: float) -> str:
    packed = int(value)
    return "".join(chr((packed >> (8 * index)) & 0xFF) for index in range(4)).rstrip("\x00")


def top_level_atoms(path: Path) -> list[tuple[bytes, int, int]]:
    """Return (atom_type, offset, size) for validated top-level MP4 atoms."""
    atoms: list[tuple[bytes, int, int]] = []
    file_size = path.stat().st_size
    offset = 0

    with path.open("rb") as handle:
        while offset < file_size:
            if file_size - offset < 8:
                raise ValueError(f"trailing {file_size - offset} byte(s) after final MP4 atom")

            handle.seek(offset)
            header = handle.read(8)
            atom_size_32, atom_type = struct.unpack(">I4s", header)
            header_size = 8

            if atom_size_32 == 1:
                extended = handle.read(8)
                if len(extended) != 8:
                    raise ValueError("truncated extended-size MP4 atom")
                atom_size = struct.unpack(">Q", extended)[0]
                header_size = 16
            elif atom_size_32 == 0:
                atom_size = file_size - offset
            else:
                atom_size = atom_size_32

            if atom_size < header_size:
                name = atom_type.decode("ascii", "replace")
                raise ValueError(f"invalid {name} atom size {atom_size}")
            if offset + atom_size > file_size:
                name = atom_type.decode("ascii", "replace")
                raise ValueError(f"{name} atom extends beyond end of file")

            atoms.append((atom_type, offset, atom_size))
            offset += atom_size

    return atoms


def check_faststart(path: Path) -> tuple[bool, str | None]:
    try:
        atoms = top_level_atoms(path)
    except (OSError, ValueError, struct.error) as exc:
        return False, f"invalid MP4 atoms: {exc}"

    moov_offsets = [offset for atom, offset, _ in atoms if atom == b"moov"]
    mdat_offsets = [offset for atom, offset, _ in atoms if atom == b"mdat"]
    if not moov_offsets:
        return False, "missing moov atom"
    if not mdat_offsets:
        return False, "missing mdat atom"
    if min(moov_offsets) >= min(mdat_offsets):
        return False, "moov atom is not before mdat"
    return True, None


def validate_video(
    spec: VideoSpec,
    video_dir: Path,
    poster_dir: Path,
    poster_mae_threshold: float,
) -> ValidationResult:
    path = video_dir / f"{spec.stem}.mp4"
    result = ValidationResult(spec=spec, path=path)
    if not path.is_file():
        result.errors.append("missing MP4")
        return result

    try:
        result.sha256 = sha256_file(path)
    except OSError as exc:
        result.errors.append(f"cannot hash: {exc}")

    result.faststart, atom_error = check_faststart(path)
    if atom_error:
        result.errors.append(atom_error)

    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        result.errors.append("OpenCV cannot open MP4")
        capture.release()
        return result

    result.width = int(round(capture.get(cv2.CAP_PROP_FRAME_WIDTH)))
    result.height = int(round(capture.get(cv2.CAP_PROP_FRAME_HEIGHT)))
    result.fps = float(capture.get(cv2.CAP_PROP_FPS))
    result.frames = int(round(capture.get(cv2.CAP_PROP_FRAME_COUNT)))
    result.codec = decode_fourcc(capture.get(cv2.CAP_PROP_FOURCC)) or "----"
    result.duration = result.frames / result.fps if result.fps > 0 else 0.0

    first_ok, first_frame = capture.read()
    if not first_ok or first_frame is None:
        result.errors.append("first frame is unreadable")

    if result.frames > 1:
        capture.set(cv2.CAP_PROP_POS_FRAMES, result.frames - 1)
        last_ok, last_frame = capture.read()
        if not last_ok or last_frame is None:
            result.errors.append("last frame is unreadable")
    capture.release()

    if (result.width, result.height) != (spec.width, spec.height):
        result.errors.append(
            f"dimensions {result.width}x{result.height}, expected {spec.width}x{spec.height}"
        )
    if result.frames <= 0:
        result.errors.append("invalid frame count")
    if abs(result.fps - EXPECTED_FPS) > FPS_TOLERANCE:
        result.errors.append(f"FPS {result.fps:.3f}, expected {EXPECTED_FPS:.0f}")
    if abs(result.duration - spec.duration) > DURATION_TOLERANCE:
        result.errors.append(f"duration {result.duration:.3f}s, expected {spec.duration:.1f}s")
    if result.codec.lower() not in H264_FOURCCS:
        result.errors.append(f"codec FourCC {result.codec!r} is not H.264")

    poster_path = poster_dir / f"{spec.stem}.webp"
    if not poster_path.is_file():
        result.errors.append("missing matching WebP poster")
    else:
        poster = cv2.imread(str(poster_path), cv2.IMREAD_COLOR)
        if poster is None:
            result.errors.append("poster is unreadable")
        elif poster.shape[1] != result.width or poster.shape[0] != result.height:
            result.errors.append(
                f"poster dimensions {poster.shape[1]}x{poster.shape[0]} do not match video"
            )
        elif first_ok and first_frame is not None:
            result.poster_mae = float(cv2.absdiff(first_frame, poster).mean())
            if result.poster_mae > poster_mae_threshold:
                result.errors.append(
                    f"poster does not match first frame (MAE {result.poster_mae:.1f})"
                )

    return result


def print_results(results: list[ValidationResult]) -> None:
    print(
        "ID  FILE                                      SIZE       FPS  FRAMES   SEC  "
        "CODEC  POSTER  FAST  UNIQUE  STATUS"
    )
    for index, result in enumerate(results, start=1):
        poster = "--" if result.poster_mae is None else f"{result.poster_mae:5.1f}"
        unique = "no" if any(error.startswith("duplicate SHA256") for error in result.errors) else "yes"
        status = "PASS" if not result.errors else "FAIL"
        print(
            f"{index:02d}  {result.path.name:<40} "
            f"{result.width:4d}x{result.height:<4d} "
            f"{result.fps:5.2f} {result.frames:7d} {result.duration:5.2f} "
            f"{result.codec:<6} {poster:>6}  "
            f"{'yes' if result.faststart else 'no':<4}  {unique:<6}  {status}"
        )
        for error in result.errors:
            print(f"    - {error}")


def parse_args() -> argparse.Namespace:
    frontend_root = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--video-dir",
        type=Path,
        default=frontend_root / "public" / "mirra" / "video",
        help="directory containing the 27 MP4 files",
    )
    parser.add_argument(
        "--poster-dir",
        type=Path,
        default=frontend_root / "public" / "mirra" / "posters",
        help="directory containing same-stem WebP posters",
    )
    parser.add_argument(
        "--poster-mae-threshold",
        type=float,
        default=POSTER_MAE_THRESHOLD,
        help="maximum mean absolute pixel error between poster and first frame",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    results = [
        validate_video(spec, args.video_dir, args.poster_dir, args.poster_mae_threshold)
        for spec in SPECS
    ]

    digest_groups: dict[str, list[ValidationResult]] = {}
    for result in results:
        if result.sha256:
            digest_groups.setdefault(result.sha256, []).append(result)
    for matches in digest_groups.values():
        if len(matches) > 1:
            names = ", ".join(match.path.name for match in matches)
            for match in matches:
                match.errors.append(f"duplicate SHA256 group: {names}")

    expected_names = {f"{spec.stem}.mp4" for spec in SPECS}
    actual_names = {path.name for path in args.video_dir.glob("*.mp4")} if args.video_dir.is_dir() else set()
    unexpected = sorted(actual_names - expected_names)

    print_results(results)
    if unexpected:
        print("Unexpected MP4 files: " + ", ".join(unexpected))

    failed = sum(bool(result.errors) for result in results)
    passed = len(results) - failed
    print(f"\nSummary: {passed}/{len(results)} passed; {failed} failed; {len(unexpected)} unexpected.")
    return 1 if failed or unexpected else 0


if __name__ == "__main__":
    raise SystemExit(main())
