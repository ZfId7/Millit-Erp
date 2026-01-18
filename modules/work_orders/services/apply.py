# File path: modules/work_orders/services/apply.py
# V0 - Apply Work Order -> create Job+Build+BOMItems, generate gated ops
from sqlalchemy import func
from datetime import datetime

from database.models import db, Job, Build, BOMItem, WorkOrder, BOMHeader, Part

# Update these imports if your routing functions live elsewhere
from modules.jobs_management.services.routing import ensure_operations_for_bom_item, enforce_release_state_for_bom_item
from modules.inventory.services.bom_explode import explode_bom_header_to_build

def generate_ops_for_bom_item(bom: BOMItem):
    ensure_operations_for_bom_item(bom)
    enforce_release_state_for_bom_item(bom.build_id, bom.id)

def _describe_wo_lines(wo, max_items=3):
    parts = []
    for l in wo.lines:
        if not l.part_number:
            continue
        qty = float(l.qty_requested or 0.0)
        if qty <= 0:
            continue
        parts.append(f"{int(qty) if qty.is_integer() else qty:g}× {l.part_number}")

    if not parts:
        return "No lines"

    if len(parts) <= max_items:
        return ", ".join(parts)

    return ", ".join(parts[:max_items]) + f" (+{len(parts) - max_items} more)"

def _next_job_number() -> str:
    """
    Generates JOB-0001 style numbers (v0).
    Adjust prefix later if you want.
    """
    last = Job.query.order_by(Job.id.desc()).first()
    if not last or not last.job_number:
        return "JOB-0001"

    # Try to parse trailing digits
    s = last.job_number
    digits = ""
    for ch in reversed(s):
        if ch.isdigit():
            digits = ch + digits
        else:
            break

    if digits:
        n = int(digits) + 1
        prefix = s[: len(s) - len(digits)] or "JOB-"
        return f"{prefix}{n:04d}"

    return f"JOB-{(last.id + 1):04d}"


def apply_work_order_to_new_build(wo_id: int) -> Build:
    wo = WorkOrder.query.get_or_404(wo_id)

    now = datetime.utcnow()

    line_summary = _describe_wo_lines(wo)
    total_ordered = sum(float(l.qty_requested or 0.0) for l in wo.lines if float(l.qty_requested or 0.0) > 0)
             
    # Create Job (required fields per your schema)
    if not wo.customer_id:
        raise RuntimeError("Work Order has no customer_id assigned.")

    job = Job(
        customer_id=wo.customer_id,
        job_number=_next_job_number(),
        title=f"{wo.wo_number} — {line_summary}",
        status="active",
        priority=None,
        due_date=None,
        notes=f"Generated from Work Order {wo.wo_number}",
        created_at=now,
        updated_at=now,
        is_archived=False,
    )
    db.session.add(job)
    db.session.flush()

    # Create Build (required fields per your schema)
    build = Build(
        job_id=job.id,
        name=f"{wo.wo_number} — {line_summary}",
        status="active",
        qty_ordered=int(total_ordered) if float(total_ordered).is_integer() else int(round(total_ordered)),
        qty_completed=0,
        qty_scrap=0,
        assembly_part_id=assembly_part.id,
        created_at=now,
    )
    db.session.add(build)
    db.session.flush()


    # For each WO line, explode its assembly BOM
    for line in wo.lines:
        if not line.part_id:
            continue

        requested_qty = float(line.qty_requested or 0.0)
        if requested_qty <= 0:
            continue

        # 🔎 Find active BOM for this assembly part (if it exists)
        bom_header = (
            BOMHeader.query
            .filter_by(assembly_part_id=line.part_id, is_active=True)
            .order_by(BOMHeader.rev.desc())
            .first()
        )
        if not bom_header:
            # ✅ Component-only WO line (no BOM) -> create a single BOMItem snapshot
            part = Part.query.get(line.part_id)
            if not part:
                raise RuntimeError(f"Part not found for part_id={line.part_id}")
            
            next_line = (
                db.session.query(func.max(BOMItem.line_no))
                .filter_by(build_id=build.id)
                .scalar() or 0
            ) + 1   

            bom_item = BOMItem(
                build_id=build.id,
                bom_header_id=None,
                part_id=part.id,
                line_no=next_line,
                part_number=part.part_number,
                name=part.name,
                description=part.description,
                qty_per=1.0,
                qty_planned=requested_qty,
                qty=requested_qty,
                unit=part.unit or "ea",
                source="wo_direct",
                created_at=now,
            )
            db.session.add(bom_item)
            db.session.flush()

            mm = (getattr(line, "make_method", None) or "MAKE").upper()
            if mm == "MAKE":
                generate_ops_for_bom_item(bom_item)

            # BUY/OUTSOURCE: no ops (for now)

            # 🔑 DO NOT fall through
            continue
        
        # ✅ Assembly path   
        explode_bom_header_to_build(
            build=build,
            bom_header=bom_header,
            assembly_qty=requested_qty,
        )


    return build
