param($s,$e,$out)
& "C:\Program Files\Microsoft Visual Studio\18\Community\VC\Tools\MSVC\14.44.35207\bin\HostX64\x64\dumpbin.exe" /nologo /disasm:nobytes "/range:0x$s,0x$e" "C:\Program Files\CLO Standalone OnlineAuth\CLO_Standalone_OnlineAuth_x64.exe" | Out-File -Encoding ascii $out
