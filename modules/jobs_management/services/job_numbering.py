# File path: modules/jobs_management/services/job_numbering.py

from datetime import datetime

from sqlalchemy import func
from database.models import Job, db
from modules.jobs_management import jobs_bp

def _next_job_number():
    # JOB-YYYY-000001 style using max(id). Good enough for now.
    year = datetime.utcnow().year
    last_id = db.session.query(func.max(Job.id)).scalar() or 0
    seq = last_id + 1
    return f"JOB-{year}-{seq:06d}"
