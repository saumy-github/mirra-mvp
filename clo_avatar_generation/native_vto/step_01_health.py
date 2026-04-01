"""Step 1: CLO health check."""


def run(ctx):
    print("\n[1] Health check ...")
    result = ctx.client.health_check()
    if result.get("status") == "ok":
        print("[OK] Connected to CLO REST server")
        print(f"  Plugin: {result.get('plugin')}")
        print(f"  Version: {result.get('version')}")
        return True

    print("[FAIL] Failed to connect to CLO REST server")
    print("  Make sure CLO is running with RestPlugin loaded")
    print(f"  Error: {result.get('error', 'Unknown error')}")
    return False
