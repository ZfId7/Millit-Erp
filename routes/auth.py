from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import check_password_hash
from database.models import User

auth_bp = Blueprint("auth_bp", __name__)

@auth_bp.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        print("📝 Attempting login for:", username)
      
        user = User.query.filter_by(username=username).first()

        if user: 
            if check_password_hash(user.password_hash, password):
                print("✅ Login successful. Setting session.")
                session["user"] = user.username          # keep for display/back-compat
                session["user_id"] = user.id             # NEW: numeric id for claims/progress
                session["is_admin"] = (user.role == "admin")

                return redirect(url_for("dashboard_bp.dashboard"))
            else:
                flash("❌ Invalid username or password", "danger")
                print("❌ Password mismatch for:", username)
        else:
            flash("❌ User not found", "danger")
            print("❌ No such user:", username)
    return render_template("login.html")

    


@auth_bp.route("/logout")
def logout():
    print("🔒 Logging out user:", session.get("user"))
    session.clear()
    print("🧹 Session after logout:", dict(session))
    flash("🔒 Logged out", "info")
    return redirect(url_for("auth_bp.login"))
