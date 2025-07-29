from flask import Blueprint, render_template, session, redirect, url_for
from modules.user.decorators import login_required, admin_required

dashboard_bp = Blueprint("dashboard_bp", __name__, url_prefix="/dashboard")

@dashboard_bp.route("/")
@login_required
def dashboard():
    username = session.get("user")
    if not username:
        return redirect(url_for("auth_bp.login"))
    return render_template("dashboard.html", username=username)
