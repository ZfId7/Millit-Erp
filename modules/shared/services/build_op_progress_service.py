# File path: modules/shared/services/build_op_progress_service.py

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

from flask import abort

from database.models import db, BuildOperation, BuildOperationProgress
from modules.shared.status import TERMINAL_STATUSES
from modules.shared.claims import claim, ROLE_ADMIN_OVERRIDE, ROLE_EDITOR


class OpProgressError(Exception):
    pass


@dataclass(frozen=True)
class OpProgressTotals:
    qty_done: float
    qty_scrap: float


def add_op_event(
    op: BuildOperation,
    user_id: int,
    event_type: str,
    actor_role: Optional[str] = None,
    note: Optional[str] = None,
    is_override: bool = False,
) -> BuildOperationProgress:
    """
    Audit-only row in BuildOperationProgress (qty deltas = 0).
    No commit here.
    """
    row = BuildOperationProgress(
        build_operation_id=op.id,
        user_id=user_id,
        qty_done_delta=0.0,
        qty_scrap_delta=0.0,
        event_type=event_type,
        actor_role=actor_role,
        event_note=(note or None),
        is_override=bool(is_override),
    )
    db.session.add(row)
    return row


def add_op_progress(
    op_id: int,
    qty_done_delta: float,
    qty_scrap_delta: float,
    note: Optional[str] = None,
    user_id: Optional[int] = None,
    is_admin: bool = False,
    force: bool = False,
) -> Tuple[BuildOperation, OpProgressTotals]:
    """
    Canonical progress writer for BuildOperations.
    - Enforces terminal guard
    - Enforces claim gating (global)
    - Writes both progress + claim audit rows into BuildOperationProgress
    - Updates cached totals on BuildOperation
    - Does NOT commit
    """
    op = BuildOperation.query.get(op_id)
    if not op:
        abort(404)

    if op.status in TERMINAL_STATUSES:
        raise OpProgressError("Cannot add progress to a cancelled/completed operation.")

    if not user_id:
        raise OpProgressError("Missing user. Please log in again.")

    # 1) claim gate — progress is a contributor action by default
    claim_res = claim(
        op,
        user_id=int(user_id),
        is_admin=bool(is_admin),
        force=bool(force),
        as_contributor=True,
    )
    if not claim_res.get("ok"):
        reason = claim_res.get("reason") or "claim_blocked"
        if reason == "claimed_by_other":
            raise OpProgressError("This operation is currently claimed by another user.")
        if reason == "cannot_contribute_unclaimed":
            raise OpProgressError("Operation is unclaimed. Start it to claim it before adding progress.")
        if reason == "terminal":
            raise OpProgressError("Cannot add progress to a cancelled/completed operation.")
        raise OpProgressError("Progress blocked by claim rules.")

    role = claim_res.get("role")  # editor|contributor|admin_override

    # 2) If claim changed (stale takeover or admin override), audit it
    if claim_res.get("changed"):
        add_op_event(
            op,
            user_id=int(user_id),
            event_type="claim",
            actor_role=("admin_override" if role == ROLE_ADMIN_OVERRIDE else ROLE_EDITOR),
            note=("stale takeover" if claim_res.get("stole_stale") else None),
            is_override=(role == ROLE_ADMIN_OVERRIDE),
        )

    # 3) Validate inputs
    qty_done_delta = float(qty_done_delta or 0.0)
    qty_scrap_delta = float(qty_scrap_delta or 0.0)
    note = (note or "").strip() or None

    if qty_done_delta == 0.0 and qty_scrap_delta == 0.0 and not note:
        raise OpProgressError("Nothing to add. Enter qty done/scrap and/or a note.")

    if qty_done_delta < 0.0 or qty_scrap_delta < 0.0:
        raise OpProgressError("Deltas must be >= 0.")

    # 4) Write progress row (new system writes to event_note)
    entry = BuildOperationProgress(
        build_operation_id=op.id,
        user_id=int(user_id),
        qty_done_delta=qty_done_delta,
        qty_scrap_delta=qty_scrap_delta,
        event_type="progress",
        actor_role=role,
        event_note=note,
        is_override=(role == ROLE_ADMIN_OVERRIDE),
    )

    # OPTIONAL compatibility:
    # If any old template still displays `progress.note`, you can mirror it here.
    # Comment out once you finish migrating templates to `event_note`.
    entry.note = note

    db.session.add(entry)

    # 5) Maintain cached totals on op (so UI can read op.qty_done/op.qty_scrap consistently)
    op.qty_done = float(op.qty_done or 0.0) + qty_done_delta
    op.qty_scrap = float(op.qty_scrap or 0.0) + qty_scrap_delta

    totals = OpProgressTotals(
        qty_done=float(op.qty_done or 0.0),
        qty_scrap=float(op.qty_scrap or 0.0),
    )
    return op, totals

def get_op_totals(op_id: int) -> OpProgressTotals:
    """
    Read totals for UI from cached fields on BuildOperation.
    No commit.
    """
    op = BuildOperation.query.get(op_id)
    if not op:
        abort(404)

    return OpProgressTotals(
        qty_done=float(op.qty_done or 0.0),
        qty_scrap=float(op.qty_scrap or 0.0),
    )
