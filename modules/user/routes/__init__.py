# /modules/user/routes/__init__.py

from flask import Blueprint, render_template, request, redirect, url_for, flash
from database.models import db, User
from werkzeug.security import generate_password_hash
from modules.user.decorators import login_required, admin_required

admin_users_bp = Blueprint("admin_users_bp", __name__)

@admin_users_bp.route("/")
@admin_required
def user_index():
    users = User.query.all()
    return render_template("user/index.html", users=users)

@admin_users_bp.route("/add_user", methods=["GET", "POST"])
@admin_required
def add_user():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        role = request.form.get("role")

        if not username or not password or not role:
            flash("❌ All fields are required.", "danger")
        elif User.query.filter_by(username=username).first():
            flash("❌ Username already exists.", "warning")
        else:
            user = User(username=username, role=role)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            flash(f"✅ User '{username}' added successfully.", "success")
            return redirect(url_for("admin_users_bp.user_index"))

    users = User.query.order_by(User.id).all()
    return render_template("user/add_user.html", users=users)

@admin_users_bp.route("/users/edit/<int:user_id>", methods=["POST"])
@admin_required
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    new_role = request.form.get("role")
    new_password = request.form.get("password")

    if new_role:
        user.role = new_role
    if new_password:
        user.set_password(new_password)

    db.session.commit()
    flash(f"✅ Updated user '{user.username}'", "success")
    return redirect(url_for("admin_users_bp.manage_users"))

@admin_users_bp.route("/users/delete/<int:user_id>", methods=["POST"])
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    flash(f"🗑️ Deleted user '{user.username}'", "info")
    return redirect(url_for("admin_users_bp.manage_users"))
