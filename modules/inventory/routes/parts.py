# File path: modules/inventory/routes/parts.py
from flask import render_template, request, redirect, url_for, flash
from sqlalchemy import or_

from database.models import db, Part, PartType
from . import inventory_bp


# ---------------------------
# PART TYPES
# ---------------------------

@inventory_bp.route("/part-types")
def part_types_index():
    types = PartType.query.order_by(PartType.name.asc()).all()
    return render_template("inventory/part_types/index.html", types=types)

@inventory_bp.route("/part-types/new", methods=["GET", "POST"])
def part_types_new():
    if request.method == "POST":
        key = (request.form.get("key") or "").strip().lower()
        name = (request.form.get("name") or "").strip()

        if not key or not name:
            flash("Key and name are required.", "error")
            return render_template("inventory/part_types/new.html")

        exists = PartType.query.filter_by(key=key).first()
        if exists:
            flash("That key already exists.", "error")
            return render_template("inventory/part_types/new.html")

        db.session.add(PartType(key=key, name=name))
        db.session.commit()
        flash("Part type created.", "success")
        return redirect(url_for("inventory_bp.part_types_index"))

    return render_template("inventory/part_types/new.html")

@inventory_bp.route("/part-types/<int:type_id>/delete", methods=["POST"])
def part_types_delete(type_id):
    pt = PartType.query.get_or_404(type_id)
    # Prevent deleting types in use
    in_use = Part.query.filter_by(part_type_id=pt.id).first()
    if in_use:
        flash("Cannot delete: part type is in use by parts.", "error")
        return redirect(url_for("inventory_bp.part_types_index"))

    db.session.delete(pt)
    db.session.commit()
    flash("Part type deleted.", "success")
    return redirect(url_for("inventory_bp.part_types_index"))


# ---------------------------
# PARTS
# ---------------------------

@inventory_bp.route("/parts")
def parts_index():
    q = (request.args.get("q") or "").strip()
    parts_query = Part.query

    if q:
        like = f"%{q}%"
        parts_query = parts_query.filter(
            or_(
                Part.part_number.ilike(like),
                Part.name.ilike(like),
                Part.description.ilike(like),
            )
        )

    parts = parts_query.order_by(Part.part_number.asc()).all()
    return render_template("inventory/parts/index.html", parts=parts, q=q)

@inventory_bp.route("/parts/new", methods=["GET", "POST"])
def parts_new():
    types = PartType.query.order_by(PartType.name.asc()).all()

    if request.method == "POST":
        part_number = (request.form.get("part_number") or "").strip()
        name = (request.form.get("name") or "").strip()
        unit = (request.form.get("unit") or "ea").strip()
        description = (request.form.get("description") or "").strip()
        part_type_id = request.form.get("part_type_id") or None

        if not part_number or not name:
            flash("Part number and name are required.", "error")
            return render_template("inventory/parts/new.html", types=types)

        exists = Part.query.filter_by(part_number=part_number).first()
        if exists:
            flash("That part number already exists.", "error")
            return render_template("inventory/parts/new.html", types=types)

        p = Part(
            part_number=part_number,
            name=name,
            unit=unit or "ea",
            description=description or None,
            part_type_id=int(part_type_id) if part_type_id else None,
        )
        db.session.add(p)
        db.session.commit()
        flash("Part created.", "success")
        return redirect(url_for("inventory_bp.parts_index"))

    return render_template("inventory/parts/new.html", types=types)

@inventory_bp.route("/parts/<int:part_id>/edit", methods=["GET", "POST"])
def parts_edit(part_id):
    part = Part.query.get_or_404(part_id)
    types = PartType.query.order_by(PartType.name.asc()).all()

    if request.method == "POST":
        part_number = (request.form.get("part_number") or "").strip()
        name = (request.form.get("name") or "").strip()
        unit = (request.form.get("unit") or "ea").strip()
        description = (request.form.get("description") or "").strip()
        part_type_id = request.form.get("part_type_id") or None

        if not part_number or not name:
            flash("Part number and name are required.", "error")
            return render_template("inventory/parts/edit.html", part=part, types=types)

        # Ensure PN uniqueness (excluding self)
        exists = Part.query.filter(Part.part_number == part_number, Part.id != part.id).first()
        if exists:
            flash("That part number is already used by another part.", "error")
            return render_template("inventory/parts/edit.html", part=part, types=types)

        part.part_number = part_number
        part.name = name
        part.unit = unit or "ea"
        part.description = description or None
        part.part_type_id = int(part_type_id) if part_type_id else None

        db.session.commit()
        flash("Part updated.", "success")
        return redirect(url_for("inventory_bp.parts_index"))

    return render_template("inventory/parts/edit.html", part=part, types=types)

@inventory_bp.route("/parts/<int:part_id>/delete", methods=["POST"])
def parts_delete(part_id):
    part = Part.query.get_or_404(part_id)
    db.session.delete(part)
    db.session.commit()
    flash("Part deleted.", "success")
    return redirect(url_for("inventory_bp.parts_index"))
