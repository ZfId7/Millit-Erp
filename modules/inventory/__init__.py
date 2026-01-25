# File path: modules/inventory/__init__.py

from flask import Blueprint

inventory_bp = Blueprint("inventory_bp", __name__)

# Import routes AFTER blueprint exists
from .routes import * # noqa