"""E01 - .avs route: which avatars does ImportFile(.avs) resize? (tests lane AL's qsAvatarID matching)

HYPOTHESIS (lane AL, findings/40_avs_avatar_targeting.md, supersedes the AG/AB "every avatar" reading):
  ImportFile(.avs) resizes only the TARGET SET = the manager's CURRENT avatar (mgr+0x98) if one exists.
  qsAvatarID is only a template-category match (Male/Female/Boy/Girl/PreSchool/Baby), NOT a per-avatar
  selector. With no current avatar it searches avatars with flag +0x990 and matching category:
  0 matches -> modal "No matching Avatar."; 1 -> used; >=2 -> modal avatar chooser. If any target fails the
  category check nothing is resized and "No matching Avatar." shows.
  Test: with two avatars loaded, ONLY the current one changes; record which index is current.
  Falsifiers: both change (old H-ALL), or the non-current/qsAvatarID-matching one changes.

PRECONDITIONS
  * One supervised CLO instance, plugin built against the installed CLO (health.host_matches_sdk true).
  * Run e07_modal_watchdog.py in a second terminal (dry-run is fine) so you can see a modal box.
  * Two DIFFERENT stock .avt files (--avt-a, --avt-b; e.g. male + female, or two templates) with
    Softbody/Divide off (all 5 repo samples are off; otherwise a resize prompt appears).
  * An .avs for avatar A (--avs). Build one with clo_avatar_generation/avatar_runtime/avs_patch.py
    OR use the stock CLO_Male_Default.avs. Optional --avs-b for the symmetric case.
  * Work on copies; back up the CLO project/settings (README "Safety").

STEPS (exactly)
  1. preflight: /health, /capabilities, idle queue.
  2. POST /clear-avatars; read /avatars/state (expect 0 avatars).
  3. Import avatar A via /import-avatar-avt (method per --load-method, default import_avatar); read state.
  4. Import avatar B the same way (B is loaded LAST, so B is expected to be CURRENT; record load order) (note: ImportAvatar may REPLACE rather than append; the state read
     after step 4 tells you; if count != 2 retry with --load-method import_file).
  5. Read /avatars/state: property snapshot BEFORE for both avatars (GetAvatarProperties).
  6. /import-avatar-avt {method: import_file, path: <avs>}  (ImportFile slot 2; its bool is NOT a success signal).
  7. Read /avatars/state AFTER; diff property dicts per avatar and print which changed.
  8. Optional --avs-b: repeat 6-7 with the second .avs.

READ-BACK LIMITATION (TODO, fails fast if --need-measurements): the plugin has no route for
  GetAvatarMeasurements(i) (full circumferences). Proposed: GET /avatars/<i>/measurements -> dispatchSyncRead
  "read-avatar-measurements" calling UTILITY_API->GetAvatarMeasurements(i). Without it this script uses
  GetAvatarProperties (via /avatars/state), which lane D says carries the raw resizing floats / height,
  so a changed property set is still a valid resize signal. Optional extra: --export-glb exports a GLB
  after step 7 (whole scene, both avatars) for mesh-level confirmation.

CURRENT-AVATAR NOTE: the plugin has no route returning or setting the current avatar (TODO: proposed
  GET /avatars/current -> index of mgr+0x98; no setter either, the GUI selection is the only way). This script
  infers it: the avatar whose properties changed IS the current one. Compare with the load order and
  /avatars/state index/name order, which are printed. Run the scenario matrix (separate runs, fresh scene):
    S1 A,B same category (e.g. two male), avs male      -> expect only current (last loaded?) changes
    S2 A male, B female, avs male (current = B female)  -> expect NO change + modal "No matching Avatar." (timeout)
    S3 after S1, select the other avatar in the GUI by hand, re-run only the .avs step (--skip-load) -> the other changes
EXPECTED OUTCOME
  * exactly one avatar's properties change                 -> AL confirmed; note index == last-loaded or not.
  * both change                                            -> AL wrong; per-avatar loop path (0x50fda06) is live.
  * none change, no modal                                  -> .avs silent skip (category mismatch handled silently) or the GUI route
                                                              (App+0x50 method 74); record qsAvatarID and avatar categories.
  * modal / timeout                                        -> record text ("No matching Avatar.", avatar chooser, Softbody/Divide,
                                                              "created in a lower version"); dismiss by hand.
RECORD: avatar names/ids from /avatars/state, the .avs qsAvatarID (printed by this script via avs_grammar),
  per-avatar changed keys, every queued result message, any modal text, CLO still responsive (/health).
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C  # noqa: E402


def avs_id(path):
    try:
        g = C.avs_grammar()
        for name, _t, val in g.parse(open(path, "rb").read()):
            if name in ("qsAvatarID", "qsAvatarIDUTF8"):
                return name, val[1].decode("utf-8", "replace") if isinstance(val, tuple) else str(val)
    except Exception as e:  # noqa: BLE001
        return "error", f"{type(e).__name__}: {e}"
    return None, None


def props_by_avatar(state):
    return {a.get("index"): {"name": a.get("name"), "props": a.get("properties", {})}
            for a in state.get("avatars", [])}


def diff_props(before, after):
    out = {}
    for idx, b in before.items():
        a = after.get(idx, {})
        keys = set(b["props"]) | set(a.get("props", {}))
        ch = {k: [b["props"].get(k), a.get("props", {}).get(k)] for k in sorted(keys)
              if b["props"].get(k) != a.get("props", {}).get(k)}
        out[idx] = {"name": b["name"], "changed_count": len(ch), "changed": dict(list(ch.items())[:40])}
    return out


def main():
    ap = C.standard_args(__doc__)
    ap.add_argument("--avt-a")
    ap.add_argument("--avt-b")
    ap.add_argument("--avs", required=True)
    ap.add_argument("--avs-b")
    ap.add_argument("--load-method", default="import_avatar", choices=["import_avatar", "import_file"])
    ap.add_argument("--need-measurements", action="store_true",
                    help="fail fast: GetAvatarMeasurements has no plugin route (see docstring)")
    ap.add_argument("--skip-load", action="store_true",
                    help="S3: keep the existing scene (no clear/import); only snapshot, ImportFile .avs, diff")
    ap.add_argument("--export-glb", help="optional output .glb path after the resize")
    args = ap.parse_args()
    if args.need_measurements:
        C.todo_missing_command("GetAvatarMeasurements(i)", "GET /avatars/<i>/measurements",
                               "Needed to read full circumferences per avatar.")
    if not args.skip_load and not (args.avt_a and args.avt_b):
        raise SystemExit("--avt-a and --avt-b required unless --skip-load")
    C.plan_only(args, [
        "preflight health/capabilities/status", "POST /clear-avatars",
        f"import {args.avt_a} then {args.avt_b} (method {args.load_method})",
        "snapshot /avatars/state (BEFORE)", f"ImportFile {args.avs} via /import-avatar-avt method=import_file",
        "snapshot /avatars/state (AFTER) and diff per avatar", "optional second .avs / GLB export"])
    rec = C.Recorder("e01_avs_single_avatar", args)
    C.preflight(rec)
    rec.step("avs.qsAvatarID", avs=args.avs, id=avs_id(args.avs),
             avs_b=(avs_id(args.avs_b) if args.avs_b else None))
    if not args.skip_load:
        C.run_cmd(rec, "clear-avatars", "/clear-avatars", {"max_index": 7}, args.queue_timeout)
        C.avatar_state(rec, "after-clear")
    for tag, p in (() if args.skip_load else (("A", args.avt_a), ("B", args.avt_b))):
        pl = {"path": p.replace("\\", "/")}
        if args.load_method != "import_avatar":
            pl["method"] = args.load_method
        C.run_cmd(rec, f"import-avt-{tag}", "/import-avatar-avt", pl, args.queue_timeout)
        C.avatar_state(rec, f"after-load-{tag}")
    before = C.avatar_state(rec, "BEFORE-avs")
    if before.get("avatar_count") != 2:
        rec.note(f"avatar_count={before.get('avatar_count')} (expected 2): the single-vs-all question is not testable; "
                 "retry with --load-method import_file.")
    bmap = props_by_avatar(before)
    for tag, avs in (("avs", args.avs), ("avs-b", args.avs_b)):
        if not avs:
            continue
        C.run_cmd(rec, f"ImportFile-{tag}", "/import-avatar-avt",
                  {"path": avs.replace("\\", "/"), "method": "import_file"}, args.queue_timeout)
        after = C.avatar_state(rec, f"AFTER-{tag}")
        d = diff_props(bmap, props_by_avatar(after))
        rec.step(f"diff[{tag}]", per_avatar=d)
        changed = [i for i, v in d.items() if v["changed_count"]]
        verdict = ("AL-CONFIRMED: only avatar index %s changed (that is the CURRENT avatar; last loaded index=%s)"
                   % (changed, len(d) - 1) if len(changed) == 1 else
                   "AL-FALSIFIED: all changed" if len(changed) > 1 and len(changed) == len(d) else
                   "NO CHANGE" if not changed else "PARTIAL %s" % changed)
        rec.note(f"{tag}: {verdict}")
        bmap = props_by_avatar(after)
    if args.export_glb:
        C.export_scene(rec, "export-glb", args.export_glb)
    rec.step("health-after", health=C.get("/health", timeout=10).get("status"))
    rec.finish("see notes")


if __name__ == "__main__":
    C.guarded(main)
