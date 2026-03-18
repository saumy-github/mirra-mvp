"""
CLO3D Python API Discovery Script

PURPOSE:
Run this script inside CLO3D to discover what Python API functions are available.

USAGE:
1. Open CLO3D
2. Main Menu → Edit → Python Script
3. Paste this entire script into the editor
4. Click "Run" or press F5
5. Check the Log Console for output

This will help us understand what automation is possible during the trial period.
"""

def discover_clo_api():
    """Discover and test available CLO API functions."""
    
    print("=" * 70)
    print("CLO3D Python API Discovery")
    print("=" * 70)
    
    # Try to import CLO module
    try:
        import CLO
        print("\n✓ CLO module imported successfully")
    except ImportError as e:
        print(f"\n✗ Could not import CLO module: {e}")
        print("  This script must be run inside CLO3D Python Editor")
        return
    
    # List all available attributes
    print("\n" + "-" * 70)
    print("Available CLO API Functions:")
    print("-" * 70)
    
    clo_functions = []
    for attr in dir(CLO):
        if not attr.startswith("_"):
            clo_functions.append(attr)
    
    if clo_functions:
        for i, func in enumerate(clo_functions, 1):
            print(f"{i:3d}. CLO.{func}")
    else:
        print("  No public functions found")
    
    print(f"\nTotal: {len(clo_functions)} functions")
    
    # Test common operations
    print("\n" + "-" * 70)
    print("Testing Common Operations:")
    print("-" * 70)
    
    # Test 1: Get version
    print("\n[1] Getting CLO version...")
    try:
        if hasattr(CLO, "GetVersion"):
            version = CLO.GetVersion()
            print(f"    ✓ Version: {version}")
        elif hasattr(CLO, "Version"):
            version = CLO.Version()
            print(f"    ✓ Version: {version}")
        else:
            print("    ⚠ Version function not found")
    except Exception as e:
        print(f"    ✗ Error: {e}")
    
    # Test 2: Get project info
    print("\n[2] Getting project info...")
    try:
        if hasattr(CLO, "GetProjectName"):
            name = CLO.GetProjectName()
            print(f"    ✓ Project name: {name}")
        elif hasattr(CLO, "ProjectName"):
            name = CLO.ProjectName()
            print(f"    ✓ Project name: {name}")
        else:
            print("    ⚠ Project name function not found")
    except Exception as e:
        print(f"    ✗ Error: {e}")
    
    # Test 3: List patterns
    print("\n[3] Listing pattern pieces...")
    try:
        if hasattr(CLO, "GetPatternPieces"):
            patterns = CLO.GetPatternPieces()
            print(f"    ✓ Found {len(patterns)} pattern pieces")
            for p in patterns:
                print(f"      - {p}")
        elif hasattr(CLO, "GetPatterns"):
            patterns = CLO.GetPatterns()
            print(f"    ✓ Found {len(patterns)} patterns")
        else:
            print("    ⚠ Pattern listing function not found")
    except Exception as e:
        print(f"    ✗ Error: {e}")
    
    # Test 4: Get avatars
    print("\n[4] Checking avatar...")
    try:
        if hasattr(CLO, "GetAvatars"):
            avatars = CLO.GetAvatars()
            print(f"    ✓ Found {len(avatars)} avatars")
        elif hasattr(CLO, "GetAvatar"):
            avatar = CLO.GetAvatar()
            print(f"    ✓ Avatar: {avatar}")
        else:
            print("    ⚠ Avatar function not found")
    except Exception as e:
        print(f"    ✗ Error: {e}")
    
    # Test 5: Get fabrics
    print("\n[5] Listing fabric presets...")
    try:
        if hasattr(CLO, "GetFabricPresets"):
            fabrics = CLO.GetFabricPresets()
            print(f"    ✓ Found {len(fabrics)} fabric presets")
            if fabrics and len(fabrics) > 0:
                print(f"      Examples: {', '.join(str(f) for f in fabrics[:5])}")
        elif hasattr(CLO, "GetFabrics"):
            fabrics = CLO.GetFabrics()
            print(f"    ✓ Found {len(fabrics)} fabrics")
        else:
            print("    ⚠ Fabric listing function not found")
    except Exception as e:
        print(f"    ✗ Error: {e}")
    
    # Test 6: Check import functions
    print("\n[6] Checking import functions...")
    import_funcs = []
    for func in clo_functions:
        if "import" in func.lower() or "load" in func.lower():
            import_funcs.append(func)
    
    if import_funcs:
        print(f"    ✓ Found {len(import_funcs)} import functions:")
        for func in import_funcs:
            print(f"      - CLO.{func}")
    else:
        print("    ⚠ No import functions found")
    
    # Test 7: Check export functions
    print("\n[7] Checking export functions...")
    export_funcs = []
    for func in clo_functions:
        if "export" in func.lower() or "save" in func.lower():
            export_funcs.append(func)
    
    if export_funcs:
        print(f"    ✓ Found {len(export_funcs)} export functions:")
        for func in export_funcs:
            print(f"      - CLO.{func}")
    else:
        print("    ⚠ No export functions found")
    
    # Test 8: Check simulation functions
    print("\n[8] Checking simulation functions...")
    sim_funcs = []
    for func in clo_functions:
        if "sim" in func.lower() or "play" in func.lower():
            sim_funcs.append(func)
    
    if sim_funcs:
        print(f"    ✓ Found {len(sim_funcs)} simulation functions:")
        for func in sim_funcs:
            print(f"      - CLO.{func}")
    else:
        print("    ⚠ No simulation functions found")
    
    # Test 9: Check seam functions
    print("\n[9] Checking seam functions...")
    seam_funcs = []
    for func in clo_functions:
        if "seam" in func.lower() or "sew" in func.lower():
            seam_funcs.append(func)
    
    if seam_funcs:
        print(f"    ✓ Found {len(seam_funcs)} seam functions:")
        for func in seam_funcs:
            print(f"      - CLO.{func}")
    else:
        print("    ⚠ No seam functions found")
    
    print("\n" + "=" * 70)
    print("Discovery Complete!")
    print("=" * 70)
    print("\nNext Steps:")
    print("1. Review the function list above")
    print("2. Check CLO Help → API Documentation for function details")
    print("3. Test specific functions you need for automation")
    print("4. Update mirra_pattern_importer.py with correct function names")
    print("\nNote: If very few functions are listed, your CLO version may have")
    print("      limited Python API. Consider checking CLO documentation or")
    print("      testing with simple manual imports first.")


def test_file_import():
    """Test importing a file to see function signature."""
    print("\n" + "=" * 70)
    print("File Import Test")
    print("=" * 70)
    print("\nTrying to import a test file...")
    print("(This will fail if file doesn't exist, but shows us the function)")
    
    try:
        import CLO
        test_path = r"C:\Users\Anant\mirra-mvp\2d_patterned_garment_generation_clo3d\output_test\patterns_dxf\front_panel.dxf"
        
        # Try common import function names
        functions_to_try = [
            "ImportPattern",
            "ImportDXF", 
            "ImportFile",
            "LoadPattern",
            "AddPattern",
            "Import"
        ]
        
        for func_name in functions_to_try:
            if hasattr(CLO, func_name):
                print(f"\n  Found: CLO.{func_name}")
                try:
                    func = getattr(CLO, func_name)
                    # Try to get function signature
                    import inspect
                    sig = inspect.signature(func)
                    print(f"  Signature: {func_name}{sig}")
                except:
                    print(f"  (Could not get signature)")
        
        print("\n  Try calling them manually with your DXF file path")
        
    except Exception as e:
        print(f"  Error: {e}")


def print_helpful_tips():
    """Print helpful tips for CLO Python API usage."""
    print("\n" + "=" * 70)
    print("Helpful Tips for CLO Python API")
    print("=" * 70)
    
    tips = [
        "1. Check CLO's Help menu for 'Python API', 'Script Reference', or 'API Documentation'",
        "2. Look for example scripts in CLO installation folder (e.g., C:\\Program Files\\CLO\\examples\\)",
        "3. Try CLO's official website: https://support.clo3d.com → Search 'Python API'",
        "4. Check if your CLO version supports Python (some versions have limited API)",
        "5. Test manual operations first, then find corresponding API function",
        "6. Use CLO's Script Editor console to test functions interactively",
        "7. If API is very limited, you can still automate via recorded macros (if available)",
        "8. Contact CLO support to ask about Python API availability during trial"
    ]
    
    for tip in tips:
        print(f"  {tip}")
    
    print("\n" + "=" * 70)


# =============================================================================
# RUN DISCOVERY
# =============================================================================

if __name__ == "__main__":
    discover_clo_api()
    test_file_import()
    print_helpful_tips()
    
    print("\n\n>>> SAVE THIS OUTPUT <<<")
    print("Copy everything from the Log Console and save it to a file.")
    print("This information is critical for developing the automation plugin.")
