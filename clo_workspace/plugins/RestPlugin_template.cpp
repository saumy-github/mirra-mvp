# CLO SDK Setup Guide - Windows

**Goal:** Build a CLO plugin from the SDK and load it into CLO GUI

**Time Required:** 2-4 hours (first time), 30 mins (after env setup)

---

## Step 1: Extract and Locate SDK (5 minutes)

### Extract the ZIP
```powershell
# Extract to a clean location (avoid spaces in path)
# Good: C:\CLO_SDK\
# Bad: C:\Program Files\CLO SDK\  (spaces cause issues)

# Recommended location:
$SDK_PATH = "C:\CLO_SDK"
```

### Find the SDK structure
```powershell
cd C:\CLO_SDK
ls
```

**You should see:**
```
├── Samples/            ← Plugin examples
│   ├── CloEventPlugin/
│   ├── ExportPlugin/
│   └── LibraryWindowImplementation/
├── include/            ← CLO API headers
├── lib/                ← CLO libraries
├── docs/               ← API documentation (maybe)
└── README.txt          ← Read this!
```

---

## Step 2: Install Build Tools (1-2 hours first time)

### Required Software

#### A. Visual Studio 2022 Community (FREE)
```powershell
# Download from: https://visualstudio.microsoft.com/downloads/

# During installation, select:
# ✅ "Desktop development with C++"
# ✅ Windows 10/11 SDK
# ✅ CMake tools for Windows

# This is ~6-8 GB download, takes 30-60 min
```

#### B. CMake (if not included in VS)
```powershell
# Download from: https://cmake.org/download/
# Get: cmake-3.XX.X-windows-x86_64.msi
# Add to PATH during installation
```

#### C. Qt 5.15.x (CLO uses Qt)
```powershell
# Download from: https://www.qt.io/download-open-source
# Install Qt 5.15.2 (or version matching your CLO version)
# Select: MSVC 2019 64-bit component

# Alternative: Check if CLO already includes Qt
# Look in: C:\Program Files\CLO Standalone OnlineAuth\
# If Qt*.dll files exist, you might not need separate Qt
```

**⚠️ IMPORTANT:** Check the SDK README.txt for exact Qt version required!

---

## Step 3: Build Sample Plugin (30-60 minutes)

### Option A: Build with Visual Studio (Easiest)

**Open Developer Command Prompt:**
1. Start → "Developer Command Prompt for VS 2022"
2. Or: Start → Visual Studio 2022 → Tools → Command Prompt

```powershell
# Navigate to SDK
cd C:\CLO_SDK\Samples\ExportPlugin

# Create build directory
mkdir build
cd build

# Generate Visual Studio project
cmake .. -G "Visual Studio 17 2022" -A x64

# This creates ExportPlugin.sln
# Open it:
start ExportPlugin.sln
```

**In Visual Studio:**
1. Set build configuration to **Release** (top toolbar)
2. Right-click solution → **Build Solution** (Ctrl+Shift+B)
3. Wait for build to complete
4. Output will be in: `build\Release\ExportPlugin.dll`

### Option B: Build via Command Line (Faster if it works)

```powershell
cd C:\CLO_SDK\Samples\ExportPlugin
mkdir build
cd build

# Configure
cmake .. -G "Visual Studio 17 2022" -A x64

# Build
cmake --build . --config Release

# Output: build\Release\ExportPlugin.dll
```

---

## Step 4: Common Build Errors & Fixes

### Error: "Qt not found"
```cmake
# Edit CMakeLists.txt in the plugin folder
# Add before find_package(Qt5):

set(CMAKE_PREFIX_PATH "C:/Qt/5.15.2/msvc2019_64")
```

### Error: "CLO headers not found"
```cmake
# CMakeLists.txt should have:
include_directories(${CMAKE_SOURCE_DIR}/../../include)

# If it doesn't, add it
```

### Error: "CLO libraries not found"
```cmake
# CMakeLists.txt should reference:
link_directories(${CMAKE_SOURCE_DIR}/../../lib)

# Check if lib/ folder exists in SDK
```

### Error: "MSVC version mismatch"
```powershell
# Use the exact VS version CLO SDK expects
# Check README.txt for required Visual Studio version

# For VS 2022:
cmake .. -G "Visual Studio 17 2022" -A x64

# For VS 2019:
cmake .. -G "Visual Studio 16 2019" -A x64
```

---

## Step 5: Install Plugin into CLO (5 minutes)

### Find CLO plugins folder
```powershell
# Common locations:
$CLO_PLUGINS = "C:\Program Files\CLO Standalone OnlineAuth\plugins"

# Or check CLO installation directory:
Get-ChildItem "C:\Program Files" -Filter "*CLO*" -Directory
```

### Copy the DLL
```powershell
# Copy your built plugin
$PLUGIN_DLL = "C:\CLO_SDK\Samples\ExportPlugin\build\Release\ExportPlugin.dll"
$CLO_PLUGINS = "C:\Program Files\CLO Standalone OnlineAuth\plugins"

# You'll need admin privileges
Copy-Item $PLUGIN_DLL $CLO_PLUGINS -Force
```

**If plugins folder doesn't exist:**
```powershell
# Create it
New-Item -ItemType Directory -Path $CLO_PLUGINS
```

---

## Step 6: Load Plugin in CLO (2 minutes)

### Method 1: Auto-load (Recommended)
1. Copy DLL to `plugins/` folder (done above)
2. Restart CLO
3. Plugin loads automatically

### Method 2: Manual load
1. Open CLO
2. Main Menu → **Settings** → **Plug-in Manager**
3. Click **"+ ADD"**
4. Browse to your `.dll` file
5. Name it and choose display position
6. Click **OK**

### Verify Plugin Loaded
```
CLO → Main Menu
Look for new menu items or check:
Settings → Plug-in Manager → See if plugin is listed
```

---

## Step 7: Test the Plugin (5 minutes)

### For ExportPlugin example:

1. Open or create a garment in CLO
2. Look for **"Export Plugin"** in menu
3. Click it → Should export garment data
4. Check console/log for output

### For CloEventPlugin example:

1. Plugin runs in background
2. Listen for CLO events (garment load, simulation, etc.)
3. Check CLO log: Help → Log Console

---

## Step 8: Build Your Own REST Plugin

Now that you can build plugins, create a simple REST endpoint plugin:

<function_calls>
<invoke name="create_file">
<parameter name="content">// RestPlugin.cpp - Minimal REST server for CLO automation
// Place this in: C:\CLO_SDK\Samples\RestPlugin\

// Update the include path based on your CLO SDK location
// Replace with the correct path to your CLO SDK include directory
#include "../../../include/API.h"  // Adjust path relative to SDK structure
#include <iostream>
#include <thread>

// We'll use cpp-httplib (header-only HTTP server)
// Download from: https://github.com/yhirose/cpp-httplib
// Place httplib.h in same folder
#include "httplib.h"

using namespace CLO_PLUGIN;

class RestPlugin : public CLO_Plugin
{
public:
    RestPlugin() {}
    virtual ~RestPlugin() {}
    
    // Called when plugin loads
    virtual void Initialize() override
    {
        std::cout << "[RestPlugin] Initializing..." << std::endl;
        
        // Start REST server in separate thread
        server_thread = std::thread([this]() {
            StartServer();
        });
        
        std::cout << "[RestPlugin] REST server started on http://localhost:50505" << std::endl;
    }
    
    // Called when plugin unloads
    virtual void Finalize() override
    {
        std::cout << "[RestPlugin] Shutting down..." << std::endl;
        server.stop();
        if (server_thread.joinable()) {
            server_thread.join();
        }
    }
    
private:
    httplib::Server server;
    std::thread server_thread;
    
    void StartServer()
    {
        // Health check endpoint
        server.Get("/health", [](const httplib::Request&, httplib::Response& res) {
            res.set_content("{\"status\":\"ok\"}", "application/json");
        });
        
        // Import avatar
        server.Post("/import-avatar", [](const httplib::Request& req, httplib::Response& res) {
            try {
                std::string avatar_path = req.body;
                
                // Call CLO API to import avatar
                CLO_API::ImportAvatar(avatar_path);
                
                res.set_content("{\"status\":\"success\"}", "application/json");
            } catch (const std::exception& e) {
                res.status = 500;
                res.set_content("{\"status\":\"error\",\"message\":\"" + std::string(e.what()) + "\"}", "application/json");
            }
        });
        
        // Import pattern
        server.Post("/import-pattern", [](const httplib::Request& req, httplib::Response& res) {
            try {
                std::string pattern_path = req.body;
                
                // Call CLO API to import DXF pattern
                CLO_API::ImportPattern(pattern_path);
                
                res.set_content("{\"status\":\"success\"}", "application/json");
            } catch (const std::exception& e) {
                res.status = 500;
                res.set_content("{\"status\":\"error\",\"message\":\"" + std::string(e.what()) + "\"}", "application/json");
            }
        });
        
        // Run simulation
        server.Post("/simulate", [](const httplib::Request& req, httplib::Response& res) {
            try {
                // Parse JSON body for parameters (optional)
                // For now, run with default settings
                
                CLO_API::RunSimulation();
                
                res.set_content("{\"status\":\"success\"}", "application/json");
            } catch (const std::exception& e) {
                res.status = 500;
                res.set_content("{\"status\":\"error\",\"message\":\"" + std::string(e.what()) + "\"}", "application/json");
            }
        });
        
        // Export garment
        server.Post("/export", [](const httplib::Request& req, httplib::Response& res) {
            try {
                // Expect JSON: {"path": "output.glb", "format": "glb"}
                std::string output_path = req.body;
                
                CLO_API::ExportGarment(output_path, "glb");
                
                res.set_content("{\"status\":\"success\"}", "application/json");
            } catch (const std::exception& e) {
                res.status = 500;
                res.set_content("{\"status\":\"error\",\"message\":\"" + std::string(e.what()) + "\"}", "application/json");
            }
        });
        
        // Start listening
        std::cout << "[RestPlugin] Listening on port 50505..." << std::endl;
        server.listen("localhost", 50505);
    }
};

// Plugin entry point
extern "C" __declspec(dllexport) CLO_Plugin* CreatePlugin()
{
    return new RestPlugin();
}

extern "C" __declspec(dllexport) void DestroyPlugin(CLO_Plugin* plugin)
{
    delete plugin;
}
