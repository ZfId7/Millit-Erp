# File path: modules/inventory/routes/routing.py
from flask import render_template, request, redirect, url_for, flash
from database.models import db, PartType, RoutingTemplate, Part, RoutingHeader, RoutingStep
from modules.user.decorators import login_required, admin_required
from modules.inventory.services.parts_service import sync_part_status
from modules.inventory.config.routing_presets import ROUTING_STEP_PRESETS
from modules.inventory import inventory_bp


ALLOWED_MODULE_KEYS = [
    "raw_materials",
    "surface_grinding",
    "bevel_grinding",
    "manufacturing",
    "heat_treat",
]



#New 
@inventory_bp.route("/routing/part/<int:part_id>/create", methods=["GET", "POST"])
@login_required
def routing_create_for_part(part_id):
    part = Part.query.get_or_404(part_id)
    bom_id = request.args.get("bom_id", type=int)
    line_id = request.args.get("line_id", type=int)
    
     # Prevent duplicate active routing (or any routing) for this part
    existing = (
        RoutingHeader.query
        .filter_by(part_id=part.id, is_active=True)
        .order_by(RoutingHeader.rev.desc())
        .first()
    )
    if existing:
        flash("Routing already exists for this part.", "info")
        return redirect(url_for(
            "inventory_bp.routing_detail",
            routing_id=existing.id,
            bom_id=bom_id,
            line_id=line_id,
        ))
        
    if request.method == "POST":
        
        # Create routing header rev A
        rh = RoutingHeader(
            part_id=part.id,
            rev="A",
            is_active=True,
        )
        db.session.add(rh)
        db.session.commit()

        flash("Routing created.", "success")
        return redirect(url_for(
            "inventory_bp.routing_detail",
            routing_id=rh.id,
            bom_id=bom_id,
            line_id=line_id,
        ))

    return render_template(
        "inventory/routing/create_for_part.html",
        part=part,
        bom_id=bom_id,
        line_id=line_id,
    )
    



@inventory_bp.route("/routing/<int:routing_id>")
@login_required
def routing_detail(routing_id):
    routing = RoutingHeader.query.get_or_404(routing_id)
    part = routing.part
    bom_id = request.args.get("bom_id", type=int)
    line_id = request.args.get("line_id", type=int)
    
    steps = (
        RoutingStep.query
        .filter_by(routing_id=routing.id)
        .order_by(RoutingStep.sequence.asc(), RoutingStep.id.asc())
        .all()
    )

    return render_template(
        "inventory/routing/detail.html",
        routing=routing,
        part=part,
        steps=steps,
        allowed_module_keys=ALLOWED_MODULE_KEYS,
        bom_id=bom_id,
        line_id=line_id,
        step_presets=ROUTING_STEP_PRESETS,
    )


@inventory_bp.route("/routing/<int:routing_id>/steps/add", methods=["POST"])
@login_required
def routing_step_add(routing_id):
    routing = RoutingHeader.query.get_or_404(routing_id)
    bom_id = request.args.get("bom_id", type=int)
    line_id = request.args.get("line_id", type=int)
     
    op_key = (request.form.get("op_key") or "").strip().lower()
    preset = ROUTING_STEP_PRESETS.get(op_key)
    
    op_name = (request.form.get("op_name") or "").strip()
    module_key = (request.form.get("module_key") or "").strip()
    sequence = request.form.get("sequence", type=int) or 10
    is_outsourced = True if request.form.get("is_outsourced") == "on" else False
    notes = (request.form.get("notes") or "").strip() or None

	# apply preset defaults if user didn't fill fields
    if preset:
        if not op_name:
            op_name = preset["op_name"]
        if not module_key:
            module_key = preset["module_key"]
        if request.form.get("sequence") in (None, "", "0"):
            sequence = preset["sequence"]
        if request.form.get("is_outsourced") is None:
            is_outsourced = preset.get("is_outsourced", False)

    if not op_key or not op_name or not module_key:
        flash("op_key, op_name, and module are required.", "error")
        return redirect(url_for("inventory_bp.routing_detail", routing_id=routing.id))

    if module_key not in ALLOWED_MODULE_KEYS:
        flash("Invalid module selected.", "error")
        return redirect(url_for("inventory_bp.routing_detail", routing_id=routing.id))

    exists = RoutingStep.query.filter_by(routing_id=routing.id, op_key=op_key).first()
    if exists:
        flash("That op_key already exists for this routing.", "error")
        return redirect(url_for("inventory_bp.routing_detail", routing_id=routing.id))

    db.session.add(RoutingStep(
        routing_id=routing.id,
        op_key=op_key,
        op_name=op_name,
        module_key=module_key,
        sequence=sequence,
        is_outsourced=is_outsourced,
        notes=notes,
    ))
    db.session.commit()

    # After creating/activating routing for a part:
    sync_part_status(routing.part_id)
    db.session.commit()

    flash("Routing step added.", "success")
    return redirect(url_for("inventory_bp.routing_detail", routing_id=routing.id, bom_id=bom_id, line_id=line_id))


@inventory_bp.route("/routing/steps/<int:step_id>/delete", methods=["POST"])
@login_required
def routing_step_delete(step_id):
    step = RoutingStep.query.get_or_404(step_id)
    routing_id = step.routing_id
    bom_id = request.args.get("bom_id", type=int)
    line_id = request.args.get("line_id", type=int)
    
    db.session.delete(step)
    db.session.commit()

    # After creating/activating routing for a part:
    routing = RoutingHeader.query.get_or_404(routing_id)
    sync_part_status(routing.part_id)
    db.session.commit()

    flash("Routing step deleted.", "success")
    return redirect(url_for("inventory_bp.routing_detail", routing_id=routing_id, bom_id=bom_id, line_id=line_id))


#Legacy model
@inventory_bp.route("/routing")
@login_required
@admin_required
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
@login_required
@admin_required
def routing_new():
    part_types = PartType.query.order_by(PartType.name.asc()).all()

    ALLOWED_MODULE_KEYS = {
        #"waterjet",
        "raw_materials",
        "surface_grinding",
        "bevel_grinding",
        "manufacturing",
        "heat_treat",
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
@login_required
@admin_required
def routing_delete(step_id):
    step = RoutingTemplate.query.get_or_404(step_id)
    db.session.delete(step)
    db.session.commit()
    flash("Routing step deleted.", "success")
    return redirect(url_for("inventory_bp.routing_index"))
