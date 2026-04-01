"""Step 3: Import native CLO avatar."""

from .helpers import print_result


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
    ctx.client.wait_for_queue(timeout=30)

    csv_path = getattr(ctx, "native_measurement_csv", None)
    if ok and csv_path:
        print(f"  Applying measurement CSV: {csv_path}")
        ok = print_result(
            ctx.client.import_avatar_measurements(
                str(csv_path),
                template_path=str(ctx.avatar_path),
            ),
            "import-avatar-measurements",
        ) and ok
        ctx.client.wait_for_queue(timeout=30)

    try:
        native_debug = ctx.client.get_native_avatar_debug()
        if isinstance(native_debug, dict) and native_debug.get("success"):
            ctx.avatar_debug = native_debug
    except Exception:
        pass

    ctx.avatar_loaded = ok
    return ok
