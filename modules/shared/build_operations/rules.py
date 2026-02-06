# File path: modules/shared/build_operations/rules.py

def can_complete_by_required(op) -> tuple[bool, str]:
    """
    Ready-to-complete rule:
    - completion allowed when qty_done >= qty_required
    - scrap never substitutes
    - planned / overbuild never blocks
    """
    required = float(getattr(op, "qty_required", 0) or 0)
    done = float(getattr(op, "qty_done", 0) or 0)

    if required <= 0:
        return False, "qty_required is not set (or is 0)."

    if done < required:
        remaining = required - done
        # keep it operator-friendly
        return False, f"Not ready: {remaining:g} required good parts remaining."

    return True, ""
