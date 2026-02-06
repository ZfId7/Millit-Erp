# File path: modules/jobs_management/services/ops_flow.py
# V1 Base Build | Global route for op completion

from database.models import db, BuildOperation

from modules.shared.claims import release_claim
from modules.shared.services.build_op_progress_service import add_op_event

from modules.shared.status import (
    STATUS_QUEUE,
    STATUS_IN_PROGRESS,
    STATUS_BLOCKED,
    STATUS_COMPLETED,
    STATUS_CANCELLED,
    LEGACY_COMPLETE,
    TERMINAL_STATUSES,
)


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


def complete_operation(op: BuildOperation, *, user_id: int = None, is_admin: bool = False, note: str = None):
    # Ready-to-complete gating (required good parts only)
    required = float(getattr(op, "qty_required", 0) or 0)
    done = float(getattr(op, "qty_done", 0) or 0)

    if required <= 0:
        raise ValueError("Cannot complete: qty_required is not set (or is 0).")

    if done < required:
        remaining = required - done
        msg = f"Cannot complete: {remaining:g} required good parts remaining (done {done:g} / required {required:g})."

        # Admin override path: allowed, but must be explicit + audited
        if not is_admin:
            raise ValueError(msg)

        if not note or not str(note).strip():
            raise ValueError("Admin override requires a note (reason).")

        # Add an explicit audit event for the blocked attempt (optional but recommended)
        add_op_event(
            op,
            user_id=user_id,
            event_type="complete_blocked",
            actor_role="admin_override",
            note=msg,
            is_override=True,
        )
        # Continue to completion below (forced)

    # Canonical terminal state
    op.status = STATUS_COMPLETED
    op.is_released = False

    # Release claim on terminal
    release_claim(op)

    # Audit completion (no commit here)
    add_op_event(
        op,
        user_id=user_id,
        event_type="complete",
        actor_role=("admin_override" if is_admin else "editor"),
        note=(note or None),
        is_override=bool(is_admin),
    )

    if op.bom_item_id is not None:
        release_next_for_bom_item(op)

