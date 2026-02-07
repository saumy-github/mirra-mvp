@echo off
REM ============================================
REM Step 5: Blender Sewing & Cloth Simulation
REM ============================================

setlocal

set BLENDER="C:\Program Files\Blender Foundation\Blender 5.0\blender.exe"
set PIPELINE_DIR=c:\Users\Anant\mirra-mvp\2D_to_3D_tshirt\minimal_pipeline

echo ============================================
echo Step 5: Blender Sewing Simulation
echo ============================================
echo.
echo This will:
echo  - Import SVG patterns from Step 4
echo  - Convert to 3D cloth meshes
echo  - Sew panels together with physics
echo  - Run cloth simulation (may take 5-10 min)
echo.
echo The Blender window will open and run automatically.
echo Watch the console for progress...
echo.
pause

cd /d "%PIPELINE_DIR%"

echo.
echo Running Blender sewing script...
echo.

%BLENDER% --background --python step5_blender_sewing.py -- --output tshirt_sewn.blend

if errorlevel 1 (
    echo.
    echo ============================================
    echo ERROR: Blender sewing failed!
    echo ============================================
    echo Check the error messages above.
    echo.
    pause
    exit /b 1
)

echo.
echo ============================================
echo Step 5 COMPLETE!
echo ============================================
echo.
echo Output saved to Blender file
echo Next: Run Step 6 to apply textures
echo.
pause
