# File path: modules/jobs_management/routes/daily_update.py

from flask import render_template
from database.models import Build, BuildOperation, BuildOperationProgress, Job
from jobs_management import jobs_bp
from modules.user.decorators import login_required

@jobs_bp.route("/<int:job_id>/daily_update", methods=["GET"])
@login_required
def job_daily_update(job_id):
    job = Job.query.get_or_404(job_id)

    ops = (
        BuildOperation.query
        .join(Build, BuildOperation.build_id == Build.id)
        .filter(Build.job_id == job.id)
        .order_by(BuildOperation.build_id.asc())
        .all()
    )

    ops_by_build = {}
    op_ids = []
    for op in ops:
        ops_by_build.setdefault(op.build_id, []).append(op)
        op_ids.append(op.id)

    progress_by_op_id = {}
    if op_ids:
        progress_rows = (
            BuildOperationProgress.query
            .filter(BuildOperationProgress.build_operation_id.in_(op_ids))
            .order_by(BuildOperationProgress.created_at.desc(), BuildOperationProgress.id.desc())
            .limit(400)  # enough for "today-ish" visibility
            .all()
        )
        for p in progress_rows:
            progress_by_op_id.setdefault(p.build_operation_id, []).append(p)

    return render_template(
        "jobs_management/daily_update.html",
        job=job,
        ops_by_build=ops_by_build,
        progress_by_op_id=progress_by_op_id,
    )
