# File path: modules/inventory/routes/part_drawings.py

import os
from flask import (
    request,
    redirect,
    url_for,
    flash,
    current_app,
    send_file,
)
from werkzeug.utils import secure_filename

from database.models import db, Part, PartDrawing
from modules.user.decorators import login_required
from modules.inventory import inventory_bp



def _part_drawing_storage_dir(part_id: int) -> str:
    return os.path.join(
        current_app.root_path,
        "modules",
        "inventory",
        "uploads",
        "part_drawings",
        str(part_id),
    )


def _abs_from_stored_path(stored_path: str) -> str:
    return os.path.join(current_app.root_path, stored_path)


@inventory_bp.route("/parts/<int:part_id>/drawings/upload", methods=["POST"])
@login_required
def part_drawing_upload(part_id):
    part = Part.query.get_or_404(part_id)

    f = request.files.get("drawing_file")
    if not f or not f.filename:
        flash("No file selected.", "error")
        return redirect(request.referrer)

    filename = secure_filename(f.filename)
    if not filename.lower().endswith(".pdf"):
        flash("Only PDF drawings are supported.", "error")
        return redirect(request.referrer)

    rev = (request.form.get("rev") or "A").strip()
    drawing_type = (request.form.get("drawing_type") or "cad_pdf").strip()
    notes = (request.form.get("notes") or "").strip() or None

    abs_dir = _part_drawing_storage_dir(part.id)
    os.makedirs(abs_dir, exist_ok=True)

    abs_path = os.path.join(abs_dir, filename)
    if os.path.exists(abs_path):
        flash("A drawing with that filename already exists for this part.", "error")
        return redirect(request.referrer)

    f.save(abs_path)

    rel_path = os.path.relpath(abs_path, current_app.root_path)

    drawing = PartDrawing(
        part_id=part.id,
        filename=filename,
        stored_path=rel_path,
        drawing_type=drawing_type,
        rev=rev,
        notes=notes,
    )

    db.session.add(drawing)
    db.session.commit()

    flash("Part drawing uploaded.", "success")
    return redirect(request.referrer)


@inventory_bp.route("/part_drawings/<int:drawing_id>/view", methods=["GET"])
@login_required
def view_part_drawing(drawing_id):
    drawing = PartDrawing.query.get_or_404(drawing_id)

    abs_path = _abs_from_stored_path(drawing.stored_path)
    if not os.path.exists(abs_path):
        flash("Drawing file not found on disk.", "error")
        return redirect(request.referrer)

    return send_file(
        abs_path,
        mimetype="application/pdf",
        as_attachment=False,
        download_name=drawing.filename,
    )
