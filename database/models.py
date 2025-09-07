# File path: database/models.py
# Change summary:
# - Adds ParsedComponent table to store per-solid geometry extracted from STEP uploads
# - Adds relationship from Assembly → ParsedComponent (cascade delete)
# - Keeps existing Parts/BOM/Inventory intact

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

# You must initialize this in your app factory
# db = SQLAlchemy(app)
db = SQLAlchemy()


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(16), default='employee')  # 'admin' or 'employee'

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def is_admin(self):
        return self.role == 'admin'


class Part(db.Model):
    __tablename__ = 'parts'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    part_number = db.Column(db.String(64), unique=True, nullable=False)
    description = db.Column(db.Text)
    type = db.Column(db.String(32))  # 'purchased', 'manufactured', 'assembly'
    unit = db.Column(db.String(16))
    revision = db.Column(db.String(16))
    cad_file_path = db.Column(db.String(256))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    children = db.relationship("BOMLine", back_populates="parent", foreign_keys='BOMLine.parent_part_id')
    parents = db.relationship("BOMLine", back_populates="child", foreign_keys='BOMLine.child_part_id')
    inventory = db.relationship("Inventory", back_populates="part", uselist=False)

    def __repr__(self):
        return f"<Part {self.part_number}>"


class BOMLine(db.Model):
    __tablename__ = 'bom_lines'

    id = db.Column(db.Integer, primary_key=True)
    parent_part_id = db.Column(db.Integer, db.ForeignKey('parts.id'), nullable=False)
    child_part_id = db.Column(db.Integer, db.ForeignKey('parts.id'), nullable=False)
    quantity = db.Column(db.Float, nullable=False)
    unit = db.Column(db.String(16))
    notes = db.Column(db.Text)

    parent = db.relationship("Part", foreign_keys=[parent_part_id], back_populates="children")
    child = db.relationship("Part", foreign_keys=[child_part_id], back_populates="parents")

    def __repr__(self):
        return f"<BOM {self.parent_part_id} → {self.child_part_id} x{self.quantity}>"


class Inventory(db.Model):
    __tablename__ = 'inventory'

    id = db.Column(db.Integer, primary_key=True)
    part_id = db.Column(db.Integer, db.ForeignKey('parts.id'), nullable=False)
    on_hand = db.Column(db.Float, default=0)
    location = db.Column(db.String(64))
    min_stock = db.Column(db.Float, default=0)
    status = db.Column(db.String(32), default="active")

    part = db.relationship("Part", back_populates="inventory")

    def __repr__(self):
        return f"<Inventory for Part {self.part_id}: {self.on_hand}>"


class Assembly(db.Model):
    __tablename__ = 'assemblies'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    assembly_number = db.Column(db.String(100), unique=True, nullable=False)
    revision = db.Column(db.String(20))
    lead_time = db.Column(db.Integer)
    description = db.Column(db.Text)
    cad_filename = db.Column(db.String(256))
    shapes_filename = db.Column(db.String(256))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # New: link to parsed SOLID components extracted from uploaded STEP
    parsed_components = db.relationship(
        "ParsedComponent",
        back_populates="assembly",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Assembly {self.assembly_number}>"


class ParsedComponent(db.Model):
    __tablename__ = 'parsed_components'

    id = db.Column(db.Integer, primary_key=True)
    assembly_id = db.Column(db.Integer, db.ForeignKey('assemblies.id'), nullable=False, index=True)

    # index in the emitted parts[] array (helps correlate viewer selection → db row)
    solid_index = db.Column(db.Integer, nullable=False)

    # viewer/parse metadata
    name = db.Column(db.String(128))
    color = db.Column(db.String(16))
    mesh_hash = db.Column(db.String(64), index=True)
    volume = db.Column(db.Float)
    bb = db.Column(db.JSON)

    assembly = db.relationship("Assembly", back_populates="parsed_components")

    def __repr__(self):
        return f"<ParsedComponent asm={self.assembly_id} solid_index={self.solid_index} hash={self.mesh_hash}>"
