# File path: modules/inventory/routes/raw_stock.py
from flask import render_template, request, redirect, url_for, flash
from modules.user.decorators import login_required, admin_required
from modules.inventory import inventory_bp
from database.models import db, RawStock
from modules.inventory.services.stock_ledger_service import get_on_hand_map, post_stock_move


@inventory_bp.route("/raw_stock", methods=["GET"])
@login_required
def raw_stock_index():
    show_inactive = request.args.get("show_inactive") == "1"
    qtext = (request.args.get("q") or "").strip()

    q = RawStock.query
    if not show_inactive:
        q = q.filter(RawStock.is_active.is_(True))

    # Search (only if your template uses name="q")
    if qtext:
        like = f"%{qtext}%"
        q = q.filter(
            (RawStock.name.ilike(like)) |
            (RawStock.grade.ilike(like)) |
            (RawStock.material_type.ilike(like)) |
            (RawStock.form.ilike(like)) |
            (RawStock.vendor.ilike(like)) |
            (RawStock.location.ilike(like))
        )

    sort = (request.args.get("sort") or "code").strip()
    dir_ = (request.args.get("dir") or "desc").strip().lower()

    SORTS = {
        "code": RawStock.id,                 # insert-ish fallback
        "material": RawStock.material_type,
        "name": RawStock.name,
        "grade": RawStock.grade,
        "form": RawStock.form,
    }

    # If you have created_at on RawStock, enable it:
    if hasattr(RawStock, "created_at"):
        SORTS["created_at"] = RawStock.created_at

    col = SORTS.get(sort, RawStock.id)

    if dir_ == "asc":
        q = q.order_by(col.asc(), RawStock.id.asc())
    else:
        q = q.order_by(col.desc(), RawStock.id.desc())

    items = q.all()

    qty_map = get_on_hand_map(
        entity_type="raw_stock",
        entity_ids=[r.id for r in items],
    )

    return render_template(
        "inventory/raw_stock/index.html",
        items=items,
        qty_map=qty_map,
        show_inactive=show_inactive,
    )



@inventory_bp.route("/raw_stock/new", methods=["GET", "POST"])
@login_required
@admin_required
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
            # NOTE: ledger-first means this should probably become 0.0 soon
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


@inventory_bp.route("/raw_stock/<int:item_id>/adjust", methods=["POST"])
@login_required
@admin_required
def raw_stock_adjust(item_id):
    item = RawStock.query.get_or_404(item_id)

    try:
        delta = float((request.form.get("qty_delta") or "0").strip())
    except ValueError:
        flash("Invalid qty delta.", "error")
        return redirect(url_for("inventory_bp.raw_stock_index"))

    if delta == 0:
        flash("Qty delta cannot be 0.", "warning")
        return redirect(url_for("inventory_bp.raw_stock_index"))

    reason = (request.form.get("reason") or "adjust").strip().lower()
    note = (request.form.get("note") or "").strip() or None

    source_type = (request.form.get("source_type") or "").strip() or None
    source_ref = (request.form.get("source_ref") or "").strip() or None

    post_stock_move(
        entity_type="raw_stock",
        entity_id=item.id,
        qty_delta=delta,
        uom=item.uom or "ea",
        reason=reason,
        note=note,
        source_type=source_type,
        source_ref=source_ref,
    )

    db.session.commit()
    flash(f"Adjusted {item.name}: {delta} {item.uom}.", "success")
    return redirect(url_for("inventory_bp.raw_stock_index"))


@inventory_bp.route("/raw_stock/<int:item_id>/details", methods=["GET"])
@login_required
def raw_stock_details(item_id):
    item = RawStock.query.get_or_404(item_id)
    return render_template("inventory/raw_stock/details.html", item=item)
    
    
@inventory_bp.route("/raw_stock/<int:item_id>/details", methods=["POST"])
@login_required
@admin_required
def raw_stock_details_post(item_id):
    item = RawStock.query.get_or_404(item_id)

    name = (request.form.get("name") or "").strip()
    material_type = (request.form.get("material_type") or "").strip().lower()
    grade = (request.form.get("grade") or "").strip() or None
    form = (request.form.get("form") or "").strip().lower()

    thickness_in = (request.form.get("thickness_in") or "").strip()
    width_in = (request.form.get("width_in") or "").strip()
    length_in = (request.form.get("length_in") or "").strip()

    uom = (request.form.get("uom") or "ea").strip().lower()
    vendor = (request.form.get("vendor") or "").strip() or None
    location = (request.form.get("location") or "").strip() or None
    notes = (request.form.get("notes") or "").strip() or None
    is_active = request.form.get("is_active") == "on"

    if not name or not material_type or not form:
        flash("Name, material type, and form are required.", "error")
        return render_template("inventory/raw_stock/details.html", item=item)

    def to_float(val):
        try:
            return float(val) if val != "" else None
        except ValueError:
            return None

    item.name = name
    item.material_type = material_type
    item.grade = grade
    item.form = form
    item.thickness_in = to_float(thickness_in)
    item.width_in = to_float(width_in)
    item.length_in = to_float(length_in)
    item.uom = uom
    item.vendor = vendor
    item.location = location
    item.notes = notes
    item.is_active = is_active

    db.session.commit()
    flash("Raw stock updated.", "success")
    return redirect(url_for("inventory_bp.raw_stock_index", item_id=item.id))

@inventory_bp.route("/raw_stock/<int:item_id>/delete", methods=["POST"])
@login_required
@admin_required
def raw_stock_delete(item_id):
    item = Part.query.get_or_404(item_id)
    db.session.delete(item)
    db.session.commit()
    flash("Item deleted.", "success")
    return redirect(url_for("inventory_bp.raw_stock_index"))
     