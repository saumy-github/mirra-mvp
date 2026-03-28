@echo off
setlocal EnableExtensions EnableDelayedExpansion
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

call :ensure_cmake
if errorlevel 1 exit /b 1

call :ensure_msvc
if errorlevel 1 exit /b 1

echo [Step 1/6] Checking prerequisites...
if not exist "%SDK_PATH%" (
    echo ERROR: CLO SDK not found at %SDK_PATH%
    echo Set CLO_SDK_PATH to your SDK root, for example:
    echo   set CLO_SDK_PATH=D:\setup\CLO_SDK_v2025.2.236_WIN\CLO_SDK_v2025.2.236_WIN
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
    echo ERROR: CMake configuration failed.
    echo Tip: Ensure Visual Studio 2022 C++ desktop workload is installed.
    exit /b 1
)

echo [Step 5/6] Building plugin (Release)...
cmake --build . --config Release
if errorlevel 1 (
    echo ERROR: Build failed!
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
echo Build complete.
echo If CLO is closed, copy DLL with:
echo   Copy-Item "%PLUGIN_DIR%\build\Release\RestPlugin.dll" -Destination "%CLO_PLUGINS%\RestPlugin.dll" -Force

set "RELEASE_DIR=%PLUGIN_DIR%\build\Release"
call :open_folder "%RELEASE_DIR%"
exit /b 0

:ensure_cmake
if not "%CMAKE_EXE%"=="" (
    if exist "%CMAKE_EXE%" (
        for %%I in ("%CMAKE_EXE%") do set "CMAKE_BIN=%%~dpI"
        set "PATH=%CMAKE_BIN%;%PATH%"
        goto :cmake_ok
    )
)

if not "%CMAKE_BIN%"=="" (
    if exist "%CMAKE_BIN%\cmake.exe" (
        set "PATH=%CMAKE_BIN%;%PATH%"
        goto :cmake_ok
    )
)

where cmake >nul 2>nul
if not errorlevel 1 goto :cmake_ok

for %%P in (
    "%ProgramFiles%\CMake\bin"
    "%ProgramFiles(x86)%\CMake\bin"
    "%LocalAppData%\Programs\CMake\bin"
    "%ProgramFiles%\Microsoft Visual Studio\2022\Community\Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin"
    "%ProgramFiles%\Microsoft Visual Studio\2022\Professional\Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin"
    "%ProgramFiles%\Microsoft Visual Studio\2022\Enterprise\Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin"
    "%ProgramFiles(x86)%\Microsoft Visual Studio\2019\Community\Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin"
    "%ChocolateyInstall%\bin"
    "%USERPROFILE%\scoop\shims"
) do (
    if exist "%%~P\cmake.exe" (
        set "PATH=%%~P;%PATH%"
        goto :cmake_ok
    )
)

echo ERROR: cmake is not available in PATH and was not found in common install locations.
echo You can also set CMAKE_BIN or CMAKE_EXE before running this script.
echo Example:
echo   set CMAKE_BIN=C:\Program Files\CMake\bin
echo Install CMake and re-run this script, or add cmake.exe to PATH.
exit /b 1

:cmake_ok
for /f "tokens=*" %%V in ('cmake --version ^| findstr /b /c:"cmake version"') do echo Detected %%V
exit /b 0

:ensure_msvc
where cl >nul 2>nul
if not errorlevel 1 goto :msvc_ok

set "VSWHERE=%ProgramFiles(x86)%\Microsoft Visual Studio\Installer\vswhere.exe"
set "VSINSTALL="
if exist "%VSWHERE%" (
    for /f "usebackq tokens=*" %%I in (`"%VSWHERE%" -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath`) do (
        set "VSINSTALL=%%I"
    )
)

if not defined VSINSTALL (
    echo ERROR: MSVC tools not found.
    echo Install Visual Studio 2022 with Desktop development with C++ workload.
    exit /b 1
)

if exist "%VSINSTALL%\Common7\Tools\VsDevCmd.bat" (
    call "%VSINSTALL%\Common7\Tools\VsDevCmd.bat" -arch=x64 -host_arch=x64 >nul
) else if exist "%VSINSTALL%\VC\Auxiliary\Build\vcvars64.bat" (
    call "%VSINSTALL%\VC\Auxiliary\Build\vcvars64.bat" >nul
) else (
    echo ERROR: Could not find VsDevCmd.bat or vcvars64.bat in Visual Studio install.
    exit /b 1
)

where cl >nul 2>nul
if errorlevel 1 (
    echo ERROR: MSVC environment failed to initialize.
    exit /b 1
)

:msvc_ok
echo Detected MSVC toolchain.
exit /b 0

:open_folder
set "TARGET_DIR=%~1"
if not exist "%TARGET_DIR%" (
    echo WARNING: Build output folder not found: %TARGET_DIR%
    exit /b 0
)

REM Windows first
where explorer >nul 2>nul
if not errorlevel 1 (
    start "" "%TARGET_DIR%"
    exit /b 0
)

REM Linux/WSL fallback
where xdg-open >nul 2>nul
if not errorlevel 1 (
    xdg-open "%TARGET_DIR%" >nul 2>nul
    exit /b 0
)

REM macOS fallback
where open >nul 2>nul
if not errorlevel 1 (
    open "%TARGET_DIR%" >nul 2>nul
    exit /b 0
)

echo WARNING: Could not auto-open folder. Open manually: %TARGET_DIR%
exit /b 0
