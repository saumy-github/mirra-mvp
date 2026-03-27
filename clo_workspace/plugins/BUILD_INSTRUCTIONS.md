# HOW TO BUILD THE REST PLUGIN

## The easiest way: Use Developer Command Prompt

1. Open **Start Menu**
2. Search for: **"Developer Command Prompt for VS 2022"**
3. Run it
4. Navigate to plugins folder:
   ```cmd
   cd <your-mirra-mvp-root>\clo_workspace\plugins
   ```
5. Run the build script:
   ```cmd
   build_rest_plugin.bat
   ```

That's it! The batch file will work perfectly in Developer Command Prompt.

## Alternative: PowerShell with manual CMake path

If you prefer PowerShell, here are the commands:

```powershell
# Set paths
$cmake = "C:\Program Files\Microsoft Visual Studio\2022\Community\Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin\cmake.exe"
$workspace = (Resolve-Path ".").Path
$sdkPath = if ($env:CLO_SDK_PATH) { $env:CLO_SDK_PATH } else { "C:\setup\CLO_SDK_v2025.2.236_WIN\CLO_SDK_v2025.2.236_WIN" }
$pluginDir = "$sdkPath\Samples\RestPlugin"

# Create and copy files
New-Item -ItemType Directory -Force -Path $pluginDir
Copy-Item "$workspace\RestPlugin.cpp" -Destination $pluginDir -Force
Copy-Item "$workspace\dllmain.cpp" -Destination $pluginDir -Force
Copy-Item "$workspace\CMakeLists.txt" -Destination $pluginDir -Force
Copy-Item "$workspace\stdafx.h" -Destination $pluginDir -Force
Copy-Item "$workspace\targetver.h" -Destination $pluginDir -Force
Copy-Item "$workspace\httplib.h" -Destination $pluginDir -Force
Copy-Item "$workspace\json.hpp" -Destination $pluginDir -Force

# Build
cd $pluginDir
Remove-Item -Force -Recurse -ErrorAction SilentlyContinue build
New-Item -ItemType Directory -Path build
cd build
& $cmake .. -G "Visual Studio 17 2022" -A x64
& $cmake --build . --config Release

# Check result
if (Test-Path "Release\RestPlugin.dll") {
    Write-Host "SUCCESS! DLL created at: $pluginDir\build\Release\RestPlugin.dll" -ForegroundColor Green
} else {
    Write-Host "Build failed!" -ForegroundColor Red
}
```

## After Building

1. Close CLO (if running)
2. Copy DLL to CLO plugins:
   ```powershell
   $cloPlugins = if ($env:CLO_PLUGINS_DIR) { $env:CLO_PLUGINS_DIR } else { "C:\Program Files\CLO Standalone OnlineAuth\plugins" }
   Copy-Item "$sdkPath\Samples\RestPlugin\build\Release\RestPlugin.dll" -Destination "$cloPlugins\RestPlugin.dll" -Force
   ```
3. Start CLO
4. Check Plugin Manager
5. Test: `curl http://localhost:50505/health`
