import os
from flask import Blueprint, render_template


bevel_bp = Blueprint("bevel_bp", __name__)

@bevel_bp.route("/")
def bevel_index():
    print("🔪 Bevel Grinding route HIT")
    return render_template("bevel_grinding/index.html")
