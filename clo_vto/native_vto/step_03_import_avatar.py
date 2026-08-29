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

    # ImportAvatar always ADDs — the SDK exposes no replace flag — so a scene
    # that was not fully cleared by step 2 ends up with two avatars and the
    # simulation drapes onto the wrong body. Fail loudly rather than deleting:
    # DeleteAvatar hangs CLO and GetAvatarProperties crashes it on a bad index
    # (clo_workspace/versions/v_1.3.2.json). The second avatar must never exist.
    count = ctx.client.get_avatar_count()
    if count == -1:
        print("  [WARN] Could not read avatar count — proceeding without the clean-scene check.")
    elif count != 1:
        print(f"  ! Expected exactly 1 avatar in the scene, found {count}.")
        print("    Restart CLO before retrying; do not delete avatars via the API.")
        ctx.avatar_loaded = False
        return False
    else:
        print("  [OK] Scene holds exactly 1 avatar.")

    try:
        native_debug = ctx.client.get_native_avatar_debug()
        if isinstance(native_debug, dict) and native_debug.get("success"):
            ctx.avatar_debug = native_debug
    except Exception:
        pass

    ctx.avatar_loaded = True
    return True
