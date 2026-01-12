# File path: modules/manufacturing/__init__.py
# V1 Base Build

from flask import Blueprint

mfg_bp = Blueprint("mfg_bp", __name__)

#Import routes AFTER blueprint exists
from .routes import * #noqa