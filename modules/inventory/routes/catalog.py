# File path: modules/inventory/routes/catalog.py
from flask import render_template, request
from modules.user.decorators import login_required
from modules.inventory.services.catalog_service import get_catalog_rows
from modules.inventory import inventory_bp

def _cat_str(v):
    return (v or "").strip().lower()


def _cat_float(v):
    try:
        return float(v or 0)
    except Exception:
        return 0.0

@inventory_bp.route("/catalog")
@login_required
def inventory_catalog():
    search = (request.args.get("q") or "").strip()
    types = request.args.getlist("type") or None
    include_inactive = request.args.get("show") == "all"

    sort = (request.args.get("sort") or "code").strip().lower()
    dir_ = (request.args.get("dir") or "asc").strip().lower()
    if dir_ not in {"asc", "desc"}:
        dir_ = "asc"

    rows = get_catalog_rows(
        item_types=None,  # you can wire this later
        search=search or None,
        include_inactive=include_inactive,
    )

    # Whitelist sort keys (safe)
    allowed = {"code", "name", "class", "uom", "qty"}
    if sort not in allowed:
        sort = "code"

    def sort_key(r):
        if sort == "code":
            return (_cat_str(r.get("code")), _cat_str(r.get("name")))
        if sort == "name":
            return (_cat_str(r.get("name")), _cat_str(r.get("code")))
        if sort == "class":
            # Item Class = item_type (raw/bulk/part)
            return (_cat_str(r.get("item_type")), _cat_str(r.get("code")))
        if sort == "uom":
            return (_cat_str(r.get("uom")), _cat_str(r.get("code")))
        if sort == "qty":
            return (_cat_float(r.get("qty_total")), _cat_str(r.get("code")))
        return (_cat_str(r.get("code")),)

    rows = sorted(rows, key=sort_key, reverse=(dir_ == "desc"))

    
        
    return render_template(
        "inventory/catalog/index.html",
        rows=rows,
        search=search,
        include_inactive=include_inactive,
    )
