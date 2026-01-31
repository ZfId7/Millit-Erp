# File path: modules/work_orders/routes/apply.py
from flask import render_template, redirect, url_for, flash
from modules.user.decorators import login_required
from database.models import db, WorkOrder
from modules.work_orders import work_orders_bp
from modules.work_orders.services.apply import apply_work_order_to_new_build
from modules.inventory.services.parts_service import validate_part_for_work_order

@work_orders_bp.route("/work_orders/<int:wo_id>/apply")
@login_required
def wo_apply_preview(wo_id):
    wo = WorkOrder.query.get_or_404(wo_id)

    lines = list(wo.lines)
    total_lines = len(lines)
    total_qty = sum(float(l.qty_requested or 0.0) for l in lines)
    
    line_checks = []
    blocking_count = 0

    for l in lines:
        ok, msg = validate_part_for_work_order(l.part_id)
        if not ok:
            blocking_count += 1
        line_checks.append({
            "line_id": l.id,
            "line_no": l.line_no,
            "part_number": l.part_number,
            "ok": ok,
            "msg": msg,
        })

    return render_template(
        "work_orders/work_orders/apply.html",
        wo=wo,
        lines=lines,
        total_lines=total_lines,
        total_qty=total_qty,
        line_checks=line_checks,
        blocking_count=blocking_count,
    )


@work_orders_bp.route("/work_orders/<int:wo_id>/apply/execute", methods=["POST"])
@login_required
def wo_apply_execute(wo_id):
    wo = WorkOrder.query.get_or_404(wo_id)

    if wo.status in ("cancelled", "complete"):
        flash("Cannot apply: Work Order is cancelled/complete.", "error")
        return redirect(url_for("work_orders_bp.wo_detail", wo_id=wo.id))
        
    # 🔒 WO Gate (apply): validate every line before doing ANY apply work
    failures = []
    for line in wo.lines:
        ok, msg = validate_part_for_work_order(line.part_id)
        if not ok:
            failures.append(msg)

    if failures:
        flash("Cannot apply Work Order. Fix these issues first:", "error")
        for m in failures:
            flash(m, "error")
        return redirect(url_for("work_orders_bp.wo_detail", wo_id=wo.id))

    try:
        build = apply_work_order_to_new_build(wo_id)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        flash(f"Apply failed: {e}", "error")
        return redirect(url_for("work_orders_bp.wo_detail", wo_id=wo.id))

    flash("Work Order applied to a new Build run.", "success")
    return redirect(url_for("jobs_bp.build_bom", build_id=build.id))
