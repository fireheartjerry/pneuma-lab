"""Durable, restartable controller state for the real production path.

No AWS SDK is imported here.  Provider submission is an outer integration
concern; this state machine is the safety boundary that makes a provider
adapter idempotent and preserves successful submission when observation fails.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import stat
from typing import Any, Protocol, cast

from .errors import CloudManifestError
from .manifests import validate_production_controller_state
from .production_run import canonical_bytes


RECORD_KIND = "cloud_production_controller_state"
SCHEMA_VERSION = "0.1.0"
_ZERO = "0" * 64
_TERMINAL = frozenset({"teardown_complete"})
_ALLOWED: dict[str | None, frozenset[str]] = {
    None: frozenset({"prepared"}),
    "prepared": frozenset({"submitting", "teardown_started"}),
    "submitting": frozenset({"submitted", "observation_error", "teardown_started"}),
    "submitted": frozenset({"observing", "observation_error", "teardown_started"}),
    "observing": frozenset({"observing", "observation_error", "workload_terminal", "teardown_started"}),
    "observation_error": frozenset({"observing", "observation_error", "teardown_started"}),
    "workload_terminal": frozenset({"observing", "teardown_started"}),
    "teardown_started": frozenset({"teardown_complete", "teardown_failed"}),
    "teardown_failed": frozenset({"teardown_started"}),
    "teardown_complete": frozenset(),
}


def _digest(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _text(value: object, *, field: str) -> str:
    if type(value) is not str or not value:
        raise CloudManifestError(f"production controller {field} must be non-empty text")
    return cast(str, value)


@dataclass(frozen=True, slots=True)
class ProductionControllerSnapshot:
    action_id: str
    run_spec_sha256: str
    binding_sha256: str
    phase: str
    sequence: int
    parent_job_id: str | None
    child_job_ids: tuple[str, ...]
    events: tuple[Mapping[str, Any], ...]
    state_sha256: str

    @property
    def terminal(self) -> bool:
        return self.phase in _TERMINAL


@dataclass(frozen=True, slots=True)
class ProductionSubmission:
    """Provider identity returned by one idempotent production submission."""

    parent_job_id: str
    child_job_ids: tuple[str, ...]


class ProductionJobProvider(Protocol):
    """The narrow provider adapter required by the durable controller.

    A provider implementation must make ``client_token`` idempotent.  This
    contract is what closes the crash window between a successful provider
    submit and the controller's durable ``submitted`` event without requiring
    this module to import an AWS SDK or mutate cloud state.
    """

    def submit(
        self,
        *,
        client_token: str,
        allocation: Mapping[str, Sequence[str]],
    ) -> ProductionSubmission: ...

    def observe(self, submission: ProductionSubmission) -> Mapping[str, Any]: ...

    def teardown(self, submission: ProductionSubmission | None) -> Mapping[str, Any] | None: ...


class ProductionOrchestrator:
    """Provider-neutral controller for the real model/benchmark workload.

    It owns allocation and lifecycle ordering, while a separately injected
    provider owns network calls.  Local tests can use a fake provider; the
    qualification fixture cannot satisfy this interface because it has no
    production run specification or real adapters.
    """

    def __init__(
        self,
        store: ProductionStateStore,
        *,
        action_id: str,
        run_spec_sha256: str,
        allocation: Mapping[str, Sequence[str]],
    ) -> None:
        if store.action_id != action_id or store.run_spec_sha256 != run_spec_sha256:
            raise CloudManifestError("production orchestrator store identity differs")
        if set(allocation) != {"worker-0", "worker-1"}:
            raise CloudManifestError("production allocation must cover both canonical workers")
        normalized: dict[str, tuple[str, ...]] = {}
        all_work: list[str] = []
        for worker_id, work_ids in allocation.items():
            if isinstance(work_ids, (str, bytes)):
                raise CloudManifestError("production allocation work IDs must be sequences")
            values = tuple(_text(value, field="work_id") for value in work_ids)
            if len(set(values)) != len(values):
                raise CloudManifestError("production allocation contains duplicate work IDs")
            normalized[worker_id] = values
            all_work.extend(values)
        if len(set(all_work)) != len(all_work):
            raise CloudManifestError("production allocation overlaps worker partitions")
        self.store = store
        self.action_id = action_id
        self.run_spec_sha256 = run_spec_sha256
        self.allocation = normalized
        # EC2 ClientToken is limited to 64 characters.  Keep the stable
        # provider namespace while retaining enough run-spec entropy for
        # idempotent restart reconciliation.
        self.client_token = f"pneuma-production-{run_spec_sha256[:46]}"

    def prepare(self) -> ProductionControllerSnapshot:
        if self.store.exists:
            snapshot = self.store.snapshot()
            first_payload = snapshot.events[0].get("payload")
            expected_payload = {
                "allocation": {worker: list(values) for worker, values in self.allocation.items()},
                "client_token": self.client_token,
            }
            if first_payload != expected_payload:
                raise CloudManifestError("production controller allocation/token differs on restart")
            return snapshot
        return self.store.prepare(
            {
                "allocation": {worker: list(values) for worker, values in self.allocation.items()},
                "client_token": self.client_token,
            }
        )

    def submit(self, provider: ProductionJobProvider) -> ProductionControllerSnapshot:
        current = self.prepare()
        if current.parent_job_id is not None:
            return current
        submission = provider.submit(
            client_token=self.client_token,
            allocation=self.allocation,
        )
        if not isinstance(submission, ProductionSubmission):
            raise CloudManifestError("production provider returned an invalid submission identity")
        return self.store.submit_once(
            parent_job_id=submission.parent_job_id,
            child_job_ids=submission.child_job_ids,
        )

    def observe(self, provider: ProductionJobProvider) -> ProductionControllerSnapshot:
        current = self.store.snapshot()
        if current.phase == "workload_terminal":
            return current
        submission = self._submission(current)
        try:
            status = provider.observe(submission)
            if not isinstance(status, Mapping) or type(status.get("terminal")) is not bool:
                raise CloudManifestError("production provider observation lacks terminal boolean")
            payload = {"status_sha256": _digest(dict(status))}
            return self.store.record_observation(
                terminal=cast(bool, status["terminal"]),
                payload=payload,
            )
        except Exception as exc:
            self.store.record_observation_error(
                detail_sha256=hashlib.sha256(type(exc).__name__.encode("utf-8")).hexdigest()
            )
            raise

    def teardown(self, provider: ProductionJobProvider) -> ProductionControllerSnapshot:
        current = self.store.snapshot()
        if current.phase == "teardown_complete":
            return current
        submission = self._submission(current) if current.parent_job_id is not None else None
        try:
            receipt = provider.teardown(submission)
            payload = {} if receipt is None else {"teardown_sha256": _digest(dict(receipt))}
            return self.store.teardown(success=True, payload=payload)
        except Exception as exc:
            self.store.teardown(
                success=False,
                payload={"detail_sha256": hashlib.sha256(type(exc).__name__.encode("utf-8")).hexdigest()},
            )
            raise

    @staticmethod
    def _submission(snapshot: ProductionControllerSnapshot) -> ProductionSubmission:
        if snapshot.parent_job_id is None or not snapshot.child_job_ids:
            raise CloudManifestError("production controller has no durable submission identity")
        return ProductionSubmission(snapshot.parent_job_id, snapshot.child_job_ids)


class ProductionStateStore:
    """Mode-600 atomic append-only state for exactly one production action."""

    def __init__(self, path: Path | None, *, action_id: str, run_spec_sha256: str, binding: Mapping[str, Any]) -> None:
        if path is not None and not isinstance(path, Path):
            raise CloudManifestError("production controller state path must be pathlib.Path")
        self.path = path
        self.action_id = _text(action_id, field="action_id")
        if len(run_spec_sha256) != 64 or any(char not in "0123456789abcdef" for char in run_spec_sha256):
            raise CloudManifestError("production controller run_spec_sha256 is invalid")
        self.run_spec_sha256 = run_spec_sha256
        self.binding = json.loads(json.dumps(binding, ensure_ascii=False, allow_nan=False))
        if not isinstance(self.binding, dict) or self.binding.get("action_id") != self.action_id:
            raise CloudManifestError("production controller binding action_id differs")
        self.binding_sha256 = _digest(self.binding)
        self._document: dict[str, Any] | None = None
        if path is not None and path.exists():
            self._document = self._read_verified()

    @property
    def exists(self) -> bool:
        return self._document is not None

    def prepare(self, payload: Mapping[str, Any] | None = None) -> ProductionControllerSnapshot:
        if self._document is not None:
            snapshot = self.snapshot()
            if snapshot.phase == "prepared" and not payload:
                return snapshot
            raise CloudManifestError(f"production controller state already exists at {snapshot.phase}")
        return self._append("prepared", dict(payload or {}))

    def submit_once(self, *, parent_job_id: str, child_job_ids: tuple[str, ...]) -> ProductionControllerSnapshot:
        parent = _text(parent_job_id, field="parent_job_id")
        children = tuple(_text(value, field="child_job_id") for value in child_job_ids)
        if not children or len(set(children)) != len(children):
            raise CloudManifestError("production submission requires unique child job IDs")
        current = self.snapshot() if self._document is not None else self.prepare()
        if current.parent_job_id is not None or current.child_job_ids:
            if current.parent_job_id != parent or current.child_job_ids != children:
                raise CloudManifestError("production submission IDs differ from the immutable first submission")
            return current
        self._append("submitting", {"parent_job_id": parent, "child_job_ids": list(children)})
        return self._append("submitted", {"parent_job_id": parent, "child_job_ids": list(children)})

    def record_observation(self, *, terminal: bool, payload: Mapping[str, Any] | None = None) -> ProductionControllerSnapshot:
        current = self.snapshot()
        if current.parent_job_id is None or not current.child_job_ids:
            raise CloudManifestError("cannot observe before one immutable submission")
        body = {"parent_job_id": current.parent_job_id, "child_job_ids": list(current.child_job_ids), **dict(payload or {})}
        self._append("observing", body)
        if terminal:
            return self._append("workload_terminal", body)
        return self.snapshot()

    def record_observation_error(self, *, detail_sha256: str) -> ProductionControllerSnapshot:
        if len(detail_sha256) != 64 or any(char not in "0123456789abcdef" for char in detail_sha256):
            raise CloudManifestError("observation error digest is invalid")
        current = self.snapshot()
        if current.parent_job_id is None or not current.child_job_ids:
            raise CloudManifestError("cannot record observation error before submission")
        return self._append(
            "observation_error",
            {
                "parent_job_id": current.parent_job_id,
                "child_job_ids": list(current.child_job_ids),
                "detail_sha256": detail_sha256,
            },
        )

    def teardown(self, *, success: bool, payload: Mapping[str, Any] | None = None) -> ProductionControllerSnapshot:
        current = self.snapshot()
        if current.phase == "teardown_complete":
            return current
        self._append("teardown_started", {"parent_job_id": current.parent_job_id, "child_job_ids": list(current.child_job_ids), **dict(payload or {})})
        return self._append("teardown_complete" if success else "teardown_failed", dict(payload or {}))

    def snapshot(self) -> ProductionControllerSnapshot:
        if self._document is None:
            raise CloudManifestError("production controller state has not been initialized")
        events = tuple(cast(tuple[Mapping[str, Any], ...], tuple(self._document["events"])))
        parent: str | None = None
        children: tuple[str, ...] = ()
        for event in events:
            payload = event.get("payload")
            if not isinstance(payload, Mapping):
                continue
            if isinstance(payload.get("parent_job_id"), str):
                parent = cast(str, payload["parent_job_id"])
            candidate = payload.get("child_job_ids")
            if isinstance(candidate, list) and all(isinstance(value, str) and value for value in candidate):
                children = tuple(cast(list[str], candidate))
        latest = events[-1]
        return ProductionControllerSnapshot(
            self.action_id,
            self.run_spec_sha256,
            self.binding_sha256,
            cast(str, latest["phase"]),
            cast(int, latest["sequence"]),
            parent,
            children,
            events,
            cast(str, self._document["state_sha256"]),
        )

    def _append(self, phase: str, payload: dict[str, Any]) -> ProductionControllerSnapshot:
        if phase not in _ALLOWED:
            raise CloudManifestError(f"unknown production controller phase: {phase}")
        current = self.snapshot().phase if self._document is not None else None
        if phase not in _ALLOWED[current]:
            if self._document is not None and phase == current and self._document["events"][-1].get("payload") == payload:
                return self.snapshot()
            raise CloudManifestError(f"invalid production controller transition {current!r} -> {phase!r}")
        sequence = 1 if self._document is None else len(self._document["events"]) + 1
        previous = _ZERO if self._document is None else cast(str, self._document["events"][-1]["event_sha256"])
        body = {"sequence": sequence, "phase": phase, "payload": payload, "previous_event_sha256": previous}
        event = {**body, "event_sha256": _digest(body)}
        if self._document is None:
            document: dict[str, Any] = {
                "record_kind": RECORD_KIND,
                "schema_version": SCHEMA_VERSION,
                "action_id": self.action_id,
                "run_spec_sha256": self.run_spec_sha256,
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
        self._validate_events(cast(list[dict[str, Any]], document["events"]))
        validate_production_controller_state(document)
        self._atomic_write(document)
        self._document = document
        return self.snapshot()

    def _read_verified(self) -> dict[str, Any]:
        if self.path is None or self.path.is_symlink() or not self.path.is_file():
            raise CloudManifestError("production controller state must be one regular file")
        # Windows does not expose POSIX group/other mode bits through stat;
        # ACL enforcement is handled by the local account. Keep the strict
        # 0600 invariant on POSIX where the bits are meaningful.
        if os.name != "nt" and stat.S_IMODE(self.path.stat().st_mode) & 0o077:
            raise CloudManifestError("production controller state must be mode 600")
        try:
            raw = self.path.read_bytes()
            document = json.loads(raw.decode("utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise CloudManifestError("production controller state is not valid JSON") from exc
        if canonical_bytes(document) != raw or not isinstance(document, dict):
            raise CloudManifestError("production controller state must use canonical JSON bytes")
        if document.get("record_kind") != RECORD_KIND or document.get("schema_version") != SCHEMA_VERSION:
            raise CloudManifestError("production controller state identity differs")
        if document.get("action_id") != self.action_id or document.get("run_spec_sha256") != self.run_spec_sha256:
            raise CloudManifestError("production controller immutable identity differs")
        if document.get("binding") != self.binding or document.get("binding_sha256") != self.binding_sha256:
            raise CloudManifestError("production controller binding differs")
        events = document.get("events")
        if not isinstance(events, list) or not events:
            raise CloudManifestError("production controller state has no events")
        self._validate_events(cast(list[dict[str, Any]], events))
        validate_production_controller_state(document)
        unsigned = dict(document)
        observed = unsigned.pop("state_sha256", None)
        if observed != _digest(unsigned):
            raise CloudManifestError("production controller state digest differs")
        return document

    @staticmethod
    def _validate_events(events: list[dict[str, Any]]) -> None:
        previous = _ZERO
        last_sequence = 0
        current: str | None = None
        parent: str | None = None
        children: tuple[str, ...] = ()
        for event in events:
            if not isinstance(event, dict) or event.get("sequence") != last_sequence + 1:
                raise CloudManifestError("production controller event sequence is not contiguous")
            phase = event.get("phase")
            if phase not in _ALLOWED or phase not in _ALLOWED[current]:
                raise CloudManifestError("production controller event transition is invalid")
            if event.get("previous_event_sha256") != previous or event.get("event_sha256") != _digest({key: value for key, value in event.items() if key != "event_sha256"}):
                raise CloudManifestError("production controller event hash chain differs")
            payload = event.get("payload")
            if not isinstance(payload, dict):
                raise CloudManifestError("production controller event payload is not an object")
            candidate_parent = payload.get("parent_job_id")
            candidate_children = payload.get("child_job_ids")
            if candidate_parent is not None:
                if not isinstance(candidate_parent, str) or not candidate_parent or (parent is not None and parent != candidate_parent):
                    raise CloudManifestError("production controller parent job identity changed")
                parent = candidate_parent
            if candidate_children is not None:
                if not isinstance(candidate_children, list) or not candidate_children or not all(isinstance(value, str) and value for value in candidate_children):
                    raise CloudManifestError("production controller child job IDs are invalid")
                observed_children = tuple(cast(list[str], candidate_children))
                if len(set(observed_children)) != len(observed_children) or (children and children != observed_children):
                    raise CloudManifestError("production controller child job identity changed")
                children = observed_children
            previous = cast(str, event["event_sha256"])
            last_sequence = cast(int, event["sequence"])
            current = cast(str, phase)

    def _atomic_write(self, document: Mapping[str, Any]) -> None:
        if self.path is None:
            return
        validate_production_controller_state(document)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_name(f".{self.path.name}.tmp")
        temporary.write_bytes(canonical_bytes(document))
        temporary.chmod(0o600)
        temporary.replace(self.path)
        self.path.chmod(0o600)


__all__ = [
    "ProductionControllerSnapshot",
    "ProductionJobProvider",
    "ProductionOrchestrator",
    "ProductionStateStore",
    "ProductionSubmission",
]
