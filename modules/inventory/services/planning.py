# File path: modules/inventory/services/planning.py
# V0 - Global planning / netting (JSON output)
from collections import defaultdict
from sqlalchemy import func
from database.models import (
    db,
    PartInventory,
    WorkOrder,
    WorkOrderLine,
    BOMHeader,
    BOMLine,
    PartType,
)
from database.models import Part

OPEN_WO_STATUSES = ("open", "in_progress")

# Inventory state buckets
FG_AVAILABLE = ("fg_complete",)
SUB_ASSY_AVAILABLE = ("mfg_complete", "finish_complete")
COMP_AVAILABLE = ("mfg_complete", "finish_complete")
COMP_EXPECTED = ("mfg_wip", "finish_wip")

def _part_label(part_id):
    p = Part.query.get(part_id)
    if not p:
        return {"part_number": None, "name": None}
    return {"part_number": p.part_number, "name": p.name}

def _sum_inventory(part_id, stage_keys, rev="A", config_key=None):
    q = (
        db.session.query(func.coalesce(func.sum(PartInventory.qty_on_hand), 0.0))
        .filter(PartInventory.part_id == part_id)
        .filter(PartInventory.rev == rev)
        .filter(PartInventory.stage_key.in_(stage_keys))
    )

    if config_key is None:
        q = q.filter(PartInventory.config_key.is_(None))
    else:
        q = q.filter(PartInventory.config_key == config_key)

    return float(q.scalar() or 0.0)


def _get_active_bom(part_id, rev="A"):
    return (
        BOMHeader.query
        .filter_by(assembly_part_id=part_id, rev=rev, is_active=True)
        .first()
    )

