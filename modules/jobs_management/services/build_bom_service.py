# File path: modules/jobs_management/services/build_bom_service.py

from sqlalchemy import func
from database.models import BOMItem, Build, BuildOperation, Part, db
from modules.jobs_management.services.routing import ensure_operations_for_bom_item


def add_bom_item_to_build(*, build_id: int, form: dict) -> tuple[int, str]:
    """
    Build BOM = snapshot BOM (BOMItem rows tied to build_id).
    Stages DB changes only. Caller commits/rolls back.
    Returns: (build_id, success_message)
    Raises: ValueError for user-facing form problems.
    """
    build = Build.query.get_or_404(build_id)

    part_id_raw = (form.get("part_id") or "").strip()
    name = (form.get("name") or "").strip()
    part_number = (form.get("part_number") or "").strip()
    description = (form.get("description") or "").strip()
    unit = (form.get("unit") or "ea").strip()
    qty_raw = (form.get("qty") or "1").strip()

    # Parse qty as float (supports 0.5, etc.)
    try:
        qty_per = float(qty_raw)
    except ValueError:
        qty_per = 1.0
    if qty_per <= 0:
        qty_per = 1.0

    assemblies = float(getattr(build, "qty_ordered", 0) or 0)
    qty_planned = qty_per * assemblies  # snapshot truth

    last_line = db.session.query(func.max(BOMItem.line_no)).filter_by(build_id=build.id).scalar() or 0
    next_line = last_line + 1

    # If a catalog part was selected, snapshot its fields
    if part_id_raw:
        try:
            selected_part = Part.query.get(int(part_id_raw))
        except ValueError:
            selected_part = None

        if not selected_part:
            raise ValueError("Selected part not found.")

        bom = BOMItem(
            build=build,
            part=selected_part,
            line_no=next_line,
            part_number=selected_part.part_number,
            name=selected_part.name,
            description=selected_part.description,
            qty=qty_per,          # legacy mirror during refactor
            qty_per=qty_per,
            qty_planned=qty_planned,
            unit=selected_part.unit or unit,
            source="manual",
        )
        db.session.add(bom)
        db.session.flush()
        ensure_operations_for_bom_item(bom)

        return build.id, "BOM item added from catalog part."

    # Free-text BOM line requires at least a name
    if not name:
        raise ValueError("Enter a name or select a catalog part.")

    bom = BOMItem(
        build=build,
        line_no=next_line,
        part_number=part_number or None,
        name=name,
        description=description or None,
        qty=qty_per,            # legacy mirror
        qty_per=qty_per,
        qty_planned=qty_planned,
        unit=unit or "ea",
        source="manual",
    )
    db.session.add(bom)
    db.session.flush()
    ensure_operations_for_bom_item(bom)

    return build.id, "BOM item added."


def delete_bom_item_from_build(*, bom_item_id: int) -> dict:
    """
    Deletes:
      - queued ops for this BOM item
      - the BOM item itself
    Leaves non-queued ops intact and reports count back for warning.
    Stages DB changes only. Caller commits/rolls back.
    """
    bom = BOMItem.query.get_or_404(bom_item_id)
    build_id = bom.build_id

    # Find ops tied to this BOM item (link confirmed via BuildOperation.bom_item_id)
    ops = (
        BuildOperation.query
        .filter(
            BuildOperation.build_id == build_id,
            BuildOperation.bom_item_id == bom.id,
        )
        .all()
    )

    non_queued_ops = [op for op in ops if op.status != "queue"]

    deleted_count = (
        BuildOperation.query
        .filter(
            BuildOperation.build_id == build_id,
            BuildOperation.bom_item_id == bom.id,
            BuildOperation.status == "queue",
        )
        .delete(synchronize_session=False)
    )

    db.session.delete(bom)

    return {
        "build_id": build_id,
        "deleted_count": int(deleted_count or 0),
        "non_queued_count": len(non_queued_ops),
    }
