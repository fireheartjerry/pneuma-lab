"""Canonical project-status validation and reporting.

``docs/project-status.json`` is the current-state source of truth. This module is
deliberately read-only: it validates the manifest against its schema and the
checkout, then renders a compact summary for humans and fresh agent sessions.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from functools import lru_cache
from pathlib import Path, PurePosixPath
from typing import Iterable

from jsonschema import Draft202012Validator, FormatChecker

from .demo import (
    EvidenceProvenanceError,
    RepositoryProvenance,
    require_official_provenance,
)


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST = ROOT / "docs" / "project-status.json"
STATUS_SCHEMA = ROOT / "schemas" / "project-status.schema.json"
STATUS_DOC_REF = "docs/project-status.json"

_STALE_PHRASES = {
    "AGENTS.md": (
        "replay later",
        "future deterministic replay harness",
        "future perturbation and evidence scoring suites",
    ),
    "CLAUDE.md": ("runtime, replay, adapters, and evals are still scaffold seams",),
    "README.md": ("adapters/ empty seam",),
    "docs/adapters/README.md": ("phase 3.1: fuzzy-join",),
    "docs/vision.md": (
        "not a runtime. there is no live psyche loop here yet",
        "not an ml training project. no models are trained or fine-tuned",
    ),
}

_CURRENT_9TO5_EDGE_STATUS = {
    "nine_to_five_snapshot_to_pneuma_trace": "specified",
    "pneuma_trace_to_replay": "implemented",
    "replay_outputs_to_shadow_log": "not_implemented",
    "shadow_log_to_advisory_pressure": "not_implemented",
    "advisory_pressure_to_authority_gated_action": "not_implemented",
    "realized_outcome_to_pneuma_feedback": "not_implemented",
}

_CURRENT_SYSTEM_STATE = {
    "canonical_project_status": ("implemented", "standalone"),
    "schema_contracts": ("implemented", "standalone"),
    "deterministic_replay": ("implemented", "internal_harness"),
    "paired_interventions": ("implemented", "internal_harness"),
    "dataset_trace_adapters": ("implemented", "offline_research"),
    "trace_to_replay_bridge": ("implemented", "offline_research"),
    "training_example_conversion": ("implemented", "offline_research"),
    "dataset_registry": ("implemented", "offline_research"),
    "pneuma_brain_v0_corpus": ("implemented", "offline_research"),
    "pneuma_brain_trainer": ("implemented", "offline_research"),
    "pneuma_nervous_system_shadow": ("implemented", "internal_harness"),
    "pneuma_voice_shadow": ("implemented", "internal_harness"),
    "pneuma_local_foundation_tooling": ("implemented", "offline_research"),
    "pneuma_local_memory_store": ("implemented", "offline_research"),
    "pneuma_local_action_guard": ("implemented", "standalone"),
    "pneuma_gauge_msa": ("implemented", "offline_research"),
    "neurips_resampling_null_task6": ("partial", "offline_research"),
}

_CURRENT_NEGATIVE_RESULTS = {
    "e0_reference_psyche_transfer": {
        "verdict": "failed_preregistered_hypotheses",
        "evidence_refs": frozenset(
            (
                "build/e0/report.json",
                "docs/research/experiments/e0-results.md",
            )
        ),
    },
    # G-1 falsified three of its six registered hypotheses (H1 partially, H4, H5
    # partially, H6) and confirmed H2. The surviving finding is a measurement-
    # methodology result, not a psyche or evidence-ladder claim.
    "g1_self_report_gauge": {
        "verdict": "failed_preregistered_hypotheses",
        "evidence_refs": frozenset(
            (
                "docs/research/experiments/g1-gauge-preregistration.md",
                "docs/research/experiments/g1-gauge-results.md",
            )
        ),
    },
}


def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"expected a JSON object: {path}")
    return value


def load_manifest(path: Path = DEFAULT_MANIFEST) -> dict:
    """Load one project-status manifest."""
    return _load_json(Path(path))


def _schema_errors(manifest: dict) -> list[str]:
    schema = _load_json(STATUS_SCHEMA)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors: list[str] = []
    for error in sorted(
        validator.iter_errors(manifest), key=lambda item: list(item.path)
    ):
        location = ".".join(str(part) for part in error.path) or "<root>"
        errors.append(f"schema:{location}: {error.message}")
    return errors


def _walk_key(value, key: str) -> Iterable:
    if isinstance(value, dict):
        for name, item in value.items():
            if name == key:
                yield item
            yield from _walk_key(item, key)
    elif isinstance(value, list):
        for item in value:
            yield from _walk_key(item, key)


def _repo_path(root: Path, value: str) -> tuple[Path | None, str | None]:
    if not isinstance(value, str) or not value:
        return None, "path must be a non-empty string"
    normalized = value.replace("\\", "/")
    relative = PurePosixPath(normalized)
    if (
        not relative.parts
        or relative.is_absolute()
        or ".." in relative.parts
        or any(":" in part for part in relative.parts)
    ):
        return None, f"path must be repo-relative without traversal: {value!r}"
    candidate = (root / Path(*relative.parts)).resolve()
    resolved_root = root.resolve()
    if candidate != resolved_root and resolved_root not in candidate.parents:
        return None, f"path escapes repository root: {value!r}"
    return candidate, None


@lru_cache(maxsize=4)
def _tracked_files(root_text: str) -> frozenset[str]:
    root = Path(root_text)
    proc = subprocess.run(
        ["git", "-C", str(root), "ls-files", "-z"],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if proc.returncode != 0:
        return frozenset()
    return frozenset(item for item in proc.stdout.split("\0") if item)


def _git_tracked(root: Path, relative: str) -> bool:
    normalized = relative.replace("\\", "/")
    return normalized in _tracked_files(str(root.resolve()))


def _remote_refs_containing(root: Path, commit: str) -> tuple[str, ...]:
    """Return fetched remote refs containing one commit, matching the demo gate."""
    proc = subprocess.run(
        [
            "git",
            "-C",
            str(root),
            "for-each-ref",
            "--format=%(refname:short)",
            "--contains",
            commit,
            "refs/remotes",
        ],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout).strip() or f"exit {proc.returncode}"
        raise ValueError(f"cannot verify canonical source commit: {detail}")
    return tuple(sorted(line for line in proc.stdout.splitlines() if line))


def _official_record_errors(record: dict, *, root: Path) -> list[str]:
    """Validate an official canonical record against the demo's provenance gate."""
    errors: list[str] = []
    if record.get("report_kind") != "canonical_evidence_summary":
        errors.append("canonical evidence record has the wrong report_kind")

    provenance = record.get("source_provenance")
    if not isinstance(provenance, dict):
        return errors + ["canonical evidence record lacks source_provenance"]

    required = {
        "source_kind",
        "git_commit",
        "tree_state",
        "remote_refs_containing_commit",
        "commit_published",
        "official",
    }
    missing = sorted(required - set(provenance))
    if missing:
        errors.append(f"canonical source_provenance is missing fields: {missing}")
        return errors

    if provenance["source_kind"] != "git":
        errors.append("canonical source_provenance.source_kind must be git")

    commit = provenance["git_commit"]
    commit_valid = (
        isinstance(commit, str)
        and len(commit) == 40
        and all(ch in "0123456789abcdef" for ch in commit.lower())
    )
    if not commit_valid:
        errors.append(
            "canonical source_provenance.git_commit must be a 40-character hex id"
        )

    tree_state = provenance["tree_state"]
    tree_state_valid = isinstance(tree_state, str) and tree_state in {"clean", "dirty"}
    if not tree_state_valid:
        errors.append("canonical source_provenance.tree_state must be clean or dirty")

    refs = provenance["remote_refs_containing_commit"]
    refs_valid = (
        isinstance(refs, list)
        and all(isinstance(item, str) and item for item in refs)
        and refs == sorted(set(refs))
    )
    if not refs_valid:
        errors.append(
            "canonical source_provenance.remote_refs_containing_commit must be "
            "a sorted unique list of non-empty refs"
        )

    if not isinstance(provenance["commit_published"], bool):
        errors.append("canonical source_provenance.commit_published must be boolean")
    if provenance["official"] is not True:
        errors.append("canonical evidence record is not marked official")

    if not (commit_valid and tree_state_valid and refs_valid):
        return errors

    source = RepositoryProvenance(
        commit=commit,
        dirty=tree_state == "dirty",
        remote_refs=tuple(refs),
    )
    try:
        require_official_provenance(source)
    except EvidenceProvenanceError as exc:
        errors.append(str(exc))

    if provenance["commit_published"] is not source.published:
        errors.append(
            "canonical source_provenance.commit_published disagrees with recorded remote refs"
        )

    try:
        fetched_refs = set(_remote_refs_containing(root, commit))
    except ValueError as exc:
        errors.append(str(exc))
    else:
        if not fetched_refs:
            errors.append(
                "canonical source commit is not contained in any fetched remote ref"
            )
        missing_refs = sorted(set(refs) - fetched_refs)
        if missing_refs:
            errors.append(
                "canonical source_provenance names refs that do not contain its commit: "
                f"{missing_refs}"
            )
    return errors


def _all_referenced_paths(manifest: dict) -> list[str]:
    paths: list[str] = ["schemas/project-status.schema.json"]
    for refs in _walk_key(manifest, "evidence_refs"):
        if isinstance(refs, list):
            paths.extend(ref for ref in refs if isinstance(ref, str))
    paths.extend(manifest.get("authoritative_docs") or [])
    paths.extend(manifest.get("historical_snapshots") or [])
    paths.extend((manifest.get("artifact_policy") or {}).get("tracked_records") or [])
    jspace_contract = (manifest.get("jspace") or {}).get("readiness_contract")
    if isinstance(jspace_contract, str):
        paths.append(jspace_contract)
    return paths


def _normalize_text(text: str) -> str:
    return " ".join(text.lower().split())


def _record_errors(record: dict, label: str) -> list[str]:
    errors: list[str] = []
    status = record.get("status")
    refs = record.get("evidence_refs") or []
    blockers = record.get("blockers") or []
    if status == "implemented" and not refs:
        errors.append(f"{label}: implemented status requires evidence_refs")
    if status == "implemented" and blockers:
        errors.append(f"{label}: implemented status cannot retain blockers")
    if status in {"partial", "specified", "in_progress", "not_implemented", "blocked"}:
        if not blockers:
            errors.append(f"{label}: {status} status requires blockers")
    return errors


def validate_manifest(manifest: dict, *, root: Path = ROOT) -> list[str]:
    """Return deterministic findings for schema and checkout incoherence."""
    errors = _schema_errors(manifest)
    if errors:
        return errors

    required_sections = {
        "evidence": (
            "evaluation_scope",
            "real_subject_claim_status",
            "internal_harness_ceiling",
            "legacy_methodology",
        ),
        "nine_to_five": (
            "direct_import_policy",
            "operational_nervous_system",
            "required_edge_ids",
            "edges",
        ),
        "jspace": (
            "status",
            "supports_consciousness_claim",
            "readiness_contract",
            "black_gray_box_workspace_probes",
            "white_box_jlens",
            "causal_negative_controls",
        ),
        "training_and_rsi": (
            "new_training_authorization",
            "trainer_preflight",
            "foundation_program",
            "runtime_model_integration",
            "rsi_loop",
        ),
        "artifact_policy": (
            "canonical_evidence_record",
            "tracked_records",
        ),
    }
    for section_name, required_keys in required_sections.items():
        section = manifest.get(section_name)
        if not isinstance(section, dict):
            errors.append(f"section must be an object: {section_name}")
            continue
        for key in required_keys:
            if key not in section:
                errors.append(f"missing required status field: {section_name}.{key}")
    if errors:
        return sorted(set(errors))

    systems = manifest["systems"]
    edges = manifest["nine_to_five"]["edges"]
    blockers = manifest["blockers"]
    if not isinstance(edges, list) or any(not isinstance(item, dict) for item in edges):
        return ["nine_to_five.edges must be a list of objects"]
    for index, record in enumerate(edges):
        missing = [
            key
            for key in ("id", "status", "evidence_refs", "blockers")
            if key not in record
        ]
        if missing:
            errors.append(f"9to5 edge {index} is missing fields: {missing}")
    if errors:
        return sorted(set(errors))

    for label, records in (
        ("system", systems),
        ("9to5 edge", edges),
        ("blocker", blockers),
    ):
        identifiers = [record.get("id") for record in records]
        duplicates = sorted(
            {item for item in identifiers if identifiers.count(item) > 1}
        )
        if duplicates:
            errors.append(f"{label} ids are duplicated: {duplicates}")

    blocker_ids = {record["id"] for record in blockers}
    blocker_uses: set[str] = set()
    for values in _walk_key(manifest, "blockers"):
        if values is blockers:
            continue
        if isinstance(values, list) and all(isinstance(item, str) for item in values):
            blocker_uses.update(values)
            unknown = sorted(set(values) - blocker_ids)
            if unknown:
                errors.append(f"unknown blocker references: {unknown}")
    unused = sorted(blocker_ids - blocker_uses)
    if unused:
        errors.append(f"unreferenced blocker definitions: {unused}")

    for record in systems:
        errors.extend(_record_errors(record, f"system {record['id']}"))
    for record in edges:
        errors.extend(_record_errors(record, f"9to5 edge {record['id']}"))

    system_map = {record["id"]: record for record in systems}
    if set(system_map) != set(_CURRENT_SYSTEM_STATE):
        errors.append(
            "system ids must exactly match the canonical current-state registry"
        )
    else:
        for system_id, expected_state in _CURRENT_SYSTEM_STATE.items():
            actual_state = (
                system_map[system_id].get("status"),
                system_map[system_id].get("scope"),
            )
            if actual_state != expected_state:
                errors.append(
                    f"system {system_id} must remain status={expected_state[0]}, "
                    f"scope={expected_state[1]} until its validator and evidence "
                    "are updated"
                )

    for relative in sorted(set(_all_referenced_paths(manifest))):
        path, path_error = _repo_path(root, relative)
        if path_error:
            errors.append(path_error)
        elif path is not None and not path.exists():
            errors.append(f"referenced path does not exist: {relative}")
        elif path is not None and not _git_tracked(root, relative):
            errors.append(f"referenced path is not Git-tracked: {relative}")

    evidence = manifest["evidence"]
    for name in ("strongest_result", "real_subject_level4", "level5", "level6"):
        errors.extend(_record_errors(evidence[name], f"evidence {name}"))
    if evidence.get("evaluation_scope") == "internal_harness":
        if evidence.get("real_subject_claim_status") != "not_evaluated":
            errors.append(
                "internal_harness evaluation must keep real_subject_claim_status=not_evaluated"
            )
    if evidence.get("internal_harness_ceiling") != 4:
        errors.append("the executable internal-harness ceiling must remain 4")
    legacy = evidence.get("legacy_methodology") or {}
    if legacy != {
        "archived": True,
        "authoritative": False,
        "delivery_gate": False,
        "learned_subject_import_allowed": False,
        "archive_ref": "docs/archive/consciousness-level-methodology.md",
    }:
        errors.append(
            "the Level methodology must remain archived and outside delivery gates"
        )
    negative_result_records = evidence.get("negative_results") or []
    negative_result_ids = [record["id"] for record in negative_result_records]
    duplicate_negative_ids = sorted(
        {item for item in negative_result_ids if negative_result_ids.count(item) > 1}
    )
    if duplicate_negative_ids:
        errors.append(f"negative-result ids are duplicated: {duplicate_negative_ids}")
    negative_results = {record["id"]: record for record in negative_result_records}
    if set(negative_results) != set(_CURRENT_NEGATIVE_RESULTS):
        errors.append("negative-result ids must exactly match the canonical registry")
    else:
        for result_id, expected in _CURRENT_NEGATIVE_RESULTS.items():
            result = negative_results[result_id]
            if result.get("verdict") != expected["verdict"]:
                errors.append(
                    f"negative result {result_id} must remain {expected['verdict']} "
                    "until its evidence and validator are updated"
                )
            if (
                frozenset(result.get("evidence_refs") or [])
                != expected["evidence_refs"]
            ):
                errors.append(
                    f"negative result {result_id} must retain its canonical evidence refs"
                )

    project = manifest["project"]
    integration = manifest["nine_to_five"]
    required_edges = set(integration.get("required_edge_ids") or [])
    edge_map = {record["id"]: record for record in edges}
    if required_edges != set(edge_map):
        errors.append("required_edge_ids must exactly match declared 9to5 edge ids")
    if set(edge_map) == set(_CURRENT_9TO5_EDGE_STATUS):
        for edge_id, expected_status in _CURRENT_9TO5_EDGE_STATUS.items():
            if edge_map[edge_id].get("status") != expected_status:
                errors.append(
                    f"9to5 edge {edge_id} must remain {expected_status} in this manifest version"
                )
    missing_edges = [
        edge_id
        for edge_id in sorted(required_edges)
        if edge_map[edge_id].get("status") != "implemented"
    ]
    if missing_edges and integration.get("operational_nervous_system"):
        errors.append("operational_nervous_system cannot be true with incomplete edges")
    if project.get("operational_nervous_system") != integration.get(
        "operational_nervous_system"
    ):
        errors.append("project and 9to5 nervous-system status must agree")
    if integration.get("direct_import_policy") != "forbidden":
        errors.append("Pneuma must keep direct 9to5 imports forbidden")

    jspace = manifest["jspace"]
    if jspace.get("supports_consciousness_claim") is not False:
        errors.append("JSpace must not be represented as consciousness proof")
    for lane in (
        "workspace_harness_substrate",
        "black_gray_box_workspace_probes",
        "white_box_jlens",
        "causal_negative_controls",
    ):
        lane_record = jspace.get(lane) or {}
        if (
            lane != "workspace_harness_substrate"
            and jspace.get("status") == "not_implemented"
            and lane_record.get("status") == "implemented"
        ):
            errors.append(
                f"JSpace lane {lane} cannot be implemented while overall status "
                "is not_implemented"
            )
        errors.extend(_record_errors(lane_record, f"JSpace lane {lane}"))

    training = manifest["training_and_rsi"]
    foundation_program = training.get("foundation_program") or {}
    if foundation_program.get("tooling_status") != "implemented":
        errors.append("foundation tooling status must record the implemented surface")
    if (
        foundation_program.get("training_status")
        != "local_8m_completed_doubling_gate_stopped_ladder"
    ):
        errors.append(
            "foundation training truth must record exactly the completed"
            " local 8M stage with the doubling gate stopping the ladder"
        )
    if foundation_program.get("runtime_status") != "not_promoted":
        errors.append("foundation runtime must remain not_promoted")
    if foundation_program.get("compatibility_reference_download_allowed") is not False:
        errors.append("397B compatibility-reference downloads must remain forbidden")
    if foundation_program.get("default_paid_compute_usd") != 0:
        errors.append("foundation default paid compute must remain zero")
    if foundation_program.get("cloud_lifetime_cap_usd") != 45:
        errors.append("foundation cloud lifetime cap must remain $45")
    if training.get("new_training_authorization") == "not_authorized":
        if training.get("runtime_model_integration") != "none":
            errors.append(
                "unauthorized training state requires runtime_model_integration=none"
            )
    preflight = training.get("trainer_preflight") or {}
    if preflight.get("status") == "in_progress" and preflight.get("integrated"):
        errors.append("in-progress trainer preflight cannot be marked integrated")
    if preflight.get("status") == "implemented" and not preflight.get("integrated"):
        errors.append("implemented trainer preflight must be marked integrated")
    if preflight.get("status") == "implemented" and not preflight.get("evidence_refs"):
        errors.append("implemented trainer preflight requires evidence_refs")
    if preflight.get("status") == "in_progress" and not preflight.get("blockers"):
        errors.append("in-progress trainer preflight requires blockers")
    errors.extend(_record_errors(preflight, "trainer preflight"))
    if preflight.get("training_authorization") != "not_authorized":
        errors.append("trainer preflight must not authorize training")
    if training.get("rsi_loop") != "not_operational":
        errors.append(
            "RSI loop cannot be operational while its declared blockers remain"
        )

    artifacts = manifest["artifact_policy"]
    for relative in artifacts.get("tracked_records") or []:
        if not _git_tracked(root, relative):
            errors.append(f"declared tracked artifact is not Git-tracked: {relative}")
    canonical = artifacts["canonical_evidence_record"]
    canonical_path = canonical["path"]
    canonical_file, canonical_path_error = _repo_path(root, canonical_path)
    if canonical_path_error:
        errors.append(canonical_path_error)
    elif canonical_file is not None:
        canonical_tracked = _git_tracked(root, canonical_path)
        if canonical.get("record_status") == "absent" and canonical_tracked:
            errors.append("canonical evidence record is tracked but status says absent")
        if canonical.get("record_status") == "present":
            if not canonical_file.is_file():
                errors.append(
                    "canonical evidence record says present but the file is absent"
                )
            elif not canonical_tracked:
                errors.append(
                    "canonical evidence record says present but is not Git-tracked"
                )
            else:
                try:
                    record = _load_json(canonical_file)
                except (OSError, ValueError, json.JSONDecodeError) as exc:
                    errors.append(f"canonical evidence record cannot be loaded: {exc}")
                else:
                    errors.extend(_official_record_errors(record, root=root))

    for relative in manifest["authoritative_docs"]:
        path = root / relative
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        if STATUS_DOC_REF not in text:
            errors.append(
                f"authoritative doc does not link {STATUS_DOC_REF}: {relative}"
            )
        normalized = _normalize_text(text)
        for phrase in _STALE_PHRASES.get(relative, ()):
            if phrase in normalized:
                errors.append(
                    f"authoritative doc retains stale phrase {phrase!r}: {relative}"
                )

    for relative in manifest["historical_snapshots"]:
        path = root / relative
        if not path.is_file():
            continue
        head = "\n".join(path.read_text(encoding="utf-8").splitlines()[:20])
        if "Historical snapshot" not in head:
            errors.append(f"historical document lacks snapshot banner: {relative}")
        if STATUS_DOC_REF not in head:
            errors.append(f"historical document lacks current-status link: {relative}")

    return sorted(set(errors))


def render_status(manifest: dict) -> str:
    """Render a stable, compact status report derived only from the manifest."""
    integration = manifest["nine_to_five"]
    edges = integration["edges"]
    implemented_edges = sum(record["status"] == "implemented" for record in edges)
    training = manifest["training_and_rsi"]
    preflight = training["trainer_preflight"]
    jspace = manifest["jspace"]
    return "\n".join(
        [
            (
                "Pneuma Lab status "
                f"(manifest {manifest['manifest_schema_version']}; as of {manifest['as_of']})"
            ),
            "role: standalone research/evaluation harness",
            (
                "evidence: legacy internal Level-4 methodology archived; "
                "real subject not evaluated; not a delivery gate"
            ),
            (
                f"9to5: {implemented_edges}/{len(edges)} integration edges implemented; "
                "operational nervous system: no"
            ),
            (
                "JSpace: workspace substrate only; probes/J-lens: absent"
                if jspace["status"] == "not_implemented"
                else f"JSpace: {jspace['status']}"
            ),
            (
                "training: offline advisory estimators; new training authorized: "
                f"{'no' if training['new_training_authorization'] == 'not_authorized' else 'yes'}"
            ),
            (
                f"trainer preflight: {preflight['status']}; integrated: "
                f"{'yes' if preflight['integrated'] else 'no'}; authorizes training: "
                f"{'no' if preflight['training_authorization'] == 'not_authorized' else 'yes'}"
            ),
            "RSI: not operational",
        ]
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m pneuma_lab.status")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate the canonical manifest and checkout without printing the full report.",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_MANIFEST,
        help="Alternate manifest path (defaults to docs/project-status.json).",
    )
    args = parser.parse_args(argv)

    try:
        manifest = load_manifest(args.manifest)
        errors = validate_manifest(manifest)
    except (OSError, ValueError, json.JSONDecodeError, KeyError, TypeError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1

    if errors:
        print("FAIL: project status is not checkout-coherent.", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1
    if args.check:
        print("PASS: docs/project-status.json is schema-valid and checkout-coherent.")
    else:
        print(render_status(manifest))
    return 0


if __name__ == "__main__":
    sys.exit(main())


__all__ = [
    "DEFAULT_MANIFEST",
    "ROOT",
    "STATUS_SCHEMA",
    "load_manifest",
    "main",
    "render_status",
    "validate_manifest",
]
