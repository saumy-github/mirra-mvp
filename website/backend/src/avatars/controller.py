"""HTTP ↔ domain translation for avatars."""

from . import service
from .models import STAGE_LABELS


def shape_job(job: dict) -> dict:
    return {
        "jobId": job["_id"],
        "state": job["state"],
        "stageLabel": STAGE_LABELS.get(job["state"], job["state"]),
        "engineMode": job["engine_mode"],
        "failureReason": job.get("failure_reason"),
        "avatarProfileId": job.get("avatar_profile_id"),
        "createdAt": job["created_at"].isoformat(),
        "completedAt": job["completed_at"].isoformat() if job.get("completed_at") else None,
    }


def shape_profile(profile: dict | None) -> dict | None:
    if profile is None:
        return None
    return {
        "avatarProfileId": profile["_id"],
        "gender": profile.get("gender"),
        "measurements": profile.get("measurements") or {},
        "bodyShapeType": profile.get("body_shape_type"),
        "skinToneHex": profile.get("skin_tone_hex"),
        "sourceJobId": profile.get("source_job_id"),
        "createdAt": profile["created_at"].isoformat(),
        "updatedAt": profile["updated_at"].isoformat(),
    }


async def start_generation(user_id: str) -> dict:
    job = await service.start_generation(user_id)
    return {"job": shape_job(job)}


async def get_job(job_id: str, user_id: str) -> dict:
    job = await service.get_job(job_id, user_id)
    return {"job": shape_job(job)}


async def get_profile(user_id: str) -> dict:
    profile = await service.get_profile(user_id)
    return {"profile": shape_profile(profile)}


async def delete_profile(user_id: str) -> dict:
    await service.delete_profile(user_id)
    return {"ok": True}
