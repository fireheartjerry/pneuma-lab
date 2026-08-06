"""Atomic hash-chained campaign state for one immutable experiment version."""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
from typing import Any, Mapping, cast

from .records import canonical_bytes, digest_record


ZERO_SHA256 = "0" * 64
_ALLOWED: dict[str | None, frozenset[str]] = {
    None: frozenset({"draft"}),
    "draft": frozenset({"classified"}),
    "classified": frozenset({"prepared"}),
    "prepared": frozenset({"reserved", "teardown_started"}),
    "reserved": frozenset({"submitting", "teardown_started"}),
    "submitting": frozenset({"submitted", "observation_error", "teardown_started"}),
    "submitted": frozenset(
        {
            "observing",
            "observation_error",
            "workload_terminal",
            "workload_failed",
            "teardown_started",
        }
    ),
    "observing": frozenset(
        {
            "observing",
            "observation_error",
            "workload_terminal",
            "workload_failed",
            "teardown_started",
        }
    ),
    "observation_error": frozenset(
        {
            "observing",
            "observation_error",
            "workload_terminal",
            "workload_failed",
            "teardown_started",
        }
    ),
    "workload_terminal": frozenset({"outputs_sealed", "teardown_started"}),
    "workload_failed": frozenset({"reviewed", "teardown_started"}),
    "outputs_sealed": frozenset({"analysed", "teardown_started"}),
    "analysed": frozenset({"reviewed", "teardown_started"}),
    "reviewed": frozenset({"decided", "teardown_started"}),
    "decided": frozenset({"teardown_started"}),
    "teardown_started": frozenset({"teardown_complete", "teardown_failed"}),
    "teardown_failed": frozenset({"teardown_complete", "teardown_failed"}),
    "teardown_complete": frozenset(),
}


class StateError(ValueError):
    """Campaign state is corrupt or an illegal transition was requested."""


@dataclass(frozen=True, slots=True)
class SubmissionIdentity:
    parent_job_id: str
    child_job_ids: tuple[str, ...]
    receipt_sha256: str


@dataclass(frozen=True, slots=True)
class CampaignSnapshot:
    campaign_id: str
    version_id: str
    phase: str
    sequence: int
    events: tuple[Mapping[str, Any], ...]
    state_sha256: str
    submission: SubmissionIdentity | None
    decision_code: str | None


class CampaignStateStore:
    def __init__(self, path: Path, *, campaign_id: str, version_id: str) -> None:
        self.path = path
        self.campaign_id = campaign_id
        self.version_id = version_id
        self._document: dict[str, Any]
        if path.exists():
            self._document = self._read_verified()
        else:
            self._document = {
                "record_kind": "rapid_campaign_state",
                "schema_version": "0.1.0",
                "campaign_id": campaign_id,
                "version_id": version_id,
                "events": [],
                "state_sha256": ZERO_SHA256,
            }
            self._append("draft", {})

    def snapshot(self) -> CampaignSnapshot:
        events = tuple(cast(list[Mapping[str, Any]], self._document["events"]))
        last = events[-1]
        submission = None
        decision_code = None
        for event in events:
            if event["phase"] == "submitted":
                body = cast(Mapping[str, Any], event["payload"])
                submission = SubmissionIdentity(
                    parent_job_id=body["parent_job_id"],
                    child_job_ids=tuple(body["child_job_ids"]),
                    receipt_sha256=body["receipt_sha256"],
                )
            if event["phase"] == "decided":
                decision_code = cast(Mapping[str, Any], event["payload"])[
                    "decision_code"
                ]
        return CampaignSnapshot(
            campaign_id=self.campaign_id,
            version_id=self.version_id,
            phase=cast(str, last["phase"]),
            sequence=cast(int, last["sequence"]),
            events=events,
            state_sha256=cast(str, self._document["state_sha256"]),
            submission=submission,
            decision_code=cast(str | None, decision_code),
        )

    def append(self, phase: str, payload: Mapping[str, Any]) -> CampaignSnapshot:
        return self._append(phase, payload)

    def record_submission(
        self,
        *,
        parent_job_id: str,
        child_job_ids: tuple[str, ...],
        receipt_sha256: str,
    ) -> SubmissionIdentity:
        current = self.snapshot()
        candidate = SubmissionIdentity(parent_job_id, child_job_ids, receipt_sha256)
        if current.submission is not None:
            if current.submission != candidate:
                raise StateError(
                    "submission identity differs from immutable first submission"
                )
            return current.submission
        if current.phase != "submitting":
            raise StateError("submission may only be recorded from submitting")
        self._append(
            "submitted",
            {
                "parent_job_id": parent_job_id,
                "child_job_ids": list(child_job_ids),
                "receipt_sha256": receipt_sha256,
            },
        )
        return candidate

    def _append(self, phase: str, payload: Mapping[str, Any]) -> CampaignSnapshot:
        events = cast(list[dict[str, Any]], self._document["events"])
        previous_phase = cast(str | None, events[-1]["phase"] if events else None)
        if phase not in _ALLOWED.get(previous_phase, frozenset()):
            raise StateError(
                f"illegal campaign transition {previous_phase!r} -> {phase!r}"
            )
        previous = cast(str, events[-1]["event_sha256"] if events else ZERO_SHA256)
        event: dict[str, Any] = {
            "sequence": len(events) + 1,
            "phase": phase,
            "payload": json.loads(
                json.dumps(payload, ensure_ascii=False, allow_nan=False)
            ),
            "previous_event_sha256": previous,
        }
        event["event_sha256"] = digest_record(event)
        events.append(event)
        state_body = {
            key: value for key, value in self._document.items() if key != "state_sha256"
        }
        self._document["state_sha256"] = digest_record(state_body)
        self._write()
        return self.snapshot()

    def _read_verified(self) -> dict[str, Any]:
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise StateError("campaign state is unreadable") from exc
        required = {
            "record_kind",
            "schema_version",
            "campaign_id",
            "version_id",
            "events",
            "state_sha256",
        }
        if not isinstance(value, dict) or set(value) != required:
            raise StateError("campaign state fields differ")
        if (
            value["record_kind"] != "rapid_campaign_state"
            or value["schema_version"] != "0.1.0"
        ):
            raise StateError("campaign state kind/version differs")
        if (
            value["campaign_id"] != self.campaign_id
            or value["version_id"] != self.version_id
        ):
            raise StateError("campaign state identity differs")
        events = value["events"]
        if not isinstance(events, list) or not events:
            raise StateError("campaign state lacks events")
        previous = ZERO_SHA256
        previous_phase: str | None = None
        for index, event in enumerate(events, start=1):
            if not isinstance(event, dict) or set(event) != {
                "sequence",
                "phase",
                "payload",
                "previous_event_sha256",
                "event_sha256",
            }:
                raise StateError("campaign event fields differ")
            if event["sequence"] != index or event["previous_event_sha256"] != previous:
                raise StateError("campaign event chain differs")
            if event["phase"] not in _ALLOWED.get(previous_phase, frozenset()):
                raise StateError("campaign event transition differs")
            expected = digest_record(
                {key: item for key, item in event.items() if key != "event_sha256"}
            )
            if event["event_sha256"] != expected:
                raise StateError("campaign event digest differs")
            previous = event["event_sha256"]
            previous_phase = event["phase"]
        expected_state = digest_record(
            {key: item for key, item in value.items() if key != "state_sha256"}
        )
        if value["state_sha256"] != expected_state:
            raise StateError("campaign state digest differs")
        return value

    def _write(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_name(f".{self.path.name}.tmp")
        data = canonical_bytes(self._document)
        with temporary.open("wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.chmod(temporary, 0o600)
        except OSError:
            pass
        os.replace(temporary, self.path)
