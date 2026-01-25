# File path: modules/inventory/routes/stock_history.py

from flask import render_template, request, abort
from modules.user.decorators import login_required
from modules.inventory.services.stock_history_service import get_stock_history
from modules.inventory import inventory_bp


# Optional display helpers (purely for UI labels)
DISPLAY_TYPE = {
    "bulk_hardware": "Bulk Hardware",
    "raw_stock": "Raw Stock",
    "part_inventory": "Part Inventory",
}


@inventory_bp.route("/stock/history/<string:entity_type>/<int:entity_id>")
@login_required
def stock_history(entity_type, entity_id):
    if entity_type not in DISPLAY_TYPE:
        abort(404)

    limit = int(request.args.get("limit") or 250)
    entries = get_stock_history(entity_type=entity_type, entity_id=entity_id, limit=limit)

    return render_template(
        "inventory/stock/history.html",
        entity_type=entity_type,
        entity_id=entity_id,
        entity_label=DISPLAY_TYPE.get(entity_type, entity_type),
        entries=entries,
        limit=limit,
    )
