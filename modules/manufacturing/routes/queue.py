# File path: modules/manufacturing/routes/queue.py
# -V1 Base Build
from flask import render_template, request
from modules.manufacturing import mfg_bp
from modules.user.decorators import login_required
from database.models import BuildOperation, Job, Build, Machine

MFG_OP_KEYS = ["cnc_profile"]

@mfg_bp.route("/queue", methods=["GET"])
@login_required
def mfg_queue():
    job_id = request.args.get("job_id", type=int)
    build_id = request.args.get("build_id", type=int)
    machine_id = request.args.get("machine_id", type=int)
    
    q = (
        BuildOperation.query
        .join(Build, Build.id == BuildOperation.build_id)
        .join(Job, Job.id == Build.job_id)
        .filter(Job.is_archived == False)
        .filter(BuildOperation.module_key == "manufacturing")
        .filter(BuildOperation.op_key.in_(MFG_OP_KEYS))  # v0
        .filter(BuildOperation.is_released.is_(True))
        .filter(BuildOperation.status.in_(["queue", "in_progress", "blocked"]))
        .order_by(Job.created_at.desc(), BuildOperation.sequence.asc(), BuildOperation.id.asc())
    )

    if job_id:
        q = q.filter(Build.job_id == job_id)
    if build_id:
        q = q.filter(BuildOperation.build_id == build_id)
    if machine_id:
        q = q.filter(BuildOperation.assigned_machine_id == machine_id)

    ops = q.all()

    # Filters UI should generally only show active jobs/builds for the module queue
    jobs = Job.query.filter(Job.is_archived == False).order_by(Job.created_at.desc()).all()

    builds = []
    if job_id:
        builds = Build.query.filter(Build.job_id == job_id).order_by(Build.created_at.asc()).all()
    
    machines = (
        Machine.query
        .filter(Machine.is_active.is_(True))
        .order_by(Machine.machine_group.asc(), Machine.name.asc())
        .all()
    )


    return render_template(
        "manufacturing/queue.html",
        ops=ops,
        jobs=jobs,
        builds=builds,
        job_id=job_id,
        build_id=build_id,
        machines=machines,
        machine_id=machine_id,
    )