# File path: modules/inventory/routes/routing.py
from flask import render_template, request, redirect, url_for, flash
from database.models import db, PartType, RoutingTemplate
from . import inventory_bp


@inventory_bp.route("/routing")
def routing_index():
    part_types = PartType.query.order_by(PartType.name.asc()).all()
    templates = RoutingTemplate.query.order_by(
        RoutingTemplate.part_type_id.asc(),
        RoutingTemplate.sequence.asc()
    ).all()

    # group for display
    grouped = {}
    for pt in part_types:
        grouped[pt.id] = {"type": pt, "steps": []}

    for t in templates:
        if t.part_type_id not in grouped:
            grouped[t.part_type_id] = {"type": t.part_type, "steps": []}
        grouped[t.part_type_id]["steps"].append(t)

    return render_template("inventory/routing/index.html", grouped=grouped, part_types=part_types)


@inventory_bp.route("/routing/new", methods=["GET", "POST"])
def routing_new():
    part_types = PartType.query.order_by(PartType.name.asc()).all()

    ALLOWED_MODULE_KEYS = {
        #"waterjet",
        "raw_materials",
        "surface_grinding",
        "bevel_grinding",
        "manufacturing",
        # "heat_treat",
        # "assembly",
    }

    if request.method == "POST":
        part_type_id = request.form.get("part_type_id") or None
        op_key = (request.form.get("op_key") or "").strip().lower()
        op_name = (request.form.get("op_name") or "").strip()
        module_key = (request.form.get("module_key") or "").strip().lower()
        sequence_raw = (request.form.get("sequence") or "").strip()
        is_outsourced = True if request.form.get("is_outsourced") == "on" else False

        if not part_type_id or not op_key or not op_name or not module_key:
            flash("Part type, op key, op name, and module key are required.", "error")
            return render_template(
                "inventory/routing/new.html",
                part_types=part_types,
                allowed_module_keys=sorted(ALLOWED_MODULE_KEYS),
            )

        # ✅ module lockout (kills raw_materials forever)
        if module_key not in ALLOWED_MODULE_KEYS:
            flash(
                f"Invalid module key: '{module_key}'. Must be one of: {', '.join(sorted(ALLOWED_MODULE_KEYS))}.",
                "error",
            )
            return render_template(
                "inventory/routing/new.html",
                part_types=part_types,
                allowed_module_keys=sorted(ALLOWED_MODULE_KEYS),
            )

        try:
            sequence = int(sequence_raw) if sequence_raw else 10
        except ValueError:
            sequence = 10

        # prevent duplicate op_key per part type
        exists = RoutingTemplate.query.filter_by(
            part_type_id=int(part_type_id),
            op_key=op_key
        ).first()
        if exists:
            flash("That op_key already exists for this part type.", "error")
            return render_template(
                "inventory/routing/new.html",
                part_types=part_types,
                allowed_module_keys=sorted(ALLOWED_MODULE_KEYS),
            )

        db.session.add(RoutingTemplate(
            part_type_id=int(part_type_id),
            op_key=op_key,
            op_name=op_name,
            module_key=module_key,
            sequence=sequence,
            is_outsourced=is_outsourced,
        ))
        db.session.commit()
        flash("Routing step created.", "success")
        return redirect(url_for("inventory_bp.routing_index"))

    return render_template(
        "inventory/routing/new.html",
        part_types=part_types,
        allowed_module_keys=sorted(ALLOWED_MODULE_KEYS),
    )



@inventory_bp.route("/routing/<int:step_id>/delete", methods=["POST"])
def routing_delete(step_id):
    step = RoutingTemplate.query.get_or_404(step_id)
    db.session.delete(step)
    db.session.commit()
    flash("Routing step deleted.", "success")
    return redirect(url_for("inventory_bp.routing_index"))
