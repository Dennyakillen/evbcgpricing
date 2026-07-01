"""
window.py -- growing-window resolution (single owner of the window default)
============================================================================
resolve_window_end() -> 'YYYY-MM-DD' for the last day of the latest CLOSED
month. The growing window keeps its fixed anchor (WINDOW_ANCHOR); only the
end moves. Orchestrators call this when --end is not given, so no runner
ever carries a stale hardcoded date again (silent date-lock class, LB.50/G7).

WARNING -- re-run vs new window: window_run_id derives from (start, end), so
auto-resolving on a later calendar date yields a NEW run_id and a NEW status
file. To RE-run an existing window (e.g. maj = 2022-07-01..2026-05-31), pass
that window's --end explicitly. Auto-resolve is for FRESH windows only,
after the parquet has been regenerated for the new period (LB.50).

Developer: Jens Palmo (Senior Business Analyst, Evidensia). Author: Claude advisor.
"""
from __future__ import annotations

from datetime import date, timedelta

WINDOW_ANCHOR = "2022-07-01"   # BCG frozen start; growing window keeps this fixed


def resolve_window_end(today: "date | None" = None) -> str:
    """Last day of the latest fully closed month, as 'YYYY-MM-DD'.

    Example: called on 2026-07-01 (or any day in July 2026) -> '2026-06-30'.
    If the DW load for the just-closed month lags, pass --end explicitly.
    """
    t = today or date.today()
    last_closed = t.replace(day=1) - timedelta(days=1)
    return last_closed.isoformat()
