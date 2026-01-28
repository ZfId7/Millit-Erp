# File path: modules/jobs_management/services/routing.py
# -V1 Base Build
# -V2 Add enforce_release_state_for_bom_item

from database.models import db, RoutingTemplate, BuildOperation, RoutingHeader, RoutingStep, BOMLine

ALLOWED_OP_STATUSES = {"queue", "in_progress", "complete"}

def get_active_routing_header_for_part(part_id: int):
    return (RoutingHeader.query
            .filter_by(part_id=part_id, is_active=True)
            .order_by(RoutingHeader.rev.desc())
            .first())

def get_routing_steps_for_bom_item(bom_item):
    """
    Returns a list of step-like objects with op_key/op_name/module_key/sequence/is_outsourced.
    Priority:
      1) BOMLine.routing_override_id (if bom_item originates from master BOM)
      2) RoutingHeader active for component part
      3) Legacy RoutingTemplate by PartType (transition fallback)
    """
    # Try BOMLine override if this bom_item came from a BOMHeader snapshot
    if bom_item.bom_header_id and bom_item.part_id:
        line = (BOMLine.query
                .filter_by(bom_id=bom_item.bom_header_id, component_part_id=bom_item.part_id)
                .order_by(BOMLine.line_no.asc())
                .first())
        if line:
            # respect MAKE/BUY/OUTSOURCE (BUY = no ops, OUTSOURCE = routing steps can exist if you want)
            if (line.make_method or "MAKE").upper() == "BUY":
                return []

            if line.routing_override_id:
                override = RoutingHeader.query.get(line.routing_override_id)
                if override:
                    return (RoutingStep.query
                            .filter_by(routing_id=override.id)
                            .order_by(RoutingStep.sequence.asc())
                            .all())

    # Default part routing
    rh = get_active_routing_header_for_part(bom_item.part_id)
    if rh:
        return (RoutingStep.query
                .filter_by(routing_id=rh.id)
                .order_by(RoutingStep.sequence.asc())
                .all())

    

    return []

def ensure_operations_for_bom_item(bom_item):
    part = bom_item.part
    if not part:
        return

    steps = get_routing_steps_for_bom_item(bom_item)
    if not steps:
        return

    planned_qty = float(getattr(bom_item, "qty_planned", None) or bom_item.qty or 0.0)

    for s in steps:
        op = BuildOperation.query.filter_by(
            build_id=bom_item.build_id,
            bom_item_id=bom_item.id,
            op_key=s.op_key,
        ).first()

        if op:
            op.qty_planned = planned_qty
            op.op_name = s.op_name
            op.module_key = s.module_key
            op.sequence = s.sequence
            op.is_outsourced = bool(getattr(s, "is_outsourced", False))
            continue

        db.session.add(BuildOperation(
            build_id=bom_item.build_id,
            bom_item_id=bom_item.id,
            op_key=s.op_key,
            op_name=s.op_name,
            module_key=s.module_key,
            sequence=s.sequence,
            is_outsourced=bool(getattr(s, "is_outsourced", False)),
            qty_planned=planned_qty,
            status="queue",
        ))

    enforce_release_state_for_bom_item(build_id=bom_item.build_id, bom_item_id=bom_item.id)

def delete_queued_operations_for_bom_item(bom_item_id: int) -> int:
    """
    SAFE delete: only queued operations may be deleted.
    Returns count deleted.
    """
    deleted = (
        BuildOperation.query
        .filter(
            BuildOperation.bom_item_id == bom_item_id,
            BuildOperation.status == "queue",
        )
        .delete(synchronize_session=False)
    )
    db.session.flush()
    return int(deleted or 0)


def delete_operations_for_bom_item(bom_item_id: int) -> int:
    """
    Backward-compatible wrapper.
    NOTE: This no longer deletes non-queued operations.
    """
    return delete_queued_operations_for_bom_item(bom_item_id)

def enforce_release_state_for_bom_item(build_id: int, bom_item_id: int):
    ops = (
        BuildOperation.query
        .filter_by(build_id=build_id, bom_item_id=bom_item_id)
        .order_by(BuildOperation.sequence.asc(), BuildOperation.id.asc())
        .all()
    )

    # Reset all
    for op in ops:
        op.is_released = False

    # Find first non-complete/non-cancelled op
    first = next(
        (o for o in ops if o.status not in ("complete", "cancelled")),
        None
    )

    if first:
        first.is_released = True

    # Ensure completed ops are never "released"
    for op in ops:
        if op.status == "complete":
            op.is_released = False




