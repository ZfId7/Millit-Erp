# File path: modules/inventory/routes/bom.py
from datetime import datetime
from flask import render_template, request, redirect, url_for, flash

from database.models import db, Part, PartType, BOMHeader, BOMLine, RoutingHeader, RoutingStep, BOMItem
from modules.user.decorators import login_required, admin_required
from . import inventory_bp


import re

PART_CODE_RE = re.compile(r"^[A-Za-z0-9]+-([A-Za-z]+)\d+", re.IGNORECASE)

def infer_part_type_from_part_number(part_number: str):
    if not part_number:
        return None
    m = PART_CODE_RE.match(part_number.strip())
    if not m:
        return None
    code = m.group(1).upper()
    return PartType.query.filter_by(code=code).first()

@inventory_bp.route("/bom")
@login_required
def bom_index():
    boms = (
        BOMHeader.query
        .order_by(BOMHeader.updated_at.desc(), BOMHeader.id.desc())
        .all()
    )
    return render_template("inventory/bom/index.html", boms=boms)

@inventory_bp.route("/bom/new", methods=["GET"])
@login_required
def bom_new():
    # Only allow assemblies/sub-assemblies as BOM headers
    assemblies = (
        Part.query
        .join(PartType, Part.part_type_id == PartType.id)
        .filter(PartType.category_key.in_(["assembly", "sub_assembly"]))
        .order_by(Part.part_number.asc())
        .all()
    )
    return render_template("inventory/bom/new.html", assemblies=assemblies)

@inventory_bp.route("/bom/create", methods=["GET", "POST"])
@login_required
def bom_create():
    assembly_part_id = request.form.get("assembly_part_id", type=int)
    rev = (request.form.get("rev") or "A").strip()
    is_active = bool(request.form.get("is_active"))

    if not assembly_part_id:
        flash("Select an assembly.", "error")
        return redirect(url_for("inventory_bp.bom_new"))

    if not rev:
        flash("Revision cannot be blank.", "error")
        return redirect(url_for("inventory_bp.bom_new"))

    # If setting active, disable other active revs for same assembly
    if is_active:
        (BOMHeader.query
         .filter(BOMHeader.assembly_part_id == assembly_part_id)
         .update({BOMHeader.is_active: False}))

    bom = BOMHeader(
        assembly_part_id=assembly_part_id,
        rev=rev,
        is_active=is_active,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.session.add(bom)
    db.session.commit()

    flash("BOM created.", "success")
    return redirect(url_for("inventory_bp.bom_details", bom_id=bom.id))


# updated 1/10/26
@inventory_bp.route("/bom/<int:bom_id>", methods=["GET"])
@login_required
def bom_details(bom_id):
    bom = BOMHeader.query.get_or_404(bom_id)
    part_types = PartType.query.order_by(PartType.category_key.asc(), PartType.name.asc()).all()

    # Component picklist (components + subassemblies + hardware)
    components = (
        Part.query
        .join(PartType, Part.part_type_id == PartType.id)
        .filter(PartType.category_key.in_(["component", "sub_assembly", "hardware"]))
        .order_by(Part.part_number.asc())
        .all()
    )

    lines = (
        BOMLine.query
        .filter(BOMLine.bom_id == bom.id)
        .order_by(BOMLine.line_no.asc(), BOMLine.id.asc())
        .all()
    )

    # ----------------------------
    # V1: routing lookup by component part
    # ----------------------------
    make_part_ids = [
        l.component_part_id
        for l in lines
        if (l.make_method or "MAKE").upper() == "MAKE"
    ]

    routing_map = {}            # part_id -> routing_header_id
    routing_rev_map = {}        # part_id -> rev string
    routing_steps_count = {}    # routing_header_id -> count
    routing_summary = {}        # routing_header_id -> "waterjet → grind → ht"

    if make_part_ids:
        # Get active routing headers for these parts
        routings = (
            RoutingHeader.query
            .filter(RoutingHeader.part_id.in_(make_part_ids), RoutingHeader.is_active == True)
            .all()
        )
        routing_map = {r.part_id: r.id for r in routings}
        routing_rev_map = {r.part_id: r.rev for r in routings}

        routing_ids = [r.id for r in routings]
        if routing_ids:
            steps = (
                RoutingStep.query
                .filter(RoutingStep.routing_id.in_(routing_ids))
                .order_by(RoutingStep.routing_id.asc(), RoutingStep.sequence.asc())
                .all()
            )

            # Count + build summary text
            steps_by_routing = {}
            for s in steps:
                steps_by_routing.setdefault(s.routing_id, []).append(s)

            for rid, s_list in steps_by_routing.items():
                routing_steps_count[rid] = len(s_list)
                # summary like: waterjet → grind → ht (use op_key or op_name)
                routing_summary[rid] = " \u2192 ".join([x.op_key for x in s_list])

    return render_template(
        "inventory/bom/details.html",
        bom=bom,
        part_types=part_types,
        components=components,
        lines=lines,
        routing_map=routing_map,
        routing_rev_map=routing_rev_map,
        routing_steps_count=routing_steps_count,
        routing_summary=routing_summary,
    )


@inventory_bp.route("/bom/<int:bom_id>/active", methods=["GET", "POST"])
@login_required
def bom_set_active(bom_id):
    bom = BOMHeader.query.get_or_404(bom_id)

    # deactivate others
    (BOMHeader.query
     .filter(BOMHeader.assembly_part_id == bom.assembly_part_id)
     .update({BOMHeader.is_active: False}))

    bom.is_active = True
    db.session.commit()

    flash("BOM marked active for this assembly.", "success")
    return redirect(url_for("inventory_bp.bom_details", bom_id=bom.id))

@inventory_bp.route("/bom/<int:bom_id>/lines/add", methods=["POST"])
@login_required
def bom_add_line(bom_id):
    bom = BOMHeader.query.get_or_404(bom_id)

    component_part_id = request.form.get("component_part_id", type=int)

    # Inline create fields (optional)
    new_part_number = (request.form.get("new_part_number") or "").strip()
    new_name = (request.form.get("new_name") or "").strip()
    new_description = (request.form.get("new_description") or "").strip() or None
    new_unit = (request.form.get("new_unit") or "ea").strip()
    new_category_key = (request.form.get("new_category_key") or "component").strip()
    new_part_type_id = request.form.get("new_part_type_id", type=int)
    
    if not component_part_id:
        # If no selected component, try to create one
        if not new_part_number and not new_name:
            flash("Select a component OR enter a new part number/name.", "error")
            return redirect(url_for("inventory_bp.bom_details", bom_id=bom.id))

        # If part_number exists, prevent duplicates
        if new_part_number:
            existing = Part.query.filter_by(part_number=new_part_number).first()
            if existing:
                component_part_id = existing.id
            else:
                # ✅ Determine PartType (priority: explicit -> inferred -> category fallback)
                pt = None

                # 1) Explicit override
                if new_part_type_id:
                    pt = PartType.query.get(new_part_type_id)

                # 2) Infer from part number code (OV-BL001-...)
                if not pt:
                    pt = infer_part_type_from_part_number(new_part_number)

                # 3) Fallback to category_key (stable order)
                if not pt:
                    pt = (PartType.query
                          .filter_by(category_key=new_category_key)
                          .order_by(PartType.id.asc())
                          .first())

                # 4) Last resort: create a category type
                if not pt:
                    pt = PartType(
                        name=new_category_key.replace("_", " ").title(),
                        category_key=new_category_key,
                    )
                    db.session.add(pt)
                    db.session.flush()

                p = Part(
                    part_number=new_part_number,
                    name=new_name or new_part_number,
                    description=new_description,
                    unit=new_unit,
                    part_type_id=pt.id,
                    status="draft",
                )
                db.session.add(p)
                db.session.flush()
                component_part_id = p.id
                flash(f"Draft part created (type: {pt.name}).", "success")
        else:
            # no part number; create using name
            pt = None

            # 1) Explicit override
            if new_part_type_id:
                pt = PartType.query.get(new_part_type_id)

            # 2) Fallback to category_key
            if not pt:
                pt = (PartType.query
                      .filter_by(category_key=new_category_key)
                      .order_by(PartType.id.asc())
                      .first())

            # 3) Last resort: create a category type
            if not pt:
                pt = PartType(
                    name=new_category_key.replace("_", " ").title(),
                    category_key=new_category_key,
                )
                db.session.add(pt)
                db.session.flush()

            p = Part(
                part_number=None,
                name=new_name,
                description=new_description,
                unit=new_unit,
                part_type_id=pt.id,
                status="draft",
            )
            db.session.add(p)
            db.session.flush()
            component_part_id = p.id
            flash(f"Draft part created (type: {pt.name}).", "success")


    qty_per = request.form.get("qty_per", type=float) or 1.0
    line_no = request.form.get("line_no", type=int) or 1
    notes = (request.form.get("notes") or "").strip()
    
    # ✅ Parse + validate make_method
    make_method = (request.form.get("make_method") or "MAKE").strip().upper()
    if make_method not in ("MAKE", "BUY", "OUTSOURCE"):
        make_method = "MAKE"
          
    if not component_part_id:
        flash("Select a component.", "error")
        return redirect(url_for("inventory_bp.bom_details", bom_id=bom.id))

    if qty_per <= 0:
        flash("qty_per must be greater than 0.", "error")
        return redirect(url_for("inventory_bp.bom_details", bom_id=bom.id))

    line = BOMLine(
        bom_id=bom.id,
        component_part_id=component_part_id,
        qty_per=qty_per,
        make_method=make_method,
        line_no=line_no,
        notes=notes or None,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.session.add(line)
    db.session.commit()

    flash("BOM line added.", "success")
    return redirect(url_for("inventory_bp.bom_details", bom_id=bom.id))

@inventory_bp.route("/bom/lines/<int:line_id>/delete", methods=["GET", "POST"])
@login_required
def bom_delete_line(line_id):
    line = BOMLine.query.get_or_404(line_id)
    bom_id = line.bom_id

    db.session.delete(line)
    db.session.commit()

    flash("BOM line deleted.", "success")
    return redirect(url_for("inventory_bp.bom_details", bom_id=bom_id))

@inventory_bp.route("/bom/<int:bom_id>/delete", methods=["POST"])
@login_required
@admin_required
def bom_delete(bom_id):
    bom = BOMHeader.query.get_or_404(bom_id)

    # 🔒 Safety: prevent deleting BOMs already snapshotted into builds
    used_count = BOMItem.query.filter_by(bom_header_id=bom.id).count()
    if used_count > 0:
        flash(
            f"Cannot delete this BOM. It has been used in {used_count} build snapshot(s). "
            f"Deactivate it instead to preserve history.",
            "danger",
        )
        return redirect(url_for("inventory_bp.bom_index"))

    db.session.delete(bom)
    db.session.commit()

    flash("BOM deleted.", "success")
    return redirect(url_for("inventory_bp.bom_index"))

