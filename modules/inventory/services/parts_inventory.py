# File path: modules/inventory/services/parts_inventory.py
# V2 - Inventory state backbone (rev + config_key aware)
from typing import Optional

from database.models import db, PartInventory


def get_or_create_inventory_row(
    part_id: int,
    stage_key: str,
    rev: str = "A",
    config_key: Optional[str] = None,
    uom: str = "ea",
) -> PartInventory:
    """
    Ensures a single unique inventory row exists for (part_id, stage_key, rev, config_key).
    Defaults: rev="A", config_key=None.
    """
    inv = (
        PartInventory.query
        .filter_by(
            part_id=part_id,
            stage_key=stage_key,
            rev=rev,
            config_key=config_key,
        )
        .first()
    )

    if inv is None:
        inv = PartInventory(
            part_id=part_id,
            stage_key=stage_key,
            rev=rev,
            config_key=config_key,
            qty_on_hand=0.0,
            uom=uom,
        )
        db.session.add(inv)

    if not getattr(inv, "uom", None):
        inv.uom = uom

    return inv


def apply_part_inventory_delta(
    part_id: int,
    stage_key: str,
    qty_delta: float,
    uom: str = "ea",
    rev: str = "A",
    config_key: Optional[str] = None,
) -> None:
    """
    Applies a delta to PartInventory, creating the row if needed.
    """
    if not part_id or not stage_key:
        return

    if qty_delta is None or float(qty_delta) == 0.0:
        return

    inv = get_or_create_inventory_row(
        part_id=part_id,
        stage_key=stage_key,
        rev=rev,
        config_key=config_key,
        uom=uom,
    )

    inv.qty_on_hand = float(inv.qty_on_hand or 0.0) + float(qty_delta)
