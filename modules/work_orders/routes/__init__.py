# File path: modules/work_orders/routes/__init__.py
from modules.work_orders import work_orders_bp

# Import route modules to register decorators
from .index import *
from .customers import *
from .work_orders import *
from .planning import *
from .apply import *
