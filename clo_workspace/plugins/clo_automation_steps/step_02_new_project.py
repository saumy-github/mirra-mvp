"""Step 2: Create a new CLO project."""

from .helpers import print_result


def run(ctx):
    print("\n[2] New project ...")
    print_result(ctx.client.new_project(), "new-project")
    ctx.client.wait_for_queue(timeout=15)
    return True
