"""Step 3: Import native CLO avatar."""

from .helpers import print_result


def _check_avatar_in_results(status: dict) -> bool | None:
    """Return True/False if last_results contains an avatar import outcome, else None."""
    for r in status.get("last_results", []):
        if r.get("type") in ("import-avatar-avt", "import-avatar"):
            return bool(r.get("success", False))
    return None


def run(ctx):
    print("\n[3] Importing native CLO avatar ...")
    if not ctx.avatar_path.exists():
        print(f"  ! Native avatar not found: {ctx.avatar_path}")
        ctx.avatar_loaded = False
        return False

    ok = print_result(
        ctx.client.import_avatar_avt(str(ctx.avatar_path)),
        "import-avatar-avt",
    )
    if not ok:
        ctx.avatar_loaded = False
        return False

    try:
        ctx.client.wait_for_queue(timeout=30)
    except Exception as exc:
        print(f"  [WARN] Avatar import drain timed out: {exc} — proceeding.")

    # Verify CLO actually processed the avatar — the plugin only confirms queuing,
    # not CLO's internal success (e.g. Unzip error won't surface until here).
    status = ctx.client.get_status()
    clo_ok = _check_avatar_in_results(status)
    if clo_ok is False:
        msg = next(
            (r.get("message", "") for r in status.get("last_results", [])
             if r.get("type") in ("import-avatar-avt", "import-avatar")),
            "CLO reported avatar import failure",
        )
        print(f"  ! CLO avatar import failed: {msg}")
        print("  Tip: verify base-1.avt was exported from the same CLO version installed.")
        ctx.avatar_loaded = False
        return False

    csv_path = getattr(ctx, "native_measurement_csv", None)
    if csv_path:
        print(f"  Applying measurement CSV: {csv_path}")
        ok = print_result(
            ctx.client.import_avatar_measurements(
                str(csv_path),
                template_path=str(ctx.avatar_path),
            ),
            "import-avatar-measurements",
        )
        try:
            ctx.client.wait_for_queue(timeout=30)
        except Exception as exc:
            print(f"  [WARN] Measurement CSV drain timed out: {exc} — proceeding.")

    try:
        native_debug = ctx.client.get_native_avatar_debug()
        if isinstance(native_debug, dict) and native_debug.get("success"):
            ctx.avatar_debug = native_debug
    except Exception:
        pass

    ctx.avatar_loaded = True
    return True
