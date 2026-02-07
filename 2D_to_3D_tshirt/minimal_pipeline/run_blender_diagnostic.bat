@echo off
REM Run Blender diagnostic script to check simulation setup
REM This opens Blender with diagnostic info in the console

echo.
echo ========================================
echo BLENDER SIMULATION DIAGNOSTIC
echo ========================================
echo.
echo This will:
echo 1. Open the current blend file in Blender
echo 2. Run comprehensive diagnostics
echo 3. Check for common issues preventing simulation
echo.
echo AFTER BLENDER OPENS:
echo - Go to Scripting workspace (top menu)
echo - Open blender_diagnostic.py
echo - Click "Run Script"
echo - Check console output for issues
echo.
pause

"C:\Program Files\Blender Foundation\Blender 5.0\blender.exe" garment_simulation.blend --python blender_diagnostic.py

echo.
echo Diagnostic complete. Check Blender console for details.
pause
