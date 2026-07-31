"""Tier-labelled local emulation gates; no network or AWS client support."""

from .errors import CloudManifestError
from .fakes import LocalControlPlane
from .watchdog import require_fresh_watchdog


def exercise_t1_fault_matrix() -> tuple[str, ...]:
    plane = LocalControlPlane()
    plane.submit("one")
    plane.publish("one", b"ok", b"ok")
    try:
        plane.submit("one")
    except CloudManifestError:
        duplicate = "duplicate_delivery_blocked"
    else:
        raise AssertionError("duplicate delivery unexpectedly accepted")
    try:
        require_fresh_watchdog(0, 0, 0, 1)
    except CloudManifestError:
        expiry = "expired_lease_blocked"
    else:
        raise AssertionError("expired lease unexpectedly accepted")
    plane.teardown()
    return ("t1_local_only", duplicate, expiry, "teardown_ordered")
