# File path: modules/shared/services/build_op_claim_service.py

from __future__ import annotations

from typing import Optional, Tuple
from flask import abort

from database.models import db, BuildOperation
from modules.shared.status import TERMINAL_STATUSES, STATUS_IN_PROGRESS
from modules.shared.claims import claim, ROLE_ADMIN_OVERRIDE
from modules.shared.services.build_op_progress_service import add_op_event, OpProgressError


def start_build_operation(
    op_id: int,
    *,
    user_id: int,
    is_admin: bool = False,
    force: bool = False,
    note: Optional[str] = None,
) -> BuildOperation:
    """
    Canonical 'Start' action:
      - status -> in_progress
      - claim as exclusive editor
      - audit 'start'
    No commit here.
    """
    op = BuildOperation.query.get(op_id)
    if not op:
        abort(404)

    if op.status in TERMINAL_STATUSES:
        raise OpProgressError("Cannot start a cancelled/completed operation.")

    if not user_id:
        raise OpProgressError("Missing user. Please log in again.")

    # Set status first (start = intention)
    op.status = STATUS_IN_PROGRESS

    # Exclusive claim on start
    claim_res = claim(
        op,
        user_id=int(user_id),
        is_admin=bool(is_admin),
        force=bool(force),
        as_contributor=False,
    )
    if not claim_res.get("ok"):
        reason = claim_res.get("reason") or "claim_blocked"
        if reason == "claimed_by_other":
            raise OpProgressError("This operation is currently claimed by another user.")
        if reason == "terminal":
            raise OpProgressError("Cannot start a cancelled/completed operation.")
        raise OpProgressError("Start blocked by claim rules.")

    role = claim_res.get("role")

    # Audit start event (always)
    add_op_event(
        op,
        user_id=int(user_id),
        event_type="start",
        actor_role=("admin_override" if role == ROLE_ADMIN_OVERRIDE else "editor"),
        note=(note or None),
        is_override=(role == ROLE_ADMIN_OVERRIDE),
    )

    return op
