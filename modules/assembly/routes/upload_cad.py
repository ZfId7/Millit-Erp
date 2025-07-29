# /Millit_ERP/modules/assembly/routes/upload_cad.py

import os
import json
from flask import Blueprint, render_template, request, redirect, url_for, flash
from werkzeug.utils import secure_filename
from database.models import db, Assembly
from modules.assembly.parser.step_parser import parse_step
from modules.user.decorators import login_required, admin_required

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), '../uploads/cad')
PUBLIC_FOLDER = os.path.join("static/uploads/cad")
ALLOWED_EXTENSIONS = {'step', 'stp'}

cad_upload_bp = Blueprint("cad_upload_bp", __name__)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@cad_upload_bp.route("/upload_cad", methods=["GET", "POST"])
@login_required
def upload_cad():
    if request.method == "POST":
        file = request.files.get("cad_file")
        assembly_id = request.form.get("assembly_id")

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            save_path = os.path.join(UPLOAD_FOLDER, filename)
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            file.save(save_path)

            # ✅ Copy to public static folder so it can be viewed
            public_path = os.path.join(PUBLIC_FOLDER, filename)
            os.makedirs(os.path.dirname(public_path), exist_ok=True)
            file.save(public_path)

            # 🔹 Parse the STEP file and save to .json
            try:
                parse_result = parse_step(public_path)
                shapes_json_filename = filename.rsplit('.', 1)[0] + ".json"
                shapes_json_path = os.path.join(PUBLIC_FOLDER, shapes_json_filename)
                with open(shapes_json_path, "w") as jf:
                    json.dump(parse_result, jf)
            except Exception as e:
                flash(f"❌ STEP parsing failed: {e}", "danger")
                return redirect(url_for("cad_upload_bp.upload_cad"))

            # ✅ Link to an existing Assembly if ID is provided
            if assembly_id:
                assembly = Assembly.query.get(int(assembly_id))
                if assembly:
                    assembly.cad_filename = filename
                    assembly.shapes_filename = shapes_json_filename  # <--- Make sure you add this field to the model & db
                    db.session.commit()
                    flash(f"✅ Linked CAD to Assembly {assembly.name}", "success")
                else:
                    flash("❌ Assembly not found.", "danger")
            else:
                flash(f"✅ File uploaded: {filename} (not linked)", "success")

            return redirect(url_for("cad_upload_bp.upload_cad"))
        else:
            flash("❌ Invalid file type. Please upload a .step or .stp file.", "danger")

    return render_template("assembly/upload_cad.html")
