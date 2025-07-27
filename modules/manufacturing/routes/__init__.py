import os
from flask import Blueprint, render_template


mfg_bp = Blueprint("mfg_bp", __name__)

@mfg_bp.route("/")
def mfg_index():
    print("🏭Manufacturing route HIT")
    return render_template("manufacturing/index.html")
