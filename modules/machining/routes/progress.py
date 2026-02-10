# File path: modules/machining/routes/progress.py

from flask import request, redirect, url_for, flash, session

from database.models import db

from modules.machining import mfg_bp
from modules.user.decorators import login_required
from modules.machining.services.progress_service import add_op_progress, OpProgressError


@mfg_bp.route("/op/<int:op_id>/progress", methods=["POST"])
@login_required
def mfg_progress_add(op_id):
    qty_done_delta = request.form.get("qty_done_delta") or 0
    qty_scrap_delta = request.form.get("qty_scrap_delta") or 0
    note = request.form.get("note") or None

    user_id = session.get("user_id")  # ✅ canonical for v0

    try:
        add_op_progress(
            op_id=op_id,
            qty_done_delta=qty_done_delta,
            qty_scrap_delta=qty_scrap_delta,
            note=note,
            user_id=user_id,
            is_admin=bool(session.get("is_admin")), 
            force=False,
        )
        db.session.commit()
        flash("Progress update added.", "success")
    except OpProgressError as e:
        db.session.rollback()
        flash(str(e), "error")

    return redirect(url_for("mfg_bp.mfg_details", op_id=op_id))
