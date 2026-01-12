# File path: modules/heat_treat/routes/queue.py
# -V1 Base Build - Queue

from flask import render_template, request
from modules.user.decorators import login_required
from modules.heat_treat import heat_treat_bp
from database.models import BuildOperation, Job, Build

HT_OP_KEYS = ["heat_treat"]

@heat_treat_bp.route("/queue", methods=["GET"])
@login_required
def heat_treat_queue():
    job_id = request.args.get("job_id", type=int)
    build_id = request.args.get("build_id", type=int)

    q = (
        BuildOperation.query
        .join(Build, Build.id == BuildOperation.build_id)
        .join(Job, Job.id == Build.job_id)
        .filter(Job.is_archived == False)
        .filter(BuildOperation.module_key == "heat_treat")
        .filter(BuildOperation.op_key.in_(HT_OP_KEYS))
        .filter(BuildOperation.is_released.is_(True))
        .filter(BuildOperation.status.in_(["queue", "in_progress", "blocked"]))
        .order_by(Job.created_at.desc(), BuildOperation.sequence.asc(), BuildOperation.id.asc())
    )

    if job_id:
        q = q.filter(Build.job_id == job_id)
    if build_id:
        q = q.filter(BuildOperation.build_id == build_id)

    ops = q.all()

    jobs = Job.query.filter(Job.is_archived == False).order_by(Job.created_at.desc()).all()
    builds = []
    if job_id:
        builds = Build.query.filter(Build.job_id == job_id).order_by(Build.created_at.asc()).all()

    return render_template(
        "heat_treat/queue.html",
        ops=ops,
        jobs=jobs,
        builds=builds,
        job_id=job_id,
        build_id=build_id,
        selected_job_id=job_id,
        selected_build_id=build_id,
    )
