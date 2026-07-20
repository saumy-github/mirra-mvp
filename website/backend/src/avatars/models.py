"""Avatar job/profile document shapes and staged states.

avatar_jobs doc:
    _id (aj_…), user_id, engine_mode ("demo"|"live"),
    measurement_snapshot (copy of the measurements doc at job creation, so a
    later measurements edit can't change what an in-flight job builds from),
    state ("queued"|"processing"|"ready"|"failed") — authoritative for live
    mode; demo mode derives it from elapsed time on read (same trick as the
    user-side mock), failure_reason, avatar_profile_id (set when ready),
    created_at, completed_at

avatar_profiles doc (one per user — unique index on user_id):
    _id (ap_…), user_id, source_job_id, gender, measurements (snapshot),
    body_shape_type, skin_tone_hex, created_at, updated_at

States are stages, never percentages (reference contract: AvatarJob).
"""

JOB_STATES = ("queued", "processing", "ready", "failed")

STAGE_LABELS = {
    "queued": "Waiting in queue",
    "processing": "Sculpting your digital twin",
    "ready": "Your avatar is ready",
    "failed": "Avatar generation failed",
}

# Demo-mode staged timeline (seconds since job creation).
DEMO_QUEUE_SECONDS = 2
DEMO_PROCESSING_SECONDS = 6
