# File path: modules/heat_treat/routes/ops.py
# -V1 Base Build

from flask import flash, redirect, url_for
from modules.heat_treat import heat_treat_bp
from modules.user.decorators import login_required
from database.models import db, BuildOperation
from modules.jobs_management.services.ops_flow import complete_operation  # adjust if different

@heat_treat_bp.route("/op/<int:op_id>/start", methods=["POST"])
@login_required
def heat_treat_start(op_id):
    op = BuildOperation.query.get_or_404(op_id)

    if op.status in ("cancelled", "complete"):
        flash("Cannot start: operation is not active.", "error")
        return redirect(url_for("heat_treat_bp.heat_treat_queue"))

    op.status = "in_progress"
    db.session.commit()
    flash("Operation started.", "success")
    return redirect(url_for("heat_treat_bp.heat_treat_details", op_id=op.id))


@heat_treat_bp.route("/op/<int:op_id>/block", methods=["POST"])
@login_required
def heat_treat_block(op_id):
    op = BuildOperation.query.get_or_404(op_id)

    if op.status in ("cancelled", "complete"):
        flash("Cannot block: operation is not active.", "error")
        return redirect(url_for("heat_treat_bp.heat_treat_queue"))

    op.status = "blocked"
    db.session.commit()
    flash("Operation blocked.", "success")
    return redirect(url_for("heat_treat_bp.heat_treat_details", op_id=op.id))


@heat_treat_bp.route("/op/<int:op_id>/complete", methods=["POST"])
@login_required
def heat_treat_complete(op_id):
    op = BuildOperation.query.get_or_404(op_id)

    if op.status == "cancelled":
        flash("Cannot complete: operation is cancelled.", "error")
        return redirect(url_for("heat_treat_bp.heat_treat_queue"))

    complete_operation(op)  # ✅ bounce-safe completion
    db.session.commit()

    flash("Operation completed. Next operation released.", "success")
    return redirect(url_for("heat_treat_bp.heat_treat_queue"))
