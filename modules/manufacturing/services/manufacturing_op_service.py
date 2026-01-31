# File path: modules/manufacturing/services/manufacturing_op_service.py

from database.models import BuildOperation


class MfgOpError(Exception):
    pass

STATUS_QUEUE = "queue"
STATUS_IN_PROGRESS = "in_progress"
STATUS_BLOCKED = "blocked"

STATUS_COMPLETED = "completed"
STATUS_CANCELLED = "cancelled"

LEGACY_COMPLETE = "complete"

TERMINAL_STATUSES = {STATUS_COMPLETED, STATUS_CANCELLED, LEGACY_COMPLETE}


def require_manufacturing_op(op: BuildOperation) -> None:
    if op.module_key != "manufacturing":
        raise MfgOpError("Invalid operation for Manufacturing.")


def start_operation(op: BuildOperation) -> None:
    """
    V0 rules:
    - must be manufacturing op
    - must not be terminal
    - must be released
    - must be queued or blocked (optional: allow restart from blocked)
    - cnc_profile must be assigned to a machine before start
    """
    require_manufacturing_op(op)

    if op.status in TERMINAL_STATUSES:
        raise MfgOpError("Cannot start: operation is not active.")

    if not op.is_released:
        raise MfgOpError("Cannot start: operation is not released.")

    if op.status not in {STATUS_QUEUE, STATUS_BLOCKED}:
        raise MfgOpError("Cannot start: operation is not queued/blocked.")

    if op.op_key == "cnc_profile" and not op.assigned_machine_id:
        raise MfgOpError("Assign a CNC machine before starting this operation.")

    op.status = STATUS_IN_PROGRESS


def block_operation(op: BuildOperation) -> None:
    """
    V0 rules:
    - must be manufacturing op
    - must not be terminal
    - allow blocking queued or in_progress (your call; this is practical)
    """
    require_manufacturing_op(op)

    if op.status in TERMINAL_STATUSES:
        raise MfgOpError("Cannot block: operation is not active.")

    if op.status not in {STATUS_QUEUE, STATUS_IN_PROGRESS}:
        raise MfgOpError("Cannot block: operation is not queued/in progress.")

    op.status = STATUS_BLOCKED


def unblock_operation(op: BuildOperation) -> None:
    """
    Optional helper for later (not wired into UI yet).
    """
    require_manufacturing_op(op)

    if op.status != STATUS_BLOCKED:
        raise MfgOpError("Operation is not blocked.")

    op.status = STATUS_QUEUE
