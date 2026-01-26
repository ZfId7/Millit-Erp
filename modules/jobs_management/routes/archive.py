# File path: modules/jobs_management/routes/archive.py

from flask import flash, redirect, render_template, url_for
from database.models import Build, BuildOperation, Job, db 
from jobs_management import jobs_bp
from modules.user.decorators import admin_required

@jobs_bp.route("/archived", methods=["GET"])
@admin_required
def jobs_archived_index():
    jobs = Job.query.filter(Job.is_archived == True).order_by(Job.archived_at.desc().nullslast(), Job.id.desc()).all()
    return render_template("jobs_management/archived_index.html", jobs=jobs)


@jobs_bp.route("/<int:job_id>/archive", methods=["GET"])
@admin_required
def job_archive_confirm(job_id):
    job = Job.query.get_or_404(job_id)

    in_progress_count = (
        db.session.query(BuildOperation)
        .join(Build, BuildOperation.build_id == Build.id)
        .filter(Build.job_id == job_id, BuildOperation.status == "in_progress")
        .count()
    )

    completed_count = (
        db.session.query(BuildOperation)
        .join(Build, BuildOperation.build_id == Build.id)
        .filter(Build.job_id == job_id, BuildOperation.status == "completed")
        .count()
    )

    return render_template(
        "jobs_management/archive_confirm.html",
        job=job,
        in_progress_count=in_progress_count,
        completed_count=completed_count,
    )


@jobs_bp.route("/<int:job_id>/unarchive", methods=["GET"])
@admin_required
def job_unarchive_confirm(job_id):
    job = Job.query.get_or_404(job_id)

    if not job.is_archived:
        flash("Job is not archived.", "warning")
        return redirect(url_for("jobs_bp.jobs_index"))

    return render_template(
        "jobs_management/unarchive_confirm.html",
        job=job,
    )
