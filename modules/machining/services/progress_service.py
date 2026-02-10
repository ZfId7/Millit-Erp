# File path: modules/machining/services/progress_service.py
# Compatibility shim: manufacturing remains the hub, but canonical logic is global/shared.

from modules.shared.services.build_op_progress_service import (
    add_op_progress,
    add_op_event,
    get_op_totals,
    OpProgressError,
    OpProgressTotals,
    
)
