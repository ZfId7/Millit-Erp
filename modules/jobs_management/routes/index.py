# File path: modules/jobs_management/routes/index.py

from datetime import datetime
from flask import flash, redirect, render_template, request, url_for
from sqlalchemy import func
from database.models import Build, Customer, Job, db
from modules.jobs_management.routes import _next_job_number
from modules.user.decorators import login_required
from modules.jobs_management import jobs_bp


@jobs_bp.route("/")
@login_required
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
