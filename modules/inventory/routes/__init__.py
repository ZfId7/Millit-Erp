# File path: modules/inventory/routes/__init__.py
# -V1 Inventory index/parts catalog
# -V2 Raw Stock index/new

from flask import Blueprint, render_template, request, redirect, url_for, flash
from database.models import db, RawStock

inventory_bp = Blueprint("inventory_bp", __name__)

@inventory_bp.route("/")
def inventory_index():
    print("📦 Inventory route HIT")
    return render_template("inventory/index.html")

# IMPORTANT: import route modules AFTER blueprint creation
from . import parts  # noqa: E402
from . import routing #noqa: E402

@inventory_bp.route("/raw_stock", methods=["GET"])
def raw_stock_index():
    show_inactive = request.args.get("show_inactive") == "1"

    q = RawStock.query
    if not show_inactive:
        q = q.filter(RawStock.is_active == True)

    items = q.order_by(RawStock.material_type.asc(), RawStock.name.asc()).all()

    return render_template(
        "inventory/raw_stock/index.html",
        items=items,
        show_inactive=show_inactive,
    )


@inventory_bp.route("/raw_stock/new", methods=["GET", "POST"])
def raw_stock_new():
    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        material_type = (request.form.get("material_type") or "").strip().lower()
        grade = (request.form.get("grade") or "").strip()
        form = (request.form.get("form") or "").strip().lower()

        thickness_in = (request.form.get("thickness_in") or "").strip()
        width_in = (request.form.get("width_in") or "").strip()
        length_in = (request.form.get("length_in") or "").strip()

        qty_on_hand = (request.form.get("qty_on_hand") or "0").strip()
        uom = (request.form.get("uom") or "ea").strip().lower()

        vendor = (request.form.get("vendor") or "").strip()
        location = (request.form.get("location") or "").strip()
        notes = (request.form.get("notes") or "").strip()

        if not name or not material_type or not form:
            flash("Name, material type, and form are required.", "error")
            return render_template("inventory/raw_stock/new.html")

        def to_float(val):
            try:
                return float(val) if val != "" else None
            except ValueError:
                return None

        item = RawStock(
            name=name,
            material_type=material_type,
            grade=grade or None,
            form=form,
            thickness_in=to_float(thickness_in),
            width_in=to_float(width_in),
            length_in=to_float(length_in),
            qty_on_hand=float(qty_on_hand) if qty_on_hand else 0.0,
            uom=uom,
            vendor=vendor or None,
            location=location or None,
            notes=notes or None,
            is_active=True,
        )

        db.session.add(item)
        db.session.commit()
        flash("Raw stock item created.", "success")
        return redirect(url_for("inventory_bp.raw_stock_index"))

    return render_template("inventory/raw_stock/new.html")

