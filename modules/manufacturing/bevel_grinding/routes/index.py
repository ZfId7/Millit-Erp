# File path: modules/manufacturing/bevel_grinding/routes/index.py

from flask import render_template
from .. import bevel_bp

@bevel_bp.route("/")
def bevel_index():
    print("🔪 Bevel Grinding route HIT")
    return render_template("bevel_grinding/index.html")
