"""Registered post-run analysis bridge for official four-arm cloud outputs."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from pneuma_lab.resampling_null.analysis import analysis_result_payload, analyze
from pneuma_lab.resampling_null.types import (
    AnalysisConfig,
    AnalysisRow,
    ArtifactRef,
    GroupKind,
    GroupLabel,
    Verdict,
)

from .decision import Evaluation
from .orchestrator import AnalysisArtifact, OutputArtifact
from .records import canonical_bytes


ARMS = frozenset({"REAL", "SHAM", "NONE", "RESAMPLE"})


def _ref(root: Path, path: Path, role: str) -> ArtifactRef:
    payload = path.read_bytes()
    return ArtifactRef(
        role=role,
        relative_path=path.relative_to(root).as_posix(),
        sha256=hashlib.sha256(payload).hexdigest(),
        byte_count=len(payload),
        media_type="application/json",
    )


def _infrastructure_failure(slot: Mapping[str, Any]) -> bool:
    reason = str(slot.get("terminal_reason", "")).lower()
    return "infrastructure" in reason or "provider" in reason


def rows_from_output_index(
    index_path: Path, *, power_root: Path
) -> tuple[AnalysisRow, ...]:
    index = json.loads(index_path.read_text(encoding="utf-8"))
    if index.get("record_kind") != "rapid_campaign_sealed_output_index":
        raise ValueError("official analysis requires the sealed output index")
    roster = json.loads(
        (power_root / "sources" / "c120-roster.json").read_text(encoding="utf-8")
    )
    roster_rows = {row["task_id"]: row for row in roster["tasks"]}
    results: dict[str, Mapping[str, Any]] = {}
    for item in index.get("objects", []):
        path = index_path.parent / item["relative_path"]
        if hashlib.sha256(path.read_bytes()).hexdigest() != item["sha256"]:
            raise ValueError("sealed official output bytes differ")
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
        if value.get("record_kind") == "cloud_official_four_arm_task_result":
            task_id = value.get("task_id")
            if task_id in results:
                raise ValueError("official outputs duplicate a task result")
            results[task_id] = value
    if set(results) != set(roster_rows):
        missing = set(roster_rows) - set(results)
        extra = set(results) - set(roster_rows)
        raise ValueError(
            f"official task-result coverage differs: missing={len(missing)} extra={len(extra)}"
        )
    rows: list[AnalysisRow] = []
    for task_id in sorted(results, key=lambda value: value.encode("utf-8")):
        result = results[task_id]
        registered = roster_rows[task_id]
        slots = result.get("slots")
        if not isinstance(slots, list) or len(slots) != 4:
            raise ValueError("official task result must contain four slots")
        by_arm = {slot.get("arm"): slot for slot in slots if isinstance(slot, dict)}
        if set(by_arm) != ARMS:
            raise ValueError("official task result must cover four unique arms")
        invalid_codes: list[str] = []
        for arm, slot in by_arm.items():
            if type(slot.get("success")) is not bool:
                invalid_codes.append(f"{arm.lower()}_success_invalid")
        prefix_grade = result.get("prefix", {}).get("grade", {})
        prefix = prefix_grade.get("resolved")
        if type(prefix) is not bool:
            prefix = float(prefix_grade.get("reward", 0.0)) == 1.0
        groups = tuple(
            GroupLabel(GroupKind(group["kind"]), group["value"])
            for group in registered["groups"]
        )
        rows.append(
            AnalysisRow(
                task_id=task_id,
                benchmark=registered["benchmark"],
                stratum=registered["stratum"],
                lineage=registered["lineage"],
                sensitivity_groups=groups,
                triggered=bool(result.get("triggered")),
                prefix=int(prefix),
                real=int(bool(by_arm["REAL"].get("success"))),
                sham=int(bool(by_arm["SHAM"].get("success"))),
                none=int(bool(by_arm["NONE"].get("success"))),
                resample=int(bool(by_arm["RESAMPLE"].get("success"))),
                real_infrastructure_failure=_infrastructure_failure(by_arm["REAL"]),
                sham_infrastructure_failure=_infrastructure_failure(by_arm["SHAM"]),
                none_infrastructure_failure=_infrastructure_failure(by_arm["NONE"]),
                resample_infrastructure_failure=_infrastructure_failure(
                    by_arm["RESAMPLE"]
                ),
                pipeline_valid=not invalid_codes,
                invalid_codes=tuple(invalid_codes),
            )
        )
    return tuple(rows)


@dataclass
class OfficialRegisteredAnalysis:
    power_root: Path
    destination: Path

    def analyse(self, output: OutputArtifact) -> AnalysisArtifact:
        index_path = Path(output.locator)
        rows = rows_from_output_index(index_path, power_root=self.power_root)
        manifest_path = self.power_root / "study-manifest.json"
        final_path = self.power_root / "c120-final.json"
        result = analyze(
            rows,
            AnalysisConfig(),
            manifest_ref=_ref(self.power_root, manifest_path, "study_manifest"),
            power_final_ref=_ref(self.power_root, final_path, "power_report"),
            run_root=self.power_root,
        )
        payload = {
            "record_kind": "rapid_campaign_registered_official_analysis",
            "schema_version": "0.1.0",
            "sealed_output_index_sha256": output.sha256,
            "power_final_sha256": hashlib.sha256(final_path.read_bytes()).hexdigest(),
            "task_count": len(rows),
            "result": analysis_result_payload(result),
        }
        encoded = canonical_bytes(payload)
        self.destination.parent.mkdir(parents=True, exist_ok=True)
        self.destination.write_bytes(encoded)
        return AnalysisArtifact(
            hashlib.sha256(encoded).hexdigest(), str(self.destination)
        )


@dataclass
class RegisteredResultReview:
    """Immediate registered validity review; hostile campaign consumes this next."""

    def review(self, analysis: AnalysisArtifact) -> Evaluation:
        value = json.loads(Path(analysis.locator).read_text(encoding="utf-8"))
        result = value["result"]
        verdict = result["verdict"]
        reasons = tuple(str(item) for item in result.get("reasons", []))
        invalid = verdict == Verdict.PIPELINE_INVALID.value
        return Evaluation(
            validity="invalid" if invalid else "valid",
            informative=not invalid,
            favorable=verdict == Verdict.CAUSAL_CONTENT.value,
            evidence_complete=not invalid,
            correctable_findings=reasons if invalid else (),
        )
