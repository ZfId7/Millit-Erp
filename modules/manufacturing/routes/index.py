# File path: modules/manufacturing/routes/index.py
# V1 Refactor Index

from flask import render_template
from modules.user.decorators import login_required
from modules.manufacturing import mfg_bp

@mfg_bp.route("/")
@login_required
def mfg_index():
    print("🏭Manufacturing route HIT")
    return render_template("manufacturing/index.html")