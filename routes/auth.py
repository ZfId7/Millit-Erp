from flask import Blueprint, render_template, request, redirect, url_for, session

auth_bp = Blueprint("auth_bp", __name__)

@auth_bp.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        if username:
            session["user"] = username
            session["is_admin"] = True if username.lower() == "admin" else False
            return redirect(url_for("dashboard_bp.dashboard"))
    return render_template("login.html")
