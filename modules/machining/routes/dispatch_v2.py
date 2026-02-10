# File path: modules/machining/routes/dispatch_v2.py

from flask import render_template, request, session
from sqlalchemy import func, and_
from collections import OrderedDict

from database.models import db, BuildOperation, BOMItem, Build, Job, WorkOrder
from modules.machining import mfg_bp

from modules.user.decorators import admin_required, login_required
from modules.shared.status import TERMINAL_STATUSES  # wherever your canonical statuses live




def _op_deeplink(op: BuildOperation):
    """
    Dispatch navigates to the module UI; modules handle claim/start/progress.
    Adjust endpoints to match your actual route names.
    """
    module = op.module_key or ""

    # Map module_key -> endpoint
    # IMPORTANT: update these to your actual blueprint endpoint names.
    MAP = {
        "surface_grinding": ("surface_grinding_bp.surface_details", {"op_id": op.id}),
        "heat_treat": ("heat_treat_bp.heat_treat_details", {"op_id": op.id}),
        "raw_materials": ("raw_mats_waterjet_bp.waterjet_detail", {"op_id": op.id}),
        "manufacturing": ("mfg_bp.mfg_details", {"op_id": op.id}),
        # "bevel_grinding": ("bevel_grinding_bp.bevel_detail", {"op_id": op.id}),  # soon
    }

    if module in MAP:
        return MAP[module]

    # Safe fallback: go to admin op detail (always exists)
    return ("admin_bp.op_detail", {"op_id": op.id})


@mfg_bp.route("/dispatch_mfg_v2", methods=["GET"])
@login_required
def mfg_dispatch_v2():
    dept = "manufacturing"

    # Checkbox behavior:
    # - First visit (no params): default released_only ON
    # - Form submitted (has params): released_only is ON only if param present
    if len(request.args) == 0:
        released_only = True
    else:
        released_only = (request.args.get("released_only") == "1")

        
    show_all = (request.args.get("show_all") == "1")  # if true, show all queue ops, not just next-per-bom
    module_key = (request.args.get("module_key") or "").strip()
    claimed = (request.args.get("claimed") or "").strip()  # "", "claimed", "unclaimed"
    

    base_filters = [
        BuildOperation.department == dept,
        BuildOperation.status.notin_(TERMINAL_STATUSES),  # includes queue + in_progress
    ]

    if module_key:
        base_filters.append(BuildOperation.module_key == module_key)

    if claimed == "claimed":
        base_filters.append(BuildOperation.claimed_by_user_id.isnot(None))
    elif claimed == "unclaimed":
        base_filters.append(BuildOperation.claimed_by_user_id.is_(None))

    if released_only and hasattr(BuildOperation, "is_released"):
        base_filters.append(BuildOperation.is_released.is_(True))


    if show_all:
        # Expanded view: all current/future ops (queue + in_progress)
        ops = (
            BuildOperation.query
            .filter(*base_filters)
            .order_by(
                BuildOperation.build_id.asc(),
                BuildOperation.bom_item_id.asc().nullsfirst(),
                BuildOperation.sequence.asc(),
                BuildOperation.id.asc(),
            )
            .limit(1000)
            .all()
        )

    else:
        # Compact view: one "current" op per BOM line
        # (lowest sequence among non-terminal, released if enabled)
        min_seq_subq = (
            db.session.query(
                BuildOperation.bom_item_id.label("bom_item_id"),
                func.min(BuildOperation.sequence).label("min_sequence"),
            )
            .filter(*base_filters)
            .filter(BuildOperation.bom_item_id.isnot(None))
            .group_by(BuildOperation.bom_item_id)
            .subquery()
        )

        ops = (
            db.session.query(BuildOperation)
            .join(
                min_seq_subq,
                and_(
                    BuildOperation.bom_item_id == min_seq_subq.c.bom_item_id,
                    BuildOperation.sequence == min_seq_subq.c.min_sequence,
                ),
            )
            .order_by(
                BuildOperation.build_id.asc(),
                BuildOperation.bom_item_id.asc(),
                BuildOperation.sequence.asc(),
                BuildOperation.id.asc(),
            )
            .all()
        )

        # Include build-level ops (queue + in_progress)
        null_bom_ops = (
            BuildOperation.query
            .filter(*base_filters)
            .filter(BuildOperation.bom_item_id.is_(None))
            .order_by(BuildOperation.sequence.asc(), BuildOperation.id.asc())
            .all()
        )

        ops = null_bom_ops + ops



    # Group: build_id -> bom_item_id -> list[op]
    grouped = OrderedDict()

    for op in ops:
        build_id = op.build_id  # do not coerce to 0; build_id should exist
        bom_item_id = op.bom_item_id  # can be None

        grouped.setdefault(build_id, OrderedDict())
        grouped[build_id].setdefault(bom_item_id, [])
        grouped[build_id][bom_item_id].append(op)

    # Build view model with deeplinks (MUST be outside the loop above)
    build_groups = []

    for build_id, bom_groups in grouped.items():
        # Representative op for build/job metadata
        rep_op = None
        for _bom_id, _ops in bom_groups.items():
            if _ops:
                rep_op = _ops[0]
                break

        job_title = None
        if rep_op is not None:
            build = getattr(rep_op, "build", None)
            job = getattr(build, "job", None) if build else None
            job_title = getattr(job, "title", None) if job else None

        bom_blocks = []

        for bom_item_id, ops_in_bom in bom_groups.items():
            bom = ops_in_bom[0].bom_item if bom_item_id is not None and ops_in_bom else None

            op_rows = []
            for op in ops_in_bom:
                endpoint, params = _op_deeplink(op)
                op_rows.append({
                    "op": op,
                    "deeplink_endpoint": endpoint,
                    "deeplink_params": params,
                })

            bom_blocks.append({
                "bom_item_id": bom_item_id,
                "bom": bom,
                "ops": op_rows,
            })

        build_groups.append({
            "build_id": build_id,
            "job_title": job_title,
            "bom_blocks": bom_blocks,
        })

    return render_template(
        "manufacturing/dispatch_v2.html",
        build_groups=build_groups,
        filters={
            "module_key": module_key,
            "claimed": claimed,
            "released_only": released_only,
            "show_all": "1" if show_all else "0",
        }
    )

