# File path: modules/inventory/services/bulk_hardware_service.py

from database.models import db, BulkHardware


def next_bulk_hardware_code():
    """
    Generates next BH-###### code.
    """
    last = (
        BulkHardware.query
        .order_by(BulkHardware.id.desc())
        .first()
    )

    if not last or not last.item_code:
        return "BH-000001"

    try:
        num = int(last.item_code.split("-")[1])
    except Exception:
        return "BH-000001"

    return f"BH-{num + 1:06d}"
