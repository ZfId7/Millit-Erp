# File path: modules/manufacturing/raw_materials/waterjet/routes/__init__.py
# -V1 queue
# -V2 Detail/Detail Edit
# -V3 Reopen cancelled ops
# -V4 Refactor Routes
# V5 Refactor again | moved inside modules/raw_materials/
from .index import * #noqa
from .queue import * # noqa
from .ops import * # noqa
from .details import * # noqa
from .manager import * # noqa 
from .progress import * # noqa


