@echo off
REM Re-run Step 5 only to fix cloth modifier issue
REM This assumes steps 1-4 have already been run successfully

echo.
echo ========================================
echo RE-RUNNING STEP 5 ONLY
echo ========================================
echo.
echo This will:
echo - Clear the Blender scene
echo - Recreate garment from existing patterns
echo - ADD CLOTH MODIFIER (the missing piece!)
echo - Save garment_simulation.blend properly
echo.
pause

cd /d c:\Users\Anant\mirra-mvp\2D_to_3D_tshirt\minimal_pipeline

echo Running Blender setup with enhanced logging...
echo.

"C:\Program Files\Blender Foundation\Blender 5.0\blender.exe" --python step5_blender_sewing.py

if errorlevel 1 (
    echo.
    echo ERROR: Blender script failed
    echo Check console for details
    pause
    exit /b 1
)

echo.
echo ========================================
echo STEP 5 COMPLETE
echo ========================================
echo.
echo The cloth modifier should now be added!
echo.
echo To verify:
echo 1. Open: garment_simulation.blend
echo 2. Select TShirt_Garment object
echo 3. Check Modifiers panel - should see "Cloth"
echo 4. Press SPACEBAR - garment should fall/drape
echo.
pause
