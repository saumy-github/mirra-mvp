@echo off
REM ============================================
REM Windows Quick-Run Script for Steps 1-4
REM ============================================
REM This runs the Python steps (no Blender)

setlocal

set PYTHON=c:\Users\Anant\mirra-mvp\.venv313\Scripts\python.exe
set PIPELINE_DIR=c:\Users\Anant\mirra-mvp\2D_to_3D_tshirt\minimal_pipeline

echo ============================================
echo 2D to 3D T-Shirt Pipeline (Python Steps)
echo ============================================
echo.

cd /d "%PIPELINE_DIR%"

echo [1/4] Running Segmentation (Step 1)...
echo ----------------------------------------
%PYTHON% step1_segmentation.py
if errorlevel 1 (
    echo ERROR in Step 1 - Check output above
    pause
    exit /b 1
)

echo.
echo.
echo [2/4] Extracting Design (Step 2)...
echo ----------------------------------------
%PYTHON% step2_design_extraction.py
if errorlevel 1 (
    echo ERROR in Step 2 - Check output above
    pause
    exit /b 1
)

echo.
echo.
echo [3/4] Extracting Color (Step 3)...
echo ----------------------------------------
%PYTHON% step3_color_extraction.py
if errorlevel 1 (
    echo ERROR in Step 3 - Check output above
    pause
    exit /b 1
)

echo.
echo.
echo [4/4] Generating Patterns (Step 4)...
echo ----------------------------------------
echo You will be prompted for measurements.
echo Press ENTER to use defaults.
echo.
%PYTHON% step4_pattern_generation.py
if errorlevel 1 (
    echo ERROR in Step 4 - Check output above
    pause
    exit /b 1
)

echo.
echo ============================================
echo ALL PYTHON STEPS COMPLETE!
echo ============================================
echo.
echo Next: Install Blender and run Steps 5-6
echo See NEXT_STEPS_PLAN.md for instructions
echo.
pause
