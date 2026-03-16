@echo off
REM Build script for CLO REST Plugin
REM Requires: Visual Studio 2022, CMake, CLO SDK

echo ========================================
echo CLO REST Plugin - Automated Build
echo ========================================
echo.

REM Configuration
set WORKSPACE=C:\Users\Anant\mirra-mvp\clo_workspace\plugins
set SDK_PATH=C:\setup\CLO_SDK_v2025.2.236_WIN\CLO_SDK_v2025.2.236_WIN
set PLUGIN_DIR=%SDK_PATH%\Samples\RestPlugin
set CLO_PLUGINS=C:\Program Files\CLO Standalone OnlineAuth\plugins

echo [Step 1/6] Checking prerequisites...
if not exist "%SDK_PATH%" (
    echo ERROR: CLO SDK not found at %SDK_PATH%
    pause
    exit /b 1
)

REM Ensure CMake is available (either already in PATH or from VS install)
where cmake >nul 2>&1
if errorlevel 1 (
    if exist "C:\Program Files\Microsoft Visual Studio\2022\Community\Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin\cmake.exe" (
        set "PATH=C:\Program Files\Microsoft Visual Studio\2022\Community\Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin;%PATH%"
    ) else if exist "C:\Program Files\Microsoft Visual Studio\2022\Professional\Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin\cmake.exe" (
        set "PATH=C:\Program Files\Microsoft Visual Studio\2022\Professional\Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin;%PATH%"
    ) else if exist "C:\Program Files\Microsoft Visual Studio\2022\Enterprise\Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin\cmake.exe" (
        set "PATH=C:\Program Files\Microsoft Visual Studio\2022\Enterprise\Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin;%PATH%"
    )
)

where cmake >nul 2>&1
if errorlevel 1 (
    echo ERROR: CMake not found in PATH.
    echo Install Visual Studio 2022 C++ workload or add CMake to PATH.
    pause
    exit /b 1
)

echo [Step 2/6] Creating plugin directory in SDK...
if not exist "%PLUGIN_DIR%" mkdir "%PLUGIN_DIR%"

echo [Step 3/6] Copying plugin files to SDK...
copy /Y "%WORKSPACE%\RestPlugin.cpp" "%PLUGIN_DIR%\"
copy /Y "%WORKSPACE%\dllmain.cpp" "%PLUGIN_DIR%\"
copy /Y "%WORKSPACE%\CMakeLists.txt" "%PLUGIN_DIR%\"
copy /Y "%WORKSPACE%\stdafx.h" "%PLUGIN_DIR%\"
copy /Y "%WORKSPACE%\targetver.h" "%PLUGIN_DIR%\"
copy /Y "%WORKSPACE%\httplib.h" "%PLUGIN_DIR%\"
copy /Y "%WORKSPACE%\json.hpp" "%PLUGIN_DIR%\"

echo [Step 4/6] Running CMake configuration...
cd /d "%PLUGIN_DIR%"
if not exist "build" mkdir build
cd build

cmake .. -G "Visual Studio 17 2022" -A x64
if errorlevel 1 (
    echo ERROR: CMake configuration failed!
    pause
    exit /b 1
)

echo [Step 5/6] Building plugin (Release)...
cmake --build . --config Release
if errorlevel 1 (
    echo ERROR: Build failed!
    pause
    exit /b 1
)

echo [Step 6/6] Plugin built successfully!
echo.
echo DLL Location: %PLUGIN_DIR%\build\Release\RestPlugin.dll
echo.
echo ========================================
echo MANUAL STEP REQUIRED:
echo 1. Close CLO if it's running
echo 2. Copy RestPlugin.dll to:
echo    %CLO_PLUGINS%
echo 3. Restart CLO
echo 4. Check Plugin Manager to verify it loaded
echo ========================================
echo.
echo Press any key to open plugin folder...
pause
explorer "%PLUGIN_DIR%\build\Release"
