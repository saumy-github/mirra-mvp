"""Step 8: Assign fabric to each pattern piece."""

from .helpers import print_result


def run(ctx):
    print("\n[8] Applying fabric (index 0, first fabric in CLO project) ...")
    for idx in range(ctx.loaded_patterns):
        print_result(ctx.client.set_fabric(idx, fabric_index=0), f"fabric pattern {idx}")

    ctx.client.wait_for_queue(timeout=15)
    return True
