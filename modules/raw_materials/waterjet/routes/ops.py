# File path: modules/raw_materials/waterjet/routes/ops.py
# V1 Refactor Status Actions
# V2 Refactor | moved inside raw_materials/waterjet/routes/ops | changed blueprint to raw_mats_waterjet_bp
import datetime
from flask import redirect, request, url_for, flash


from modules.user.decorators import login_required
from modules.raw_materials.waterjet import raw_mats_waterjet_bp
from modules.jobs_management.services.ops_flow import complete_operation
from database.models import WaterjetOperationDetail, db, BuildOperation

# Canonical status strings (v0 normalization)
STATUS_QUEUE = "queue"
STATUS_IN_PROGRESS = "in_progress"
STATUS_BLOCKED = "blocked"

STATUS_COMPLETED = "completed"   # canonical terminal
STATUS_CANCELLED = "cancelled"   # canonical terminal

#Legacy/compat
LEGACY_COMPLETE = "complete"

TERMINAL_STATUSES = {STATUS_COMPLETED, STATUS_CANCELLED, LEGACY_COMPLETE}

@raw_mats_waterjet_bp.route("/<int:op_id>/start", methods=["POST"])
@login_required
def waterjet_start(op_id):
    op = BuildOperation.query.get_or_404(op_id)
   


    if op.status in TERMINAL_STATUSES:
        flash(f"Cannot start: operation is {op.status}.", "error")
        return redirect(url_for("raw_mats_waterjet_bp.waterjet_detail", op_id=op.id))


    op.status = STATUS_IN_PROGRESS
    db.session.commit()
    flash("Operation started.", "success")
    return redirect(url_for("raw_mats_waterjet_bp.waterjet_detail", op_id=op.id))

@raw_mats_waterjet_bp.route("/<int:op_id>/complete", methods=["POST"])
@login_required
def waterjet_complete(op_id):
    op = BuildOperation.query.get_or_404(op_id)
   

    complete_operation(op)
    db.session.commit()
    flash("Operation complete.", "success")
    return redirect(url_for("raw_mats_waterjet_bp.waterjet_detail", op_id=op.id))

@raw_mats_waterjet_bp.route("/<int:op_id>/cancel", methods=["POST"])
@login_required
def waterjet_cancel(op_id):
    op = BuildOperation.query.get_or_404(op_id)
   


    op.status = STATUS_CANCELLED
    db.session.commit()
    flash("Operation cancelled.", "success")
    return redirect(url_for("raw_mats_waterjet_bp.waterjet_detail", op_id=op.id))

@raw_mats_waterjet_bp.route("/<int:op_id>/reopen", methods=["POST"])
@login_required
def waterjet_reopen(op_id):
    op = BuildOperation.query.get_or_404(op_id)


  


    if op.status != STATUS_CANCELLED:
        flash("Only cancelled operations can be reopened.", "warning")
        return redirect(url_for("raw_mats_waterjet_bp.waterjet_detail", op_id=op.id))


    op.status = STATUS_QUEUE
    db.session.commit()
    flash("Operation reopened and set back to queue.", "success")
    return redirect(url_for("raw_mats_waterjet_bp.waterjet_detail", op_id=op.id))
    
@raw_mats_waterjet_bp.route("/<int:op_id>/block", methods=["POST"])
@login_required
def waterjet_block(op_id):
    op = BuildOperation.query.get_or_404(op_id)
    
    detail = WaterjetOperationDetail.query.filter_by(build_operation_id=op.id).first()
    if not detail:
        detail = WaterjetOperationDetail(build_operation_id=op.id, updated_at=datetime.utcnow())
        db.session.add(detail)

    reason = (request.form.get("blocked_reason") or "").strip().lower()
    notes = (request.form.get("blocked_notes") or "").strip()

    if not reason:
        flash("Blocked reason is required.", "danger")
        return redirect(url_for("raw_mats_waterjet_bp.waterjet_detail", op_id=op.id))

    # Allow other with optional notes
    detail.blocked_reason = reason
    detail.blocked_notes = notes or None
    detail.updated_at = datetime.utcnow()

    op.status = STATUS_BLOCKED
    db.session.commit()

    flash("Operation blocked.", "warning")
    return redirect(url_for("raw_mats_waterjet_bp.waterjet_detail", op_id=op.id))
