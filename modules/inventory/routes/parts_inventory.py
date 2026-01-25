# File path: modules/inventory/routes/parts_inventory.py
from flask import render_template, request
from modules.user.decorators import login_required
from modules.inventory import inventory_bp
from database.models import PartInventory


@inventory_bp.route("/parts_inventory", methods=["GET"])
@login_required
def parts_inventory_index():
    stage = (request.args.get("stage") or "").strip()

    q = PartInventory.query.join(PartInventory.part).filter(PartInventory.is_active.is_(True))
    if stage:
        q = q.filter(PartInventory.stage_key == stage)

    items = q.order_by(PartInventory.stage_key.asc(), PartInventory.id.asc()).all()

    return render_template("inventory/parts_inventory/index.html", items=items, stage=stage)
