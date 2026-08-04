"""Durable, restartable control state for the bounded AWS qualification.

The controller state is an append-only event history stored in an atomically
replaced, mode-600 JSON document.  Provider observations are deliberately not
treated as teardown commands: a process may stop after submission and resume
from the persisted parent/child IDs without submitting a second Batch array.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import stat
import tempfile
from typing import Any

from .authorization_keys import canonical_bytes
from .errors import CloudManifestError


CONTROLLER_STATE_RECORD_KIND = "cloud_qualification_controller_state"
CONTROLLER_STATE_SCHEMA_VERSION = "0.1.0"

_TERMINAL_PHASES = frozenset({"teardown_complete"})
_ALLOWED_TRANSITIONS: dict[str | None, frozenset[str]] = {
    None: frozenset({"prepared"}),
    "prepared": frozenset({"applying", "ready", "teardown_started"}),
    "applying": frozenset({"applied", "teardown_started"}),
    "applied": frozenset({"ready", "teardown_started"}),
    "ready": frozenset({"submitting", "teardown_started"}),
    "submitting": frozenset({"submitted", "observation_pending", "teardown_started"}),
    "submitted": frozenset({"launch_reconciled", "observation_pending", "teardown_started"}),
    "launch_reconciled": frozenset({"observing", "observation_pending", "teardown_started"}),
    "observing": frozenset({
        "observation_pending",
        "admission_reconciled",
        "workload_terminal",
        "teardown_started",
    }),
    "observation_pending": frozenset({"launch_reconciled", "observing", "teardown_started"}),
    "admission_reconciled": frozenset({"observing", "artifact_reconciled", "teardown_started"}),
    "artifact_reconciled": frozenset({"observing", "recovering", "teardown_started"}),
    "recovering": frozenset({"observing", "recovery_reconciled", "recovery_pending", "teardown_started"}),
    "recovery_pending": frozenset({"recovering", "teardown_started"}),
    "recovery_reconciled": frozenset({"observing", "teardown_started"}),
    "workload_terminal": frozenset({"observing", "teardown_started"}),
    "teardown_started": frozenset({"teardown_complete", "teardown_failed"}),
    "teardown_complete": frozenset(),
    # A failed teardown is recoverable control state, not a terminal outcome.
    # The next process may retry the idempotent disable/destroy/absence proof.
    "teardown_failed": frozenset({"teardown_started"}),
}


def _digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _require_string(value: Any, *, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise CloudManifestError(f"controller state {field} must be a nonempty string")
    return value


@dataclass(frozen=True, slots=True)
class ControllerSnapshot:
    """The verified state derived from an immutable event history."""

    action_id: str
    binding_sha256: str
    phase: str
    sequence: int
    parent_job_id: str | None
    child_job_ids: tuple[str, ...]
    events: tuple[Mapping[str, Any], ...]
    state_sha256: str

    @property
    def terminal(self) -> bool:
        return self.phase in _TERMINAL_PHASES

    @property
    def resume_count(self) -> int:
        return sum(
            1
            for event in self.events
            if isinstance(event.get("payload"), Mapping)
            and event["payload"].get("resumed") is True
        )

    def summary(self) -> dict[str, Any]:
        return {
            "state_sha256": self.state_sha256,
            "event_count": self.sequence,
            "terminal_phase": self.phase,
            "resume_count": self.resume_count,
            "parent_job_id_sha256": (
                hashlib.sha256(self.parent_job_id.encode("utf-8")).hexdigest()
                if self.parent_job_id
                else None
            ),
            "child_job_id_sha256": [
                hashlib.sha256(job_id.encode("utf-8")).hexdigest()
                for job_id in self.child_job_ids
            ],
        }


class QualificationStateStore:
    """Atomic append-only state store for one action and immutable binding."""

    def __init__(
        self,
        path: Path | None,
        *,
        action_id: str,
        binding: Mapping[str, Any],
    ) -> None:
        if path is not None and not isinstance(path, Path):
            raise CloudManifestError("controller state path must be a pathlib.Path")
        self.path = path
        self.action_id = _require_string(action_id, field="action_id")
        self.binding = dict(binding)
        if self.binding.get("action_id") != self.action_id:
            raise CloudManifestError("controller state binding action differs")
        self.binding_sha256 = _digest(self.binding)
        self._document: dict[str, Any] | None = None
        if path is not None and path.exists():
            self._document = self._read_verified()

    @property
    def exists(self) -> bool:
        return self._document is not None

    def start(self, payload: Mapping[str, Any] | None = None) -> ControllerSnapshot:
        if self._document is not None:
            snapshot = self.snapshot()
            if snapshot.phase == "prepared" and not payload:
                return snapshot
            raise CloudManifestError(
                f"controller state already exists at phase {snapshot.phase}"
            )
        return self._append("prepared", dict(payload or {}))

    def append(
        self,
        phase: str,
        payload: Mapping[str, Any] | None = None,
    ) -> ControllerSnapshot:
        return self._append(phase, dict(payload or {}))

    def snapshot(self) -> ControllerSnapshot:
        if self._document is None:
            raise CloudManifestError("controller state has not been initialized")
        events = tuple(self._document["events"])
        latest = events[-1]
        parent_job_id: str | None = None
        child_job_ids: tuple[str, ...] = ()
        for event in events:
            event_payload = event.get("payload")
            if not isinstance(event_payload, Mapping):
                continue
            candidate_parent = event_payload.get("parent_job_id")
            if isinstance(candidate_parent, str) and candidate_parent:
                parent_job_id = candidate_parent
            candidate_children = event_payload.get("child_job_ids")
            if isinstance(candidate_children, list) and all(
                isinstance(value, str) and value for value in candidate_children
            ):
                child_job_ids = tuple(candidate_children)
        return ControllerSnapshot(
            action_id=self.action_id,
            binding_sha256=self.binding_sha256,
            phase=latest["phase"],
            sequence=latest["sequence"],
            parent_job_id=parent_job_id,
            child_job_ids=child_job_ids,
            events=events,
            state_sha256=self._document["state_sha256"],
        )

    def _append(self, phase: str, payload: dict[str, Any]) -> ControllerSnapshot:
        if phase not in _ALLOWED_TRANSITIONS:
            raise CloudManifestError(f"unknown qualification controller phase: {phase}")
        current = self.snapshot().phase if self._document is not None else None
        allowed = _ALLOWED_TRANSITIONS[current]
        if phase not in allowed:
            if (
                self._document is not None
                and phase == current
                and self._document["events"][-1].get("payload") == payload
            ):
                return self.snapshot()
            if (
                self._document is None
                or phase != current
                or payload.get("resumed") is not True
            ):
                raise CloudManifestError(
                    f"invalid qualification controller transition {current!r} -> {phase!r}"
                )
        sequence = 1 if self._document is None else len(self._document["events"]) + 1
        previous = "0" * 64 if self._document is None else self._document["events"][-1]["event_sha256"]
        body = {
            "sequence": sequence,
            "phase": phase,
            "payload": payload,
            "previous_event_sha256": previous,
        }
        event = dict(body)
        event["event_sha256"] = _digest(body)
        if self._document is None:
            document = {
                "record_kind": CONTROLLER_STATE_RECORD_KIND,
                "schema_version": CONTROLLER_STATE_SCHEMA_VERSION,
                "action_id": self.action_id,
                "binding": self.binding,
                "binding_sha256": self.binding_sha256,
                "events": [event],
            }
        else:
            document = dict(self._document)
            document["events"] = [*self._document["events"], event]
        unsigned = dict(document)
        unsigned.pop("state_sha256", None)
        document["state_sha256"] = _digest(unsigned)
        self._validate_identity_history(document["events"])
        self._atomic_write(document)
        self._document = document
        return self.snapshot()

    def _read_verified(self) -> dict[str, Any]:
        if self.path is None:
            raise CloudManifestError("in-memory controller state has no file to read")
        if self.path.is_symlink() or not self.path.is_file():
            raise CloudManifestError("controller state path must be a regular file")
        mode = stat.S_IMODE(self.path.stat().st_mode)
        if mode & 0o077:
            raise CloudManifestError("controller state must be mode 600")
        try:
            document = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise CloudManifestError("controller state is not valid JSON") from exc
        if not isinstance(document, dict):
            raise CloudManifestError("controller state must be a JSON object")
        if document.get("record_kind") != CONTROLLER_STATE_RECORD_KIND:
            raise CloudManifestError("controller state has the wrong record kind")
        if document.get("schema_version") != CONTROLLER_STATE_SCHEMA_VERSION:
            raise CloudManifestError("controller state has the wrong schema version")
        if document.get("action_id") != self.action_id:
            raise CloudManifestError("controller state action id differs")
        if document.get("binding") != self.binding:
            raise CloudManifestError("controller state immutable binding differs")
        if document.get("binding_sha256") != self.binding_sha256:
            raise CloudManifestError("controller state binding digest differs")
        events = document.get("events")
        if not isinstance(events, list) or not events:
            raise CloudManifestError("controller state has no event history")
        previous = "0" * 64
        last_sequence = 0
        for event in events:
            if not isinstance(event, dict):
                raise CloudManifestError("controller state event is not an object")
            sequence = event.get("sequence")
            if sequence != last_sequence + 1:
                raise CloudManifestError("controller state event sequence is not contiguous")
            phase = event.get("phase")
            if not isinstance(phase, str) or phase not in _ALLOWED_TRANSITIONS:
                raise CloudManifestError("controller state event has an unknown phase")
            if event.get("previous_event_sha256") != previous:
                raise CloudManifestError("controller state event hash chain differs")
            event_sha = event.get("event_sha256")
            body = dict(event)
            body.pop("event_sha256", None)
            if event_sha != _digest(body):
                raise CloudManifestError("controller state event digest differs")
            previous = event_sha
            last_sequence = sequence
        unsigned = dict(document)
        actual_state_sha = unsigned.pop("state_sha256", None)
        if actual_state_sha != _digest(unsigned):
            raise CloudManifestError("controller state digest differs")
        self._validate_transitions(events)
        self._validate_identity_history(events)
        return document

    @staticmethod
    def _validate_transitions(events: list[dict[str, Any]]) -> None:
        current: str | None = None
        for event in events:
            phase = event["phase"]
            payload = event.get("payload")
            same_phase_resume = (
                phase == current
                and isinstance(payload, Mapping)
                and payload.get("resumed") is True
            )
            if phase not in _ALLOWED_TRANSITIONS[current] and not same_phase_resume:
                raise CloudManifestError(
                    f"controller state history contains invalid transition {current!r} -> {phase!r}"
                )
            current = phase

    @staticmethod
    def _validate_identity_history(events: list[dict[str, Any]]) -> None:
        parent_job_id: str | None = None
        child_job_ids: tuple[str, ...] | None = None
        for event in events:
            payload = event.get("payload")
            if not isinstance(payload, Mapping):
                continue
            candidate_parent = payload.get("parent_job_id")
            if candidate_parent is not None:
                if not isinstance(candidate_parent, str) or not candidate_parent:
                    raise CloudManifestError("controller state parent job id is invalid")
                if parent_job_id is not None and candidate_parent != parent_job_id:
                    raise CloudManifestError("controller state parent job id changed")
                parent_job_id = candidate_parent
            candidate_children = payload.get("child_job_ids")
            if candidate_children is not None:
                if not isinstance(candidate_children, list) or not all(
                    isinstance(value, str) and value for value in candidate_children
                ):
                    raise CloudManifestError("controller state child job ids are invalid")
                if not candidate_children:
                    continue
                normalized_children = tuple(candidate_children)
                if child_job_ids is not None and normalized_children != child_job_ids:
                    raise CloudManifestError("controller state child job ids changed")
                child_job_ids = normalized_children

    def _atomic_write(self, document: Mapping[str, Any]) -> None:
        if self.path is None:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{self.path.name}.", suffix=".tmp", dir=self.path.parent
        )
        temporary = Path(temporary_name)
        try:
            os.fchmod(descriptor, 0o600)
            data = (json.dumps(document, indent=2, sort_keys=True) + "\n").encode("utf-8")
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, self.path)
            try:
                directory = os.open(self.path.parent, os.O_RDONLY)
            except OSError:
                return
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        finally:
            temporary.unlink(missing_ok=True)


class QualificationController:
    """Small lifecycle facade used by the concrete runner and fault tests."""

    def __init__(self, store: QualificationStateStore) -> None:
        self.store = store

    @property
    def snapshot(self) -> ControllerSnapshot:
        return self.store.snapshot()

    def start_or_resume(self, payload: Mapping[str, Any] | None = None) -> ControllerSnapshot:
        if not self.store.exists:
            return self.store.start(payload)
        snapshot = self.store.snapshot()
        if snapshot.terminal:
            raise CloudManifestError(
                f"qualification controller state is already terminal: {snapshot.phase}"
            )
        previous_payload = snapshot.events[-1].get("payload")
        resume_payload = dict(previous_payload) if isinstance(previous_payload, Mapping) else {}
        resume_payload.update({
            "resumed": True,
            "resume_from": snapshot.phase,
            "parent_job_id": snapshot.parent_job_id,
            "child_job_ids": list(snapshot.child_job_ids),
        })
        return self.store.append(snapshot.phase, resume_payload)

    def transition(
        self,
        phase: str,
        payload: Mapping[str, Any] | None = None,
    ) -> ControllerSnapshot:
        return self.store.append(phase, payload)
