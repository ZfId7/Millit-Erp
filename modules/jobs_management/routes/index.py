# File path: modules/jobs_management/routes/index.py

from flask import render_template, url_for
from sqlalchemy import func
from database.models import  Job
from modules.jobs_management.services.job_numbering import _next_job_number
from modules.user.decorators import login_required, admin_required
from modules.jobs_management import jobs_bp


@jobs_bp.route("/")
@login_required
def jobs_index():
    jobs = Job.query.filter(Job.is_archived == False).order_by(Job.id.desc()).all()
    return render_template(
        "jobs_management/index.html", 
        jobs=jobs,
        )

@jobs_bp.route("/archived", methods=["GET"])
@admin_required
def jobs_archived_index():
    jobs = Job.query.filter(Job.is_archived == True).order_by(Job.archived_at.desc().nullslast(), Job.id.desc()).all()
    return render_template("jobs_management/archived_index.html", jobs=jobs)
