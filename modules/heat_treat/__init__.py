# File path: modules/heat_treat/__init__.py
# -V1 Base Build

from flask import Blueprint

heat_treat_bp = Blueprint("heat_treat_bp", __name__)

from .routes import * #noqa
