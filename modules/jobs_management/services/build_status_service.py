# modules/jobs_management/services/build_status_service.py
from __future__ import annotations

from typing import Dict, Set

from database.models import Build, db


ALLOWED_BUILD_STATUSES: Set[str] = {"queue", "in_progress", "complete"}


def update_build_status(build_id: int, new_status: str) -> Dict[str, object]:
    """
    Updates a Build.status and derives the parent Job.status from all builds.

    Returns:
      {
        "ok": bool,
        "message": str,
        "flash_level": str,
        "job_id": int | None,
        "build_name": str | None,
      }
    """
    build = Build.query.get(build_id)
    if not build:
        return {
            "ok": False,
            "message": "Build not found.",
            "flash_level": "error",
            "job_id": None,
            "build_name": None,
        }

    status = (new_status or "").strip()
    if status not in ALLOWED_BUILD_STATUSES:
        return {
            "ok": False,
            "message": "Invalid status.",
            "flash_level": "error",
            "job_id": build.job_id,
            "build_name": build.name,
        }

    # Mutations
    build.status = status

    # Derive job status from builds
    job = build.job
    statuses = {b.status for b in job.builds}

    if statuses == {"complete"}:
        job.status = "complete"
    elif "in_progress" in statuses:
        job.status = "in_progress"
    else:
        job.status = "queue"

    db.session.commit()

    return {
        "ok": True,
        "message": f'Updated build "{build.name}" → {status.replace("_", " ")}.',
        "flash_level": "success",
        "job_id": build.job_id,
        "build_name": build.name,
    }
