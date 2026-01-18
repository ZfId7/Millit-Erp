# File path: modules/inventory/services/parts_service.py
"""
Shared Part business rules (NOT tied to any blueprint).

V1 readiness rule:
A part is "ready" (allowed into Work Orders) if it has:
- a PartType assigned (part_type_id not null)
- an active RoutingHeader (is_active == True)

We do NOT rely on Part.status, because it can drift / be cosmetic.
"""

from __future__ import annotations

from typing import Optional, Dict, Any

from database.models import db, Part, RoutingHeader, BOMHeader


def part_is_ready(part_id: int) -> bool:
    """
    Fast boolean readiness check used as a hard gate in WO creation/apply.
    """
    part = Part.query.get(part_id)
    if not part:
        return False

    # must be classified
    if not part.part_type_id:
        return False

    # must have at least one active routing
    has_active_routing = (
        db.session.query(RoutingHeader.id)
        .filter(
            RoutingHeader.part_id == part.id,
            RoutingHeader.is_active == True,  # noqa: E712
        )
        .first()
        is not None
    )

    return has_active_routing


def part_readiness_detail(part_id: int) -> Dict[str, Any]:
    """
    Optional helper for UI: tells you WHY a part is not ready.
    Great for Draft Parts Manager cards and WO validation messages.
    """
    part = Part.query.get(part_id)
    if not part:
        return {
            "exists": False,
            "is_ready": False,
            "missing": ["part_not_found"],
        }

    missing = []

    if not part.part_type_id:
        missing.append("missing_part_type")

    has_active_routing = (
        db.session.query(RoutingHeader.id)
        .filter(
            RoutingHeader.part_id == part.id,
            RoutingHeader.is_active == True,  # noqa: E712
        )
        .first()
        is not None
    )
    if not has_active_routing:
        missing.append("missing_active_routing")

    return {
        "exists": True,
        "is_ready": len(missing) == 0,
        "missing": missing,
        "part_id": part.id,
        "part_number": part.part_number,
        "name": part.name,
    }

def part_has_active_bom(part_id: int) -> bool:
    return (
        db.session.query(BOMHeader.id)
        .filter(
            BOMHeader.assembly_part_id == part_id,
            BOMHeader.is_active == True,  # noqa: E712
        )
        .first()
        is not None
    )

def sync_part_status(part_id: int) -> str:
    """
    Auto-sets Part.status based on readiness rules.
    - "active" if ready
    - "draft" if not ready
    Returns the new status.
    """
    part = Part.query.get(part_id)
    if not part:
        return "draft"

    new_status = "active" if part_is_ready(part_id) else "draft"

    if part.status != new_status:
        part.status = new_status
        db.session.add(part)

    return new_status


def validate_part_for_work_order(part_id: int) -> tuple[bool, str]:
    """
    WO eligibility (V1):
    - Must exist
    - Must be classified (part_type_id)
    - If it's an Assembly WO line candidate (has an active BOMHeader): routing NOT required
    - Otherwise (component-only): must have active routing header
    """
    part = Part.query.get(part_id)
    if not part:
        return False, "Selected part does not exist."

    if not part.part_type_id:
        return False, f"Part {part.part_number} is not WO-eligible: missing Part Type."

    # ✅ Assembly WO line path: Active BOM exists => allow without routing
    if part_has_active_bom(part.id):
        return True, ""

    # ✅ Component-only path: requires active routing
    has_active_routing = (
        db.session.query(RoutingHeader.id)
        .filter(
            RoutingHeader.part_id == part.id,
            RoutingHeader.is_active == True,  # noqa: E712
        )
        .first()
        is not None
    )
    if not has_active_routing:
        return (
            False,
            f"Part {part.part_number} is not WO-eligible: missing active routing (component-only parts require routing).",
        )

    return True, ""