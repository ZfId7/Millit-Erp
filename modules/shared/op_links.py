# File path: modules/shared/op_links.py

from flask import url_for

def op_queue_url(op):
    """
    Return the correct queue URL for the module that owns this operation.
    """
    key = op.module_key

    if key == "surface_grinding":
        return url_for("surface_grinding_bp.surface_queue")

    if key == "heat_treat":
        return url_for("heat_treat_bp.heat_treat_queue")

    if key == "manufacturing":
        return url_for("mfg_bp.mfg_queue")

    if key == "raw_materials_waterjet":
        return url_for("raw_mats_waterjet_bp.waterjet_queue")

    # Fallback (safe)
    return url_for("jobs_bp.jobs_index")
