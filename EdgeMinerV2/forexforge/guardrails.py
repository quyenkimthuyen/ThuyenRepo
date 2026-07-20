"""Research hygiene — hold-out before promote, epoch spam limits."""
from __future__ import annotations

from dataclasses import dataclass

from .contracts import Report
from .kb_profiles import get_profile, list_snapshots
from .leakage import LeakageError, assert_no_leakage
from .logging_util import get_logger

log = get_logger("forexforge.guardrails")

MAX_EPOCHS_PER_ERA = 8
MIN_HOLDOUT_MONTHS_FOR_PROMOTE = 3


@dataclass
class PromoteVerdict:
  ok: bool
  reasons: list[str]


def check_epoch_limit(profile_id: str, additional: int = 1) -> PromoteVerdict:
  p = get_profile(profile_id)
  current = int((p or {}).get("epochs") or 0)
  snaps = list_snapshots(profile_id) if p else []
  n = max(current, len(snaps))
  if n + additional > MAX_EPOCHS_PER_ERA:
    msg = (
      f"Epoch limit: profile '{profile_id}' already has {n} epochs "
      f"(max {MAX_EPOCHS_PER_ERA}). Create a new era profile instead."
    )
    log.warning(msg)
    return PromoteVerdict(ok=False, reasons=[msg])
  return PromoteVerdict(ok=True, reasons=[])


def can_promote_profile(
  profile_id: str,
  *,
  oos_from: str,
  holdout_report: Report | None = None,
  require_holdout: bool = True,
) -> PromoteVerdict:
  """Promote only after leakage-safe OOS and optional hold-out evidence."""
  reasons: list[str] = []
  try:
    assert_no_leakage(profile_id, oos_from, require_trained_to=True)
  except LeakageError as exc:
    reasons.append(str(exc))

  if require_holdout:
    if holdout_report is None or not holdout_report.holdout_forward:
      reasons.append(
        f"Hold-out >= {MIN_HOLDOUT_MONTHS_FOR_PROMOTE} months required before promote."
      )
    else:
      months = int(holdout_report.holdout_forward.get("months") or 0)
      if months < MIN_HOLDOUT_MONTHS_FOR_PROMOTE:
        reasons.append(
          f"Hold-out months={months} < required {MIN_HOLDOUT_MONTHS_FOR_PROMOTE}."
        )
      metrics = holdout_report.holdout_forward.get("metrics") or {}
      if float(metrics.get("total_r") or 0) <= 0:
        reasons.append("Hold-out total_r <= 0 — do not promote.")

  ok = len(reasons) == 0
  if ok:
    log.info("Promote OK for profile=%s oos_from=%s", profile_id, oos_from)
  else:
    log.warning("Promote blocked profile=%s: %s", profile_id, "; ".join(reasons))
  return PromoteVerdict(ok=ok, reasons=reasons)
