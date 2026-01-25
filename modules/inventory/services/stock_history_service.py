# File path: modules/inventory/services/stock_history_service.py

from database.models import StockLedgerEntry


def get_stock_history(entity_type: str, entity_id: int, limit: int = 250):
    return (
        StockLedgerEntry.query
        .filter(StockLedgerEntry.entity_type == entity_type, StockLedgerEntry.entity_id == entity_id)
        .order_by(StockLedgerEntry.created_at.desc(), StockLedgerEntry.id.desc())
        .limit(limit)
        .all()
    )
