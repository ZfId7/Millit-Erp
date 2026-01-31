# File path: modules/shared/status.py

STATUS_QUEUE = "queue"
STATUS_IN_PROGRESS = "in_progress"
STATUS_BLOCKED = "blocked"
STATUS_COMPLETED = "completed"
STATUS_CANCELLED = "cancelled"

LEGACY_COMPLETE = "complete"

TERMINAL_STATUSES = (
    STATUS_COMPLETED,
    STATUS_CANCELLED,
    LEGACY_COMPLETE,
)
