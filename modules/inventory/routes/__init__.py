import os
from flask import Blueprint, render_template


inventory_bp = Blueprint("inventory_bp", __name__)

@inventory_bp.route("/")
def inventory_index():
    print("📦 Inventory route HIT")
    return render_template("inventory/index.html")
