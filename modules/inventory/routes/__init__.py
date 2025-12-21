# File path: modules/inventory/routes/__init__.py
from flask import Blueprint, render_template

inventory_bp = Blueprint("inventory_bp", __name__)

@inventory_bp.route("/")
def inventory_index():
    print("📦 Inventory route HIT")
    return render_template("inventory/index.html")

# IMPORTANT: import route modules AFTER blueprint creation
from . import parts  # noqa: E402
from . import routing #noqa: E402
