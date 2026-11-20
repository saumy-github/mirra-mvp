param([string]$Id = "", [string]$Value = "", [string]$Combo = "", [string]$Out = "")
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
Add-Type -AssemblyName System.Windows.Forms
Add-Type @"
using System; using System.Runtime.InteropServices;
public class D4 { [DllImport("user32.dll")] public static extern bool SetProcessDPIAware(); [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h); }
"@
[void][D4]::SetProcessDPIAware()
$AE = [System.Windows.Automation.AutomationElement]
$p = Get-Process | Where-Object { $_.ProcessName -like 'CLO_Standalone*' } | Select-Object -First 1
[void][D4]::SetForegroundWindow($p.MainWindowHandle)
$root = $AE::FromHandle($p.MainWindowHandle)
$cond = New-Object System.Windows.Automation.PropertyCondition($AE::ControlTypeProperty, [System.Windows.Automation.ControlType]::Spinner)
$spins = $root.FindAll([System.Windows.Automation.TreeScope]::Descendants, $cond)
function Short($s) { $i = $s.LastIndexOf('.'); if ($i -ge 0) { $s.Substring($i + 1) } else { $s } }
if ($Id -ne "" -and $Value -ne "") {
  foreach ($e in $spins) {
    $sid = Short $e.Current.AutomationId
    if ($sid -eq $Id) {
      $e.SetFocus()
      Start-Sleep -Milliseconds 250
      [System.Windows.Forms.SendKeys]::SendWait("^a")
      Start-Sleep -Milliseconds 150
      [System.Windows.Forms.SendKeys]::SendWait($Value)
      Start-Sleep -Milliseconds 150
      [System.Windows.Forms.SendKeys]::SendWait("{ENTER}")
      Start-Sleep -Milliseconds 1500
      break
    }
  }
}
# re-read all spinners
$spins = $root.FindAll([System.Windows.Automation.TreeScope]::Descendants, $cond)
$o = @{}
foreach ($e in $spins) {
  $vp = $null
  if ($e.TryGetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern, [ref]$vp)) { $o[(Short $e.Current.AutomationId)] = $vp.Current.Value }
}
$o.GetEnumerator() | Sort-Object Name | ForEach-Object { "{0}={1}" -f $_.Name, $_.Value }
