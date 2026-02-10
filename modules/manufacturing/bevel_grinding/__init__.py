
from flask import Blueprint


bevel_bp = Blueprint(
    "bevel_bp",
    __name__,
    template_folder="templates"
    )

#Import routes AFTER blueprint exists
from .routes import * #noqa
