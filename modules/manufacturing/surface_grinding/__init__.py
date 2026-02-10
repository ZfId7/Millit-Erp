# File path: modules/surface_grinding/__init__.py
# V1 Refactor

from flask import Blueprint

surface_bp = Blueprint("surface_grinding_bp", __name__)

#Import routes AFTER blueprint exists
from .routes import * #noqa