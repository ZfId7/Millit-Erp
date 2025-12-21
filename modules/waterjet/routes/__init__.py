# File path: modules/waterjet/routes/__init__.py
from flask import Blueprint, render_template, request, redirect, url_for, flash

from database.models import db, BuildOperation, Build, Job
from sqlalchemy import case

waterjet_bp = Blueprint("waterjet_bp", __name__)


@waterjet_bp.route("/")
def waterjet_index():
    return render_template("waterjet/index.html")


@waterjet_bp.route("/queue", methods=["GET"])
def waterjet_queue():
    """
    Shows all queued/in-progress/cancelled operations for the waterjet module.
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
        (BuildOperation.status == "in_progress", 0),
        (BuildOperation.status == "queue", 1),
        (BuildOperation.status == "cancelled", 2),
        (BuildOperation.status == "completed", 3),
        else_=9,
    )

    q = (
        BuildOperation.query
        .join(Build, BuildOperation.build_id == Build.id)
        .join(Job, Build.job_id == Job.id)
        .filter(Job.is_archived == False)  # ✅ critical
        .filter(BuildOperation.module_key == "waterjet")
        .filter(BuildOperation.status.in_(["queue", "in_progress", "cancelled", "completed"]))
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
        "waterjet/queue.html",
        ops=ops,
        jobs=jobs,
        builds=builds,
        selected_job_id=job_id,
        selected_build_id=build_id,
    )



@waterjet_bp.route("/op/<int:op_id>/start", methods=["POST"])
def waterjet_op_start(op_id):
    op = BuildOperation.query.get_or_404(op_id)

    if op.module_key != "waterjet":
        flash("That operation does not belong to Waterjet.", "error")
        return redirect(url_for("waterjet_bp.waterjet_queue"))

    if op.status == "complete":
        flash("Cannot start: operation is already complete.", "error")
        return redirect(url_for("waterjet_bp.waterjet_queue"))

    op.status = "in_progress"
    db.session.commit()
    flash("Operation started.", "success")
    return redirect(url_for("waterjet_bp.waterjet_queue"))


@waterjet_bp.route("/op/<int:op_id>/complete", methods=["POST"])
def waterjet_op_complete(op_id):
    op = BuildOperation.query.get_or_404(op_id)

    if op.module_key != "waterjet":
        flash("That operation does not belong to Waterjet.", "error")
        return redirect(url_for("waterjet_bp.waterjet_queue"))

    qty_done = request.form.get("qty_done", type=float) or 0.0
    qty_scrap = request.form.get("qty_scrap", type=float) or 0.0

    if qty_done < 0 or qty_scrap < 0:
        flash("Quantities cannot be negative.", "error")
        return redirect(url_for("waterjet_bp.waterjet_queue"))

    op.qty_done = qty_done
    op.qty_scrap = qty_scrap
    op.status = "complete"

    db.session.commit()
    flash("Operation completed.", "success")
    return redirect(url_for("waterjet_bp.waterjet_queue"))
