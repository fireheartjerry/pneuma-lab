"""Seal the minimal prospective official-study prelaunch authorities.

The 2026-08-05 amendment replaced the abandoned external ceremony with a
content-addressed, deterministic pre-outcome freeze.  This module implements
that freeze without inventing completed prefixes, packets, or task outcomes:
it seals the exact roster, allocations, packet-construction authority,
task-block execution plan, blinding authority, and frozen analysis source.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
import hashlib
import hmac
import json
from pathlib import Path
from typing import Any

from pneuma_lab.cloud.errors import CloudManifestError


STUDY_ID = "neurips-2026-resampling-null"
ARMS = ("REAL", "SHAM", "NONE", "RESAMPLE")
TREATMENT_TABLE = (
    ("NO_PACKET", "NO_PACKET", "REAL", "SHAM"),
    ("NO_PACKET", "NO_PACKET", "SHAM", "REAL"),
    ("NO_PACKET", "REAL", "NO_PACKET", "SHAM"),
    ("NO_PACKET", "REAL", "SHAM", "NO_PACKET"),
    ("NO_PACKET", "SHAM", "NO_PACKET", "REAL"),
    ("NO_PACKET", "SHAM", "REAL", "NO_PACKET"),
    ("REAL", "NO_PACKET", "NO_PACKET", "SHAM"),
    ("REAL", "NO_PACKET", "SHAM", "NO_PACKET"),
    ("REAL", "SHAM", "NO_PACKET", "NO_PACKET"),
    ("SHAM", "NO_PACKET", "NO_PACKET", "REAL"),
    ("SHAM", "NO_PACKET", "REAL", "NO_PACKET"),
    ("SHAM", "REAL", "NO_PACKET", "NO_PACKET"),
)
SEED_LABELS = (
    "roster",
    "schedule",
    "assignment",
    "packet",
    "model",
    "benchmark",
    "unblind",
)


def canonical_bytes(value: object) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def digest(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_canonical(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise CloudManifestError(f"missing regular prelaunch input: {path}")
    raw = path.read_bytes()
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CloudManifestError(f"invalid JSON prelaunch input: {path}") from exc
    if not isinstance(value, dict) or canonical_bytes(value) != raw:
        raise CloudManifestError(f"prelaunch input is not canonical JSON: {path}")
    return value


def _secret(path: Path) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise CloudManifestError(f"missing regular secret: {path}")
    raw = path.read_bytes()
    if len(raw) != 32:
        raise CloudManifestError(f"secret must contain exactly 32 bytes: {path}")
    return raw


def _commitment(label: str, secret: bytes) -> str:
    return hashlib.sha256(
        b"official-study-commitment-v1\0" + label.encode("ascii") + b"\0" + secret
    ).hexdigest()


def _draw(key: bytes, domain: str, task_id: str, upper: int) -> int:
    if not 1 <= upper <= 2**64:
        raise CloudManifestError("draw upper bound is invalid")
    frame = (
        b"official-study-draw-v1\0"
        + domain.encode("ascii")
        + b"\0"
        + task_id.encode("utf-8")
    )
    limit = 2**64 - (2**64 % upper)
    for counter in range(2**32):
        raw = hmac.new(key, frame + counter.to_bytes(4, "big"), hashlib.sha256).digest()
        candidate = int.from_bytes(raw[:8], "big")
        if candidate < limit:
            return candidate % upper
    raise CloudManifestError("unbiased draw counter exhausted")


def _derive(key: bytes, domain: str, *fields: str) -> bytes:
    framed = bytearray(b"official-study-derive-v1\0")
    for value in (domain, *fields):
        encoded = value.encode("utf-8")
        framed.extend(len(encoded).to_bytes(4, "big"))
        framed.extend(encoded)
    return hmac.new(key, bytes(framed), hashlib.sha256).digest()


def _ref(root: Path, path: Path, role: str) -> dict[str, object]:
    relative = path.resolve().relative_to(root.resolve()).as_posix()
    return {
        "role": role,
        "relative_path": relative,
        "sha256": file_digest(path),
        "byte_count": path.stat().st_size,
        "media_type": "application/json",
    }


def _write(path: Path, value: object, *, private: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_bytes(value))
    if private:
        path.chmod(0o600)


def _validate_power(power_report: Mapping[str, object]) -> None:
    if power_report.get("record_kind") != "resampling_power_report":
        raise CloudManifestError("power report has the wrong identity")
    payload = power_report.get("payload")
    if not isinstance(payload, Mapping) or payload.get("stage") != "final":
        raise CloudManifestError("power report is not final")
    finalization = payload.get("finalization")
    if (
        not isinstance(finalization, Mapping)
        or finalization.get("decision") != "GO"
        or finalization.get("selected_tier") != 120
    ):
        raise CloudManifestError("power report did not select C120 GO")


def seal_prelaunch(
    *,
    package_root: Path,
    secret_root: Path,
    power_report_path: Path,
    protocol_amendment_path: Path,
    code_commit: str,
) -> Path:
    """Seal all pre-outcome authorities required by amendment item four."""

    if len(code_commit) != 40 or any(c not in "0123456789abcdef" for c in code_commit):
        raise CloudManifestError("code_commit must be full lowercase Git SHA-1")
    package_root = package_root.resolve()
    input_root = package_root / "inputs"
    task_path = input_root / "task-registry.json"
    roster_path = package_root / "power/sources/c120-roster.json"
    commitment_path = package_root / "power/sources/deterministic-seed-commitments.json"
    analysis_path = input_root / "analysis-graph.json"
    input_lock_path = input_root / "input-lock.json"
    tasks_doc = _load_canonical(task_path)
    roster_doc = _load_canonical(roster_path)
    commitments_doc = _load_canonical(commitment_path)
    analysis_doc = _load_canonical(analysis_path)
    _load_canonical(input_lock_path)
    power_report = _load_canonical(power_report_path)
    _validate_power(power_report)
    if (
        file_digest(protocol_amendment_path)
        != "e5f7e169b866a880383666df9a5fa69565c6a54b0e69fa42ed88bf8255b3758a"
    ):
        raise CloudManifestError("prospective protocol amendment digest differs")

    tasks = tasks_doc.get("tasks")
    roster_tasks = roster_doc.get("tasks")
    if not isinstance(tasks, list) or not isinstance(roster_tasks, list):
        raise CloudManifestError("task registry or roster lacks tasks")
    by_id = {
        str(task.get("task_id")): task
        for task in tasks
        if isinstance(task, Mapping) and isinstance(task.get("task_id"), str)
    }
    roster_ids = [
        str(task.get("task_id"))
        for task in roster_tasks
        if isinstance(task, Mapping) and isinstance(task.get("task_id"), str)
    ]
    if len(by_id) != 240 or len(roster_ids) != 240 or set(by_id) != set(roster_ids):
        raise CloudManifestError("C120 roster must exactly cover 240 unique tasks")
    counts = Counter(str(by_id[task_id].get("benchmark")) for task_id in roster_ids)
    if counts != Counter({"SWE": 120, "TAU": 120}):
        raise CloudManifestError("C120 roster must contain 120 tasks per benchmark")

    commitments = commitments_doc.get("commitments")
    if not isinstance(commitments, Mapping) or set(commitments) != set(SEED_LABELS):
        raise CloudManifestError("seed commitment set is incomplete")
    secrets = {
        label: _secret(secret_root / f"{label}-seed.bin") for label in SEED_LABELS
    }
    for label, secret in secrets.items():
        if commitments.get(label) != _commitment(label, secret):
            raise CloudManifestError(f"{label} seed does not open its commitment")

    ordered_by_benchmark: dict[str, list[str]] = {}
    for benchmark in ("SWE", "TAU"):
        members = [
            task_id
            for task_id in roster_ids
            if by_id[task_id]["benchmark"] == benchmark
        ]
        ordered_by_benchmark[benchmark] = sorted(
            members,
            key=lambda task_id: (
                _derive(secrets["schedule"], "schedule-rank", task_id),
                task_id,
            ),
        )
    worker_by_task: dict[str, str] = {}
    schedule: list[str] = []
    for benchmark in ("SWE", "TAU"):
        for index, task_id in enumerate(ordered_by_benchmark[benchmark]):
            worker_by_task[task_id] = f"worker-{index % 2}"
            schedule.append(task_id)

    clear_rows: list[dict[str, object]] = []
    block_rows: list[dict[str, object]] = []
    for schedule_index, task_id in enumerate(schedule):
        allocation_index = _draw(secrets["assignment"], "allocation", task_id, 12)
        orientation = _draw(secrets["assignment"], "orientation", task_id, 2)
        null_arms = ("NONE", "RESAMPLE") if orientation == 0 else ("RESAMPLE", "NONE")
        no_packet_index = 0
        arms: list[str] = []
        for treatment in TREATMENT_TABLE[allocation_index]:
            if treatment == "NO_PACKET":
                arms.append(null_arms[no_packet_index])
                no_packet_index += 1
            else:
                arms.append(treatment)
        slots: list[dict[str, object]] = []
        clear_slots: list[dict[str, object]] = []
        for ordinal, arm in enumerate(arms):
            slot_id = hashlib.sha256(
                _derive(secrets["assignment"], "opaque-slot", task_id, str(ordinal))
            ).hexdigest()
            capability = hmac.new(
                secrets["assignment"],
                b"official-slot-capability-v1\0"
                + task_id.encode("utf-8")
                + b"\0"
                + slot_id.encode("ascii")
                + b"\0"
                + arm.encode("ascii"),
                hashlib.sha256,
            ).hexdigest()
            slot = {
                "ordinal": ordinal,
                "slot_id": slot_id,
                "opaque_capability_id": capability,
                "model_seed_commitment_sha256": hashlib.sha256(
                    _derive(secrets["model"], "model-slot", task_id, slot_id)
                ).hexdigest(),
                "benchmark_seed_commitment_sha256": hashlib.sha256(
                    _derive(secrets["benchmark"], "benchmark-slot", task_id, slot_id)
                ).hexdigest(),
            }
            slots.append(slot)
            clear_slots.append({**slot, "arm": arm})
        clear_rows.append(
            {
                "task_id": task_id,
                "worker_id": worker_by_task[task_id],
                "allocation_index": allocation_index,
                "no_packet_orientation_bit": orientation,
                "slots": clear_slots,
            }
        )
        block_rows.append(
            {
                "schedule_index": schedule_index,
                "task_id": task_id,
                "benchmark": by_id[task_id]["benchmark"],
                "worker_id": worker_by_task[task_id],
                "common_prefix_seed_commitment_sha256": hashlib.sha256(
                    _derive(secrets["schedule"], "common-prefix", task_id)
                ).hexdigest(),
                "slots": slots,
                "block_rule": "one-common-prefix-then-four-opaque-continuations-v1",
            }
        )

    binding = {
        "code_commit": code_commit,
        "input_lock_sha256": file_digest(input_lock_path),
        "task_registry_sha256": file_digest(task_path),
        "roster_sha256": file_digest(roster_path),
        "power_report_sha256": file_digest(power_report_path),
        "analysis_graph_sha256": file_digest(analysis_path),
        "seed_commitments_sha256": file_digest(commitment_path),
        "protocol_amendment_sha256": file_digest(protocol_amendment_path),
    }
    output = package_root / "sealed"
    roster_seal = {
        "record_kind": "cloud_official_roster_seal",
        "schema_version": "0.1.0",
        "study_id": STUDY_ID,
        "status": "sealed",
        "selected_tier": 120,
        "task_count_by_benchmark": {"SWE": 120, "TAU": 120},
        "task_ids": schedule,
        "binding": binding,
    }
    roster_seal_path = output / "roster.json"
    _write(roster_seal_path, roster_seal)
    assignment = {
        "record_kind": "cloud_official_assignment_seal",
        "schema_version": "0.1.0",
        "study_id": STUDY_ID,
        "status": "sealed_controller_only",
        "synthetic": False,
        "seed_commitment_sha256": commitments["assignment"],
        "allocation_table_id": "registered-12-way-allocation-v1",
        "rows": clear_rows,
        "binding": binding,
    }
    assignment_path = output / "assignment.controller-only.json"
    _write(assignment_path, assignment, private=True)
    packet_authority = {
        "record_kind": "cloud_official_packet_authority",
        "schema_version": "0.1.0",
        "study_id": STUDY_ID,
        "status": "sealed_pre_prefix_authority",
        "seed_commitment_sha256": commitments["packet"],
        "construction": "registered-real-sham-token-exact-v1",
        "real_source": "focal-prefix-disposable-verifier",
        "sham_source": "post-prefix-matched-different-lineage-donor",
        "no_packet_arms": ["NONE", "RESAMPLE"],
        "packet_content_status": "materialize_only_after_common_prefix",
        "outcome_access_forbidden": True,
        "binding": binding,
    }
    packet_path = output / "packet-authority.json"
    _write(packet_path, packet_authority)
    task_blocks = {
        "record_kind": "cloud_official_task_block_plan",
        "schema_version": "0.1.0",
        "study_id": STUDY_ID,
        "status": "sealed_pre_execution_plan",
        "completed_task_blocks": False,
        "task_count": 240,
        "worker_counts": Counter(row["worker_id"] for row in block_rows),
        "rows": block_rows,
        "binding": binding,
    }
    task_blocks_path = output / "task-block-plan.json"
    _write(task_blocks_path, task_blocks)
    blinding = {
        "record_kind": "cloud_official_blinding_seal",
        "schema_version": "0.1.0",
        "study_id": STUDY_ID,
        "status": "sealed",
        "analysis_labels": ["A", "B", "C", "D"],
        "worker_receives_arm_labels": False,
        "analysis_receives_arm_labels_pre_unblind": False,
        "unblind_seed_commitment_sha256": commitments["unblind"],
        "clear_assignment_ref": _ref(
            package_root, assignment_path, "controller_only_assignment"
        ),
        "binding": binding,
    }
    blinding_path = output / "blinding.json"
    _write(blinding_path, blinding)
    frozen_analysis = {
        "record_kind": "cloud_official_analysis_freeze",
        "schema_version": "0.1.0",
        "study_id": STUDY_ID,
        "status": "sealed_pre_outcome",
        "analysis_graph_ref": _ref(package_root, analysis_path, "analysis_graph"),
        "analysis_graph_semantic_sha256": digest(analysis_doc),
        "unblind_before_analysis_forbidden": True,
        "binding": binding,
    }
    frozen_analysis_path = output / "frozen-analysis.json"
    _write(frozen_analysis_path, frozen_analysis)
    root = {
        "record_kind": "cloud_official_prelaunch_seal",
        "schema_version": "0.1.0",
        "study_id": STUDY_ID,
        "status": "sealed",
        "selected_tier": 120,
        "binding": binding,
        "artifacts": [
            _ref(package_root, roster_seal_path, "roster_seal"),
            _ref(package_root, assignment_path, "assignment_seal"),
            _ref(package_root, packet_path, "packet_authority"),
            _ref(package_root, task_blocks_path, "task_block_plan"),
            _ref(package_root, blinding_path, "blinding_seal"),
            _ref(package_root, frozen_analysis_path, "analysis_freeze"),
        ],
    }
    root_path = output / "prelaunch-root.json"
    _write(root_path, root)
    verify_prelaunch(root_path, package_root=package_root)
    return root_path


def verify_prelaunch(root_path: Path, *, package_root: Path) -> Mapping[str, object]:
    """Recompute the closed prelaunch root and its load-bearing invariants."""

    root = _load_canonical(root_path)
    if set(root) != {
        "record_kind",
        "schema_version",
        "study_id",
        "status",
        "selected_tier",
        "binding",
        "artifacts",
    }:
        raise CloudManifestError("prelaunch root has an open or incomplete shape")
    if (
        root.get("record_kind") != "cloud_official_prelaunch_seal"
        or root.get("schema_version") != "0.1.0"
        or root.get("study_id") != STUDY_ID
        or root.get("status") != "sealed"
        or root.get("selected_tier") != 120
    ):
        raise CloudManifestError("prelaunch root identity or state differs")
    artifacts = root.get("artifacts")
    if not isinstance(artifacts, list) or len(artifacts) != 6:
        raise CloudManifestError("prelaunch root must bind six sealed artifacts")
    roles: set[str] = set()
    for item in artifacts:
        if not isinstance(item, Mapping):
            raise CloudManifestError("prelaunch artifact reference is malformed")
        role = item.get("role")
        relative = item.get("relative_path")
        if not isinstance(role, str) or not isinstance(relative, str) or role in roles:
            raise CloudManifestError("prelaunch artifact role/path is malformed")
        roles.add(role)
        path = package_root.resolve() / relative
        resolved = path.resolve(strict=True)
        resolved.relative_to(package_root.resolve())
        raw = resolved.read_bytes()
        if len(raw) != item.get("byte_count") or hashlib.sha256(
            raw
        ).hexdigest() != item.get("sha256"):
            raise CloudManifestError("prelaunch artifact bytes differ")
        _load_canonical(resolved)
    expected = {
        "roster_seal",
        "assignment_seal",
        "packet_authority",
        "task_block_plan",
        "blinding_seal",
        "analysis_freeze",
    }
    if roles != expected:
        raise CloudManifestError("prelaunch root role set differs")
    return root


__all__ = ["seal_prelaunch", "verify_prelaunch"]
