import os
from flask import Blueprint, render_template


analytics_bp = Blueprint("analytics_bp", __name__)

@analytics_bp.route("/")
def analytics_index():
    print("📊 Analytics route HIT")
    return render_template("analytics/index.html")
