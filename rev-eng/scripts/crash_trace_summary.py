#!/usr/bin/env python3
"""Stream-summarise clo_workspace/logs/plugin_crash_trace.log (stdlib only, read-only).
Usage: python scripts/crash_trace_summary.py [path]
Lines: [HH:MM:SS] [tid=N] text   (local time, no date). Midnight wrap handled for durations."""
import re, sys, collections
P = sys.argv[1] if len(sys.argv) > 1 else r"C:\D-drive-data\mirra-mvp\clo_workspace\logs\plugin_crash_trace.log"
LINE = re.compile(r"^\[(\d\d):(\d\d):(\d\d)\] \[tid=(\d+)\] (.*)$")
BEG = re.compile(r"^BEGIN (\S+)(.*)$"); END = re.compile(r"^END\s+(\S+)\s*(.*)$")
def secs(m): return int(m.group(1))*3600+int(m.group(2))*60+int(m.group(3))
nb = ne = nl = 0
mix = collections.Counter(); pending = {}  # tid -> list of (line, ts, cmd, args)
unmatched = []; markers = []; sessions = []
cur = None; pre = dict(warn=False, sdk=None)  # SDK/warn lines are logged just BEFORE the 'discovered' line
def new_session(ln, ts, tid, txt):
    global cur
    close_pending("session boundary")
    cur = dict(start_line=ln, start_ts=ts, tid=tid, marker=txt[:60], cmds=[], unmatched=[], warn=pre['warn'],
               end_line=ln, end_ts=ts, ended_clean_marker=0, last_tick=None, sdk=pre['sdk'], wrap=0)
    pre['warn']=False; pre['sdk']=None
    sessions.append(cur)
def close_pending(why):
    for tid, st in list(pending.items()):
        for (ln, ts, cmd, args) in st:
            rec = (ln, tid, cmd, why, args[:90]); unmatched.append(rec)
            (cur["unmatched"].append(rec) if cur else None)
    pending.clear()
prev_ts = None; day = 0
with open(P, "r", encoding="utf-8", errors="replace") as f:
    for ln, raw in enumerate(f, 1):
        nl = ln
        m = LINE.match(raw.rstrip("\n"))
        if not m: continue
        ts = secs(m); tid = int(m.group(4)); txt = m.group(5)
        if cur is not None:
            if cur["end_ts"] is not None and ts < cur["end_ts"] - 3600: cur["wrap"] += 1
            cur["end_line"] = ln; cur["end_ts"] = ts
        if txt.startswith("QueueDrainTimer heartbeat"):
            t = re.search(r"tick=(\d+)", txt)
            if cur and t: cur["last_tick"] = int(t.group(1))
            continue
        if "g_cloMainWnd discovered" in txt:
            markers.append((ln, m.group(1)+":"+m.group(2)+":"+m.group(3), tid, "discovered"))
            new_session(ln, ts, tid, txt); continue
        if "host CLO version differs" in txt:
            markers.append((ln, m.group(0)[1:9], tid, "VERSION-DIFFERS")); 
            pre['warn'] = True
            continue
        if "built against SDK folder" in txt:
            markers.append((ln, m.group(0)[1:9], tid, txt.split("built against")[1].strip()[:110]))
            pre['sdk'] = txt.split("built against SDK folder")[1].strip()
            continue
        if "ProcessCommandQueue() returned normally" in txt and cur: cur["ended_clean_marker"] += 1
        b = BEG.match(txt)
        if b:
            nb += 1; mix[b.group(1)] += 1
            st = pending.setdefault(tid, [])
            if st:  # earlier BEGIN on same tid never ENDed
                for (l0, t0, c0, a0) in st:
                    rec = (l0, tid, c0, "next BEGIN on same tid", a0[:90]); unmatched.append(rec)
                    if cur: cur["unmatched"].append(rec)
                st.clear()
            st.append((ln, ts, b.group(1), b.group(2).strip()))
            continue
        e = END.match(txt)
        if e:
            ne += 1; st = pending.get(tid)
            if st and st[-1][2] == e.group(1):
                l0, t0, c0, a0 = st.pop()
                if cur:
                    d = (ts - t0) % 86400
                    cur["cmds"].append((l0, c0, d, e.group(2)[:40]))
                if not st: pending.pop(tid, None)
            else:
                mix["(END without BEGIN)"] += 1
close_pending("EOF (no END yet; may be in flight if CLO still running)")
print(f"file={P}\nlines={nl} BEGIN={nb} END={ne} BEGIN-END={nb-ne}")
print("\nCommand mix:"); [print(f"  {c:8d} {k}") for k, c in mix.most_common()]
print(f"\nUnmatched BEGINs ({len(unmatched)}):")
for ln, tid, cmd, why, a in unmatched: print(f"  line {ln} tid={tid} {cmd} [{why}] {a}")
print("\nMarkers (line, time, tid, kind):")
for mk in markers: print("  ", *mk)
print(f"\nSessions: {len(sessions)}")
for i, s in enumerate(sessions):
    dur = ((s['end_ts'] - s['start_ts']) % 86400) if s['end_ts'] is not None else 0
    print(f"  #{i} lines {s['start_line']}-{s['end_line']} tid={s['tid']} cmds={len(s['cmds'])} unmatched={len(s['unmatched'])} versionWarn={s['warn']} sdk={s['sdk']} span~{dur//3600}h{dur%3600//60:02d}m")
s = sessions[-1]
print("\nLAST SESSION detail:")
print(f"  start line {s['start_line']} @ {s['start_ts']//3600:02d}:{s['start_ts']%3600//60:02d} tid={s['tid']}; last line {s['end_line']} @ {s['end_ts']//3600:02d}:{s['end_ts']%3600//60:02d}; last heartbeat tick={s['last_tick']}")
print(f"  sdk={s['sdk']}  versionDiffersWarning={s['warn']}  unmatched={len(s['unmatched'])}  'returned normally' lines={s['ended_clean_marker']}")
c = collections.Counter(x[1] for x in s["cmds"]); print("  commands:", dict(c))
for k in c:
    ds = [x[2] for x in s["cmds"] if x[1] == k]
    print(f"    {k}: n={len(ds)} min={min(ds)}s max={max(ds)}s avg={sum(ds)/len(ds):.1f}s")
bad = [x for x in s["cmds"] if "success=false" in x[3]]
print(f"  success=false ENDs: {len(bad)}", [(x[0], x[1]) for x in bad[:15]])
