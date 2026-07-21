"""Exact, handle-bound authorization for one local foundation stage."""

from __future__ import annotations

from collections.abc import Mapping
from contextlib import ExitStack, contextmanager
import copy
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import hmac
import io
import json
import math
import os
from pathlib import Path
import re
import subprocess
from types import MappingProxyType
from typing import Any, Iterator
from typing import TYPE_CHECKING
import unicodedata

from jsonschema import Draft202012Validator, FormatChecker

from pneuma_lab.converters import open_swe_traces_training as ost_converter
from pneuma_lab.converters import openhands_sampled_training as openhands_converter
from pneuma_lab.foundation.artifacts import (
    ArtifactPublicationError,
    BoundArtifactRead,
    BoundArtifactReadHandle,
    bind_artifact_publication,
    write_atomic_json,
)
from pneuma_lab.foundation.contamination import (
    CROSS_DATASET_LEAKAGE_QUARANTINE_ID,
    EVAL_REPO_QUARANTINE_ID,
    build_contamination_receipt,
)
from pneuma_lab.foundation.budget import MAX_LIFETIME_CLOUD_USD
from pneuma_lab.governance import open_swe_traces as ost_governance
from pneuma_lab.training import leakage_registry
from pneuma_lab.foundation.data import (
    ACTIVE_DATASET_GROUPS,
    build_diversity_inventory,
)
from pneuma_lab.foundation.eval_identities import (
    IdentityRecord,
    _metadata_rows,
    identity_from_foundation_record,
)
from pneuma_lab.foundation.identity_normalization import normalize_identity_text
from pneuma_lab.foundation.records import (
    EffectiveTrainingRecord,
    FoundationRecordError,
    GradientEligibility,
    LaneDisposition,
    TerminalRole,
    _make_effective_training_record,
    validate_derived_foundation_record,
    validate_foundation_record,
)
from pneuma_lab.foundation.snapshot_receipt import (
    SnapshotReceiptError,
    VerifiedPinnedSnapshot,
    verify_pinned_snapshot,
)
from pneuma_lab.foundation.specs import MODEL_SPECS
from pneuma_lab.schemas import load_schema

if TYPE_CHECKING:
    from pneuma_lab.foundation.preparation import PreparationResult


APPROVAL_PHRASE_PREFIX = "I APPROVE THIS EXACT PNEUMA FOUNDATION SCOPE"
_OPENHANDS_LANE_ID = "swe-gym-openhands-sampled"
_OST_LANE_ID = "open-swe-traces"
_AUTHORIZED_LANE_WEIGHTS = {_OPENHANDS_LANE_ID: 1.0}
_MULTI_LANE_AUTHORIZED_LANE_WEIGHTS = {
    _OPENHANDS_LANE_ID: 1.0,
    _OST_LANE_ID: 1.0,
}
_SINGLE_LANE_STAGES = frozenset({"100k", "500k", "1m"})
_STAGE_TOKEN_CEILINGS = {
    "100k": 100_000,
    "500k": 500_000,
    "1m": 1_000_000,
    "2m": 2_000_000,
    "8m": 8_000_000,
    "16m": 16_000_000,
    "32m": 32_000_000,
}


def _stage_lane_ids(stage: str) -> tuple[str, ...]:
    """Exact gradient lanes per stage: OpenHands only before 2m, both after."""

    if stage in _SINGLE_LANE_STAGES:
        return (_OPENHANDS_LANE_ID,)
    return (_OPENHANDS_LANE_ID, _OST_LANE_ID)


def _stage_lane_weights(stage: str) -> dict:
    if stage in _SINGLE_LANE_STAGES:
        return dict(_AUTHORIZED_LANE_WEIGHTS)
    return dict(_MULTI_LANE_AUTHORIZED_LANE_WEIGHTS)


_ARTIFACT_FIELDS = {
    "preparation_manifest": "preparation_manifest_path",
    "suite_report": "suite_report_path",
    "license_receipt": "license_receipt_path",
    "source_presence_receipt": "source_presence_receipt_path",
    "source_integrity_receipt": "source_integrity_receipt_path",
    "shard": "shard_path",
    "shard_manifest": "shard_manifest_path",
    "split_receipt": "split_receipt_path",
    "contamination_receipt": "contamination_receipt_path",
    "diversity_receipt": "diversity_receipt_path",
    "selection_receipt": "selection_receipt_path",
}
_CONVERSION_ARTIFACT_FIELDS = {
    "examples": "conversion_examples_path",
    "invalid_examples": "conversion_invalid_examples_path",
    "conversion_report": "conversion_report_path",
    "hash_manifest": "conversion_hash_manifest_path",
}
_CONVERSION_PAYLOAD_NAMES = {
    name: f"conversion:{name}" for name in _CONVERSION_ARTIFACT_FIELDS
}
_MULTI_LANE_ARTIFACT_FIELDS = {
    **_ARTIFACT_FIELDS,
    "ost_license_receipt": "ost_license_receipt_path",
    "leakage_receipt": "leakage_receipt_path",
}
_CONVERSION_FILENAMES = {
    "examples": "examples.jsonl",
    "invalid_examples": "invalid_examples.jsonl",
    "conversion_report": "conversion_report.json",
    "hash_manifest": "hash_manifest.json",
}
_EVAL_PAYLOAD_PREFIX = "eval_identity:"
_REQUIRED_EVAL_FAMILIES = ("swe-bench", "swe-mera", "swe-polybench")
_OPENHANDS_SOURCE_PATHS = (
    "processed/swe-gym/openhands-sampled/pneuma_traces.jsonl",
    "processed/swe-gym/openhands-sampled/adapter_report.json",
)
_OST_SOURCE_PATHS = (
    "processed/open-swe-traces/pneuma-trace/pneuma_traces.jsonl",
    "processed/open-swe-traces/pneuma-trace/adapter_report.json",
)
_LEAKAGE_REGISTRY_RELATIVE_PATH = (
    "docs/data/training-readiness/cross-dataset-leakage-registry.json"
)
_LEAKAGE_DIGEST_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
_FIRST_STAGE_DISPOSITION = LaneDisposition(
    terminal_role=TerminalRole.TRAIN,
    gradient_eligibility=GradientEligibility.FIRST_STAGE,
    license_disposition="local_research_candidate_no_redistribution",
    privacy_disposition="redaction_verified",
    dual_use_disposition="not_flagged",
    oracle_disposition="target_only",
)
_OST_LANE_DISPOSITION = LaneDisposition(
    terminal_role=TerminalRole.TRAIN,
    gradient_eligibility=GradientEligibility.LATER,
    license_disposition="local_research_candidate_no_redistribution",
    privacy_disposition="digest_only_by_construction",
    dual_use_disposition="not_flagged",
    oracle_disposition="target_only",
)


@dataclass(frozen=True)
class _LaneRules:
    lane_id: str
    family: str
    dataset_id: str
    gradient_eligibility: str
    disposition: LaneDisposition
    converter: Any
    converter_name: str
    source_paths: tuple[str, str]


_LANE_RULES = {
    _OPENHANDS_LANE_ID: _LaneRules(
        lane_id=_OPENHANDS_LANE_ID,
        family="swe-gym",
        dataset_id=_OPENHANDS_LANE_ID,
        gradient_eligibility="first_stage",
        disposition=_FIRST_STAGE_DISPOSITION,
        converter=openhands_converter,
        converter_name="openhands-sampled-training",
        source_paths=_OPENHANDS_SOURCE_PATHS,
    ),
    _OST_LANE_ID: _LaneRules(
        lane_id=_OST_LANE_ID,
        family="open-swe-traces",
        dataset_id=_OST_LANE_ID,
        gradient_eligibility="later",
        disposition=_OST_LANE_DISPOSITION,
        converter=ost_converter,
        converter_name="open-swe-traces-training",
        source_paths=_OST_SOURCE_PATHS,
    ),
}
_RECEIPT_FILENAMES = {
    "suite_report": "suite_report.json",
    "license_receipt": "license_receipt.json",
    "source_presence_receipt": "source_presence_receipt.json",
    "source_integrity_receipt": "source_integrity_receipt.json",
    "split_receipt": "split_receipt.json",
    "contamination_receipt": "contamination_receipt.json",
    "diversity_receipt": "diversity_receipt.json",
    "selection_receipt": "selection_receipt.json",
}
_MULTI_LANE_RECEIPT_FILENAMES = {
    **_RECEIPT_FILENAMES,
    "ost_license_receipt": "ost_license_receipt.json",
    "leakage_receipt": "leakage_receipt.json",
}


def _artifact_fields(stage: str) -> dict[str, str]:
    if stage in _SINGLE_LANE_STAGES:
        return _ARTIFACT_FIELDS
    return _MULTI_LANE_ARTIFACT_FIELDS


def _receipt_filenames(stage: str) -> dict[str, str]:
    if stage in _SINGLE_LANE_STAGES:
        return _RECEIPT_FILENAMES
    return _MULTI_LANE_RECEIPT_FILENAMES


def _conversion_payload_name(stage: str, lane_id: str, name: str) -> str:
    if stage in _SINGLE_LANE_STAGES:
        return _CONVERSION_PAYLOAD_NAMES[name]
    return f"conversion:{lane_id}:{name}"


_LOCAL_PROFILE = {
    "profile": "wsl2_local_nf4",
    "quantization": "nf4_double_quant",
    "core_dtype": "bf16",
    "projection_dtype": "bf16",
    "gradient_checkpointing": True,
    "sequence_length": 512,
    "microbatch_size": 1,
    "gradient_accumulation": 32,
    "data_loader_workers": 8,
    "max_ram_gb": 24.0,
    "max_vram_gb": 7.5,
}
_BUDGET = {
    "paid_compute_usd": 0,
    "paid_compute_ceiling_usd": 0,
    "cloud_jobs_used": 0,
    "cloud_jobs_ceiling": 0,
    "cloud_lifetime_cap_usd": 45,
}
_SOURCE_POLICY = {
    "root": "C:\\pneuma-data",
    "write_allowed": False,
    "private_cloud_transfer": False,
}
_CLOUD_SOURCE_POLICY = {
    "root": "bundle://authorized-shard",
    "write_allowed": False,
    "private_cloud_transfer": False,
    "private_cloud_transfer_allowed": True,
}
_CLOUD_BUDGET_KEYS = {
    "paid_compute_usd",
    "paid_compute_ceiling_usd",
    "cloud_jobs_used",
    "cloud_job_ceiling",
    "cloud_lifetime_cap_usd",
}
_LOCAL_GATE_REPORT_SIZE_CEILING = 4 * 1024 * 1024
_OUTPUT_ROOT = "build/foundation/runs/"
_PROTECTED_DATA_ROOT = Path(r"C:\pneuma-data")
_COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40}$")
_DIGEST_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_UTC_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z$")
_MIB = 1024 * 1024
_GIB = 1024 * _MIB
_AUTHORIZATION_MANIFEST_SIZE_CEILING = 8 * _MIB


class FoundationAuthorizationError(ValueError):
    """Raised before model allocation when an authorization binding fails."""


def _artifact_size_limits(
    stage: str,
    eval_families: tuple[str, ...],
) -> tuple[dict[str, int], int]:
    if stage not in _STAGE_TOKEN_CEILINGS:
        raise FoundationAuthorizationError("artifact size ceiling stage is invalid")
    token_ceiling = _STAGE_TOKEN_CEILINGS[stage]
    lane_ids = _stage_lane_ids(stage)
    limits = {
        "preparation_manifest": 4 * _MIB,
        "suite_report": 4 * _MIB,
        "license_receipt": 1 * _MIB,
        "source_presence_receipt": 16 * _MIB,
        "source_integrity_receipt": 16 * _MIB,
        "shard": max(4 * _MIB, token_ceiling * 96),
        "shard_manifest": 8 * _MIB,
        # Split assignments scale with the converted-lane example count,
        # not the stage token ceiling: the full Open-SWE-Traces lane alone
        # contributes ~161k assignments (~67 MiB measured at 2m).
        "split_receipt": (
            max(4 * _MIB, token_ceiling * 16)
            if stage in _SINGLE_LANE_STAGES
            else 256 * _MIB
        ),
        "contamination_receipt": 16 * _MIB,
        "diversity_receipt": 8 * _MIB,
        "selection_receipt": 8 * _MIB,
    }
    if stage not in _SINGLE_LANE_STAGES:
        limits["ost_license_receipt"] = 1 * _MIB
        limits["leakage_receipt"] = 4 * _MIB
    # Conversion always renders the full approved lane before stage
    # selection, so the examples payload scales with the lane (about
    # 16 MiB for the 6k-trace OpenHands-Sampled lane and ~554 MiB
    # measured for the full 161k-trace Open-SWE-Traces lane), not with
    # the stage token ceiling.
    for lane_id in lane_ids:
        limits[_conversion_payload_name(stage, lane_id, "examples")] = max(
            1 * _GIB if stage not in _SINGLE_LANE_STAGES else 64 * _MIB,
            token_ceiling * 128,
        )
        limits[_conversion_payload_name(stage, lane_id, "invalid_examples")] = 1 * _MIB
        limits[_conversion_payload_name(stage, lane_id, "conversion_report")] = 8 * _MIB
        limits[_conversion_payload_name(stage, lane_id, "hash_manifest")] = 2 * _MIB
    eval_limit = min(
        256 * _MIB,
        max(4 * _MIB, token_ceiling * 64),
    )
    limits.update(
        {f"{_EVAL_PAYLOAD_PREFIX}{family}": eval_limit for family in eval_families}
    )
    # Strict JSON/JSONL materialization can transiently amplify held bytes by
    # roughly 8x. Keep the aggregate under 2 GiB so parsing remains bounded
    # beneath the 24 GiB local process envelope even at the largest stage.
    # Multi-lane stages hold the full converted lanes at once, so they use
    # the fixed 2 GiB aggregate rather than the token-scaled bound.
    if stage in _SINGLE_LANE_STAGES:
        total_limit = min(
            2 * _GIB,
            max(128 * _MIB, token_ceiling * 64),
        )
    else:
        total_limit = 2 * _GIB
    return limits, total_limit


def _validate_declared_size_limits(
    bindings: Mapping[str, Mapping],
    *,
    limits: Mapping[str, int],
    total_limit: int,
) -> None:
    if set(bindings) != set(limits):
        raise FoundationAuthorizationError(
            "authorized artifact size-limit set is incomplete"
        )
    total = 0
    for name, binding in bindings.items():
        size = binding.get("size") if isinstance(binding, Mapping) else None
        if type(size) is not int or size < 0 or size > limits[name]:
            raise FoundationAuthorizationError(
                f"authorized artifact declared size exceeds ceiling: {name}"
            )
        total += size
    if total > total_limit:
        raise FoundationAuthorizationError(
            "authorized artifact declared total exceeds size ceiling"
        )


@dataclass(frozen=True)
class VerifiedFoundationAuthorization:
    model_key: str
    token_ceiling: int
    shard_path: Path
    shard_manifest_path: Path
    output_root: Path
    authorized_lane_weights: Mapping
    authorized_record_membership: Mapping
    scope_digest: str
    manifest: Mapping


@dataclass
class _HeldArtifact:
    path: Path
    handle: BoundArtifactReadHandle
    read: BoundArtifactRead


def _semantic_key(key: str) -> str:
    return unicodedata.normalize("NFKC", key).casefold()


def _validated_json_value(value: Any, *, path: str = "scope") -> Any:
    if value is None or isinstance(value, (str, bool)):
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise FoundationAuthorizationError(f"{path} JSON number must be finite")
        return value
    if isinstance(value, list):
        return [
            _validated_json_value(item, path=f"{path}[{index}]")
            for index, item in enumerate(value)
        ]
    if isinstance(value, Mapping):
        result = {}
        semantic_keys: set[str] = set()
        for key, item in value.items():
            if not isinstance(key, str):
                raise FoundationAuthorizationError(
                    f"{path} JSON object key must be a string"
                )
            semantic = _semantic_key(key)
            if semantic in semantic_keys:
                raise FoundationAuthorizationError(
                    f"{path} contains duplicate semantic key aliases"
                )
            semantic_keys.add(semantic)
            result[key] = _validated_json_value(item, path=f"{path}.{key}")
        return result
    raise FoundationAuthorizationError(
        f"{path} is not JSON-safe: {type(value).__name__}"
    )


def _reject_constant(value: str) -> None:
    raise FoundationAuthorizationError(f"JSON number must be finite: {value}")


def _strict_pairs(pairs: list[tuple[str, Any]]) -> dict:
    result = {}
    semantic_keys: set[str] = set()
    for key, value in pairs:
        if key in result:
            raise FoundationAuthorizationError(f"duplicate JSON member: {key}")
        semantic = _semantic_key(key)
        if semantic in semantic_keys:
            raise FoundationAuthorizationError(
                f"duplicate semantic JSON member alias: {key}"
            )
        semantic_keys.add(semantic)
        result[key] = value
    return result


def _strict_json_bytes(payload: bytes, *, label: str) -> dict:
    try:
        value = json.loads(
            payload.decode("utf-8"),
            object_pairs_hook=_strict_pairs,
            parse_constant=_reject_constant,
        )
    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
        FoundationAuthorizationError,
    ) as exc:
        raise FoundationAuthorizationError(
            f"cannot load strict JSON {label}: {exc}"
        ) from exc
    if not isinstance(value, dict):
        raise FoundationAuthorizationError(f"expected JSON object: {label}")
    return value


def _strict_jsonl_records(payload: bytes, *, label: str) -> tuple[dict, ...]:
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise FoundationAuthorizationError(
            f"cannot decode strict JSONL {label}: {exc}"
        ) from exc
    if not text or not text.endswith("\n"):
        raise FoundationAuthorizationError(
            f"{label} must be nonempty newline-terminated JSONL"
        )
    records = []
    for index, line in enumerate(text.splitlines(), start=1):
        if not line:
            raise FoundationAuthorizationError(
                f"{label} contains a blank line at {index}"
            )
        records.append(
            _strict_json_bytes(line.encode("utf-8"), label=f"{label} line {index}")
        )
    return tuple(records)


def _is_exact_positive_zero(value: Any) -> bool:
    return type(value) is float and value == 0.0 and math.copysign(1.0, value) > 0


def _require_digest(value: Any, *, label: str) -> str:
    if not isinstance(value, str) or not _DIGEST_PATTERN.fullmatch(value):
        raise FoundationAuthorizationError(f"{label} must be a SHA-256 digest")
    return value


def _coherence_error(detail: str) -> FoundationAuthorizationError:
    return FoundationAuthorizationError(
        f"foundation authorization artifact coherence failed: {detail}"
    )


def authorization_scope_digest(scope: Mapping) -> str:
    """Return the strict canonical digest of an immutable authorization scope."""

    canonical = _validated_json_value(scope)
    payload = json.dumps(
        canonical,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _canonical_record_digest(record: Mapping) -> str:
    canonical = _validated_json_value(record, path="foundation_record")
    payload = json.dumps(
        canonical,
        allow_nan=False,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _absolute_lexical(path: Path) -> Path:
    candidate = Path(path)
    if ".." in candidate.parts:
        raise FoundationAuthorizationError(
            "authorization path contains parent traversal"
        )
    if not candidate.is_absolute():
        candidate = Path.cwd() / candidate
    return Path(os.path.abspath(candidate))


def _inside(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def _repo_relative(path: Path, *, repo_root: Path) -> str:
    root = _absolute_lexical(repo_root)
    candidate = _absolute_lexical(path)
    build_root = root / "build"
    if not _inside(candidate, build_root) or candidate == build_root:
        raise FoundationAuthorizationError(
            "authorization artifacts must be physical files under repository build/"
        )
    return candidate.relative_to(root).as_posix()


def _path_from_binding(binding: Mapping, *, repo_root: Path) -> Path:
    relative = binding.get("path")
    if (
        not isinstance(relative, str)
        or not relative.startswith("build/")
        or "\\" in relative
        or ".." in Path(relative).parts
    ):
        raise FoundationAuthorizationError("artifact binding path is not canonical")
    path = _absolute_lexical(Path(repo_root) / Path(relative))
    if _repo_relative(path, repo_root=repo_root) != relative:
        raise FoundationAuthorizationError("artifact binding path is not canonical")
    return path


def _task7_tokenizer_snapshot_path(path: Path, *, repo_root: Path) -> Path:
    """Validate the exact local Task 7 cache layout without resolving aliases."""

    root = _absolute_lexical(repo_root)
    candidate = _absolute_lexical(path)
    try:
        relative = candidate.relative_to(root)
    except ValueError as exc:
        raise FoundationAuthorizationError(
            "tokenizer snapshot must be under repository build/"
        ) from exc
    revision = MODEL_SPECS["2b"].revision
    if (
        len(relative.parts) < 5
        or relative.parts[0] != "build"
        or tuple(relative.parts[-3:]) != ("models", "2b", revision)
    ):
        raise FoundationAuthorizationError(
            "tokenizer snapshot path must match "
            f"build/<cache_root>/models/2b/{revision}"
        )
    return candidate


def _verify_authorization_snapshot(
    path: Path,
    *,
    repo_root: Path,
) -> VerifiedPinnedSnapshot:
    exact = _task7_tokenizer_snapshot_path(path, repo_root=repo_root)
    try:
        return verify_pinned_snapshot("2b", snapshot_path=exact)
    except SnapshotReceiptError as exc:
        raise FoundationAuthorizationError(
            f"pinned tokenizer snapshot verification failed: {exc}"
        ) from exc


def _snapshot_scope(
    verified: VerifiedPinnedSnapshot,
    *,
    repo_root: Path,
) -> dict:
    return {
        "path": _repo_relative(verified.snapshot_path, repo_root=repo_root),
        "model_id": verified.model_id,
        "revision": verified.revision,
        "receipt_sha256": verified.receipt_sha256,
        "snapshot_sha256": verified.snapshot_sha256,
    }


def _scope_snapshot_path(scope: Mapping, *, repo_root: Path) -> Path:
    binding = scope.get("tokenizer_snapshot")
    if not isinstance(binding, Mapping):
        raise FoundationAuthorizationError(
            "authorization tokenizer snapshot binding is missing"
        )
    path = _path_from_binding(binding, repo_root=repo_root)
    return _task7_tokenizer_snapshot_path(path, repo_root=repo_root)


def _assert_snapshot_binding(
    binding: Mapping,
    verified: VerifiedPinnedSnapshot,
    *,
    repo_root: Path,
) -> None:
    expected = _snapshot_scope(verified, repo_root=repo_root)
    if dict(binding) != expected:
        raise FoundationAuthorizationError(
            "authorization tokenizer snapshot binding changed"
        )


def _load_authorization_tokenizer(snapshot: Path):
    """Load tokenizer metadata only, with network access forced off."""

    previous = {
        name: os.environ.get(name)
        for name in ("HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE")
    }
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    try:
        try:
            from transformers import AutoTokenizer
        except ImportError as exc:
            raise FoundationAuthorizationError(
                "transformers is required to recount with the pinned tokenizer"
            ) from exc
        return AutoTokenizer.from_pretrained(
            str(snapshot),
            local_files_only=True,
            trust_remote_code=False,
        )
    finally:
        for name, value in previous.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


def _load_and_reverify_tokenizer(
    verified: VerifiedPinnedSnapshot,
    *,
    repo_root: Path,
    tokenizer_loader,
):
    loader = tokenizer_loader or _load_authorization_tokenizer
    try:
        tokenizer = loader(verified.snapshot_path)
    except FoundationAuthorizationError:
        raise
    except Exception as exc:
        raise FoundationAuthorizationError(
            f"pinned tokenizer load failed: {exc}"
        ) from exc
    after_load = _verify_authorization_snapshot(
        verified.snapshot_path,
        repo_root=repo_root,
    )
    if after_load != verified:
        raise FoundationAuthorizationError(
            "pinned tokenizer snapshot changed during local load"
        )
    if not callable(getattr(tokenizer, "encode", None)):
        raise FoundationAuthorizationError("loaded tokenizer has no encode method")
    return tokenizer


@contextmanager
def _hold_artifacts(
    paths: Mapping[str, Path],
    *,
    repo_root: Path,
    max_sizes: Mapping[str, int] | None = None,
    max_total_size: int | None = None,
) -> Iterator[dict[str, _HeldArtifact]]:
    root = _absolute_lexical(repo_root)
    build_root = root / "build"
    held: dict[str, _HeldArtifact] = {}
    forbidden_roots = (
        (_PROTECTED_DATA_ROOT,) if _PROTECTED_DATA_ROOT.is_absolute() else ()
    )
    try:
        with ExitStack() as stack:
            opened = {}
            for name, raw_path in paths.items():
                path = _absolute_lexical(raw_path)
                _repo_relative(path, repo_root=root)
                publication = stack.enter_context(
                    bind_artifact_publication(
                        path.parent,
                        anchor_root=root,
                        allowed_root=build_root,
                        forbidden_roots=forbidden_roots,
                    )
                )
                handle = stack.enter_context(publication.hold_read(path))
                opened[name] = (path, handle)
            total_size = sum(handle.size for _path, handle in opened.values())
            for name, (_path, handle) in opened.items():
                maximum = max_sizes.get(name) if max_sizes is not None else None
                if maximum is not None and handle.size > maximum:
                    raise FoundationAuthorizationError(
                        f"authorized artifact exceeds size ceiling: {name}"
                    )
            if max_total_size is not None and total_size > max_total_size:
                raise FoundationAuthorizationError(
                    "authorized artifact set exceeds total size ceiling"
                )
            for name, (path, handle) in opened.items():
                held[name] = _HeldArtifact(
                    path=path,
                    handle=handle,
                    read=handle.read_bytes(),
                )
            yield held
    except FoundationAuthorizationError:
        raise
    except (
        ArtifactPublicationError,
        OSError,
        RuntimeError,
        TypeError,
        ValueError,
    ) as exc:
        raise FoundationAuthorizationError(f"artifact binding failed: {exc}") from exc


def _revalidate_held(held: Mapping[str, _HeldArtifact]) -> None:
    for item in held.values():
        item.handle.revalidate(item.read)


def artifact_binding(path: Path, repo_root: Path) -> dict:
    """Bind one artifact from a single no-follow handle read."""

    with _hold_artifacts({"artifact": Path(path)}, repo_root=repo_root) as held:
        item = held["artifact"]
        _revalidate_held(held)
        return {
            "path": _repo_relative(item.path, repo_root=repo_root),
            "sha256": item.read.sha256,
            "size": item.read.size,
        }


def _git(repo_root: Path, *arguments: str) -> str:
    try:
        completed = subprocess.run(
            ["git", *arguments],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise FoundationAuthorizationError(f"cannot inspect git state: {exc}") from exc
    return completed.stdout.strip()


def current_clean_code_commit(repo_root: Path) -> str:
    """Return HEAD only when the repository has no tracked or untracked changes."""

    root = _absolute_lexical(repo_root)
    commit = _git(root, "rev-parse", "HEAD")
    if not _COMMIT_PATTERN.fullmatch(commit):
        raise FoundationAuthorizationError("current git commit is not a full SHA-1")
    status = _git(root, "status", "--porcelain", "--untracked-files=all")
    if status:
        raise FoundationAuthorizationError(
            "foundation authorization requires a clean git checkout"
        )
    return commit


def _validate_commit_binding(repo_root: Path, code_commit: str) -> None:
    if not isinstance(code_commit, str) or not _COMMIT_PATTERN.fullmatch(code_commit):
        raise FoundationAuthorizationError(
            "code_commit must be a full lowercase git SHA-1"
        )
    current = current_clean_code_commit(repo_root)
    if not hmac.compare_digest(current, code_commit):
        raise FoundationAuthorizationError(
            "code_commit differs from the current clean checkout"
        )


def _validate_manifest(manifest: Mapping) -> None:
    validator = Draft202012Validator(
        load_schema("foundation-training-authorization.schema.json"),
        format_checker=FormatChecker(),
    )
    errors = sorted(
        validator.iter_errors(dict(manifest)), key=lambda error: list(error.path)
    )
    if errors:
        detail = "; ".join(
            f"{'.'.join(str(part) for part in error.path) or '<root>'}: {error.message}"
            for error in errors
        )
        raise FoundationAuthorizationError(f"authorization schema invalid: {detail}")


def _candidate_path(preparation: Any, *, repo_root: Path, stage: str) -> Path:
    expected = _absolute_lexical(
        Path(repo_root) / f"build/foundation/authorizations/candidates/{stage}.json"
    )
    actual = _absolute_lexical(preparation.authorization_candidate_path)
    if actual != expected:
        raise FoundationAuthorizationError("authorization candidate path is not exact")
    return actual


def _artifact_paths_from_preparation(
    preparation: Any,
    *,
    stage: str,
) -> dict[str, Path]:
    try:
        return {
            name: Path(getattr(preparation, field))
            for name, field in _artifact_fields(stage).items()
        }
    except (AttributeError, TypeError) as exc:
        raise FoundationAuthorizationError("preparation result is incomplete") from exc


def _evidence_paths_from_preparation(
    preparation: Any,
    *,
    stage: str,
) -> dict[str, Path]:
    try:
        if stage in _SINGLE_LANE_STAGES:
            paths = {
                _CONVERSION_PAYLOAD_NAMES[name]: Path(getattr(preparation, field))
                for name, field in _CONVERSION_ARTIFACT_FIELDS.items()
            }
        else:
            lane_conversion_paths = preparation.lane_conversion_paths
            lane_ids = _stage_lane_ids(stage)
            if not isinstance(lane_conversion_paths, Mapping) or set(
                lane_conversion_paths
            ) != set(lane_ids):
                raise TypeError("lane conversion paths are incomplete")
            paths = {}
            for lane_id in lane_ids:
                lane_paths = lane_conversion_paths[lane_id]
                if not isinstance(lane_paths, Mapping) or set(lane_paths) != set(
                    _CONVERSION_ARTIFACT_FIELDS
                ):
                    raise TypeError("lane conversion paths are incomplete")
                for name in _CONVERSION_ARTIFACT_FIELDS:
                    paths[_conversion_payload_name(stage, lane_id, name)] = Path(
                        lane_paths[name]
                    )
        eval_paths = preparation.eval_identity_paths
        if not isinstance(eval_paths, Mapping) or not eval_paths:
            raise TypeError("evaluation identity paths are incomplete")
        for family, path in eval_paths.items():
            if not isinstance(family, str) or not re.fullmatch(
                r"[a-z0-9][a-z0-9-]*", family
            ):
                raise TypeError("evaluation identity family is invalid")
            paths[f"{_EVAL_PAYLOAD_PREFIX}{family}"] = Path(path)
        return paths
    except (AttributeError, TypeError) as exc:
        raise FoundationAuthorizationError(
            "preparation evidence result is incomplete"
        ) from exc


def _flatten_scope_bindings(scope: Mapping, *, stage: str) -> dict[str, Mapping]:
    evidence = scope.get("evidence_artifacts")
    if not isinstance(evidence, Mapping) or set(evidence) != {
        "conversion",
        "eval_identities",
    }:
        raise _coherence_error("scope evidence artifact groups are incomplete")
    conversion = evidence.get("conversion")
    eval_identities = evidence.get("eval_identities")
    if (
        not isinstance(conversion, Mapping)
        or not isinstance(eval_identities, Mapping)
        or not eval_identities
    ):
        raise _coherence_error("scope evidence artifact bindings are incomplete")
    flattened = {}
    if stage in _SINGLE_LANE_STAGES:
        if set(conversion) != set(_CONVERSION_ARTIFACT_FIELDS):
            raise _coherence_error("scope evidence artifact bindings are incomplete")
        flattened.update(
            {
                _CONVERSION_PAYLOAD_NAMES[name]: binding
                for name, binding in conversion.items()
            }
        )
    else:
        lane_ids = _stage_lane_ids(stage)
        if set(conversion) != set(lane_ids):
            raise _coherence_error("scope evidence artifact bindings are incomplete")
        for lane_id in lane_ids:
            lane_group = conversion[lane_id]
            if not isinstance(lane_group, Mapping) or set(lane_group) != set(
                _CONVERSION_ARTIFACT_FIELDS
            ):
                raise _coherence_error(
                    "scope evidence artifact bindings are incomplete"
                )
            flattened.update(
                {
                    _conversion_payload_name(stage, lane_id, name): binding
                    for name, binding in lane_group.items()
                }
            )
    for family, binding in eval_identities.items():
        if not isinstance(family, str) or not re.fullmatch(
            r"[a-z0-9][a-z0-9-]*", family
        ):
            raise _coherence_error("scope evaluation identity family is invalid")
        flattened[f"{_EVAL_PAYLOAD_PREFIX}{family}"] = binding
    return flattened


def _validate_exact_preparation_paths(
    paths: Mapping[str, Path],
    evidence_paths: Mapping[str, Path],
    *,
    repo_root: Path,
    stage: str,
) -> None:
    preparation_root = _absolute_lexical(
        Path(repo_root) / "build/foundation/preparation" / stage
    )
    if _absolute_lexical(paths["preparation_manifest"].parent) != preparation_root:
        raise FoundationAuthorizationError(
            "preparation root is not the exact repository stage root"
        )
    expected_direct = {
        "preparation_manifest": "preparation_manifest.json",
        "suite_report": "suite_report.json",
        "license_receipt": "license_receipt.json",
        "source_presence_receipt": "source_presence_receipt.json",
        "source_integrity_receipt": "source_integrity_receipt.json",
        "split_receipt": "split_receipt.json",
        "contamination_receipt": "contamination_receipt.json",
        "diversity_receipt": "diversity_receipt.json",
        "selection_receipt": "selection_receipt.json",
    }
    if stage not in _SINGLE_LANE_STAGES:
        expected_direct = {
            **expected_direct,
            "ost_license_receipt": "ost_license_receipt.json",
            "leakage_receipt": "leakage_receipt.json",
        }
    if set(paths) != set(expected_direct) | {"shard", "shard_manifest"}:
        raise FoundationAuthorizationError(
            "preparation artifact path set is not exact for this stage"
        )
    for name, filename in expected_direct.items():
        if _absolute_lexical(paths[name]) != preparation_root / filename:
            raise FoundationAuthorizationError(f"preparation {name} path is not exact")
    shard_root = preparation_root / "shards"
    if (
        _absolute_lexical(paths["shard"].parent) != shard_root
        or _absolute_lexical(paths["shard_manifest"].parent) != shard_root
    ):
        raise FoundationAuthorizationError("preparation shard paths are not exact")
    for lane_id in _stage_lane_ids(stage):
        for name in _CONVERSION_ARTIFACT_FIELDS:
            key = _conversion_payload_name(stage, lane_id, name)
            if stage in _SINGLE_LANE_STAGES:
                expected = preparation_root / "conversion" / _CONVERSION_FILENAMES[name]
            else:
                expected = (
                    preparation_root
                    / "conversion"
                    / lane_id
                    / _CONVERSION_FILENAMES[name]
                )
            if _absolute_lexical(evidence_paths[key]) != expected:
                raise FoundationAuthorizationError(
                    f"preparation conversion {name} path is not exact"
                )
    eval_keys = {
        key.removeprefix(_EVAL_PAYLOAD_PREFIX)
        for key in evidence_paths
        if key.startswith(_EVAL_PAYLOAD_PREFIX)
    }
    if not eval_keys:
        raise FoundationAuthorizationError(
            "preparation evaluation identity paths are incomplete"
        )
    for family in eval_keys:
        key = f"{_EVAL_PAYLOAD_PREFIX}{family}"
        expected = preparation_root / "eval-identities" / f"{family}.jsonl"
        if _absolute_lexical(evidence_paths[key]) != expected:
            raise FoundationAuthorizationError(
                f"preparation evaluation identity {family} path is not exact"
            )
    normalized = tuple(
        _absolute_lexical(path) for path in (*paths.values(), *evidence_paths.values())
    )
    if len(normalized) != len(set(normalized)):
        raise FoundationAuthorizationError(
            "preparation artifact paths must be distinct"
        )


def _validate_preparation_coherence_unchecked(
    scope: Mapping,
    bound_payloads: Mapping[str, BoundArtifactRead],
    *,
    tokenizer,
    repo_root: Path,
) -> dict[str, str]:
    """Prove all held preparation artifacts describe one exact local run."""

    stage = scope.get("stage")
    if stage not in _STAGE_TOKEN_CEILINGS:
        raise _coherence_error("scope stage is unknown")
    lane_ids = _stage_lane_ids(stage)
    multi_lane = len(lane_ids) > 1
    artifact_fields = _artifact_fields(stage)
    receipt_filenames = _receipt_filenames(stage)
    evidence_bindings = _flatten_scope_bindings(scope, stage=stage)
    expected_payloads = set(artifact_fields) | set(evidence_bindings)
    if set(bound_payloads) != expected_payloads:
        raise _coherence_error("bound artifact set is incomplete")
    bindings = scope.get("artifacts")
    if not isinstance(bindings, Mapping) or set(bindings) != set(artifact_fields):
        raise _coherence_error("scope artifact bindings are incomplete")
    flattened_bindings = {**bindings, **evidence_bindings}
    for name, read in bound_payloads.items():
        binding = flattened_bindings[name]
        if (
            not isinstance(binding, Mapping)
            or binding.get("sha256") != read.sha256
            or binding.get("size") != read.size
        ):
            raise _coherence_error(f"scope binding differs from held {name}")

    parsed = {
        name: _strict_json_bytes(read.payload, label=name.replace("_", " "))
        for name, read in bound_payloads.items()
        if name in artifact_fields and name != "shard"
    }
    records = _strict_jsonl_records(
        bound_payloads["shard"].payload,
        label="foundation shard",
    )
    preparation = parsed["preparation_manifest"]
    model = scope.get("model")
    if not isinstance(model, Mapping) or model.get("key") not in MODEL_SPECS:
        raise _coherence_error("scope model key is not pinned")
    spec = MODEL_SPECS[model["key"]]
    if spec.key != "2b":
        raise _coherence_error(
            "the first local preparation authorizes only the exact 2b model"
        )
    expected_model = {
        "key": spec.key,
        "model_id": spec.model_id,
        "revision": spec.revision,
        "tokenizer_id": spec.model_id,
        "tokenizer_revision": spec.revision,
    }
    if dict(model) != expected_model:
        raise _coherence_error("scope model and tokenizer pin changed")
    token_ceiling = _STAGE_TOKEN_CEILINGS[stage]
    if scope.get("token_ceiling") != token_ceiling:
        raise _coherence_error("scope stage and token ceiling differ")
    if multi_lane:
        lane_binding_exact = (
            preparation.get("gradient_lanes") == list(lane_ids)
            and "gradient_lane" not in preparation
        )
    else:
        lane_binding_exact = (
            preparation.get("gradient_lane") == "swe-gym-openhands-sampled"
            and "gradient_lanes" not in preparation
        )
    if (
        preparation.get("manifest_kind") != "pneuma_foundation_preparation_manifest"
        or preparation.get("manifest_schema_version") != "0.1.0"
        or preparation.get("stage") != stage
        or preparation.get("token_ceiling") != token_ceiling
        or preparation.get("dry_run") is not False
        or preparation.get("dataset_suite") != "all_ten_governed_groups"
        or not lane_binding_exact
        or preparation.get("training_authorized") is not False
        or not _is_exact_positive_zero(preparation.get("persisted_training_weight"))
    ):
        raise _coherence_error("preparation scope fields are not exact")

    prepared_tokenizer = preparation.get("tokenizer_snapshot")
    scoped_tokenizer = scope.get("tokenizer_snapshot")
    if (
        not isinstance(prepared_tokenizer, Mapping)
        or prepared_tokenizer.get("model_id") != spec.model_id
    ):
        raise _coherence_error("preparation tokenizer model differs from scope")
    if prepared_tokenizer.get("revision") != spec.revision:
        raise _coherence_error("preparation tokenizer revision differs from scope")
    tokenizer_receipt_digest = _require_digest(
        prepared_tokenizer.get("receipt_sha256"),
        label="tokenizer receipt",
    )
    tokenizer_snapshot_digest = _require_digest(
        prepared_tokenizer.get("snapshot_sha256"),
        label="tokenizer snapshot",
    )
    if (
        not isinstance(scoped_tokenizer, Mapping)
        or scoped_tokenizer.get("model_id") != spec.model_id
        or scoped_tokenizer.get("revision") != spec.revision
        or scoped_tokenizer.get("receipt_sha256") != tokenizer_receipt_digest
        or scoped_tokenizer.get("snapshot_sha256") != tokenizer_snapshot_digest
    ):
        raise _coherence_error("scope tokenizer snapshot differs from preparation")

    receipt_digests = preparation.get("receipt_sha256")
    expected_receipt_names = set(receipt_filenames.values())
    if (
        not isinstance(receipt_digests, Mapping)
        or set(receipt_digests) != expected_receipt_names
    ):
        raise _coherence_error("preparation receipt digest map is not exact")
    for binding_name, filename in receipt_filenames.items():
        expected = _require_digest(
            receipt_digests[filename],
            label=f"{filename} receipt binding",
        )
        if not hmac.compare_digest(expected, bound_payloads[binding_name].sha256):
            raise _coherence_error(f"{filename} digest differs from held bytes")

    generated = preparation.get("generated_artifact_sha256")
    if (
        not isinstance(generated, Mapping)
        or set(generated) != {"conversion", "eval_identities"}
        or generated != scope.get("evidence_artifacts")
    ):
        raise _coherence_error("generated artifact digest groups are incomplete")
    conversion = generated["conversion"]
    if multi_lane:
        if not isinstance(conversion, Mapping) or set(conversion) != set(lane_ids):
            raise _coherence_error("generated conversion digest map is incomplete")
        conversion_groups = {}
        for lane_id in lane_ids:
            lane_group = conversion[lane_id]
            if not isinstance(lane_group, Mapping) or set(lane_group) != set(
                _CONVERSION_ARTIFACT_FIELDS
            ):
                raise _coherence_error("generated conversion digest map is incomplete")
            conversion_groups[lane_id] = lane_group
    else:
        if not isinstance(conversion, Mapping) or set(conversion) != set(
            _CONVERSION_ARTIFACT_FIELDS
        ):
            raise _coherence_error("generated conversion digest map is incomplete")
        conversion_groups = {lane_ids[0]: conversion}
    eval_digests = generated["eval_identities"]
    if not isinstance(eval_digests, Mapping) or not eval_digests:
        raise _coherence_error("generated evaluation identity digests are empty")
    for family, binding in eval_digests.items():
        if not isinstance(family, str) or not family:
            raise _coherence_error("generated evaluation family is invalid")
        if not isinstance(binding, Mapping):
            raise _coherence_error("generated evaluation binding is invalid")

    source_receipt_hashes = preparation.get("source_receipt_hashes")
    if not isinstance(source_receipt_hashes, list) or source_receipt_hashes != sorted(
        set(source_receipt_hashes)
    ):
        raise _coherence_error("preparation source receipt hashes are not canonical")
    for digest in source_receipt_hashes:
        _require_digest(digest, label="preparation source receipt")
    required_source_digests = {
        bound_payloads["license_receipt"].sha256,
        tokenizer_receipt_digest,
        tokenizer_snapshot_digest,
    }
    for lane_id in lane_ids:
        required_source_digests.add(
            conversion_groups[lane_id]["conversion_report"]["sha256"]
        )
        required_source_digests.add(
            conversion_groups[lane_id]["hash_manifest"]["sha256"]
        )
    if multi_lane:
        required_source_digests.add(bound_payloads["ost_license_receipt"].sha256)
        required_source_digests.add(bound_payloads["leakage_receipt"].sha256)
    if not required_source_digests.issubset(source_receipt_hashes):
        raise _coherence_error("generated and tokenizer sources lack receipts")

    record_ids = []
    source_record_ids = []
    record_membership = {}
    recount_by_source_id = {}
    record_lane_by_source_id = {}
    records_per_lane = {lane_id: 0 for lane_id in lane_ids}
    recount_total = 0
    for record in records:
        try:
            validate_foundation_record(record)
        except FoundationRecordError as exc:
            raise _coherence_error(f"shard record is invalid: {exc}") from exc
        source = record.get("source")
        disposition = record.get("disposition")
        split = record.get("split")
        rendered = record.get("rendered")
        forecasts = record.get("forecast_targets")
        tokenization = record.get("tokenization")
        record_lane = source.get("lane_id") if isinstance(source, Mapping) else None
        rules = _LANE_RULES.get(record_lane) if record_lane in lane_ids else None
        if (
            not _is_exact_positive_zero(record.get("training_weight"))
            or not isinstance(source, Mapping)
            or rules is None
            or source.get("dataset_family") != rules.family
            or source.get("receipt_hashes") != source_receipt_hashes
            or not isinstance(disposition, Mapping)
            or disposition.get("terminal_role") != "train"
            or disposition.get("gradient_eligibility") != rules.gradient_eligibility
            or not isinstance(split, Mapping)
            or split.get("split_id") != "train"
            or not isinstance(rendered, Mapping)
            or not isinstance(rendered.get("target_text"), str)
            or not rendered["target_text"].strip()
            or not isinstance(tokenization, Mapping)
            or tokenization.get("tokenizer_id") != spec.model_id
            or tokenization.get("tokenizer_revision") != spec.revision
            or tokenization.get("total_tokens")
            != tokenization.get("prompt_tokens", -1)
            + tokenization.get("target_tokens", -1)
            or not isinstance(forecasts, Mapping)
            or not any(
                isinstance(target, Mapping)
                and target.get("applicable") is True
                and target.get("provenance") == "observed_outcome"
                for target in forecasts.values()
            )
        ):
            raise _coherence_error("shard record is outside the exact gradient lane")
        record_id = record["record_id"]
        source_record_id = source.get("source_record_id")
        if not isinstance(source_record_id, str) or not source_record_id:
            raise _coherence_error("shard source record ID is missing")
        try:
            prompt_tokens = len(
                tokenizer.encode(
                    rendered["prompt_text"],
                    add_special_tokens=False,
                )
            )
            target_tokens = len(
                tokenizer.encode(
                    rendered["target_text"],
                    add_special_tokens=False,
                )
            )
        except Exception as exc:
            raise _coherence_error(f"pinned tokenizer recount failed: {exc}") from exc
        if prompt_tokens <= 0 or target_tokens <= 0:
            raise _coherence_error(
                "pinned tokenizer recount produced an empty record component"
            )
        record_ids.append(record_id)
        source_record_ids.append(source_record_id)
        recount_by_source_id[source_record_id] = (
            prompt_tokens,
            target_tokens,
        )
        record_lane_by_source_id[source_record_id] = record_lane
        records_per_lane[record_lane] += 1
        recount_total += prompt_tokens + target_tokens
        record_membership[record_id] = _canonical_record_digest(record)
    if len(record_ids) != len(set(record_ids)):
        raise _coherence_error("shard record IDs are not unique")
    if len(source_record_ids) != len(set(source_record_ids)):
        raise _coherence_error("shard source record IDs are not unique")

    shard_digest = bound_payloads["shard"].sha256
    shard_entry = preparation.get("shard")
    shard_manifest = parsed["shard_manifest"]
    expected_inventory = build_diversity_inventory(records)
    if (
        not isinstance(shard_entry, Mapping)
        or shard_entry.get("artifact") != f"{shard_digest}.jsonl"
        or shard_entry.get("sha256") != shard_digest
        or shard_entry.get("example_count") != len(records)
        or shard_entry.get("manifest_artifact") != f"{shard_digest}.manifest.json"
        or shard_manifest.get("manifest_kind") != "pneuma_foundation_shard"
        or shard_manifest.get("schema_version") != "0.1.0"
        or shard_manifest.get("sha256") != shard_digest
        or shard_manifest.get("example_count") != len(records)
        or shard_manifest.get("duplicate_example_ids") != []
        or shard_manifest.get("inventory") != expected_inventory
        or shard_manifest.get("source_policy") != "read_only_external_corpus"
        or shard_manifest.get("token_ceiling") != token_ceiling
        or expected_inventory["token_count"] > token_ceiling
        or recount_total > token_ceiling
    ):
        raise _coherence_error("shard bytes, manifest, and preparation differ")

    gates = preparation.get("gates")
    expected_gates = {
        "all_ten_present": True,
        "eval_coverage_complete": True,
        "contamination_findings": 0,
        "source_unchanged": True,
        "tokenizer_recount_matches": True,
    }
    if multi_lane:
        expected_gates["cross_dataset_leakage_quarantine_applied"] = True
    if gates != expected_gates:
        raise _coherence_error("preparation gates are not exact")

    suite = parsed["suite_report"]
    suite_families = suite.get("families")
    suite_first_stage = suite.get("first_stage")
    if (
        suite.get("manifest_kind") != "pneuma_foundation_suite_report"
        or suite.get("manifest_schema_version") != "0.1.0"
        or not isinstance(suite_first_stage, Mapping)
        or suite_first_stage.get("stage") != "100k"
        or suite_first_stage.get("authorized_lane_candidates")
        != ["swe-gym-openhands-sampled"]
        or not isinstance(suite_families, list)
        or [item.get("family") for item in suite_families]
        != list(ACTIVE_DATASET_GROUPS)
        or any(item.get("exists") is not True for item in suite_families)
        or any(
            not isinstance(item.get(f"payload_access_{stage}"), str)
            for item in suite_families
        )
    ):
        raise _coherence_error("suite receipt does not prove all-ten presence")

    license_receipt = parsed["license_receipt"]
    if (
        license_receipt.get("receipt_kind") != "dataset_license_posture"
        or license_receipt.get("receipt_schema_version") != "0.1.0"
        or license_receipt.get("dataset_id") != "swe-gym-openhands-sampled"
        or license_receipt.get("decision")
        != "local_research_candidate_no_redistribution"
        or license_receipt.get("cloud_redistribution_allowed") is not False
        or license_receipt.get("requires_exact_operator_authorization") is not True
    ):
        raise _coherence_error("license receipt does not permit exact local research")

    leak_digests: frozenset[str] = frozenset()
    if multi_lane:
        ost_license = parsed["ost_license_receipt"]
        if (
            ost_license.get("receipt_kind") != "dataset_license_posture"
            or ost_license.get("receipt_schema_version") != "0.1.0"
            or ost_license.get("dataset_id") != "open-swe-traces"
            or ost_license.get("artifact_card_license_declared") is not True
            or ost_license.get("upstream_dataset_license") != "CC-BY-4.0"
            or not isinstance(ost_license.get("model_output_tos_note"), str)
            or not ost_license["model_output_tos_note"].strip()
            or ost_license.get("decision")
            != "local_research_candidate_no_redistribution"
            or ost_license.get("cloud_redistribution_allowed") is not False
            or ost_license.get("requires_exact_operator_authorization") is not True
        ):
            raise _coherence_error(
                "Open-SWE-Traces license receipt does not permit exact local research"
            )
        leakage = parsed["leakage_receipt"]
        try:
            registry_bytes = (
                _absolute_lexical(repo_root) / _LEAKAGE_REGISTRY_RELATIVE_PATH
            ).read_bytes()
        except OSError as exc:
            raise _coherence_error(
                f"committed cross-dataset leakage registry cannot be read: {exc}"
            ) from exc
        registry = _strict_json_bytes(
            registry_bytes,
            label="cross-dataset leakage registry",
        )
        registry_pairs = registry.get("pairs")
        registry_matches = (
            [
                pair
                for pair in registry_pairs
                if isinstance(pair, Mapping)
                and pair.get("dataset_a") == _OPENHANDS_LANE_ID
                and pair.get("dataset_b") == _OST_LANE_ID
            ]
            if isinstance(registry_pairs, list)
            else []
        )
        if (
            registry.get("status") != "populated"
            or registry.get("registry_version") != leakage_registry.REGISTRY_VERSION
            or len(registry_matches) != 1
        ):
            raise _coherence_error(
                "committed cross-dataset leakage registry is not a populated "
                "OpenHands/Open-SWE-Traces pair"
            )
        registry_digests = registry_matches[0].get("overlapping_repo_digests")
        receipt_digest_list = leakage.get("overlapping_repo_digests")
        if (
            leakage.get("manifest_kind")
            != "pneuma_foundation_cross_dataset_leakage_receipt"
            or leakage.get("manifest_schema_version") != "0.1.0"
            or leakage.get("registry_relative_path") != _LEAKAGE_REGISTRY_RELATIVE_PATH
            or leakage.get("registry_sha256")
            != hashlib.sha256(registry_bytes).hexdigest()
            or leakage.get("registry_version") != leakage_registry.REGISTRY_VERSION
            or leakage.get("registry_status") != "populated"
            or not isinstance(receipt_digest_list, list)
            or any(
                not isinstance(digest, str)
                or not _LEAKAGE_DIGEST_PATTERN.fullmatch(digest)
                for digest in receipt_digest_list
            )
            or receipt_digest_list != sorted(set(receipt_digest_list))
            or receipt_digest_list != registry_digests
            or leakage.get("pair")
            != {
                "dataset_a": _OPENHANDS_LANE_ID,
                "dataset_b": _OST_LANE_ID,
                "overlap_count": len(receipt_digest_list),
            }
            or leakage.get("quarantine_id") != CROSS_DATASET_LEAKAGE_QUARANTINE_ID
        ):
            raise _coherence_error(
                "leakage receipt contradicts the committed leakage registry"
            )
        leak_digests = frozenset(receipt_digest_list)

    source_presence = parsed["source_presence_receipt"]
    if (
        source_presence.get("manifest_kind")
        != "pneuma_foundation_source_presence_receipt"
        or source_presence.get("manifest_schema_version") != "0.1.0"
        or source_presence.get("all_ten_present") is not True
        or source_presence.get("before") != source_presence.get("after")
        or not isinstance(source_presence.get("before"), Mapping)
        or source_presence["before"].get("complete") is not True
        or source_presence.get("families") != source_presence["after"].get("families")
        or source_presence.get("lanes") != source_presence["after"].get("lanes")
    ):
        raise _coherence_error("source presence receipt contradicts all-ten gate")

    source_integrity = parsed["source_integrity_receipt"]
    if (
        source_integrity.get("manifest_kind")
        != "pneuma_foundation_source_integrity_receipt"
        or source_integrity.get("manifest_schema_version") != "0.1.0"
        or source_integrity.get("unchanged") is not True
        or source_integrity.get("before") != source_integrity.get("after")
        or not isinstance(source_integrity.get("before"), list)
        or not source_integrity["before"]
        or source_integrity.get("all_ten_before")
        != source_integrity.get("all_ten_after")
        or not isinstance(source_integrity.get("all_ten_before"), Mapping)
        or source_integrity["all_ten_before"].get("complete") is not True
        or source_integrity.get("tokenizer_snapshot") != prepared_tokenizer
    ):
        raise _coherence_error("source integrity receipt contradicts source gate")

    source_snapshots = source_integrity["before"]
    expected_source_paths = {
        *(path for lane_id in lane_ids for path in _LANE_RULES[lane_id].source_paths),
        *(
            f"processed/{family}/normalized_metadata.jsonl"
            for family in _REQUIRED_EVAL_FAMILIES
        ),
    }
    if len(source_snapshots) != len(expected_source_paths):
        raise _coherence_error(
            "source integrity does not contain every authorized input"
        )
    snapshots_by_path = {}
    for snapshot in source_snapshots:
        if (
            not isinstance(snapshot, Mapping)
            or set(snapshot)
            != {
                "relative_path",
                "size",
                "mtime_ns",
                "device",
                "inode",
                "sha256",
            }
            or not isinstance(snapshot.get("relative_path"), str)
            or snapshot["relative_path"] in snapshots_by_path
            or type(snapshot.get("size")) is not int
            or snapshot["size"] <= 0
            or type(snapshot.get("mtime_ns")) is not int
            or snapshot["mtime_ns"] < 0
            or type(snapshot.get("device")) is not int
            or type(snapshot.get("inode")) is not int
            or not isinstance(snapshot.get("sha256"), str)
            or not _DIGEST_PATTERN.fullmatch(snapshot["sha256"])
        ):
            raise _coherence_error("source integrity snapshot is malformed")
        snapshots_by_path[snapshot["relative_path"]] = snapshot
    if set(snapshots_by_path) != expected_source_paths:
        raise _coherence_error("source integrity paths differ from authorized inputs")

    example_ids = []
    examples_by_id = {}
    example_lane_by_id = {}
    lane_example_counts = {}
    for lane_id in lane_ids:
        rules = _LANE_RULES[lane_id]
        lane_converter = rules.converter
        examples_name = _conversion_payload_name(stage, lane_id, "examples")
        invalid_name = _conversion_payload_name(stage, lane_id, "invalid_examples")
        report_name = _conversion_payload_name(stage, lane_id, "conversion_report")
        manifest_name = _conversion_payload_name(stage, lane_id, "hash_manifest")
        examples = _strict_jsonl_records(
            bound_payloads[examples_name].payload,
            label=f"{lane_id} conversion examples",
        )
        try:
            lane_converter.validate_training_examples(
                [dict(example) for example in examples]
            )
        except (RuntimeError, TypeError, ValueError) as exc:
            raise _coherence_error(
                f"conversion examples fail the committed training schema: {exc}"
            ) from exc
        invalid_payload = bound_payloads[invalid_name].payload
        if invalid_payload != b"":
            _strict_jsonl_records(
                invalid_payload,
                label=f"{lane_id} conversion invalid examples",
            )
            raise _coherence_error("conversion invalid examples are not empty")
        conversion_report = _strict_json_bytes(
            bound_payloads[report_name].payload,
            label=f"{lane_id} conversion report",
        )
        hash_manifest = _strict_json_bytes(
            bound_payloads[manifest_name].payload,
            label=f"{lane_id} conversion hash manifest",
        )
        lane_example_counts[lane_id] = len(examples)
        for example in examples:
            example_id = example.get("example_id")
            split_group = example.get("split_group")
            repo = split_group.get("repo") if isinstance(split_group, Mapping) else None
            if (
                not isinstance(example_id, str)
                or not example_id
                or not isinstance(repo, str)
                or not repo.strip()
                or example.get("dataset_id") != rules.dataset_id
                or example.get("dataset_family") != rules.family
                or example.get("example_type") != "TrajectoryExample"
                or example.get("input_modality") != "structured_features"
                or example.get("model_use_tier") != "train_after_adapter"
                or not _is_exact_positive_zero(example.get("training_weight"))
                or example.get("split_policy") != "repo_grouped"
                or lane_converter.CONVERTER_VERSION
                not in example.get("canonical_feature_refs", ())
                or (
                    lane_id == _OST_LANE_ID
                    and not _LEAKAGE_DIGEST_PATTERN.fullmatch(repo)
                )
            ):
                raise _coherence_error("conversion example identity is incomplete")
            if example_id in examples_by_id:
                raise _coherence_error("conversion example IDs are not unique")
            example_ids.append(example_id)
            examples_by_id[example_id] = example
            example_lane_by_id[example_id] = lane_id

        report_output = conversion_report.get("output")
        report_hashes = (
            report_output.get("hashes") if isinstance(report_output, Mapping) else None
        )
        examples_read = bound_payloads[examples_name]
        invalid_read = bound_payloads[invalid_name]
        resolved_examples = sum(
            example["target"]["resolved"] is True for example in examples
        )
        unresolved_examples = len(examples) - resolved_examples
        if lane_id == _OPENHANDS_LANE_ID:
            agent_steps = sum(
                int(example["input"]["trajectory"]["num_agent_steps"])
                for example in examples
            )
        else:
            agent_steps = sum(
                int(example["input"]["trajectory_summary"]["num_agent_steps"])
                for example in examples
            )
        report_converter = conversion_report.get("converter")
        report_input = conversion_report.get("input")
        report_source_hashes = conversion_report.get("source_hashes")
        report_source_counts = conversion_report.get("source_counts")
        report_source_trajectory = conversion_report.get("source_trajectory")
        report_reconciliation = conversion_report.get("count_reconciliation")
        report_schema = conversion_report.get("schema")
        expected_report_keys = {
            "conversion_report_schema_version",
            "mode",
            "converter",
            "dataset_id",
            "dataset_family",
            "input",
            "output",
            "source_hashes",
            "source_counts",
            "source_trajectory",
            "count_reconciliation",
            "privacy",
            "schema",
            "training_authorization",
            "warnings",
        }
        if lane_id == _OST_LANE_ID:
            expected_report_keys |= {
                "label_policy",
                "third_party_model_output_tos_reviewed",
            }
            expected_warnings = [ost_governance.MINIMAX_QWEN_TOS_CAVEAT]
        else:
            expected_warnings = []
        expected_source_hash_fields = {
            "traces_file_sha256",
            "trace_index_file_sha256",
            "invalid_traces_file_sha256",
        }
        if (
            set(conversion_report) != expected_report_keys
            or conversion_report.get("conversion_report_schema_version") != "0.1.0"
            or conversion_report.get("mode") != "full"
            or conversion_report.get("dataset_id") != rules.dataset_id
            or conversion_report.get("dataset_family") != rules.family
            or report_converter
            != {
                "name": rules.converter_name,
                "version": lane_converter.CONVERTER_VERSION,
                "git_sha": report_converter.get("git_sha")
                if isinstance(report_converter, Mapping)
                else None,
            }
            or not isinstance(report_converter, Mapping)
            or not isinstance(report_converter.get("git_sha"), str)
            or not _COMMIT_PATTERN.fullmatch(report_converter["git_sha"])
            or report_input
            != {
                "trace_jsonl": "verified-stream:pneuma_traces.jsonl",
                "adapter_report": "verified-stream:adapter_report.json",
                "requested_limit": None,
                "loaded_traces": len(examples),
                "selection": "all_adapter_emitted_processed_traces",
            }
            or not isinstance(report_output, Mapping)
            or set(report_output)
            != {
                "examples_emitted",
                "invalid_examples",
                "quarantined_examples",
                "resolved_targets",
                "unresolved_targets",
                "hashes",
                "schema_validation_passed",
            }
            or report_output.get("examples_emitted") != len(examples)
            or report_output.get("invalid_examples") != 0
            or report_output.get("quarantined_examples") != 0
            or report_output.get("resolved_targets") != resolved_examples
            or report_output.get("unresolved_targets") != unresolved_examples
            or report_output.get("schema_validation_passed") is not True
            or report_hashes
            != {
                "examples_jsonl_sha256": examples_read.sha256,
                "invalid_examples_jsonl_sha256": invalid_read.sha256,
            }
            or not isinstance(report_source_hashes, Mapping)
            or set(report_source_hashes) != expected_source_hash_fields
            or any(
                not isinstance(digest, str) or not _DIGEST_PATTERN.fullmatch(digest)
                for digest in report_source_hashes.values()
            )
            or not isinstance(report_source_counts, Mapping)
            or not report_source_counts
            or report_source_counts.get(
                "valid",
                report_source_counts.get("traces_emitted"),
            )
            != len(examples)
            or report_source_counts.get("invalid") != 0
            or not isinstance(report_source_trajectory, Mapping)
            or not report_source_trajectory
            or report_source_trajectory.get("total_agent_steps") != agent_steps
            or report_source_trajectory.get("resolved_true") != resolved_examples
            or report_source_trajectory.get("resolved_false") != unresolved_examples
            or not isinstance(report_reconciliation, Mapping)
            or report_reconciliation.get("reconciled") is not True
            or not isinstance(report_reconciliation.get("checks"), Mapping)
            or report_reconciliation["checks"]
            != {
                "examples_plus_quarantined_match_traces_read": True,
                "traces_read_match_adapter_valid": True,
                "agent_steps_match_adapter_report": True,
                "resolved_targets_match_adapter_report": True,
                "unresolved_targets_match_adapter_report": True,
            }
            or report_reconciliation.get("expected")
            != {
                "valid_traces": len(examples),
                "invalid_traces": 0,
                "skipped_rows": report_source_counts.get("skipped"),
                "agent_steps": agent_steps,
                "resolved": resolved_examples,
                "unresolved": unresolved_examples,
            }
            or not isinstance(report_reconciliation.get("observed"), Mapping)
            or report_reconciliation["observed"]
            != {
                "traces_read": len(examples),
                "examples_emitted": len(examples),
                "invalid_examples": 0,
                "quarantined_examples": 0,
                "agent_steps": agent_steps,
                "resolved": resolved_examples,
                "unresolved": unresolved_examples,
            }
            or report_schema
            != {
                "training_example": lane_converter.TRAINING_EXAMPLE_SCHEMA,
                "training_example_version": load_schema(
                    lane_converter.TRAINING_EXAMPLE_SCHEMA
                ).get("x-pneuma-version"),
            }
            or not isinstance(conversion_report.get("training_authorization"), Mapping)
            or conversion_report["training_authorization"].get("model_use_tier")
            != "train_after_adapter"
            or not _is_exact_positive_zero(
                conversion_report["training_authorization"].get("training_weight")
            )
            or not isinstance(conversion_report.get("privacy"), Mapping)
            or conversion_report.get("warnings") != expected_warnings
        ):
            raise _coherence_error(
                "conversion report contradicts held conversion bytes"
            )
        if lane_id == _OST_LANE_ID and (
            conversion_report.get("label_policy")
            != {
                "kind": "constructed_label",
                "confidence": "medium",
                "harness_outcome_forbidden": True,
            }
            or conversion_report.get("third_party_model_output_tos_reviewed")
            is not False
        ):
            raise _coherence_error(
                "Open-SWE-Traces conversion report label policy is not exact"
            )

        trace_snapshot = snapshots_by_path[rules.source_paths[0]]
        if not hmac.compare_digest(
            trace_snapshot["sha256"],
            report_source_hashes["traces_file_sha256"],
        ):
            raise _coherence_error(
                "conversion trace digest differs from source integrity"
            )

        manifest_hashes = hash_manifest.get("hashes")
        report_read = bound_payloads[report_name]
        if (
            set(hash_manifest)
            != {
                "hash_manifest_schema_version",
                "mode",
                "dataset_id",
                "converter_version",
                "hash_manifest_hash_convention",
                "input",
                "hashes",
            }
            or hash_manifest.get("hash_manifest_schema_version") != "0.1.0"
            or hash_manifest.get("mode") != "full"
            or hash_manifest.get("dataset_id") != rules.dataset_id
            or hash_manifest.get("converter_version")
            != lane_converter.CONVERTER_VERSION
            or hash_manifest.get("hash_manifest_hash_convention")
            != (
                "hash_manifest_json_sha256 is the sha256 of canonical manifest JSON "
                "with hashes.hash_manifest_json_sha256 set to null"
            )
            or hash_manifest.get("input")
            != {
                "trace_jsonl": "verified-stream:pneuma_traces.jsonl",
                "adapter_report": "verified-stream:adapter_report.json",
                "requested_limit": None,
            }
            or not isinstance(manifest_hashes, Mapping)
            or set(manifest_hashes)
            != {
                "examples_jsonl_sha256",
                "invalid_examples_jsonl_sha256",
                "conversion_report_json_sha256",
                "hash_manifest_json_sha256",
            }
            or manifest_hashes.get("examples_jsonl_sha256") != examples_read.sha256
            or manifest_hashes.get("invalid_examples_jsonl_sha256")
            != invalid_read.sha256
            or manifest_hashes.get("conversion_report_json_sha256")
            != report_read.sha256
        ):
            raise _coherence_error("conversion hash manifest differs from held bytes")
        self_digest = _require_digest(
            manifest_hashes.get("hash_manifest_json_sha256"),
            label="conversion hash manifest self digest",
        )
        self_hash_value = copy.deepcopy(hash_manifest)
        self_hash_value["hashes"]["hash_manifest_json_sha256"] = None
        self_hash_payload = (
            json.dumps(
                self_hash_value,
                allow_nan=False,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            + "\n"
        ).encode("utf-8")
        if not hmac.compare_digest(
            self_digest,
            hashlib.sha256(self_hash_payload).hexdigest(),
        ):
            raise _coherence_error("conversion hash manifest self digest is invalid")

    if multi_lane:
        lane_counts = preparation.get("lane_counts")
        expected_lane_counts = {
            lane_id: {
                "converted_examples": lane_example_counts[lane_id],
                "selected_records": records_per_lane[lane_id],
            }
            for lane_id in lane_ids
        }
        if lane_counts != expected_lane_counts:
            raise _coherence_error(
                "preparation lane counts differ from held conversions and shard"
            )

    suite_evaluation = suite.get("evaluation_identity")
    if not isinstance(suite_evaluation, Mapping):
        raise _coherence_error("suite evaluation identity policy is missing")
    required_eval_families = suite_evaluation.get("required_families")
    blocked_eval_families = suite_evaluation.get("blocked_unavailable_families")
    if (
        required_eval_families != ["swe-bench", "swe-mera", "swe-polybench"]
        or blocked_eval_families != ["swe-bench-pro"]
        or set(eval_digests) != set(required_eval_families)
    ):
        raise _coherence_error("suite and bound evaluation families differ")
    eval_identities = []
    for family in required_eval_families:
        rows = _metadata_rows(
            io.BytesIO(bound_payloads[f"{_EVAL_PAYLOAD_PREFIX}{family}"].payload)
        )
        eval_identities.extend(
            IdentityRecord(
                family=family,
                lane_id=family,
                repo=row["repo"],
                issue_or_pr=(
                    match.group(1)
                    if (
                        match := re.search(
                            r"(?:^|[-_#/])([0-9]+)$",
                            row["source_id"],
                        )
                    )
                    else None
                ),
                task_id=row["source_id"],
                base_commit=row["base_commit"],
                patch_sha256=None,
                test_patch_sha256=None,
                fuzzy_text_sha256=None,
            )
            for row in rows
        )
    eval_repo_keys = {
        normalized
        for identity in eval_identities
        if (normalized := normalize_identity_text(identity.repo)) is not None
    }
    if multi_lane:
        eval_repo_keys |= {
            leakage_registry.canonicalize_repo(identity.repo)
            for identity in eval_identities
            if isinstance(identity.repo, str) and identity.repo.strip()
        }
    policy_families = []
    for item in suite_families:
        policy_item = {
            name: item[name]
            for name in (
                "family",
                "terminal_role",
                "gradient_eligibility",
                "payload_access_100k",
                "payload_access_500k",
                "payload_access_2m",
                "payload_access_8m",
            )
        }
        if "identity_metadata_relative_path" in item:
            policy_item["identity_metadata_relative_path"] = item[
                "identity_metadata_relative_path"
            ]
        policy_families.append(policy_item)
    suite_policy = {
        "manifest_kind": "pneuma_foundation_dataset_suite",
        "manifest_schema_version": "0.1.0",
        "first_stage": copy.deepcopy(suite_first_stage),
        "evaluation_identity": {
            "required_families": list(required_eval_families),
            "blocked_unavailable_families": list(blocked_eval_families),
        },
        "families": policy_families,
    }

    contamination = parsed["contamination_receipt"]
    recomputed_contamination = build_contamination_receipt(
        (identity_from_foundation_record(record) for record in records),
        eval_identities,
        suite_policy=suite_policy,
    )
    if (
        contamination != recomputed_contamination
        or contamination.get("manifest_kind")
        != "pneuma_foundation_contamination_receipt"
        or contamination.get("manifest_schema_version") != "0.1.0"
        or contamination.get("training_identity_count") != len(records)
        or contamination.get("evaluation_coverage_complete") is not True
        or contamination.get("finding_count") != 0
        or contamination.get("findings") != []
        or contamination.get("repo_issue_disjoint") is not True
        or contamination.get("required_evaluation_families") != required_eval_families
    ):
        raise _coherence_error("contamination receipt contradicts disjointness gates")

    diversity = parsed["diversity_receipt"]
    if (
        diversity.get("manifest_kind") != "pneuma_foundation_diversity_receipt"
        or diversity.get("manifest_schema_version") != "0.1.0"
        or {
            key: value
            for key, value in diversity.items()
            if key not in {"manifest_kind", "manifest_schema_version"}
        }
        != expected_inventory
    ):
        raise _coherence_error("diversity receipt differs from shard inventory")

    selection = parsed["selection_receipt"]
    resolved_count = sum(
        record["observations"]["labels"]["resolved"] is True for record in records
    )
    if (
        selection.get("manifest_kind") != "pneuma_foundation_selection_receipt"
        or selection.get("manifest_schema_version") != "0.1.0"
        or selection.get("stage") != stage
        or selection.get("token_ceiling") != token_ceiling
        or selection.get("selected_record_count") != len(records)
        or type(selection.get("candidate_record_count")) is not int
        or selection["candidate_record_count"] < len(records)
        or selection.get("selected_record_ids") != record_ids
        or selection.get("selected_token_count") != recount_total
        or selection.get("tokenizer_recount_total") != recount_total
        or selection.get("resolved_count") != resolved_count
        or selection.get("unresolved_count") != len(records) - resolved_count
        or not _is_exact_positive_zero(selection.get("persisted_training_weight"))
    ):
        raise _coherence_error("selection receipt differs from shard records")

    split = parsed["split_receipt"]
    canonical_sets = split.get("canonical_repository_sets")
    if (
        split.get("manifest_kind") != "pneuma_foundation_repo_grouped_split_receipt"
        or split.get("manifest_schema_version") != "0.1.0"
        or split.get("repository_grouped") is not True
        or not isinstance(split.get("assignments"), list)
        or not isinstance(canonical_sets, Mapping)
        or set(canonical_sets) != {"train", "validation", "held_out"}
    ):
        raise _coherence_error("split receipt is incomplete")
    normalized_sets = {
        name: set(values) if isinstance(values, list) else None
        for name, values in canonical_sets.items()
    }
    if any(values is None for values in normalized_sets.values()) or any(
        normalized_sets[left] & normalized_sets[right]
        for index, left in enumerate(normalized_sets)
        for right in tuple(normalized_sets)[index + 1 :]
    ):
        raise _coherence_error("split receipt repository sets overlap")
    assignments = split["assignments"]
    expected_assignment_fields = {
        "record_source_id",
        "repo",
        "canonical_repo",
        "split_id",
        "quarantine_id",
    }
    allowed_quarantine_ids = (
        (None, EVAL_REPO_QUARANTINE_ID, CROSS_DATASET_LEAKAGE_QUARANTINE_ID)
        if multi_lane
        else (None, EVAL_REPO_QUARANTINE_ID)
    )
    assignment_by_source = {}
    expected_sets = {"train": set(), "validation": set(), "held_out": set()}
    leak_quarantine_counts = {lane_id: 0 for lane_id in lane_ids}
    for assignment in assignments:
        if (
            not isinstance(assignment, Mapping)
            or set(assignment) != expected_assignment_fields
        ):
            raise _coherence_error("split assignment fields are not exact")
        source_id = assignment.get("record_source_id")
        repo = assignment.get("repo")
        canonical_repo = assignment.get("canonical_repo")
        split_id = assignment.get("split_id")
        if (
            not isinstance(source_id, str)
            or source_id not in examples_by_id
            or source_id in assignment_by_source
            or not isinstance(repo, str)
            or not isinstance(canonical_repo, str)
            or split_id not in expected_sets
            or assignment.get("quarantine_id") not in allowed_quarantine_ids
        ):
            raise _coherence_error("split assignment identity is invalid")
        try:
            normalized_repo = normalize_identity_text(repo)
        except TypeError as exc:
            raise _coherence_error("split repository cannot be normalized") from exc
        if normalized_repo is None or normalized_repo != canonical_repo:
            raise _coherence_error("split canonical repository is not reproducible")
        if canonical_repo in eval_repo_keys:
            expected_quarantine = EVAL_REPO_QUARANTINE_ID
        elif multi_lane and leakage_registry.canonicalize_repo(repo) in leak_digests:
            expected_quarantine = CROSS_DATASET_LEAKAGE_QUARANTINE_ID
        else:
            expected_quarantine = None
        if assignment.get("quarantine_id") != expected_quarantine:
            raise _coherence_error("split quarantine is not reproducible")
        if expected_quarantine == CROSS_DATASET_LEAKAGE_QUARANTINE_ID:
            leak_quarantine_counts[example_lane_by_id[source_id]] += 1
        bucket = (
            int(
                hashlib.sha256(canonical_repo.encode("utf-8")).hexdigest()[:8],
                16,
            )
            % 100
        )
        expected_split = (
            "train" if bucket < 80 else "validation" if bucket < 90 else "held_out"
        )
        example_repo = examples_by_id[source_id]["split_group"]["repo"]
        if (
            split_id != expected_split
            or normalize_identity_text(example_repo) != canonical_repo
        ):
            raise _coherence_error("split assignment differs from conversion example")
        assignment_by_source[source_id] = assignment
        expected_sets[split_id].add(canonical_repo)
    if set(assignment_by_source) != set(example_ids):
        raise _coherence_error(
            "conversion examples do not join exactly to split assignments"
        )
    if {name: sorted(values) for name, values in expected_sets.items()} != dict(
        canonical_sets
    ):
        raise _coherence_error("split repository sets are not reproducible")
    if multi_lane:
        leakage = parsed["leakage_receipt"]
        if leakage.get("quarantined_example_counts") != leak_quarantine_counts or (
            leakage.get("quarantined_example_total")
            != sum(leak_quarantine_counts.values())
        ):
            raise _coherence_error(
                "leakage receipt quarantine counts are not reproducible"
            )
    for record in records:
        source_id = record["source"]["source_record_id"]
        assignment = assignment_by_source.get(source_id)
        identity = record.get("identity")
        record_lane = record_lane_by_source_id[source_id]
        if (
            assignment is None
            or example_lane_by_id.get(source_id) != record_lane
            or assignment["split_id"] != "train"
            or assignment["quarantine_id"] is not None
            or not isinstance(identity, Mapping)
            or normalize_identity_text(identity.get("repo"))
            != assignment["canonical_repo"]
        ):
            raise _coherence_error("shard record does not join to its train split")
        try:
            prompt_tokens, target_tokens = recount_by_source_id[source_id]
            validate_derived_foundation_record(
                record,
                example=examples_by_id[source_id],
                split_assignment=assignment,
                lane_disposition=_LANE_RULES[record_lane].disposition,
                source_receipt_hashes=tuple(source_receipt_hashes),
                tokenizer_id=spec.model_id,
                tokenizer_revision=spec.revision,
                prompt_tokens=prompt_tokens,
                target_tokens=target_tokens,
            )
        except FoundationRecordError as exc:
            raise _coherence_error(
                f"shard record derivation is invalid: {exc}"
            ) from exc

    return record_membership


def _validate_preparation_coherence(
    scope: Mapping,
    bound_payloads: Mapping[str, BoundArtifactRead],
    *,
    tokenizer,
    repo_root: Path,
) -> dict[str, str]:
    """Fail closed around the shared held-byte semantic validator."""

    try:
        return _validate_preparation_coherence_unchecked(
            scope,
            bound_payloads,
            tokenizer=tokenizer,
            repo_root=repo_root,
        )
    except FoundationAuthorizationError:
        raise
    except (
        AttributeError,
        KeyError,
        OverflowError,
        TypeError,
        ValueError,
    ) as exc:
        raise _coherence_error(f"malformed cross-artifact value: {exc}") from exc


def build_authorization_candidate(
    preparation: PreparationResult,
    *,
    repo_root: Path,
    code_commit: str,
    model_key: str = "2b",
    _tokenizer=None,
    _tokenizer_loader=None,
) -> Path:
    """Build a nonauthorizing exact-scope candidate after preparation stabilizes."""

    root = _absolute_lexical(repo_root)
    _validate_commit_binding(root, code_commit)
    if model_key not in ("2b", "4b"):
        raise FoundationAuthorizationError(
            "only pinned 2b or 4b models may be authorized"
        )
    spec = MODEL_SPECS[model_key]
    snapshot_path = getattr(preparation, "tokenizer_snapshot_path", None)
    if not isinstance(snapshot_path, Path):
        raise FoundationAuthorizationError(
            "preparation tokenizer snapshot path is missing"
        )
    verified_snapshot = _verify_authorization_snapshot(
        snapshot_path,
        repo_root=root,
    )
    if _tokenizer is not None and _tokenizer_loader is not None:
        raise FoundationAuthorizationError(
            "provide either an already loaded tokenizer or a tokenizer loader"
        )
    if _tokenizer is None:
        tokenizer = _load_and_reverify_tokenizer(
            verified_snapshot,
            repo_root=root,
            tokenizer_loader=_tokenizer_loader,
        )
    else:
        tokenizer = _tokenizer
        if not callable(getattr(tokenizer, "encode", None)):
            raise FoundationAuthorizationError(
                "provided tokenizer has no encode method"
            )
        after_ready = _verify_authorization_snapshot(
            verified_snapshot.snapshot_path,
            repo_root=root,
        )
        if after_ready != verified_snapshot:
            raise FoundationAuthorizationError(
                "pinned tokenizer snapshot changed before recount"
            )
    try:
        stage_hint = Path(preparation.preparation_manifest_path).parent.name
    except (AttributeError, TypeError) as exc:
        raise FoundationAuthorizationError("preparation result is incomplete") from exc
    if stage_hint not in _STAGE_TOKEN_CEILINGS:
        raise FoundationAuthorizationError("preparation stage path is not authorized")
    artifact_paths = _artifact_paths_from_preparation(preparation, stage=stage_hint)
    evidence_paths = _evidence_paths_from_preparation(preparation, stage=stage_hint)
    all_paths = {**artifact_paths, **evidence_paths}
    _validate_exact_preparation_paths(
        artifact_paths,
        evidence_paths,
        repo_root=root,
        stage=stage_hint,
    )
    eval_families = tuple(
        name.removeprefix(_EVAL_PAYLOAD_PREFIX)
        for name in evidence_paths
        if name.startswith(_EVAL_PAYLOAD_PREFIX)
    )
    size_limits, total_size_limit = _artifact_size_limits(
        stage_hint,
        eval_families,
    )
    with _hold_artifacts(
        all_paths,
        repo_root=root,
        max_sizes=size_limits,
        max_total_size=total_size_limit,
    ) as held:
        preparation_manifest = _strict_json_bytes(
            held["preparation_manifest"].read.payload,
            label="preparation manifest",
        )
        selection_receipt = _strict_json_bytes(
            held["selection_receipt"].read.payload,
            label="selection receipt",
        )
        stage = preparation_manifest.get("stage")
        if stage not in _STAGE_TOKEN_CEILINGS:
            raise FoundationAuthorizationError("preparation stage is not authorized")
        if stage != stage_hint:
            raise FoundationAuthorizationError(
                "preparation manifest stage differs from its exact stage root"
            )
        _validate_exact_preparation_paths(
            artifact_paths,
            evidence_paths,
            repo_root=root,
            stage=stage,
        )
        token_ceiling = _STAGE_TOKEN_CEILINGS[stage]
        if (
            preparation_manifest.get("training_authorized") is not False
            or preparation_manifest.get("persisted_training_weight") != 0.0
            or preparation_manifest.get("dry_run") is not False
            or preparation_manifest.get("token_ceiling") != token_ceiling
        ):
            raise FoundationAuthorizationError(
                "preparation manifest is not a zero-weight final plan"
            )
        if (
            selection_receipt.get("stage") != stage
            or selection_receipt.get("token_ceiling") != token_ceiling
        ):
            raise FoundationAuthorizationError(
                "selection receipt ceiling differs from preparation"
            )
        shard_entry = preparation_manifest.get("shard")
        if (
            not isinstance(shard_entry, Mapping)
            or shard_entry.get("artifact") != artifact_paths["shard"].name
            or shard_entry.get("manifest_artifact")
            != artifact_paths["shard_manifest"].name
        ):
            raise FoundationAuthorizationError(
                "preparation manifest shard paths are not exact"
            )
        candidate_path = _candidate_path(preparation, repo_root=root, stage=stage)
        artifact_field_names = _artifact_fields(stage)
        bindings = {
            name: {
                "path": _repo_relative(item.path, repo_root=root),
                "sha256": item.read.sha256,
                "size": item.read.size,
            }
            for name, item in held.items()
            if name in artifact_field_names
        }

        def _held_conversion_binding(payload_name: str) -> dict:
            return {
                "path": _repo_relative(held[payload_name].path, repo_root=root),
                "sha256": held[payload_name].read.sha256,
                "size": held[payload_name].read.size,
            }

        if stage in _SINGLE_LANE_STAGES:
            conversion_bindings = {
                name: _held_conversion_binding(_CONVERSION_PAYLOAD_NAMES[name])
                for name in _CONVERSION_ARTIFACT_FIELDS
            }
        else:
            conversion_bindings = {
                lane_id: {
                    name: _held_conversion_binding(
                        _conversion_payload_name(stage, lane_id, name)
                    )
                    for name in _CONVERSION_ARTIFACT_FIELDS
                }
                for lane_id in _stage_lane_ids(stage)
            }
        evidence_bindings = {
            "conversion": conversion_bindings,
            "eval_identities": {
                name.removeprefix(_EVAL_PAYLOAD_PREFIX): {
                    "path": _repo_relative(item.path, repo_root=root),
                    "sha256": item.read.sha256,
                    "size": item.read.size,
                }
                for name, item in held.items()
                if name.startswith(_EVAL_PAYLOAD_PREFIX)
            },
        }
        scope = {
            "model": {
                "key": spec.key,
                "model_id": spec.model_id,
                "revision": spec.revision,
                "tokenizer_id": spec.model_id,
                "tokenizer_revision": spec.revision,
            },
            "tokenizer_snapshot": _snapshot_scope(
                verified_snapshot,
                repo_root=root,
            ),
            "stage": stage,
            "token_ceiling": token_ceiling,
            "local_profile": copy.deepcopy(_LOCAL_PROFILE),
            "learning_rates": [0.00005, 0.0001, 0.0002],
            "code_commit": code_commit,
            "artifacts": bindings,
            "evidence_artifacts": evidence_bindings,
            "authorized_lane_weights": _stage_lane_weights(stage),
            "source_data_policy": copy.deepcopy(_SOURCE_POLICY),
            "output_root": _OUTPUT_ROOT,
            "budget": copy.deepcopy(_BUDGET),
        }
        _validate_preparation_coherence(
            scope,
            {name: item.read for name, item in held.items()},
            tokenizer=tokenizer,
            repo_root=root,
        )
        after_recount = _verify_authorization_snapshot(
            verified_snapshot.snapshot_path,
            repo_root=root,
        )
        if after_recount != verified_snapshot:
            raise FoundationAuthorizationError(
                "pinned tokenizer snapshot changed during authorization recount"
            )
        digest = authorization_scope_digest(scope)
        candidate = {
            "manifest_kind": "pneuma_foundation_training_authorization",
            "manifest_schema_version": "0.2.0",
            "authorization_status": "candidate",
            "scope": scope,
            "scope_digest": digest,
            "operator_approval": None,
        }
        _validate_manifest(candidate)
        try:
            with bind_artifact_publication(
                candidate_path.parent,
                anchor_root=root,
                allowed_root=root / "build",
                forbidden_roots=(
                    (_PROTECTED_DATA_ROOT,)
                    if _PROTECTED_DATA_ROOT.is_absolute()
                    else ()
                ),
            ) as publication:
                write_atomic_json(candidate_path, candidate, publication=publication)
                _revalidate_held(held)
        except (
            ArtifactPublicationError,
            OSError,
            RuntimeError,
            TypeError,
            ValueError,
        ) as exc:
            raise FoundationAuthorizationError(
                f"authorization candidate publication failed: {exc}"
            ) from exc
    return candidate_path


def required_approval_phrase(candidate: Mapping) -> str:
    """Return the exact phrase for a validated nonauthorizing candidate."""

    if not isinstance(candidate, Mapping):
        raise FoundationAuthorizationError(
            "approval phrase requires a candidate mapping"
        )
    _validate_manifest(candidate)
    if candidate.get("authorization_status") != "candidate":
        raise FoundationAuthorizationError("approval phrase requires candidate status")
    scope = candidate.get("scope")
    digest = candidate.get("scope_digest")
    computed = authorization_scope_digest(scope)
    if not isinstance(digest, str) or not hmac.compare_digest(digest, computed):
        raise FoundationAuthorizationError("candidate scope digest does not match")
    return f"{APPROVAL_PHRASE_PREFIX} {digest}"


def _repo_from_authorization_path(path: Path) -> Path:
    candidate = _absolute_lexical(path)
    for parent in candidate.parents:
        if parent.name == "build":
            return parent.parent
    raise FoundationAuthorizationError(
        "authorization path is outside a repository build tree"
    )


def _require_exact_authorization_path(
    path: Path, *, repo_root: Path, status: str, stage: str, cloud: bool = False
) -> Path:
    folder = "candidates" if status == "candidate" else "final"
    name = f"{stage}-cloud.json" if cloud else f"{stage}.json"
    expected = _absolute_lexical(
        repo_root / f"build/foundation/authorizations/{folder}/{name}"
    )
    actual = _absolute_lexical(path)
    if actual != expected:
        raise FoundationAuthorizationError(f"{status} authorization path is not exact")
    return actual


def _is_cloud_scope(scope: Mapping) -> bool:
    return isinstance(scope, Mapping) and scope.get("execution_profile") == "cloud"


def _assert_exact_cloud_posture(scope: Mapping) -> None:
    """Enforce the cloud transfer posture and quoted one-job budget exactly.

    Both lane license receipts stay ``cloud_redistribution_allowed: false``;
    the only permitted cloud movement is the private single-job transfer of
    derived, digest-bearing artifacts recorded by the operator-approved
    ``private_cloud_transfer_allowed`` posture below.
    """

    if scope.get("source_data_policy") != _CLOUD_SOURCE_POLICY:
        raise FoundationAuthorizationError(
            "cloud authorization transfer posture is not exact"
        )
    budget = scope.get("budget")
    if not isinstance(budget, Mapping) or set(budget) != _CLOUD_BUDGET_KEYS:
        raise FoundationAuthorizationError(
            "cloud authorization budget keys are not exact"
        )
    ceiling = budget.get("paid_compute_ceiling_usd")
    if (
        budget.get("paid_compute_usd") != 0
        or isinstance(budget.get("paid_compute_usd"), bool)
        or budget.get("cloud_jobs_used") != 0
        or isinstance(budget.get("cloud_jobs_used"), bool)
        or budget.get("cloud_job_ceiling") != 1
        or isinstance(budget.get("cloud_job_ceiling"), bool)
        or budget.get("cloud_lifetime_cap_usd") != MAX_LIFETIME_CLOUD_USD
        or isinstance(ceiling, bool)
        or not isinstance(ceiling, (int, float))
        or not math.isfinite(float(ceiling))
        or not 0 < float(ceiling) <= MAX_LIFETIME_CLOUD_USD
    ):
        raise FoundationAuthorizationError(
            "cloud authorization budget ceilings are not exact"
        )
    if not isinstance(scope.get("local_gate_report"), Mapping):
        raise FoundationAuthorizationError(
            "cloud authorization local gate report binding is missing"
        )


def _verify_cloud_gate_report(scope: Mapping, *, repo_root: Path) -> None:
    """Re-bind the passing local-gate report named by one cloud scope."""

    binding = scope.get("local_gate_report")
    if not isinstance(binding, Mapping):
        raise FoundationAuthorizationError(
            "cloud authorization local gate report binding is missing"
        )
    path = _path_from_binding(binding, repo_root=repo_root)
    with _hold_artifacts(
        {"local_gate_report": path},
        repo_root=repo_root,
        max_sizes={"local_gate_report": _LOCAL_GATE_REPORT_SIZE_CEILING},
        max_total_size=_LOCAL_GATE_REPORT_SIZE_CEILING,
    ) as held:
        item = held["local_gate_report"]
        expected_digest = binding.get("sha256")
        if (
            not isinstance(expected_digest, str)
            or not hmac.compare_digest(item.read.sha256, expected_digest)
            or item.read.size != binding.get("size")
        ):
            raise FoundationAuthorizationError(
                "cloud local gate report binding changed"
            )
        report = _strict_json_bytes(item.read.payload, label="local gate report")
        if report.get("local_gates_passed") is not True:
            raise FoundationAuthorizationError(
                "cloud reproduction requires all local gates to pass"
            )
        _revalidate_held(held)


def _validated_utc_timestamp(value: str) -> str:
    if not isinstance(value, str) or not _UTC_PATTERN.fullmatch(value):
        raise FoundationAuthorizationError(
            "approved_at must be a strict UTC timestamp ending in Z"
        )
    try:
        parsed = datetime.fromisoformat(value.removesuffix("Z") + "+00:00")
    except ValueError as exc:
        raise FoundationAuthorizationError(
            "approved_at is not a valid UTC timestamp"
        ) from exc
    if parsed.tzinfo != timezone.utc:
        raise FoundationAuthorizationError("approved_at must be UTC")
    return value


def finalize_authorization(
    candidate_path: Path,
    supplied_scope_digest: str,
    supplied_approval_phrase: str,
    operator_id: str,
    approved_at: str,
    output_path: Path,
) -> Path:
    """Convert one unchanged candidate into a separately published final authorization."""

    repo_root = _repo_from_authorization_path(candidate_path)
    candidate_path = _absolute_lexical(candidate_path)
    with _hold_artifacts(
        {"candidate": candidate_path},
        repo_root=repo_root,
        max_sizes={"candidate": _AUTHORIZATION_MANIFEST_SIZE_CEILING},
        max_total_size=_AUTHORIZATION_MANIFEST_SIZE_CEILING,
    ) as held:
        candidate = _strict_json_bytes(
            held["candidate"].read.payload,
            label="authorization candidate",
        )
        _validate_manifest(candidate)
        if candidate.get("authorization_status") != "candidate":
            raise FoundationAuthorizationError("only a candidate may be finalized")
        scope = candidate["scope"]
        stage = scope["stage"]
        cloud = _is_cloud_scope(scope)
        _require_exact_authorization_path(
            candidate_path,
            repo_root=repo_root,
            status="candidate",
            stage=stage,
            cloud=cloud,
        )
        output_path = _require_exact_authorization_path(
            output_path,
            repo_root=repo_root,
            status="authorized",
            stage=stage,
            cloud=cloud,
        )
        digest = candidate["scope_digest"]
        computed = authorization_scope_digest(scope)
        if not hmac.compare_digest(digest, computed):
            raise FoundationAuthorizationError("candidate scope digest does not match")
        if not isinstance(supplied_scope_digest, str) or not hmac.compare_digest(
            supplied_scope_digest,
            digest,
        ):
            raise FoundationAuthorizationError("supplied scope digest does not match")
        expected_phrase = f"{APPROVAL_PHRASE_PREFIX} {digest}"
        if not isinstance(supplied_approval_phrase, str) or not hmac.compare_digest(
            supplied_approval_phrase,
            expected_phrase,
        ):
            raise FoundationAuthorizationError(
                "supplied approval phrase does not match"
            )
        if (
            not isinstance(operator_id, str)
            or not operator_id.strip()
            or operator_id != operator_id.strip()
        ):
            raise FoundationAuthorizationError(
                "operator_id must be a nonempty exact string"
            )
        approved_at = _validated_utc_timestamp(approved_at)
        final = {
            "manifest_kind": candidate["manifest_kind"],
            "manifest_schema_version": candidate["manifest_schema_version"],
            "authorization_status": "authorized",
            "scope": copy.deepcopy(scope),
            "scope_digest": digest,
            "operator_approval": {
                "operator_id": operator_id,
                "approved_at": approved_at,
                "scope_digest": digest,
                "approval_phrase_sha256": hashlib.sha256(
                    supplied_approval_phrase.encode("utf-8")
                ).hexdigest(),
            },
        }
        _validate_manifest(final)
        try:
            with bind_artifact_publication(
                output_path.parent,
                anchor_root=repo_root,
                allowed_root=repo_root / "build",
                forbidden_roots=(
                    (_PROTECTED_DATA_ROOT,)
                    if _PROTECTED_DATA_ROOT.is_absolute()
                    else ()
                ),
            ) as publication:
                write_atomic_json(output_path, final, publication=publication)
                _revalidate_held(held)
        except (
            ArtifactPublicationError,
            OSError,
            RuntimeError,
            TypeError,
            ValueError,
        ) as exc:
            raise FoundationAuthorizationError(
                f"final authorization publication failed: {exc}"
            ) from exc
    return output_path


def _assert_exact_scope(scope: Mapping, *, repo_root: Path) -> None:
    model = scope.get("model")
    if not isinstance(model, Mapping) or model.get("key") not in ("2b", "4b"):
        raise FoundationAuthorizationError("authorization model key is not permitted")
    spec = MODEL_SPECS[model["key"]]
    if dict(model) != {
        "key": spec.key,
        "model_id": spec.model_id,
        "revision": spec.revision,
        "tokenizer_id": spec.model_id,
        "tokenizer_revision": spec.revision,
    }:
        raise FoundationAuthorizationError(
            "authorization does not match the model/tokenizer pin"
        )
    tokenizer_snapshot = scope.get("tokenizer_snapshot")
    if (
        not isinstance(tokenizer_snapshot, Mapping)
        or set(tokenizer_snapshot)
        != {
            "path",
            "model_id",
            "revision",
            "receipt_sha256",
            "snapshot_sha256",
        }
        or tokenizer_snapshot.get("model_id") != MODEL_SPECS["2b"].model_id
        or tokenizer_snapshot.get("revision") != MODEL_SPECS["2b"].revision
    ):
        raise FoundationAuthorizationError(
            "authorization tokenizer snapshot binding is not exact"
        )
    _require_digest(
        tokenizer_snapshot.get("receipt_sha256"),
        label="authorization tokenizer receipt",
    )
    _require_digest(
        tokenizer_snapshot.get("snapshot_sha256"),
        label="authorization tokenizer snapshot",
    )
    _scope_snapshot_path(scope, repo_root=repo_root)
    stage = scope.get("stage")
    if stage not in _STAGE_TOKEN_CEILINGS:
        raise FoundationAuthorizationError("authorization stage is unknown")
    if scope.get("token_ceiling") != _STAGE_TOKEN_CEILINGS[stage]:
        raise FoundationAuthorizationError("authorization stage and ceiling differ")
    if scope.get("local_profile") != _LOCAL_PROFILE:
        raise FoundationAuthorizationError(
            "authorization is not the exact local profile"
        )
    if scope.get("learning_rates") != [0.00005, 0.0001, 0.0002]:
        raise FoundationAuthorizationError("authorization learning-rate scope changed")
    if scope.get("authorized_lane_weights") != _stage_lane_weights(stage):
        raise FoundationAuthorizationError("authorization lane-weight map changed")
    if _is_cloud_scope(scope):
        _assert_exact_cloud_posture(scope)
    else:
        if scope.get("source_data_policy") != _SOURCE_POLICY:
            raise FoundationAuthorizationError("protected source policy changed")
        if scope.get("budget") != _BUDGET:
            raise FoundationAuthorizationError(
                "authorization budget must remain zero-paid local"
            )
    if scope.get("output_root") != _OUTPUT_ROOT:
        raise FoundationAuthorizationError("authorization output root changed")
    _validate_commit_binding(repo_root, scope.get("code_commit"))


def _deep_freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType(
            {key: _deep_freeze(item) for key, item in value.items()}
        )
    if isinstance(value, list):
        return tuple(_deep_freeze(item) for item in value)
    return value


def verify_foundation_authorization(
    authorization_path: Path,
    *,
    repo_root: Path,
    registry_path: Path | None = None,
    _tokenizer_loader=None,
) -> VerifiedFoundationAuthorization:
    """Verify one exact final authorization and every held artifact before use."""

    del registry_path
    root = _absolute_lexical(repo_root)
    path = _absolute_lexical(authorization_path)
    pending_template = _absolute_lexical(
        root / "docs/data/training-authorizations/pneuma-foundation-v0.pending.json"
    )
    if path == pending_template:
        raise FoundationAuthorizationError("foundation training is not authorized")
    try:
        with _hold_artifacts(
            {"authorization": path},
            repo_root=root,
            max_sizes={"authorization": _AUTHORIZATION_MANIFEST_SIZE_CEILING},
            max_total_size=_AUTHORIZATION_MANIFEST_SIZE_CEILING,
        ) as authorization_held:
            manifest = _strict_json_bytes(
                authorization_held["authorization"].read.payload,
                label="foundation authorization",
            )
            _validate_manifest(manifest)
            status = manifest.get("authorization_status")
            if status != "authorized":
                raise FoundationAuthorizationError(
                    "foundation training is not authorized"
                )
            scope = manifest["scope"]
            stage = scope["stage"]
            cloud = _is_cloud_scope(scope)
            _require_exact_authorization_path(
                path,
                repo_root=root,
                status="authorized",
                stage=stage,
                cloud=cloud,
            )
            digest = manifest["scope_digest"]
            computed = authorization_scope_digest(scope)
            approval = manifest["operator_approval"]
            if not hmac.compare_digest(digest, computed):
                raise FoundationAuthorizationError(
                    "authorization scope digest does not match"
                )
            if not hmac.compare_digest(approval["scope_digest"], digest):
                raise FoundationAuthorizationError(
                    "operator scope digest does not match"
                )
            phrase = f"{APPROVAL_PHRASE_PREFIX} {digest}"
            phrase_sha256 = hashlib.sha256(phrase.encode("utf-8")).hexdigest()
            if not hmac.compare_digest(
                approval["approval_phrase_sha256"],
                phrase_sha256,
            ):
                raise FoundationAuthorizationError(
                    "operator approval phrase hash changed"
                )
            if (
                not isinstance(approval["operator_id"], str)
                or not approval["operator_id"].strip()
                or approval["operator_id"] != approval["operator_id"].strip()
            ):
                raise FoundationAuthorizationError("operator approval is invalid")
            _validated_utc_timestamp(approval["approved_at"])
            _assert_exact_scope(scope, repo_root=root)
            if cloud:
                _verify_cloud_gate_report(scope, repo_root=root)
            snapshot_path = _scope_snapshot_path(scope, repo_root=root)
            verified_snapshot = _verify_authorization_snapshot(
                snapshot_path,
                repo_root=root,
            )
            _assert_snapshot_binding(
                scope["tokenizer_snapshot"],
                verified_snapshot,
                repo_root=root,
            )
            tokenizer = _load_and_reverify_tokenizer(
                verified_snapshot,
                repo_root=root,
                tokenizer_loader=_tokenizer_loader,
            )
            bindings = scope["artifacts"]
            if set(bindings) != set(_artifact_fields(stage)):
                raise FoundationAuthorizationError(
                    "authorization artifact set is incomplete"
                )
            paths = {
                name: _path_from_binding(binding, repo_root=root)
                for name, binding in bindings.items()
            }
            evidence_bindings = _flatten_scope_bindings(scope, stage=stage)
            evidence_paths = {
                name: _path_from_binding(binding, repo_root=root)
                for name, binding in evidence_bindings.items()
            }
            _validate_exact_preparation_paths(
                paths,
                evidence_paths,
                repo_root=root,
                stage=stage,
            )
            all_bindings = {**bindings, **evidence_bindings}
            eval_families = tuple(scope["evidence_artifacts"]["eval_identities"])
            size_limits, total_size_limit = _artifact_size_limits(
                stage,
                eval_families,
            )
            _validate_declared_size_limits(
                all_bindings,
                limits=size_limits,
                total_limit=total_size_limit,
            )
            with _hold_artifacts(
                {**paths, **evidence_paths},
                repo_root=root,
                max_sizes=size_limits,
                max_total_size=total_size_limit,
            ) as artifact_held:
                for name, item in artifact_held.items():
                    binding = all_bindings[name]
                    if (
                        not hmac.compare_digest(item.read.sha256, binding["sha256"])
                        or item.read.size != binding["size"]
                    ):
                        raise FoundationAuthorizationError(
                            f"authorized artifact digest or size changed: {name}"
                        )
                record_membership = _validate_preparation_coherence(
                    scope,
                    {name: item.read for name, item in artifact_held.items()},
                    tokenizer=tokenizer,
                    repo_root=root,
                )
                after_recount = _verify_authorization_snapshot(
                    verified_snapshot.snapshot_path,
                    repo_root=root,
                )
                if after_recount != verified_snapshot:
                    raise FoundationAuthorizationError(
                        "pinned tokenizer snapshot changed during final recount"
                    )
                _revalidate_held(artifact_held)
                _revalidate_held(authorization_held)
                frozen_manifest = _deep_freeze(copy.deepcopy(manifest))
                return VerifiedFoundationAuthorization(
                    model_key=scope["model"]["key"],
                    token_ceiling=scope["token_ceiling"],
                    shard_path=paths["shard"],
                    shard_manifest_path=paths["shard_manifest"],
                    output_root=root / Path(scope["output_root"]),
                    authorized_lane_weights=_deep_freeze(
                        copy.deepcopy(scope["authorized_lane_weights"])
                    ),
                    authorized_record_membership=_deep_freeze(record_membership),
                    scope_digest=digest,
                    manifest=frozen_manifest,
                )
    except FoundationAuthorizationError:
        raise
    except (
        ArtifactPublicationError,
        OSError,
        RuntimeError,
        TypeError,
        ValueError,
    ) as exc:
        raise FoundationAuthorizationError(
            f"authorization verification failed: {exc}"
        ) from exc


def apply_verified_authorization(
    record: Mapping,
    authorization: VerifiedFoundationAuthorization,
) -> EffectiveTrainingRecord:
    """Apply one in-memory lane weight without mutating the persisted record."""

    if not isinstance(authorization, VerifiedFoundationAuthorization):
        raise FoundationAuthorizationError(
            "a verified foundation authorization is required"
        )
    if not isinstance(record, Mapping):
        raise FoundationAuthorizationError("foundation record must be a mapping")
    weight = record.get("training_weight")
    if type(weight) is not float or weight != 0.0 or math.copysign(1.0, weight) < 0:
        raise FoundationAuthorizationError(
            "persisted training weight must be exactly +0.0"
        )
    try:
        validate_foundation_record(record)
    except FoundationRecordError as exc:
        raise FoundationAuthorizationError(
            f"foundation record is invalid: {exc}"
        ) from exc
    source = record.get("source")
    lane = source.get("lane_id") if isinstance(source, Mapping) else None
    if lane not in authorization.authorized_lane_weights:
        raise FoundationAuthorizationError(
            "foundation record lane is not exactly authorized"
        )
    lane_rules = _LANE_RULES.get(lane)
    if lane_rules is None or source.get("dataset_family") != lane_rules.family:
        raise FoundationAuthorizationError(
            "foundation record lane is outside the exact scope"
        )
    disposition = record.get("disposition")
    if (
        not isinstance(disposition, Mapping)
        or disposition.get("terminal_role") != "train"
        or disposition.get("gradient_eligibility") != lane_rules.gradient_eligibility
    ):
        raise FoundationAuthorizationError(
            "foundation record is not eligible for this lane"
        )
    rendered = record.get("rendered")
    target_text = rendered.get("target_text") if isinstance(rendered, Mapping) else None
    if not isinstance(target_text, str) or not target_text.strip():
        raise FoundationAuthorizationError(
            "foundation record target text must be nonempty"
        )
    forecasts = record.get("forecast_targets")
    applicable = isinstance(forecasts, Mapping) and any(
        isinstance(target, Mapping)
        and target.get("applicable") is True
        and target.get("provenance") == "observed_outcome"
        and isinstance(target.get("value"), (int, float))
        and not isinstance(target.get("value"), bool)
        and math.isfinite(target["value"])
        for target in forecasts.values()
    )
    if not applicable:
        raise FoundationAuthorizationError(
            "foundation record needs an applicable outcome-derived forecast"
        )
    record_id = record.get("record_id")
    expected_record_digest = authorization.authorized_record_membership.get(record_id)
    actual_record_digest = _canonical_record_digest(record)
    if not isinstance(expected_record_digest, str) or not hmac.compare_digest(
        expected_record_digest, actual_record_digest
    ):
        raise FoundationAuthorizationError(
            "foundation record is not an exact member of the authorized shard"
        )
    effective_weight = authorization.authorized_lane_weights[lane]
    if (
        type(effective_weight) is not float
        or effective_weight <= 0
        or not math.isfinite(effective_weight)
    ):
        raise FoundationAuthorizationError("authorized effective weight is invalid")
    try:
        return _make_effective_training_record(
            record,
            effective_weight=effective_weight,
        )
    except FoundationRecordError as exc:
        raise FoundationAuthorizationError(
            f"effective training record could not be sealed: {exc}"
        ) from exc


__all__ = [
    "APPROVAL_PHRASE_PREFIX",
    "FoundationAuthorizationError",
    "VerifiedFoundationAuthorization",
    "apply_verified_authorization",
    "artifact_binding",
    "authorization_scope_digest",
    "build_authorization_candidate",
    "current_clean_code_commit",
    "finalize_authorization",
    "required_approval_phrase",
    "verify_foundation_authorization",
]
