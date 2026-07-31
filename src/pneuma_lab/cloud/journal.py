"""Append-only resumable local forensic event records."""

from dataclasses import dataclass

from .errors import CloudManifestError


@dataclass(frozen=True, slots=True)
class JournalEvent:
    sequence: int
    event: str
    binding_sha256: str


def append(events: tuple[JournalEvent, ...], event: JournalEvent) -> tuple[JournalEvent, ...]:
    if event.sequence != len(events) + 1 or any(existing.sequence == event.sequence for existing in events):
        raise CloudManifestError("journal sequence must append exactly once")
    return (*events, event)
