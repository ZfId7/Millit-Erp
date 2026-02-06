# File path: modules/raw_materials/waterjet/routes/ops.py
# V1 Refactor Status Actions
# V2 Refactor | moved inside raw_materials/waterjet/routes/ops | changed blueprint to raw_mats_waterjet_bp
import datetime
from flask import redirect, request, url_for, flash, session
from sqlalchemy.exc import SQLAlchemyError

from database.models import WaterjetOperationDetail, db, BuildOperation

from modules.surface_grinding.routes.ops import _redirect_queue
from modules.user.decorators import login_required
from modules.raw_materials.waterjet import raw_mats_waterjet_bp
from modules.jobs_management.services.ops_flow import complete_operation

from modules.shared.services.build_op_claim_service import start_build_operation
from modules.shared.services.build_op_status_service import cancel_build_operation
from modules.shared.services.build_op_progress_service import OpProgressError


from modules.shared.status import (
    STATUS_BLOCKED,
    STATUS_COMPLETED,
    STATUS_CANCELLED,
    LEGACY_COMPLETE,
    STATUS_IN_PROGRESS,
    STATUS_QUEUE,
    TERMINAL_STATUSES,
)


def _redirect_queue(*args, **kwargs):
    return redirect(url_for("raw_mats_waterjet_bp.waterjet_queue"))

def _ensure_waterjet(op: BuildOperation) -> bool:
    if op.module_key != "raw_materials":
        flash("That operation does not belong to Waterjet.", "error")
        return False
    return True

@raw_mats_waterjet_bp.route("/<int:op_id>/start", methods=["POST"])
@login_required
def waterjet_start(op_id):
    op = BuildOperation.query.get_or_404(op_id)
   
    if not _ensure_waterjet(op):
        return _redirect_queue()

    if op.status in TERMINAL_STATUSES:
        flash(f"Cannot start: operation is {op.status}.", "error")
        return redirect(url_for("raw_mats_waterjet_bp.waterjet_detail", op_id=op.id))


    try:
        start_build_operation(
            op_id=op.id,
            user_id=session.get("user_id"),
            is_admin=bool(session.get("is_admin")),
            force=False,
            note=None,
        )
        db.session.commit()
        flash("Operation started.", "success")
    except OpProgressError as e:
        db.session.rollback()
        flash(str(e), "error")
    except SQLAlchemyError:
        db.session.rollback()
        flash("Database error while starting operation.", "error")

    return _redirect_queue()

@raw_mats_waterjet_bp.route("/<int:op_id>/complete", methods=["POST"])
@login_required
def waterjet_complete(op_id):
    op = BuildOperation.query.get_or_404(op_id)
   

    if op.status in TERMINAL_STATUSES:
        flash(f"Cannot complete: operation is {op.status}.", "error")
        return _redirect_queue()

    try:
        complete_operation(
            op, 
            user_id=session.get("user_id"), 
            is_admin=bool(session.get("is_admin"))
            # note=request.form.get("note"), #later when UI supports override notes
        )    
        db.session.commit()
        flash("Operation completed. Next operation released.", "success")
    except ValueError as e:
        db.session.rollback()
        flash(str(e), "warning")
    except Exception:
        db.session.rollback()
        raise


    return _redirect_queue()

@raw_mats_waterjet_bp.route("/<int:op_id>/cancel", methods=["POST"])
@login_required
def waterjet_cancel(op_id):
    op = BuildOperation.query.get_or_404(op_id)
   
    try:
        cancel_build_operation(
            op_id=op.id,
            user_id=session.get("user_id"),
            is_admin=bool(session.get("is_admin")),
        )

        db.session.commit()
        flash("Operation cancelled.", "success")
    except OpProgressError as e:
        db.session.rollback()
        flash(str(e), "error")
    except SQLAlchemyError:
        db.session.rollback()
        flash("Database error while cancelling operation.", "error")

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
