# File path: modules/raw_materials/waterjet/routes/queue.py
# V1 Refactor Queue
# V2 Module_key update
# V3 Refactor | moved inside of raw_materials/waterjet/ | changed blueprint to raw_mats_waterjet_bp
from flask import render_template, request
from sqlalchemy import case, asc

from modules.user.decorators import login_required
from modules.raw_materials.waterjet import raw_mats_waterjet_bp
from database.models import BuildOperation, Build, Job, WaterjetOperationDetail

from modules.shared.status import (
    STATUS_BLOCKED,
    STATUS_COMPLETED,
    STATUS_CANCELLED,
    LEGACY_COMPLETE,
    STATUS_IN_PROGRESS,
    STATUS_QUEUE,
    TERMINAL_STATUSES,
)


@raw_mats_waterjet_bp.route("/queue", methods=["GET"])
@login_required
def waterjet_queue():
    job_id = request.args.get("job_id", type=int)
    build_id = request.args.get("build_id", type=int)


    status_sort = case(
        (BuildOperation.status == STATUS_IN_PROGRESS, 0),
        (BuildOperation.status == STATUS_QUEUE, 1),
        (BuildOperation.status == STATUS_BLOCKED, 2),
        (BuildOperation.status == STATUS_CANCELLED, 3),
        (BuildOperation.status == STATUS_COMPLETED, 4),
        else_=9,
    )


    q = (
        BuildOperation.query
        .join(Build, BuildOperation.build_id == Build.id)
        .join(Job, Build.job_id == Job.id)
        .outerjoin(WaterjetOperationDetail, WaterjetOperationDetail.build_operation_id == BuildOperation.id)
        .filter(Job.is_archived == False)
        .filter(BuildOperation.module_key == "raw_materials")
        .filter(BuildOperation.op_key.in_(["waterjet_cut"]))
        .filter(BuildOperation.is_released.is_(True))
        .filter(BuildOperation.status.in_([STATUS_QUEUE, STATUS_IN_PROGRESS, STATUS_BLOCKED]))
        .order_by(
			Job.created_at.desc(),
			asc(status_sort),
			BuildOperation.sequence.asc(),
			BuildOperation.id.asc()
		)

    )


    if job_id:
        q = q.filter(Build.job_id == job_id)
    if build_id:
        q = q.filter(BuildOperation.build_id == build_id)


    ops = q.all()


    # Filters UI should generally only show active jobs/builds for the module queue
    jobs = Job.query.filter(Job.is_archived == False).order_by(Job.created_at.desc()).all()
    builds = []
    if job_id:
        builds = (
            Build.query
            .filter(Build.job_id == job_id)
            .order_by(Build.created_at.asc())
            .all()
        )


    return render_template(
        "raw_materials/waterjet/queue.html",
        ops=ops,
        jobs=jobs,
        builds=builds,
        selected_job_id=job_id,
        selected_build_id=build_id,
    )
