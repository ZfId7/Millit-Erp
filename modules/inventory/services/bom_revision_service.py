# File path: modules/inventory/services/bom_revision_service.py

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, List

from database.models import db, BOMHeader, BOMLine


# ----------------------------
# Results / Errors
# ----------------------------

@dataclass(frozen=True)
class CloneResult:
    new_bom: BOMHeader
    old_bom: BOMHeader
    copied_lines: int
    new_rev: str


class BOMRevisionError(Exception):
    pass


class BOMNotFound(BOMRevisionError):
    pass


class BOMNotCloneable(BOMRevisionError):
    pass


class BOMRevisionConflict(BOMRevisionError):
    pass


# ----------------------------
# Public API
# ----------------------------

def clone_bom_revision(bom_id: int, new_rev: Optional[str] = None) -> CloneResult:
    """
    Clone an ACTIVE BOMHeader into a new numeric revision.

    Rules:
    - Source BOM must be active
    - New revision auto-increments last numeric segment (unless overridden)
    - New BOM becomes active
    - Old BOM is deactivated
    - All BOMLines are copied verbatim
    """

    source = BOMHeader.query.get(bom_id)
    if not source:
        raise BOMNotFound(f"BOMHeader {bom_id} not found")

    if not source.is_active:
        raise BOMNotCloneable("Only active BOMs may be cloned")

    target_rev = new_rev or _next_numeric_revision(source)

    if _revision_exists(source.assembly_part_id, target_rev):
        raise BOMRevisionConflict(
            f"Revision '{target_rev}' already exists for this assembly"
        )

    try:
        # ---- create new header
        new_bom = BOMHeader(
            assembly_part_id=source.assembly_part_id,
            rev=target_rev,
            is_active=True,
            notes=source.notes,
        )
        db.session.add(new_bom)
        db.session.flush()  # get new_bom.id

        # ---- copy lines
        copied = _copy_lines(source.id, new_bom.id)

        # ---- deactivate old
        source.is_active = False

        db.session.commit()

        return CloneResult(
            new_bom=new_bom,
            old_bom=source,
            copied_lines=copied,
            new_rev=target_rev,
        )

    except Exception:
        db.session.rollback()
        raise


# ----------------------------
# Helpers
# ----------------------------

def _revision_exists(assembly_part_id: int, rev: str) -> bool:
    return (
        db.session.query(
            BOMHeader.query
            .filter(
                BOMHeader.assembly_part_id == assembly_part_id,
                BOMHeader.rev == rev,
            )
            .exists()
        )
        .scalar()
    )


def _next_numeric_revision(source: BOMHeader) -> str:
    """
    Increment the rightmost numeric segment.
    Examples:
      1        -> 2
      1.4.2    -> 1.4.3
      2.9      -> 2.10
    """
    current = (source.rev or "").strip()
    if not current:
        return "1"

    parts = current.split(".")
    if not all(p.isdigit() for p in parts):
        raise BOMRevisionError(
            f"Cannot auto-increment non-numeric revision '{current}'"
        )

    parts[-1] = str(int(parts[-1]) + 1)
    return ".".join(parts)


def _copy_lines(source_bom_id: int, target_bom_id: int) -> int:
    lines: List[BOMLine] = (
        BOMLine.query
        .filter(BOMLine.bom_id == source_bom_id)
        .order_by(BOMLine.line_no.asc(), BOMLine.id.asc())
        .all()
    )

    count = 0
    for line in lines:
        new_line = BOMLine(
            bom_id=target_bom_id,
            component_part_id=line.component_part_id,
            qty_per=line.qty_per,
            line_no=line.line_no,
            make_method=line.make_method,
            routing_override_id=line.routing_override_id,
            notes=line.notes,
        )
        db.session.add(new_line)
        count += 1

    return count