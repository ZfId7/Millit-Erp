# modules/jobs_management/services/build_status_service.py
from __future__ import annotations

from typing import Dict, Set

from database.models import Build

from modules.shared.status import (
    STATUS_QUEUE,
    STATUS_IN_PROGRESS,
    STATUS_COMPLETED,
    LEGACY_COMPLETE,
    TERMINAL_STATUSES,
)

# Build/job allowed statuses
ALLOWED_BUILD_STATUSES: Set[str] = {
    STATUS_QUEUE, 
    STATUS_IN_PROGRESS, 
    STATUS_COMPLETED,
    LEGACY_COMPLETE,
}

BUILD_TERMINAL_STATUSES = {STATUS_COMPLETED, LEGACY_COMPLETE}


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

    status_in = (new_status or "").strip()
    if status_in not in ALLOWED_BUILD_STATUSES:
        return {
            "ok": False,
            "message": "Invalid status.",
            "flash_level": "error",
            "job_id": build.job_id,
            "build_name": build.name,
        }

    # Normalize legacy input into canonical output
    status = STATUS_COMPLETED if status_in == LEGACY_COMPLETE else status_in

    # Mutations
    build.status = status

    # Derive job status from builds
    job = build.job
    statuses = {b.status for b in job.builds}

    if statuses.issubset(set(BUILD_TERMINAL_STATUSES)):
        job.status = STATUS_COMPLETED
    elif STATUS_IN_PROGRESS in statuses:
        job.status = STATUS_IN_PROGRESS
    else:
        job.status = STATUS_QUEUE

    return {
        "ok": True,
        "message": f'Updated build "{build.name}" → {status.replace("_", " ")}.',
        "flash_level": "success",
        "job_id": build.job_id,
        "build_name": build.name,
    }
