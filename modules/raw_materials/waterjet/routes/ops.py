# File path: modules/raw_materials/waterjet/routes/ops.py
# V1 Refactor Status Actions
# V2 Refactor | moved inside raw_materials/waterjet/routes/ops | changed blueprint to raw_mats_waterjet_bp
from flask import redirect, url_for, flash


from modules.user.decorators import login_required
from modules.raw_materials.waterjet import raw_mats_waterjet_bp
from modules.jobs_management.services.ops_flow import complete_operation
from database.models import db, BuildOperation

@raw_mats_waterjet_bp.route("/<int:op_id>/start", methods=["POST"])
@login_required
def waterjet_start(op_id):
    op = BuildOperation.query.get_or_404(op_id)
   


    if op.status in ("complete", "cancelled"):
        flash("This operation is already closed.", "warning")
        return redirect(url_for("raw_mats_waterjet_bp.waterjet_detail", op_id=op.id))


    op.status = "in_progress"
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
   


    op.status = "cancelled"
    db.session.commit()
    flash("Operation cancelled.", "success")
    return redirect(url_for("raw_mats_waterjet_bp.waterjet_detail", op_id=op.id))

@raw_mats_waterjet_bp.route("/<int:op_id>/reopen", methods=["POST"])
@login_required
def waterjet_reopen(op_id):
    op = BuildOperation.query.get_or_404(op_id)


  


    if op.status != "cancelled":
        flash("Only cancelled operations can be reopened.", "warning")
        return redirect(url_for("raw_mats_waterjet_bp.waterjet_detail", op_id=op.id))


    op.status = "queue"
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

    op.status = "blocked"
    db.session.commit()

    flash("Operation blocked.", "warning")
    return redirect(url_for("raw_mats_waterjet_bp.waterjet_detail", op_id=op.id))