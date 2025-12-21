# File path: modules/job_management/services/routing.py
from database.models import db, RoutingTemplate, BuildOperation

ALLOWED_OP_STATUSES = {"queue", "in_progress", "complete"}

def ensure_operations_for_bom_item(bom_item):
    part = bom_item.part
    if not part or not getattr(part, "part_type_id", None):
        return

    templates = (
        RoutingTemplate.query
        .filter_by(part_type_id=part.part_type_id)
        .order_by(RoutingTemplate.sequence.asc())
        .all()
    )
    if not templates:
        return

    # ✅ Planned qty is PER-ASSEMBLY qty * assemblies ordered
    assemblies = float(getattr(bom_item.build, "qty_ordered", 0) or 0)
    per_assembly = float(bom_item.qty or 0)
    planned_qty = assemblies * per_assembly

    for t in templates:
        op = BuildOperation.query.filter_by(
            build_id=bom_item.build_id,
            bom_item_id=bom_item.id,
            op_key=t.op_key,
        ).first()

        if op:
            op.qty_planned = planned_qty
            continue

        db.session.add(BuildOperation(
            build_id=bom_item.build_id,
            bom_item_id=bom_item.id,
            op_key=t.op_key,
            op_name=t.op_name,
            module_key=t.module_key,
            sequence=t.sequence,
            is_outsourced=bool(getattr(t, "is_outsourced", False)),
            qty_planned=planned_qty,
            status="queue",
        ))



def delete_operations_for_bom_item(bom_item_id: int):
    """Call this when a BOM line is deleted."""
    BuildOperation.query.filter_by(bom_item_id=bom_item_id).delete()
