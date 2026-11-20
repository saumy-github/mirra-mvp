# 05 — Starting CLO and driving its Avatar Editor from the terminal

*Status: verified working on CLO 2026.1.224, Windows 11, screen 1920x1080 at 125% scaling*
*Compiled: 2026-10-15*

This lists what let an AI agent start CLO, start the REST plugin, open the Avatar Editor, apply an avatar-size file and save the editor's measurement CSV without anyone clicking. Everything below was tried live. The helper scripts used were kept in the session scratchpad, not in the repo; the snippets here are enough to rebuild them.

---

## 1. What works, step by step

| Goal | Method | Notes |
|---|---|---|
| Is CLO and the plugin alive? | `GET http://localhost:50505/health` | `status: ok`, `host_matches_sdk: true`, `plugin_built_at` tells which DLL is loaded. |
| Start CLO | `Start-Process "C:\Program Files\CLO Standalone OnlineAuth\CLO_Standalone_OnlineAuth_x64.exe"` | It is the "OnlineAuth" build; the session was already signed in, so no login window appeared. |
| Close CLO | `(Get-Process CLO_Standalone_OnlineAuth*).CloseMainWindow()` | Graceful. A "save changes?" prompt would appear instead of data being lost. |
| Dismiss the update prompt | Real mouse click on **Skip** (about real pixel 1007, 822) | Never click Update: 2026.1.310 broke the plugin before (the plugin is built for 2026.1.224). The prompt appears on every launch. |
| Start the plugin | UI Automation: open the **Plugins** menu, invoke the item matching `REST\s+Server\s+Execute` | The menu item's name has extra spaces, so an exact-name search fails. Run the invoke from a detached process, because the plugin then opens a modal message box that blocks the call. |
| Dismiss the plugin's message box | Real mouse click on **OK** (about real pixel 961, 569) | The box ("Starting REST server on http://localhost:50505 ...") is not in the UI Automation tree, and a posted Enter key did nothing. |
| Put an avatar in the scene | Plugin: `POST /new-project`, wait 4–5 s, then `POST /import-avatar-avt` with the unpatched `base-1.avt` | `NewProject` clears the previous avatar only when given the settle time. |
| Open the Avatar Editor | UI Automation: open the **Avatar** menu, invoke **Avatar Editor** | The item is greyed out when no avatar is loaded. Re-open the menu after loading an avatar, because a menu opened earlier keeps its old greyed state. |
| Open an `.avs` file | UI Automation: invoke the middle of the three small unnamed buttons at the top right of the Avatar Size panel | The three buttons are reset / open / save, at UI Automation rectangles x = 1482, 1502, 1522, y = 114. |
| Type into the Open File dialog | `WScript.Shell.SendKeys(<full path>)` then `{ENTER}` | The file-name box has focus when the dialog opens, so this works. |
| Save the measurement CSV | Invoke the right-hand button, then use mouse clicks in the dialog (see section 3) | The editor offers `Avatar Size File (*.avs)` or `Avatar Size (*.csv)` as the save type. |
| See the screen | PowerShell screenshot, then read the image | See section 2. |

---

## 2. Seeing the screen and clicking (DPI)

A PowerShell script that does not declare itself DPI-aware gets a virtualised screen. At 125% scaling that gave a **cropped** screenshot (the top-left 1536x864 of the real 1920x1080) and cursor positions that are scaled by 1.25. Both scripts must call `SetProcessDPIAware()` before anything else:

```powershell
Add-Type @"
using System; using System.Runtime.InteropServices;
public class DPI { [DllImport("user32.dll")] public static extern bool SetProcessDPIAware(); }
"@
[void][DPI]::SetProcessDPIAware()
```

After that, `System.Windows.Forms.SystemInformation.VirtualScreen` is 1920x1080, `Graphics.CopyFromScreen` captures the whole screen, and `SetCursorPos` plus `mouse_event` use real pixels. Screenshots are downscaled to 1600 wide before reading, so a point seen at (x, y) in the image is at (x / 0.8333, y / 0.8333) in real pixels.

A click is `SetCursorPos(x, y)`, a short sleep, then `mouse_event` left-down and left-up.

---

## 3. File dialogs

Windows file dialogs opened by CLO are owned windows. They did **not** appear as top-level windows in UI Automation, and the buttons and edit boxes inside were not found, so:

- **Open File**: the file-name box already has focus. Send the path with `SendKeys`, then `{ENTER}`.
- **Save File**: the layout moves between runs and the keyboard focus order is not reliable. In tests, the first Tab went to the address bar, and Alt+T (the "Save as type" access key) did not move focus. What worked each time:
  1. Take a screenshot.
  2. Click the "Save as type" combo, take another screenshot, click `Avatar Size (*.csv)` in the list that opens.
  3. Click the "File name" box, press Ctrl+A, send the full destination path, then `{ENTER}`.
  4. Check the file exists and starts with `Default Measurements`. If the type was wrong, an `.avs`-format file would be written under the `.csv` name.
- `SendKeys` treats `+ ^ % ~ ( ) { } [ ]` as special. The paths used here contain none of them.
- Note that keys sent while a menu is open, or while the editor is closed, go to CLO's main window and can trigger single-key shortcuts. Always confirm the editor is open (screenshot or the UI Automation tab list) before sending text.

---

## 4. Things that did not work, so they are not repeated

- Invoking a menu item while the target panel is already open, or invoking the editor with no avatar loaded: nothing happens, and later keystrokes go to the wrong place.
- Reading the two start-up pop-ups through UI Automation: they are not in the tree.
- Posting Enter to the plugin message box: no effect.
- `Start-Sleep -Milliseconds` is required in PowerShell 5.1. `Start-Sleep 500ms` is an error, and it aborted a key sequence halfway.
- `MI` is a built-in alias for `Move-Item`. A helper function with that name did not run. Give helper functions distinct names.
- Shell heredocs eat backslashes in some positions (`'\'` became an unterminated string). Write scripts to files, or avoid a trailing backslash inside quotes.
- Calling the plugin's `clear-avatars` is unsafe here: the plugin's tracked avatar count is never reset, so it tries to delete an index that does not exist, which can hang CLO.

---

## 5. What still needs a person

- Nothing in the CLO session above needed a person once CLO was running, but the **two start-up pop-ups** are handled by coordinate clicks, which depend on the pop-up appearing at the same place. A changed screen size or scaling would move them.
- The plugin's modal "Starting REST server" message could be removed in the plugin source so startup needs no click. That is a separate, not-yet-done change.
- Turning off CLO's automatic update check, if the application has such a setting, would remove the update prompt. It was not looked for.
