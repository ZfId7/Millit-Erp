# File path: modules/jobs_management/routes/build_bom.py

from flask import flash, redirect, render_template, request, url_for
from sqlalchemy import func
from database.models import BOMItem, Build, BuildOperation, Part, db
from modules.jobs_management import jobs_bp
from modules.jobs_management.services.routing import enforce_release_state_for_bom_item, ensure_operations_for_bom_item
from modules.jobs_management.services.build_bom_service import (
    add_bom_item_to_build,
    delete_bom_item_from_build,
)


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
    try:
        build_id_out, msg = add_bom_item_to_build(build_id=build_id, form=request.form)
        db.session.commit()
        flash(msg, "success")
        return redirect(url_for("jobs_bp.build_bom", build_id=build_id_out))
    except ValueError as e:
        db.session.rollback()
        flash(str(e), "error")
        return redirect(url_for("jobs_bp.build_bom", build_id=build_id))
    except Exception:
        db.session.rollback()
        flash("Failed to add BOM item.", "error")
        return redirect(url_for("jobs_bp.build_bom", build_id=build_id))


@jobs_bp.route("/bom/<int:bom_item_id>/delete", methods=["POST"])
def build_bom_delete(bom_item_id):
    try:
        result = delete_bom_item_from_build(bom_item_id=bom_item_id)
        db.session.commit()

        if result["non_queued_count"] > 0:
            flash(
                f"BOM item deleted. {result['deleted_count']} queued ops removed. "
                f"WARNING: {result['non_queued_count']} non-queued ops were left intact.",
                "warning",
            )
        else:
            flash(f"BOM item deleted. {result['deleted_count']} queued ops removed.", "success")

        return redirect(url_for("jobs_bp.build_bom", build_id=result["build_id"]))
    except Exception:
        db.session.rollback()
        flash("Failed to delete BOM item.", "error")
        # fall back safely: route to build_bom requires build_id; re-query is acceptable here
        bom = BOMItem.query.get_or_404(bom_item_id)
        return redirect(url_for("jobs_bp.build_bom", build_id=bom.build_id))



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
