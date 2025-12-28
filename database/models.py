# File path: database/models.py
# Change summary:
# -V1 Job Management backbone models (Customer → Job → Build → BOM)
# -V1 BuildDrawing stores PDF metadata for in-browser viewing
# -V1 Work logs and notes provide richer job-level tracking
# -V1 User table supports admin/employee auth
# -V2 Inventory Tables for managing shop stock
# -V3 Waterjet Integration/Consumables
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import UniqueConstraint


db = SQLAlchemy()


# OPTIONAL: tiny perf wins
# Add index=True where you’ll filter/sort often.


class User(db.Model):
    __tablename__ = 'users'


    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(16), default='employee') # 'admin' or 'employee'


    def set_password(self, password):
        self.password_hash = generate_password_hash(password)


    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


    def is_admin(self):
        return self.role == 'admin'

class Customer(db.Model):
    __tablename__ = "customers"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, unique=True, index=True)
    email = db.Column(db.String(120))
    phone = db.Column(db.String(50))
    notes = db.Column(db.Text)


    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


    jobs = db.relationship("Job", back_populates="customer", cascade="all, delete-orphan")

class Job(db.Model):
    __tablename__ = "jobs"
    __table_args__ = {"sqlite_autoincrement": True}
    id = db.Column(db.Integer, primary_key=True)


    customer_id = db.Column(db.Integer, db.ForeignKey("customers.id"), nullable=False, index=True)
    customer = db.relationship("Customer", back_populates="jobs")


    job_number = db.Column(db.String(32), nullable=False, unique=True, index=True)
    title = db.Column(db.String(200), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="queue", index=True)


    priority = db.Column(db.String(20), default="normal")
    due_date = db.Column(db.Date)
    notes = db.Column(db.Text)


    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    builds = db.relationship("Build", back_populates="job", cascade="all, delete-orphan")
    work_logs = db.relationship("JobWorkLog", back_populates="job", cascade="all, delete-orphan")
    job_notes = db.relationship("JobNote", back_populates="job", cascade="all, delete-orphan")
    # archive batch 001 here
    is_archived = db.Column(db.Boolean, default=False, nullable=False)
    archived_at = db.Column(db.DateTime, nullable=True)
    archived_by = db.Column(db.Integer, nullable=True)  # store user_id if you have it	
    
class Build(db.Model):
    __tablename__ = "builds"
    __table_args__ = {"sqlite_autoincrement": True}
    id = db.Column(db.Integer, primary_key=True)


    job_id = db.Column(db.Integer, db.ForeignKey("jobs.id"), nullable=False, index=True)
    job = db.relationship("Job", back_populates="builds")


    name = db.Column(db.String(120), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="queue", index=True)


    qty_ordered = db.Column(db.Integer, nullable=False, default=1)
    qty_completed = db.Column(db.Integer, nullable=False, default=0)
    qty_scrap = db.Column(db.Integer, nullable=False, default=0)


    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


    bom_items = db.relationship("BOMItem", back_populates="build", cascade="all, delete-orphan")
    drawings = db.relationship("BuildDrawing", back_populates="build", cascade="all, delete-orphan")    

class Part(db.Model):
    __tablename__ = "parts"
    id = db.Column(db.Integer, primary_key=True)


    part_number = db.Column(db.String(64), nullable=False, unique=True, index=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)

    part_type_id = db.Column(db.Integer, db.ForeignKey("part_types.id"))
    part_type = db.relationship("PartType")
    
    unit = db.Column(db.String(20), default="ea")
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

class BOMItem(db.Model):
    __tablename__ = "bom_items"
    __table_args__ = {"sqlite_autoincrement": True}
    id = db.Column(db.Integer, primary_key=True)


    build_id = db.Column(db.Integer, db.ForeignKey("builds.id"), nullable=False, index=True)
    build = db.relationship("Build", back_populates="bom_items")


    part_id = db.Column(db.Integer, db.ForeignKey("parts.id"))
    part = db.relationship("Part")


    line_no = db.Column(db.Integer, nullable=False, default=1)


    part_number = db.Column(db.String(64))
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)


    qty = db.Column(db.Float, nullable=False, default=1.0)
    unit = db.Column(db.String(20), default="ea")


    source = db.Column(db.String(20), default="manual") # manual | template | csv
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


    __table_args__ = (
    UniqueConstraint("build_id", "line_no", name="uq_bom_build_line"),
    )

class BuildDrawing(db.Model):
    __tablename__ = "build_drawings"
    id = db.Column(db.Integer, primary_key=True)


    build_id = db.Column(db.Integer, db.ForeignKey("builds.id"), nullable=False, index=True)
    build = db.relationship("Build", back_populates="drawings")


    filename = db.Column(db.String(260), nullable=False)
    stored_path = db.Column(db.String(500), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

class JobWorkLog(db.Model):
    __tablename__ = "job_work_logs"
    id = db.Column(db.Integer, primary_key=True)


    job_id = db.Column(db.Integer, db.ForeignKey("jobs.id"), nullable=False, index=True)
    job = db.relationship("Job", back_populates="work_logs")


    entry_ts = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


    qty_completed_delta = db.Column(db.Integer, default=0, nullable=False)
    qty_scrap_delta = db.Column(db.Integer, default=0, nullable=False)


    runtime_seconds = db.Column(db.Integer, default=0, nullable=False)


    note = db.Column(db.Text)

class JobNote(db.Model):
    __tablename__ = "job_notes"
    id = db.Column(db.Integer, primary_key=True)


    job_id = db.Column(db.Integer, db.ForeignKey("jobs.id"), nullable=False, index=True)
    job = db.relationship("Job", back_populates="job_notes")


    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    body = db.Column(db.Text, nullable=False)
    
class PartType(db.Model):
    __tablename__ = "part_types"
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(50), unique=True, nullable=False)   # e.g. "blade"
    name = db.Column(db.String(120), nullable=False)              # e.g. "Blade"

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
class RoutingTemplate(db.Model):
    """
    Defines the default routing steps for a PartType.
    """
    __tablename__ = "routing_templates"
    id = db.Column(db.Integer, primary_key=True)

    part_type_id = db.Column(db.Integer, db.ForeignKey("part_types.id"), nullable=False)
    part_type = db.relationship("PartType")

    op_key = db.Column(db.String(50), nullable=False)     # e.g. "surface_grind"
    op_name = db.Column(db.String(120), nullable=False)   # e.g. "Surface Grind"
    module_key = db.Column(db.String(50), nullable=False) # e.g. "surface_grinding"
    sequence = db.Column(db.Integer, nullable=False)      # 10,20,30... (easy inserts later)

    is_outsourced = db.Column(db.Boolean, default=False, nullable=False)

    __table_args__ = (
        UniqueConstraint("part_type_id", "op_key", name="uq_routing_parttype_op"),
    )


class BuildOperation(db.Model):
    """
    Concrete queued operation instance generated from BOM.
    """
    __tablename__ = "build_operations"
    __table_args__ = {"sqlite_autoincrement": True}
    id = db.Column(db.Integer, primary_key=True)

    build_id = db.Column(
		db.Integer, 
		db.ForeignKey("builds.id", ondelete="CASCADE"),
		nullable=False
	)
    build = db.relationship("Build")

    bom_item_id = db.Column(db.Integer, db.ForeignKey("bom_items.id"), nullable=True)
    bom_item = db.relationship("BOMItem")

    op_key = db.Column(db.String(50), nullable=False)
    op_name = db.Column(db.String(120), nullable=False)
    module_key = db.Column(db.String(50), nullable=False)

    sequence = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="queue")  # queue/in_progress/complete

    qty_planned = db.Column(db.Float, nullable=False, default=0.0)
    qty_done = db.Column(db.Float, nullable=False, default=0.0)
    qty_scrap = db.Column(db.Float, nullable=False, default=0.0)

    is_outsourced = db.Column(db.Boolean, default=False, nullable=False)
    vendor = db.Column(db.String(120))   # for outsourced ops later (heat treat)
    notes = db.Column(db.Text)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    # archive batch 001 here
    cancelled_at = db.Column(db.DateTime, nullable=True)
    cancelled_reason = db.Column(db.String(255), nullable=True)
    
    __table_args__ = (
        UniqueConstraint("build_id", "bom_item_id", "op_key", name="uq_build_bom_op"),
    )

class BuildOperationProgress(db.Model):
    __tablename__ = "build_operation_progress"
    __table_args__ = {"sqlite_autoincrement": True}

    id = db.Column(db.Integer, primary_key=True)

    build_operation_id = db.Column(
        db.Integer,
        db.ForeignKey("build_operations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    qty_done_delta = db.Column(db.Float, nullable=False, default=0.0)
    qty_scrap_delta = db.Column(db.Float, nullable=False, default=0.0)

    note = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    build_operation = db.relationship(
        "BuildOperation",
        backref=db.backref("progress_updates", cascade="all, delete-orphan"),
    )

    
class RawStock(db.Model):
    __tablename__ = "raw_stock"
    __table_args__ = {"sqlite_autoincrement": True}

    id = db.Column(db.Integer, primary_key=True)

    # Core identity
    name = db.Column(db.String(128), nullable=False)          # e.g. "CPM Magnacut Sheet"
    material_type = db.Column(db.String(32), nullable=False)  # steel, titanium, g10, micarta, cf, wood, etc.
    grade = db.Column(db.String(64), nullable=True)           # e.g. "Magnacut", "Ti-6Al-4V", "AEB-L"
    form = db.Column(db.String(32), nullable=False)           # sheet, plate, bar, round, tube, scale, block, etc.

    # “Defaults” Waterjet cares about
    thickness_in = db.Column(db.Float, nullable=True)         # inches; optional for wood/etc
    width_in = db.Column(db.Float, nullable=True)
    length_in = db.Column(db.Float, nullable=True)

    # Inventory controls (v1 simple)
    qty_on_hand = db.Column(db.Float, default=0.0, nullable=False)   # sheets count, feet, pieces, lbs—depends on unit
    uom = db.Column(db.String(16), default="ea", nullable=False)     # ea, sheet, in, ft, lb, etc.

    vendor = db.Column(db.String(128), nullable=True)
    location = db.Column(db.String(64), nullable=True)        # rack/bin/shelf
    notes = db.Column(db.Text, nullable=True)

    is_active = db.Column(db.Boolean, default=True, nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

class PartInventory(db.Model):
    __tablename__ = "part_inventory"
    __table_args__ = (
        UniqueConstraint("part_id", "stage_key", name="uq_part_inventory_part_stage"),
        {"sqlite_autoincrement": True},
    )

    id = db.Column(db.Integer, primary_key=True)

    part_id = db.Column(db.Integer, db.ForeignKey("parts.id"), nullable=False, index=True)
    part = db.relationship("Part")

    # stage_key examples: "blank", "wip", "finished"
    stage_key = db.Column(db.String(32), nullable=False, default="blank", index=True)

    qty_on_hand = db.Column(db.Float, default=0.0, nullable=False)
    uom = db.Column(db.String(16), default="ea", nullable=False)

    location = db.Column(db.String(64), nullable=True)
    notes = db.Column(db.Text, nullable=True)

    is_active = db.Column(db.Boolean, default=True, nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class WaterjetOperationDetail(db.Model):
    __tablename__ = "waterjet_operation_details"
    __table_args__ = {"sqlite_autoincrement": True}

    id = db.Column(db.Integer, primary_key=True)

    build_operation_id = db.Column(
        db.Integer,
        db.ForeignKey("build_operations.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    raw_stock_id = db.Column(
        db.Integer,
        db.ForeignKey("raw_stock.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # per-op overrides (optional)
    thickness_override = db.Column(db.Float, nullable=True)
    width_override = db.Column(db.Float, nullable=True)
    length_override = db.Column(db.Float, nullable=True)

    material_source = db.Column(db.String(32), nullable=True)  # inventory/customer_supplied/outsourced/other
    yield_note = db.Column(db.String(128), nullable=True)
    # material / stock usage
    material_remaining = db.Column(db.Boolean, nullable=True)  # True = some left, False = all used


    file_name = db.Column(db.String(255), nullable=True)
    program_revision = db.Column(db.String(64), nullable=True)

    runtime_est_min = db.Column(db.Integer, nullable=True)
    runtime_actual_min = db.Column(db.Integer, nullable=True)

    blocked_reason = db.Column(db.String(64), nullable=True)   # required when op.status == 'blocked'
    blocked_notes = db.Column(db.Text, nullable=True)

    notes = db.Column(db.Text, nullable=True)

    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # relationships (optional but handy)
    operation = db.relationship("BuildOperation", backref=db.backref("waterjet_detail", uselist=False))
    raw_stock = db.relationship("RawStock")

class WaterjetConsumable(db.Model):
    __tablename__ = "waterjet_consumables"
    __table_args__ = {"sqlite_autoincrement": True}

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(128), nullable=False)          # "0.010 Orifice", "Mixing Tube", "Garnet 80 mesh"
    category = db.Column(db.String(32), nullable=False)       # nozzle, orifice, garnet, seal, filter, other
    part_number = db.Column(db.String(64), nullable=True)
    vendor = db.Column(db.String(128), nullable=True)

    qty_on_hand = db.Column(db.Float, default=0.0, nullable=False)
    uom = db.Column(db.String(16), default="ea", nullable=False)     # ea, lb, bag, etc.
    reorder_point = db.Column(db.Float, nullable=True)              # when <= reorder_point => low
    reorder_qty = db.Column(db.Float, nullable=True)

    location = db.Column(db.String(64), nullable=True)        # bin/rack
    notes = db.Column(db.Text, nullable=True)

    is_active = db.Column(db.Boolean, default=True, nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

class SurfaceGrindingOperationDetail(db.Model):
    __tablename__ = "surface_grinding_operation_details"

    id = db.Column(db.Integer, primary_key=True)

    build_operation_id = db.Column(
        db.Integer,
        db.ForeignKey("build_operations.id", ondelete="CASCADE"),
        unique=True,
        nullable=False
    )

    # Wheel / setup
    wheel_brand = db.Column(db.String(80))
    wheel_model = db.Column(db.String(120))
    wheel_grit = db.Column(db.Integer)            # 46 / 60 / 80 / 120 etc
    wheel_grade = db.Column(db.String(10))        # e.g. "G", "F", "K"
    wheel_structure = db.Column(db.String(10))    # e.g. "10", "15"
    wheel_bond = db.Column(db.String(10))         # e.g. "V"

    #coolant = db.Column(db.String(80))            # optional: flood/mist/brand/etc

    # Process notes (keep it flexible early)
    cycles = db.Column(db.Integer)                # total passes (or cycles)
    stock_removed_in = db.Column(db.Float)        # inches removed (total)
    target_thickness_in = db.Column(db.Float)
    actual_thickness_in = db.Column(db.Float)

    finish_notes = db.Column(db.Text)
    issue_notes = db.Column(db.Text)

    # Optional “parameter” capture (don’t overdo: just enough)
    wheel_speed_hz = db.Column(db.Float)
    table_speed_setting = db.Column(db.String(20))      # "2.5", "3:00", etc (string is safer)
    traverse_speed_setting = db.Column(db.String(20))   # "10.5", "11:00", etc
    doc_per_pass_in = db.Column(db.Float)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    build_operation = db.relationship(
        "BuildOperation",
        backref=db.backref("surface_grinding_detail", uselist=False, cascade="all, delete-orphan")
    )

