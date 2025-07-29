from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from database.models import db, User

auth_bp = Blueprint("auth_bp", __name__)

@auth_bp.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            session["user_id"] = user.id
            session["username"] = user.username
            session["is_admin"] = user.is_admin()
            flash("✅ Logged in successfully", "success")
            return redirect(url_for("dashboard_bp.dashboard"))
        else:
            flash("❌ Invalid username or password", "danger")

    return render_template("login.html")

@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("🔒 Logged out", "info")
    return redirect(url_for("auth_bp.login"))
