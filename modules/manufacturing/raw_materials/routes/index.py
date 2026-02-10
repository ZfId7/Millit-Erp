# File path: modules/manufacturing/raw_materials/routes/index.py
# V1 Base Build | Raw Materials Index

from flask import render_template
from modules.user.decorators import login_required
from .. import raw_mats_bp

@raw_mats_bp.route("/")
@login_required
def raw_mats_index():
    return render_template("raw_materials/index.html")
