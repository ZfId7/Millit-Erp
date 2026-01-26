from datetime import datetime

from database.models import db, Job, Build, BuildOperation


def archive_job(job_id, force_cancel_in_progress=False):
    job = Job.query.get_or_404(job_id)

    in_progress_ops_q = (
        BuildOperation.query
        .join(Build, BuildOperation.build_id == Build.id)
        .filter(Build.job_id == job_id, BuildOperation.status == "in_progress")
    )
    in_progress_count = in_progress_ops_q.count()

    if in_progress_count > 0 and not force_cancel_in_progress:
        return {
            "ok": False,
            "message": (
                f"This job has {in_progress_count} operation(s) in progress. "
                "Check the override box to cancel them and archive the job."
            ),
            "flash_level": "danger",
        }

    try:
        if in_progress_count > 0:
            now = datetime.utcnow()
            for op in in_progress_ops_q.all():
                op.status = "cancelled"
                if hasattr(op, "cancelled_at"):
                    op.cancelled_at = now
                if hasattr(op, "cancelled_reason"):
                    op.cancelled_reason = "Job archived by admin; in-progress op cancelled."

        job.is_archived = True
        job.archived_at = datetime.utcnow()

        db.session.commit()

        return {
            "ok": True,
            "message": "Job archived. In-progress operations were cancelled.",
            "flash_level": "success",
        }

    except Exception:
        db.session.rollback()
        raise
