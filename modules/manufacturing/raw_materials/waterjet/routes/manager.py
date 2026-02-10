# File path: modules/manufacturing/raw_materials/waterjet/routes/manager.py
# V1 Base build for Waterjet Consumables Manager
# V2 refactor | move inside of modules/raw_materials/waterjet/ | blueprint changed to raw_mats_waterjet_bp

from flask import render_template, request, redirect, url_for, flash
from sqlalchemy import or_

from modules.user.decorators import login_required
from .. import raw_mats_waterjet_bp
from database.models import db, WaterjetConsumable


def _to_float(v):
    v = (v or "").strip()
    try:
        return float(v) if v != "" else None
    except ValueError:
        return None


@raw_mats_waterjet_bp.route("/manager", methods=["GET"])
@login_required
def waterjet_manager_index():
    show_inactive = request.args.get("show_inactive") == "1"
    low_only = request.args.get("low_only") == "1"
    q_txt = (request.args.get("q") or "").strip()

    q = WaterjetConsumable.query

    if not show_inactive:
        q = q.filter(WaterjetConsumable.is_active == True)

    if q_txt:
        like = f"%{q_txt}%"
        q = q.filter(
            or_(
                WaterjetConsumable.name.ilike(like),
                WaterjetConsumable.category.ilike(like),
                WaterjetConsumable.part_number.ilike(like),
                WaterjetConsumable.vendor.ilike(like),
                WaterjetConsumable.location.ilike(like),
            )
        )

    items = q.order_by(WaterjetConsumable.category.asc(), WaterjetConsumable.name.asc()).all()

    if low_only:
        items = [
            i for i in items
            if i.reorder_point is not None and i.qty_on_hand <= i.reorder_point
        ]

    return render_template(
        "raw_materials/waterjet/manager/index.html",
        items=items,
        show_inactive=show_inactive,
        low_only=low_only,
        q=q_txt,
    )


@raw_mats_waterjet_bp.route("/manager/new", methods=["GET", "POST"])
@login_required
def waterjet_manager_new():
    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        category = (request.form.get("category") or "").strip().lower()
        part_number = (request.form.get("part_number") or "").strip() or None
        vendor = (request.form.get("vendor") or "").strip() or None
        uom = (request.form.get("uom") or "ea").strip().lower()

        qty_on_hand = _to_float(request.form.get("qty_on_hand")) or 0.0
        reorder_point = _to_float(request.form.get("reorder_point"))
        reorder_qty = _to_float(request.form.get("reorder_qty"))

        location = (request.form.get("location") or "").strip() or None
        notes = (request.form.get("notes") or "").strip() or None

        if not name or not category:
            flash("Name and category are required.", "error")
            return render_template("raw_materials/waterjet/manager/new.html")

        item = WaterjetConsumable(
            name=name,
            category=category,
            part_number=part_number,
            vendor=vendor,
            qty_on_hand=qty_on_hand,
            uom=uom,
            reorder_point=reorder_point,
            reorder_qty=reorder_qty,
            location=location,
            notes=notes,
            is_active=True,
        )
        db.session.add(item)
        db.session.commit()
        flash("Consumable created.", "success")
        return redirect(url_for("raw_mats_waterjet_bp.waterjet_manager_index"))

    return render_template("raw_materials/waterjet/manager/new.html")


@raw_mats_waterjet_bp.route("/manager/<int:item_id>/edit", methods=["GET", "POST"])
@login_required
def waterjet_manager_edit(item_id):
    item = WaterjetConsumable.query.get_or_404(item_id)

    if request.method == "POST":
        item.name = (request.form.get("name") or "").strip()
        item.category = (request.form.get("category") or "").strip().lower()
        item.part_number = (request.form.get("part_number") or "").strip() or None
        item.vendor = (request.form.get("vendor") or "").strip() or None
        item.uom = (request.form.get("uom") or "ea").strip().lower()

        qoh = _to_float(request.form.get("qty_on_hand"))
        if qoh is not None:
            item.qty_on_hand = qoh

        item.reorder_point = _to_float(request.form.get("reorder_point"))
        item.reorder_qty = _to_float(request.form.get("reorder_qty"))

        item.location = (request.form.get("location") or "").strip() or None
        item.notes = (request.form.get("notes") or "").strip() or None

        item.is_active = True if request.form.get("is_active") == "on" else False

        if not item.name or not item.category:
            flash("Name and category are required.", "error")
            return render_template("raw_materials/waterjet/manager/edit.html", item=item)

        db.session.commit()
        flash("Consumable updated.", "success")
        return redirect(url_for("raw_mats_waterjet_bp.waterjet_manager_index"))

    return render_template("raw_materials/waterjet/manager/edit.html", item=item)
