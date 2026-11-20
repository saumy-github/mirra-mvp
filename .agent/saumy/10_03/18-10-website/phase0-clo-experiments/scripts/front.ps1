Add-Type @"
using System; using System.Runtime.InteropServices;
public class W {
  [DllImport("user32.dll")] public static extern bool SetProcessDPIAware();
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int c);
  [DllImport("user32.dll")] public static extern bool IsIconic(IntPtr h);
}
"@
[void][W]::SetProcessDPIAware()
$p = Get-Process | Where-Object { $_.ProcessName -like 'CLO_Standalone*' } | Select-Object -First 1
if (-not $p) { "CLO not running"; exit 1 }
$h = $p.MainWindowHandle
"handle $h title '$($p.MainWindowTitle)' iconic $([W]::IsIconic($h))"
if ([W]::IsIconic($h)) { [void][W]::ShowWindow($h, 9) }
[void][W]::SetForegroundWindow($h)
Start-Sleep -Milliseconds 1200
"done"
