"""
Test CLO3D API Connection

This script tests basic connectivity with the CLO3D API server.
"""
import sys
import time
import subprocess
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from config.clo_config import (
        CLO_EXECUTABLE,
        CLO_API_BASE_URL,
        CLO_API_PORT,
        verify_installation
    )
    import requests
except ImportError as e:
    print(f"Error: Missing required package: {e}")
    print("\nPlease install required packages:")
    print("  pip install requests")
    sys.exit(1)


def check_api_server():
    """Check if CLO API server is running."""
    try:
        response = requests.get(
            f"{CLO_API_BASE_URL}/version",
            timeout=2
        )
        
        if response.status_code == 200:
            print(f"✓ API server responding")
            try:
                data = response.json()
                print(f"  Version: {data.get('version', 'Unknown')}")
            except:
                print(f"  (Could not parse version)")
            return True
        else:
            print(f"✗ API returned status {response.status_code}")
            return False
            
    except requests.ConnectionError:
        print("✗ Cannot connect to API (connection refused)")
        print(f"  URL: {CLO_API_BASE_URL}")
        return False
    except requests.Timeout:
        print("✗ API connection timeout")
        return False
    except Exception as e:
        print(f"✗ API connection error: {e}")
        return False


def test_basic_operations():
    """Test basic API operations."""
    print("\nTesting basic API operations...")
    
    # Test 1: Create project
    try:
        print("  1. Creating test project...")
        response = requests.post(
            f"{CLO_API_BASE_URL}/project/new",
            json={"name": "test_connection"},
            timeout=5
        )
        
        if response.status_code in [200, 201]:
            print("     ✓ Project creation successful")
        else:
            print(f"     ⚠ Unexpected status: {response.status_code}")
    except Exception as e:
        print(f"     ⚠ Could not test project creation: {e}")
    
    # Test 2: List projects
    try:
        print("  2. Listing projects...")
        response = requests.get(
            f"{CLO_API_BASE_URL}/projects",
            timeout=5
        )
        
        if response.status_code == 200:
            print("     ✓ Project listing successful")
        else:
            print(f"     ⚠ Unexpected status: {response.status_code}")
    except Exception as e:
        print(f"     ⚠ Could not test project listing: {e}")


def print_instructions():
    """Print instructions for enabling API server."""
    print("\n" + "=" * 60)
    print("HOW TO ENABLE CLO3D API SERVER")
    print("=" * 60)
    print("\nBefore running this test, you need to:")
    print("\n1. Install CLO3D SET Enterprise (if not already installed)")
    print(f"   Expected location: {CLO_EXECUTABLE}")
    print("\n2. Start CLO3D application")
    print("\n3. Enable API Server:")
    print("   - Click: Edit → Preferences (or press Ctrl+,)")
    print("   - Navigate to: API tab")
    print("   - Check: ☑ Enable API Server")
    print(f"   - Set Port: {CLO_API_PORT}")
    print("   - Set Host: localhost")
    print("   - Check: ☑ Start on Launch (optional)")
    print("   - Click: OK")
    print("\n4. Restart CLO3D (if you enabled 'Start on Launch')")
    print("   OR keep CLO3D running while testing")
    print("\n5. Run this test again")
    print("=" * 60)


def main():
    """Run all connection tests."""
    print("\n" + "=" * 60)
    print("CLO3D API Connection Test")
    print("=" * 60 + "\n")
    
    # Step 1: Verify installation
    print("Step 1: Verify Configuration")
    try:
        config = verify_installation()
        print("✓ Configuration loaded")
        print(f"  Workspace: {config['workspace']}")
        
        if config['clo_installed']:
            print(f"  CLO Path: {config['clo_path']}")
            print("  Status: CLO3D detected")
        else:
            print(f"  CLO Path: {config['clo_path']} (not found)")
            print("  Status: CLO3D not installed")
            print("\n⚠ CLO3D is not installed at the expected location.")
            print("  If you have CLO3D installed elsewhere, update config/clo_config.py")
    except Exception as e:
        print(f"✗ Configuration error: {e}")
        return False
    
    # Step 2: Check API server
    print("\nStep 2: Check API Server")
    api_running = check_api_server()
    
    if not api_running:
        print("\n⚠ CLO3D API server is not responding")
        print_instructions()
        return False
    
    # Step 3: Test basic operations
    print("\nStep 3: Test Basic Operations")
    test_basic_operations()
    
    print("\n" + "=" * 60)
    print("Connection Test Complete!")
    print("=" * 60)
    
    if api_running:
        print("\n✓ API server is running and accessible")
        print("  You can proceed with CLO3D integration development")
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
