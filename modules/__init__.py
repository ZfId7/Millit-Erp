# /app/modules/__init__.py

# Import each module's blueprint
from .inventory.routes import inventory_bp
from .surface_grinding.routes import surface_bp
from .bevel_grinding.routes import bevel_bp
from .jobs_management.routes import jobs_bp
from .manufacturing.routes import mfg_bp
from .assembly.routes import assembly_bp, cad_upload_bp
from .assembly.routes.assembly_bom import assembly_bom_bp
from .analytics.routes import analytics_bp
from .user.routes import admin_users_bp


module_blueprints = [
    ("inventory_bp", inventory_bp, "/inventory"),
    ("surface_grinding_bp", surface_bp, "/surface"),
    ("bevel_bp", bevel_bp, "/bevel"),
    ("jobs_bp", jobs_bp, "/jobs"),
    ("mfg_bp", mfg_bp, "/manufacturing"),
    ("assembly_bp", assembly_bp, "/assembly"),
    ("upload_cad", cad_upload_bp, "/assembly"),
    ("assembly_bom_bp", assembly_bom_bp, "/"),
    ("analytics_bp", analytics_bp, "/analytics"),
    ("admin_users_bp", admin_users_bp, "/user"),
]

# Optional: export list so app.py can loop through them
__all__ = ["module_blueprints"]
