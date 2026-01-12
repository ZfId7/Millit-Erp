# File path: modules/manufacturing/routes/details.py
# -V1 Base Build
from flask import render_template, flash, redirect, url_for
from modules.manufacturing import mfg_bp
from modules.user.decorators import login_required
from database.models import BuildOperation

@mfg_bp.route("/op/<int:op_id>", methods=["GET"])
@login_required
def mfg_details(op_id):
    op = BuildOperation.query.get_or_404(op_id)

    if op.module_key != "manufacturing":
        flash("Invalid operation for Manufacturing.", "error")
        return redirect(url_for("mfg_bp.mfg_queue"))

    return render_template("manufacturing/details.html", op=op)
