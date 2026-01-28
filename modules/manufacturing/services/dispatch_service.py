# File path: modules/manufacturing/services/dispatch_service.py

from dataclasses import dataclass
from typing import List, Optional

from database.models import BuildOperation, Machine


MFG_OP_KEYS = ["cnc_profile"]  # v0: blanket CNC op


@dataclass(frozen=True)
class DispatchFilters:
    machine_id: Optional[int] = None


def get_dispatchable_ops(filters: Optional[DispatchFilters] = None) -> List[BuildOperation]:
    """
    V0-B: Dispatchable = manufacturing ops that are released + queued, and currently unassigned.
    """
    if filters is None:
        filters = DispatchFilters()

    q = (
        BuildOperation.query
        .filter(BuildOperation.module_key == "manufacturing")
        .filter(BuildOperation.op_key.in_(MFG_OP_KEYS))
        .filter(BuildOperation.is_released.is_(True))
        .filter(BuildOperation.status == "queue")
        .filter(BuildOperation.assigned_machine_id.is_(None))
        .order_by(BuildOperation.sequence.asc(), BuildOperation.id.asc())
    )

    # In V0-B, machine_id does not filter dispatchable ops because they’re unassigned.
    # Keeping filters object for future growth.
    return q.all()


def get_active_machines() -> List[Machine]:
    return (
        Machine.query
        .filter(Machine.is_active.is_(True))
        .order_by(Machine.machine_group.asc(), Machine.name.asc())
        .all()
    )


class DispatchError(Exception):
    pass


def assign_op_to_machine(op: BuildOperation, machine: Machine) -> None:
    """
    Assign op to a machine. No commit here (route owns commit).
    """
    if op.module_key != "manufacturing":
        raise DispatchError("Invalid operation for Manufacturing.")

    if op.status != "queue":
        raise DispatchError("Only queued operations can be assigned.")

    if not op.is_released:
        raise DispatchError("Operation must be released before assignment.")

    if not machine.is_active:
        raise DispatchError("Cannot assign to an inactive machine.")

    op.assigned_machine_id = machine.id


def unassign_op(op: BuildOperation) -> None:
    """
    Unassign op from its machine. No commit here.
    """
    if op.module_key != "manufacturing":
        raise DispatchError("Invalid operation for Manufacturing.")

    if op.status != "queue":
        raise DispatchError("Only queued operations can be unassigned safely.")

    op.assigned_machine_id = None
