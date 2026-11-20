@echo off
call "C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvars64.bat" >nul 2>&1
cl /nologo /EHsc /std:c++17 /W3 /Zs /I"C:\Users\Saumy\Downloads\CLO_SDK_v2026.1.224_Win\CLOAPIInterface" /I"C:\Users\Saumy\Downloads\CLO_SDK_v2026.1.224_Win\CLOAPIInterface\include" /I"C:\D-drive-data\mirra-mvp\clo_workspace\windows" /I"C:\D-drive-data\mirra-mvp\clo_workspace\shared" /DUNICODE /D_UNICODE /DBOMAPIDLL_EXPORTS "C:\D-drive-data\mirra-mvp\clo_workspace\windows\RestPlugin_windows.cpp"
echo EXITCODE=%ERRORLEVEL%
