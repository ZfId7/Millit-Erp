from datetime import datetime

from database.models import db, Job, Build, BuildOperation
from modules.shared.status import (
    STATUS_CANCELLED,
    TERMINAL_STATUSES,
)


def archive_job(job_id, force_cancel_in_progress=False):
    job = Job.query.get_or_404(job_id)

    active_ops_q = (
        BuildOperation.query
        .join(Build, BuildOperation.build_id == Build.id)
        .filter(
            Build.job_id == job_id,
            BuildOperation.status.notin_(TERMINAL_STATUSES),
        )
    )
    active_count = active_ops_q.count()

    if active_count > 0 and not force_cancel_in_progress:
        return {
            "ok": False,
            "message": (
                f"This job has {active_count} active operation(s). "
                "Check the override box to cancel them and archive the job."
            ),
            "flash_level": "danger",
        }

    try:
        if active_count > 0:
            now = datetime.utcnow()
            for op in active_ops_q.all():
                op.status = STATUS_CANCELLED
                if hasattr(op, "cancelled_at"):
                    op.cancelled_at = now
                if hasattr(op, "cancelled_reason"):
                    op.cancelled_reason = "Job archived by admin; active op cancelled."

        job.is_archived = True
        job.archived_at = datetime.utcnow()

        db.session.commit()

        return {
            "ok": True,
            "message": "Job archived. Active operations were cancelled.",
            "flash_level": "success",
        }

    except Exception:
        db.session.rollback()
        raise

