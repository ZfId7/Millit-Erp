# File path: modules/heat_treat/routes/ops.py
# -V1 Base Build
#- V2 Service upgrades TO DO


from flask import flash, redirect, session, url_for
from sqlalchemy.exc import SQLAlchemyError

from database.models import db, BuildOperation
from modules.user.decorators import login_required

from modules.heat_treat import heat_treat_bp
from modules.shared.services.build_op_claim_service import start_build_operation
from modules.shared.services.build_op_progress_service import OpProgressError
from modules.jobs_management.services.ops_flow import complete_operation  # adjust if different

from modules.shared.status import (
    STATUS_BLOCKED,
    STATUS_COMPLETED,
    LEGACY_COMPLETE,
    TERMINAL_STATUSES,
)

def _redirect_queue(*args, **kwargs):
    return redirect(url_for("heat_treat_bp.heat_treat_queue"))

def _ensure_heat_treat(op: BuildOperation) -> bool:
    if op.module_key != "heat_treat":
        flash("That operation does not belong to Heat Treat.", "error")
        return False
    return True

@heat_treat_bp.route("/op/<int:op_id>/start", methods=["POST"])
@login_required
def heat_treat_start(op_id):
    op = BuildOperation.query.get_or_404(op_id)

    if not _ensure_heat_treat(op):
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


@heat_treat_bp.route("/op/<int:op_id>/block", methods=["POST"])
@login_required
def heat_treat_block(op_id):
    op = BuildOperation.query.get_or_404(op_id)

    if op.status in TERMINAL_STATUSES:
        flash(f"Cannot block: operation is {op.status}.", "error")
        return redirect(url_for("heat_treat_bp.heat_treat_queue"))

    op.status = STATUS_BLOCKED
    db.session.commit()
    flash("Operation blocked.", "success")
    return redirect(url_for("heat_treat_bp.heat_treat_details", op_id=op.id))


@heat_treat_bp.route("/op/<int:op_id>/complete", methods=["POST"])
@login_required
def heat_treat_complete(op_id):
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
