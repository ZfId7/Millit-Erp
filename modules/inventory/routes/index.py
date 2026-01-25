# File path: modules/inventory/routes/index.py
from flask import render_template
from modules.user.decorators import login_required
from modules.inventory import inventory_bp


@inventory_bp.route("/")
@login_required
def inventory_index():
    return render_template("inventory/index.html")
