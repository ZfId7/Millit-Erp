# File path: modules/jobs_management/routes/build_status.py


from flask import flash, redirect, request, url_for
from database.models import Build, db
from jobs_management import jobs_bp


@jobs_bp.route("/build/<int:build_id>/status", methods=["POST"])
def build_update_status(build_id):
    build = Build.query.get_or_404(build_id)

    new_status = (request.form.get("status") or "").strip()
    allowed = {"queue", "in_progress", "complete"}

    if new_status not in allowed:
        flash("Invalid status.", "error")
        return redirect(url_for("jobs_bp.job_detail", job_id=build.job_id))

    build.status = new_status
    # Optional: derive job status from builds
    job = build.job
    statuses = {b.status for b in job.builds}

    if statuses == {"complete"}:
            job.status = "complete"
    elif "in_progress" in statuses:
            job.status = "in_progress"
    else:
            job.status = "queue"
    db.session.commit()

    flash(f'Updated build "{build.name}" → {new_status.replace("_"," ")}.', "success")
    return redirect(url_for("jobs_bp.job_detail", job_id=build.job_id))
