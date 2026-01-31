# File path: modules/heat_treat/routes/details.py
# -V1 Base Build
from flask import render_template, flash, redirect, url_for
from database.models import BuildOperation

from modules.heat_treat import heat_treat_bp
from modules.user.decorators import login_required

from modules.manufacturing.services.progress_service import get_op_totals

@heat_treat_bp.route("/op/<int:op_id>", methods=["GET"])
@login_required
def heat_treat_details(op_id):
    op = BuildOperation.query.get_or_404(op_id)

    if op.module_key != "heat_treat":
        flash("Invalid operation for Heat Treat.", "error")
        return redirect(url_for("heat_treat_bp.heat_treat_queue"))
    
    totals = get_op_totals(op.id)

    return render_template("heat_treat/details.html", op=op, totals=totals)
