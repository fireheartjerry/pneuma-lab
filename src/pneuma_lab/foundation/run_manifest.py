"""Atomic run-state manifests and an append-only run event log."""

from __future__ import annotations

import errno
import json
import os
from pathlib import Path
from typing import Mapping

from pneuma_lab.foundation.artifacts import write_atomic_json


MANIFEST_NAME = "manifest.json"
EVENTS_NAME = "events.jsonl"

_UNSUPPORTED_FSYNC_ERRNOS = frozenset(
    value
    for value in (
        getattr(errno, "EINVAL", None),
        getattr(errno, "ENOSYS", None),
        getattr(errno, "ENOTSUP", None),
    )
    if value is not None
)


class RunManifestError(ValueError):
    """Raised when run state or run events cannot be recorded coherently."""


def _canonical_event_line(event: Mapping) -> bytes:
    try:
        payload = json.dumps(
            dict(event),
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
    except (TypeError, ValueError) as exc:
        raise RunManifestError(f"run event is not canonical JSON: {exc}") from exc
    return (payload + "\n").encode("utf-8")


class RunManifestWriter:
    """Atomically replace ``manifest.json``; append rows to ``events.jsonl``.

    The manifest is the complete current run state and is only ever replaced
    through the atomic publication helpers, so a crash can never leave a
    partial manifest. The event log is additive history: one canonical JSON
    object per line, serialized fully before the append so a rejected event
    never writes a partial row.
    """

    def __init__(self, run_root: Path) -> None:
        self.run_root = Path(run_root)
        self.manifest_path = self.run_root / MANIFEST_NAME
        self.events_path = self.run_root / EVENTS_NAME

    def write_manifest(self, manifest: Mapping) -> Path:
        if not isinstance(manifest, Mapping):
            raise RunManifestError("run manifest must be a mapping")
        self.run_root.mkdir(parents=True, exist_ok=True)
        try:
            write_atomic_json(self.manifest_path, dict(manifest))
        except (TypeError, ValueError) as exc:
            raise RunManifestError(
                f"run manifest is not canonical JSON: {exc}"
            ) from exc
        return self.manifest_path

    def append_event(self, event: Mapping) -> Path:
        if not isinstance(event, Mapping):
            raise RunManifestError("run event must be a mapping")
        line = _canonical_event_line(event)
        self.run_root.mkdir(parents=True, exist_ok=True)
        with self.events_path.open("ab") as stream:
            stream.write(line)
            stream.flush()
            try:
                os.fsync(stream.fileno())
            except OSError as exc:  # pragma: no cover - filesystem specific
                if exc.errno not in _UNSUPPORTED_FSYNC_ERRNOS:
                    raise
        return self.events_path
