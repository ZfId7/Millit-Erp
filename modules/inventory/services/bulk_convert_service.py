# File path: modules/inventory/services/bulk_convert_service.py
from dataclasses import dataclass

from database.models import db, BulkHardware, Part, PartType, PartInventory, BulkConversionEvent
from modules.inventory.services.stock_ledger_service import post_stock_move

from typing import Optional

class BulkConvertError(Exception):
    pass


@dataclass
class BulkConvertResult:
    part: Part
    inv: PartInventory
    bulk: BulkHardware


def _suggest_part_number_from_bulk(item_code: str) -> str:
    # BH-000123 -> HW-000123 (suggestion only)
    if not item_code:
        return ""
    return item_code.replace("BH-", "HW-", 1)


def _get_or_create_hardware_part_type() -> PartType:
    # Prefer an explicit HW code if it exists, else any hardware category type.
    pt = PartType.query.filter_by(code="HW").first()
    if pt:
        return pt

    pt = PartType.query.filter_by(category_key="hardware").first()
    if pt:
        return pt

    # Create a minimal one if you have none yet.
    pt = PartType(
        name="Hardware",
        category_key="hardware",
        code="HW",
        legacy_key=None,
    )

    db.session.add(pt)
    db.session.flush()
    return pt


def convert_bulk_to_part(
    bulk_id: int,
    part_number: str,
    name: str,
    description: Optional[str],
    unit: str,
    stage_key: str,
    produced_qty: float,
    consumed_qty: float,
    set_active: bool,
    source_type: Optional[str] = None,
    source_ref: Optional[str] = None,
    note: Optional[str] = None,
) -> BulkConvertResult:
    bulk = BulkHardware.query.get_or_404(bulk_id)

    if not bulk.is_active:
        raise BulkConvertError("Cannot convert an inactive bulk item.")

    part_number = (part_number or "").strip()
    name = (name or "").strip()
    description = (description or "").strip() or None
    
    if not part_number or not name:
        raise BulkConvertError("Part # and Name are required.")

    # Unique Part #
    existing = Part.query.filter_by(part_number=part_number).first()
    if existing:
        raise BulkConvertError(f"Part number {part_number} already exists.")

    if produced_qty <= 0:
        raise BulkConvertError("Produced Qty must be > 0.")
    if consumed_qty <= 0:
        raise BulkConvertError("Consumed Qty must be > 0.")
    if consumed_qty > bulk.qty_on_hand:
        raise BulkConvertError("Consumed Qty exceeds bulk qty on hand.")

    pt = _get_or_create_hardware_part_type()

    # Create Part
    p = Part(
        part_number=part_number,
        name=name,
        description=description,
        part_type_id=pt.id,
        unit=(unit or "ea").strip().lower(),
        status="active" if set_active else "draft",
    )
    db.session.add(p)
    db.session.flush()

    # Create initial PartInventory entry
    inv = PartInventory(
        part_id=p.id,
        stage_key=(stage_key or "mfg_wip").strip(),
        rev="1",          # align with your numeric rev direction
        config_key=None,
        qty_on_hand=0.0, #ledger is source of truth now
        uom=(unit or "ea").strip().lower(),
        is_active=True,
    )
    db.session.add(inv)
    db.session.flush()


  
    
    event = BulkConversionEvent(
        bulk_hardware_id=bulk.id,
        part_id=p.id,
        produced_qty=produced_qty,
        produced_uom=(unit or "ea").strip().lower(),
        consumed_qty=consumed_qty,
        consumed_uom=(bulk.uom or "ea").strip().lower(),
        stage_key=(stage_key or "mfg_wip").strip(),
        source_type=(source_type or "").strip() or None,
        source_ref=(source_ref or "").strip() or None,
        note=(note or "").strip() or None,
    )
    db.session.add(event)
    
    post_stock_move(
        entity_type="bulk_hardware",
        entity_id=bulk.id,
        qty_delta=-consumed_qty,
        uom=(bulk.uom or "ea"),
        reason="convert",
        source_type=source_type,
        source_ref=source_ref,
        note=note or f"Converted to part {p.part_number}",
    )

    post_stock_move(
        entity_type="part_inventory",
        entity_id=inv.id,
        qty_delta=produced_qty,
        uom=(unit or "ea"),
        reason="convert",
        source_type=source_type,
        source_ref=source_ref,
        note=note or f"Produced from bulk {bulk.item_code}",
    )


    db.session.commit()

    return BulkConvertResult(part=p, inv=inv, bulk=bulk)


def get_bulk_convert_defaults(bulk: BulkHardware) -> dict:
    return {
        "suggested_part_number": _suggest_part_number_from_bulk(bulk.item_code),
        "unit_default": (bulk.uom or "ea").strip().lower(),
        "stage_default": "mfg_wip",
        "produced_default": 1.0,
        "consumed_default": 1.0,
        "active_default": False,  # draft by default (safe)
    }
