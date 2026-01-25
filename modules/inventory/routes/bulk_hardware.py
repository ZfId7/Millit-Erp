# File path: modules/inventory/routes/bulk_hardware.py
from flask import render_template, request, redirect, url_for, flash

from database.models import db, BulkHardware
from modules.user.decorators import login_required, admin_required
from modules.inventory.services.bulk_hardware_service import next_bulk_hardware_code
from modules.inventory.services.bulk_convert_service import (
    convert_bulk_to_part,
    get_bulk_convert_defaults,
    BulkConvertError,
)
from modules.inventory.services.stock_ledger_service import post_stock_move, get_on_hand_map

from modules.inventory import inventory_bp



@inventory_bp.route("/bulk")
@login_required
def bulk_index():
    show_inactive = request.args.get("show_inactive") == "1"
    qtext = (request.args.get("q") or "").strip()

    q = BulkHardware.query
    if not show_inactive:
        q = q.filter(BulkHardware.is_active.is_(True))

    # Search (only if your template uses name="q")
    if qtext:
        like = f"%{qtext}%"
        q = q.filter(
            (BulkHardware.name.ilike(like)) |
            (BulkHardware.grade.ilike(like)) |
            (BulkHardware.material_type.ilike(like)) |
            (BulkHardware.form.ilike(like)) |
            (BulkHardware.vendor.ilike(like)) |
            (BulkHardware.location.ilike(like))
        )

    sort = (request.args.get("sort") or "code").strip()
    dir_ = (request.args.get("dir") or "desc").strip().lower()

    SORTS = {
        "code": BulkHardware.id,                 # insert-ish fallback
        "name": BulkHardware.name,
    }

    # If you have created_at on BulkHardware, enable it:
    if hasattr(BulkHardware, "created_at"):
        SORTS["created_at"] = BulkHardware.created_at

    col = SORTS.get(sort, BulkHardware.id)

    if dir_ == "asc":
        q = q.order_by(col.asc(), BulkHardware.id.asc())
    else:
        q = q.order_by(col.desc(), BulkHardware.id.desc())

    items = q.all()
    
    qty_map = get_on_hand_map("bulk_hardware", [b.id for b in items])
    return render_template("inventory/bulk/index.html", items=items, qty_map=qty_map)

@inventory_bp.route("/bulk/new", methods=["GET", "POST"])
@login_required
@admin_required
def bulk_new():
    if request.method == "GET":
        return render_template(
            "inventory/bulk/form.html",
            item=None,
            next_code=next_bulk_hardware_code(),
        )

    item = BulkHardware(
        item_code=next_bulk_hardware_code(),
        name=request.form.get("name"),
        description=request.form.get("description"),
        vendor=request.form.get("vendor"),
        vendor_sku=request.form.get("vendor_sku"),
        uom=request.form.get("uom") or "ea",
        qty_on_hand=float(request.form.get("qty_on_hand") or 0),
        is_active=True,
    )

    db.session.add(item)
    db.session.commit()

    flash("Bulk hardware created.", "success")
    return redirect(url_for("inventory_bp.bulk_index"))


@inventory_bp.route("/bulk/<int:item_id>/edit", methods=["GET", "POST"])
@login_required
@admin_required
def bulk_edit(item_id):
    item = BulkHardware.query.get_or_404(item_id)

    if request.method == "GET":
        return render_template(
            "inventory/bulk/form.html",
            item=item,
            next_code=None,
        )

    item.name = request.form.get("name")
    item.description = request.form.get("description")
    item.vendor = request.form.get("vendor")
    item.vendor_sku = request.form.get("vendor_sku")
    item.uom = request.form.get("uom") or item.uom
    item.is_active = request.form.get("is_active") == "on"

    db.session.commit()

    flash("Bulk hardware updated.", "success")
    return redirect(url_for("inventory_bp.bulk_index"))


@inventory_bp.route("/bulk/<int:item_id>/adjust", methods=["POST"])
@login_required
@admin_required
def bulk_adjust_qty(item_id):
    item = BulkHardware.query.get_or_404(item_id)

    delta = float(request.form.get("delta") or 0)
    
    post_stock_move(
        entity_type="bulk_hardware",
        entity_id=item.id,
        qty_delta=delta,
        uom=item.uom,
        reason="adjust",
        note="Manual bulk qty adjustment",
    )

    db.session.commit()

    flash(f"Quantity adjusted by {delta}.", "success")
    return redirect(url_for("inventory_bp.bulk_index"))

@inventory_bp.route("/bulk/<int:item_id>/convert", methods=["GET", "POST"])
@login_required
@admin_required
def bulk_convert_to_part(item_id):
    item = BulkHardware.query.get_or_404(item_id)

    if request.method == "GET":
        defaults = get_bulk_convert_defaults(item)
        return render_template(
            "inventory/bulk/convert.html",
            item=item,
            defaults=defaults,
        )

    # POST
    part_number = (request.form.get("part_number") or "").strip()
    name = (request.form.get("name") or "").strip()
    description = (request.form.get("description") or "").strip() or None
    unit = (request.form.get("unit") or item.uom or "ea").strip().lower()
    stage_key = (request.form.get("stage_key") or "mfg_wip").strip()
    produced_qty = float(request.form.get("produced_qty") or 0)
    consumed_qty = float(request.form.get("consumed_qty") or 0)
    source_type = (request.form.get("source_type") or "").strip() or None
    source_ref = (request.form.get("source_ref") or "").strip() or None
    note = (request.form.get("note") or "").strip() or None
    set_active = request.form.get("set_active") == "on"

    try:
        res = convert_bulk_to_part(
            bulk_id=item.id,
            part_number=part_number,
            name=name,
            description=description,
            unit=unit,
            stage_key=stage_key,
            produced_qty=produced_qty,
            consumed_qty=consumed_qty,
            set_active=set_active,
            source_type=source_type,
            source_ref=source_ref,
            note=note,
        )

        flash(
            f"Converted {consumed_qty} {item.uom} of {item.item_code} into "
            f"{produced_qty} {unit} of new part {res.part.part_number}.",
            "success",
        )
        return redirect(url_for("inventory_bp.parts_edit", part_id=res.part.id))

    except BulkConvertError as e:
        flash(str(e), "danger")
        defaults = get_bulk_convert_defaults(item)
        return render_template(
            "inventory/bulk/convert.html",
            item=item,
            defaults=defaults,
            form=request.form,
            
        )
