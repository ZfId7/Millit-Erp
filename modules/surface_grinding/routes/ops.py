# File path: modules/surface_grinding/routes/ops.py
# V1 Refactor Ops
# V2 Change complete route to run through ops_flow
from flask import request, redirect, session, url_for, flash
from sqlalchemy.exc import SQLAlchemyError

from database.models import db, BuildOperation

from modules.user.decorators import login_required
from modules.surface_grinding import surface_bp
from modules.jobs_management.services.ops_flow import complete_operation

from modules.shared.services.build_op_claim_service import start_build_operation
from modules.shared.services.build_op_progress_service import OpProgressError
from modules.shared.services.build_op_status_service import cancel_build_operation

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
    return redirect(url_for("surface_grinding_bp.surface_queue"))
    
def _ensure_surface_grinding(op: BuildOperation) -> bool:
    if op.module_key != "surface_grinding":
        flash("That operation does not belong to Surface Grinding.", "error")
        return False
    return True

@surface_bp.route("/op/<int:op_id>/start", methods=["POST"])
@login_required
def surface_start(op_id):
    op = BuildOperation.query.get_or_404(op_id)

    if not _ensure_surface_grinding(op):
        return _redirect_queue()

    # Keep the quick terminal guard for nicer UX (service also guards)
    if op.status in TERMINAL_STATUSES:
        flash(f"Cannot start: operation is {op.status}.", "error")
        return _redirect_queue()

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


@surface_bp.route("/op/<int:op_id>/complete", methods=["POST"])
@login_required
def surface_complete(op_id):
    op = BuildOperation.query.get_or_404(op_id)

    if op.status in TERMINAL_STATUSES:
        flash(f"Cannot complete: operation is {op.status}.", "error")
        return _redirect_queue()

    complete_operation(
        op,
        user_id=session.get("user_id"),
        is_admin=bool(session.get("is_admin")),
    )    

    db.session.commit()
    flash("Operation completed. Next operation released.", "success")
    return _redirect_queue()
    
@surface_bp.route("/op/<int:op_id>/cancel", methods=["POST"])
@login_required
def surface_cancel(op_id):
    op = BuildOperation.query.get_or_404(op_id)

    if not _ensure_surface_grinding(op):
        return _redirect_queue()

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

    return _redirect_queue()
    
@surface_bp.route("/op/<int:op_id>/block", methods=["POST"])
@login_required
def surface_block(op_id):
    op = BuildOperation.query.get_or_404(op_id)

    if not _ensure_surface_grinding(op):
        return _redirect_queue()

    if op.status in TERMINAL_STATUSES:
        flash(f"Cannot block: operation is {op.status}.", "error")
        return _redirect_queue()

    op.status = STATUS_BLOCKED
    db.session.commit()
    flash("Operation blocked.", "success")
    return _redirect_queue()


@surface_bp.route("/op/<int:op_id>/reopen", methods=["POST"])
@login_required
def surface_reopen(op_id):
    op = BuildOperation.query.get_or_404(op_id)

    if not _ensure_surface_grinding(op):
        return _redirect_queue()

    if op.status not in (STATUS_BLOCKED, STATUS_CANCELLED):
        flash("Only blocked/cancelled operations can be reopened.", "error")
        return _redirect_queue()

    op.status = STATUS_QUEUE
    db.session.commit()
    flash("Operation reopened and returned to queue.", "success")
    return _redirect_queue()
