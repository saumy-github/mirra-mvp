# 012 Plan - Cleanup, Deletions, and Commit Hygiene

## Goal

After `011-plan.md` completes the working restructure and macOS parity work, this plan will clean up the plugin workspace by removing unnecessary files, dead code, generated artifacts, and things that should not be committed.

This is the cleanup plan.

---

## Scope

This plan should happen **after** the code structure and parity work are stable.

The focus here is:
- remove stale files
- remove unused code blocks
- remove hardcoded values that should not remain
- clean generated artifacts from source areas
- add proper `.gitignore` coverage where needed
- remove old docs/files that were intentionally kept during `011` until the new structure was verified

---

## Cleanup Targets

### Phase 1 - Delete unnecessary files

Delete high-confidence stale files such as:
- template/backup plugin source files
- stale duplicate CMake files
- old helper scripts that are no longer part of the active flow
- duplicated docs once the new root docs are confirmed complete
- any old platform-folder files that became unnecessary after the new `shared/`, `windows/`, and `mac/` structure is verified

### Phase 2 - Remove unnecessary code blocks

Clean up dead or misleading code blocks, including:
- unused helper functions
- unused includes
- stale comments
- outdated status/help strings
- any code that no longer matches the new structure

### Phase 3 - Remove hardcoded machine-specific lines

After the new structure is working:
- remove remaining hardcoded paths
- remove stale hardcoded build/install messages
- remove hardcoded references that should now come from shared config or metadata
- remove any hardcoded values that survived the `011` move only temporarily for safety

### Phase 4 - Handle generated folders and build artifacts

This is where build folders are handled.

Examples:
- committed build output folders
- generated cache folders
- temporary build artifacts

Important:
- do **not** delete these in `011-plan.md`
- handle them here, after the working restructure is finished

This explicitly includes any existing generated build folders that were intentionally left in place during `011`.

### Phase 5 - `.gitignore` and commit hygiene

Add or fix ignore rules for things that should not be committed, such as:
- generated build folders
- cache folders
- temporary outputs
- local machine artifacts
- other non-source generated files

### Phase 6 - Final doc cleanup

After deleting/moving stale files:
- update docs so they only reference active files
- remove references to deleted legacy files
- keep repo docs aligned with the new `clo_workspace/` structure

Also:
- remove or archive docs that were marked for later cleanup during `011`
- double-check before deleting anything important

---

## Important Ordering

### First do `011-plan.md`

That plan makes sure:
- structure is correct
- imports/includes/build paths still work
- macOS plugin is brought up to date
- root env/docs/build/script flow is in place

### Then do `012-plan.md`

Only after the code works in the new structure should we:
- delete stale files
- delete generated artifacts
- remove dead code
- add ignore rules for non-source files

This order reduces the risk of deleting something before the new structure is confirmed working.

---

## Notes

- This plan is allowed to include deletions.
- This plan is allowed to add `.gitignore` coverage.
- This plan is where build folders are finally handled.
- This plan should be conservative until `011` is verified complete.
- This plan is where files/docs intentionally kept for safety during `011` should finally be removed if no longer needed.
