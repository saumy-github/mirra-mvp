param([string]$Action, [string]$Id = "", [string]$Value = "")
# Drives CLO's Avatar Editor through UI Automation.
#   open_editor : Avatar menu -> Avatar Editor (only if it is not already open)
#   read        : print every spinner (id=value) of the editor
#   set         : type $Value into the spinner whose AutomationId ends with $Id, press Enter, then print all spinners
#   click       : invoke the button whose AutomationId ends with $Id
#   keys        : send the keys in $Value (SendKeys syntax) to CLO
#   combo       : select the item named $Value in the combo box whose AutomationId ends with $Id
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
Add-Type -AssemblyName System.Windows.Forms
Add-Type @"
using System; using System.Runtime.InteropServices;
public class D5 { [DllImport("user32.dll")] public static extern bool SetProcessDPIAware(); [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h); }
"@
[void][D5]::SetProcessDPIAware()
$AE = [System.Windows.Automation.AutomationElement]
$TS = [System.Windows.Automation.TreeScope]
$p = Get-Process | Where-Object { $_.ProcessName -like 'CLO_Standalone*' } | Select-Object -First 1
[void][D5]::SetForegroundWindow($p.MainWindowHandle)
$root = $AE::FromHandle($p.MainWindowHandle)
function Short($s) { $i = $s.LastIndexOf('.'); if ($i -ge 0) { $s.Substring($i + 1) } else { $s } }
function FindById($ctype, $suffix) {
  $cond = New-Object System.Windows.Automation.PropertyCondition($AE::ControlTypeProperty, $ctype)
  foreach ($e in $root.FindAll($TS::Descendants, $cond)) { if ((Short $e.Current.AutomationId) -eq $suffix) { return $e } }
  return $null
}
function PrintSpinners() {
  $cond = New-Object System.Windows.Automation.PropertyCondition($AE::ControlTypeProperty, [System.Windows.Automation.ControlType]::Spinner)
  $o = @{}
  foreach ($e in $root.FindAll($TS::Descendants, $cond)) {
    $vp = $null
    if ($e.TryGetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern, [ref]$vp)) { $o[(Short $e.Current.AutomationId)] = $vp.Current.Value }
  }
  $o.GetEnumerator() | Sort-Object Name | ForEach-Object { "{0}={1}" -f $_.Name, $_.Value }
}
switch ($Action) {
  "open_editor" {
    $already = FindById ([System.Windows.Automation.ControlType]::Spinner) "spinBoxWaistCircumMeasureID006"
    if ($already) { "editor already open"; break }
    $cond = New-Object System.Windows.Automation.PropertyCondition($AE::NameProperty, "Avatar")
    $menu = $root.FindFirst($TS::Descendants, $cond)
    $menu.GetCurrentPattern([System.Windows.Automation.ExpandCollapsePattern]::Pattern).Expand()
    Start-Sleep -Milliseconds 800
    $desk = $AE::RootElement
    $target = $null
    foreach ($scope in @($root, $desk)) {
      foreach ($e in $scope.FindAll($TS::Descendants, [System.Windows.Automation.Condition]::TrueCondition)) { try { if ($e.Current.Name -match '^\s*Avatar Editor\s*$' -and $e.Current.ControlType.ProgrammaticName -eq 'ControlType.MenuItem') { $target = $e; break } } catch {} }
      if ($target) { break }
    }
    if (-not $target) { "Avatar Editor menu item not found"; break }
    $target.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern).Invoke()
    Start-Sleep -Milliseconds 1500
    "opened"
  }
  "read" { PrintSpinners }
  "set" {
    $e = FindById ([System.Windows.Automation.ControlType]::Spinner) $Id
    if (-not $e) { "spinner not found: $Id"; break }
    $e.SetFocus(); Start-Sleep -Milliseconds 200
    [System.Windows.Forms.SendKeys]::SendWait("^a"); Start-Sleep -Milliseconds 100
    [System.Windows.Forms.SendKeys]::SendWait($Value); Start-Sleep -Milliseconds 100
    [System.Windows.Forms.SendKeys]::SendWait("{ENTER}"); Start-Sleep -Milliseconds 1200
    PrintSpinners
  }
  "click" {
    $e = FindById ([System.Windows.Automation.ControlType]::Button) $Id
    if (-not $e) { "button not found: $Id"; break }
    $e.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern).Invoke(); Start-Sleep -Milliseconds 800; "clicked $Id"
  }
  "keys" { [System.Windows.Forms.SendKeys]::SendWait($Value); Start-Sleep -Milliseconds 800; "sent $Value" }
  "combo" {
    $e = FindById ([System.Windows.Automation.ControlType]::ComboBox) $Id
    if (-not $e) { "combo not found: $Id"; break }
    $e.GetCurrentPattern([System.Windows.Automation.ExpandCollapsePattern]::Pattern).Expand(); Start-Sleep -Milliseconds 600
    $item = $null
    foreach ($x in $e.FindAll($TS::Descendants, [System.Windows.Automation.Condition]::TrueCondition)) { if ($x.Current.Name -eq $Value) { $item = $x; break } }
    if (-not $item) { foreach ($x in $AE::RootElement.FindAll($TS::Descendants, [System.Windows.Automation.Condition]::TrueCondition)) { try { if ($x.Current.Name -eq $Value -and $x.Current.ControlType.ProgrammaticName -match 'ListItem') { $item = $x; break } } catch {} } }
    if ($item) { $item.GetCurrentPattern([System.Windows.Automation.SelectionItemPattern]::Pattern).Select(); Start-Sleep -Milliseconds 800; "selected $Value" } else { "item not found: $Value" }
  }
}
if ($Action -eq "combos") {
  $cond = New-Object System.Windows.Automation.PropertyCondition($AE::ControlTypeProperty, [System.Windows.Automation.ControlType]::ComboBox)
  foreach ($e in $root.FindAll($TS::Descendants, $cond)) {
    $vp = $null; $v = ""
    if ($e.TryGetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern, [ref]$vp)) { $v = $vp.Current.Value }
    "{0}={1}" -f (Short $e.Current.AutomationId), $v
  }
}
if ($Action -eq "focus") {
  $cond = New-Object System.Windows.Automation.PropertyCondition($AE::ControlTypeProperty, [System.Windows.Automation.ControlType]::ComboBox)
  foreach ($e in $root.FindAll($TS::Descendants, $cond)) { if ((Short $e.Current.AutomationId) -eq $Id) { $e.SetFocus(); Start-Sleep -Milliseconds 300; "focused $Id" } }
}
Add-Type @"
using System; using System.Runtime.InteropServices;
public class C9 {
  [DllImport("user32.dll")] public static extern bool SetCursorPos(int x, int y);
  [DllImport("user32.dll")] public static extern void mouse_event(uint f, uint dx, uint dy, uint d, UIntPtr e);
}
"@
if ($Action -eq "setmany") {
  # $Value = "spinnerId=number;spinnerId=number;..."  (fast: short pauses)
  foreach ($pair in $Value.Split(';')) {
    $kv = $pair.Split('=')
    $e = FindById ([System.Windows.Automation.ControlType]::Spinner) $kv[0]
    if (-not $e) { "missing $($kv[0])"; continue }
    $e.SetFocus(); Start-Sleep -Milliseconds 120
    [System.Windows.Forms.SendKeys]::SendWait("^a"); Start-Sleep -Milliseconds 60
    [System.Windows.Forms.SendKeys]::SendWait($kv[1]); Start-Sleep -Milliseconds 60
    [System.Windows.Forms.SendKeys]::SendWait("{ENTER}"); Start-Sleep -Milliseconds 450
  }
  PrintSpinners
}
if ($Action -eq "driver_weight") {
  # open the Width driver popup, go to the first entry, commit it, then step down $Value times to reach Weight
  [void][C9]::SetCursorPos(948, 204); Start-Sleep -Milliseconds 150
  [C9]::mouse_event(2, 0, 0, 0, [UIntPtr]::Zero); Start-Sleep -Milliseconds 60; [C9]::mouse_event(4, 0, 0, 0, [UIntPtr]::Zero); Start-Sleep -Milliseconds 500
  foreach ($k in @("{UP}", "{UP}", "{UP}", "{ENTER}")) { [System.Windows.Forms.SendKeys]::SendWait($k); Start-Sleep -Milliseconds 250 }
  for ($i = 0; $i -lt [int]$Value; $i++) { [System.Windows.Forms.SendKeys]::SendWait("{DOWN}"); Start-Sleep -Milliseconds 450 }
  Start-Sleep -Milliseconds 300
  PrintSpinners | Select-String "spinBoxWidthCircum"
}
