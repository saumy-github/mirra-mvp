Moved orchestration and CLO automation step modules into vto/ for Phase 4.

Files moved:
- vto/clo_automation_client.py (from clo_workspace/plugins)
- vto/mirra_pattern_importer.py (from clo_workspace/plugins)
- vto/discover_seam_indices.py (from clo_workspace/plugins)
- vto/clo_automation_steps/ (entire package moved)

Remaining in clo_workspace/plugins (intended to keep):
- clo_rest_client.py (REST connection helper - KEEP)
- clo_api_discovery.py (KEEP)
- build scripts and RestPlugin C++ sources (KEEP)

Suggested deletions / retirements after manual verification and Gate 3:
- Any remaining orchestration helpers or duplicated scripts that reference the moved files (search for imports pointing to clo_workspace.plugins.clo_automation_* and update)
- Old examples or README sections that reference the previous `clo_workspace/plugins` orchestration entrypoints (update to point to `vto/`)

Immediate next steps (follow-up work):
1. Implement `vto/run_vto.py` as the canonical Step 3 runner (interactive selection + confirmation).
2. Update internal imports in moved modules if they assume package path `clo_workspace.plugins` (most imports are relative and should still work; run a quick import smoke test).
3. Run project tests or a small import script to validate moved modules import correctly.
4. Update docs/README to point users at `vto/run_vto.py` once created.
5. After Gate 3 manual verification, remove any legacy orchestration files still under `clo_workspace` that are now obsolete.

Notes on comments and content preservation:
- Files were moved using filesystem move operations; file contents (including comments) were preserved unchanged.
