import os
from flask import Blueprint, render_template


jobs_bp = Blueprint("jobs_bp", __name__)

@jobs_bp.route("/")
def jobs_index():
    print("📋 Job Management route HIT")
    return render_template("jobs_management/index.html")
