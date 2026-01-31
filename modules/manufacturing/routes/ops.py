# File path: modules/manufacturing/routes/ops.py
# -V1 Base Build

from flask import flash, redirect, request, url_for
from modules.manufacturing import mfg_bp
from modules.user.decorators import login_required
from database.models import db, BuildOperation, Machine
from modules.jobs_management.services.ops_flow import complete_operation  # adjust if different

from modules.manufacturing.services.manufacturing_op_service import (
    start_operation,
    block_operation,
    MfgOpError,
    unblock_operation,
)

from modules.shared.status import (
    STATUS_BLOCKED,
    STATUS_COMPLETED,
    STATUS_CANCELLED,
    LEGACY_COMPLETE,
    STATUS_IN_PROGRESS,
    STATUS_QUEUE,
    TERMINAL_STATUSES,
)


@mfg_bp.route("/op/<int:op_id>/start", methods=["POST"])
@login_required
def mfg_start(op_id):
    op = BuildOperation.query.get_or_404(op_id)

    try:
        start_operation(op)
        db.session.commit()
        flash("Operation started.", "success")
        return redirect(url_for("mfg_bp.mfg_details", op_id=op.id))
    except MfgOpError as e:
        db.session.rollback()
        flash(str(e), "error")
        return redirect(request.referrer or url_for("mfg_bp.mfg_queue"))



@mfg_bp.route("/op/<int:op_id>/block", methods=["POST"])
@login_required
def mfg_block(op_id):
    op = BuildOperation.query.get_or_404(op_id)

    try:
        block_operation(op)
        db.session.commit()
        flash("Operation blocked.", "success")
        return redirect(url_for("mfg_bp.mfg_details", op_id=op.id))
    except MfgOpError as e:
        db.session.rollback()
        flash(str(e), "error")
        return redirect(request.referrer or url_for("mfg_bp.mfg_queue"))

@mfg_bp.route("/op/<int:op_id>/unblock", methods=["POST"])
@login_required
def mfg_unblock(op_id):
    op = BuildOperation.query.get_or_404(op_id)

    try:
        unblock_operation(op)
        db.session.commit()
        flash("Operation unblocked (returned to queue).", "success")
        return redirect(url_for("mfg_bp.mfg_details", op_id=op.id))
    except MfgOpError as e:
        db.session.rollback()
        flash(str(e), "error")
        return redirect(request.referrer or url_for("mfg_bp.mfg_details", op_id=op.id))


@mfg_bp.route("/op/<int:op_id>/complete", methods=["POST"])
@login_required
def mfg_complete(op_id):
    op = BuildOperation.query.get_or_404(op_id)

    if op.status in TERMINAL_STATUSES:
        flash(f"Cannot complete: operation is {op.status}.", "error")
        return redirect(url_for("mfg_bp.mfg_queue"))

    complete_operation(op)  # ✅ bounce-safe completion
    db.session.commit()

    flash("Operation completed. Next operation released.", "success")
    return redirect(url_for("mfg_bp.mfg_queue"))


@mfg_bp.route("/op/<int:op_id>/assign_machine", methods=["POST"])
@login_required
def mfg_assign_machine(op_id):
    op = BuildOperation.query.get_or_404(op_id)

    if op.module_key != "manufacturing":
        flash("Invalid operation for Manufacturing.", "error")
        return redirect(url_for("mfg_bp.mfg_queue"))

    # Safety: only queued ops are safe to assign/unassign
    if op.status != STATUS_QUEUE:
        flash("Only queued operations can be assigned/unassigned.", "error")
        return redirect(request.referrer or url_for("mfg_bp.mfg_queue"))

    machine_id = request.form.get("machine_id", type=int)

    # Unassign
    if not machine_id:
        op.assigned_machine_id = None
        db.session.commit()
        flash("Machine unassigned.", "info")
        return redirect(request.referrer or url_for("mfg_bp.mfg_queue"))

    machine = Machine.query.get_or_404(machine_id)

    # Eligibility guard (V0): cnc_profile must be assigned to CNC machines only
    if op.op_key == "cnc_profile" and machine.machine_group != "cnc":
        flash("cnc_profile operations can only be assigned to CNC machines.", "error")
        return redirect(request.referrer or url_for("mfg_bp.mfg_queue"))

    op.assigned_machine_id = machine.id
    db.session.commit()
    flash("Machine assigned.", "success")
    return redirect(request.referrer or url_for("mfg_bp.mfg_queue"))

