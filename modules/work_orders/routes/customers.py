# File path: modules/work_orders/routes/customers.py
from datetime import datetime
from flask import render_template, request, redirect, url_for, flash

from database.models import db, Customer, WorkOrder, Job
from modules.user.decorators import login_required
from modules.work_orders import work_orders_bp


@work_orders_bp.route("/customers")
@login_required
def customers_index():
    customers = Customer.query.order_by(Customer.name.asc()).all()
    return render_template("work_orders/customers/index.html", customers=customers)


@work_orders_bp.route("/customers/new")
@login_required
def customers_new():
    return render_template("work_orders/customers/new.html")


@work_orders_bp.route("/customers/create", methods=["POST"])
@login_required
def customers_create():
    name = (request.form.get("name") or "").strip()
    email = (request.form.get("email") or "").strip() or None
    phone = (request.form.get("phone") or "").strip() or None
    notes = (request.form.get("notes") or "").strip() or None

    if not name:
        flash("Customer name is required.", "error")
        return redirect(url_for("work_orders_bp.customers_new"))

    c = Customer(
        name=name,
        email=email,
        phone=phone,
        notes=notes,
        created_at=datetime.utcnow(),
    )
    db.session.add(c)
    db.session.commit()

    flash("Customer created.", "success")
    return redirect(url_for("work_orders_bp.customers_index"))


@work_orders_bp.route("/customers/<int:customer_id>")
@login_required
def customers_detail(customer_id):
    customer = Customer.query.get_or_404(customer_id)

    # V0 lists (assumes WorkOrder has customer_id)
    wos = WorkOrder.query.filter_by(customer_id=customer.id).order_by(WorkOrder.created_at.desc()).all()
    jobs = Job.query.filter_by(customer_id=customer.id).order_by(Job.created_at.desc()).all()

    return render_template("work_orders/customers/detail.html", customer=customer, wos=wos, jobs=jobs)


@work_orders_bp.route("/customers/<int:customer_id>/edit")
@login_required
def customers_edit(customer_id):
    customer = Customer.query.get_or_404(customer_id)
    return render_template("work_orders/customers/edit.html", customer=customer)


@work_orders_bp.route("/customers/<int:customer_id>/update", methods=["POST"])
@login_required
def customers_update(customer_id):
    customer = Customer.query.get_or_404(customer_id)

    name = (request.form.get("name") or "").strip()
    email = (request.form.get("email") or "").strip() or None
    phone = (request.form.get("phone") or "").strip() or None
    notes = (request.form.get("notes") or "").strip() or None

    if not name:
        flash("Customer name is required.", "error")
        return redirect(url_for("work_orders_bp.customers_edit", customer_id=customer.id))

    customer.name = name
    customer.email = email
    customer.phone = phone
    customer.notes = notes

    db.session.commit()
    flash("Customer updated.", "success")
    return redirect(url_for("work_orders_bp.customers_detail", customer_id=customer.id))
