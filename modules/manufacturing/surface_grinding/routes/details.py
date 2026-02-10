# File path: modules/manufacturing/surface_grinding/routes/details.py
# V1 Refactor | Base Build for surface/details

from flask import render_template, redirect, url_for, flash, request

from database.models import db, BuildOperation
from modules.user.decorators import login_required
from .. import surface_bp


@surface_bp.route("/details/<int:op_id>", methods=["GET"])
@login_required
def surface_details(op_id):
    op = BuildOperation.query.get_or_404(op_id)

    if op.module_key != "surface_grinding":
        flash("That operation does not belong to Surface Grinding.", "error")
        return redirect(url_for("surface_bp.surface_grinding_queue"))

    return render_template("surface_grinding/details.html", op=op)


@surface_bp.route("/details/<int:op_id>/edit", methods=["GET", "POST"])
@login_required
def surface_details_edit(op_id):
    op = BuildOperation.query.get_or_404(op_id)

    if op.module_key != "surface_grinding":
        flash("That operation does not belong to Surface Grinding.", "error")
        return redirect(url_for("surface_bp.surface_grinding_queue"))

    if request.method == "POST":
        # TODO: Save SurfaceGrindingOperationDetail fields (next step)
        flash("Saved (detail model wiring coming next).", "success")
        return redirect(url_for("surface_bp.surface_grinding_details", op_id=op.id))

    return render_template("surface_grinding/details_edit.html", op=op)
