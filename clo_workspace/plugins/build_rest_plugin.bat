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

REM Detect CMake from PATH, common install paths, or Visual Studio via vswhere.
set "CMAKE_EXE=cmake"
where /Q cmake
if errorlevel 1 (
    set "CMAKE_EXE="

    if exist "C:\Program Files\CMake\bin\cmake.exe" set "CMAKE_EXE=C:\Program Files\CMake\bin\cmake.exe"
    if not defined CMAKE_EXE if exist "C:\Program Files\Microsoft Visual Studio\2022\Community\Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin\cmake.exe" set "CMAKE_EXE=C:\Program Files\Microsoft Visual Studio\2022\Community\Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin\cmake.exe"
    if not defined CMAKE_EXE if exist "C:\Program Files\Microsoft Visual Studio\2022\Professional\Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin\cmake.exe" set "CMAKE_EXE=C:\Program Files\Microsoft Visual Studio\2022\Professional\Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin\cmake.exe"
    if not defined CMAKE_EXE if exist "C:\Program Files\Microsoft Visual Studio\2022\Enterprise\Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin\cmake.exe" set "CMAKE_EXE=C:\Program Files\Microsoft Visual Studio\2022\Enterprise\Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin\cmake.exe"
    if not defined CMAKE_EXE if exist "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin\cmake.exe" set "CMAKE_EXE=C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin\cmake.exe"

    if not defined CMAKE_EXE (
        if exist "%ProgramFiles(x86)%\Microsoft Visual Studio\Installer\vswhere.exe" (
            for /f "usebackq delims=" %%I in (`"%ProgramFiles(x86)%\Microsoft Visual Studio\Installer\vswhere.exe" -latest -products * -property installationPath`) do (
                if exist "%%I\Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin\cmake.exe" set "CMAKE_EXE=%%I\Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin\cmake.exe"
            )
        )
    )
)

if not defined CMAKE_EXE (
    echo ERROR: CMake was not found.
    echo.
    echo Install one of the following and retry:
    echo   1. Standalone CMake: https://cmake.org/download/
    echo   2. Visual Studio Installer - C++ CMake tools for Windows
    echo.
    echo If already installed, restart terminal and run this script again.
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

echo Using CMake: %CMAKE_EXE%
"%CMAKE_EXE%" .. -G "Visual Studio 17 2022" -A x64
if errorlevel 1 (
    echo ERROR: CMake configuration failed!
    pause
    exit /b 1
)

echo [Step 5/6] Building plugin (Release)...
"%CMAKE_EXE%" --build . --config Release
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
