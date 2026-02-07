@echo off
REM ============================================
REM Step 6: Apply Color and Design Texture
REM ============================================

setlocal

set BLENDER="C:\Program Files\Blender Foundation\Blender 5.0\blender.exe"
set PIPELINE_DIR=c:\Users\Anant\mirra-mvp\2D_to_3D_tshirt\minimal_pipeline

echo ============================================
echo Step 6: Apply Texture to 3D Garment
echo ============================================
echo.
echo This will:
echo  - Load the sewn garment from Step 5
echo  - Apply fabric color (Black)
echo  - Apply design texture
echo  - Create final textured 3D model
echo.
pause

cd /d "%PIPELINE_DIR%"

echo.
echo Running Blender texture script...
echo.

REM Open the sewn file and run texture script
%BLENDER% tshirt_sewn.blend --background --python step6_apply_texture.py

if errorlevel 1 (
    echo.
    echo ============================================
    echo ERROR: Texture application failed!
    echo ============================================
    echo Check the error messages above.
    echo.
    pause
    exit /b 1
)

echo.
echo ============================================
echo Step 6 COMPLETE!
echo ============================================
echo.
echo Your 3D T-shirt is ready!
echo Open tshirt_sewn.blend in Blender to view it.
echo.
echo To export:
echo  1. Open Blender
echo  2. File -^> Export -^> FBX or OBJ
echo.
pause
