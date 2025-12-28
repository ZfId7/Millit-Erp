# File path: modules/inventory/services/parts_inventory.py
# -V1 Base Build Parts inventory hook
from database.models import db, PartInventory

def apply_part_inventory_delta(part_id: int, stage_key: str, qty_delta: float, uom: str = "ea"):
    if not part_id or not stage_key or not qty_delta:
        return

    inv = PartInventory.query.filter_by(part_id=part_id, stage_key=stage_key).first()
    if inv is None:
        inv = PartInventory(part_id=part_id, stage_key=stage_key, qty_on_hand=0.0, uom=uom)
        db.session.add(inv)

    inv.qty_on_hand = float(inv.qty_on_hand or 0.0) + float(qty_delta)
