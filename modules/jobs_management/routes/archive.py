# File path: modules/jobs_management/routes/archive.py

from flask import flash, redirect, render_template, request, url_for
from database.models import Build, BuildOperation, Job, db 
from modules.jobs_management import jobs_bp
from modules.jobs_management.services.job_archive_service import archive_job
from modules.user.decorators import admin_required

from modules.shared.status import (
    STATUS_BLOCKED,
    STATUS_COMPLETED,
    STATUS_CANCELLED,
    LEGACY_COMPLETE,
    STATUS_IN_PROGRESS,
    STATUS_QUEUE,
    TERMINAL_STATUSES,
)

@jobs_bp.route("/<int:job_id>/archive", methods=["GET"])
@admin_required
def job_archive_confirm(job_id):
    job = Job.query.get_or_404(job_id)

    active_count = (
        db.session.query(BuildOperation)
        .join(Build, BuildOperation.build_id == Build.id)
        .filter(
            Build.job_id == job_id, 
            BuildOperation.status.notin_(TERMINAL_STATUSES),
        )
        .count()
    )

    completed_count = (
        db.session.query(BuildOperation)
        .join(Build, BuildOperation.build_id == Build.id)
        .filter(
            Build.job_id == job_id,
            BuildOperation.status.in_((STATUS_COMPLETED, LEGACY_COMPLETE)),
        )
        .count()
    )

    return render_template(
        "jobs_management/archive_confirm.html",
        job=job,
        in_progress_count=active_count,
        completed_count=completed_count,
    )


@jobs_bp.route("/<int:job_id>/archive", methods=["POST"])
@admin_required
def job_archive_post(job_id):
    if request.form.get("confirm_archive") != "yes":
        flash("Archive not confirmed.", "warning")
        return redirect(url_for("jobs_bp.job_archive_confirm", job_id=job_id))

    if request.form.get("typed") != "ARCHIVE":
        flash("Type ARCHIVE to confirm.", "warning")
        return redirect(url_for("jobs_bp.job_archive_confirm", job_id=job_id))

    force_cancel = request.form.get("force_cancel_in_progress") == "yes"
    result = archive_job(job_id, force_cancel_in_progress=force_cancel)
    if not result["ok"]:
        flash(result["message"], result["flash_level"])
        return redirect(url_for("jobs_bp.job_archive_confirm", job_id=job_id))

    flash(result["message"], result["flash_level"])
    return redirect(url_for("jobs_bp.jobs_index"))


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


@jobs_bp.route("/<int:job_id>/unarchive", methods=["POST"])
@admin_required
def job_unarchive_post(job_id):
    job = Job.query.get_or_404(job_id)

    if not job.is_archived:
        flash("Job is not archived.", "warning")
        return redirect(url_for("jobs_bp.jobs_index"))

    if request.form.get("confirm_unarchive") != "yes":
        flash("Unarchive not confirmed.", "warning")
        return redirect(url_for("jobs_bp.job_unarchive_confirm", job_id=job_id))

    if request.form.get("typed") != "UNARCHIVE":
        flash("Type UNARCHIVE to confirm.", "warning")
        return redirect(url_for("jobs_bp.job_unarchive_confirm", job_id=job_id))

    job.is_archived = False
    job.archived_at = None
    job.archived_by = None

    db.session.commit()
    flash("Job unarchived.", "success")
    return redirect(url_for("jobs_bp.jobs_index"))
