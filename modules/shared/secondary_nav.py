# File path: modules/shared/secondary_nav.py

# modules/shared/secondary_nav.py

from typing import Dict, List, Optional

Tab = Dict[str, str]

def _tabs(*items: Tab) -> List[Tab]:
    return list(items)

SECONDARY_NAV_RULES = [
    # ----------------------------
    # Inventory / Catalog section
    # ----------------------------
    {
        "match": {
            "blueprint": "inventory_bp",
                "endpoint_prefixes": [
                    "inventory_bp.inventory_catalog", 
                    "inventory_bp.raw_stock", 
                    "inventory_bp.bulk",
                    "inventory_bp.parts_inventory",
                ]
             
        },
        "tabs": _tabs(
            {"label": "Raw Stock", "endpoint": "inventory_bp.raw_stock_index"},
            {"label": "Bulk Hardware", "endpoint": "inventory_bp.bulk_index"},
            {"label": "Parts Inventory", "endpoint": "inventory_bp.parts_inventory_index"},
        ),
    },

    # ----------------------------
    # Inventory / Master BOM section
    # ----------------------------
    {
        "match": {
            "blueprint": "inventory_bp",
            "endpoint_prefixes": [
                "inventory_bp.bom",
                "inventory_bp.parts",
                "inventory_bp.part_types",
            ],
        },
        "tabs": _tabs(
            {"label": "Parts Catalog", "endpoint": "inventory_bp.parts_index"},
            {"label": "Part Type Manager", "endpoint": "inventory_bp.part_types_index"},
        ),
    },
]


def resolve_secondary_tabs(blueprint: Optional[str], endpoint: Optional[str]) -> List[Tab]:
    """
    Returns the secondary tabs for the current request based on matching rules.
    Rules can match by blueprint + endpoint prefix.
    """
    if not blueprint or not endpoint:
        return []

    for rule in SECONDARY_NAV_RULES:
        match = rule.get("match", {})
        if match.get("blueprint") and match["blueprint"] != blueprint:
            continue

        prefixes = match.get("endpoint_prefixes")
        if prefixes:
            if not any(endpoint.startswith(p) for p in prefixes):
                continue
        else:
            prefix = match.get("endpoint_prefix")
            if prefix and not endpoint.startswith(prefix):
                continue

        return rule.get("tabs", [])

    return []
