# File path: modules/surface_grinding/routes/ops.py
# V1 Refactor Ops
# V2 Change complete route to run through ops_flow
from flask import request, redirect, url_for, flash

from database.models import db, BuildOperation
from modules.user.decorators import login_required
from modules.surface_grinding import surface_bp
from modules.jobs_management.services.ops_flow import complete_operation

# Terminal guard (canonical + legacy)
STATUS_COMPLETED = "completed"   # canonical terminal
STATUS_CANCELLED = "cancelled"   # canonical terminal

STATUS_IN_PROGRESS = "in_progress"
STATUS_QUEUE = "queue"
STATUS_BLOCKED = "blocked"

#Legacy/compat
LEGACY_COMPLETE = "complete"


TERMINAL_STATUSES = (
    STATUS_COMPLETED,
    STATUS_CANCELLED,
    LEGACY_COMPLETE,
)

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
    if op.status in TERMINAL_STATUSES:
        flash(f"Cannot start: operation is {op.status}.", "error")
        return _redirect_queue()

    op.status = STATUS_IN_PROGRESS
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

    if op.status == STATUS_COMPLETED:
        flash("Cannot cancel: operation is completed.", "error")
        return _redirect_queue()

    op.status = STATUS_CANCELLED
    db.session.commit()
    flash("Operation cancelled.", "success")
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
