"""Local lease state machine; wraps no scientific producer or cloud SDK."""

from __future__ import annotations

from dataclasses import dataclass

from .errors import CloudManifestError


@dataclass(frozen=True, slots=True)
class Lease:
    assignment_id: str
    owner: str
    expires_at: int
    state: str = "active"


class LocalLeaseStore:
    """Conditional-write fake with one terminal sample per assignment."""

    def __init__(self) -> None:
        self._leases: dict[str, Lease] = {}
        self._terminal: set[str] = set()

    def acquire(self, assignment_id: str, owner: str, now: int, ttl: int) -> Lease:
        if not assignment_id or not owner or ttl <= 0:
            raise CloudManifestError("lease inputs must be nonempty with positive ttl")
        current = self._leases.get(assignment_id)
        if assignment_id in self._terminal:
            raise CloudManifestError("terminal assignment cannot be delivered again")
        if current and current.expires_at > now:
            raise CloudManifestError("conditional lease contention")
        lease = Lease(assignment_id, owner, now + ttl)
        self._leases[assignment_id] = lease
        return lease

    def terminal(self, lease: Lease, now: int, *, restore_matches: bool) -> Lease:
        current = self._leases.get(lease.assignment_id)
        if current != lease or lease.expires_at <= now:
            raise CloudManifestError("stale or expired lease")
        if not restore_matches:
            invalid = Lease(lease.assignment_id, lease.owner, lease.expires_at, "invalid")
            self._leases[lease.assignment_id] = invalid
            self._terminal.add(lease.assignment_id)
            return invalid
        terminal = Lease(lease.assignment_id, lease.owner, lease.expires_at, "terminal")
        self._leases[lease.assignment_id] = terminal
        self._terminal.add(lease.assignment_id)
        return terminal
