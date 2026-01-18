# File path: modules/work_orders/services/planning.py
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


def plan_global_netting(rev="A", max_depth=6):
    from collections import defaultdict

    fg_demand = defaultdict(float)         # (part_id, config_key) -> qty requested
    sub_assy_demand = defaultdict(float)   # part_id -> qty requested
    comp_demand = defaultdict(float)       # part_id -> qty required

    # Track current recursion path (part_id) to detect cycles
    path = set()

    def explode_part(part_id, qty, depth):
        if depth > max_depth:
            raise RuntimeError("BOM recursion depth exceeded (check for deep nesting)")

        if part_id in path:
            raise RuntimeError("BOM cycle detected (a sub-assembly references itself)")

        bom = _get_active_bom(part_id, rev=rev)
        if not bom:
            # If no BOM exists, treat it as a leaf component demand
            comp_demand[part_id] += qty
            return

        path.add(part_id)

        for line in bom.lines:
            child = line.component_part
            child_qty = qty * float(line.qty_per or 0.0)

            # If a child part doesn't have a part_type, treat as component
            cat = "component"
            if child.part_type and child.part_type.category_key:
                cat = child.part_type.category_key

            if cat in ("component", "hardware", "raw"):
                comp_demand[child.id] += child_qty

            elif cat == "sub_assembly":
                # Stock-first for sub assemblies:
                have = _sum_inventory(child.id, SUB_ASSY_AVAILABLE, rev=rev)
                remaining = max(0.0, child_qty - have)

                sub_assy_demand[child.id] += child_qty

                if remaining > 0:
                    explode_part(child.id, remaining, depth + 1)

            else:
                # Defensive: unknown categories count as component demand
                comp_demand[child.id] += child_qty

        path.remove(part_id)

    # --- Gather open work orders ---
    work_orders = WorkOrder.query.filter(WorkOrder.status.in_(OPEN_WO_STATUSES)).all()

    for wo in work_orders:
        for line in wo.lines:
            qty = float(line.qty_requested or 0.0)
            if qty <= 0:
                continue

            part = line.part
            if not part or not part.part_type or not part.part_type.category_key:
                # If not classified, treat as component
                comp_demand[line.part_id] += qty
                continue

            cat = part.part_type.category_key
            cfg = line.config_key

            if cat == "assembly":
                have = _sum_inventory(part.id, FG_AVAILABLE, rev=rev, config_key=cfg)
                remaining = max(0.0, qty - have)

                fg_demand[(part.id, cfg)] += qty

                if remaining > 0:
                    explode_part(part.id, remaining, depth=1)

            elif cat == "sub_assembly":
                have = _sum_inventory(part.id, SUB_ASSY_AVAILABLE, rev=rev)
                remaining = max(0.0, qty - have)

                sub_assy_demand[part.id] += qty

                if remaining > 0:
                    explode_part(part.id, remaining, depth=1)

            else:
                comp_demand[part.id] += qty

    # --- Net components ---
    component_results = []
    for part_id, demand in comp_demand.items():
        available = _sum_inventory(part_id, COMP_AVAILABLE, rev=rev)
        expected = _sum_inventory(part_id, COMP_EXPECTED, rev=rev)
        
        label = _part_label(part_id)
        
        component_results.append({
            "part_id": part_id,
            ** label,
            "demand": demand,
            "available": available,
            "expected": expected,
            "shortage_now": max(0.0, demand - available),
            "shortage_after_expected": max(0.0, demand - (available + expected)),
        })

    component_results.sort(key=lambda r: r["part_id"])

    finished_goods = []
    for (pid, cfg), qty in fg_demand.items():
        label = _part_label(pid)
        
        finished_goods.append({
            "part_id": pid,
            **label,
            "config_key": cfg,
            "demand": qty,
            "available": _sum_inventory(pid, FG_AVAILABLE, rev=rev, config_key=cfg),
        })

    finished_goods.sort(key=lambda r: (r["part_id"], r["config_key"] or ""))

    sub_assemblies = []
    for pid, qty in sub_assy_demand.items():
        label = _part_label(pid)
        
        sub_assemblies.append({
            "part_id": pid,
            **label,
            "demand": qty,
            "available": _sum_inventory(pid, SUB_ASSY_AVAILABLE, rev=rev),
        })

    sub_assemblies.sort(key=lambda r: r["part_id"])

    return {
        "finished_goods": finished_goods,
        "sub_assemblies": sub_assemblies,
        "components": component_results,
    }