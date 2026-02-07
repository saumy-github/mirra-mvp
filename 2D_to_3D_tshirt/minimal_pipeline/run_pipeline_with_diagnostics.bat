@echo off
REM ============================================
REM Complete Fresh Run with Diagnostics
REM ============================================

setlocal

set PYTHON=c:\Users\Anant\mirra-mvp\.venv313\Scripts\python.exe
set BLENDER="C:\Program Files\Blender Foundation\Blender 5.0\blender.exe"
set PIPELINE_DIR=c:\Users\Anant\mirra-mvp\2D_to_3D_tshirt\minimal_pipeline

echo ============================================
echo 2D to 3D T-Shirt Pipeline - WITH DIAGNOSTICS
echo ============================================
echo.

cd /d "%PIPELINE_DIR%"

REM ============================================
REM PRE-FLIGHT CHECK
REM ============================================
echo.
echo ========================================
echo PRE-FLIGHT DIAGNOSTIC
echo ========================================
echo.

%PYTHON% pipeline_diagnostic.py
if errorlevel 1 (
    echo.
    echo Some prerequisites missing, but continuing...
    pause
)

REM ============================================
REM CLEAN UP
REM ============================================
echo.
echo Cleaning up old outputs...
if exist "segmentation_output" rmdir /s /q "segmentation_output"
if exist "design_output" rmdir /s /q "design_output"
if exist "color_output" rmdir /s /q "color_output"
if exist "pattern_output" rmdir /s /q "pattern_output"
if exist "garment_simulation.blend" del "garment_simulation.blend"
if exist "garment_simulation.blend1" del "garment_simulation.blend1"
echo Done.
pause

REM ============================================
REM PYTHON STEPS
REM ============================================
echo.
echo [1/4] Segmentation...
%PYTHON% step1_segmentation.py
if errorlevel 1 goto :error

echo.
echo [2/4] Design Extraction...
%PYTHON% step2_design_extraction.py
if errorlevel 1 goto :error

echo.
echo [3/4] Color Extraction...
%PYTHON% step3_color_extraction.py
if errorlevel 1 goto :error

echo.
echo [4/4] Pattern Generation...
%PYTHON% step4_pattern_generation.py
if errorlevel 1 goto :error

REM ============================================
REM POST-PYTHON DIAGNOSTIC
REM ============================================
echo.
echo ========================================
echo POST-PYTHON DIAGNOSTIC
echo ========================================
echo.
echo Verifying Python step outputs...
%PYTHON% pipeline_diagnostic.py
pause

REM ============================================
REM BLENDER STEP
REM ============================================
echo.
echo ========================================
echo STEP 5: BLENDER SIMULATION SETUP
echo ========================================
echo.
echo Opening Blender with enhanced logging...
echo Watch the system console for detailed mesh info.
echo.
echo After Blender opens:
echo  1. Look at the 3D viewport
echo  2. Press SPACEBAR to run simulation
echo  3. Watch if panels move
echo.
echo If panels don't move:
echo  - Open Scripting workspace
echo  - Open blender_diagnostic.py
echo  - Click Run Script
echo  - Read the diagnostic output
echo.
pause

%BLENDER% --python step5_blender_sewing.py

echo.
echo ========================================
echo PIPELINE COMPLETE
echo ========================================
echo.
echo Check Blender for the result.
echo If simulation didn't work, run:
echo   blender garment_simulation.blend --python blender_diagnostic.py
echo.
pause
exit /b 0

:error
echo.
echo ========================================
echo ERROR OCCURRED
echo ========================================
echo Check the error messages above.
pause
exit /b 1
