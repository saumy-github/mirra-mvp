"""Full-pilot-flow smoke test against the real backend + mirratest DB.

Covers the whole journey end-to-end in one client:
guest session → measurements → QR capture (pair/consent/upload/complete) →
demo avatar job → catalog browse → try-on demo render → hanger restore →
signature look → analytics event → account deletion (cascade incl. photo).

Creates one uniquely-named guest, deletes everything it touched. Safe to
rerun. Exit code 0 = all good.

Run from website/backend:
    ../../.venv/Scripts/python.exe scripts/smoke_e2e.py
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient  # noqa: E402
from pymongo import MongoClient  # noqa: E402

from src.config import get_settings  # noqa: E402
from src.main import app  # noqa: E402

settings = get_settings()
sync_db = MongoClient(settings.mongodb_uri)[settings.database_name]

PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000d49444154789c626001000000ffff03000006000557bfabd40000000049454e44ae426082"
)

checks = []


def check(name, ok, detail=""):
    checks.append((name, ok))
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail and not ok else ""))


def wait_for(fn, timeout=15):
    deadline = time.time() + timeout
    while time.time() < deadline:
        value = fn()
        if value:
            return value
        time.sleep(1)
    return None


user_id = None
with TestClient(app) as c:
    check("health", c.get("/api/v1/health").json()["database"] == "connected")

    # guest all the way through — the pilot's lowest-friction path
    r = c.post("/api/v1/auth/guest")
    user_id = r.json()["account"]["userId"]
    H = {"Authorization": f"Bearer {r.json()['accessToken']}"}
    check("guest session", r.status_code == 201)

    r = c.put("/api/v1/measurements/me", headers=H, json={
        "gender": "male", "height_cm": 178.5, "weight_kg": 75.2, "chest_circumference_cm": 100.0})
    check("measurements submitted", r.status_code == 200)

    s = c.post("/api/v1/capture-sessions", headers=H).json()["session"]
    token = s["token"]
    c.post(f"/api/v1/capture-sessions/by-token/{token}/pair")
    c.post(f"/api/v1/capture-sessions/by-token/{token}/consent")
    c.post(f"/api/v1/capture-sessions/by-token/{token}/uploads",
           files={"file": ("photo.png", PNG, "image/png")})
    r = c.post(f"/api/v1/capture-sessions/by-token/{token}/complete")
    job_id = r.json()["session"]["avatarJobId"]
    check("capture completed, job enqueued", r.status_code == 200 and bool(job_id))

    ready = wait_for(lambda: c.get(f"/api/v1/avatars/jobs/{job_id}", headers=H).json()["job"]["state"] == "ready")
    check("avatar job ready (demo)", bool(ready))
    check("avatar profile exists", c.get("/api/v1/avatars/profile", headers=H).json()["profile"] is not None)

    garments = c.get("/api/v1/catalog/garments").json()
    check("catalog browsable", garments["total"] >= 10)
    size_id = garments["items"][0]["sizeId"]

    sess = c.post("/api/v1/tryon/sessions", headers=H).json()["session"]["sessionId"]
    render = c.post(f"/api/v1/tryon/sessions/{sess}/renders", headers=H,
                    json={"sizeId": size_id}).json()["render"]["renderId"]
    ready = wait_for(lambda: c.get(f"/api/v1/tryon/sessions/{sess}/renders/{render}",
                                   headers=H).json()["render"]["state"] == "ready")
    check("try-on render ready (demo)", bool(ready))
    check("hanger restore", c.get(f"/api/v1/tryon/sessions/{sess}/renders/{render}",
                                  headers=H).json()["render"]["state"] == "ready")
    check("history seeded", len(c.get("/api/v1/tryon/history", headers=H).json()["items"]) == 1)

    r = c.post("/api/v1/signature-looks", headers=H,
               json={"name": "Smoke look", "items": [{"sizeId": size_id, "renderId": render}]})
    check("signature look saved", r.status_code == 201)

    r = c.post("/api/v1/analytics/events", headers=H,
               json={"event": "try_on_completed", "authenticated": True, "environment": "smoke"})
    check("analytics ingested", r.status_code == 200)

    r = c.delete("/api/v1/users/me", headers=H)
    check("account deleted", r.status_code == 200)

leftovers = sum(
    sync_db[col].count_documents({"user_id": user_id})
    for col in ("measurements", "refresh_tokens", "avatar_jobs", "avatar_profiles",
                "tryon_sessions", "tryon_renders", "signature_looks", "capture_sessions")
) + sync_db["users"].count_documents({"_id": user_id})
check("cascade left nothing behind", leftovers == 0, f"leftover docs: {leftovers}")
sync_db["analytics_events"].delete_many({"user_id": user_id})

failed = [n for n, ok in checks if not ok]
print(f"\n{len(checks) - len(failed)}/{len(checks)} checks passed" + (f"  FAILED: {failed}" if failed else ""))
sys.exit(1 if failed else 0)
