"""
CLO3D API Configuration

Configuration settings for CLO3D integration.
"""
import os
from pathlib import Path

# CLO Installation Paths
CLO_INSTALL_DIR = Path("C:/Program Files/CLO Standalone OnlineAuth")
CLO_EXECUTABLE = CLO_INSTALL_DIR / "CLO_Standalone_OnlineAuth_x64.exe"
CLO_API_DIR = CLO_INSTALL_DIR / "ApiStubFiles"

# Project Paths
PROJECT_ROOT = Path(__file__).parent.parent
CLO_WORKSPACE = PROJECT_ROOT / "clo_workspace"
CLO_PROJECTS = CLO_WORKSPACE / "projects"
CLO_EXPORTS = CLO_WORKSPACE / "exports"
CLO_TEMP = CLO_WORKSPACE / "temp"

# Create directories if they don't exist
CLO_WORKSPACE.mkdir(parents=True, exist_ok=True)
CLO_PROJECTS.mkdir(exist_ok=True)
CLO_EXPORTS.mkdir(exist_ok=True)
CLO_TEMP.mkdir(exist_ok=True)

# API Configuration
CLO_API_HOST = "localhost"
CLO_API_PORT = 50505  # Default CLO API port
CLO_API_BASE_URL = f"http://{CLO_API_HOST}:{CLO_API_PORT}/api"

# Simulation Settings (defaults)
DEFAULT_SIMULATION_QUALITY = "high"  # low, medium, high, very_high
DEFAULT_SIMULATION_FRAMES = 120
DEFAULT_FABRIC_PRESET = "Cotton Medium"

# Export Settings
DEFAULT_EXPORT_FORMAT = "glb"
DEFAULT_TEXTURE_RESOLUTION = 2048
DEFAULT_INCLUDE_AVATAR = True

# Units
UNIT_SYSTEM = "metric"  # metric or imperial
LENGTH_UNIT = "cm"  # cm or inch
WEIGHT_UNIT = "kg"  # kg or lb

# Logging
LOG_LEVEL = "INFO"
LOG_FILE = CLO_WORKSPACE / "clo_api.log"

# Version
CLO_VERSION = "7.2"  # Update based on your installation


def verify_installation():
    """
    Verify CLO3D installation and paths.
    
    Returns:
        dict: Installation status and paths
        
    Raises:
        RuntimeError: If verification fails
    """
    issues = []
    
    # Check if CLO executable exists (optional - may not be installed yet)
    clo_exists = CLO_EXECUTABLE.exists()
    
    # Check if API directory exists (optional - may not be installed yet)
    api_exists = CLO_API_DIR.exists()
    
    # Workspace should exist (we create it)
    if not CLO_WORKSPACE.exists():
        issues.append(f"CLO workspace directory not found: {CLO_WORKSPACE}")
    
    # Return status even if CLO is not installed yet
    # This allows configuration to be created before installation
    return {
        "clo_version": CLO_VERSION,
        "clo_path": str(CLO_EXECUTABLE),
        "clo_installed": clo_exists,
        "api_path": str(CLO_API_DIR),
        "api_installed": api_exists,
        "workspace": str(CLO_WORKSPACE),
        "status": "CLO NOT INSTALLED" if not clo_exists else "OK",
        "issues": issues if issues else None
    }


if __name__ == "__main__":
    # Test configuration
    print("CLO3D Configuration Test")
    print("=" * 50)
    result = verify_installation()
    for key, value in result.items():
        if value is not None:
            print(f"{key}: {value}")
    
    if result["status"] == "OK":
        print("\n✓ Configuration valid and CLO3D installation detected")
    else:
        print("\n⚠ Configuration created but CLO3D not yet installed")
        print("  This is normal if you haven't installed CLO3D yet")
