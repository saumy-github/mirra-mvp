@echo off
REM ============================================
REM Complete Fresh Run - 2D to 3D Pipeline
REM ============================================

setlocal

set PYTHON=c:\Users\Anant\mirra-mvp\.venv313\Scripts\python.exe
set BLENDER="C:\Program Files\Blender Foundation\Blender 5.0\blender.exe"
set PIPELINE_DIR=c:\Users\Anant\mirra-mvp\2D_to_3D_tshirt\minimal_pipeline

echo ============================================
echo 2D to 3D T-Shirt Pipeline - COMPLETE RUN
echo ============================================
echo.
echo This will run ALL steps from scratch:
echo  Steps 1-4: Python (segmentation, design, color, patterns)
echo  Step 5: Blender (sewing simulation)
echo.
echo Make sure you have:
echo  [x] front.png in input_images/
echo  [x] Python 3.13 environment active
echo  [x] Blender 5.0 installed
echo.
pause

cd /d "%PIPELINE_DIR%"

REM ============================================
REM CLEAN UP OLD OUTPUTS
REM ============================================
echo.
echo Cleaning up old output directories...
if exist "segmentation_output" rmdir /s /q "segmentation_output"
if exist "design_output" rmdir /s /q "design_output"
if exist "color_output" rmdir /s /q "color_output"
if exist "pattern_output" rmdir /s /q "pattern_output"
echo Done.

REM ============================================
REM PYTHON STEPS (1-4)
REM ============================================
echo.
echo ============================================
echo Running Python Steps (1-4)
echo ============================================

echo.
echo [1/4] Segmentation...
%PYTHON% step1_segmentation.py
if errorlevel 1 goto error

echo.
echo [2/4] Design Extraction...
%PYTHON% step2_design_extraction.py
if errorlevel 1 goto error

echo.
echo [3/4] Color Extraction...
%PYTHON% step3_color_extraction.py
if errorlevel 1 goto error

echo.
echo [4/4] Pattern Generation...
echo You'll be prompted for measurements (press ENTER for defaults)
%PYTHON% step4_pattern_generation.py
if errorlevel 1 goto error

REM ============================================
REM BLENDER STEP (5)
REM ============================================
echo.
echo ============================================
echo Running Blender Sewing (Step 5)
echo ============================================
echo.
echo This will create 3D garment with cloth physics.
echo The simulation is NOT auto-run to save time.
echo.
pause

%BLENDER% --python step5_blender_sewing.py

if errorlevel 1 goto error

echo.
echo ============================================
echo ALL STEPS COMPLETE!
echo ============================================
echo.
echo Next: Open Blender to view and run simulation
echo   1. Run: run_blender_manual.bat
echo   2. Press SPACEBAR to run simulation
echo   3. Watch garment drape over avatar
echo   4. File -^> Save As -^> tshirt_final.blend
echo.
pause
exit /b 0

:error
echo.
echo ============================================
echo ERROR at step %ERRORLEVEL%
echo ============================================
echo Check the error messages above
pause
exit /b 1
