# File path: modules/jobs_management/services/ops_flow.py
# V1 Base Build | Global route for op completion

from database.models import db, BuildOperation

def release_next_for_bom_item(current_op: BuildOperation):
    BuildOperation.query.filter_by(
        build_id=current_op.build_id,
        bom_item_id=current_op.bom_item_id
    ).update(
        {BuildOperation.is_released: False},
        synchronize_session=False
    )

    next_op = (
        BuildOperation.query
        .filter(
            BuildOperation.build_id == current_op.build_id,
            BuildOperation.bom_item_id == current_op.bom_item_id,
            BuildOperation.sequence > current_op.sequence,
            BuildOperation.status.notin_(["complete", "cancelled"]),
        )
        .order_by(BuildOperation.sequence.asc(), BuildOperation.id.asc())
        .first()
    )

    if next_op:
        next_op.is_released = True
        if next_op.status not in ("blocked", "in_progress"):
            next_op.status = "queue"


def complete_operation(op: BuildOperation):
    op.status = "complete"
    op.is_released = False
    if op.bom_item_id is not None:
        release_next_for_bom_item(op)
