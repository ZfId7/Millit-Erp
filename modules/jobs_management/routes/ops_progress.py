# File path: modules/jobs_management/routes/ops_progress.py

from flask import flash, redirect, request, session, url_for, render_template
from database.models import BuildOperation, BuildOperationProgress, db, User
from datetime import datetime, timedelta
from sqlalchemy import distinct

from modules.user.decorators import login_required
from modules.jobs_management import jobs_bp

from modules.inventory.services.parts_inventory import apply_part_inventory_delta
from modules.jobs_management.services.ops_flow import complete_operation
from modules.manufacturing.services.progress_service import add_op_progress, OpProgressError

@jobs_bp.route("/ops/<int:op_id>/progress/add", methods=["POST"])
@login_required
def op_progress_add(op_id):
    op = BuildOperation.query.get_or_404(op_id)

    # deltas
    qty_done_delta = request.form.get("qty_done_delta", type=float) or 0.0
    qty_scrap_delta = request.form.get("qty_scrap_delta", type=float) or 0.0
    note = (request.form.get("note") or "").strip()


    # redirect target
    job_id = request.form.get("job_id", type=int) or (op.build.job_id if op.build else None)

    # Resolve current user id (based on session username)
    username = session.get("user")
    current_user = User.query.filter_by(username=username).first() if username else None
    current_user_id = current_user.id if current_user else None

    

    try:
        # NOTE: this will require BuildOperationProgress.user_id to exist
        add_op_progress(
            op_id=op.id,
            qty_done_delta=qty_done_delta,
            qty_scrap_delta=qty_scrap_delta,
            note=note,
            user_id=current_user_id,
        )

        # keep your inventory posting logic EXACTLY as-is (it uses qty_done_delta/qty_scrap_delta)
        # ... RAW_MATS_BLANK_OP_KEYS block remains unchanged ...

        # ---- Inventory posting (ops-driven) ----
        # Only for raw materials ops that produce "blank" inventory
        RAW_MATS_BLANK_OP_KEYS = {
            "waterjet_cut",
            "laser_cut",
            "bandsaw_cut",
            "tablesaw_cut",
            "edm_cut",
        }

        if op.module_key == "raw_materials" and op.op_key in RAW_MATS_BLANK_OP_KEYS:
            if op.bom_item and op.bom_item.part_id:
                part_id = op.bom_item.part_id
                uom = op.bom_item.unit or "ea"

                # Done adds blanks
                if qty_done_delta:
                    apply_part_inventory_delta(part_id, "blank", qty_done_delta, uom=uom)

                # Scrap reduces blanks (delta)
                if qty_scrap_delta:
                    apply_part_inventory_delta(part_id, "blank", -qty_scrap_delta, uom=uom)
            else:
                flash(
                    "Progress saved, but Parts Inventory was not updated (BOM item is not linked to a catalog Part).",
                    "warning",
                )

        db.session.commit()
        flash("Progress saved.", "success")

    except OpProgressError as e:
        db.session.rollback()
        flash(str(e), "error")

    # Always redirect somewhere
    if job_id:
        return redirect(url_for("jobs_bp.job_daily_update", job_id=job_id, _anchor=f"op-{op.id}"))
    return redirect(request.referrer or url_for("jobs_bp.jobs_index"))


def release_next_for_bom_item(current_op: BuildOperation):
    # clear any releases for this bom item (enforces 1-released invariant)
    BuildOperation.query.filter_by(
        build_id=current_op.build_id,
        bom_item_id=current_op.bom_item_id
    ).update(
        {BuildOperation.is_released: False},
        synchronize_session=False
    )
    current_op.is_released = False
    
    next_op = (
        BuildOperation.query
        .filter(
            BuildOperation.build_id == current_op.build_id,
            BuildOperation.bom_item_id == current_op.bom_item_id,
            BuildOperation.sequence > current_op.sequence,
            BuildOperation.status.notin_(["complete", "completed", "cancelled"]),
        )
        .order_by(BuildOperation.sequence.asc(), BuildOperation.id.asc())
        .first()
    )

    if next_op:
        next_op.is_released = True
        if next_op.status not in ("blocked", "in_progress"):
            next_op.status = "queue"

@jobs_bp.route("/ops/<int:op_id>/complete", methods=["POST"])
@login_required
def op_mark_complete(op_id):
    op = BuildOperation.query.get_or_404(op_id)

    job_id = request.form.get("job_id", type=int) or (op.build.job_id if op.build else None)

    complete_operation(op)

    db.session.commit()
    flash("Operation marked complete. Next operation released.", "success")
    return redirect(url_for("jobs_bp.job_daily_update", job_id=job_id, _anchor=f"op-{op.id}"))

@jobs_bp.route("/ops/active", methods=["GET"])
@login_required
def ops_active():
    username = session.get("user")
    user = User.query.filter_by(username=username).first_or_404()

    cutoff = datetime.utcnow() - timedelta(days=7)

    # Ops I’ve touched recently via progress entries
    op_ids = (
        db.session.query(distinct(BuildOperationProgress.build_operation_id))
        .filter(BuildOperationProgress.user_id == user.id)
        .filter(BuildOperationProgress.created_at >= cutoff)
        .all()
    )
    op_ids = [row[0] for row in op_ids]

    ops = []
    progress_by_op_id = {}

    if op_ids:
        ops = (
            BuildOperation.query
            .filter(BuildOperation.id.in_(op_ids))
            .filter(BuildOperation.status.in_(["queue", "in_progress", "blocked"]))
            .order_by(BuildOperation.id.desc())
            .all()
        )

        progress_rows = (
            BuildOperationProgress.query
            .filter(BuildOperationProgress.build_operation_id.in_(op_ids))
            .order_by(BuildOperationProgress.created_at.desc(), BuildOperationProgress.id.desc())
            .limit(300)
            .all()
        )
        for p in progress_rows:
            progress_by_op_id.setdefault(p.build_operation_id, []).append(p)

    return render_template(
        "ops_active.html",
        ops=ops,
        progress_by_op_id=progress_by_op_id,
        me=user,
    )
