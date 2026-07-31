"""Read-only Task 7 implementation-path continuity check against Step 4A.

Run from the repository root:

    timeout 120s .venv/bin/python scripts/research/task7_step4a_continuity.py

This is a one-off forensic receipt for EJ-20260731-task7-step4a-revalidation,
not a delivery gate and not part of any test tier. It executes no lineage path,
writes nothing into the run root, and produces no scientific claim: the Step 4A
root is implementation verification only and stays inadmissible as P0 or
scientific evidence. All live-code derivation happens in memory or under a
system temporary directory, never against the Step 4A root.
"""
import dataclasses
import hashlib
import itertools
import json
import tempfile
from math import inf, isfinite, nan
from pathlib import Path

import pneuma_lab.resampling_null.analysis as analysis_module
import pneuma_lab.resampling_null.artifacts as artifacts_module
import pneuma_lab.resampling_null.assignment as assignment_module
from pneuma_lab.resampling_null.analysis import (analysis_result_payload, classify_verdict,
                                                 manifest_inference_seed)
from pneuma_lab.resampling_null.artifacts import load_record, validate_scientific_graph
from pneuma_lab.resampling_null.assignment import require_schedulable_power_final
from pneuma_lab.resampling_null.cli import _analysis_config
from pneuma_lab.resampling_null.types import (AnalysisConfig, AnalysisResult, AnalysisRow,
                                              ArtifactRef, ContrastResult, GateResult, GroupKind,
                                              GroupLabel, RandomizationResult, ResolutionResult,
                                              SecondaryFamilyResult, SimultaneousBounds, Verdict)

root = Path("build/research/neurips-2026-workshop/step4a-iv-20260730-210059")


def ref(relative: str, *, role: str, media_type: str = "application/json") -> ArtifactRef:
    data = (root / relative).read_bytes()
    return ArtifactRef(role=role, relative_path=relative, sha256=hashlib.sha256(data).hexdigest(),
                       byte_count=len(data), media_type=media_type)


checks: list[tuple[str, object]] = []
notes: list[str] = []

# A. graph binding of the preserved records (Task 7 consumes finalized authority)
validate_scientific_graph(root)
checks.append(("scientific_graph", "PASS"))

manifest_ref = ref("study-manifest.json", role="study_manifest")
manifest = load_record(root / "study-manifest.json")
schedule = load_record(root / "prefix-schedule.json")
analysis = load_record(root / "analysis/analysis.json")
payload = analysis["payload"]

# B. Task 7 authority reload: the preserved power final is still schedulable.
power_final_ref = ArtifactRef(**{k: schedule["payload"]["power_final_ref"][k] for k in
                                 ("role", "relative_path", "sha256", "byte_count", "media_type")})
selection = require_schedulable_power_final(manifest_ref, power_final_ref, run_root=root)
selected = selection.selected_task_ids
checks.append(("power_final_schedulable",
               f"authority={selection.schedule_authority} tier={selection.selected_tier} "
               f"selected_tasks={len(selected)}"))

# C. frozen analysis config bytes still parse into the registered constants, seed-free.
config_ref = payload["config_ref"]
config_bytes = (root / config_ref["relative_path"]).read_bytes()
assert hashlib.sha256(config_bytes).hexdigest() == config_ref["sha256"], "config bytes drifted"
config = _analysis_config(root / config_ref["relative_path"])
assert type(config) is AnalysisConfig
assert "seed" not in json.loads(config_bytes), "frozen analysis config must carry no seed"
checks.append(("frozen_config_parses", f"alpha={config.alpha} delta_star={config.delta_star} "
                                       f"sharp_draws={config.sharp_draws} "
                                       f"multiplier_draws={config.multiplier_draws}"))

# D. manifest-owned inference randomness: deterministic, manifest-bound, caller-free.
study_id = analysis["study_id"]
seed_a = manifest_inference_seed(manifest_ref, study_id=study_id)
mutated = ArtifactRef(role=manifest_ref.role, relative_path=manifest_ref.relative_path,
                      sha256=("0" * 64), byte_count=manifest_ref.byte_count,
                      media_type=manifest_ref.media_type)
assert manifest_inference_seed(mutated, study_id=study_id) != seed_a, "seed not manifest-bound"
assert manifest_inference_seed(manifest_ref, study_id=study_id + "x") != seed_a
# The preserved record's own secondary bound must carry exactly this seed.
recorded_seed = payload["result"]["secondary_family"]["bounds"]["seed"]
assert recorded_seed == seed_a, (recorded_seed, seed_a)
checks.append(("inference_seed", f"{seed_a:016x} matches recorded secondary bound seed"))

# E. roster ancestry: the manifest roster bytes referenced by Task 7 still resolve and hash.
roster_ref = manifest["payload"]["roster_ref"]
roster_bytes = (root / roster_ref["relative_path"]).read_bytes()
assert hashlib.sha256(roster_bytes).hexdigest() == roster_ref["sha256"], "roster bytes drifted"
roster = json.loads(roster_bytes)
assert roster["record_kind"] == "resampling_roster_v1"
roster_ids = {task["task_id"] for task in roster["tasks"]}
missing = [t for t in selected if t not in roster_ids]
assert not missing, f"selected tasks missing from roster: {missing}"
checks.append(("roster_ancestry", f"tasks={len(roster['tasks'])} kind={roster['roster_kind']}"))

# ---------------------------------------------------------------------------
# F. LIVE gate/payload vocabulary, derived by actually running analyze().
#
# analyze() is admission-bound: it reloads power/manifest authority and verifies
# rows against roster bytes on disk. Those three admission I/O calls are shimmed
# in-process (exactly the seams tests/resampling_null/test_analysis.py shims) so
# that a synthetic in-memory row set can reach the real statistical core. Every
# gate, verdict, and payload key below is produced by unmodified live code:
# evaluate_binary_gate_kernel, classify_verdict, analysis_result_payload.
# ---------------------------------------------------------------------------


def _row(task_id: str, *, benchmark: str = "SWE", real: int, sham: int, none: int,
         resample: int) -> AnalysisRow:
    """Hand fixture copied from tests/resampling_null/test_analysis.py::_row."""
    return AnalysisRow(
        task_id=task_id, benchmark=benchmark, stratum="s", lineage="l",
        sensitivity_groups=(GroupLabel(GroupKind.LANGUAGE, "python"),),
        triggered=True, prefix=0, real=real, sham=sham, none=none,
        resample=resample, real_infrastructure_failure=False,
        sham_infrastructure_failure=False, none_infrastructure_failure=False,
        resample_infrastructure_failure=False, pipeline_valid=True,
        invalid_codes=(),
    )


synthetic_rows = [
    _row("s1", real=1, sham=0, none=0, resample=0),
    _row("s2", real=1, sham=0, none=0, resample=0),
    _row("t1", benchmark="TAU", real=0, sham=1, none=1, resample=1),
]

_probe_manifest_ref = ArtifactRef("study_manifest", "study.json", "1" * 64, 1, "application/json")
_probe_power_ref = ArtifactRef("power_report", "power.json", "2" * 64, 1, "application/json")
_probe_roster_ref = ArtifactRef("power_roster", "roster.json", "3" * 64, 1, "application/json")


class _Parent:
    def __init__(self, value):
        self.value = value


class _Selection:
    selected_task_ids = ("s1", "s2", "t1")


_probe_parent = _Parent({
    "study_id": "probe-study",
    "payload": {
        # decision_authority caps draws to 999 -> cheap, and mirrors the
        # bounded implementation-verification path the Step 4A record used.
        "decision_authority": "implementation_verification",
        "roster_ref": {f: getattr(_probe_roster_ref, f)
                       for f in _probe_roster_ref.__dataclass_fields__},
    },
})

_saved = (assignment_module.require_schedulable_power_final,
          artifacts_module._load_direct_scientific_parent,
          analysis_module._verify_roster_rows)
with tempfile.TemporaryDirectory() as probe_root:
    try:
        assignment_module.require_schedulable_power_final = (
            lambda manifest, final, *, run_root: _Selection())
        artifacts_module._load_direct_scientific_parent = (
            lambda *a, **k: _probe_parent)
        analysis_module._verify_roster_rows = lambda *a, **k: None
        live_result = analysis_module.analyze(
            synthetic_rows, AnalysisConfig(), manifest_ref=_probe_manifest_ref,
            power_final_ref=_probe_power_ref, run_root=Path(probe_root),
        )
    finally:
        (assignment_module.require_schedulable_power_final,
         artifacts_module._load_direct_scientific_parent,
         analysis_module._verify_roster_rows) = _saved
    assert not any(Path(probe_root).iterdir()), "probe must not write artifacts"

assert type(live_result) is AnalysisResult
live_codes = tuple(gate.code for gate in live_result.gates)
live_payload_keys = set(analysis_result_payload(live_result))

result = payload["result"]
recorded_codes = tuple(gate["code"] for gate in result["gates"])
assert recorded_codes == live_codes, (recorded_codes, live_codes)
assert set(result) == live_payload_keys, set(result) ^ live_payload_keys
current_fields = {f.name for f in dataclasses.fields(AnalysisResult)}
assert live_payload_keys == current_fields, live_payload_keys ^ current_fields
checks.append(("live_gate_vocabulary",
               f"analyze()-derived codes={len(live_codes)} order-identical; "
               f"payload keys={len(live_payload_keys)} identical"))

assert result["verdict"] in {v.name for v in Verdict}, result["verdict"]
assert set(result["reasons"]) <= set(recorded_codes)
assert list(result["reasons"]) == [g["code"] for g in result["gates"] if not g["passed"]], \
    "reasons must be exactly the unmet gates, in gate order"
checks.append(("verdict_totality", f"{result['verdict']} unmet={len(result['reasons'])}"))

# G. recompute every preserved gate's `passed` from its own observed/threshold.
_COMPARATORS = {
    "==": lambda o, t: o == t,
    "<=": lambda o, t: o <= t,
    ">=": lambda o, t: o >= t,
    "<": lambda o, t: o < t,
    ">": lambda o, t: o > t,
    "is": lambda o, t: o is t,
}
unverifiable_gates = []
for gate in result["gates"]:
    if gate["observed"] is None or gate["threshold"] is None:
        unverifiable_gates.append(gate["code"])
        continue
    op = _COMPARATORS[gate["comparator"]]
    assert bool(op(gate["observed"], gate["threshold"])) == gate["passed"], gate
if unverifiable_gates:
    notes.append(f"gates with JSON-null observed/threshold not recomputable: {unverifiable_gates}")
checks.append(("gate_passed_recomputed",
               f"{len(result['gates']) - len(unverifiable_gates)}/{len(result['gates'])} gates "
               f"agree with their own observed/comparator/threshold"))


# H. rebuild the dataclasses from the record and re-run the live classifier.
#    JSON null encodes "non-finite" without preserving which non-finite value,
#    so every ambiguous field is expanded over {+inf, -inf, nan} and the verdict
#    must be invariant across the whole reconstruction set.
def _randomization(raw):
    if raw is None:
        return None
    return RandomizationResult(**raw)


_AMBIGUOUS = (inf, -inf, nan)


def _slots(raw, *names):
    return [tuple(_AMBIGUOUS) if raw[n] is None else (raw[n],) for n in names]


contrast_names = ("content", "excess", "sham_packet")
axes = []
for name in contrast_names:
    axes.extend(_slots(result[name], "standard_error", "simultaneous_lower", "simultaneous_upper"))

recorded_gates = tuple(GateResult(g["code"], g["passed"], g["observed"], g["comparator"],
                                  g["threshold"]) for g in result["gates"])
resolution = ResolutionResult(**result["resolution"])
sec_raw = result["secondary_family"]
bounds_raw = dict(sec_raw["bounds"])
bounds = SimultaneousBounds(
    family_name=bounds_raw["family_name"],
    contrast_names=tuple(bounds_raw["contrast_names"]),
    estimates=tuple(bounds_raw["estimates"]),
    standard_errors=tuple(inf if v is None else v for v in bounds_raw["standard_errors"]),
    lowers=tuple(-inf if v is None else v for v in bounds_raw["lowers"]),
    uppers=tuple(inf if v is None else v for v in bounds_raw["uppers"]),
    critical_value=inf if bounds_raw["critical_value"] is None else bounds_raw["critical_value"],
    method=bounds_raw["method"], draws=bounds_raw["draws"], seed=bounds_raw["seed"],
    quantile_order_1_based=bounds_raw["quantile_order_1_based"],
)
secondary = SecondaryFamilyResult(
    contrast_names=tuple(sec_raw["contrast_names"]),
    raw_one_sided_p=tuple(sec_raw["raw_one_sided_p"]),
    holm_adjusted_p=tuple(sec_raw["holm_adjusted_p"]),
    bounds=bounds,
)
assert not any(v is None for v in sec_raw["holm_adjusted_p"]), "holm p values must be recorded"

verdicts = set()
for combo in itertools.product(*axes):
    contrasts = {}
    for index, name in enumerate(contrast_names):
        se, lower, upper = combo[index * 3:index * 3 + 3]
        contrasts[name] = ContrastResult(result[name]["estimate"], se, lower, upper,
                                         _randomization(result[name]["randomization"]))
    verdicts.add(classify_verdict(recorded_gates, content=contrasts["content"],
                                  excess=contrasts["excess"],
                                  sham_packet=contrasts["sham_packet"],
                                  resolution=resolution, secondary=secondary))
assert verdicts == {Verdict[result["verdict"]]}, verdicts
checks.append(("verdict_recomputed",
               f"classify_verdict -> {result['verdict']} for all "
               f"{len(list(itertools.product(*axes)))} non-finite reconstructions"))

# I. row_count is bound to the projection record's own expected task count.
projection_ref = payload["projection_ref"]
projection_bytes = (root / projection_ref["relative_path"]).read_bytes()
assert hashlib.sha256(projection_bytes).hexdigest() == projection_ref["sha256"], \
    "projection bytes drifted"
projection = json.loads(projection_bytes)["payload"]
expected_task_count = projection["expected_task_count"]
assert projection["complete"] is True
assert payload["row_count"] == expected_task_count, (payload["row_count"], expected_task_count)
assert len(projection["rows"]) == expected_task_count
assert len(selected) == expected_task_count, (len(selected), expected_task_count)
assert len(roster_ids) >= expected_task_count
assert payload["numeric_receipt"] == {"finite": True}
checks.append(("row_count_bound",
               f"row_count={payload['row_count']} == projection.expected_task_count == "
               f"len(projection.rows) == len(selected_task_ids); roster={len(roster_ids)}"))

for name, detail in checks:
    print(f"{name}: {detail}")
for note in notes:
    print(f"NOTE: {note}")
print("PASS")
