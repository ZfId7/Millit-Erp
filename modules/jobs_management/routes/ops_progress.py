# File path: modules/jobs_management/routes/ops_progress.py

from flask import flash, redirect, request, url_for
from database.models import BuildOperation, BuildOperationProgress, db
from jobs_management import jobs_bp
from modules.inventory.services.parts_inventory import apply_part_inventory_delta
from modules.jobs_management.services.ops_flow import complete_operation
from modules.user.decorators import login_required

@jobs_bp.route("/ops/<int:op_id>/progress/add", methods=["POST"])
@login_required
def op_progress_add(op_id):
    op = BuildOperation.query.get_or_404(op_id)

    # Ensure we can redirect back to the correct job page
    job_id = request.form.get("job_id", type=int)
    if not job_id and op.build:
        job_id = op.build.job_id

    qty_done_delta = request.form.get("qty_done_delta", type=float) or 0.0
    qty_scrap_delta = request.form.get("qty_scrap_delta", type=float) or 0.0
    note = (request.form.get("note") or "").strip()

    if qty_done_delta < 0 or qty_scrap_delta < 0:
        flash("Progress values cannot be negative.", "error")
        return redirect(url_for("jobs_bp.job_detail", job_id=job_id))

    if qty_done_delta == 0 and qty_scrap_delta == 0 and not note:
        flash("Nothing to add. Enter qty and/or a note.", "error")
        return redirect(url_for("jobs_bp.job_detail", job_id=job_id, _anchor=f"op-{op.id}"))

    entry = BuildOperationProgress(
        build_operation_id=op.id,
        qty_done_delta=qty_done_delta,
        qty_scrap_delta=qty_scrap_delta,
        note=note or None,
    )
    db.session.add(entry)

    # Update operation totals
    op.qty_done = (op.qty_done or 0.0) + qty_done_delta
    op.qty_scrap = (op.qty_scrap or 0.0) + qty_scrap_delta

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
            BuildOperation.status.notin_(["complete", "cancelled"]),
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
