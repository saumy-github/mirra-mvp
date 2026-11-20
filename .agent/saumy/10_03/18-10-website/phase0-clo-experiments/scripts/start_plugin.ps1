Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
Add-Type @"
using System.Runtime.InteropServices;
public class D3 { [DllImport("user32.dll")] public static extern bool SetProcessDPIAware(); }
"@
[void][D3]::SetProcessDPIAware()
$AE = [System.Windows.Automation.AutomationElement]
$p = Get-Process | Where-Object { $_.ProcessName -like 'CLO_Standalone*' } | Select-Object -First 1
$root = $AE::FromHandle($p.MainWindowHandle)
$cond = New-Object System.Windows.Automation.PropertyCondition($AE::NameProperty, "Plugins")
$menu = $root.FindFirst([System.Windows.Automation.TreeScope]::Descendants, $cond)
if (-not $menu) { "Plugins menu not found"; exit 1 }
$ec = $menu.GetCurrentPattern([System.Windows.Automation.ExpandCollapsePattern]::Pattern)
$ec.Expand()
Start-Sleep -Milliseconds 800
$items = $root.FindAll([System.Windows.Automation.TreeScope]::Descendants, [System.Windows.Automation.Condition]::TrueCondition)
$target = $null
foreach ($e in $items) { try { if ($e.Current.Name -match 'REST\s+Server\s+Execute') { $target = $e; break } } catch {} }
if (-not $target) {
  # menu popups may be top-level windows
  $desk = $AE::RootElement
  $items = $desk.FindAll([System.Windows.Automation.TreeScope]::Descendants, [System.Windows.Automation.Condition]::TrueCondition)
  foreach ($e in $items) { try { if ($e.Current.Name -match 'REST\s+Server\s+Execute') { $target = $e; break } } catch {} }
}
if (-not $target) { "REST Server Execute item not found"; exit 2 }
"found: '$($target.Current.Name)'"
$inv = $target.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern)
$inv.Invoke()
"invoked"
