"""Step 5: Verify pattern count after import."""


def run(ctx):
    print("\n[5] Verifying pattern count ...")
    status = ctx.client.get_status()
    ctx.loaded_patterns = status.get("patterns_loaded", 0)
    print(f"  Patterns in CLO scene: {ctx.loaded_patterns} (expected {len(ctx.pattern_files)})")
    if ctx.loaded_patterns == 0:
        print("  No patterns loaded - check file paths and DXF format. Aborting.")
        return False
    return True
