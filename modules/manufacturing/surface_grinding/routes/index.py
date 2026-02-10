# File path: modules/manufacturing/surface_grinding/routes/index.py
# V1 Refactor Index

from flask import render_template
from modules.user.decorators import login_required
from .. import surface_bp

@surface_bp.route("/")
@login_required
def surface_index():
    return render_template("surface_grinding/index.html")
