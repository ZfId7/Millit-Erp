# File path: modules/raw_materials/waterjet/__init__.py
# V1 Refactor
# V2 Refactor again | Move inside raw_materials.module | change blueprint: raw_mats_waterjet_bp
from flask import Blueprint

raw_mats_waterjet_bp = Blueprint(
	"raw_mats_waterjet_bp",
	__name__,
	template_folder="templates",
	)

# Import routes AFTER blueprint exists
from .routes import * # noqa