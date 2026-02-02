# File path: modules/shared/services/build_op_queries.py

from database.models import BuildOperation
from modules.shared.status import TERMINAL_STATUSES


def query_my_active_ops(user_id: int):
    return (
        BuildOperation.query
        .filter(BuildOperation.claimed_by_user_id == user_id)
        .filter(~BuildOperation.status.in_(TERMINAL_STATUSES))
        .order_by(
            BuildOperation.claim_touched_at.desc().nullslast(),
            BuildOperation.claimed_at.desc().nullslast(),
            BuildOperation.id.desc(),
        )
    )
