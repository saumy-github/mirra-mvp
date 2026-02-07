@echo off
REM ============================================
REM Open Blender GUI for Manual Execution
REM ============================================

setlocal

set BLENDER="C:\Program Files\Blender Foundation\Blender 5.0\blender.exe"
set PIPELINE_DIR=c:\Users\Anant\mirra-mvp\2D_to_3D_tshirt\minimal_pipeline

echo ============================================
echo Opening Blender - Manual Mode
echo ============================================
echo.
echo Blender will open. To run the scripts:
echo.
echo FOR STEP 5 (Sewing):
echo   1. Switch to "Scripting" workspace (top menu)
echo   2. Click "Open" and select: step5_blender_sewing.py
echo   3. Click the "Run Script" button (play icon)
echo   4. Wait 5-10 minutes for simulation
echo.
echo FOR STEP 6 (Texture):
echo   1. After Step 5 completes
echo   2. Open: step6_apply_texture.py
echo   3. Click "Run Script"
echo.
pause

cd /d "%PIPELINE_DIR%"

%BLENDER%
