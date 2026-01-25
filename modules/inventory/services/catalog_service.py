# File Path: modules/inventory/services/catalog_service.py
from collections import defaultdict

from modules.inventory.services.stock_ledger_service import get_on_hand_map

from database.models import (
    db,
    Part,
    PartType,
    PartInventory,
    RawStock,
    BulkHardware,
)


def get_catalog_rows(
    item_types=None,
    search=None,
    include_inactive=False,
):
    """
    Returns unified catalog rows for:
    - Parts
    - Raw Stock
    - Bulk Hardware

    item_types: set {"part", "raw", "bulk"} or None
    """

    rows = []

    # ----------------------------
    # Parts
    # ----------------------------
    if item_types is None or "part" in item_types:
        part_q = (
            Part.query
            .join(PartType, Part.part_type_id == PartType.id)
        )

        if not include_inactive:
            part_q = part_q.filter(Part.status == "active")

        if search:
            like = f"%{search}%"
            part_q = part_q.filter(
                (Part.part_number.ilike(like)) |
                (Part.name.ilike(like))
            )

        parts = part_q.all()

        # aggregate inventory by stage_key
        inv_rows = (
            db.session.query(
                PartInventory.part_id,
                PartInventory.stage_key,
                db.func.sum(PartInventory.qty_on_hand)
            )
            .group_by(PartInventory.part_id, PartInventory.stage_key)
            .all()
        )

        stage_map = defaultdict(dict)
        total_map = defaultdict(float)

        for part_id, stage, qty in inv_rows:
            stage_map[part_id][stage] = qty
            total_map[part_id] += qty

        for p in parts:
            rows.append({
                "item_type": "part",
                "id": p.id,
                "code": p.part_number,
                "name": p.name,
                "category": p.part_type.category_key,
                "uom": p.unit,
                "qty_total": total_map.get(p.id, 0),
                "stage_map": stage_map.get(p.id, {}),
                "status": p.status,
            })

    # ----------------------------
    # Raw Stock
    # ----------------------------
    if item_types is None or "raw" in item_types:
        raw_q = RawStock.query

        if not include_inactive:
            raw_q = raw_q.filter(RawStock.is_active == True)

        if search:
            like = f"%{search}%"
            raw_q = raw_q.filter(
                (RawStock.name.ilike(like)) |
                (RawStock.grade.ilike(like))
            )

        raws = raw_q.all()
        raw_qty_map = get_on_hand_map("raw_stock", [r.id for r in raws])
        
        for r in raws:
            rows.append({
                "item_type": "raw",
                "id": r.id,
                "code": f"RS-{r.id:06d}",
                "name": r.name,
                "category": "raw",
                "uom": r.uom,
                "qty_total": raw_qty_map.get(r.id, 0.0),
                "status": "active" if r.is_active else "inactive",
            })

    # ----------------------------
    # Bulk Hardware
    # ----------------------------
    if item_types is None or "bulk" in item_types:
        bulk_q = BulkHardware.query

        if not include_inactive:
            bulk_q = bulk_q.filter(BulkHardware.is_active == True)

        if search:
            like = f"%{search}%"
            bulk_q = bulk_q.filter(
                (BulkHardware.item_code.ilike(like)) |
                (BulkHardware.name.ilike(like))
            )

        bulks = bulk_q.all()
        bulk_qty_map = get_on_hand_map("bulk_hardware", [b.id for b in bulks])
        
        for b in bulks:
            rows.append({
                "item_type": "bulk",
                "id": b.id,
                "code": b.item_code,
                "name": b.name,
                "category": "bulk",
                "uom": b.uom,
                "qty_total": bulk_qty_map.get(b.id, 0.0),
                "status": "active" if b.is_active else "inactive",
            })

    return rows
