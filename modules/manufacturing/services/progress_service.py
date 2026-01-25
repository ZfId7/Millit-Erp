# File path: modules/manufacturing/services/progress_service.py

from dataclasses import dataclass
from typing import Optional, Tuple

from database.models import db, BuildOperation, BuildOperationProgress


class OpProgressError(Exception):
    pass


@dataclass
class OpProgressTotals:
    qty_done: float
    qty_scrap: float


def get_op_totals(op_id: int) -> OpProgressTotals:
    # Sum deltas from ledger (authoritative)
    done = (
        db.session.query(db.func.coalesce(db.func.sum(BuildOperationProgress.qty_done_delta), 0.0))
        .filter(BuildOperationProgress.build_operation_id == op_id)
        .scalar()
    )
    scrap = (
        db.session.query(db.func.coalesce(db.func.sum(BuildOperationProgress.qty_scrap_delta), 0.0))
        .filter(BuildOperationProgress.build_operation_id == op_id)
        .scalar()
    )
    return OpProgressTotals(qty_done=float(done or 0.0), qty_scrap=float(scrap or 0.0))


def add_op_progress(
    op_id: int,
    qty_done_delta: float,
    qty_scrap_delta: float,
    note: Optional[str] = None,
) -> Tuple[BuildOperation, OpProgressTotals]:
    op = BuildOperation.query.get_or_404(op_id)

    if op.status in ("cancelled", "complete"):
        raise OpProgressError("Cannot add progress to a cancelled/completed operation.")

    qty_done_delta = float(qty_done_delta or 0.0)
    qty_scrap_delta = float(qty_scrap_delta or 0.0)
    note = (note or "").strip() or None

    if qty_done_delta == 0 and qty_scrap_delta == 0 and not note:
        raise OpProgressError("Nothing to add. Enter qty done/scrap and/or a note.")

    if qty_done_delta < 0 or qty_scrap_delta < 0:
        raise OpProgressError("Deltas must be >= 0.")

    # Ledger entry (authoritative)
    entry = BuildOperationProgress(
        build_operation_id=op.id,
        qty_done_delta=qty_done_delta,
        qty_scrap_delta=qty_scrap_delta,
        note=note,
    )
    db.session.add(entry)
    db.session.commit()

    totals = get_op_totals(op.id)
    return op, totals
