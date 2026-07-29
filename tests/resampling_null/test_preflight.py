"""Small high-signal checks for deterministic authority imports."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from pneuma_lab.foundation.artifacts import canonical_json_bytes

from pneuma_lab.resampling_null.artifacts import RecordValidationError
from pneuma_lab.resampling_null.preflight import (
    ClosedJsonImport,
    ConfirmationPreflightRegistry,
    ConfirmationPreflightUnavailable,
    ConfirmationRosterCeremonyCapability,
    import_assignment_program,
    import_closed_json,
    import_task_registry,
    verify_ed25519_canonical_json,
)


GRAMMAR = ClosedJsonImport(
    record_kind="resampling_task_registry_v1",
    fields=frozenset({"record_kind", "schema_version", "revision", "tasks"}),
    exact_integer_fields=frozenset({"revision"}),
    semantic_set_fields=frozenset({"tasks"}),
)


def _source(path: Path, value: object) -> Path:
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
    return path


def test_t3_s05_import_is_closed_normalized_and_content_addressed(
    tmp_path: Path,
) -> None:
    root = tmp_path / "run"
    root.mkdir()
    first = {
        "record_kind": "resampling_task_registry_v1",
        "schema_version": "1",
        "revision": 7,
        "tasks": [{"task_id": "b"}, {"task_id": "a"}],
    }
    second = {**first, "tasks": list(reversed(first["tasks"]))}

    first_ref = import_closed_json(
        _source(tmp_path / "first.json", first),
        grammar=GRAMMAR,
        run_root=root,
        destination_template="inputs/task-registry/{sha256}.json",
        role="task_registry",
    )
    second_ref = import_closed_json(
        _source(tmp_path / "second.json", second),
        grammar=GRAMMAR,
        run_root=root,
        destination_template="inputs/task-registry/{sha256}.json",
        role="task_registry",
    )

    assert first_ref == second_ref
    imported = json.loads((root / first_ref.relative_path).read_bytes())
    assert [row["task_id"] for row in imported["tasks"]] == ["a", "b"]


@pytest.mark.parametrize(
    "mutation",
    [
        {"unknown": True},
        {"revision": True},
        {"schema_version": "e\u0301"},
        {"tasks": [{"task_id": "a"}, {"task_id": "a"}]},
    ],
)
def test_t3_s05_import_rejects_ambiguous_authority(
    tmp_path: Path,
    mutation: dict[str, object],
) -> None:
    root = tmp_path / "run"
    root.mkdir()
    value: dict[str, object] = {
        "record_kind": "resampling_task_registry_v1",
        "schema_version": "1",
        "revision": 7,
        "tasks": [{"task_id": "a"}],
    }
    value.update(mutation)

    with pytest.raises(RecordValidationError):
        import_closed_json(
            _source(tmp_path / "source.json", value),
            grammar=GRAMMAR,
            run_root=root,
            destination_template="inputs/task-registry/{sha256}.json",
            role="task_registry",
        )


def test_t3_s05_concrete_imports_close_nested_scientific_authority(
    tmp_path: Path,
) -> None:
    root = tmp_path / "run"
    root.mkdir()
    registry = {
        "record_kind": "resampling_task_registry_v1",
        "schema_version": "1",
        "tasks": [
            {
                "task_id": "task-a",
                "benchmark": "SWE",
                "stratum": "python",
                "lineage": "repo-a",
                "groups": [
                    {"kind": "domain", "value": "software"},
                    {"kind": "language", "value": "python"},
                ],
            }
        ],
    }
    registry_ref = import_task_registry(
        _source(tmp_path / "registry.json", registry),
        run_root=root,
    )
    assert registry_ref.relative_path == "inputs/task-registry.json"
    imported_registry = json.loads((root / registry_ref.relative_path).read_bytes())
    assert [
        group["kind"] for group in imported_registry["tasks"][0]["groups"]
    ] == ["language", "domain"]

    source_ref = {
        "role": "normalizer",
        "relative_path": "sources/normalizer.py",
        "sha256": "a" * 64,
        "byte_count": 1,
        "media_type": "text/x-python",
    }
    program = {
        "record_kind": "resampling_assignment_program_v1",
        "schema_version": "1",
        "assignment_mode": "synthetic_derangement",
        "matching_algorithm": "synthetic_cyclic_offset_v1",
        "finding_count_band_upper_bounds": [1, 3],
        "report_length_band_upper_bounds": [128, 512],
        "verifier_normalizer_contract": {
            "contract_id": "assignment-verifier-normalizer-v1",
            "normalizer_source_ref": source_ref,
            "normalizer_source_sha256": "a" * 64,
            "report_tokenizer_sha256": "b" * 64,
            "benchmark_component_kinds": {
                "SWE": ["check_runner", "failure_class"],
                "TAU": ["evaluator_component"],
            },
        },
        "assignment_runtime_contract": {
            "implementation": "CPython",
            "python_version": "3.12.3",
            "unicodedata_unidata_version": "15.0.0",
        },
        "backend_receipt_ref": None,
        "stratum_keys": ["benchmark", "stratum"],
    }
    program_ref = import_assignment_program(
        _source(tmp_path / "program.json", program),
        run_root=root,
    )
    assert program_ref.relative_path == "inputs/assignment-program.json"

    malformed = json.loads(json.dumps(program))
    malformed["verifier_normalizer_contract"]["benchmark_component_kinds"]["SWE"] = [
        "check_runner"
    ]
    with pytest.raises(RecordValidationError, match="component kinds"):
        import_assignment_program(
            _source(tmp_path / "malformed.json", malformed),
            run_root=root,
            destination="inputs/malformed-program.json",
        )

    boolean_cutpoint = json.loads(json.dumps(program))
    boolean_cutpoint["finding_count_band_upper_bounds"] = [True]
    with pytest.raises(RecordValidationError, match="non-negative integer"):
        import_assignment_program(
            _source(tmp_path / "boolean.json", boolean_cutpoint),
            run_root=root,
            destination="inputs/boolean-program.json",
        )


def test_t3_s05_concrete_import_validates_and_publishes_one_source_snapshot(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    root = tmp_path / "run"
    root.mkdir()
    source = tmp_path / "registry.json"
    valid = {
        "record_kind": "resampling_task_registry_v1",
        "schema_version": "1",
        "tasks": [
            {
                "task_id": "task-a",
                "benchmark": "SWE",
                "stratum": "python",
                "lineage": "repo-a",
                "groups": [{"kind": "language", "value": "python"}],
            }
        ],
    }
    changed = {**valid, "tasks": [{"attacker_controlled": True}]}
    valid_bytes = json.dumps(valid).encode()
    changed_bytes = json.dumps(changed).encode()
    original_read = Path.read_bytes
    source_reads = 0

    def unstable_read(path: Path) -> bytes:
        nonlocal source_reads
        if path == source:
            source_reads += 1
            return valid_bytes if source_reads == 1 else changed_bytes
        return original_read(path)

    monkeypatch.setattr(Path, "read_bytes", unstable_read)
    imported = import_task_registry(source, run_root=root)

    assert source_reads == 1
    assert json.loads((root / imported.relative_path).read_bytes()) == valid

    alternate = json.loads(json.dumps(valid))
    alternate["tasks"][0]["task_id"] = "task-b"
    alternate["tasks"][0]["lineage"] = "repo-b"
    monkeypatch.setattr(Path, "read_bytes", original_read)
    _source(source, alternate)
    with pytest.raises(RecordValidationError, match="other bytes"):
        import_task_registry(source, run_root=root)
    assert json.loads((root / imported.relative_path).read_bytes()) == valid


def test_t3_s06_ed25519_verifies_exact_canonical_bytes() -> None:
    private_key = Ed25519PrivateKey.from_private_bytes(bytes(range(32)))
    public_key_hex = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    ).hex()
    unsigned: dict[str, object] = {
        "record_kind": "signed_fixture_v1",
        "sequence": 7,
    }
    signature_hex = private_key.sign(
        canonical_json_bytes(unsigned, indent=None)
    ).hex()
    signed = {**unsigned, "runner_signature_ed25519_hex": signature_hex}

    digest = verify_ed25519_canonical_json(
        signed,
        public_key_ed25519_hex=public_key_hex,
        signature_ed25519_hex=signature_hex,
        signature_field="runner_signature_ed25519_hex",
    )

    assert len(digest) == 64
    bad_signature = "00" * 64
    for changed_value, changed_signature, changed_key in (
        ({**signed, "sequence": 8}, signature_hex, public_key_hex),
        (
            {**signed, "runner_signature_ed25519_hex": bad_signature},
            bad_signature,
            public_key_hex,
        ),
        (signed, signature_hex, "00" * 32),
    ):
        with pytest.raises(RecordValidationError, match="verification failed"):
            verify_ed25519_canonical_json(
                changed_value,
                public_key_ed25519_hex=changed_key,
                signature_ed25519_hex=changed_signature,
                signature_field="runner_signature_ed25519_hex",
            )


def test_t3_s06_live_ceremony_capability_fails_closed(tmp_path: Path) -> None:
    with pytest.raises(TypeError, match="no public constructor"):
        ConfirmationRosterCeremonyCapability()
    with pytest.raises(TypeError, match="cannot be subclassed"):

        class ForgedCapability(ConfirmationRosterCeremonyCapability):
            pass

    registry = ConfirmationPreflightRegistry()
    sources = [tmp_path / f"source-{index}.json" for index in range(7)]
    with pytest.raises(ConfirmationPreflightUnavailable, match="unavailable"):
        registry.claim_roster_ceremony(
            qualification_universe_source=sources[0],
            selection_program_source=sources[1],
            precommit_source=sources[2],
            anchor_source=sources[3],
            reveal_source=sources[4],
            eligibility_source=sources[5],
            ceremony_policy_source=sources[6],
            study_id="study-1",
        )
