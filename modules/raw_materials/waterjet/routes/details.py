# File path: modules/raw_materials/waterjet/routes/details.py
# V1 Refactor Details/Edit
from datetime import datetime

from flask import render_template, request, redirect, url_for, flash

from modules.user.decorators import login_required
from modules.raw_materials.waterjet import raw_mats_waterjet_bp
from database.models import db, BuildOperation, Build, Job, RawStock, WaterjetOperationDetail

@raw_mats_waterjet_bp.route("/<int:op_id>", methods=["GET"])
@login_required
def waterjet_detail(op_id):
    op = (
        BuildOperation.query
        .join(Build, BuildOperation.build_id == Build.id)
        .join(Job, Build.job_id == Job.id)
        .filter(BuildOperation.id == op_id)
        .first_or_404()
    )


    if op.module_key != "raw_materials":
        flash("That operation is not a Raw Materials operation.", "danger")
        return redirect(url_for("raw_mats_waterjet_bp.waterjet_queue"))


    detail = WaterjetOperationDetail.query.filter_by(build_operation_id=op.id).first()
    if not detail:
        detail = WaterjetOperationDetail(build_operation_id=op.id, updated_at=datetime.utcnow())
        db.session.add(detail)
        db.session.commit()


    return render_template("raw_materials/waterjet/detail.html", op=op, detail=detail)

@raw_mats_waterjet_bp.route("/<int:op_id>/edit", methods=["GET"])
@login_required
def waterjet_detail_edit(op_id):
    op = (
        BuildOperation.query
        .join(Build, BuildOperation.build_id == Build.id)
        .join(Job, Build.job_id == Job.id)
        .filter(BuildOperation.id == op_id)
        .first_or_404()
    )


    


    detail = WaterjetOperationDetail.query.filter_by(build_operation_id=op.id).first()
    if not detail:
        detail = WaterjetOperationDetail(build_operation_id=op.id, updated_at=datetime.utcnow())
        db.session.add(detail)
        db.session.commit()


    raw_stock_items = (
        RawStock.query
        .filter(RawStock.is_active == True)
        .order_by(RawStock.material_type.asc(), RawStock.name.asc())
        .all()
    )


    raw_stock_map = {
        r.id: {
            "thickness_in": r.thickness_in,
            "width_in": r.width_in,
            "length_in": r.length_in,
            "material_type": r.material_type,
            "name": r.name,
        }
        for r in raw_stock_items
    }


    return render_template(
        "raw_materials/waterjet/detail_edit.html",
        op=op,
        detail=detail,
        raw_stock_items=raw_stock_items,
        raw_stock_map=raw_stock_map,
    )

@raw_mats_waterjet_bp.route("/<int:op_id>/update", methods=["POST"])
@login_required
def waterjet_detail_update(op_id):
    op = BuildOperation.query.get_or_404(op_id)
    
    

    detail = WaterjetOperationDetail.query.filter_by(build_operation_id=op.id).first()
    if not detail:
        detail = WaterjetOperationDetail(build_operation_id=op.id, updated_at=datetime.utcnow())
        db.session.add(detail)

    def set_str(field_name, attr_name=None):
        if field_name not in request.form:
            return
        val = (request.form.get(field_name) or "").strip()
        setattr(detail, attr_name or field_name, val or None)

    def set_int(field_name, attr_name=None):
        if field_name not in request.form:
            return
        v = (request.form.get(field_name) or "").strip()
        try:
            setattr(detail, attr_name or field_name, int(v) if v != "" else None)
        except ValueError:
            setattr(detail, attr_name or field_name, None)

    def set_float(field_name, attr_name=None):
        if field_name not in request.form:
            return
        v = (request.form.get(field_name) or "").strip()
        try:
            setattr(detail, attr_name or field_name, float(v) if v != "" else None)
        except ValueError:
            setattr(detail, attr_name or field_name, None)

    # IMPORTANT: material_remaining must NOT be inside set_float
    if "material_remaining" in request.form:
        val = request.form.get("material_remaining")
        if val == "yes":
            detail.material_remaining = True
        elif val == "no":
            detail.material_remaining = False
        else:
            detail.material_remaining = None

    if "raw_stock_id" in request.form:
        raw_stock_id = request.form.get("raw_stock_id")
        detail.raw_stock_id = int(raw_stock_id) if raw_stock_id and raw_stock_id.isdigit() else None

    set_float("thickness_override")
    set_float("width_override")
    set_float("length_override")

    set_str("material_source")
    set_str("yield_note")

    set_str("file_name")
    set_str("program_revision")

    set_int("runtime_est_min")
    set_int("runtime_actual_min")

    set_str("blocked_reason")
    set_str("blocked_notes")

    set_str("notes")

    detail.updated_at = datetime.utcnow()
    db.session.commit()

    flash("Waterjet details saved.", "success")
    return redirect(url_for("raw_mats_waterjet_bp.waterjet_detail", op_id=op.id))