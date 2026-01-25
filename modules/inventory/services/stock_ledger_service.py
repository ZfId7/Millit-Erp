# File path: modules/inventory/services/stock_ledger_service.py
from typing import Optional, Dict, List
from flask import session
from sqlalchemy import func

from database.models import db, StockLedgerEntry


def post_stock_move(
    entity_type: str,
    entity_id: int,
    qty_delta: float,
    uom: str,
    reason: str = "adjust",
    note: Optional[str] = None,
    source_type: Optional[str] = None,
    source_ref: Optional[str] = None,
) -> StockLedgerEntry:
    """
    Write a ledger entry for any inventory movement.
    Does NOT mutate qty_on_hand — callers can keep doing that for V1.
    """
    if qty_delta == 0:
        raise ValueError("qty_delta cannot be 0")

    user_id = session.get("user_id")  # matches your session auth pattern

    entry = StockLedgerEntry(
        entity_type=entity_type,
        entity_id=entity_id,
        qty_delta=qty_delta,
        uom=(uom or "ea").strip().lower(),
        reason=(reason or "adjust").strip().lower(),
        note=(note or "").strip() or None,
        source_type=(source_type or "").strip() or None,
        source_ref=(source_ref or "").strip() or None,
        created_by_user_id=user_id,
    )
    db.session.add(entry)
    return entry

def get_on_hand(entity_type: str, entity_ids: List[int]) -> Dict[int, float]:
    qty = (
        db.session.query(func.coalesce(func.sum(StockLedgerEntry.qty_delta), 0.0))
        .filter(
            StockLedgerEntry.entity_type == entity_type,
            StockLedgerEntry.entity_id == entity_id,
        )
        .scalar()
    )
    return float(qty or 0.0)


def get_on_hand_map(entity_type: str, entity_ids: list) -> Dict[int, float]:
    """
    Returns {entity_id: on_hand} for a list of ids.
    """
    if not entity_ids:
        return {}

    rows = (
        db.session.query(
            StockLedgerEntry.entity_id,
            func.coalesce(func.sum(StockLedgerEntry.qty_delta), 0.0),
        )
        .filter(
            StockLedgerEntry.entity_type == entity_type,
            StockLedgerEntry.entity_id.in_(entity_ids),
        )
        .group_by(StockLedgerEntry.entity_id)
        .all()
    )
    out = {int(eid): float(qty or 0.0) for eid, qty in rows}
    for eid in entity_ids:
        out.setdefault(int(eid), 0.0)
    return out