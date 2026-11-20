"""E04 - grading flow: template .zprj -> group count -> ChangeGradingSizeInformation -> current index;
        plus graded-DXF import group count (lane AF recommended flow, findings/37)

STATUS: BLOCKED BY MISSING PLUGIN COMMANDS. The plugin REST surface has NO route for
  PatternAPI::GetGradingSizeGroupCount, GetGradingSizeListFromRuleTable, ChangeGradingSizeInformation
  (slot 146 by index / 147 by name), GetCurrentGradingSizeIndex or GetGradingPairedAvatar.
  The only grading code in the plugin is POST /avatar/grading-size, which calls the UNIMPLEMENTED thunk
  AddGradingSizeGroup (returns -1) - DO NOT USE IT. This script therefore fails fast (exit code 3) unless
  the proposed routes below have been added to the plugin and show up in /capabilities as
  has_grading_readback / has_grading_change.

PROPOSED PLUGIN ROUTES (to unblock; main-thread dispatch, all with group < count guards inside the plugin):
  GET  /grading/info        -> {group_count, current_size_index, size_list(group 0), paired_avatar_names[]}
  POST /grading/change-size -> {group, index}; plugin must refuse group >= GetGradingSizeGroupCount()
                               (lane AF off-by-one: group == count reads one past the end).
Extra source of truth that already exists: /patterns/count and /patterns/<i>/bbox to see that pieces were
  rebuilt at the new size (bbox changes).

HYPOTHESES
  H1: after opening a template .zprj authored with a Size Group, GetGradingSizeGroupCount() >= 1.
  H2: ChangeGradingSizeInformation(0, idx) returns true and GetCurrentGradingSizeIndex() == idx; patterns
      rebuilt (bbox changes); an undo step is pushed; no pairing avatar swap if template has none.
  H3: Simulate() is (or is not) required after the switch (compare bbox/GLB before and after Simulate).
  H4: ImportDXF of a graded ASTM DXF (GRADE RULE TABLE / NUMBER OF SIZES / SIZE LIST) yields group count >= 1.
      Mirra's writer emits no rule table so it should stay 0.

PRECONDITIONS (when unblocked): template .zprj with a Size Group, NO Pair-3D-Form entries (else the scene
  avatar may be swapped); a graded DXF for H4; supervised, watchdog running. Open the .zprj via
  ImportFile (only generic route is /import-avatar-avt method=import_file; type 0x1C; UNVERIFIED).

STEPS (when unblocked)
  1. new-project; ImportFile template.zprj. 2. GET /grading/info -> group_count (require >= 1 else stop).
  3. For idx in --sizes: POST /grading/change-size {group:0, index:idx} (script enforces 0 < group_count);
     then GET /grading/info (require current_size_index == idx) and record bbox of every pattern.
  4. Simulate(--sim-steps) once; record bbox again (H3). 5. new-project; /import-pattern graded DXF;
     GET /grading/info -> group_count (H4).

EXPECTED OUTCOME: H1/H2 true -> adopt lane AF flow (template-per-garment, switch size, then apply avatar,
  then Simulate). group_count 0 after template open -> template lacks a Size Group (author it in the GUI).
  change-size true but index unchanged -> trust GetCurrentGradingSizeIndex, not the bool.
RECORD: group_count, size labels, return bools, current index, bbox per size, paired avatar names, modals.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C  # noqa: E402


def main():
    ap = C.standard_args(__doc__)
    ap.add_argument("--zprj")
    ap.add_argument("--graded-dxf")
    ap.add_argument("--sizes", default="0,1,2")
    ap.add_argument("--sim-steps", type=int, default=30)
    args = ap.parse_args()
    # Fail fast, always (also in dry-run) so nobody mistakes a dry run for a runnable test.
    C.todo_missing_command(
        "PatternAPI::GetGradingSizeGroupCount / ChangeGradingSizeInformation(group, idx) / GetCurrentGradingSizeIndex",
        "GET /grading/info and POST /grading/change-size (see docstring)",
        "Only the broken AddGradingSizeGroup thunk route (/avatar/grading-size) exists; never call it.")
    # ---- below: reference implementation, reachable only after the TODO above is removed ----
    rec = C.Recorder("e04_grading_flow", args)  # noqa: unreachable until unblocked
    C.preflight(rec)
    C.run_cmd(rec, "new-project", "/new-project", {}, args.queue_timeout)
    C.run_cmd(rec, "open-template", "/import-avatar-avt", {"path": args.zprj.replace("\\", "/"), "method": "import_file"},
              args.queue_timeout)
    info = C.get("/grading/info")
    rec.step("grading/info", info=info)
    count = int(info.get("group_count", 0))
    if count < 1:
        rec.finish("NO_GROUP")
        return
    for idx in [int(s) for s in args.sizes.split(",")]:
        if not 0 < count:  # group 0 < count guard (lane AF off-by-one)
            break
        r = C.post("/grading/change-size", {"group": 0, "index": idx})
        after = C.get("/grading/info")
        rec.step(f"change-size[{idx}]", response=r, current=after.get("current_size_index"),
                 matches=after.get("current_size_index") == idx)
        n = C.pattern_count(rec, f"size{idx}")
        for i in range(max(n, 0)):
            rec.step(f"bbox[size{idx}][{i}]", bbox=C.get(f"/patterns/{i}/bbox"))
    C.run_cmd(rec, "simulate", "/simulate", {"steps": args.sim_steps}, 600)
    rec.finish("done")


if __name__ == "__main__":
    C.guarded(main)
