# File path: modules/manufacturing/routes/dispatch.py

from flask import render_template, request, redirect, url_for, flash
from modules.manufacturing import mfg_bp
from modules.user.decorators import login_required
from database.models import db, BuildOperation, Machine

from modules.manufacturing.services.dispatch_service import (
    get_dispatchable_ops,
    get_active_machines,
    assign_op_to_machine,
    unassign_op,
    DispatchError,
)


@mfg_bp.route("/dispatch", methods=["GET"])
@login_required
def mfg_dispatch():
    ops = get_dispatchable_ops()
    machines = get_active_machines()
    return render_template("manufacturing/dispatch.html", ops=ops, machines=machines)


@mfg_bp.route("/dispatch/assign", methods=["POST"])
@login_required
def mfg_dispatch_assign():
    op_id = request.form.get("op_id", type=int)
    machine_id = request.form.get("machine_id", type=int)

    if not op_id or not machine_id:
        flash("Missing op_id or machine_id.", "error")
        return redirect(request.referrer or url_for("mfg_bp.mfg_dispatch"))

    op = BuildOperation.query.get_or_404(op_id)
    machine = Machine.query.get_or_404(machine_id)

    try:
        assign_op_to_machine(op, machine)
        db.session.commit()
        flash("Operation assigned.", "success")
    except DispatchError as e:
        db.session.rollback()
        flash(str(e), "error")

    return redirect(request.referrer or url_for("mfg_bp.mfg_dispatch"))


@mfg_bp.route("/dispatch/unassign/<int:op_id>", methods=["POST"])
@login_required
def mfg_dispatch_unassign(op_id):
    op = BuildOperation.query.get_or_404(op_id)

    try:
        unassign_op(op)
        db.session.commit()
        flash("Operation unassigned.", "info")
    except DispatchError as e:
        db.session.rollback()
        flash(str(e), "error")

    return redirect(request.referrer or url_for("mfg_bp.mfg_dispatch"))
