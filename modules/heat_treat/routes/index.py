# File path: modules/heat_treat/routes/index.py
# -V1 Base Build - Index
from flask import render_template
from modules.user.decorators import login_required
from modules.heat_treat import heat_treat_bp

@heat_treat_bp.route("/")
@login_required
def heat_treat_index():
    return render_template("heat_treat/index.html")
