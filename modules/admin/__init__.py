# File path:modules/admin/__init__.py

from flask import Blueprint

admin_bp = Blueprint("admin_bp",__name__) 

from . import routes  # noqa
