# File path: modules/inventory/services/bom_explode.py

from datetime import datetime
from database.models import db, BOMItem, BOMLine, BOMHeader
from modules.jobs_management.services.routing import ensure_operations_for_bom_item

def explode_bom_header_to_build(build, bom_header, assembly_qty):
    now = datetime.utcnow()

    for line in bom_header.lines:
        qty_planned = float(line.qty_per or 0.0) * float(assembly_qty or 0.0)
        if qty_planned <= 0:
            continue

        bom_item = BOMItem(
            build_id=build.id,
            bom_header_id=bom_header.id,
            part_id=line.component_part_id,
            line_no=line.line_no,
            part_number=line.component_part.part_number,
            name=line.component_part.name,
            description=line.component_part.description,
            qty_per=line.qty_per,
            qty_planned=qty_planned,
            qty=qty_planned,
            unit=line.component_part.unit or "ea",
            source="bom_snapshot",
            created_at=now,
        )
        db.session.add(bom_item)
        db.session.flush()

        # 🔒 Only generate ops for MAKE components
        if (line.make_method or "MAKE") == "MAKE":
            ensure_operations_for_bom_item(bom_item)
