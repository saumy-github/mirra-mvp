"""Smoke test against the real backend + mirratest DB, scoped to the flows
that don't need CLO3D: guest session → measurements → catalog browse →
analytics event → account deletion (cascade).

Avatar generation and try-on rendering always run the real CLO3D pipeline
now (no demo/live mode) — they're covered by CLI runs
(clo_avatar_generation/run_avatar.py, clo_vto/run_clo_vto.py) and manual
live tests against the native worker instead of this smoke test. See
.agent/website-launch/22-remove-demo-live-mode-and-upload-split.md.

Creates one uniquely-named guest, deletes everything it touched. Safe to
rerun. Exit code 0 = all good.

Run from website/backend:
    ../../.venv/Scripts/python.exe scripts/smoke_e2e.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient  # noqa: E402
from pymongo import MongoClient  # noqa: E402

from src.config import get_settings  # noqa: E402
from src.main import app  # noqa: E402

settings = get_settings()
sync_db = MongoClient(settings.mongodb_uri)[settings.database_name]

checks = []


def check(name, ok, detail=""):
    checks.append((name, ok))
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail and not ok else ""))


user_id = None
with TestClient(app) as c:
    check("health", c.get("/api/v1/health").json()["database"] == "connected")

    # guest all the way through — the pilot's lowest-friction path
    r = c.post("/api/v1/auth/guest")
    user_id = r.json()["account"]["userId"]
    H = {"Authorization": f"Bearer {r.json()['accessToken']}"}
    check("guest session", r.status_code == 201)

    r = c.put("/api/v1/user-measurements/me", headers=H, json={
        "gender": "male", "height_cm": 178.5, "weight_kg": 75.2, "chest_circumference_cm": 100.0})
    check("measurements submitted", r.status_code == 200)

    garments = c.get("/api/v1/catalog/garments").json()
    check("catalog browsable", garments["total"] >= 10)

    r = c.post("/api/v1/analytics/events", headers=H,
               json={"event": "page_view", "authenticated": True, "environment": "smoke"})
    check("analytics ingested", r.status_code == 200)

    r = c.delete("/api/v1/users/me", headers=H)
    check("account deleted", r.status_code == 200)

leftovers = sum(
    sync_db[col].count_documents({"user_id": user_id})
    for col in ("user_measurements", "refresh_tokens", "avatar_jobs", "avatar_profiles",
                "tryon_sessions", "tryon_renders", "signature_looks")
) + sync_db["users"].count_documents({"_id": user_id})
check("cascade left nothing behind", leftovers == 0, f"leftover docs: {leftovers}")
sync_db["analytics_events"].delete_many({"user_id": user_id})

failed = [n for n, ok in checks if not ok]
print(f"\n{len(checks) - len(failed)}/{len(checks)} checks passed" + (f"  FAILED: {failed}" if failed else ""))
sys.exit(1 if failed else 0)
