# /Millit_ERP/modules/assembly/routes/__init__.py

import os
from flask import Blueprint, render_template, request, redirect, url_for
from database.models import db, Part, BOMLine, Assembly
from .upload_cad import cad_upload_bp

assembly_bp = Blueprint("assembly_bp", __name__)

@assembly_bp.route("/")
def assembly_index():
    assemblies = Assembly.query.all()
    return render_template("assembly/index.html", assemblies=assemblies)

#@assembly_bp.route("/add", methods=["GET", "POST"])
#def add_part():
    if request.method == "POST":
        name = request.form.get("name")
        part_number = request.form.get("part_number")
        part_type = request.form.get("type")
        unit = request.form.get("unit")
        description = request.form.get("description")

        new_part = Part(
            name=name,
            part_number=part_number,
            type=part_type,
            unit=unit,
            description=description
        )
        db.session.add(new_part)
        db.session.commit()
        return redirect(url_for("assembly_bp.assembly_index"))

    return render_template("assembly/add_part.html")

@assembly_bp.route("/add", methods=["GET", "POST"])
def add_assy():
    if request.method == "POST":
        name = request.form.get("name")
        assembly_number = request.form.get("assembly_number")
        revision = request.form.get("revision")
        lead_time = request.form.get("lead_time")
        description = request.form.get("description")

        new_assy = Assembly(
            name=name,
            assembly_number=assembly_number,
            revision=revision,
            lead_time=lead_time,
            description=description
        )
        db.session.add(new_assy)
        db.session.commit()
        return redirect(url_for("assembly_bp.assembly_index"))

    return render_template("assembly/add_assy.html")

@assembly_bp.route("/add_bom", methods=["GET", "POST"])
def add_bom():
    parts = Part.query.all()

    if request.method == "POST":
        parent_id = request.form.get("parent_part")
        child_ids = request.form.getlist("child_part_id[]")
        quantities = request.form.getlist("quantity[]")

        for child_id, qty in zip(child_ids, quantities):
            if not child_id or not qty:
                continue
            line = BOMLine(
                parent_part_id=parent_id,
                child_part_id=child_id,
                quantity=float(qty)
            )
            db.session.add(line)
        db.session.commit()
        return redirect(url_for("assembly_bp.assembly_index"))

    return render_template("assembly/add_bom.html", parts=parts)


@assembly_bp.route("/view_bom", methods=["GET"])
def view_bom():
    parts = Part.query.all()
    part_id = request.args.get("part_id")
    selected_part = Part.query.get(part_id) if part_id else None

    def build_tree(part):
        lines = BOMLine.query.filter_by(parent_part_id=part.id).all()
        for line in lines:
            child = Part.query.get(line.child_part_id)
            line.child = child
            line.child.children = build_tree(child)
        return lines

    tree = build_tree(selected_part) if selected_part else None
    return render_template("assembly/view_bom.html", parts=parts, selected_part=selected_part, tree=tree)

@assembly_bp.route("/view/<int:part_id>")
def assy_view(part_id):
    part = Part.query.get_or_404(part_id)
    return render_template("assembly/assy_view.html", part=part)

@assembly_bp.route("/cad_viewer/<int:assembly_id>")
def cad_viewer(assembly_id):
    assembly = Assembly.query.get_or_404(assembly_id)
    return render_template("assembly/cad_viewer.html", assembly=assembly)
