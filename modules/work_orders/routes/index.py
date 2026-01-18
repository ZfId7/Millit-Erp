# File path: modules/work_orders/routes/index.py
from flask import render_template
from modules.user.decorators import login_required
from modules.work_orders import work_orders_bp


@work_orders_bp.route("/")
@login_required
def work_orders_index():
    return render_template("work_orders/index.html")
