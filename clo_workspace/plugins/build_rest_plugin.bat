@echo off
REM Build script for CLO REST Plugin
REM Requires: Visual Studio 2022, CMake, CLO SDK

echo ========================================
echo CLO REST Plugin - Automated Build
echo ========================================
echo.

REM Configuration
REM Derive workspace from this script location so the repo can live anywhere.
set "WORKSPACE=%~dp0"
if "%WORKSPACE:~-1%"=="\" set "WORKSPACE=%WORKSPACE:~0,-1%"

REM Allow overriding paths via environment variables.
if "%CLO_SDK_PATH%"=="" (
    set "SDK_PATH=C:\setup\CLO_SDK_v2025.2.236_WIN\CLO_SDK_v2025.2.236_WIN"
) else (
    set "SDK_PATH=%CLO_SDK_PATH%"
)
set PLUGIN_DIR=%SDK_PATH%\Samples\RestPlugin
if "%CLO_PLUGINS_DIR%"=="" (
    set "CLO_PLUGINS=C:\Program Files\CLO Standalone OnlineAuth\plugins"
) else (
    set "CLO_PLUGINS=%CLO_PLUGINS_DIR%"
)

where cmake >nul 2>nul
if errorlevel 1 (
    echo ERROR: cmake is not available in PATH.
    echo Open "Developer Command Prompt for VS 2022" and run this script again.
    pause
    exit /b 1
)

echo [Step 1/6] Checking prerequisites...
if not exist "%SDK_PATH%" (
    echo ERROR: CLO SDK not found at %SDK_PATH%
    echo Set CLO_SDK_PATH to your SDK root, for example:
    echo   set CLO_SDK_PATH=D:\setup\CLO_SDK_v2025.2.236_WIN\CLO_SDK_v2025.2.236_WIN
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
