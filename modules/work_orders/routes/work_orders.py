# File path: modules/work_orders/routes/work_orders.py
from datetime import datetime
from flask import render_template, request, redirect, url_for, flash

from database.models import db, WorkOrder, WorkOrderLine, Part, Customer
from modules.user.decorators import login_required
from modules.work_orders import work_orders_bp
from modules.inventory.services.parts_service import validate_part_for_work_order

OPEN_WO_STATUSES = ("open", "in_progress")


def _next_wo_number():
    last = WorkOrder.query.order_by(WorkOrder.id.desc()).first()
    if not last or not last.wo_number:
        return "WO-0001"
    try:
        prefix, num = last.wo_number.split("-")
        n = int(num) + 1
        return f"{prefix}-{n:04d}"
    except Exception:
        return f"WO-{(last.id + 1):04d}"


@work_orders_bp.route("/work_orders")
@login_required
def wo_index():
    status = (request.args.get("status") or "").strip()
    customers = Customer.query.order_by(Customer.name.asc()).all()
    q = WorkOrder.query
    if status:
        q = q.filter(WorkOrder.status == status)
    work_orders = q.order_by(WorkOrder.created_at.desc(), WorkOrder.id.desc()).all()
    return render_template("work_orders/work_orders/index.html", work_orders=work_orders, status=status)


@work_orders_bp.route("/work_orders/new")
@login_required
def wo_new():
    customers = Customer.query.order_by(Customer.name.asc()).all()
    default_wo_number = _next_wo_number()
    return render_template(
        "work_orders/work_orders/new.html",
        customers=customers,
        default_wo_number=default_wo_number,
    )


@work_orders_bp.route("/work_orders/create", methods=["POST"])
@login_required
def wo_create():
    wo_number = (request.form.get("wo_number") or "").strip()
    title = (request.form.get("title") or "").strip()
    notes = (request.form.get("notes") or "").strip()
    status = (request.form.get("status") or "open").strip()
    customer_id = request.form.get("customer_id", type=int)

    if not customer_id:
        flash("Customer is required.", "error")
        return redirect(url_for("work_orders_bp.wo_new"))

    if not wo_number:
        flash("WO number is required.", "error")
        return redirect(url_for("work_orders_bp.wo_new"))

    exists = WorkOrder.query.filter_by(wo_number=wo_number).first()
    if exists:
        flash("That WO number already exists.", "error")
        return redirect(url_for("work_orders_bp.wo_new"))

    wo = WorkOrder(
        customer_id=customer_id,
        wo_number=wo_number,
        title=title or None,
        notes=notes or None,
        status=status if status in ("open", "in_progress", "complete", "cancelled") else "open",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.session.add(wo)
    db.session.commit()

    flash("Work Order created.", "success")
    return redirect(url_for("work_orders_bp.wo_detail", wo_id=wo.id))


@work_orders_bp.route("/work_orders/<int:wo_id>")
@login_required
def wo_detail(wo_id):
    wo = WorkOrder.query.get_or_404(wo_id)

    parts = Part.query.order_by(Part.part_number.asc()).all()

    lines = (
        WorkOrderLine.query
        .filter(WorkOrderLine.work_order_id == wo.id)
        .order_by(WorkOrderLine.line_no.asc(), WorkOrderLine.id.asc())
        .all()
    )

    return render_template("work_orders/work_orders/detail.html", wo=wo, parts=parts, lines=lines)

@work_orders_bp.route("/work_orders/<int:wo_id>/delete", methods=["POST"])
@login_required
def wo_delete(wo_id):
    wo = WorkOrder.query.get_or_404(wo_id)

    # 🔒 Safety rule (recommended)
    # Only allow delete if WO has not been applied to builds
    if wo.status not in ("draft", "open"):
        flash("This work order cannot be deleted because it has already been applied.", "danger")
        return redirect(url_for("work_orders_bp.wo_detail", wo_id=wo.id))

    # Optional: ensure no builds exist
    #if wo.builds:
        #flash("This work order has builds and cannot be deleted.", "danger")
        #return redirect(url_for("work_orders_bp.wo_detail", wo_id=wo.id))

    # Delete lines first (SQLite FK safety)
    for line in wo.lines:
        db.session.delete(line)

    db.session.delete(wo)
    db.session.commit()

    flash("Work order deleted.", "success")
    return redirect(url_for("work_orders_bp.wo_index"))

@work_orders_bp.route("/work_orders/<int:wo_id>/status", methods=["POST"])
@login_required
def wo_update_status(wo_id):
    wo = WorkOrder.query.get_or_404(wo_id)
    status = (request.form.get("status") or "").strip()

    if status not in ("open", "in_progress", "complete", "cancelled"):
        flash("Invalid status.", "error")
        return redirect(url_for("work_orders_bp.wo_detail", wo_id=wo.id))

    wo.status = status
    db.session.commit()
    flash("Status updated.", "success")
    return redirect(url_for("work_orders_bp.wo_detail", wo_id=wo.id))


@work_orders_bp.route("/work_orders/<int:wo_id>/lines/add", methods=["POST"])
@login_required
def wo_add_line(wo_id):
    wo = WorkOrder.query.get_or_404(wo_id)

    part_id = request.form.get("part_id", type=int)
    qty_requested = request.form.get("qty_requested", type=float) or 0.0
    config_key = (request.form.get("config_key") or "").strip() or None
    line_no = request.form.get("line_no", type=int) or None
    notes = (request.form.get("notes") or "").strip() or None
    make_method = (request.form.get("make_method") or "MAKE").strip().upper()
    
    if make_method not in ("MAKE", "BUY", "OUTSOURCE"):
        make_method = "MAKE"

    if not part_id:
        flash("Select a part.", "error")
        return redirect(url_for("work_orders_bp.wo_detail", wo_id=wo.id))

    if qty_requested <= 0:
        flash("Quantity must be greater than 0.", "error")
        return redirect(url_for("work_orders_bp.wo_detail", wo_id=wo.id))

    part = Part.query.get_or_404(part_id)

    ok, msg = validate_part_for_work_order(part.id)  # or part_id — either works
    if not ok:
        flash(msg, "danger")
        return redirect(url_for("work_orders_bp.wo_detail", wo_id=wo.id))


    if line_no is None:
        last_line = (
            WorkOrderLine.query
            .filter_by(work_order_id=wo.id)
            .order_by(WorkOrderLine.line_no.desc())
            .first()
        )
        line_no = (last_line.line_no + 1) if last_line else 1

    exists = WorkOrderLine.query.filter_by(work_order_id=wo.id, line_no=line_no).first()
    if exists:
        flash("That line number already exists in this Work Order.", "error")
        return redirect(url_for("work_orders_bp.wo_detail", wo_id=wo.id))

    line = WorkOrderLine(
        work_order_id=wo.id,
        part_id=part.id,
        part_number=part.part_number,
        name=part.name,
        description=part.description,
        qty_requested=float(qty_requested),
        unit=part.unit or "ea",
        config_key=config_key,
        make_method=make_method, 
        source="manual",
        line_no=line_no,
        notes=notes,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.session.add(line)
    db.session.commit()

    flash("Line added.", "success")
    return redirect(url_for("work_orders_bp.wo_detail", wo_id=wo.id))


@work_orders_bp.route("/work_orders/lines/<int:line_id>/delete", methods=["POST"])
@login_required
def wo_delete_line(line_id):
    line = WorkOrderLine.query.get_or_404(line_id)
    wo_id = line.work_order_id

    db.session.delete(line)
    db.session.commit()

    flash("Line deleted.", "success")
    return redirect(url_for("work_orders_bp.wo_detail", wo_id=wo_id))
