"""Step 9: Create seams using seam map."""

from .helpers import print_result


def run(ctx):
    print("\n[9] Creating seams ...")
    if not ctx.seams:
        print("  No seam map provided. Skipping seam creation.")
        return True
    if ctx.using_default_seams:
        print("  NOTE: Using placeholder edge indices.")
        print("  Run plugins/discover_seam_indices.py to get real indices.")

    for seam in ctx.seams:
        print_result(
            ctx.client.create_seam(
                seam["a"],
                seam["la"],
                seam["b"],
                seam["lb"],
                seam.get("da", True),
                seam.get("db", True),
            ),
            seam["name"],
        )

    ctx.client.wait_for_queue(timeout=60)
    return True
