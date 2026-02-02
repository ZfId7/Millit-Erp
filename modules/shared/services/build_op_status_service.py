# File path: modules/shared/services/build_op_status_service.py

from flask import abort

from database.models import BuildOperation
from modules.shared.status import STATUS_CANCELLED, TERMINAL_STATUSES
from modules.shared.claims import release_claim
from modules.shared.services.build_op_progress_service import add_op_event, OpProgressError

def cancel_build_operation(
    op_id: int, 
    *, 
    user_id: int = None,
    is_admin: bool = False,
    note: str = None,
    ) -> BuildOperation:
    op = BuildOperation.query.get(op_id)
    if not op:
        abort(404)

    if op.status in TERMINAL_STATUSES:
        raise OpProgressError(f"Cannot cancel: operation is {op.status}.")

    op.status = STATUS_CANCELLED

    # terminal -> release claim
    release_claim(op)

    # audit cancel (best-effort attribution for now)
    add_op_event(
        op,
        user_id=user_id,
        event_type="cancel",
        actor_role=("admin_override" if is_admin else "editor"),
        note=(note or None),
        is_override=bool(is_admin),
    )
    
    return op
