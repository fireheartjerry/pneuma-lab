"""Typed, content-addressed inputs for the real study execution path.

This module is deliberately provider-neutral.  It can validate and replay the
same run specification on a developer machine, while the official mode still
requires a separately supplied authorization artifact before a controller may
submit anything.  The old qualification harness is not accepted here.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
from typing import Literal, cast

from .authorization_keys import trusted_now, verify_ledger_binding, verify_signature
from .errors import CloudManifestError
from .manifests import (
    validate_official_study_authorization,
    validate_production_provider_binding,
    validate_production_run_spec,
)
from .production_surface import require_production_execution_surface
from .worker_allocation import WORKER_IDS, partition_work_ids, verify_partition


RUN_SPEC_KIND = "cloud_production_run_spec"
RUN_SPEC_VERSION = "0.1.0"
WORKER_EVIDENCE_KIND = "cloud_production_worker_evidence"

OFFICIAL_MODEL_REPOSITORY = "Qwen/Qwen3.6-35B-A3B-FP8"
OFFICIAL_MODEL_REVISION = "95a723d08a9490559dae23d0cff1d9466213d989"
OFFICIAL_TOKENIZER_REVISION = OFFICIAL_MODEL_REVISION
OFFICIAL_ENGINE = "vllm"
OFFICIAL_ENGINE_VERSION = "0.19.0"
OFFICIAL_SWE_REPOSITORY = "microsoft/SWE-bench-Live"
OFFICIAL_SWE_REVISION = "70ec57e852e3f2d195790fe71f553e272c691833"
OFFICIAL_SWE_DATASET = "SWE-bench-Live/MultiLang"
OFFICIAL_SWE_DATASET_REVISION = "608f7ae9ab8ea1f9f0d030fe04562cf6bd1a0c8b"
OFFICIAL_TAU_REPOSITORY = "sierra-research/tau2-bench"
OFFICIAL_TAU_REVISION = "fc0055dc4e0a316c3f83133267fbd6faaa770992"

_SHA256 = re.compile(r"\A[0-9a-f]{64}\Z")
_COMMIT = re.compile(r"\A[0-9a-f]{40}\Z")
_IMAGE = re.compile(r"\Asha256:[0-9a-f]{64}\Z")
_BENCHMARK_ALIASES = {
    "SWE": "swe_multilang",
    "swe": "swe_multilang",
    "swe_multilang": "swe_multilang",
    "TAU": "tau2",
    "tau": "tau2",
    "tau2": "tau2",
}


def canonical_bytes(value: object) -> bytes:
    """Return the newline-terminated JSON bytes used by this contract."""

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


def _canonical_scientific_bytes(value: object) -> bytes:
    """Return the sorted pretty JSON bytes emitted by scientific artifact IO."""

    return (
        json.dumps(
            value,
            sort_keys=True,
            indent=4,
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def canonical_digest(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def official_authorization_subject(value: Mapping[str, object]) -> dict[str, object]:
    """Return the non-circular semantic run-spec body signed by authority.

    The final run specification contains the authorization and key-registry
    file references. Signing the digest of those final bytes would require the
    authorization to contain its own digest. The detached subject therefore
    binds every scientific and operational field while replacing only those
    two signature-container references with null.
    """

    copied = json.loads(json.dumps(value, ensure_ascii=False, allow_nan=False))
    if not isinstance(copied, dict):
        raise CloudManifestError("official authorization subject must be an object")
    if copied.get("record_kind") != RUN_SPEC_KIND:
        raise CloudManifestError(
            "official authorization subject has the wrong identity"
        )
    copied["official_authorization_ref"] = None
    copied["official_key_registry_ref"] = None
    return cast(dict[str, object], copied)


def official_authorization_subject_digest(value: Mapping[str, object]) -> str:
    return canonical_digest(official_authorization_subject(value))


def _require_digest(value: object, *, field: str) -> str:
    if type(value) is not str or _SHA256.fullmatch(value) is None:
        raise CloudManifestError(f"{field} must be a lowercase SHA-256 digest")
    return cast(str, value)


def _require_commit(value: object, *, field: str) -> str:
    if type(value) is not str or _COMMIT.fullmatch(value) is None:
        raise CloudManifestError(f"{field} must be a lowercase 40-hex commit")
    return cast(str, value)


def _require_nonempty(value: object, *, field: str) -> str:
    if type(value) is not str or not value:
        raise CloudManifestError(f"{field} must be non-empty text")
    return cast(str, value)


def _safe_relative_path(value: object, *, field: str) -> str:
    path = _require_nonempty(value, field=field)
    candidate = Path(path)
    if (
        candidate.is_absolute()
        or "\\" in path
        or any(part in {"", ".", ".."} for part in path.split("/"))
    ):
        raise CloudManifestError(f"{field} must be a safe run-root-relative POSIX path")
    return path


@dataclass(frozen=True, slots=True)
class FileBinding:
    role: str
    relative_path: str
    sha256: str
    byte_count: int
    media_type: str

    @classmethod
    def from_value(cls, value: object, *, field: str) -> FileBinding:
        if not isinstance(value, Mapping):
            raise CloudManifestError(f"{field} must be an object")
        expected = {"role", "relative_path", "sha256", "byte_count", "media_type"}
        if set(value) != expected:
            raise CloudManifestError(
                f"{field} fields differ from the file-binding contract"
            )
        byte_count = value["byte_count"]
        if type(byte_count) is not int or byte_count < 0:
            raise CloudManifestError(
                f"{field}.byte_count must be a nonnegative integer"
            )
        return cls(
            _require_nonempty(value["role"], field=f"{field}.role"),
            _safe_relative_path(value["relative_path"], field=f"{field}.relative_path"),
            _require_digest(value["sha256"], field=f"{field}.sha256"),
            byte_count,
            _require_nonempty(value["media_type"], field=f"{field}.media_type"),
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "role": self.role,
            "relative_path": self.relative_path,
            "sha256": self.sha256,
            "byte_count": self.byte_count,
            "media_type": self.media_type,
        }


@dataclass(frozen=True, slots=True)
class ProductionRunSpec:
    """Immutable semantic view over one validated production run specification."""

    value: Mapping[str, object]
    digest: str

    @classmethod
    def from_mapping(
        cls, value: Mapping[str, object], *, digest: str | None = None
    ) -> ProductionRunSpec:
        if not isinstance(value, Mapping):
            raise CloudManifestError("production run specification must be an object")
        copied = json.loads(json.dumps(value, ensure_ascii=False, allow_nan=False))
        if not isinstance(copied, dict):
            raise CloudManifestError(
                "production run specification must be a JSON object"
            )
        if (
            copied.get("record_kind") != RUN_SPEC_KIND
            or copied.get("schema_version") != RUN_SPEC_VERSION
        ):
            raise CloudManifestError(
                "production run specification has the wrong identity"
            )
        observed_digest = canonical_digest(copied)
        if digest is not None and digest != observed_digest:
            raise CloudManifestError("production run specification digest differs")
        validate_production_run_spec(cast(Mapping[str, object], copied))
        instance = cls(cast(Mapping[str, object], copied), observed_digest)
        instance.validate_semantics()
        return instance

    @classmethod
    def load(
        cls, path: Path, *, expected_sha256: str | None = None
    ) -> ProductionRunSpec:
        if path.is_symlink() or not path.is_file():
            raise CloudManifestError(
                "production run specification must be one regular file"
            )
        try:
            raw = path.read_bytes()
            value = json.loads(raw.decode("utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise CloudManifestError(
                "production run specification is not valid JSON"
            ) from exc
        if canonical_bytes(value) != raw:
            raise CloudManifestError(
                "production run specification must use canonical JSON bytes"
            )
        observed = hashlib.sha256(raw).hexdigest()
        if expected_sha256 is not None and observed != expected_sha256:
            raise CloudManifestError("production run specification file digest differs")
        return cls.from_mapping(cast(Mapping[str, object], value), digest=observed)

    @property
    def run_mode(self) -> Literal["official_candidate", "official", "local_mock"]:
        return cast(
            Literal["official_candidate", "official", "local_mock"],
            self.value["run_mode"],
        )

    @property
    def study_id(self) -> str:
        return cast(str, self.value["study_id"])

    @property
    def worker_ids(self) -> tuple[str, ...]:
        topology = cast(Mapping[str, object], self.value["worker_topology"])
        return tuple(cast(list[str], topology["worker_ids"]))

    @property
    def task_manifest_ref(self) -> FileBinding:
        return FileBinding.from_value(
            self.value["task_manifest_ref"], field="task_manifest_ref"
        )

    @property
    def image_bindings(self) -> Mapping[str, str]:
        return {
            cast(str, cast(Mapping[str, object], item)["role"]): cast(
                str, cast(Mapping[str, object], item)["image_digest"]
            )
            for item in cast(list[object], self.value["image_bindings"])
        }

    @property
    def authorization_subject_digest(self) -> str:
        """Digest of the complete non-circular official authorization subject."""

        return official_authorization_subject_digest(self.value)

    def file_binding(self, field: str) -> FileBinding:
        return FileBinding.from_value(self.value[field], field=field)

    def verify_power_binding(self, *, run_root: Path) -> Mapping[str, object]:
        """Verify the exact roster-bound C120/C160 final used by an official run."""

        if self.run_mode != "official":
            raise CloudManifestError(
                "power final binding is only valid for official run mode"
            )
        report = load_bound_json(
            self.file_binding("power_report_ref"),
            run_root=run_root,
            allow_scientific_pretty_json=True,
        )
        try:
            from pneuma_lab.resampling_null.artifacts import validate_record
            from pneuma_lab.resampling_null.errors import RecordValidationError

            validated = validate_record(report)
        except RecordValidationError as exc:
            raise CloudManifestError(
                "bound power report fails the registered scientific schema"
            ) from exc
        if validated.get("record_kind") != "resampling_power_report":
            raise CloudManifestError(
                "official power binding must be a resampling_power_report"
            )
        payload = validated.get("payload")
        if not isinstance(payload, Mapping) or payload.get("stage") != "final":
            raise CloudManifestError(
                "official power binding must reference a final power report"
            )
        if payload.get("decision_authority") != "roster_bound_selection":
            raise CloudManifestError(
                "official power binding rejects synthetic or implementation-verification authority"
            )
        finalization = payload.get("finalization")
        if (
            not isinstance(finalization, Mapping)
            or finalization.get("decision") != "GO"
        ):
            raise CloudManifestError(
                "official power binding requires a roster-bound GO final"
            )
        selected_tier = finalization.get("selected_tier")
        if selected_tier not in {120, 160} or selected_tier != self.value.get(
            "power_tier"
        ):
            raise CloudManifestError(
                "official power final selected tier differs from the run specification"
            )
        return cast(Mapping[str, object], validated)

    def verify_provider_binding(self, *, run_root: Path) -> Mapping[str, object]:
        """Validate the concrete provider contract bound by a production plan."""

        if self.run_mode not in {"official_candidate", "official"}:
            raise CloudManifestError(
                "provider binding is only valid for production plans"
            )
        binding = validate_production_provider_binding(
            load_bound_json(
                self.file_binding("provider_binding_ref"), run_root=run_root
            )
        )
        if binding["provider"] != "aws" or binding["region"] != "us-east-1":
            raise CloudManifestError(
                "production provider binding is not the approved AWS region"
            )
        return cast(Mapping[str, object], binding)

    def verify_official_execution_surface(
        self, *, run_root: Path
    ) -> Mapping[str, object]:
        """Verify that the external role-image E2E receipt matches this run."""

        surface = require_production_execution_surface(
            load_bound_json(
                self.file_binding("execution_surface_ref"), run_root=run_root
            )
        )
        if (
            surface["input_lock_sha256"] != self.file_binding("input_lock_ref").sha256
            or surface["source_commit"] != self.value["code_commit"]
        ):
            raise CloudManifestError(
                "production execution surface is not bound to this code or input lock"
            )
        surface_provider_digest = surface.get("provider_binding_sha256")
        if (
            surface_provider_digest is not None
            and surface_provider_digest
            != self.file_binding("provider_binding_ref").sha256
        ):
            raise CloudManifestError(
                "production execution surface provider binding differs"
            )
        surface_images = {
            cast(str, role["role"]): cast(str, role["image_digest"])
            for role in cast(list[Mapping[str, object]], surface["roles"])
        }
        if surface_images != dict(self.image_bindings):
            raise CloudManifestError(
                "production execution surface image bindings differ from the run specification"
            )
        return surface

    def verify_official_authorization(self, *, run_root: Path) -> Mapping[str, object]:
        """Verify the separate signed official-study authority at execution time."""

        if self.run_mode != "official":
            raise CloudManifestError(
                "official authorization is only valid for official run mode"
            )
        authorization = validate_official_study_authorization(
            load_bound_json(
                self.file_binding("official_authorization_ref"), run_root=run_root
            )
        )
        registry = load_bound_json(
            self.file_binding("official_key_registry_ref"), run_root=run_root
        )
        if (
            authorization["status"] != "authorized"
            or authorization["scope"] != "official_p0_step4b"
            or authorization["action_id"] != self.value["action_id"]
            or authorization["study_id"] != self.value["study_id"]
            or authorization["run_spec_subject_sha256"]
            != self.authorization_subject_digest
            or authorization["input_lock_sha256"]
            != self.file_binding("input_lock_ref").sha256
            or authorization["task_manifest_sha256"] != self.task_manifest_ref.sha256
            or authorization["code_commit"] != self.value["code_commit"]
            or authorization["image_bindings"]
            != [
                {"role": role, "image_digest": digest}
                for role, digest in self.image_bindings.items()
            ]
            or authorization["power_report_sha256"]
            != self.file_binding("power_report_ref").sha256
            or authorization["analysis_graph_sha256"]
            != self.file_binding("analysis_graph_ref").sha256
            or authorization["selected_tier"] != self.value["power_tier"]
            or float(authorization["max_usd"])
            != float(cast(Mapping[str, object], self.value["budget"])["max_usd"])
            or authorization["max_attempts"] != 1
            or authorization["spot_only"] is not True
            or authorization["teardown_protected"] is not True
        ):
            raise CloudManifestError(
                "official authorization is not bound to this run specification, inputs, or budget"
            )
        self.verify_official_execution_surface(run_root=run_root)
        self.verify_power_binding(run_root=run_root)
        self.verify_provider_binding(run_root=run_root)
        ledger_binding = FileBinding.from_value(
            authorization["ledger_ref"], field="official_authorization.ledger_ref"
        )
        ledger_path, _ = resolve_binding(ledger_binding, run_root=run_root)
        verify_ledger_binding(authorization, ledger_path)
        verify_signature(authorization, registry, now=trusted_now())
        return cast(Mapping[str, object], authorization)

    def validate_semantics(self) -> None:
        """Apply invariants that JSON Schema cannot express without stale duplication."""

        value = self.value
        if value.get("run_mode") not in {
            "official_candidate",
            "official",
            "local_mock",
        }:
            raise CloudManifestError(
                "run_mode must be official_candidate, official, or local_mock"
            )
        _require_nonempty(value.get("action_id"), field="action_id")
        _require_nonempty(value.get("study_id"), field="study_id")
        _require_commit(value.get("code_commit"), field="code_commit")

        image_bindings = cast(list[object], value.get("image_bindings"))
        if {
            cast(Mapping[str, object], item).get("role") for item in image_bindings
        } != {"controller", "model-server", "benchmark-worker"}:
            raise CloudManifestError(
                "image_bindings must cover exactly the three production roles"
            )
        for index, item in enumerate(image_bindings):
            binding = cast(Mapping[str, object], item)
            digest = binding.get("image_digest")
            if type(digest) is not str or _IMAGE.fullmatch(digest) is None:
                raise CloudManifestError(
                    f"image_bindings[{index}].image_digest is invalid"
                )

        model = cast(Mapping[str, object], value.get("model"))
        if model.get("repository") != OFFICIAL_MODEL_REPOSITORY:
            raise CloudManifestError(
                "production spec must use the registered Qwen3.6 FP8 model"
            )
        if model.get("revision") != OFFICIAL_MODEL_REVISION:
            raise CloudManifestError(
                "production spec model revision differs from the registered revision"
            )
        if model.get("tokenizer_revision") != OFFICIAL_TOKENIZER_REVISION:
            raise CloudManifestError(
                "production spec tokenizer revision differs from the registered revision"
            )
        if (
            model.get("serving_engine") != OFFICIAL_ENGINE
            or model.get("serving_engine_version") != OFFICIAL_ENGINE_VERSION
        ):
            raise CloudManifestError(
                "production spec serving engine is not the registered vLLM pin"
            )

        task_manifest_ref = self.task_manifest_ref
        benchmark_values = cast(list[object], value.get("benchmarks"))
        benchmark_ids = {
            cast(str, cast(Mapping[str, object], item).get("benchmark_id"))
            for item in benchmark_values
        }
        if benchmark_ids != {"swe_multilang", "tau2"}:
            raise CloudManifestError(
                "production spec must bind both registered benchmark surfaces"
            )
        for index, item in enumerate(benchmark_values):
            benchmark = cast(Mapping[str, object], item)
            self._validate_benchmark(benchmark, index=index)
            if (
                benchmark["task_manifest_sha256"] != task_manifest_ref.sha256
                or benchmark["task_manifest_size_bytes"] != task_manifest_ref.byte_count
            ):
                raise CloudManifestError(
                    f"benchmarks[{index}] task manifest binding differs from task_manifest_ref"
                )

        for field in (
            "execution_surface_ref",
            "input_lock_ref",
            "task_manifest_ref",
            "roster_ref",
            "assignment_ref",
            "analysis_graph_ref",
        ):
            self.file_binding(field)
        power_report = value.get("power_report_ref")
        power_tier = value.get("power_tier")
        authorization = value.get("official_authorization_ref")
        if self.run_mode == "official":
            FileBinding.from_value(power_report, field="power_report_ref")
            if power_tier not in {120, 160}:
                raise CloudManifestError(
                    "official run specifications must select C120 or C160"
                )
            FileBinding.from_value(authorization, field="official_authorization_ref")
            FileBinding.from_value(
                value.get("official_key_registry_ref"),
                field="official_key_registry_ref",
            )
        elif self.run_mode == "official_candidate":
            if (
                authorization is not None
                or value.get("official_key_registry_ref") is not None
            ):
                raise CloudManifestError(
                    "official_candidate run specifications cannot carry official authorization"
                )
            if power_report is not None or power_tier is not None:
                raise CloudManifestError(
                    "official_candidate run specifications cannot carry a power selection"
                )
        elif authorization is not None:
            raise CloudManifestError(
                "local_mock run specifications cannot carry official authorization"
            )
        elif value.get("official_key_registry_ref") is not None:
            raise CloudManifestError(
                "local_mock run specifications cannot carry an official key registry"
            )
        elif power_report is not None or power_tier is not None:
            raise CloudManifestError(
                "local_mock run specifications cannot carry a power selection"
            )

        topology = cast(Mapping[str, object], value.get("worker_topology"))
        if tuple(topology.get("worker_ids", ())) != WORKER_IDS:
            raise CloudManifestError(
                "production topology must use the canonical worker order"
            )
        if (
            topology.get("instance_type") != "g6e.2xlarge"
            or topology.get("vcpus_per_worker") != 8
            or topology.get("gpus_per_worker") != 1
        ):
            raise CloudManifestError(
                "production topology differs from the registered two-L40S plan"
            )
        if topology.get("allocation_contract_id") not in {
            "canonical-round-robin-two-worker-v1",
            "two-l40s-swe-dual-tau-subject-simulator-v1",
        }:
            raise CloudManifestError(
                "production topology has an unknown allocation contract"
            )

        budget = cast(Mapping[str, object], value.get("budget"))
        if budget.get("max_attempts") != 1 or budget.get("spot_only") is not True:
            raise CloudManifestError(
                "production budget must remain one-attempt Spot-only"
            )
        if (
            type(budget.get("max_usd")) not in {int, float}
            or float(budget["max_usd"]) <= 0
        ):
            raise CloudManifestError("production budget must have a positive ceiling")

        output = cast(Mapping[str, object], value.get("output"))
        for field in ("root", "worker_evidence_template", "controller_state_path"):
            _safe_relative_path(output.get(field), field=f"output.{field}")

        rng = cast(Mapping[str, object], value.get("rng"))
        if rng.get("contract_id") != "official-study-rng-v1":
            raise CloudManifestError("production spec RNG contract is not registered")
        early_adapter = cast(Mapping[str, object], value.get("benchmark_adapter"))
        early_entrypoint = early_adapter.get("entrypoint")
        if (
            self.run_mode in {"official_candidate", "official"}
            and isinstance(early_entrypoint, list)
            and any(
                "mock" in str(arg).lower() or "fixture" in str(arg).lower()
                for arg in early_entrypoint
            )
        ):
            raise CloudManifestError(
                "official production specs cannot use mock or fixture adapters"
            )
        seeds = rng.get("seeds")
        if not isinstance(seeds, Mapping):
            raise CloudManifestError("production spec RNG seeds must be an object")
        for key, seed in seeds.items():
            _require_digest(seed, field=f"rng.seeds.{key}")
        if self.run_mode == "official_candidate":
            if rng.get("root_u64") is not None:
                raise CloudManifestError(
                    "official_candidate RNG root must remain unrevealed"
                )
            if rng.get("status") != "pending_commitments":
                raise CloudManifestError(
                    "official_candidate RNG must remain pending external commitments"
                )
            if seeds:
                raise CloudManifestError(
                    "official_candidate RNG cannot invent sealed seed digests"
                )
            self.file_binding_from_mapping(
                rng.get("commitment_ref"), field="rng.commitment_ref"
            )
        elif self.run_mode == "official":
            if (
                type(rng.get("root_u64")) is not int
                or rng.get("status") != "sealed"
                or not seeds
            ):
                raise CloudManifestError(
                    "official RNG must carry sealed named seed digests"
                )

        model_server = cast(Mapping[str, object], value.get("model_server"))
        launch = model_server.get("launch_argv")
        if not isinstance(launch, list) or not launch:
            raise CloudManifestError("model-server launch_argv must be explicit")
        if self.run_mode in {"official_candidate", "official"}:
            launch_text = "\x00".join(cast(str, arg) for arg in launch)
            if (
                OFFICIAL_MODEL_REPOSITORY not in launch_text
                or OFFICIAL_MODEL_REVISION not in launch_text
            ):
                raise CloudManifestError(
                    "official model-server command is not bound to the pinned model revision"
                )
            if "vllm.entrypoints.openai.api_server" not in launch:
                raise CloudManifestError(
                    "official model-server command must use the pinned vLLM OpenAI server"
                )

        adapter = cast(Mapping[str, object], value.get("benchmark_adapter"))
        entrypoint = adapter.get("entrypoint")
        if not isinstance(entrypoint, list) or not entrypoint:
            raise CloudManifestError("benchmark adapter entrypoint must be explicit")
        if self.run_mode in {"official_candidate", "official"} and any(
            "mock" in str(arg).lower() or "fixture" in str(arg).lower()
            for arg in entrypoint
        ):
            raise CloudManifestError(
                "official production specs cannot use mock or fixture adapters"
            )
        if self.run_mode in {"official_candidate", "official"}:
            self.file_binding("provider_binding_ref")
            self.file_binding_from_mapping(
                adapter.get("adapter_manifest_ref"),
                field="benchmark_adapter.adapter_manifest_ref",
            )

        if self.run_mode in {"official_candidate", "official"}:
            sampling_by_benchmark = model.get("sampling_by_benchmark")
            if not isinstance(sampling_by_benchmark, Mapping) or set(
                sampling_by_benchmark
            ) != {"swe_multilang", "tau2"}:
                raise CloudManifestError(
                    "production specs must bind benchmark-specific sampling"
                )
            expected_sampling = {
                "swe_multilang": (0.6, 0.95, 20, 0.0, 1.0),
                "tau2": (1.0, 0.95, 20, 1.5, 1.0),
            }
            for benchmark_id, expected in expected_sampling.items():
                sampling = sampling_by_benchmark[benchmark_id]
                if not isinstance(sampling, Mapping):
                    raise CloudManifestError(
                        f"sampling_by_benchmark.{benchmark_id} must be an object"
                    )
                observed = tuple(
                    sampling.get(field)
                    for field in (
                        "temperature",
                        "top_p",
                        "top_k",
                        "presence_penalty",
                        "repetition_penalty",
                    )
                )
                if observed != expected or sampling.get("thinking_mode") is not True:
                    raise CloudManifestError(
                        f"sampling_by_benchmark.{benchmark_id} differs from the registered design"
                    )

    @staticmethod
    def file_binding_from_mapping(value: object, *, field: str) -> FileBinding:
        return FileBinding.from_value(value, field=field)

    @staticmethod
    def _validate_benchmark(value: Mapping[str, object], *, index: int) -> None:
        benchmark_id = value.get("benchmark_id")
        if benchmark_id == "swe_multilang":
            expected = (
                OFFICIAL_SWE_REPOSITORY,
                OFFICIAL_SWE_REVISION,
                OFFICIAL_SWE_DATASET,
                OFFICIAL_SWE_DATASET_REVISION,
            )
        elif benchmark_id == "tau2":
            expected = (
                OFFICIAL_TAU_REPOSITORY,
                OFFICIAL_TAU_REVISION,
                OFFICIAL_TAU_REPOSITORY,
                OFFICIAL_TAU_REVISION,
            )
        else:
            raise CloudManifestError(
                f"benchmarks[{index}] has an unregistered benchmark id"
            )
        observed = tuple(
            value.get(field)
            for field in (
                "repository",
                "revision",
                "dataset_repository",
                "dataset_revision",
            )
        )
        if observed != expected:
            raise CloudManifestError(
                f"benchmarks[{index}] differs from the registered benchmark/task pin"
            )
        _require_digest(
            value.get("task_manifest_sha256"),
            field=f"benchmarks[{index}].task_manifest_sha256",
        )
        size = value.get("task_manifest_size_bytes")
        if type(size) is not int or size < 0:
            raise CloudManifestError(
                f"benchmarks[{index}].task_manifest_size_bytes is invalid"
            )


def resolve_binding(binding: FileBinding, *, run_root: Path) -> tuple[Path, bytes]:
    """Read one bound file without following symlinks or leaving ``run_root``."""

    root = run_root.resolve()
    path = root / binding.relative_path
    try:
        resolved = path.resolve(strict=True)
    except OSError as exc:
        raise CloudManifestError(
            f"bound input is unavailable: {binding.relative_path}"
        ) from exc
    if (
        resolved.parent != path.parent.resolve()
        or path.is_symlink()
        or not path.is_file()
    ):
        raise CloudManifestError(
            f"bound input must be one regular non-symlink file: {binding.relative_path}"
        )
    raw = path.read_bytes()
    if (
        len(raw) != binding.byte_count
        or hashlib.sha256(raw).hexdigest() != binding.sha256
    ):
        raise CloudManifestError(
            f"bound input digest/size mismatch: {binding.relative_path}"
        )
    return path, raw


def load_bound_json(
    binding: FileBinding,
    *,
    run_root: Path,
    allow_scientific_pretty_json: bool = False,
) -> Mapping[str, object]:
    path, raw = resolve_binding(binding, run_root=run_root)
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CloudManifestError(f"bound JSON is invalid: {path}") from exc
    if not isinstance(value, Mapping):
        raise CloudManifestError(f"bound JSON must be an object: {path}")
    if canonical_bytes(value) != raw and not (
        allow_scientific_pretty_json
        and _canonical_scientific_bytes(value) == raw
    ):
        raise CloudManifestError(f"bound JSON must use canonical JSON bytes: {path}")
    return cast(Mapping[str, object], value)


def task_rows(
    spec: ProductionRunSpec, *, run_root: Path
) -> tuple[Mapping[str, object], ...]:
    """Load the registered task registry without interpreting task payloads."""

    registry = load_bound_json(spec.task_manifest_ref, run_root=run_root)
    if (
        registry.get("record_kind") != "resampling_task_registry_v1"
        or registry.get("schema_version") != "1"
    ):
        raise CloudManifestError(
            "production task manifest must be the registered resampling task registry"
        )
    try:
        from pneuma_lab.resampling_null.errors import RecordValidationError
        from pneuma_lab.resampling_null.preflight import validate_task_registry

        validated_registry = dict(registry)
        validate_task_registry(validated_registry)
    except RecordValidationError as exc:
        raise CloudManifestError(
            "production task manifest fails the registered task-registry contract"
        ) from exc
    rows = validated_registry.get("tasks")
    if not isinstance(rows, list) or not rows:
        raise CloudManifestError("production task registry must contain tasks")
    result: list[Mapping[str, object]] = []
    seen: set[str] = set()
    for index, row in enumerate(rows):
        if not isinstance(row, Mapping):
            raise CloudManifestError(f"task registry row {index} is not an object")
        task_id = _require_nonempty(row.get("task_id"), field=f"tasks[{index}].task_id")
        benchmark = _BENCHMARK_ALIASES.get(row.get("benchmark"))
        if benchmark is None:
            raise CloudManifestError(
                f"tasks[{index}].benchmark is not one of the registered surfaces"
            )
        work_id = f"{benchmark}:{task_id}"
        if work_id in seen:
            raise CloudManifestError("production task work identifiers must be unique")
        seen.add(work_id)
        normalized = dict(row)
        normalized["benchmark"] = benchmark
        normalized["work_id"] = work_id
        result.append(normalized)
    return tuple(result)


def work_ids_for_worker(
    spec: ProductionRunSpec, *, worker_id: str, run_root: Path
) -> tuple[str, ...]:
    if worker_id not in WORKER_IDS:
        raise CloudManifestError(
            "worker_id is not one of the approved production workers"
        )
    rows = task_rows(spec, run_root=run_root)
    allocation = partition_work_ids(tuple(cast(str, row["work_id"]) for row in rows))
    return allocation[worker_id]


def verify_work_partition(
    spec: ProductionRunSpec, allocation: Mapping[str, Sequence[str]], *, run_root: Path
) -> dict[str, tuple[str, ...]]:
    rows = task_rows(spec, run_root=run_root)
    return verify_partition(
        allocation, expected_work_ids=tuple(cast(str, row["work_id"]) for row in rows)
    )


__all__ = [
    "FileBinding",
    "OFFICIAL_ENGINE",
    "OFFICIAL_ENGINE_VERSION",
    "OFFICIAL_MODEL_REPOSITORY",
    "OFFICIAL_MODEL_REVISION",
    "OFFICIAL_SWE_DATASET",
    "OFFICIAL_SWE_DATASET_REVISION",
    "OFFICIAL_SWE_REPOSITORY",
    "OFFICIAL_SWE_REVISION",
    "OFFICIAL_TAU_REPOSITORY",
    "OFFICIAL_TAU_REVISION",
    "ProductionRunSpec",
    "canonical_bytes",
    "canonical_digest",
    "load_bound_json",
    "resolve_binding",
    "task_rows",
    "verify_work_partition",
    "work_ids_for_worker",
]
