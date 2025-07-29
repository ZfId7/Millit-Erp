from functools import wraps
from flask import session, redirect, url_for, flash

def login_required(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            flash("🔐 Please log in to access this page.", "warning")
            return redirect(url_for("auth_bp.login"))
        return f(*args, **kwargs)
    return wrapped

def admin_required(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        if not session.get("is_admin"):
            flash("⚠️ Admin access required.", "danger")
            return redirect(url_for("dashboard_bp.dashboard"))
        return f(*args, **kwargs)
    return wrapped
