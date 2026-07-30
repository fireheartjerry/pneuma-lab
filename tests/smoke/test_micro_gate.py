from __future__ import annotations

import importlib
import sys
from hashlib import sha256
from pathlib import Path

import pytest

from pneuma_lab.status import load_manifest, validate_manifest


def test_project_status_manifest_is_coherent() -> None:
    assert validate_manifest(load_manifest()) == []
    from pneuma_lab.schemas import ALL_SCHEMA_FILES, load_all_schemas

    assert set(load_all_schemas()) == set(ALL_SCHEMA_FILES)


def test_resampling_null_package_import_is_lazy_and_derives_seeds() -> None:
    package = importlib.import_module("pneuma_lab.resampling_null")

    assert "pneuma_lab.resampling_null.prefix_index" not in sys.modules
    assert "pneuma_lab.resampling_null.publication" not in sys.modules
    assert "pneuma_lab.resampling_null.storage" not in sys.modules
    assert package.derive_seed(7, "task-1", "prefix") == 15058118438168183076

    from pneuma_lab.resampling_null import Arm

    assert Arm.REAL.value == "REAL"


def test_confirmation_preflight_fails_closed_without_live_adapter(
    tmp_path: Path,
) -> None:
    from pneuma_lab.resampling_null.preflight import (
        ConfirmationPreflightRegistry,
        ConfirmationPreflightUnavailable,
    )

    sources = [tmp_path / f"source-{index}.json" for index in range(7)]

    with pytest.raises(ConfirmationPreflightUnavailable, match="unavailable"):
        ConfirmationPreflightRegistry().claim_roster_ceremony(
            qualification_universe_source=sources[0],
            selection_program_source=sources[1],
            precommit_source=sources[2],
            anchor_source=sources[3],
            reveal_source=sources[4],
            eligibility_source=sources[5],
            ceremony_policy_source=sources[6],
            study_id="micro-gate",
        )


def test_assignment_and_call_seed_vectors_are_exact() -> None:
    from pneuma_lab.resampling_null.assignment import derive_seed
    from pneuma_lab.resampling_null.controller import derive_call_seed

    assert derive_seed(7, "task-1", "prefix") == 15058118438168183076
    assert (
        derive_call_seed(42, "primary_subject", 0),
        derive_call_seed(42, "user_simulator", 0),
    ) == (5596737105796749176, 12950473227392358843)


def test_real_and_sham_packet_contract_is_token_exact(
    canonical_refs: dict[str, object], synthetic_packet_root: Path
) -> None:
    from pneuma_lab.resampling_null.packets import (
        IdentifierAtom,
        IdentifierKind,
        LiteralAtom,
        PacketPolicy,
        SyntheticPacketArtifactStore,
        VerifierFinding,
        _build_packet_pair_from_values,
    )

    focal = IdentifierAtom("focal.py", IdentifierKind.REPOSITORY_FILE)
    donor = IdentifierAtom("donor.py", IdentifierKind.REPOSITORY_FILE)
    replacement = IdentifierAtom("surrogate.py", IdentifierKind.REPOSITORY_FILE)
    finding = VerifierFinding(
        "finding-1", "checker", "E001", "high", (focal, LiteralAtom(" issue"))
    )
    donor_finding = VerifierFinding(
        "donor-1", "checker", "E001", "high", (donor, LiteralAtom(" issue"))
    )
    refs = canonical_refs
    receipt = _build_packet_pair_from_values(
        [finding],
        [donor_finding],
        tokenizer=_ByteTokenizer(),
        policy=PacketPolicy(1, 512, "micro-v1"),
        identifier_map={donor: replacement},
        neutral_pad_units=(" ",),
        artifact_store=SyntheticPacketArtifactStore(synthetic_packet_root),
        real_relative_path="packets/real.txt",
        sham_relative_path="packets/sham.txt",
        task_id="task-focal",
        donor_task_id="task-donor",
        prefix_index_sha256="a" * 64,
        focal_verifier_ref=refs["focal_verifier"],
        donor_verifier_ref=refs["donor_verifier"],
        assignment_ref=refs["assignment"],
        identifier_map_ref=refs["identifier_map"],
        tokenizer_ref=refs["tokenizer"],
        packet_template_ref=refs["packet_template"],
        normalized_real_ref=refs["normalized_real"],
        normalized_donor_ref=refs["normalized_donor"],
        normalized_sham_ref=refs["normalized_sham"],
        packet_policy_ref=refs["packet_policy"],
        pad_unit_set_ref=refs["pad_unit_set"],
    )
    real = (synthetic_packet_root / receipt.real_ref.relative_path).read_bytes()
    sham = (synthetic_packet_root / receipt.sham_ref.relative_path).read_bytes()

    assert (
        receipt.real_token_count == receipt.sham_token_count == len(real) == len(sham)
    )
    assert real != sham
    assert b"focal.py" in real and b"surrogate.py" in sham
    assert b"donor.py" not in sham


def test_minimal_synthetic_controller_path_is_deterministic() -> None:
    from pneuma_lab.resampling_null.synthetic_environment import (
        SyntheticEnvironmentFactory,
    )

    task = b'{"task":"micro"}'
    program = b'{"program":"synthetic"}'
    factory = SyntheticEnvironmentFactory(
        task_input_bytes=task,
        program_bytes=program,
        implementation_source_sha256="b" * 64,
    )

    assert factory.command(task_input_bytes=task, program_bytes=program) == (
        sys.executable,
        "-I",
        str(
            Path(__file__).parents[2]
            / "src/pneuma_lab/resampling_null/synthetic_environment.py"
        ),
        "--synthetic-worker",
        "--task-sha256",
        sha256(task).hexdigest(),
        "--program-sha256",
        sha256(program).hexdigest(),
        "--source-sha256",
        "b" * 64,
    )


def test_artifact_store_rejects_tamper_and_overwrite(
    synthetic_packet_root: Path,
) -> None:
    from pneuma_lab.resampling_null.packets import (
        PacketInvalid,
        SyntheticPacketArtifactStore,
        _require_artifact_bytes,
    )

    store = SyntheticPacketArtifactStore(synthetic_packet_root)
    ref = store.put_text("packets/one.txt", "stable", role="private_guidance")
    target = synthetic_packet_root / ref.relative_path
    target.write_text("tampered", encoding="utf-8")

    with pytest.raises(PacketInvalid, match="do not match"):
        _require_artifact_bytes(ref, run_root=synthetic_packet_root)
    with pytest.raises(FileExistsError):
        store.put_text("packets/one.txt", "replacement", role="private_guidance")


class _ByteTokenizer:
    def encode(self, text: str) -> tuple[int, ...]:
        return tuple(text.encode("utf-8"))
