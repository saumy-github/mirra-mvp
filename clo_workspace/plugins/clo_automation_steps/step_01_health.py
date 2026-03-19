"""Step 1: CLO health check."""


def run(ctx):
    print("\n[1] Health check ...")
    result = ctx.client.health_check()
    if result.get("status") == "ok":
        print("\u2713 Connected to CLO REST server")
        print(f"  Plugin: {result.get('plugin')}")
        print(f"  Version: {result.get('version')}")
        
        # Get detailed version info
        version_info = ctx.client.get_version()
        if version_info.get("build_date"):
            print(f"  Build: {version_info.get('build_date')} {version_info.get('build_time')}")
        
        return True

    print("\u2717 Failed to connect to CLO REST server")
    print("  Make sure CLO is running with RestPlugin loaded")
    print(f"  Error: {result.get('error', 'Unknown error')}")
    return False
