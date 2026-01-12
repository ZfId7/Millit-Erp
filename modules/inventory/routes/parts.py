# File path: modules/inventory/routes/parts.py
from flask import render_template, request, redirect, url_for, flash
from sqlalchemy import or_

from database.models import db, Part, PartType
from modules.user.decorators import login_required, admin_required
from . import inventory_bp


# ---------------------------
# PART TYPES
# ---------------------------

CATEGORY_OPTIONS = [
    ("assembly", "Assembly"),
    ("sub_assembly", "Sub-Assembly"),
    ("component", "Component"),
    ("hardware", "Hardware"),
    ("raw", "Raw"),
]

ALLOWED_CATEGORY_KEYS = {k for k, _ in CATEGORY_OPTIONS}

@inventory_bp.route("/part-types")
@login_required
@admin_required
def part_types_index():
    part_types = PartType.query.order_by(
		PartType.code.asc().nullslast(),
		PartType.name.asc()
	).all()
	
    return render_template(
    "inventory/part_types/index.html", 
    part_types=part_types,
    category_options=CATEGORY_OPTIONS,
    )

@inventory_bp.route("/part-types/new", methods=["GET", "POST"])
@login_required
@admin_required
def part_types_new():
    if request.method == "POST":
        key = (request.form.get("key") or "").strip().lower()
        name = (request.form.get("name") or "").strip()
        category_key = (request.form.get("category_key") or "component").strip()
        code = (request.form.get("code") or "").strip().upper() or None
        
        if code:
            exists_code = PartType.query.filter_by(code=code).first()
            if exists_code:
                flash("That code already exists.", "error")
                return render_template(
                    "inventory/part_types/new.html",
                    category_options=CATEGORY_OPTIONS,
                    form={"key": key, "name": name, "category_key": category_key, "code": code},
                )

        if not key or not name:
            flash("Key and name are required.", "error")
            return render_template(
            "inventory/part_types/new.html",
            category_options=CATEGORY_OPTIONS,
            form={"key": key, "name": name, "category_key": category_key},
            )
        
        if category_key not in ALLOWED_CATEGORY_KEYS:
          category_key = "component"

        exists = PartType.query.filter_by(key=key).first()
        if exists:
            flash("That key already exists.", "error")
            return render_template(
            "inventory/part_types/new.html",
            category_options=CATEGORY_OPTIONS,
            form={"key": key, "name": name, "category_key": category_key},
            )
        
        db.session.add(PartType(key=key, name=name, category_key=category_key, code=code))
        db.session.commit()
        flash("Part type created.", "success")
        return redirect(url_for("inventory_bp.part_types_index"))

    return render_template("inventory/part_types/new.html", category_options=CATEGORY_OPTIONS)

@inventory_bp.route("/part-types/<int:type_id>/edit", methods=["GET", "POST"])
@login_required
@admin_required
def part_types_edit(type_id):
    pt = PartType.query.get_or_404(type_id)

    if request.method == "POST":
        key = (request.form.get("key") or "").strip().lower()
        name = (request.form.get("name") or "").strip()
        category_key = (request.form.get("category_key") or "component").strip()
        code = (request.form.get("code") or "").strip().upper() or None

        # Validate category
        if category_key not in ALLOWED_CATEGORY_KEYS:
            category_key = "component"
        
        # Code uniqueness (excluding self)
        if code:
            exists_code = PartType.query.filter(PartType.code == code, PartType.id != pt.id).first()
            if exists_code:
                flash("That code is already used by another part type.", "error")
                return render_template(
                    "inventory/part_types/edit.html",
                    pt=pt,
                    category_options=CATEGORY_OPTIONS,
                )

        if not key or not name:
            flash("Key and name are required.", "error")
            return render_template(
                "inventory/part_types/edit.html",
                pt=pt,
                category_options=CATEGORY_OPTIONS,
            )

        # Ensure key uniqueness (excluding self)
        exists = PartType.query.filter(PartType.key == key, PartType.id != pt.id).first()
        if exists:
            flash("That key is already used by another part type.", "error")
            return render_template(
                "inventory/part_types/edit.html",
                pt=pt,
                category_options=CATEGORY_OPTIONS,
            )

        pt.key = key
        pt.name = name
        pt.category_key = category_key
        pt.code = code

        db.session.commit()
        flash("Part type updated.", "success")
        return redirect(url_for("inventory_bp.part_types_index"))

    return render_template("inventory/part_types/edit.html", pt=pt, category_options=CATEGORY_OPTIONS)
    
@inventory_bp.route("/part-types/<int:type_id>/delete", methods=["POST"])
@login_required
@admin_required
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
@login_required
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
@login_required
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
@login_required
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
@login_required
@admin_required
def parts_delete(part_id):
    part = Part.query.get_or_404(part_id)
    db.session.delete(part)
    db.session.commit()
    flash("Part deleted.", "success")
    return redirect(url_for("inventory_bp.parts_index"))

# updated 1/11/26
@inventory_bp.route("/parts/quick-create", methods=["POST"])
@login_required
def parts_quick_create():
    """
    Create a minimal draft Part from the BOM screen.
    Intended for inline creation and later CAD import usage.
    """
    bom_id = request.form.get("bom_id", type=int)

    part_number = (request.form.get("part_number") or "").strip()
    name = (request.form.get("name") or "").strip()
    description = (request.form.get("description") or "").strip() or None
    unit = (request.form.get("unit") or "ea").strip()
    category_key = (request.form.get("category_key") or "component").strip()

    if not part_number and not name:
        flash("Enter a Part Number or Name to create a part.", "error")
        return redirect(url_for("inventory_bp.bom_details", bom_id=bom_id))

    # If part_number exists, prevent duplicates
    if part_number:
        existing = Part.query.filter_by(part_number=part_number).first()
        if existing:
            flash("Part already exists. Select it from the list.", "info")
            return redirect(url_for("inventory_bp.bom_details", bom_id=bom_id))

    # Auto-pick a PartType by category_key (optional but helpful)
    part_type = PartType.query.filter_by(category_key=category_key).first()
    if not part_type:
        # Create a simple type on the fly (you can refine later)
        part_type = PartType(
            name=category_key.replace("_", " ").title(),
            category_key=category_key,
        )
        db.session.add(part_type)
        db.session.flush()

    p = Part(
        part_number=part_number or None,
        name=name or part_number,  # fallback so it’s not blank
        description=description,
        unit=unit,
        part_type_id=part_type.id,
        status="draft",  # ✅ draft by default
    )

    db.session.add(p)
    db.session.commit()

    flash("Draft part created.", "success")
    return redirect(url_for("inventory_bp.bom_details", bom_id=bom_id))
