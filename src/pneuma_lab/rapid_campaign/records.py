"""Strict canonical records for the rapid experiment campaign."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
from typing import Any, Mapping, cast


SCHEMA_VERSION = "0.1.0"
_SHA_RE = re.compile(r"^[0-9a-f]{64}$")
_ID_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]{0,127}$")


class RecordError(ValueError):
    """A campaign record is malformed or ambiguous."""


def canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def digest_record(value: object) -> str:
    if hasattr(value, "to_mapping"):
        value = value.to_mapping()  # type: ignore[union-attr]
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _require_exact(payload: Mapping[str, Any], expected: set[str], label: str) -> None:
    missing = expected - set(payload)
    extra = set(payload) - expected
    if missing:
        raise RecordError(f"{label} missing fields: {sorted(missing)}")
    if extra:
        raise RecordError(f"{label} unexpected fields: {sorted(extra)}")


def _identifier(value: object, field: str) -> str:
    if type(value) is not str or _ID_RE.fullmatch(value) is None:
        raise RecordError(f"{field} must be a stable identifier")
    return cast(str, value)


def _sha(value: object, field: str) -> str:
    if type(value) is not str or _SHA_RE.fullmatch(value) is None:
        raise RecordError(f"{field} must be a lowercase sha256")
    return cast(str, value)


def _positive_int(value: object, field: str) -> int:
    if type(value) is not int or value <= 0:
        raise RecordError(f"{field} must be a positive integer")
    return cast(int, value)


@dataclass(frozen=True, slots=True)
class CampaignManifest:
    campaign_id: str
    aws_account_id: str
    region: str
    ceiling_microusd: int
    root_version_id: str
    allowed_resource_classes: tuple[str, ...]
    tag_namespace: str
    impact_policy_version: str = "c0-c4-v1"

    def __post_init__(self) -> None:
        _identifier(self.campaign_id, "campaign_id")
        if not re.fullmatch(r"[0-9]{12}", self.aws_account_id):
            raise RecordError("aws_account_id must contain exactly 12 digits")
        if not re.fullmatch(r"[a-z]{2}-[a-z]+-[0-9]", self.region):
            raise RecordError("region is invalid")
        _positive_int(self.ceiling_microusd, "ceiling_microusd")
        _identifier(self.root_version_id, "root_version_id")
        if not self.allowed_resource_classes or len(
            set(self.allowed_resource_classes)
        ) != len(self.allowed_resource_classes):
            raise RecordError("allowed_resource_classes must be unique and non-empty")
        for value in self.allowed_resource_classes:
            _identifier(value, "allowed_resource_class")
        _identifier(self.tag_namespace, "tag_namespace")
        _identifier(self.impact_policy_version, "impact_policy_version")

    def to_mapping(self) -> dict[str, object]:
        return {
            "record_kind": "rapid_campaign_manifest",
            "schema_version": SCHEMA_VERSION,
            "campaign_id": self.campaign_id,
            "aws_account_id": self.aws_account_id,
            "region": self.region,
            "ceiling_microusd": self.ceiling_microusd,
            "root_version_id": self.root_version_id,
            "allowed_resource_classes": list(self.allowed_resource_classes),
            "tag_namespace": self.tag_namespace,
            "impact_policy_version": self.impact_policy_version,
        }

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> CampaignManifest:
        fields = {
            "record_kind",
            "schema_version",
            "campaign_id",
            "aws_account_id",
            "region",
            "ceiling_microusd",
            "root_version_id",
            "allowed_resource_classes",
            "tag_namespace",
            "impact_policy_version",
        }
        _require_exact(payload, fields, "campaign manifest")
        if (
            payload["record_kind"] != "rapid_campaign_manifest"
            or payload["schema_version"] != SCHEMA_VERSION
        ):
            raise RecordError("campaign manifest kind/version differs")
        resources = payload["allowed_resource_classes"]
        if not isinstance(resources, list) or not all(
            type(item) is str for item in resources
        ):
            raise RecordError("allowed_resource_classes must be a list of strings")
        return cls(
            campaign_id=payload["campaign_id"],
            aws_account_id=payload["aws_account_id"],
            region=payload["region"],
            ceiling_microusd=payload["ceiling_microusd"],
            root_version_id=payload["root_version_id"],
            allowed_resource_classes=tuple(resources),
            tag_namespace=payload["tag_namespace"],
            impact_policy_version=payload["impact_policy_version"],
        )


@dataclass(frozen=True, slots=True)
class ExperimentVersion:
    version_id: str
    parent_version_id: str | None
    hypothesis_status: str
    action_id: str
    run_spec_sha256: str
    package_sha256: str
    authorization_sha256: str
    image_set_sha256: str
    power_sha256: str
    declared_criteria_sha256: str
    version_ceiling_microusd: int
    dependencies: Mapping[str, str]

    def __post_init__(self) -> None:
        _identifier(self.version_id, "version_id")
        if self.parent_version_id is not None:
            _identifier(self.parent_version_id, "parent_version_id")
            if self.parent_version_id == self.version_id:
                raise RecordError("experiment version cannot parent itself")
        if self.hypothesis_status not in {
            "confirmatory",
            "exploratory",
            "operational_repair",
        }:
            raise RecordError("hypothesis_status is invalid")
        _identifier(self.action_id, "action_id")
        for field in (
            "run_spec_sha256",
            "package_sha256",
            "authorization_sha256",
            "image_set_sha256",
            "power_sha256",
            "declared_criteria_sha256",
        ):
            _sha(getattr(self, field), field)
        _positive_int(self.version_ceiling_microusd, "version_ceiling_microusd")
        if not self.dependencies:
            raise RecordError("dependencies must not be empty")
        normalized: dict[str, str] = {}
        for key, value in self.dependencies.items():
            normalized[_identifier(key, "dependency name")] = _sha(
                value, f"dependency {key}"
            )
        object.__setattr__(self, "dependencies", dict(sorted(normalized.items())))

    def to_mapping(self) -> dict[str, object]:
        return {
            "record_kind": "rapid_campaign_experiment_version",
            "schema_version": SCHEMA_VERSION,
            "version_id": self.version_id,
            "parent_version_id": self.parent_version_id,
            "hypothesis_status": self.hypothesis_status,
            "action_id": self.action_id,
            "run_spec_sha256": self.run_spec_sha256,
            "package_sha256": self.package_sha256,
            "authorization_sha256": self.authorization_sha256,
            "image_set_sha256": self.image_set_sha256,
            "power_sha256": self.power_sha256,
            "declared_criteria_sha256": self.declared_criteria_sha256,
            "version_ceiling_microusd": self.version_ceiling_microusd,
            "dependencies": dict(self.dependencies),
        }

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> ExperimentVersion:
        fields = {
            "record_kind",
            "schema_version",
            "version_id",
            "parent_version_id",
            "hypothesis_status",
            "action_id",
            "run_spec_sha256",
            "package_sha256",
            "authorization_sha256",
            "image_set_sha256",
            "power_sha256",
            "declared_criteria_sha256",
            "version_ceiling_microusd",
            "dependencies",
        }
        _require_exact(payload, fields, "experiment version")
        if (
            payload["record_kind"] != "rapid_campaign_experiment_version"
            or payload["schema_version"] != SCHEMA_VERSION
        ):
            raise RecordError("experiment version kind/version differs")
        dependencies = payload["dependencies"]
        if not isinstance(dependencies, dict):
            raise RecordError("dependencies must be an object")
        return cls(
            version_id=payload["version_id"],
            parent_version_id=payload["parent_version_id"],
            hypothesis_status=payload["hypothesis_status"],
            action_id=payload["action_id"],
            run_spec_sha256=payload["run_spec_sha256"],
            package_sha256=payload["package_sha256"],
            authorization_sha256=payload["authorization_sha256"],
            image_set_sha256=payload["image_set_sha256"],
            power_sha256=payload["power_sha256"],
            declared_criteria_sha256=payload["declared_criteria_sha256"],
            version_ceiling_microusd=payload["version_ceiling_microusd"],
            dependencies=dependencies,
        )
