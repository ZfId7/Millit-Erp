# File path: modules/manufacturing/raw_materials/__init__.py
# V1 Refactor | Addition of Raw Materials as base module for waterjet/cutting
from flask import Blueprint

raw_mats_bp = Blueprint(
    "raw_materials_bp",
    __name__,
    template_folder="templates",
    )

# Import routes AFTER blueprint exists
from .routes import * # noqa
