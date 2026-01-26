# File path: modules/jobs_management/__init__.py

from flask import Blueprint

jobs_bp = Blueprint("jobs_bp", __name__)

# Import routes AFTER blueprint exists
from .routes import * # noqa
