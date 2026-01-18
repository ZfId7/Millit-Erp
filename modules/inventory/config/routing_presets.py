# File path: modules/inventory/config/routing_presets.py

ROUTING_STEP_PRESETS = {
    "waterjet_cut": {
        "op_name": " Waterjet Blanks",
        "module_key": "raw_materials",
        "sequence": 10,
        "is_outsourced": False,
    },
    "laser_cut": {
        "op_name": " Laser Cut Blanks",
        "module_key": "raw_materials",
        "sequence": 12,
        "is_outsourced": True,
    },
    "edm_cut": {
        "op_name": " EDM Blanks",
        "module_key": "raw_materials",
        "sequence": 14,
        "is_outsourced": True,
    },
    "bandsaw_cut": {
        "op_name": " Bandsaw Cut Blanks",
        "module_key": "raw_materials",
        "sequence": 16,
        "is_outsourced": False,
    },
    "tablesaw_cut": {
        "op_name": " Tablesaw Cut Blanks",
        "module_key": "raw_materials",
        "sequence": 18,
        "is_outsourced": False,
    },
    "surface_grind": {
        "op_name": " Surface Grind Blade Blanks",
        "module_key": "surface_grinding",
        "sequence": 20,
        "is_outsourced": False,
    },
    "cnc_profile": {
        "op_name": "Profile Blanks",
        "module_key": "manufacturing",
        "sequence": 30,
        "is_outsourced": False,
    },
    "heat_treat": {
        "op_name": "Send Blades out for Heat Treat",
        "module_key": "heat_treat",
        "sequence": 40,
        "is_outsourced": True,
    },
    "in_house_ht": {
        "op_name": "Heat Treat",
        "module_key": "heat_treat",
        "sequence": 45,
        "is_outsourced": False,
    },
    "bevel_grind": {
        "op_name": "Bevel Grind Blades",
        "module_key": "bevel_grinding",
        "sequence": 50,
        "is_outsourced": False,
    }
    
    
}