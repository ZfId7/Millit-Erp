# File path: modules/jobs_management/routes/__init__.py
# V3 Add op_progress_add
# V4 Add Parts_inventory hook
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash
from sqlalchemy import func

from database.models import db, Customer, Job, Build, JobWorkLog, BOMItem, Part, BuildOperation, BuildOperationProgress
from modules.jobs_management.services.routing import ensure_operations_for_bom_item
from modules.inventory.services.parts_inventory import apply_part_inventory_delta

from functools import wraps
from flask import abort
from modules.user.decorators import login_required, admin_required

jobs_bp = Blueprint("jobs_bp", __name__)


def _next_job_number():
    # JOB-YYYY-000001 style using max(id). Good enough for now.
    year = datetime.utcnow().year
    last_id = db.session.query(func.max(Job.id)).scalar() or 0
    seq = last_id + 1
    return f"JOB-{year}-{seq:06d}"

@jobs_bp.route("/")
def jobs_index():
    jobs = Job.query.filter(Job.is_archived == False).order_by(Job.id.desc()).all()
    return render_template(
        "jobs_management/index.html", 
        jobs=jobs,
        )

@jobs_bp.route("/new", methods=["GET", "POST"])
def jobs_new():
    customers = Customer.query.order_by(Customer.name.asc()).all()

    # Defaults for GET + error re-render
    form = {
        "customer_id": "",
        "new_customer_name": "",
        "title": "",
        "due_date": "",
        "priority": "normal",
        "notes": "",
        "builds": [
            {"name": "", "qty": "1"},
            {"name": "", "qty": "1"},
            {"name": "", "qty": "1"},
        ],
    }

    if request.method == "POST":
        existing_customer_id = (request.form.get("customer_id") or "").strip()
        new_customer_name = (request.form.get("new_customer_name") or "").strip()

        title = (request.form.get("title") or "").strip()
        due_date_raw = (request.form.get("due_date") or "").strip()
        priority = (request.form.get("priority") or "normal").strip()
        notes = (request.form.get("notes") or "").strip()

        build_names = request.form.getlist("build_name")
        build_qtys = request.form.getlist("build_qty")

        # Refill form dict for re-render
        form.update({
            "customer_id": existing_customer_id,
            "new_customer_name": new_customer_name,
            "title": title,
            "due_date": due_date_raw,
            "priority": priority or "normal",
            "notes": notes,
            "builds": [
                {"name": (n or "").strip(), "qty": (q or "1").strip()}
                for n, q in zip(build_names, build_qtys)
            ] or form["builds"],
        })

        if not title:
            flash("Job title is required.", "error")
            return render_template("jobs_management/new.html", customers=customers, form=form)

        # Don’t allow both
        if existing_customer_id and new_customer_name:
            flash("Choose an existing customer OR enter a new customer name (not both).", "error")
            return render_template("jobs_management/new.html", customers=customers, form=form)

        # Resolve customer
        customer = None
        if existing_customer_id:
            customer = Customer.query.get(int(existing_customer_id))
            if not customer:
                flash("Selected customer not found.", "error")
                return render_template("jobs_management/new.html", customers=customers, form=form)
        elif new_customer_name:
            customer = Customer(name=new_customer_name)
            db.session.add(customer)
        else:
            flash("Select an existing customer or enter a new customer name.", "error")
            return render_template("jobs_management/new.html", customers=customers, form=form)

        # Parse date
        due_date = None
        if due_date_raw:
            try:
                due_date = datetime.strptime(due_date_raw, "%Y-%m-%d").date()
            except ValueError:
                flash("Invalid due date format.", "error")
                return render_template("jobs_management/new.html", customers=customers, form=form)

        # Must have at least one build name
        cleaned_builds = []
        for name, qty in zip(build_names, build_qtys):
            name = (name or "").strip()
            if not name:
                continue
            try:
                q = int(qty) if qty else 1
            except ValueError:
                q = 1
            cleaned_builds.append((name, max(q, 1)))

        if not cleaned_builds:
            flash("Add at least one build (name required).", "error")
            return render_template("jobs_management/new.html", customers=customers, form=form)

        job = Job(
            customer=customer,
            job_number=_next_job_number(),
            title=title,
            status="queue",
            priority=priority,
            due_date=due_date,
            notes=notes or None,
        )
        db.session.add(job)
        db.session.flush()

        for bname, bqty in cleaned_builds:
            db.session.add(Build(job=job, name=bname, qty_ordered=bqty))

        db.session.commit()
        flash("Job created.", "success")
        return redirect(url_for("jobs_bp.job_detail", job_id=job.id))

    return render_template("jobs_management/new.html", customers=customers, form=form)

@jobs_bp.route("/archived", methods=["GET"])
@admin_required
def jobs_archived_index():
    jobs = Job.query.filter(Job.is_archived == True).order_by(Job.archived_at.desc().nullslast(), Job.id.desc()).all()
    return render_template("jobs_management/archived_index.html", jobs=jobs)


@jobs_bp.route("/<int:job_id>/archive", methods=["GET"])
@admin_required
def job_archive_confirm(job_id):
    job = Job.query.get_or_404(job_id)

    in_progress_count = (
        db.session.query(BuildOperation)
        .join(Build, BuildOperation.build_id == Build.id)
        .filter(Build.job_id == job_id, BuildOperation.status == "in_progress")
        .count()
    )

    completed_count = (
        db.session.query(BuildOperation)
        .join(Build, BuildOperation.build_id == Build.id)
        .filter(Build.job_id == job_id, BuildOperation.status == "completed")
        .count()
    )

    return render_template(
        "jobs_management/archive_confirm.html",
        job=job,
        in_progress_count=in_progress_count,
        completed_count=completed_count,
    )

@jobs_bp.route("/<int:job_id>/archive", methods=["POST"])
@admin_required
def job_archive_post(job_id):
    job = Job.query.get_or_404(job_id)

    if request.form.get("confirm_archive") != "yes":
        flash("Archive not confirmed.", "warning")
        return redirect(url_for("jobs_bp.job_archive_confirm", job_id=job_id))

    if request.form.get("typed") != "ARCHIVE":
        flash("Type ARCHIVE to confirm.", "warning")
        return redirect(url_for("jobs_bp.job_archive_confirm", job_id=job_id))

    in_progress_ops_q = (
        BuildOperation.query
        .join(Build, BuildOperation.build_id == Build.id)
        .filter(Build.job_id == job_id, BuildOperation.status == "in_progress")
    )
    in_progress_count = in_progress_ops_q.count()

    # Option 2: allow, but require explicit override if in-progress exists
    force_cancel = request.form.get("force_cancel_in_progress") == "yes"
    if in_progress_count > 0 and not force_cancel:
        flash(
            f"This job has {in_progress_count} operation(s) in progress. "
            "Check the override box to cancel them and archive the job.",
            "danger",
        )
        return redirect(url_for("jobs_bp.job_archive_confirm", job_id=job_id))

    # Cancel any in-progress ops so queues can't pull them anymore
    if in_progress_count > 0:
        now = datetime.utcnow()
        for op in in_progress_ops_q.all():
            op.status = "cancelled"
            # Optional columns:
            if hasattr(op, "cancelled_at"):
                op.cancelled_at = now
            if hasattr(op, "cancelled_reason"):
                op.cancelled_reason = "Job archived by admin; in-progress op cancelled."

    # Archive the job
    job.is_archived = True
    job.archived_at = datetime.utcnow()

    # If you store session user id, set it (adjust to match your session keys)
    # job.archived_by = session.get("user_id")

    db.session.commit()

    flash("Job archived. In-progress operations were cancelled.", "success")
    return redirect(url_for("jobs_bp.jobs_index"))
    
@jobs_bp.route("/<int:job_id>/unarchive", methods=["GET"])
@admin_required
def job_unarchive_confirm(job_id):
    job = Job.query.get_or_404(job_id)

    if not job.is_archived:
        flash("Job is not archived.", "warning")
        return redirect(url_for("jobs_bp.jobs_index"))

    return render_template(
        "jobs_management/unarchive_confirm.html",
        job=job,
    )


@jobs_bp.route("/<int:job_id>/unarchive", methods=["POST"])
@admin_required
def job_unarchive_post(job_id):
    job = Job.query.get_or_404(job_id)

    if not job.is_archived:
        flash("Job is not archived.", "warning")
        return redirect(url_for("jobs_bp.jobs_index"))

    if request.form.get("confirm_unarchive") != "yes":
        flash("Unarchive not confirmed.", "warning")
        return redirect(url_for("jobs_bp.job_unarchive_confirm", job_id=job_id))

    if request.form.get("typed") != "UNARCHIVE":
        flash("Type UNARCHIVE to confirm.", "warning")
        return redirect(url_for("jobs_bp.job_unarchive_confirm", job_id=job_id))

    job.is_archived = False
    job.archived_at = None
    job.archived_by = None

    db.session.commit()
    flash("Job unarchived.", "success")
    return redirect(url_for("jobs_bp.jobs_index"))

@jobs_bp.route("/<int:job_id>")
def job_detail(job_id):
    job = Job.query.get_or_404(job_id)

    ops = (
        BuildOperation.query
        .join(Build, BuildOperation.build_id == Build.id)
        .filter(Build.job_id == job.id)
        .order_by(BuildOperation.build_id.asc(), BuildOperation.sequence.asc())
        .all()
    )

    ops_by_build = {}
    for op in ops:
        ops_by_build.setdefault(op.build_id, []).append(op)

    return render_template("jobs_management/detail.html", job=job, ops_by_build=ops_by_build)


@jobs_bp.route("/build/<int:build_id>/status", methods=["POST"])
def build_update_status(build_id):
    build = Build.query.get_or_404(build_id)

    new_status = (request.form.get("status") or "").strip()
    allowed = {"queue", "in_progress", "complete"}

    if new_status not in allowed:
        flash("Invalid status.", "error")
        return redirect(url_for("jobs_bp.job_detail", job_id=build.job_id))

    build.status = new_status
    # Optional: derive job status from builds
    job = build.job
    statuses = {b.status for b in job.builds}

    if statuses == {"complete"}:
            job.status = "complete"
    elif "in_progress" in statuses:
            job.status = "in_progress"
    else:
            job.status = "queue"
    db.session.commit()

    flash(f'Updated build "{build.name}" → {new_status.replace("_"," ")}.', "success")
    return redirect(url_for("jobs_bp.job_detail", job_id=build.job_id))

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
    build = Build.query.get_or_404(build_id)

    part_id_raw = (request.form.get("part_id") or "").strip()
    name = (request.form.get("name") or "").strip()
    part_number = (request.form.get("part_number") or "").strip()
    description = (request.form.get("description") or "").strip()
    unit = (request.form.get("unit") or "ea").strip()
    qty_raw = (request.form.get("qty") or "1").strip()

    # Parse qty as float (supports things like 0.5 for material lengths later)
    try:
        qty = float(qty_raw)
    except ValueError:
        qty = 1.0
    if qty <= 0:
        qty = 1.0

    # Next line number
    last_line = db.session.query(func.max(BOMItem.line_no)).filter_by(build_id=build.id).scalar() or 0
    next_line = last_line + 1

    # If a catalog part was selected, snapshot its fields
    selected_part = None
    if part_id_raw:
        try:
            selected_part = Part.query.get(int(part_id_raw))
        except ValueError:
            selected_part = None

        if not selected_part:
            flash("Selected part not found.", "error")
            return redirect(url_for("jobs_bp.build_bom", build_id=build.id))

        bom = BOMItem(
            build=build,
            part=selected_part,
            line_no=next_line,
            part_number=selected_part.part_number,
            name=selected_part.name,
            description=selected_part.description,
            qty=qty,
            unit=selected_part.unit or unit,
            source="manual",
        )
        db.session.add(bom)
        db.session.flush()
        ensure_operations_for_bom_item(bom)  # safe no-op until routing exists
        db.session.commit()

        flash("BOM item added from catalog part.", "success")
        return redirect(url_for("jobs_bp.build_bom", build_id=build.id))

    # Free-text BOM line requires at least a name
    if not name:
        flash("Enter a name or select a catalog part.", "error")
        return redirect(url_for("jobs_bp.build_bom", build_id=build.id))

    bom = BOMItem(
        build=build,
        line_no=next_line,
        part_number=part_number or None,
        name=name,
        description=description or None,
        qty=qty,
        unit=unit or "ea",
        source="manual",
    )
    db.session.add(bom)
    db.session.commit()

    flash("BOM item added.", "success")
    return redirect(url_for("jobs_bp.build_bom", build_id=build.id))


@jobs_bp.route("/bom/<int:bom_item_id>/delete", methods=["POST"])
def build_bom_delete(bom_item_id):
    bom = BOMItem.query.get_or_404(bom_item_id)
    build_id = bom.build_id

    db.session.delete(bom)
    db.session.commit()

    flash("BOM item deleted.", "success")
    return redirect(url_for("jobs_bp.build_bom", build_id=build_id))



@jobs_bp.route("/build/<int:build_id>/ops/regenerate", methods=["POST"])
def build_ops_regenerate(build_id):
    build = Build.query.get_or_404(build_id)
    job = build.job

    if job.is_archived:
        flash("This job is archived. Regenerate Ops is disabled.", "danger")
        return redirect(url_for("jobs_bp.job_detail", job_id=job_id))

    # Re-run routing for every BOM line on this build
    for bom in build.bom_items:
        ensure_operations_for_bom_item(bom)

    db.session.commit()
    flash("Operations regenerated from BOM + routing.", "success")
    return redirect(url_for("jobs_bp.build_bom", build_id=build.id))

@jobs_bp.route("/<int:job_id>/delete", methods=["GET"])
@admin_required
def job_delete_confirm(job_id):
    job = Job.query.get_or_404(job_id)

    completed_count = (
        db.session.query(BuildOperation)
        .join(Build, BuildOperation.build_id == Build.id)
        .filter(Build.job_id == job_id, BuildOperation.status == "completed")
        .count()
    )

    return render_template(
        "jobs_management/delete_confirm.html",
        job=job,
        completed_count=completed_count
    )
    
@jobs_bp.route("/<int:job_id>/delete", methods=["POST"])
@admin_required
def delete_job(job_id):
    job = Job.query.get_or_404(job_id)

    # Hard confirmation guard
    if request.form.get("confirm_delete") != "yes":
        flash("Deletion not confirmed.", "warning")
        return redirect(url_for("jobs_bp.job_detail", job_id=job_id))

    # Optional: enforce typing DELETE (recommended)
    if request.form.get("typed") != "DELETE":
        flash("Type DELETE to confirm job deletion.", "warning")
        return redirect(url_for("jobs_bp.job_detail", job_id=job_id))

    # Completed ops behavior: warn + require override checkbox
    completed_count = (
        db.session.query(BuildOperation)
        .join(Build, BuildOperation.build_id == Build.id)
        .filter(Build.job_id == job_id, BuildOperation.status == "completed")
        .count()
    )

    if completed_count > 0 and request.form.get("allow_completed") != "yes":
        flash(
            f"Job has {completed_count} completed operation(s). "
            "Check the override box to delete anyway.",
            "danger",
        )
        return redirect(url_for("jobs_bp.job_detail", job_id=job_id))

    # Delete root; cascades should delete children
    db.session.delete(job)
    db.session.commit()

    flash("Job deleted.", "success")
    return redirect(url_for("jobs_bp.jobs_index"))

@jobs_bp.route("/ops/<int:op_id>/progress/add", methods=["POST"])
@login_required
def op_progress_add(op_id):
    op = BuildOperation.query.get_or_404(op_id)

    # Ensure we can redirect back to the correct job page
    job_id = request.form.get("job_id", type=int)
    if not job_id and op.build:
        job_id = op.build.job_id

    qty_done_delta = request.form.get("qty_done_delta", type=float) or 0.0
    qty_scrap_delta = request.form.get("qty_scrap_delta", type=float) or 0.0
    note = (request.form.get("note") or "").strip()

    if qty_done_delta < 0 or qty_scrap_delta < 0:
        flash("Progress values cannot be negative.", "error")
        return redirect(url_for("jobs_bp.job_detail", job_id=job_id))

    if qty_done_delta == 0 and qty_scrap_delta == 0 and not note:
        flash("Nothing to add. Enter qty and/or a note.", "error")
        return redirect(url_for("jobs_bp.job_detail", job_id=job_id, _anchor=f"op-{op.id}"))

    entry = BuildOperationProgress(
        build_operation_id=op.id,
        qty_done_delta=qty_done_delta,
        qty_scrap_delta=qty_scrap_delta,
        note=note or None,
    )
    db.session.add(entry)

    # Update operation totals
    op.qty_done = (op.qty_done or 0.0) + qty_done_delta
    op.qty_scrap = (op.qty_scrap or 0.0) + qty_scrap_delta

    # ---- Inventory posting (ops-driven) ----
    # Only for raw materials ops that produce "blank" inventory
    RAW_MATS_BLANK_OP_KEYS = {
        "waterjet_cut",
        "laser_cut",
        "bandsaw_cut",
        "tablesaw_cut",
        "edm_cut",
    }

    if op.module_key == "raw_materials" and op.op_key in RAW_MATS_BLANK_OP_KEYS:
        if op.bom_item and op.bom_item.part_id:
            part_id = op.bom_item.part_id
            uom = op.bom_item.unit or "ea"

            # Done adds blanks
            if qty_done_delta:
                apply_part_inventory_delta(part_id, "blank", qty_done_delta, uom=uom)

            # Scrap reduces blanks (delta)
            if qty_scrap_delta:
                apply_part_inventory_delta(part_id, "blank", -qty_scrap_delta, uom=uom)
        else:
            flash(
                "Progress saved, but Parts Inventory was not updated (BOM item is not linked to a catalog Part).",
                "warning",
            )
    # ---------------------------------------------

    db.session.commit()
    flash("Progress added.", "success")
    return redirect(url_for("jobs_bp.job_daily_update", job_id=job_id, _anchor=f"op-{op.id}"))

@jobs_bp.route("/<int:job_id>/daily_update", methods=["GET"])
@login_required
def job_daily_update(job_id):
    job = Job.query.get_or_404(job_id)

    ops = (
        BuildOperation.query
        .join(Build, BuildOperation.build_id == Build.id)
        .filter(Build.job_id == job.id)
        .order_by(BuildOperation.build_id.asc())
        .all()
    )

    ops_by_build = {}
    op_ids = []
    for op in ops:
        ops_by_build.setdefault(op.build_id, []).append(op)
        op_ids.append(op.id)

    progress_by_op_id = {}
    if op_ids:
        progress_rows = (
            BuildOperationProgress.query
            .filter(BuildOperationProgress.build_operation_id.in_(op_ids))
            .order_by(BuildOperationProgress.created_at.desc(), BuildOperationProgress.id.desc())
            .limit(400)  # enough for "today-ish" visibility
            .all()
        )
        for p in progress_rows:
            progress_by_op_id.setdefault(p.build_operation_id, []).append(p)

    return render_template(
        "jobs_management/daily_update.html",
        job=job,
        ops_by_build=ops_by_build,
        progress_by_op_id=progress_by_op_id,
    )
