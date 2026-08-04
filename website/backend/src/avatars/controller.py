"""HTTP ↔ domain translation for avatars."""

from . import service
from .models import STAGE_LABELS, AvatarJobDocument, AvatarProfileDocument


def shape_job(job: AvatarJobDocument) -> dict:
    return {
        "jobId": job.id,
        "state": job.state,
        "stageLabel": STAGE_LABELS.get(job.state, job.state),
        "engineMode": job.engine_mode,
        "failureReason": job.failure_reason,
        "avatarProfileId": job.avatar_profile_id,
        "createdAt": job.created_at.isoformat(),
        "completedAt": job.completed_at.isoformat() if job.completed_at else None,
    }


def shape_profile(profile: AvatarProfileDocument | None) -> dict | None:
    if profile is None:
        return None
    return {
        "avatarProfileId": profile.id,
        "gender": profile.gender,
        "measurements": profile.measurements or {},
        "bodyShapeType": profile.body_shape_type,
        "skinToneHex": profile.skin_tone_hex,
        "sourceJobId": profile.source_job_id,
        "createdAt": profile.created_at.isoformat(),
        "updatedAt": profile.updated_at.isoformat(),
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
