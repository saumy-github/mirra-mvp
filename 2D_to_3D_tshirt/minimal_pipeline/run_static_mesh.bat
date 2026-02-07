@echo off
REM Quick Static 3D T-Shirt Generator
REM No physics, no simulation, instant result!

echo ============================================================
echo    STATIC 3D T-SHIRT MESH GENERATOR
echo ============================================================
echo.
echo This creates a 3D T-shirt mesh using geometric deformation
echo instead of physics simulation. Much faster!
echo.

"C:\Program Files\Blender Foundation\Blender 5.0\blender.exe" --background --python step5_static_mesh.py

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ============================================================
    echo    SUCCESS! Static mesh created
    echo ============================================================
    echo.
    echo Output files:
    echo   - pattern_output\tshirt_static.blend
    echo   - pattern_output\exports\TShirt_Static.obj
    echo   - pattern_output\exports\TShirt_Static.fbx
    echo   - pattern_output\exports\TShirt_Static.glb
    echo.
) else (
    echo.
    echo ============================================================
    echo    FAILED - Check errors above
    echo ============================================================
    echo.
)

pause
