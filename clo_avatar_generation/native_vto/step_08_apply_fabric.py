"""Step 8: Assign fabric to each pattern piece."""

from .helpers import print_result


def run(ctx):
    print("\n[8] Applying fabric (index 0, first fabric in CLO project) ...")
    if ctx.piece_to_index:
        indices = [ctx.piece_to_index[p] for p in ["front_panel", "back_panel", "sleeve_left", "sleeve_right"] if p in ctx.piece_to_index]
    else:
        indices = list(range(ctx.loaded_patterns))

    for idx in indices:
        print_result(ctx.client.set_fabric(idx, fabric_index=0), f"fabric pattern {idx}")

    ctx.client.wait_for_queue(timeout=15)
    return True
