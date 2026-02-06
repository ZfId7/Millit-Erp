# File path: modules/admin/routes/index.py

from flask import render_template
from modules.admin import admin_bp
from modules.user.decorators import admin_required


@admin_bp.get("/")
@admin_required
def admin_index():
    return render_template("admin/index.html")
