"""First-class anti-leakage — hard block when trained_to > oos_from."""
from __future__ import annotations

from datetime import date

import pandas as pd

from .contracts import LeakageCheck
from .kb_profiles import DEFAULT_PROFILE_ID, get_profile


class LeakageError(ValueError):
  """Raised when a run would train/use KB past the OOS boundary."""


def _as_date(v) -> date | None:
  if v is None or v == "":
    return None
  if isinstance(v, date) and not isinstance(v, pd.Timestamp):
    return v
  return pd.Timestamp(v).date()


def check_kb_leakage(
  profile_id: str | None,
  oos_from,
  *,
  require_trained_to: bool = False,
) -> LeakageCheck:
  """
  Causal rule: KB trained_to must be <= oos_from.
  Missing trained_to is allowed only when require_trained_to=False
  (still filtered by as_of each week).
  """
  pid = profile_id or DEFAULT_PROFILE_ID
  oos = _as_date(oos_from)
  p = get_profile(pid)
  if not p or not p.get("exists"):
    return LeakageCheck(
      ok=False,
      message=f"KB profile '{pid}' missing or empty.",
      profile_id=pid,
      oos_from=oos,
    )

  trained_to = _as_date(p.get("trained_to"))
  if trained_to is None:
    if require_trained_to:
      return LeakageCheck(
        ok=False,
        message=f"Profile '{pid}' has no trained_to — cannot promote/OOS.",
        profile_id=pid,
        oos_from=oos,
      )
    return LeakageCheck(
      ok=True,
      message="Profile has no trained_to — weekly as_of causal filter still applies.",
      profile_id=pid,
      oos_from=oos,
    )

  if oos is None:
    return LeakageCheck(
      ok=True,
      message=f"OK — KB through {trained_to.isoformat()} (oos_from not set).",
      profile_id=pid,
      trained_to=trained_to,
    )

  if trained_to > oos:
    return LeakageCheck(
      ok=False,
      message=(
        f"LEAKAGE BLOCK: KB trained_to {trained_to.isoformat()} "
        f"> oos_from {oos.isoformat()}. "
        "Train KB only on the period BEFORE OOS."
      ),
      profile_id=pid,
      trained_to=trained_to,
      oos_from=oos,
    )

  return LeakageCheck(
    ok=True,
    message=f"OK — KB through {trained_to.isoformat()}, OOS from {oos.isoformat()}.",
    profile_id=pid,
    trained_to=trained_to,
    oos_from=oos,
  )


def assert_no_leakage(profile_id: str | None, oos_from, *, require_trained_to: bool = False) -> LeakageCheck:
  check = check_kb_leakage(profile_id, oos_from, require_trained_to=require_trained_to)
  if not check.ok:
    raise LeakageError(check.message)
  return check
