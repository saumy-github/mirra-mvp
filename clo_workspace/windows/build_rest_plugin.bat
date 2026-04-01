@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
if "%SCRIPT_DIR:~-1%"=="\" set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"
for %%I in ("%SCRIPT_DIR%\..") do set "WORKSPACE_DIR=%%~fI"

where py >nul 2>nul
if not errorlevel 1 (
    py -3 "%WORKSPACE_DIR%\build_plugin.py" %*
    exit /b %errorlevel%
)

where python >nul 2>nul
if not errorlevel 1 (
    python "%WORKSPACE_DIR%\build_plugin.py" %*
    exit /b %errorlevel%
)

echo ERROR: Python was not found in PATH.
echo Install Python or run the shared build entry point manually:
echo   python "%WORKSPACE_DIR%\build_plugin.py"
exit /b 1
