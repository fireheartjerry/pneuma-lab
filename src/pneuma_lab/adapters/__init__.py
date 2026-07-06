"""Adapters — translate external records into Pneuma Lab frames (Phase 1 seam).

Planned adapters (NOT yet implemented — see migration/MIGRATION_REPORT.md):

    - from_9to5_run_events : map human_nature/run_events.py event logs -> WorldFrame
    event streams and the InstinctSignal / PsycheStateFrame output frames.
    - from_manager_data    : map manager-data ``manager_event_v1`` / decision-point
    rows -> GovernanceFrame + InterventionFrame candidates (operator-preference
    stream). Treated as POSSIBLE FUTURE operator-preference data only; never the
    base mind, never overfit to.

Nothing here imports from 9to5 or manager-data. Adapters consume already-exported
records (JSONL), keeping Pneuma Lab standalone.
"""

from __future__ import annotations

__all__: list[str] = []
