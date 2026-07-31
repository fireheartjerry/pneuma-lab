"""Independent local watchdog gate; budget alarms are not an enforcement path."""

from .errors import CloudManifestError


def require_fresh_watchdog(lease_expires_at: int, now: int, projected: float, ceiling: float) -> None:
    if lease_expires_at <= now:
        raise CloudManifestError("watchdog lease is stale; no new call permitted")
    if projected > ceiling:
        raise CloudManifestError("watchdog projection overrun; termination required")
