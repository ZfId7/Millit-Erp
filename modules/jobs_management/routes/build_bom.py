# File path: modules/jobs_management/routes/build_bom.py

from flask import flash, redirect, render_template, request, url_for
from sqlalchemy import func
from database.models import BOMItem, Build, Part, db
from jobs_management import jobs_bp
from modules.jobs_management.services.routing import enforce_release_state_for_bom_item, ensure_operations_for_bom_item

@jobs_bp.route("/build/<int:build_id>/bom")
def build_bom(build_id):
    build = Build.query.get_or_404(build_id)
    # Parts list for dropdown selection
    parts = Part.query.order_by(Part.part_number.asc()).all()
    # BOM items sorted by line number
    bom_items = BOMItem.query.filter_by(build_id=build.id).order_by(BOMItem.line_no.asc()).all()

    return render_template(
        "jobs_management/build_bom.html",
        build=build,
        job=build.job,
        parts=parts,
        bom_items=bom_items
    )

@jobs_bp.route("/build/<int:build_id>/bom/add", methods=["POST"])
def build_bom_add(build_id):
    build = Build.query.get_or_404(build_id)

    part_id_raw = (request.form.get("part_id") or "").strip()
    name = (request.form.get("name") or "").strip()
    part_number = (request.form.get("part_number") or "").strip()
    description = (request.form.get("description") or "").strip()
    unit = (request.form.get("unit") or "ea").strip()
    qty_raw = (request.form.get("qty") or "1").strip()

    # Parse qty as float (supports things like 0.5 for material lengths later)
    try:
        qty_per = float(qty_raw)
    except ValueError:
        qty_per = 1.0
    if qty_per <= 0:
        qty_per = 1.0

    assemblies = float(getattr(build, "qty_ordered", 0) or 0)
    qty_planned = qty_per * assemblies  # ✅ snapshot truth

    # Next line number
    last_line = db.session.query(func.max(BOMItem.line_no)).filter_by(build_id=build.id).scalar() or 0
    next_line = last_line + 1

    # If a catalog part was selected, snapshot its fields
    selected_part = None
    if part_id_raw:
        try:
            selected_part = Part.query.get(int(part_id_raw))
        except ValueError:
            selected_part = None

        if not selected_part:
            flash("Selected part not found.", "error")
            return redirect(url_for("jobs_bp.build_bom", build_id=build.id))

        bom = BOMItem(
            build=build,
            part=selected_part,
            line_no=next_line,
            part_number=selected_part.part_number,
            name=selected_part.name,
            description=selected_part.description,
            # Legacy qty kept for compatibility during refactor
            qty=qty_per,
            qty_per=qty_per,
            qty_planned=qty_planned,
            unit=selected_part.unit or unit,
            source="manual",
        )
        db.session.add(bom)
        db.session.flush()
        ensure_operations_for_bom_item(bom)  # will set op.qty_planned = bom.qty_planned
        db.session.commit()

        flash("BOM item added from catalog part.", "success")
        return redirect(url_for("jobs_bp.build_bom", build_id=build.id))

    # Free-text BOM line requires at least a name
    if not name:
        flash("Enter a name or select a catalog part.", "error")
        return redirect(url_for("jobs_bp.build_bom", build_id=build.id))

    bom = BOMItem(
        build=build,
        line_no=next_line,
        part_number=part_number or None,
        name=name,
        description=description or None,
        qty=qty_per,              # legacy mirror
        qty_per=qty_per,
        qty_planned=qty_planned,
        unit=unit or "ea",
        source="manual",
    )
    db.session.add(bom)
    db.session.flush()
    ensure_operations_for_bom_item(bom)      # ✅ generate ops too (you were missing this)
    db.session.commit()

    flash("BOM item added.", "success")
    return redirect(url_for("jobs_bp.build_bom", build_id=build.id))

@jobs_bp.route("/bom/<int:bom_item_id>/delete", methods=["POST"])
def build_bom_delete(bom_item_id):
    bom = BOMItem.query.get_or_404(bom_item_id)
    build_id = bom.build_id

    db.session.delete(bom)
    db.session.commit()

    flash("BOM item deleted.", "success")
    return redirect(url_for("jobs_bp.build_bom", build_id=build_id))

@jobs_bp.route("/build/<int:build_id>/ops/regenerate", methods=["POST"])
def build_ops_regenerate(build_id):
    build = Build.query.get_or_404(build_id)
    job = build.job

    if job.is_archived:
        flash("This job is archived. Regenerate Ops is disabled.", "danger")
        return redirect(url_for("jobs_bp.job_detail", job_id=job.id))  # ✅ job.id

    # Re-run routing for every BOM line on this build
    for bom in build.bom_items:
        ensure_operations_for_bom_item(bom)

        # ✅ enforce release for THIS bom line
        enforce_release_state_for_bom_item(build_id=build.id, bom_item_id=bom.id)

    db.session.commit()
    flash("Operations regenerated from BOM + routing.", "success")
    return redirect(url_for("jobs_bp.build_bom", build_id=build.id))
