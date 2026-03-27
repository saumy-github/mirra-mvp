# CLO REST Plugin - Build & Usage Guide

## Overview
This plugin creates an HTTP REST server inside CLO3D, allowing Python scripts to control CLO via HTTP requests.

## What We've Discovered from SDK

### Import API (IMPORT_API namespace)
- `ImportOBJ(const std::string& path, const Marvelous::ImportExportOption& options)` - Import OBJ avatars
- `ImportDXF(const std::string& path, const Marvelous::ImportDxfOption& options)` - Import DXF patterns
- `ImportAvatar(std::string path, Marvelous::ImportExportOption opt)` - Direct avatar import

### Pattern API (PATTERN_API namespace)
- `GetPatternCount()` - Get number of patterns
- `GetPatternInformation(int index)` - Get pattern details as JSON
- `AddSeamlinePairGroup(int patternA, int lineA, int patternB, int lineB, bool dirA, bool dirB)` - Create seams

### Utility API (UTILITY_API namespace)
- `Simulate(unsigned int steps)` - Run simulation for N steps
- `DisplayMessageBox(std::string msg)` - Show messages in CLO
- `GetProjectName()` - Get current project name

### Export API (EXPORT_API namespace)
- `ExportGLTF(const std::string& path, const Marvelous::ImportExportOption& opts, bool bGLB)` - Export GLB/GLTF
- `ExportZPrj(const std::string& path, bool createThumbnail)` - Save project

## Build Instructions

### Prerequisites
- Visual Studio 2022 with C++ Desktop Development
- CLO SDK v2025.2.236 extracted
- CLO Standalone OnlineAuth installed
- CMake (via Developer Command Prompt)

### Step 1: Copy Plugin Files to SDK
```powershell
# Copy from workspace to SDK samples folder
$pluginSource = "C:\Users\Anant\mirra-mvp\clo_workspace\plugins"
$sdkSamples = "C:\setup\CLO_SDK_v2025.2.236_WIN\CLO_SDK_v2025.2.236_WIN\Samples\RestPlugin"

# Create RestPlugin folder
New-Item -ItemType Directory -Force -Path $sdkSamples

# Copy files
Copy-Item "$pluginSource\RestPlugin.cpp" -Destination $sdkSamples
Copy-Item "$pluginSource\CMakeLists.txt" -Destination $sdkSamples
Copy-Item "$pluginSource\stdafx.h" -Destination $sdkSamples
Copy-Item "$pluginSource\httplib.h" -Destination $sdkSamples
Copy-Item "$pluginSource\json.hpp" -Destination $sdkSamples
```

### Step 2: Build the Plugin
```powershell
# Open Developer Command Prompt for VS 2022
# Navigate to plugin folder
cd "C:\setup\CLO_SDK_v2025.2.236_WIN\CLO_SDK_v2025.2.236_WIN\Samples\RestPlugin"

# Create build directory
New-Item -ItemType Directory -Force -Path build
cd build

# Generate project
cmake .. -G "Visual Studio 17 2022" -A x64

# Build Release version
cmake --build . --config Release

# Result: build\Release\RestPlugin.dll
```

### Step 3: Install Plugin to CLO
```powershell
# IMPORTANT: Close CLO before copying!
# Copy DLL to CLO plugins folder (requires admin or closing CLO)
Copy-Item "build\Release\RestPlugin.dll" -Destination "C:\Program Files\CLO Standalone OnlineAuth\plugins\RestPlugin.dll"
```

### Step 4: Verify Plugin Loaded
1. Start CLO3D
2. Go to **Main Menu → Plugins → Plugin Manager**
3. Look for "RestPlugin" in the list
4. It should show as loaded/active
5. Check for message box: "CLO REST Server starting on http://localhost:50505"

### Step 5: Test REST API
```powershell
# Test health endpoint
curl http://localhost:50505/health

# Expected response:
# {"status":"ok","plugin":"CLO REST Automation","version":"1.0"}
```

## REST API Endpoints

### Health Check
```http
GET /health
Response: {"status":"ok","plugin":"CLO REST Automation","version":"1.0"}
```

### Import Avatar
```http
POST /import-avatar
Content-Type: application/json

{
  "path": "C:/Users/Anant/mirra-mvp/avatar_generation/output/u_001-001/avatar.obj"
}

Response: {"success":true,"message":"Avatar imported successfully","path":"..."}
```

### Import Pattern (DXF)
```http
POST /import-pattern
Content-Type: application/json

{
  "path": "C:/Users/Anant/mirra-mvp/output_test/patterns_dxf/front_panel.dxf"
}

Response: {"success":true,"message":"Pattern imported successfully","path":"..."}
```

### Create Seam Between Patterns
```http
POST /create-seam
Content-Type: application/json

{
  "patternA_index": 0,
  "lineA_index": 1,
  "patternB_index": 1,
  "lineB_index": 3,
  "directionA": true,
  "directionB": false
}

Response: {"success":true,"message":"Seam created successfully"}
```

### Run Simulation
```http
POST /simulate
Content-Type: application/json

{
  "steps": 100
}

Response: {"success":true,"message":"Simulation completed","steps":100}
```

### Export Garment
```http
POST /export
Content-Type: application/json

{
  "path": "C:/Users/Anant/mirra-mvp/clo_workspace/exports/output.glb",
  "format": "glb"
}

Response: {"success":true,"message":"Export successful","output_paths":["..."]}
```

### Get Pattern Count
```http
GET /patterns/count

Response: {"success":true,"count":4}
```

### Get Pattern Information
```http
GET /patterns/0

Response: {"success":true,"pattern_index":0,"info":{...}}
```

### Save Project
```http
POST /save-project
Content-Type: application/json

{
  "path": "C:/Users/Anant/mirra-mvp/clo_workspace/projects/test_project.zprj",
  "thumbnail": true
}

Response: {"success":true,"message":"Project saved","output_path":"..."}
```

## Python Client Usage

```python
import requests
import json

class CLORestClient:
    def __init__(self, base_url="http://localhost:50505"):
        self.base_url = base_url
    
    def health_check(self):
        """Check if CLO REST server is running"""
        response = requests.get(f"{self.base_url}/health")
        return response.json()
    
    def import_avatar(self, obj_path):
        """Import avatar OBJ file"""
        response = requests.post(
            f"{self.base_url}/import-avatar",
            json={"path": obj_path}
        )
        return response.json()
    
    def import_pattern(self, dxf_path):
        """Import pattern DXF file"""
        response = requests.post(
            f"{self.base_url}/import-pattern",
            json={"path": dxf_path}
        )
        return response.json()
    
    def create_seam(self, pattern_a, line_a, pattern_b, line_b, dir_a=True, dir_b=True):
        """Create seam between two pattern edges"""
        response = requests.post(
            f"{self.base_url}/create-seam",
            json={
                "patternA_index": pattern_a,
                "lineA_index": line_a,
                "patternB_index": pattern_b,
                "lineB_index": line_b,
                "directionA": dir_a,
                "directionB": dir_b
            }
        )
        return response.json()
    
    def simulate(self, steps=100):
        """Run simulation"""
        response = requests.post(
            f"{self.base_url}/simulate",
            json={"steps": steps}
        )
        return response.json()
    
    def export_garment(self, output_path, format="glb"):
        """Export garment as GLB or GLTF"""
        response = requests.post(
            f"{self.base_url}/export",
            json={"path": output_path, "format": format}
        )
        return response.json()
    
    def get_pattern_count(self):
        """Get number of patterns in CLO"""
        response = requests.get(f"{self.base_url}/patterns/count")
        return response.json()
    
    def get_pattern_info(self, pattern_index):
        """Get pattern information"""
        response = requests.get(f"{self.base_url}/patterns/{pattern_index}")
        return response.json()
    
    def save_project(self, zprj_path, thumbnail=True):
        """Save CLO project file"""
        response = requests.post(
            f"{self.base_url}/save-project",
            json={"path": zprj_path, "thumbnail": thumbnail}
        )
        return response.json()

# Example usage
if __name__ == "__main__":
    client = CLORestClient()
    
    # Check connection
    print("Health check:", client.health_check())
    
    # Import avatar
    avatar_path = "C:/Users/Anant/mirra-mvp/avatar_generation/output/u_001-001/avatar.obj"
    print("Importing avatar:", client.import_avatar(avatar_path))
    
    # Import patterns
    patterns_dir = "C:/Users/Anant/mirra-mvp/output_test/patterns_dxf"
    patterns = ["front_panel.dxf", "back_panel.dxf", "sleeve_left.dxf", "sleeve_right.dxf"]
    
    for pattern in patterns:
        result = client.import_pattern(f"{patterns_dir}/{pattern}")
        print(f"Imported {pattern}:", result)
    
    # Get pattern count
    count = client.get_pattern_count()
    print("Pattern count:", count)
    
    # Create seams (example - you'll need to determine correct indices)
    # Front to Back at shoulders
    print("Creating seam:", client.create_seam(0, 1, 1, 1, True, True))
    
    # Run simulation
    print("Running simulation:", client.simulate(steps=100))
    
    # Export result
    output_path = "C:/Users/Anant/mirra-mvp/clo_workspace/exports/tshirt_output.glb"
    print("Exporting:", client.export_garment(output_path, format="glb"))
    
    # Save project
    project_path = "C:/Users/Anant/mirra-mvp/clo_workspace/projects/automated_tshirt.zprj"
    print("Saving project:", client.save_project(project_path))
```

## Troubleshooting

### Plugin doesn't appear in Plugin Manager
- Check that RestPlugin.dll is in `C:\Program Files\CLO Standalone OnlineAuth\plugins\`
- Make sure CLO was restarted after copying the DLL
- Check CLO is the correct version (2025)

### "Port 50505 already in use"
- Another instance of CLO is running with the plugin
- Close all CLO instances and restart
- Or change port in RestPlugin.cpp and rebuild

### "Connection refused" when calling API
- Plugin may not have started - check for message box on CLO startup
- Check CLO logs (if accessible)
- Try `curl http://localhost:50505/health` to verify server is running

### Import functions return false
- Check file paths use forward slashes or escaped backslashes
- Verify files exist and are valid DXF/OBJ format
- Check CLO has read permissions for the files

### Simulation doesn't work
- Make sure patterns are imported and seams are created first
- Avatar must be present in 3D window
- Check simulation settings in CLO (may need configuration)

## Next Steps

1. **Build the plugin** using the instructions above
2. **Test with Python client** to verify all endpoints work
3. **Determine pattern edge indices** for creating seams (may need trial/error or inspection)
4. **Add more endpoints** as needed:
   - Fabric assignment
   - Texture application
   - Render settings
   - Camera positioning
5. **Create automation script** for full pipeline

## SDK Documentation Reference

All API functions are documented in:
- `ImportAPIInterface.h` - Import functions
- `ExportAPIInterface.h` - Export functions
- `PatternAPIInterface.h` - Pattern manipulation
- `UtilityAPIInterface.h` - Simulation and utilities
- `FabricAPIInterface.h` - Fabric properties

Located at: `C:\setup\CLO_SDK_v2025.2.236_WIN\CLO_SDK_v2025.2.236_WIN\CLOAPIInterface\include\`
