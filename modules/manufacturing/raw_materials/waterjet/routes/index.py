# File path: modules/manufacturing/raw_materials/waterjet/routes/index.py
# V1 Refactor Index
# V2 Refactor | move inside of modules/raw_materials/waterjet/ | change blueprint to raw_mats_waterjet_bp

from flask import render_template
from modules.user.decorators import login_required
from .. import raw_mats_waterjet_bp

@raw_mats_waterjet_bp.route("/")
@login_required
def waterjet_index():
    return render_template("raw_materials/waterjet/index.html")
