# File path: modules/manufacturing/machining/__init__.py
# V1 Base Build

from flask import Blueprint

mfg_bp = Blueprint(
    "mfg_bp",
    __name__,
    template_folder="templates",
    )

#Import routes AFTER blueprint exists
from .routes import * #noqa
