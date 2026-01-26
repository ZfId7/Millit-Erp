from database.models import db, Job, Build, BOMItem, BuildOperation


def delete_job_with_children(job_id):
    result = {
        "ok": False,
        "message": "",
        "job_id": job_id,
    }

    try:
        job = Job.query.get(job_id)
        if not job:
            raise ValueError("Job not found.")

        build_ids = [b.id for b in Build.query.filter_by(job_id=job_id).all()]
        if build_ids:
            BuildOperation.query.filter(BuildOperation.build_id.in_(build_ids)).delete(
                synchronize_session=False
            )
            BOMItem.query.filter(BOMItem.build_id.in_(build_ids)).delete(
                synchronize_session=False
            )
            Build.query.filter(Build.id.in_(build_ids)).delete(
                synchronize_session=False
            )

        db.session.delete(job)
        db.session.commit()

        result["ok"] = True
        result["message"] = "Job deleted (including BOM + ops)."
        return result
    except Exception:
        db.session.rollback()
        raise
