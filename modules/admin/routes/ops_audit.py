# File path: modules/admin/routes/audit.py

from flask import Blueprint, render_template, request
from modules.user.decorators import admin_required
from database.models import db, User, BuildOperation, BuildOperationProgress
from modules.admin import admin_bp

@admin_bp.get("/ops/audit")
@admin_required
def ops_audit():
    # Filters (all optional)
    event_type = (request.args.get("event_type") or "").strip()
    module_key = (request.args.get("module_key") or "").strip()
    op_key = (request.args.get("op_key") or "").strip()
    user_id = (request.args.get("user_id") or "").strip()
    status = (request.args.get("status") or "").strip()

    q = (
        db.session.query(BuildOperationProgress)
        .join(BuildOperation, BuildOperation.id == BuildOperationProgress.build_operation_id)
        .order_by(BuildOperationProgress.created_at.desc())
    )

    if event_type:
        q = q.filter(BuildOperationProgress.event_type == event_type)
    if module_key:
        q = q.filter(BuildOperation.module_key == module_key)
    if op_key:
        q = q.filter(BuildOperation.op_key == op_key)
    if user_id.isdigit():
        q = q.filter(BuildOperationProgress.user_id == int(user_id))
    if status:
        q = q.filter(BuildOperation.status == status)

    # Keep V0 sane
    rows = q.limit(500).all()

    users = User.query.order_by(User.username.asc()).all()

    return render_template(
        "admin/ops_audit.html",
        rows=rows,
        users=users,
        filters={
            "event_type": event_type,
            "module_key": module_key,
            "op_key": op_key,
            "user_id": user_id,
            "status": status,
        },
    )
