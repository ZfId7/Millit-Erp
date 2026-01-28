# File path: modules/jobs_management/routes/delete.py

from flask import flash, redirect, render_template, request, url_for
from database.models import Build, BuildOperation, Job, db
from modules.jobs_management import jobs_bp
from modules.jobs_management.services.job_delete_service import delete_job_with_children
from modules.user.decorators import admin_required, login_required

@jobs_bp.route("/<int:job_id>/delete", methods=["POST"])
@login_required
@admin_required
def delete_job(job_id):
    job = Job.query.get_or_404(job_id)

    # Hard confirmation guard
    if request.form.get("confirm_delete") != "yes":
        flash("Deletion not confirmed.", "warning")
        return redirect(url_for("jobs_bp.job_detail", job_id=job_id))

    # Optional: enforce typing DELETE (recommended)
    if request.form.get("typed") != "DELETE":
        flash("Type DELETE to confirm job deletion.", "warning")
        return redirect(url_for("jobs_bp.job_detail", job_id=job_id))

    # Completed ops behavior: warn + require override checkbox
    completed_count = (
        db.session.query(BuildOperation)
        .join(Build, BuildOperation.build_id == Build.id)
        .filter(Build.job_id == job_id, BuildOperation.status == "completed")
        .count()
    )

    if completed_count > 0 and request.form.get("allow_completed") != "yes":
        flash(
            f"Job has {completed_count} completed operation(s). "
            "Check the override box to delete anyway.",
            "danger",
        )
        return redirect(url_for("jobs_bp.job_detail", job_id=job_id))
    
    result = delete_job_with_children(job_id)
    flash(result["message"], "success")
    return redirect(url_for("jobs_bp.jobs_index"))    

@jobs_bp.route("/<int:job_id>/delete", methods=["GET"])
@admin_required
def job_delete_confirm(job_id):
    job = Job.query.get_or_404(job_id)

    completed_count = (
        db.session.query(BuildOperation)
        .join(Build, BuildOperation.build_id == Build.id)
        .filter(Build.job_id == job_id, BuildOperation.status == "completed")
        .count()
    )

    return render_template(
        "jobs_management/delete_confirm.html",
        job=job,
        completed_count=completed_count
    )
