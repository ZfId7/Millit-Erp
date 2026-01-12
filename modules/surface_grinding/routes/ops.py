# File path: modules/surface_grinding/routes/ops.py
# V1 Refactor Ops
# V2 Change complete route to run through ops_flow
from flask import request, redirect, url_for, flash

from database.models import db, BuildOperation
from modules.user.decorators import login_required
from modules.surface_grinding import surface_bp
from modules.jobs_management.services.ops_flow import complete_operation
def _redirect_queue(*args, **kwargs):
    return redirect(url_for("surface_grinding_bp.surface_queue"))
    
def _ensure_surface_grinding(op: BuildOperation) -> bool:
    if op.module_key != "surface_grinding":
        flash("That operation does not belong to Surface Grinding.", "error")
        return False
    return True

@surface_bp.route("/op/<int:op_id>/start", methods=["POST"])
def surface_start(op_id):
    op = BuildOperation.query.get_or_404(op_id)
    
    if not _ensure_surface_grinding(op):
        return _redirect_queue()

    # Only allow starting from queue
    if op.status in ("complete", "cancelled"):
        flash("Cannot start: operation is already complete.", "error")
        return _redirect_queue()

    op.status = "in_progress"
    db.session.commit()
    flash("Operation started.", "success")
    return _redirect_queue()


@surface_bp.route("/op/<int:op_id>/complete", methods=["POST"])
def surface_complete(op_id):
    op = BuildOperation.query.get_or_404(op_id)

   
    complete_operation(op)

    db.session.commit()
    flash("Operation completed.", "success")
    return _redirect_queue()
    
@surface_bp.route("/op/<int:op_id>/cancel", methods=["POST"])
@login_required
def surface_cancel(op_id):
    op = BuildOperation.query.get_or_404(op_id)

    if not _ensure_surface_grinding(op):
        return _redirect_queue()

    if op.status == "complete":
        flash("Cannot cancel: operation is completed.", "error")
        return _redirect_queue()

    op.status = "cancelled"
    db.session.commit()
    flash("Operation cancelled.", "success")
    return _redirect_queue()
    
@surface_bp.route("/op/<int:op_id>/block", methods=["POST"])
@login_required
def surface_block(op_id):
    op = BuildOperation.query.get_or_404(op_id)

    if not _ensure_surface_grinding(op):
        return _redirect_queue()

    if op.status == "complete":
        flash("Cannot block: operation is completed.", "error")
        return _redirect_queue()

    op.status = "blocked"
    db.session.commit()
    flash("Operation blocked.", "success")
    return _redirect_queue()


@surface_bp.route("/op/<int:op_id>/reopen", methods=["POST"])
@login_required
def surface_reopen(op_id):
    op = BuildOperation.query.get_or_404(op_id)

    if not _ensure_surface_grinding(op):
        return _redirect_queue()

    if op.status not in ("blocked", "cancelled"):
        flash("Only blocked/cancelled operations can be reopened.", "error")
        return _redirect_queue()

    op.status = "queue"
    db.session.commit()
    flash("Operation reopened and returned to queue.", "success")
    return _redirect_queue()