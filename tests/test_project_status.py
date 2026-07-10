from __future__ import annotations

import copy
import json
from pathlib import Path

from jsonschema import Draft202012Validator

from pneuma_lab import status


ROOT = Path(__file__).resolve().parents[1]


def _manifest() -> dict:
    return status.load_manifest()


def _official_record() -> dict:
    return {
        "report_kind": "canonical_evidence_summary",
        "source_provenance": {
            "source_kind": "git",
            "git_commit": "a" * 40,
            "tree_state": "clean",
            "remote_refs_containing_commit": ["origin/main"],
            "commit_published": True,
            "official": True,
        },
    }


def test_project_status_schema_is_valid_and_manifest_conforms() -> None:
    schema = json.loads(status.STATUS_SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(_manifest())


def test_project_status_is_checkout_coherent() -> None:
    assert status.validate_manifest(_manifest()) == []


def test_status_report_is_deterministic_and_conservative() -> None:
    manifest = _manifest()
    first = status.render_status(manifest)
    second = status.render_status(manifest)
    assert first == second
    assert "internal Level-4 methodology; real subject not evaluated" in first
    assert "operational nervous system: no" in first
    assert "probes/J-lens: absent" in first
    assert "new training authorized: no" in first
    preflight = manifest["training_and_rsi"]["trainer_preflight"]
    expected_preflight = (
        f"trainer preflight: {preflight['status']}; integrated: "
        f"{'yes' if preflight['integrated'] else 'no'}; authorizes training: no"
    )
    assert expected_preflight in first
    assert "RSI: not operational" in first


def test_status_cli_check_passes(capsys) -> None:
    assert status.main(["--check"]) == 0
    captured = capsys.readouterr()
    assert "schema-valid and checkout-coherent" in captured.out
    assert captured.err == ""


def test_internal_scope_cannot_claim_a_real_subject() -> None:
    manifest = copy.deepcopy(_manifest())
    manifest["evidence"]["real_subject_claim_status"] = "evaluated"
    findings = status.validate_manifest(manifest)
    assert any("real_subject_claim_status" in finding for finding in findings)


def test_missing_nested_status_field_fails_closed() -> None:
    manifest = copy.deepcopy(_manifest())
    del manifest["nine_to_five"]["edges"]
    findings = status.validate_manifest(manifest)
    assert any("nine_to_five" in finding and "edges" in finding for finding in findings)


def test_incomplete_edges_cannot_claim_an_operational_nervous_system() -> None:
    manifest = copy.deepcopy(_manifest())
    manifest["project"]["operational_nervous_system"] = True
    manifest["nine_to_five"]["operational_nervous_system"] = True
    findings = status.validate_manifest(manifest)
    assert any("operational_nervous_system" in finding for finding in findings)


def test_jspace_never_promotes_a_consciousness_claim() -> None:
    manifest = copy.deepcopy(_manifest())
    manifest["jspace"]["supports_consciousness_claim"] = True
    findings = status.validate_manifest(manifest)
    assert any("supports_consciousness_claim" in finding for finding in findings)


def test_training_preflight_stays_non_authorizing_until_integrated() -> None:
    manifest = copy.deepcopy(_manifest())
    manifest["training_and_rsi"]["trainer_preflight"]["status"] = "in_progress"
    manifest["training_and_rsi"]["trainer_preflight"]["integrated"] = True
    findings = status.validate_manifest(manifest)
    assert any("in-progress trainer preflight" in finding for finding in findings)


def test_broken_evidence_reference_fails_closed() -> None:
    manifest = copy.deepcopy(_manifest())
    manifest["systems"][0]["evidence_refs"].append("docs/does-not-exist.md")
    findings = status.validate_manifest(manifest)
    assert any("does not exist" in finding for finding in findings)


def test_untracked_evidence_reference_fails_closed(monkeypatch) -> None:
    manifest = copy.deepcopy(_manifest())
    target = manifest["systems"][0]["evidence_refs"][0]
    original = status._git_tracked

    def fake_tracked(root: Path, relative: str) -> bool:
        if relative == target:
            return False
        return original(root, relative)

    monkeypatch.setattr(status, "_git_tracked", fake_tracked)
    findings = status.validate_manifest(manifest)
    assert any(
        f"referenced path is not Git-tracked: {target}" in finding
        for finding in findings
    )


def test_unknown_and_duplicate_blockers_fail_closed() -> None:
    manifest = copy.deepcopy(_manifest())
    manifest["systems"][-1]["blockers"] = ["B-NOT-DECLARED"]
    manifest["blockers"].append(copy.deepcopy(manifest["blockers"][0]))
    findings = status.validate_manifest(manifest)
    assert any("unknown blocker" in finding for finding in findings)
    assert any("blocker ids are duplicated" in finding for finding in findings)


def test_status_paths_are_repo_relative() -> None:
    manifest = copy.deepcopy(_manifest())
    manifest["systems"][0]["evidence_refs"].append("../outside")
    findings = status.validate_manifest(manifest)
    assert any(
        "systems.0.evidence_refs" in finding or "repo-relative" in finding
        for finding in findings
    )


def test_status_date_format_is_enforced() -> None:
    manifest = copy.deepcopy(_manifest())
    manifest["as_of"] = "not-a-date"
    findings = status.validate_manifest(manifest)
    assert any("schema:as_of" in finding and "date" in finding for finding in findings)


def test_strongest_result_cannot_overclaim_a_real_subject() -> None:
    manifest = copy.deepcopy(_manifest())
    manifest["evidence"]["strongest_result"].update(
        scope="real_subject",
        claim="phenomenal_consciousness_proven",
    )
    findings = status.validate_manifest(manifest)
    assert any("evidence.strongest_result" in finding for finding in findings)


def test_real_subject_and_level5_status_cannot_be_word_promoted() -> None:
    for field, promoted_status in (
        ("real_subject_level4", "implemented"),
        ("level5", "implemented"),
    ):
        manifest = copy.deepcopy(_manifest())
        manifest["evidence"][field]["status"] = promoted_status
        findings = status.validate_manifest(manifest)
        assert any(f"evidence.{field}.status" in finding for finding in findings)


def test_training_authorization_cannot_be_word_promoted() -> None:
    manifest = copy.deepcopy(_manifest())
    manifest["training_and_rsi"]["new_training_authorization"] = "authorized"
    findings = status.validate_manifest(manifest)
    assert any("new_training_authorization" in finding for finding in findings)


def test_edge_status_requires_known_enum_and_current_state() -> None:
    manifest = copy.deepcopy(_manifest())
    manifest["nine_to_five"]["edges"][1]["status"] = "telepathic"
    findings = status.validate_manifest(manifest)
    assert any("nine_to_five.edges.1.status" in finding for finding in findings)

    manifest = copy.deepcopy(_manifest())
    edge = manifest["nine_to_five"]["edges"][2]
    edge["status"] = "implemented"
    edge["evidence_refs"] = ["README.md"]
    findings = status.validate_manifest(manifest)
    assert any(
        "replay_outputs_to_shadow_log must remain not_implemented" in finding
        for finding in findings
    )


def test_system_and_negative_result_cannot_be_word_promoted() -> None:
    manifest = copy.deepcopy(_manifest())
    registry_system = next(
        system for system in manifest["systems"] if system["id"] == "dataset_registry"
    )
    registry_system["status"] = "partial"
    registry_system["blockers"] = ["B-TRAIN-AUTHORIZATION"]
    findings = status.validate_manifest(manifest)
    assert any(
        "dataset_registry must remain status=implemented, scope=offline_research"
        in finding
        for finding in findings
    )

    manifest = copy.deepcopy(_manifest())
    manifest["systems"][4]["scope"] = "production_9to5"
    findings = status.validate_manifest(manifest)
    assert any(
        "dataset_trace_adapters must remain status=implemented, scope=offline_research"
        in finding
        for finding in findings
    )

    manifest = copy.deepcopy(_manifest())
    manifest["evidence"]["negative_results"][0]["verdict"] = (
        "passed_preregistered_hypotheses"
    )
    findings = status.validate_manifest(manifest)
    assert any(
        "must remain failed_preregistered_hypotheses" in finding for finding in findings
    )


def test_negative_result_rejects_duplicate_claims_and_provenance_replacement() -> None:
    manifest = copy.deepcopy(_manifest())
    passed = copy.deepcopy(manifest["evidence"]["negative_results"][0])
    passed["verdict"] = "passed_preregistered_hypotheses"
    manifest["evidence"]["negative_results"].insert(0, passed)
    findings = status.validate_manifest(manifest)
    assert any("negative-result ids are duplicated" in finding for finding in findings)

    manifest = copy.deepcopy(_manifest())
    manifest["evidence"]["negative_results"][0]["evidence_refs"] = ["README.md"]
    findings = status.validate_manifest(manifest)
    assert any(
        "must retain its canonical evidence refs" in finding for finding in findings
    )


def test_canonical_record_requires_path_without_crashing() -> None:
    manifest = copy.deepcopy(_manifest())
    del manifest["artifact_policy"]["canonical_evidence_record"]["path"]
    findings = status.validate_manifest(manifest)
    assert any(
        "canonical_evidence_record" in finding and "path" in finding
        for finding in findings
    )


def test_canonical_record_path_cannot_escape_repo() -> None:
    manifest = copy.deepcopy(_manifest())
    manifest["artifact_policy"]["canonical_evidence_record"]["path"] = (
        "../../outside.json"
    )
    findings = status.validate_manifest(manifest)
    assert any("canonical_evidence_record.path" in finding for finding in findings)


def test_official_record_rejects_boolean_only_provenance() -> None:
    record = {
        "report_kind": "canonical_evidence_summary",
        "source_provenance": {"official": True},
    }
    findings = status._official_record_errors(record, root=ROOT)
    assert any("missing fields" in finding for finding in findings)


def test_official_record_reuses_demo_gate_and_verifies_fetched_refs(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        status,
        "_remote_refs_containing",
        lambda root, commit: ("origin/main",),
    )
    assert status._official_record_errors(_official_record(), root=ROOT) == []

    dirty = _official_record()
    dirty["source_provenance"]["tree_state"] = "dirty"
    findings = status._official_record_errors(dirty, root=ROOT)
    assert any("working tree is dirty" in finding for finding in findings)

    wrong_ref = _official_record()
    wrong_ref["source_provenance"]["remote_refs_containing_commit"] = ["origin/release"]
    findings = status._official_record_errors(wrong_ref, root=ROOT)
    assert any("do not contain its commit" in finding for finding in findings)


def test_malformed_official_tree_state_returns_findings() -> None:
    record = _official_record()
    record["source_provenance"]["tree_state"] = []
    findings = status._official_record_errors(record, root=ROOT)
    assert any("tree_state" in finding for finding in findings)


def test_status_manifest_does_not_embed_drift_prone_counts_or_git_head() -> None:
    text = status.DEFAULT_MANIFEST.read_text(encoding="utf-8")
    assert "test_count" not in text
    assert "git_head" not in text
    assert "rows_verified" not in text


def test_cli_corrupted_manifest_fails_without_output_artifacts(
    tmp_path, capsys
) -> None:
    manifest = copy.deepcopy(_manifest())
    manifest["manifest_kind"] = "not_pneuma_status"
    path = tmp_path / "broken-status.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")

    before = sorted(item.name for item in tmp_path.iterdir())
    assert status.main(["--check", "--manifest", str(path)]) == 1
    after = sorted(item.name for item in tmp_path.iterdir())

    assert before == after == ["broken-status.json"]
    assert "FAIL: project status" in capsys.readouterr().err
