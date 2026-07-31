"""Read-only Task 6 implementation-path continuity check against Step 4A.

Run from the repository root:

    timeout 180s .venv/bin/python scripts/research/task6_step4a_continuity.py

This is a one-off forensic receipt for EJ-20260731-task6-step4a-revalidation,
not a delivery gate and not part of any test tier. It executes no Task-6
lineage step and no Task-6 closure: nothing here freezes, seals, permits,
unblinds, taints, locks, or publishes. It writes nothing into the run root
(asserted by a before/after inventory), spawns no subprocess, and opens no
network. The Step 4A root is implementation verification only and stays
inadmissible as P0 or scientific evidence; every derivation below is either a
pure recomputation in memory or a fail-closed verifier reading preserved bytes.
"""
import hashlib
import json
from pathlib import Path

from pneuma_lab.resampling_null.artifacts import (load_record, validate_preunblind_graph,
                                                  validate_scientific_graph)
from pneuma_lab.resampling_null.errors import RecordValidationError
from pneuma_lab.resampling_null.freeze import verify_frozen_analysis_inputs
from pneuma_lab.resampling_null.projection_candidate import build_candidate
from pneuma_lab.resampling_null.task6_state import (require_preunblind_context,
                                                    require_singleton_absent)
from pneuma_lab.resampling_null.types import ArtifactRef

root = Path("build/research/neurips-2026-workshop/step4a-iv-20260730-210059")

# Read-only contract: the exact inventory (path, size, mtime_ns) is captured
# before any live code touches the root and re-asserted at the end.
_before = sorted((str(p.relative_to(root)), p.stat().st_size, p.stat().st_mtime_ns)
                 for p in root.rglob("*") if p.is_file())


def ref(relative: str, *, role: str, media_type: str = "application/json") -> ArtifactRef:
    data = (root / relative).read_bytes()
    return ArtifactRef(role=role, relative_path=relative, sha256=hashlib.sha256(data).hexdigest(),
                       byte_count=len(data), media_type=media_type)


def as_ref(raw: dict) -> ArtifactRef:
    return ArtifactRef(**{k: raw[k] for k in
                          ("role", "relative_path", "sha256", "byte_count", "media_type")})


def raises(call) -> bool:
    try:
        call()
    except (RecordValidationError, ValueError, TypeError, OSError):
        return True
    return False


checks: list[tuple[str, object]] = []
notes: list[str] = []

freeze = load_record(root / "analysis/freeze.json")
projection = load_record(root / "analysis/projection.json")
receipt = load_record(root / "analysis/unblind-receipt.json")
analysis = load_record(root / "analysis/analysis.json")
schedule = load_record(root / "prefix-schedule.json")

# 1. graph binding: full scientific graph, and the pre-unblind graph with the
#    ledger excluded by its one bound relative name (no aliased ledger present).
validate_scientific_graph(root)
ledger_ref = as_ref(projection["payload"]["task_block_refs"] and
                    load_record(root / projection["payload"]["task_block_refs"][0]
                                ["relative_path"])["payload"]["assignment_ref"])
validate_preunblind_graph(root, ledger_ref)
assert ledger_ref.relative_path == "assignment/ledger.json", ledger_ref.relative_path
checks.append(("graph_binding",
               f"scientific graph PASS; pre-unblind graph PASS with exactly one "
               f"ledger at {ledger_ref.relative_path}"))

# 2. the freeze verifier accepts the freeze's own bytes and fails closed on any
#    single-field mutation of the reference it is handed.
freeze_ref = ref("analysis/freeze.json", role="analysis_freeze")
verify_frozen_analysis_inputs(freeze_ref, run_root=root)
mutated_digest = ArtifactRef(freeze_ref.role, freeze_ref.relative_path, "0" * 64,
                             freeze_ref.byte_count, freeze_ref.media_type)
mutated_count = ArtifactRef(freeze_ref.role, freeze_ref.relative_path, freeze_ref.sha256,
                            freeze_ref.byte_count + 1, freeze_ref.media_type)
assert raises(lambda: verify_frozen_analysis_inputs(mutated_digest, run_root=root))
assert raises(lambda: verify_frozen_analysis_inputs(mutated_count, run_root=root))
checks.append(("frozen_inputs_verified",
               f"verify_frozen_analysis_inputs PASS on own bytes "
               f"(sha256={freeze_ref.sha256[:12]}… bytes={freeze_ref.byte_count}); "
               f"mutated sha256 and mutated byte_count both raise"))

# 3. freeze record integrity: every frozen input lives in the immutable source
#    namespace and hash-matches on disk; the freeze binds a sealed packet index.
freeze_payload = freeze["payload"]
frozen_refs = [(binding["name"], as_ref(binding["ref"]))
               for binding in freeze_payload["source_refs"]]
frozen_refs.append(("config", as_ref(freeze_payload["config_ref"])))
frozen_refs.append(("projection_schema", as_ref(freeze_payload["projection_schema_ref"])))
for name, frozen in frozen_refs:
    assert frozen.relative_path.startswith("sources/analysis-freeze/"), (name, frozen)
    data = (root / frozen.relative_path).read_bytes()
    assert hashlib.sha256(data).hexdigest() == frozen.sha256, name
    assert len(data) == frozen.byte_count, name
packet_index_ref = as_ref(freeze_payload["packet_index_ref"])
packet_index = load_record(root / packet_index_ref.relative_path)
packet_bytes = (root / packet_index_ref.relative_path).read_bytes()
assert hashlib.sha256(packet_bytes).hexdigest() == packet_index_ref.sha256
assert packet_index["record_kind"] == "resampling_packet_index"
assert packet_index["payload"]["stage"] == "sealed", packet_index["payload"]["stage"]
assert packet_index["study_id"] == freeze["study_id"]
checks.append(("freeze_integrity",
               f"{len(frozen_refs)} frozen inputs all under sources/analysis-freeze/ and "
               f"byte-identical; packet index {packet_index_ref.relative_path} "
               f"kind={packet_index['record_kind']} stage=sealed"))

# 4. blinded projection continuity: refs bind the freeze/schedule, and the
#    recorded candidate digest is reproduced by the PURE build_candidate over
#    preserved schedule slot IDs and preserved task-block slot outcomes.
projection_payload = projection["payload"]
assert projection_payload["analysis_freeze_ref"] == {
    "role": freeze_ref.role, "relative_path": freeze_ref.relative_path,
    "sha256": freeze_ref.sha256, "byte_count": freeze_ref.byte_count,
    "media_type": freeze_ref.media_type,
}, "projection does not bind the freeze bytes on disk"
schedule_ref = as_ref(projection_payload["schedule_ref"])
schedule_bytes = (root / schedule_ref.relative_path).read_bytes()
assert hashlib.sha256(schedule_bytes).hexdigest() == schedule_ref.sha256

schedule_rows = schedule["payload"]["tasks"]
schedule_task_ids = [entry["task"]["task_id"] for entry in schedule_rows]
blocks_by_task: dict[str, dict] = {}
for block_raw in projection_payload["task_block_refs"]:
    block_ref = as_ref(block_raw)
    block_bytes = (root / block_ref.relative_path).read_bytes()
    assert hashlib.sha256(block_bytes).hexdigest() == block_ref.sha256, block_ref.relative_path
    block = json.loads(block_bytes)
    assert block["record_kind"] == "resampling_task_block"
    blocks_by_task[block["payload"]["task_id"]] = block["payload"]
assert set(blocks_by_task) == set(schedule_task_ids)

frozen_schedule = [{
    "task_id": task_id,
    "prefix_success": blocks_by_task[task_id]["prefix_success"],
    "slot_ids": [slot["slot_id"] for slot in entry["slots"]],
} for task_id, entry in zip(schedule_task_ids, schedule_rows)]
closed_outcomes = {task_id: [{
    "success": outcome["success"], "prefix_success": outcome["prefix_success"],
    "partial_reward": outcome["partial_reward"],
    "infrastructure_failure": outcome["infrastructure_failure"],
    "counters": outcome["counters"],
} for outcome in blocks_by_task[task_id]["slot_outcomes"]] for task_id in schedule_task_ids}
candidate = build_candidate(frozen_schedule, closed_outcomes)
assert candidate.sha256 == projection_payload["projection_candidate_sha256"], (
    candidate.sha256, projection_payload["projection_candidate_sha256"])
notes.append("prefix_success is an outcome, not a schedule field, so the candidate rebuild "
             "takes it from the task blocks; build_candidate's prefix cross-check is "
             "therefore block-internal, not schedule-versus-block")
checks.append(("projection_candidate_recomputed",
               f"build_candidate over {len(frozen_schedule)} preserved schedule rows + "
               f"task-block outcomes -> {candidate.sha256[:16]}… == recorded "
               f"projection_candidate_sha256"))

# blindness: only opaque A-D slots survive; no clear arm identity is exposed.
projection_bytes = (root / "analysis/projection.json").read_bytes()
for row in projection_payload["rows"]:
    assert [slot["label"] for slot in row["slots"]] == ["A", "B", "C", "D"], row["task_id"]
    for slot in row["slots"]:
        assert set(slot) == {"label", "slot_id", "outcome"}, set(slot)
        assert set(slot["outcome"]) == {"success", "prefix_success", "partial_reward",
                                        "infrastructure_failure", "counters"}
leaked = [token for token in (b"opaque_arm_id", b"arm_id", b'"real"', b'"sham"',
                              b'"none"', b'"resample"') if token in projection_bytes]
assert not leaked, leaked
checks.append(("projection_blindness",
               f"{len(projection_payload['rows'])} rows carry only A-D slots with a closed "
               f"5-key outcome; no arm token present in projection bytes"))

# 5. gated unblind receipt and the paired-publication invariant.
receipt_payload = receipt["payload"]
projection_ref = ref("analysis/projection.json", role="blinded_projection")
assert as_ref(receipt_payload["projection_ref"]) == projection_ref
assert as_ref(receipt_payload["analysis_freeze_ref"]) == freeze_ref
assert as_ref(receipt_payload["assignment_ledger_ref"]) == ledger_ref
assert receipt_payload["expected_task_count"] == projection_payload["expected_task_count"]
receipt_ref = ref("analysis/unblind-receipt.json", role="unblind_receipt")
assert as_ref(analysis["payload"]["unblind_receipt_ref"]) == receipt_ref, \
    "analysis does not bind the unblind receipt's own bytes"
assert as_ref(analysis["payload"]["projection_ref"]) == projection_ref
assert as_ref(analysis["payload"]["analysis_freeze_ref"]) == freeze_ref
pair_transaction = root / "operational/task6/paired-publication.json"
assert not pair_transaction.exists(), "paired-publication transaction marker survives"
checks.append(("gated_unblind",
               f"receipt binds on-disk projection/ledger/freeze bytes and "
               f"expected_task_count={receipt_payload['expected_task_count']}; "
               f"analysis.unblind_receipt_ref == receipt bytes; "
               f"paired-publication.json absent (transaction completed)"))

# 6. durable taint: the one-way marker still fails the gate closed under
#    today's code, for every protected action and both run-wide singletons.
taint = root / "operational/task6/outcome-tainted.json"
assert taint.exists()
assert json.loads(taint.read_text(encoding="utf-8")) == {"state": "outcome_tainted_v1"}
protected = ("resampling_blinded_projection", "resampling_analysis_freeze",
             "resampling_task_block")
for action in protected:
    assert raises(lambda action=action: require_preunblind_context(root, action)), action
# An unprotected action must still pass, so the gate is not vacuously raising.
require_preunblind_context(root, "resampling_unblind_receipt")
for kind in ("resampling_blinded_projection", "resampling_unblind_receipt"):
    assert raises(lambda kind=kind: require_singleton_absent(root, kind)), kind
checks.append(("durable_taint",
               f"outcome-tainted.json present; require_preunblind_context raises for "
               f"{len(protected)} protected actions and passes for an unprotected one; "
               f"both singleton kinds already exist"))

# 7. task-block chain coverage.
on_disk_blocks = sorted((root / "task-blocks").glob("*.json"))
expected_task_count = projection_payload["expected_task_count"]
assert len(on_disk_blocks) == expected_task_count, (len(on_disk_blocks), expected_task_count)
assert len(projection_payload["task_block_refs"]) == expected_task_count
assert len(projection_payload["rows"]) == expected_task_count
assert [row["task_id"] for row in projection_payload["rows"]] == schedule_task_ids
assert len(schedule_task_ids) == len(set(schedule_task_ids)) == expected_task_count
assert analysis["payload"]["row_count"] == expected_task_count
for block_path in on_disk_blocks:
    block = json.loads(block_path.read_bytes())
    assert block["payload"]["task_id"] in blocks_by_task
    assert as_ref(block["payload"]["analysis_freeze_ref"]) == freeze_ref
    assert as_ref(block["payload"]["schedule_ref"]) == schedule_ref
checks.append(("task_block_chain",
               f"task-blocks/*.json={len(on_disk_blocks)} == task_block_refs == "
               f"projection.rows == schedule tasks == analysis.row_count == "
               f"expected_task_count={expected_task_count}; row order equals frozen "
               f"schedule order; every block binds the same freeze and schedule bytes"))

_after = sorted((str(p.relative_to(root)), p.stat().st_size, p.stat().st_mtime_ns)
                for p in root.rglob("*") if p.is_file())
assert _after == _before, "this check must not modify the run root"
checks.append(("read_only_receipt",
               f"{len(_after)} run-root files unchanged (path/size/mtime_ns identical)"))

for name, detail in checks:
    print(f"{name}: {detail}")
for note in notes:
    print(f"NOTE: {note}")
print("PASS")
