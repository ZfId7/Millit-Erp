#File path: modules/user/decorators.py

from functools import wraps
from flask import session, redirect, url_for, flash

def _is_logged_in() -> bool:
    # Transition-safe: accept either legacy session["user"] or new session["user_id"]
    return bool(session.get("user_id") or session.get("user"))

def login_required(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        if not _is_logged_in():
            flash("🔐 Please log in to access this page.", "warning")
            return redirect(url_for("auth_bp.login"))
        return f(*args, **kwargs)
    return wrapped


def admin_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if not _is_logged_in() or not session.get("is_admin"):
            flash("⛔ Admin access required", "danger")
            return redirect(url_for("auth_bp.login"))
        return view_func(*args, **kwargs)
    return wrapper
