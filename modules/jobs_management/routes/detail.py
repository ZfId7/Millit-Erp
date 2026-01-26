# File path: modules/jobs_management/routes/detail.py

from flask import flash, redirect, render_template, url_for
from database.models import BOMHeader, Build, BuildOperation, Customer, Job
from modules.user.decorators import login_required
from modules.jobs_management import jobs_bp


@jobs_bp.route("/<int:job_id>")
@login_required
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
    
    # Map build_id -> active master BOMHeader id
    master_bom_by_build = {}

    for b in job.builds:
        bom = (
            BOMHeader.query
            .filter_by(assembly_part_id=b.assembly_part_id, is_active=True)
            .first()
        )
        master_bom_by_build[b.id] = bom.id if bom else None


    return render_template(
        "jobs_management/detail.html", 
        job=job, 
        ops_by_build=ops_by_build,
        master_bom_by_build=master_bom_by_build,
        )
