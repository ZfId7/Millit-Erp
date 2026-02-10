# File path: modules/manufacturing/machining/routes/machines.py

from flask import render_template, request, redirect, url_for, flash
from .. import mfg_bp
from modules.user.decorators import login_required
from database.models import db, BuildOperation, Machine

from modules.manufacturing.machining.services.dispatch_service import (
    get_active_machines,
    assign_op_to_machine,
    unassign_op,
    DispatchError,
)

from modules.manufacturing.machining.services.machine_service import (
    get_machine_by_id,
    get_machine_queue,
    get_machine_by_key,
)


@mfg_bp.route("/machines", methods=["GET"])
@login_required
def mfg_machines_index():
    machines = get_active_machines()
    return render_template("machining/machines.html", machines=machines)


@mfg_bp.route("/machines/<int:machine_id>", methods=["GET"])
@login_required
def mfg_machine_detail(machine_id):
    machine = get_machine_by_id(machine_id)
    queue = get_machine_queue(machine)
    return render_template("machining/machine_detail.html", machine=machine, queue=queue)

@mfg_bp.route("/machines/<int:machine_id>/claim/<int:op_id>", methods=["POST"])
@login_required
def mfg_machine_claim(machine_id, op_id):
    machine = Machine.query.get_or_404(machine_id)
    op = BuildOperation.query.get_or_404(op_id)

    try:
        assign_op_to_machine(op, machine)
        db.session.commit()
        flash("Operation claimed.", "success")
    except DispatchError as e:
        db.session.rollback()
        flash(str(e), "error")

    return redirect(request.referrer or url_for("mfg_bp.mfg_machine_detail", machine_id=machine_id))


@mfg_bp.route("/machines/<int:machine_id>/release/<int:op_id>", methods=["POST"])
@login_required
def mfg_machine_release(machine_id, op_id):
    op = BuildOperation.query.get_or_404(op_id)

    try:
        unassign_op(op)
        db.session.commit()
        flash("Operation released.", "info")
    except DispatchError as e:
        db.session.rollback()
        flash(str(e), "error")

    return redirect(request.referrer or url_for("mfg_bp.mfg_machine_detail", machine_id=machine_id))

@mfg_bp.route("/machines/by_key/<string:machine_key>", methods=["GET"])
@login_required
def mfg_machine_detail_by_key(machine_key):
    machine = get_machine_by_key(machine_key)

    # Option 1 (cleanest): redirect to canonical ID URL
    return redirect(url_for("mfg_bp.mfg_machine_detail", machine_id=machine.id))
