import os
from flask import Blueprint, render_template


surface_bp = Blueprint("surface_grinding_bp", __name__)

@surface_bp.route("/")
def surface_index():
    print("🧱 Surface Grinding route HIT")
    return render_template("surface_grinding/index.html")

