"""Milestone claims: closed imports, exact signatures, and live-adapter denial."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from pneuma_lab.foundation.artifacts import canonical_json_bytes
from pneuma_lab.resampling_null.preflight import (
    ClosedJsonImport,
    ConfirmationPreflightRegistry,
    ConfirmationPreflightUnavailable,
    import_closed_json,
    verify_ed25519_canonical_json,
)


pytestmark = pytest.mark.milestone


def test_closed_import_is_normalized_and_content_addressed(tmp_path: Path) -> None:
    root = tmp_path / "run"
    root.mkdir()
    grammar = ClosedJsonImport(
        record_kind="registry",
        fields=frozenset({"record_kind", "revision", "tasks"}),
        exact_integer_fields=frozenset({"revision"}),
        semantic_set_fields=frozenset({"tasks"}),
    )
    source = tmp_path / "registry.json"
    source.write_text(
        json.dumps({"record_kind": "registry", "revision": 1, "tasks": ["b", "a"]}),
        encoding="utf-8",
    )

    ref = import_closed_json(
        source,
        grammar=grammar,
        run_root=root,
        destination_template="inputs/{sha256}.json",
        role="registry",
    )

    assert json.loads((root / ref.relative_path).read_text(encoding="utf-8"))[
        "tasks"
    ] == ["a", "b"]


def test_ed25519_verification_binds_exact_canonical_bytes() -> None:
    private = Ed25519PrivateKey.from_private_bytes(bytes(range(32)))
    public = (
        private.public_key()
        .public_bytes(
            serialization.Encoding.Raw,
            serialization.PublicFormat.Raw,
        )
        .hex()
    )
    unsigned = {"record_kind": "signed", "sequence": 7}
    signature = private.sign(canonical_json_bytes(unsigned, indent=None)).hex()

    assert (
        len(
            verify_ed25519_canonical_json(
                unsigned, public_key_ed25519_hex=public, signature_ed25519_hex=signature
            )
        )
        == 64
    )
    with pytest.raises(Exception, match="verification failed"):
        verify_ed25519_canonical_json(
            {**unsigned, "sequence": 8},
            public_key_ed25519_hex=public,
            signature_ed25519_hex=signature,
        )


def test_confirmation_preflight_is_unavailable_without_live_adapter(
    tmp_path: Path,
) -> None:
    sources = [tmp_path / str(index) for index in range(7)]

    with pytest.raises(ConfirmationPreflightUnavailable):
        ConfirmationPreflightRegistry().claim_roster_ceremony(
            qualification_universe_source=sources[0],
            selection_program_source=sources[1],
            precommit_source=sources[2],
            anchor_source=sources[3],
            reveal_source=sources[4],
            eligibility_source=sources[5],
            ceremony_policy_source=sources[6],
            study_id="study",
        )
