# File path: modules/admin/routes/detail.py

from modules.user.decorators import admin_required
from modules.admin import admin_bp
from flask import render_template
from database.models import BuildOperation, BuildOperationProgress

@admin_bp.get("/ops/<int:op_id>")
@admin_required
def op_detail(op_id: int):
    op = BuildOperation.query.get_or_404(op_id)

    events = (
        BuildOperationProgress.query
        .filter_by(build_operation_id=op.id)
        .order_by(BuildOperationProgress.created_at.asc())
        .all()
    )

    return render_template("admin/op_detail.html", op=op, events=events)
