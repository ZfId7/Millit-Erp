# File path: modules/shared/nav_registry.py

from typing import Optional

MFG_BLUEPRINTS = {
    "mfg_bp",
    "surface_grinding_bp",
    "bevel_bp",
    "heat_treat_bp",
    "raw_materials_bp",
    "raw_mats_waterjet_bp",
}

ADMIN_BLUEPRINTS = {
    "admin_bp",
    "analytics_bp",
    "job_management_bp",
    "admin_users_bp",
    # add more admin blueprints here
}

DEPT_NAV = {
    "manufacturing": [
        # label, endpoint
        ("Dispatch", "mfg_bp.mfg_dispatch_v2"), # or whatever your hub route is
        ("Machining", "mfg_bp.mfg_index"),

        ("Surface Grinding", "surface_grinding_bp.surface_index"),
        ("Bevel Grinding", "bevel_bp.bevel_index"),
        ("Heat Treat", "heat_treat_bp.heat_treat_index"),

        ("Raw Materials", "raw_materials_bp.raw_mats_index"),
        
    ],

    "admin": [
        ("Admin Dashboard", "admin_bp.admin_index"),
        ("Analytics", "analytics_bp.analytics_index"),
        ("User Management", "admin_users_bp.user_index"),
        ("Job Management", "jobs_bp.jobs_index"),
        # add more admin links here
    ],
}

def infer_department_from_request(request) -> Optional[str]:
    bp = request.blueprint
    if not bp:
        return None
    if bp in MFG_BLUEPRINTS:
        return "manufacturing"
    if bp in ADMIN_BLUEPRINTS:
        return "admin"
    return None
