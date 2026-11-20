param([int]$X, [int]$Y)
Add-Type @"
using System; using System.Runtime.InteropServices;
public class C1 {
  [DllImport("user32.dll")] public static extern bool SetProcessDPIAware();
  [DllImport("user32.dll")] public static extern bool SetCursorPos(int x, int y);
  [DllImport("user32.dll")] public static extern void mouse_event(uint f, uint dx, uint dy, uint d, UIntPtr e);
}
"@
[void][C1]::SetProcessDPIAware()
[void][C1]::SetCursorPos($X, $Y)
Start-Sleep -Milliseconds 250
[C1]::mouse_event(2, 0, 0, 0, [UIntPtr]::Zero)
Start-Sleep -Milliseconds 80
[C1]::mouse_event(4, 0, 0, 0, [UIntPtr]::Zero)
"clicked $X,$Y"
