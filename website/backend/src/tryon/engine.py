"""The cloth-physics hand-off seam (TRYON_ENGINE_MODE=demo|live).

demo: no cloth physics — a staged, clearly-labelled simulation so the
frontend can integrate before the CLO3D worker exists.

live: will hand the render to the CLO3D VTO pipeline via the worker queue
(same pending decision as avatars). Refuses cleanly until then.
"""

from datetime import datetime, timezone

from ..config import get_settings
from ..core.errors import ServiceUnavailable
from .models import DEMO_RENDERING_SECONDS, DEMO_REQUESTED_SECONDS


def engine_mode() -> str:
    return get_settings().tryon_engine_mode


def start_render(render: dict) -> None:
    if engine_mode() == "live":
        raise ServiceUnavailable(
            "Live try-on engine is not wired yet (CLO3D worker queue pending)",
            code="engine_unavailable",
        )


def derive_demo_state(render: dict) -> str:
    elapsed = (datetime.now(timezone.utc) - render["created_at"]).total_seconds()
    if elapsed < DEMO_REQUESTED_SECONDS:
        return "requested"
    if elapsed < DEMO_REQUESTED_SECONDS + DEMO_RENDERING_SECONDS:
        return "rendering"
    return "ready"
