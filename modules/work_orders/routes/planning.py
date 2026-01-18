# File path: modules/work_orders/routes/planning.py
from modules.user.decorators import login_required
from modules.work_orders import work_orders_bp
from modules.work_orders.services.planning import plan_global_netting


@work_orders_bp.route("/planning.json")
@login_required
def planning_json():
    return plan_global_netting()
