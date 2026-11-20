param([string]$Out = "C:\D-drive-data\mirra-mvp\.agent\saumy\10_03\18-10-website\phase0-clo-experiments\work\uia.txt")
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
Add-Type @"
using System.Runtime.InteropServices;
public class D2 { [DllImport("user32.dll")] public static extern bool SetProcessDPIAware(); }
"@
[void][D2]::SetProcessDPIAware()
$p = Get-Process | Where-Object { $_.ProcessName -like 'CLO_Standalone*' } | Select-Object -First 1
$root = [System.Windows.Automation.AutomationElement]::FromHandle($p.MainWindowHandle)
$all = $root.FindAll([System.Windows.Automation.TreeScope]::Descendants, [System.Windows.Automation.Condition]::TrueCondition)
$lines = New-Object System.Collections.Generic.List[string]
foreach ($e in $all) {
  try {
    $c = $e.Current
    $r = $c.BoundingRectangle
    $val = ""
    $vp = $null
    if ($e.TryGetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern, [ref]$vp)) { $val = $vp.Current.Value }
    $lines.Add(("{0}|{1}|{2}|{3},{4},{5},{6}|{7}" -f $c.ControlType.ProgrammaticName, $c.Name, $c.AutomationId, [int]$r.X, [int]$r.Y, [int]$r.Width, [int]$r.Height, $val))
  } catch {}
}
$lines | Out-File -FilePath $Out -Encoding utf8
"$($lines.Count) elements -> $Out"
