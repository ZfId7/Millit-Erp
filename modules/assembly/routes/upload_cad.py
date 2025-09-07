# File: modules/assembly/routes/upload_cad.py
# Purpose: Handle STEP upload, parse to multi-part shapes JSON, and persist per-solid rows

import os
import json
import shutil
from flask import Blueprint, render_template, request, redirect, url_for, flash
from werkzeug.utils import secure_filename

from database.models import db, Assembly, ParsedComponent
from modules.assembly.parser.step_parser import parse_step
from modules.user.decorators import login_required  # admin_required not needed here

# Storage paths
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), '../uploads/cad')
PUBLIC_FOLDER = os.path.join('static/uploads/cad')  # served by Flask static
ALLOWED_EXTENSIONS = {'step', 'stp'}

cad_upload_bp = Blueprint("cad_upload_bp", __name__)


def allowed_file(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@cad_upload_bp.route("/upload_cad", methods=["GET", "POST"])
@login_required
def upload_cad():
    if request.method == "POST":
        file = request.files.get("cad_file")
        assembly_id = request.form.get("assembly_id")

        if not file or not allowed_file(file.filename):
            flash("❌ Invalid file type. Please upload a .step or .stp file.", "danger")
            return redirect(url_for("cad_upload_bp.upload_cad"))

        # Save original upload and copy to public/static
        filename = secure_filename(file.filename)
        save_path = os.path.join(UPLOAD_FOLDER, filename)
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        file.save(save_path)

        public_path = os.path.join(PUBLIC_FOLDER, filename)
        os.makedirs(os.path.dirname(public_path), exist_ok=True)
        shutil.copyfile(save_path, public_path)

        # Parse STEP → shapes JSON (multi-solid)
        try:
            # Use absolute path for the parser to avoid CWD issues
            abs_public = os.path.abspath(public_path)
            parse_result = parse_step(abs_public)

            shapes_json_filename = filename.rsplit('.', 1)[0] + ".json"
            shapes_json_path = os.path.join(PUBLIC_FOLDER, shapes_json_filename)
            with open(shapes_json_path, "w") as jf:
                json.dump(parse_result, jf)
        except Exception as e:
            flash(f"❌ STEP parsing failed: {e}", "danger")
            return redirect(url_for("cad_upload_bp.upload_cad"))

        # Optionally link to an Assembly and persist parsed components
        if assembly_id:
            assembly = Assembly.query.get(int(assembly_id))
            if not assembly:
                flash("❌ Assembly not found.", "danger")
                return redirect(url_for("cad_upload_bp.upload_cad"))

            # Link files to assembly
            assembly.cad_filename = filename
            assembly.shapes_filename = shapes_json_filename

            # Rebuild parsed components for this assembly
            try:
                # Clear previous rows for a clean rebuild
                ParsedComponent.query.filter_by(assembly_id=assembly.id).delete()

                parts = parse_result.get("parts", [])
                for i, p in enumerate(parts):
                    metrics = p.get("metrics") or {}
                    db.session.add(ParsedComponent(
                        assembly_id=assembly.id,
                        solid_index=i,
                        name=p.get("name") or f"Solid_{i}",
                        color=p.get("color"),
                        mesh_hash=metrics.get("mesh_hash"),
                        volume=metrics.get("volume"),
                        bb=p.get("bb")
                    ))

                db.session.commit()
                flash(f"✅ Linked CAD to Assembly {assembly.name} and stored {len(parts)} components.", "success")
            except Exception as e:
                db.session.rollback()
                flash(f"⚠️ Linked files but failed to store parsed components: {e}", "danger")
        else:
            flash(f"✅ File uploaded: {filename} (not linked)", "success")

        return redirect(url_for("cad_upload_bp.upload_cad"))

    # GET
    return render_template("assembly/upload_cad.html")
