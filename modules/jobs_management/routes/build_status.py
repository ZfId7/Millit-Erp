from flask import flash, redirect, request, url_for
from modules.jobs_management import jobs_bp
from database.models import Build, Job, db

from modules.jobs_management.services.build_status_service import update_build_status


@jobs_bp.route("/build/<int:build_id>/status", methods=["POST"])
def build_update_status(build_id):
    new_status = (request.form.get("status") or "").strip()

    try:
        result = update_build_status(build_id=build_id, new_status=new_status)

        if result.get("ok"):
            db.session.commit()
        else:
            db.session.rollback()

        flash(result["message"], result.get("flash_level", "info"))

    except Exception as e:
        db.session.rollback()
        flash(f"Build status update failed: {e}", "error")
        return redirect(url_for("jobs_bp.jobs_index"))

    job_id = result.get("job_id")
    if not job_id:
        # Fallback: send user back to jobs list if something is really wrong
        return redirect(url_for("jobs_bp.jobs_index"))

    return redirect(url_for("jobs_bp.job_detail", job_id=job_id))
