# File path: modules/manufacturing/surface_grinding/routes/queue.py
# V1 Refactor Queue

from flask import render_template, request
from sqlalchemy import case

from modules.user.decorators import login_required
from .. import surface_bp
from database.models import BuildOperation, Build, Job

# Terminal guard (canonical + legacy)
STATUS_COMPLETED = "completed"   # canonical terminal
STATUS_CANCELLED = "cancelled"   # canonical terminal

STATUS_IN_PROGRESS = "in_progress"
STATUS_QUEUE = "queue"
STATUS_BLOCKED = "blocked"

#Legacy/compat
LEGACY_COMPLETE = "complete"


TERMINAL_STATUSES = (
    STATUS_COMPLETED,
    STATUS_CANCELLED,
    LEGACY_COMPLETE,
)

@surface_bp.route("/queue", methods=["GET"])
@login_required
def surface_queue():
    """
    Shows all queued/in-progress/cancelled/completed operations for the surface grinding module.
    Optional filters: job_id, build_id

    Archive rules:
    - Archived jobs are excluded from the queue.
    - In-progress ops cancelled during archival will show as 'cancelled' (if not archived/excluded).
    - Completed ops remain completed, but are not shown in this queue view.
    """
    job_id = request.args.get("job_id", type=int)
    build_id = request.args.get("build_id", type=int)

    # Optional: custom status ordering for cleaner UX
    status_sort = case(
        (BuildOperation.status == STATUS_IN_PROGRESS, 0),
        (BuildOperation.status == STATUS_QUEUE, 1),
        (BuildOperation.status == STATUS_BLOCKED, 2),
        (BuildOperation.status == STATUS_CANCELLED, 3),
        (BuildOperation.status == STATUS_COMPLETED, 4),
        (BuildOperation.status == LEGACY_COMPLETE, 5),
        else_=9,
    )

    q = (
        BuildOperation.query
        .join(Build, BuildOperation.build_id == Build.id)
        .join(Job, Build.job_id == Job.id)
        .filter(Job.is_archived == False)  # ✅ critical
        .filter(BuildOperation.module_key == "surface_grinding")
        .filter(BuildOperation.is_released.is_(True))
        .filter(BuildOperation.status.in_(list(TERMINAL_STATUSES) + [STATUS_QUEUE, STATUS_IN_PROGRESS, STATUS_BLOCKED]))
        .order_by(
            Job.created_at.desc(),
            status_sort.asc(),
            BuildOperation.sequence.asc(),
            BuildOperation.id.asc(),
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
        "surface_grinding/queue.html",
        ops=ops,
        jobs=jobs,
        builds=builds,
        selected_job_id=job_id,
        selected_build_id=build_id,
    )
