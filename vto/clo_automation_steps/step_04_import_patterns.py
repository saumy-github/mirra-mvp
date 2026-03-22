"""Step 4: Import DXF pattern pieces."""

from .helpers import print_result


def run(ctx):
    print("\n[4] Importing patterns ...")
    for fname in ctx.pattern_files:
        path = ctx.patterns_dir / fname
        if not path.exists():
            print(f"  ! Pattern not found: {path}")
            continue
        print_result(ctx.client.import_pattern(str(path)), fname)

    print("     Waiting for CLO to finish imports ...")
    ctx.client.wait_for_queue(timeout=60)
    return True
