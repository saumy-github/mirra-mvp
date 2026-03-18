"""
CLO Python Discovery (No SDK Version)

Your trial doesn't have CLOAPISDK or CLOPython modules.
But CLO might still expose functions in the global namespace.

Run this in CLO Python Editor to see what's available.
"""

print("=" * 70)
print("CLO Python Discovery (No SDK Mode)")
print("=" * 70)

# Check globals for CLO-related objects
print("\n[1] Checking global namespace for CLO functions...")
print("-" * 70)

clo_related = []
for name in dir():
    if not name.startswith('_'):
        obj = eval(name)
        clo_related.append((name, type(obj).__name__))

if clo_related:
    print("Found global objects:")
    for name, type_name in clo_related:
        print(f"  {name}: {type_name}")
else:
    print("  No CLO objects found in global namespace")

# Check for common CLO function names directly
print("\n[2] Testing common CLO function names...")
print("-" * 70)

test_names = [
    "CLO", "API", "Project", "Pattern", "Avatar", "Garment", "Fabric",
    "Simulation", "Export", "Import", "NewProject", "GetProject",
    "ExportGLTF", "ExportOBJ", "ImportAvatar", "ImportPattern",
    "GetPatterns", "GetAvatars", "RunSimulation", "GetFabrics"
]

found_functions = []
for name in test_names:
    try:
        obj = eval(name)
        found_functions.append(name)
        print(f"  ✓ Found: {name} ({type(obj).__name__})")
    except NameError:
        pass

if not found_functions:
    print("  ✗ None of the common CLO functions found")

# Check builtins for CLO additions
print("\n[3] Checking __builtins__ for CLO additions...")
print("-" * 70)

import builtins
builtin_names = dir(builtins)
clo_builtins = [name for name in builtin_names if 'clo' in name.lower() or 'api' in name.lower()]

if clo_builtins:
    print("Found CLO-related builtins:")
    for name in clo_builtins:
        print(f"  {name}")
else:
    print("  No CLO-related items in builtins")

# Try importing with different names
print("\n[4] Trying alternative module names...")
print("-" * 70)

module_attempts = [
    "CLO", "clo", "Clo", 
    "CLOAPISDK", "CLOApiSDK", "clo_api_sdk",
    "CLOPython", "cloPython", "clo_python",
    "CLO3D", "clo3d", "Clo3D",
    "API", "api", "Api",
    "clostudio", "CLOStudio", "clo_studio"
]

found_modules = []
for module_name in module_attempts:
    try:
        mod = __import__(module_name)
        found_modules.append(module_name)
        print(f"  ✓ Successfully imported: {module_name}")
        print(f"    Contents: {dir(mod)[:10]}...")  # First 10 items
    except ImportError:
        pass

if not found_modules:
    print("  ✗ No CLO modules found with common names")

# Check sys.path for CLO directories
print("\n[5] Checking Python path for CLO directories...")
print("-" * 70)

import sys
clo_paths = [p for p in sys.path if 'clo' in p.lower()]

if clo_paths:
    print("Found CLO-related paths:")
    for path in clo_paths:
        print(f"  {path}")
else:
    print("  No CLO directories in Python path")
    print("\n  Full sys.path:")
    for path in sys.path:
        print(f"    {path}")

# Final verdict
print("\n" + "=" * 70)
print("VERDICT")
print("=" * 70)

if found_modules or found_functions:
    print("\n✓ Some CLO Python functionality detected!")
    print("  Available modules:", ", ".join(found_modules) if found_modules else "None")
    print("  Available functions:", ", ".join(found_functions) if found_functions else "None")
    print("\n  → Try calling these functions to test automation")
else:
    print("\n✗ NO CLO Python API detected in this trial version")
    print("\n  This means your CLO trial has one of these limitations:")
    print("  1. Python scripting is not enabled/available")
    print("  2. SDK package not included with trial")
    print("  3. Need to activate/enable Python API in settings")
    print("  4. Trial is Standalone (which has limited/no SDK)")
    
    print("\n  RECOMMENDED ACTIONS:")
    print("  → Check CLO version: Help → About CLO3D")
    print("  → Check for Python settings: Edit → Preferences → API/Python")
    print("  → Contact CLO support: 'Does trial include Python SDK?'")
    print("  → Request CLO 2024/2025 trial (not Standalone)")
    print("  → Consider Marvelous Designer as alternative")

print("\n" + "=" * 70)
print("\nNext: Copy this output and share with developer")
print("=" * 70)
