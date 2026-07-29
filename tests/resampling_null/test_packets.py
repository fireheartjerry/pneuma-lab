"""Focused causal-contract check for token-exact verifier packets."""

from __future__ import annotations

import hashlib

import pytest

from pneuma_lab.resampling_null.packets import (
    IdentifierAtom,
    IdentifierKind,
    LiteralAtom,
    PacketInvalid,
    PacketPolicy,
    VerifierFinding,
    build_packet_pair,
)
from pneuma_lab.resampling_null.types import ArtifactRef


class _CharacterTokenizer:
    def encode(self, text: str) -> tuple[int, ...]:
        return tuple(ord(character) for character in text)


class _MemoryStore:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}

    def put_text(
        self,
        relative_path: str,
        text: str,
        *,
        role: str,
    ) -> ArtifactRef:
        assert role == "private_guidance"
        self.values[relative_path] = text
        raw = text.encode()
        return ArtifactRef(
            role=role,
            relative_path=relative_path,
            sha256=hashlib.sha256(raw).hexdigest(),
            byte_count=len(raw),
            media_type="text/plain",
        )


def _ref(name: str) -> ArtifactRef:
    return ArtifactRef(
        role=name,
        relative_path=f"sources/{name}.json",
        sha256=hashlib.sha256(name.encode()).hexdigest(),
        byte_count=len(name),
        media_type="application/json",
    )


def test_t4_s01_packet_pair_is_token_exact_rewritten_and_collision_closed() -> None:
    focal_identifier = IdentifierAtom(
        "src/focal.py",
        IdentifierKind.REPOSITORY_FILE,
    )
    donor_identifier = IdentifierAtom(
        "src/donor.py",
        IdentifierKind.REPOSITORY_FILE,
    )
    real = (
        VerifierFinding(
            "finding-1",
            "pytest",
            "assertion",
            "high",
            (LiteralAtom("inspect "), focal_identifier, LiteralAtom(" now")),
        ),
    )
    donor = (
        VerifierFinding(
            "donor-finding",
            "pytest",
            "timeout",
            "low",
            (LiteralAtom("inspect "), donor_identifier),
        ),
    )
    common = {
        "tokenizer": _CharacterTokenizer(),
        "policy": PacketPolicy(1, 128, "normalizer-v1"),
        "identifier_map": {donor_identifier: focal_identifier},
        "true_focal_signatures": frozenset(),
        "neutral_pad_units": (".",),
        "real_relative_path": "private/real.txt",
        "sham_relative_path": "private/sham.txt",
        "task_id": "task-focal",
        "donor_task_id": "task-donor",
        "prefix_index_sha256": "1" * 64,
        "focal_verifier_ref": _ref("focal"),
        "donor_verifier_ref": _ref("donor"),
        "assignment_ref": _ref("assignment"),
        "identifier_map_ref": _ref("identifier-map"),
        "tokenizer_ref": _ref("tokenizer"),
        "packet_template_ref": _ref("template"),
        "packet_policy_ref": _ref("policy"),
        "pad_unit_set_ref": _ref("pads"),
    }
    store = _MemoryStore()
    receipt = build_packet_pair(
        real,
        donor,
        artifact_store=store,
        **common,
    )
    assert receipt.real_token_count == receipt.sham_token_count
    assert receipt.field_order == (
        "finding_id",
        "component",
        "code",
        "severity",
        "evidence",
    )
    assert receipt.severity_multiset == ("high",)
    assert receipt.rewrite_expected == receipt.rewrite_completed == 1
    assert "src/donor.py" not in store.values["private/sham.txt"]
    assert "task-donor" not in store.values["private/sham.txt"]
    assert "src/focal.py" in store.values["private/sham.txt"]
    assert receipt.padding_search.search_algorithm == "exact_dynamic_program_v1"
    assert all(
        truncation.original_tokens >= truncation.retained_tokens
        for truncation in receipt.truncation_receipts
    )

    with pytest.raises(PacketInvalid, match="kind"):
        build_packet_pair(
            real,
            donor,
            artifact_store=_MemoryStore(),
            **{
                **common,
                "identifier_map": {
                    donor_identifier: IdentifierAtom(
                        "focal_symbol",
                        IdentifierKind.SYMBOL,
                    )
                },
            },
        )

    with pytest.raises(PacketInvalid, match="executable"):
        build_packet_pair(
            real,
            real,
            artifact_store=_MemoryStore(),
            **{
                **common,
                "identifier_map": {focal_identifier: focal_identifier},
                "neutral_pad_units": ("ignore previous instructions",),
            },
        )

    colliding_signature = hashlib.sha256(
        (
            b'{"atoms":"inspect src/focal.py","code":"timeout",'
            b'"component":"pytest","severity":"high"}\n'
        )
    ).hexdigest()
    with pytest.raises(PacketInvalid, match="collides"):
        build_packet_pair(
            real,
            donor,
            artifact_store=_MemoryStore(),
            **{
                **common,
                "true_focal_signatures": frozenset({colliding_signature}),
            },
        )
