# File path: modules/manufacturing/services/machine_service.py

from dataclasses import dataclass
from typing import List, Optional

from database.models import BuildOperation, Machine
from modules.manufacturing.services.dispatch_service import MFG_OP_KEYS


@dataclass(frozen=True)
class MachineQueue:
    assigned: List[BuildOperation]
    eligible_unassigned: List[BuildOperation]


def get_machine_by_id(machine_id: int) -> Machine:
    return Machine.query.get_or_404(machine_id)


def get_machine_queue(machine: Machine) -> MachineQueue:
    """
    V0:
    - "assigned" = ops explicitly assigned to this machine (any active status)
    - "eligible_unassigned" = queued+released manufacturing ops that are unassigned
      (eligibility currently == cnc_profile blanket)
    """
    assigned = (
        BuildOperation.query
        .filter(BuildOperation.module_key == "manufacturing")
        .filter(BuildOperation.op_key.in_(MFG_OP_KEYS))
        .filter(BuildOperation.assigned_machine_id == machine.id)
        .filter(BuildOperation.status.in_(["queue", "in_progress", "blocked"]))
        .order_by(BuildOperation.sequence.asc(), BuildOperation.id.asc())
        .all()
    )

    eligible_unassigned = (
        BuildOperation.query
        .filter(BuildOperation.module_key == "manufacturing")
        .filter(BuildOperation.op_key.in_(MFG_OP_KEYS))
        .filter(BuildOperation.is_released.is_(True))
        .filter(BuildOperation.status == "queue")
        .filter(BuildOperation.assigned_machine_id.is_(None))
        .order_by(BuildOperation.sequence.asc(), BuildOperation.id.asc())
        .all()
    )

    return MachineQueue(assigned=assigned, eligible_unassigned=eligible_unassigned)
