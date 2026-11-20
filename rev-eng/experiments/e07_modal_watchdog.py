"""E07 - modal-dialog watchdog probe (Windows only; ctypes; no plugin contact at all)

PURPOSE: lane X/AG/AB list modal boxes that block CLO's UI thread with no timeout: "No matching Avatar.",
  "The Softbody Option will be turned off ... proceed?", Divide Option, "Negative thread lengths",
  "This file format is not supported", "Loading a motion will delete...", "Added avatars for graded size will be
  replaced...", <10 GB disk prompt, GPU out-of-memory / stopped-with-error, E11000 assert box,
  "created in a lower version". This helper detects such windows and (optionally) dismisses them.

HYPOTHESES
  H1: modal boxes are top-level windows of the CLO process with class "#32770" (native) OR a Qt window
      (class like "Qt5QWindowIcon" / "Qt6...") that is a popup/owned window while the main window is DISABLED.
  H2: WM_CLOSE (or Esc) maps to the "Cancel"/"No" button (button id 2 assumed; unverified, lane AB), so closing
      is a safe "decline" for the resize prompts. Qt buttons are not native children, so BM_CLICK will not work.

DEFAULT IS DRY-RUN: enumerates and logs only. Dismissal requires BOTH `--no-dry-run` and an explicit match:
  `--dismiss-regex REGEX` (matched against title + class) or `--dismiss-any`. Action: `--action close` (WM_CLOSE,
  default) or `--action esc` (WM_KEYDOWN/UP VK_ESCAPE). It never clicks anything else.

PRECONDITIONS: Windows; CLO running; run it in a SECOND terminal beside the experiment; no admin needed for
  same-user processes. Process name match via --process (case-insensitive substring of exe name, default "clo").
  Uses only kernel32/user32 via ctypes; does not inject or hook anything into CLO.

STEPS
  1. Snapshot processes (Toolhelp) -> pids whose exe name contains --process.
  2. Every --interval s for --duration s: EnumWindows; for each top-level window of those pids record
     hwnd, class, title, visible, enabled, owner hwnd, style popup flag, rect.
  3. Flag a window as DIALOG-LIKE if class == "#32770", or (visible and owner != 0), or (WS_POPUP and visible and
     the main window is disabled). Also log when the largest visible non-dialog window is disabled
     (strong modal indicator).
  4. Append JSON lines to out/e07_watchdog_<ts>.jsonl. Text inside Qt message boxes is NOT readable from outside;
     record a screenshot by hand and the title; then note the button.

EXPECTED OUTCOME: while a known prompt is open, at least one DIALOG-LIKE row appears AND the main window is
  disabled (H1). After --no-dry-run close, the experiment's queue resumes (check /status) and the avatar is
  unchanged for resize prompts (H2). If nothing is detected while CLO is visibly blocked, classes/titles differ
  from H1: use the logged window list to refine matching.
RECORD: class names, titles, enabled flag of main window, whether close/esc cleared it, button semantics observed.
"""
import argparse
import ctypes
import json
import os
import re
import sys
import time
from ctypes import wintypes

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C  # noqa: E402

GWL_STYLE, GWL_HWNDPARENT = -16, -8
WS_POPUP = 0x80000000
WM_CLOSE, WM_KEYDOWN, WM_KEYUP, VK_ESCAPE = 0x0010, 0x0100, 0x0101, 0x1B
TH32CS_SNAPPROCESS = 0x2


class PROCESSENTRY32W(ctypes.Structure):
    _fields_ = [("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD), ("th32ProcessID", wintypes.DWORD),
                ("th32DefaultHeapID", ctypes.c_size_t), ("th32ModuleID", wintypes.DWORD),
                ("cntThreads", wintypes.DWORD), ("th32ParentProcessID", wintypes.DWORD),
                ("pcPriClassBase", wintypes.LONG), ("dwFlags", wintypes.DWORD), ("szExeFile", wintypes.WCHAR * 260)]


def find_pids(needle):
    k32 = ctypes.windll.kernel32
    k32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    snap = k32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    pe, pids = PROCESSENTRY32W(), {}
    pe.dwSize = ctypes.sizeof(pe)
    ok = k32.Process32FirstW(snap, ctypes.byref(pe))
    while ok:
        if needle.lower() in pe.szExeFile.lower():
            pids[pe.th32ProcessID] = pe.szExeFile
        ok = k32.Process32NextW(snap, ctypes.byref(pe))
    k32.CloseHandle(snap)
    return pids


def enum_windows(pids):
    u32 = ctypes.windll.user32
    rows = []
    CB = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    def cb(hwnd, _):
        pid = wintypes.DWORD()
        u32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value in pids:
            cls, title = ctypes.create_unicode_buffer(256), ctypes.create_unicode_buffer(512)
            u32.GetClassNameW(hwnd, cls, 256)
            u32.GetWindowTextW(hwnd, title, 512)
            rect = wintypes.RECT()
            u32.GetWindowRect(hwnd, ctypes.byref(rect))
            style = u32.GetWindowLongW(hwnd, GWL_STYLE) & 0xFFFFFFFF
            owner = u32.GetWindow(hwnd, 4)  # GW_OWNER
            rows.append({"hwnd": int(hwnd), "pid": pid.value, "class": cls.value, "title": title.value,
                         "visible": bool(u32.IsWindowVisible(hwnd)), "enabled": bool(u32.IsWindowEnabled(hwnd)),
                         "owner": int(owner or 0), "popup": bool(style & WS_POPUP),
                         "w": rect.right - rect.left, "h": rect.bottom - rect.top})
        return True

    u32.EnumWindows(CB(cb), 0)
    return rows


def classify(rows):
    vis = [r for r in rows if r["visible"] and r["w"] > 200 and r["h"] > 200 and not r["owner"]]
    main = max(vis, key=lambda r: r["w"] * r["h"], default=None)
    main_disabled = bool(main and not main["enabled"])
    for r in rows:
        r["dialog_like"] = bool(r["visible"] and (r["class"] == "#32770" or r["owner"] or
                                                  (r["popup"] and main_disabled and r is not main)))
    return main, main_disabled


def dismiss(r, action):
    u32 = ctypes.windll.user32
    if action == "close":
        u32.PostMessageW(r["hwnd"], WM_CLOSE, 0, 0)
    else:
        u32.PostMessageW(r["hwnd"], WM_KEYDOWN, VK_ESCAPE, 0)
        u32.PostMessageW(r["hwnd"], WM_KEYUP, VK_ESCAPE, 0)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--process", default="clo")
    ap.add_argument("--interval", type=float, default=1.0)
    ap.add_argument("--duration", type=float, default=300.0)
    ap.add_argument("--no-dry-run", action="store_true", help="allow dismissal (default is log only)")
    ap.add_argument("--dismiss-regex")
    ap.add_argument("--dismiss-any", action="store_true")
    ap.add_argument("--action", choices=["close", "esc"], default="close")
    ap.add_argument("--list-once", action="store_true", help="print one snapshot and exit")
    args = ap.parse_args()
    if os.name != "nt":
        raise SystemExit("Windows only")
    os.makedirs(C.OUT_DIR, exist_ok=True)
    log = os.path.join(C.OUT_DIR, f"e07_watchdog_{C.now_tag()}.jsonl")
    dry = not args.no_dry_run
    print(f"watchdog: process~'{args.process}' dry_run={dry} log={log}")
    rx = re.compile(args.dismiss_regex, re.I) if args.dismiss_regex else None
    t_end, seen = time.time() + args.duration, set()
    while time.time() < t_end:
        pids = find_pids(args.process)
        rows = enum_windows(pids) if pids else []
        main_w, main_disabled = classify(rows)
        dl = [r for r in rows if r["dialog_like"]]
        rec = {"t": time.strftime("%H:%M:%S"), "pids": pids, "windows": len(rows),
               "main_disabled": main_disabled, "dialogs": dl}
        key = tuple(sorted(r["hwnd"] for r in dl)) + (main_disabled,)
        if key not in seen or args.list_once:
            seen.add(key)
            print(json.dumps(rec)[:800])
            with open(log, "a", encoding="utf-8") as f:
                f.write(json.dumps(rec) + "\n")
        for r in dl:
            hit = args.dismiss_any or (rx and rx.search(r["title"] + " " + r["class"]))
            if hit and not dry:
                dismiss(r, args.action)
                msg = {"t": time.strftime("%H:%M:%S"), "dismissed": r, "action": args.action}
                print(json.dumps(msg))
                with open(log, "a", encoding="utf-8") as f:
                    f.write(json.dumps(msg) + "\n")
            elif hit:
                print(f"[dry-run] would {args.action}: {r['class']} '{r['title']}'")
        if args.list_once:
            break
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
