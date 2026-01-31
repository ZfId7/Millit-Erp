# File path: modules/waterjet/routes/__init__.py
# -V1 queue
# -V2 Detail/Detail Edit
# -V3 Reopen cancelled ops

from flask import Blueprint, render_template, request, redirect, url_for, flash
from datetime import datetime
from database.models import db, BuildOperation, Build, Job, RawStock, WaterjetOperationDetail
from sqlalchemy import case
from modules.user.decorators import login_required
waterjet_bp = Blueprint("waterjet_bp", __name__)


@waterjet_bp.route("/")
@login_required
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
        .outerjoin(WaterjetOperationDetail, WaterjetOperationDetail.build_operation_id == BuildOperation.id)
        .filter(Job.is_archived == False)  # ✅ critical
        .filter(BuildOperation.module_key == "waterjet")
        .filter(BuildOperation.status.in_(["queue", "in_progress", "blocked", "cancelled", "completed"]))
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

@waterjet_bp.route("/<int:op_id>", methods=["GET"])
@login_required
def waterjet_detail(op_id):
    op = (
        BuildOperation.query
        .join(Build, BuildOperation.build_id == Build.id)
        .join(Job, Build.job_id == Job.id)
        .filter(BuildOperation.id == op_id)
        .first_or_404()
    )

    # Guard: only allow waterjet ops here
    if op.module_key != "waterjet":
        flash("That operation is not a Waterjet operation.", "danger")
        return redirect(url_for("waterjet_bp.waterjet_queue"))

    # No editing archived jobs (still viewable? you decide)
    job = Job.query.get(op.build.job_id) if hasattr(op, "build") else None
    if job and getattr(job, "is_archived", False):
        flash("This job is archived. Waterjet details can be viewed, but queues exclude archived jobs.", "warning")

    detail = WaterjetOperationDetail.query.filter_by(build_operation_id=op.id).first()
    if not detail:
        detail = WaterjetOperationDetail(build_operation_id=op.id, updated_at=datetime.utcnow())
        db.session.add(detail)
        db.session.commit()

    raw_stock_items = (
        RawStock.query
        .filter(RawStock.is_active == True)
        .order_by(RawStock.material_type.asc(), RawStock.name.asc())
        .all()
    )

    raw_stock_map= {
		r.id: {
			"thickness_in": r.thickness_in,
			"width_in": r.width_in,
			"length_in": r.length_in,
			"material_type": r.material_type,
			"name": r.name,
		}
		for r in raw_stock_items
	}

    return render_template(
        "waterjet/detail.html",
        op=op,
        detail=detail,
        raw_stock_items=raw_stock_items,
        raw_stock_map=raw_stock_map,
    )

@waterjet_bp.route("/<int:op_id>/update", methods=["POST"])
@login_required
def waterjet_detail_update(op_id):
    op = BuildOperation.query.get_or_404(op_id)

    if op.module_key != "waterjet":
        flash("That operation is not a Waterjet operation.", "danger")
        return redirect(url_for("waterjet_bp.waterjet_queue"))

    detail = WaterjetOperationDetail.query.filter_by(build_operation_id=op.id).first()
    if not detail:
        detail = WaterjetOperationDetail(
            build_operation_id=op.id,
            updated_at=datetime.utcnow()
        )
        db.session.add(detail)

    def set_str(field_name, attr_name=None):
        if field_name not in request.form:
            return
        val = (request.form.get(field_name) or "").strip()
        setattr(detail, attr_name or field_name, val or None)

    def set_int(field_name, attr_name=None):
        if field_name not in request.form:
            return
        v = (request.form.get(field_name) or "").strip()
        try:
            setattr(detail, attr_name or field_name, int(v) if v != "" else None)
        except ValueError:
            setattr(detail, attr_name or field_name, None)

    def set_float(field_name, attr_name=None):
        if field_name not in request.form:
            return
        v = (request.form.get(field_name) or "").strip()
        try:
            setattr(detail, attr_name or field_name, float(v) if v != "" else None)
        except ValueError:
            setattr(detail, attr_name or field_name, None)
        if "material_remaining" in request.form:
            val = request.form.get("material_remaining")
            if val == "yes":
                detail.material_remaining = True
            elif val == "no":
                detail.material_remaining = False
            else:
                detail.material_remaining = None

    # raw_stock_id (special)
    if "raw_stock_id" in request.form:
        raw_stock_id = request.form.get("raw_stock_id")
        detail.raw_stock_id = (
            int(raw_stock_id)
            if raw_stock_id and raw_stock_id.isdigit()
            else None
        )

    # overrides
    set_float("thickness_override")
    set_float("width_override")
    set_float("length_override")

    # misc
    set_str("material_source")
    set_str("yield_note")

    # file / program
    set_str("file_name")
    set_str("program_revision")

    # runtime
    set_int("runtime_est_min")
    set_int("runtime_actual_min")

    # blocked fields (editable any time)
    set_str("blocked_reason")
    set_str("blocked_notes")

    # notes
    set_str("notes")

    detail.updated_at = datetime.utcnow()
    db.session.commit()

    if "notes" in request.form and len(request.form) == 1:
        flash("Notes saved.", "success")
    else:
        flash("Waterjet details saved.", "success")

    return redirect(url_for("waterjet_bp.waterjet_detail", op_id=op.id))



@waterjet_bp.route("/<int:op_id>/start", methods=["POST"])
@login_required
def waterjet_start(op_id):
    op = BuildOperation.query.get_or_404(op_id)
    if op.module_key != "waterjet":
        flash("Not a waterjet operation.", "danger")
        return redirect(url_for("waterjet_bp.waterjet_queue"))

    if op.status in ("completed", "cancelled"):
        flash("This operation is already closed.", "warning")
        return redirect(url_for("waterjet_bp.waterjet_detail", op_id=op.id))

    op.status = "in_progress"
    db.session.commit()
    flash("Operation started.", "success")
    return redirect(url_for("waterjet_bp.waterjet_detail", op_id=op.id))

@waterjet_bp.route("/<int:op_id>/complete", methods=["POST"])
@login_required
def waterjet_complete(op_id):
    op = BuildOperation.query.get_or_404(op_id)
    if op.module_key != "waterjet":
        flash("Not a waterjet operation.", "danger")
        return redirect(url_for("waterjet_bp.waterjet_queue"))

    op.status = "completed"
    db.session.commit()
    flash("Operation completed.", "success")
    return redirect(url_for("waterjet_bp.waterjet_detail", op_id=op.id))

@waterjet_bp.route("/<int:op_id>/cancel", methods=["POST"])
@login_required
def waterjet_cancel(op_id):
    op = BuildOperation.query.get_or_404(op_id)
    if op.module_key != "waterjet":
        flash("Not a waterjet operation.", "danger")
        return redirect(url_for("waterjet_bp.waterjet_queue"))

    op.status = "cancelled"
    db.session.commit()
    flash("Operation cancelled.", "success")
    return redirect(url_for("waterjet_bp.waterjet_detail", op_id=op.id))

@waterjet_bp.route("/<int:op_id>/block", methods=["POST"])
@login_required
def waterjet_block(op_id):
    op = BuildOperation.query.get_or_404(op_id)
    if op.module_key != "waterjet":
        flash("Not a waterjet operation.", "danger")
        return redirect(url_for("waterjet_bp.waterjet_queue"))

    detail = WaterjetOperationDetail.query.filter_by(build_operation_id=op.id).first()
    if not detail:
        detail = WaterjetOperationDetail(build_operation_id=op.id, updated_at=datetime.utcnow())
        db.session.add(detail)

    reason = (request.form.get("blocked_reason") or "").strip().lower()
    notes = (request.form.get("blocked_notes") or "").strip()

    if not reason:
        flash("Blocked reason is required.", "danger")
        return redirect(url_for("waterjet_bp.waterjet_detail", op_id=op.id))

    # Allow other with optional notes
    detail.blocked_reason = reason
    detail.blocked_notes = notes or None
    detail.updated_at = datetime.utcnow()

    op.status = "blocked"
    db.session.commit()

    flash("Operation blocked.", "warning")
    return redirect(url_for("waterjet_bp.waterjet_detail", op_id=op.id))

@waterjet_bp.route("/<int:op_id>/reopen", methods=["POST"])
@login_required
def waterjet_reopen(op_id):
    op = BuildOperation.query.get_or_404(op_id)

    if op.module_key != "waterjet":
        flash("Not a waterjet operation.", "danger")
        return redirect(url_for("waterjet_bp.waterjet_queue"))

    if op.status != "cancelled":
        flash("Only cancelled operations can be reopened.", "warning")
        return redirect(url_for("waterjet_bp.waterjet_detail", op_id=op.id))

    # Reopen back to queue (safe default)
    op.status = "queue"

    # Optional: if you track cancelled_at/cancelled_reason on BuildOperation, clear them here.
    # op.cancelled_at = None
    # op.cancelled_reason = None

    db.session.commit()
    flash("Operation reopened and set back to queue.", "success")
    return redirect(url_for("waterjet_bp.waterjet_detail", op_id=op.id))

@waterjet_bp.route("/<int:op_id>/edit", methods=["GET"])
@login_required
def waterjet_detail_edit(op_id):
    op = (
        BuildOperation.query
        .join(Build, BuildOperation.build_id == Build.id)
        .join(Job, Build.job_id == Job.id)
        .filter(BuildOperation.id == op_id)
        .first_or_404()
    )

    if op.module_key != "waterjet":
        flash("That operation is not a Waterjet operation.", "danger")
        return redirect(url_for("waterjet_bp.waterjet_queue"))

    detail = WaterjetOperationDetail.query.filter_by(build_operation_id=op.id).first()
    if not detail:
        detail = WaterjetOperationDetail(build_operation_id=op.id, updated_at=datetime.utcnow())
        db.session.add(detail)
        db.session.commit()

    raw_stock_items = (
        RawStock.query
        .filter(RawStock.is_active == True)
        .order_by(RawStock.material_type.asc(), RawStock.name.asc())
        .all()
    )

    raw_stock_map = {
        r.id: {
            "thickness_in": r.thickness_in,
            "width_in": r.width_in,
            "length_in": r.length_in,
            "material_type": r.material_type,
            "name": r.name,
        }
        for r in raw_stock_items
    }

    return render_template(
        "waterjet/detail_edit.html",  # EDITABLE
        op=op,
        detail=detail,
        raw_stock_items=raw_stock_items,
        raw_stock_map=raw_stock_map,
    )
