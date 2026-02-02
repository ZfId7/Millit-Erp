# File path: modules/shared/claims.py

# modules/shared/claims.py

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from flask import current_app

from modules.shared.status import TERMINAL_STATUSES


ROLE_EDITOR = "editor"
ROLE_CONTRIBUTOR = "contributor"
ROLE_ADMIN_OVERRIDE = "admin_override"


def _now() -> datetime:
    return datetime.utcnow()


def claim_stale_seconds() -> int:
    return int(current_app.config.get("MERP_CLAIM_STALE_SECONDS", 2 * 60 * 60))


def is_claim_stale(obj) -> bool:
    touched = getattr(obj, "claim_touched_at", None)
    if not touched:
        return True
    return (_now() - touched) > timedelta(seconds=claim_stale_seconds())


def touch_claim(obj) -> None:
    obj.claim_touched_at = _now()


def release_claim(obj) -> None:
    obj.claimed_by_user_id = None
    obj.claimed_at = None
    obj.claim_touched_at = None
    if hasattr(obj, "claim_note"):
        obj.claim_note = None


def claim(obj, *, user_id: int, is_admin: bool = False, force: bool = False, as_contributor: bool = False) -> Dict[str, Any]:
    """
    Global claim policy (Mode A):

    - Start should call claim(... as_contributor=False) → exclusive editor.
    - Progress should call claim(... as_contributor=True) → contributor allowed if:
        allow_multi_user OR stale OR admin OR force
      contributors do NOT steal ownership unless stale/admin/force.

    Returns:
      { ok: bool, role: str, changed: bool, reason?: str, stole_stale?: bool }
    """
    status = (getattr(obj, "status", None) or "")
    if status in TERMINAL_STATUSES:
        return {"ok": False, "reason": "terminal"}

    owner_id = getattr(obj, "claimed_by_user_id", None)
    allow_multi = bool(getattr(obj, "allow_multi_user", False))

    # already owner
    if owner_id == user_id:
        touch_claim(obj)
        if not getattr(obj, "claimed_at", None):
            obj.claimed_at = obj.claim_touched_at
        return {"ok": True, "role": ROLE_EDITOR, "changed": False}

    # unclaimed
    if not owner_id:
        if as_contributor and not (allow_multi or is_admin or force):
            return {"ok": False, "reason": "cannot_contribute_unclaimed"}
        obj.claimed_by_user_id = user_id
        obj.claimed_at = _now()
        obj.claim_touched_at = obj.claimed_at
        return {"ok": True, "role": ROLE_EDITOR, "changed": True}

    # claimed by someone else
    if force or is_admin:
        obj.claimed_by_user_id = user_id
        obj.claimed_at = _now()
        obj.claim_touched_at = obj.claimed_at
        return {"ok": True, "role": ROLE_ADMIN_OVERRIDE, "changed": True}

    if allow_multi:
        touch_claim(obj)
        return {"ok": True, "role": ROLE_CONTRIBUTOR, "changed": False}

    if is_claim_stale(obj):
        obj.claimed_by_user_id = user_id
        obj.claimed_at = _now()
        obj.claim_touched_at = obj.claimed_at
        return {"ok": True, "role": ROLE_EDITOR, "changed": True, "stole_stale": True}

    return {"ok": False, "reason": "claimed_by_other"}
