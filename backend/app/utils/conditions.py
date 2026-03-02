"""Condition evaluator for the conditional policy engine.

Policy rules may carry an optional 'conditions' dict. All present condition
keys are AND-ed together. A missing key is treated as always-passing.

Supported condition keys:
  env         list[str]  — agent.environment must be in this list
  time_range  dict       — {start: "HH:MM", end: "HH:MM", tz: "UTC"}
                           current UTC time must fall within [start, end]
  day_of_week list[str]  — e.g. ["Mon","Tue","Wed","Thu","Fri"]
                           current UTC weekday must be in this list

Example rule with conditions:
  {
    "action": "deploy:*",
    "resource": "production/*",
    "conditions": {
      "env": ["production"],
      "time_range": {"start": "09:00", "end": "17:00", "tz": "UTC"},
      "day_of_week": ["Mon", "Tue", "Wed", "Thu", "Fri"]
    }
  }
"""
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, Optional

if TYPE_CHECKING:
    from app.models.agent import Agent

_DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def evaluate_conditions(
    conditions: Dict[str, Any],
    agent: "Agent",
    context: Optional[Dict[str, Any]],
) -> bool:
    """Return True if all conditions in the dict are satisfied.

    Args:
        conditions: The 'conditions' value from a policy rule (may be empty).
        agent:      The Agent ORM object making the enforcement request.
        context:    The request context dict (reserved for future context-based conditions).

    Returns:
        True if every present condition passes, or if conditions is empty/None.
    """
    if not conditions:
        return True

    now_utc = datetime.now(timezone.utc)

    # ------------------------------------------------------------------
    # env — agent.environment must be in the allowed list
    # ------------------------------------------------------------------
    if "env" in conditions:
        allowed_envs = conditions["env"]
        if not isinstance(allowed_envs, list):
            allowed_envs = [allowed_envs]
        if agent.environment not in allowed_envs:
            return False

    # ------------------------------------------------------------------
    # time_range — current time must fall within [start, end] (UTC)
    # ------------------------------------------------------------------
    if "time_range" in conditions:
        tr = conditions["time_range"]
        # Use UTC regardless of tz field for now; tz stored for future ZoneInfo support
        start_h, start_m = _parse_hhmm(tr.get("start", "00:00"))
        end_h, end_m = _parse_hhmm(tr.get("end", "23:59"))
        current_minutes = now_utc.hour * 60 + now_utc.minute
        start_minutes = start_h * 60 + start_m
        end_minutes = end_h * 60 + end_m
        if not (start_minutes <= current_minutes <= end_minutes):
            return False

    # ------------------------------------------------------------------
    # day_of_week — current UTC weekday must be in the allowed list
    # ------------------------------------------------------------------
    if "day_of_week" in conditions:
        allowed_days = conditions["day_of_week"]
        if not isinstance(allowed_days, list):
            allowed_days = [allowed_days]
        current_day = _DAY_NAMES[now_utc.weekday()]
        if current_day not in allowed_days:
            return False

    return True


def _parse_hhmm(value: str) -> tuple[int, int]:
    """Parse 'HH:MM' into (hour, minute) integers. Defaults to (0, 0) on error."""
    try:
        parts = value.split(":")
        return int(parts[0]), int(parts[1])
    except (IndexError, ValueError):
        return 0, 0
