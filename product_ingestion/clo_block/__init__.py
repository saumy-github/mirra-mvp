"""CLO-compatible parametric t-shirt block."""
from .clo_draft import CloTShirtDraft, CapSolveError, Notch, InternalLine
from .clo_draft_config import CloBlockMeasurements, CloDraftConfig, relaxed_tee, woven_tee
from .clo_dxf_writer import build_piece_dxf, write_pattern_set, write_svg

__all__ = [
    "CloTShirtDraft", "CapSolveError", "Notch", "InternalLine",
    "CloBlockMeasurements", "CloDraftConfig", "relaxed_tee", "woven_tee",
    "build_piece_dxf", "write_pattern_set", "write_svg",
]
