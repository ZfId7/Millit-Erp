# File path: modules/manufacturing/routes/details.py

from flask import render_template, flash, redirect, url_for
from modules.manufacturing import mfg_bp
from modules.user.decorators import login_required
from database.models import BuildOperation, BuildOperationProgress
from modules.manufacturing.services.progress_service import get_op_totals

@mfg_bp.route("/op/<int:op_id>", methods=["GET"])
@login_required
def mfg_details(op_id):
    op = BuildOperation.query.get_or_404(op_id)

    if op.module_key != "manufacturing":
        flash("Invalid operation for Manufacturing.", "error")
        return redirect(url_for("mfg_bp.mfg_queue"))

    totals = get_op_totals(op.id)

    progress_updates = (
        BuildOperationProgress.query
        .filter_by(build_operation_id=op.id)
        .order_by(BuildOperationProgress.created_at.desc(), BuildOperationProgress.id.desc())
        .all()
    )

    return render_template(
        "manufacturing/details.html", 
        op=op,
        totals=totals,
        progress_updates=progress_updates,
    )
