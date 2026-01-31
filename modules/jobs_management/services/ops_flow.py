# File path: modules/jobs_management/services/ops_flow.py
# V1 Base Build | Global route for op completion

from database.models import db, BuildOperation

# Canonical status strings (v0 normalization)
STATUS_QUEUE = "queue"
STATUS_IN_PROGRESS = "in_progress"
STATUS_BLOCKED = "blocked"
STATUS_COMPLETED = "completed"   # canonical terminal
STATUS_CANCELLED = "cancelled"   # canonical terminal

# Legacy/compat
LEGACY_COMPLETE = "complete"

TERMINAL_STATUSES = {STATUS_COMPLETED, STATUS_CANCELLED, LEGACY_COMPLETE}


def release_next_for_bom_item(current_op: BuildOperation):
    # Release gating is per BOM item within a build
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
            BuildOperation.status.notin_(list(TERMINAL_STATUSES)),
        )
        .order_by(BuildOperation.sequence.asc(), BuildOperation.id.asc())
        .first()
    )

    if next_op:
        next_op.is_released = True
        if next_op.status not in (STATUS_BLOCKED, STATUS_IN_PROGRESS):
            next_op.status = STATUS_QUEUE


def complete_operation(op: BuildOperation):
    # Canonical terminal state
    op.status = STATUS_COMPLETED
    op.is_released = False

    if op.bom_item_id is not None:
        release_next_for_bom_item(op)
