from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from pneuma_lab.cloud.authorization_keys import (
    LEDGER_RELATIVE_PATH,
    instant,
    trusted_now,
    authorization_body_digest,
    canonical_bytes,
    resolve_trusted_key,
    signed_body,
    validate_key_registry,
    verify_ledger_binding,
    verify_signature,
)
from pneuma_lab.cloud.errors import CloudManifestError
from pneuma_lab.cloud.inputs import verify_input_lock
from pneuma_lab.cloud.retrieval import (
    require_authorized,
    retrieve_and_verify,
    validate_retrieval_authorization,
)

from .test_input_lock import _real_parts  # reuse the structurally real identities

from pneuma_lab.cloud.input_lock import build_candidate_input_lock


REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = REPO_ROOT / "fixtures" / "cloud"
LEDGER = REPO_ROOT / LEDGER_RELATIVE_PATH

NOW = "2026-08-01T00:00:00Z"


def _clock(at: str = NOW):
    """A pinned clock. Injecting one is a test seam, never an execution option."""

    return lambda: instant(at)
BOUND_ROW = "CL-026"


# ---------------------------------------------------------------------------
# Helpers: an ephemeral key ceremony, created per test rather than committed.
# ---------------------------------------------------------------------------


def _keypair(seed: bytes = b"\x01" * 32) -> Ed25519PrivateKey:
    return Ed25519PrivateKey.from_private_bytes(seed)


def _registry(private: Ed25519PrivateKey, **overrides) -> dict:
    from cryptography.hazmat.primitives import serialization

    public = private.public_key().public_bytes(
        encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw
    )
    key = {
        "key_id": "approver-primary",
        "approver_id": "jerry",
        "algorithm": "ed25519",
        "public_key_hex": public.hex(),
        "not_before": "2026-01-01T00:00:00Z",
        "not_after": "2027-01-01T00:00:00Z",
        "status": "active",
        "revoked_timestamp": None,
        "revocation_reason": None,
    }
    key.update(overrides)
    return {
        "record_kind": "cloud_approver_key_registry",
        "schema_version": "0.1.0",
        "frozen_timestamp": "2026-07-31T00:00:00Z",
        "keys": [key],
    }


def _ledger_row_digest(row_id: str = BOUND_ROW) -> str:
    prefix = f"| {row_id} |"
    line = next(item for item in LEDGER.read_text(encoding="utf-8").splitlines() if item.startswith(prefix))
    return hashlib.sha256(line.encode("utf-8")).hexdigest()


def _lock() -> dict:
    return build_candidate_input_lock(**_real_parts())


def _authorization(private: Ed25519PrivateKey, lock: dict, **overrides) -> dict:
    record = {
        "record_kind": "cloud_retrieval_authorization",
        "schema_version": "0.2.0",
        "frozen_timestamp": "2026-07-31T00:00:00Z",
        "provenance": {"design_sha256": "1" * 63 + "a", "code_sha256": "2" * 63 + "b"},
        "status": "authorized",
        "input_lock_sha256": verify_input_lock(lock),
        "scopes": ["model", "tokenizer", "benchmark", "container_base", "verifier", "license", "contamination"],
        "byte_ceiling_bytes": 1024,
        "mirror_root": "mirror/step5b",
        "ledger_row_id": BOUND_ROW,
        "ledger_row_sha256": _ledger_row_digest(),
        "human_authorization": {
            "approver_id": "jerry",
            "key_id": "approver-primary",
            "granted_timestamp": "2026-07-31T00:00:00Z",
            "expires_timestamp": "2026-08-07T00:00:00Z",
            "body_sha256": "0" * 64,
            "signature_ed25519": "0" * 128,
        },
    }
    record.update(overrides)
    return _sign(private, record)


def _sign(private: Ed25519PrivateKey, record: dict) -> dict:
    body = canonical_bytes(signed_body(record))
    record["human_authorization"]["body_sha256"] = hashlib.sha256(body).hexdigest()
    record["human_authorization"]["signature_ed25519"] = private.sign(body).hex()
    return record


# ---------------------------------------------------------------------------
# The committed state authorizes nothing.
# ---------------------------------------------------------------------------


def test_committed_registry_trusts_only_the_project_scoped_cloudshell_key() -> None:
    """The public registry names precisely the generated CloudShell key."""

    registry = validate_key_registry(json.loads((FIXTURES / "approver-key-registry.json").read_text(encoding="utf-8")))
    assert [key["key_id"] for key in registry["keys"]] == ["pneuma-b1-20260731"]
    with pytest.raises(CloudManifestError, match="not in the trusted registry"):
        resolve_trusted_key(registry, "approver-primary", now=instant(NOW))


def test_committed_candidate_carries_no_authority() -> None:
    record = validate_retrieval_authorization(json.loads((FIXTURES / "retrieval-authorization-candidate.json").read_text(encoding="utf-8")))
    assert record["status"] == "candidate"
    assert record["ledger_row_id"] is None
    assert record["ledger_row_sha256"] is None
    assert record["human_authorization"] is None


def test_a_candidate_may_not_carry_a_signature(tmp_path: Path) -> None:
    private = _keypair()
    record = _authorization(private, _lock(), status="candidate")
    with pytest.raises(CloudManifestError, match="a candidate must carry no ledger row"):
        validate_retrieval_authorization(record)


def test_a_candidate_can_never_retrieve() -> None:
    lock = _lock()
    record = json.loads((FIXTURES / "retrieval-authorization-candidate.json").read_text(encoding="utf-8"))
    registry = json.loads((FIXTURES / "approver-key-registry.json").read_text(encoding="utf-8"))
    with pytest.raises(CloudManifestError, match="not a candidate"):
        require_authorized(record, lock, key_registry=registry, ledger_path=LEDGER, clock=_clock())


# ---------------------------------------------------------------------------
# Retrieval: authenticated sizes, in-transfer enforcement, durable publication.
# ---------------------------------------------------------------------------


def _uniform_lock(payload: bytes) -> dict:
    """A real candidate lock whose every pinned artifact is exactly `payload`.

    Receipt *paths* stay distinct, since a real candidate lock may not point two
    artifacts at one destination; only the content digests and sizes coincide,
    so one payload satisfies every step of the plan.
    """

    digest = hashlib.sha256(payload).hexdigest()
    size = len(payload)
    parts = _real_parts()
    for pin in (*parts["model_pins"], parts["tokenizer_pin"], *parts["benchmark_pins"], *parts["verifier_sources"]):
        pin["snapshot_receipt"]["sha256"] = digest
        pin["snapshot_receipt"]["size_bytes"] = size
    parts["benchmark_pins"][0]["task_manifest_sha256"] = digest
    parts["benchmark_pins"][0]["task_manifest_size_bytes"] = size
    parts["container_bases"][0]["digest"] = f"linux/amd64@sha256:{digest}"
    parts["container_bases"][0]["manifest_size_bytes"] = size
    for receipt in (*parts["contamination_receipts"], *parts["license_receipts"]):
        receipt["sha256"] = digest
        receipt["size_bytes"] = size
    return build_candidate_input_lock(**parts)


def _chunks(payload: bytes, size: int = 4):
    """A fetcher that streams, so in-transfer enforcement is actually exercised."""

    def fetcher(step):
        for offset in range(0, len(payload), size):
            yield payload[offset:offset + size]
    return fetcher


def _context(private, **overrides):
    context = {"key_registry": _registry(private), "ledger_path": LEDGER, "clock": _clock()}
    context.update(overrides)
    return context


def test_authorized_retrieval_publishes_and_independently_reverifies(tmp_path: Path) -> None:
    """The receipt must attest to a file that exists and rehashes correctly."""

    payload = b"pinned-bytes-of-an-artifact"
    private = _keypair()
    lock = _uniform_lock(payload)
    record = _authorization(private, lock, byte_ceiling_bytes=10_000)
    mirror = tmp_path / "mirror"

    receipts = retrieve_and_verify(lock, record, _chunks(payload), mirror_root=mirror, **_context(private))
    assert [item["kind"] for item in receipts] == ["model", "tokenizer", "benchmark", "benchmark_dataset", "verifier", "container"]

    # Every receipt names a real, durably published file with the pinned bytes.
    for item in receipts:
        installed = Path(item["installed_path"])
        assert installed.is_file(), item["mirror_path"]
        assert installed.read_bytes() == payload
        assert hashlib.sha256(installed.read_bytes()).hexdigest() == item["sha256"]
        assert item["size_bytes"] == len(payload)

    # Nothing is left behind in staging.
    assert not (mirror / ".staging").exists()


def test_substituted_bytes_are_refused_and_nothing_is_published(tmp_path: Path) -> None:
    payload = b"pinned-bytes-of-an-artifact"
    private = _keypair()
    lock = _uniform_lock(payload)
    record = _authorization(private, lock, byte_ceiling_bytes=10_000)
    mirror = tmp_path / "mirror"

    substituted = b"substituted-bytes-of-eq-len"
    assert len(substituted) == len(payload)  # same size, wrong content
    with pytest.raises(CloudManifestError, match="do not match the pinned digest"):
        retrieve_and_verify(lock, record, _chunks(substituted), mirror_root=mirror, **_context(private))

    published = [path for path in mirror.rglob("*") if path.is_file()]
    assert published == [], published


def test_a_plan_over_the_ceiling_is_refused_before_any_fetch(tmp_path: Path) -> None:
    """The whole authenticated plan is checked before the first byte moves."""

    payload = b"pinned-bytes"
    private = _keypair()
    lock = _uniform_lock(payload)
    record = _authorization(private, lock, byte_ceiling_bytes=10)
    calls: list[str] = []

    def fetcher(step):
        calls.append(step["kind"])
        yield payload

    with pytest.raises(CloudManifestError, match="authenticated plan size .* exceeds the authorized byte ceiling"):
        retrieve_and_verify(lock, record, fetcher, mirror_root=tmp_path / "mirror", **_context(private))
    assert calls == []


def test_an_oversized_transfer_is_abandoned_mid_stream(tmp_path: Path) -> None:
    """A fetcher exceeding its authenticated size is cut off, not absorbed.

    The size is authenticated: it is pinned in the input lock, whose digest sits
    inside the signed authorization body. So a fetcher cannot simply declare a
    larger size, and it cannot spend past the ceiling before being noticed.
    """

    payload = b"pinned-bytes"
    private = _keypair()
    lock = _uniform_lock(payload)
    record = _authorization(private, lock, byte_ceiling_bytes=10_000)
    delivered = {"bytes": 0}

    def flooding_fetcher(step):
        # Ten times the authenticated size, streamed in small chunks.
        for _ in range(10):
            delivered["bytes"] += len(payload)
            yield payload

    with pytest.raises(CloudManifestError, match="exceeded its authenticated size"):
        retrieve_and_verify(lock, record, flooding_fetcher, mirror_root=tmp_path / "mirror", **_context(private))

    # Cut off almost immediately rather than after the full flood.
    assert delivered["bytes"] <= 2 * len(payload)
    assert [path for path in (tmp_path / "mirror").rglob("*") if path.is_file()] == []


def test_a_short_transfer_is_refused(tmp_path: Path) -> None:
    payload = b"pinned-bytes"
    private = _keypair()
    lock = _uniform_lock(payload)
    record = _authorization(private, lock, byte_ceiling_bytes=10_000)

    def truncating_fetcher(step):
        yield payload[:-1]

    with pytest.raises(CloudManifestError, match="ended at .* not its authenticated size"):
        retrieve_and_verify(lock, record, truncating_fetcher, mirror_root=tmp_path / "mirror", **_context(private))


def test_an_occupied_mirror_destination_is_refused(tmp_path: Path) -> None:
    """A published artifact is never silently overwritten."""

    payload = b"pinned-bytes"
    private = _keypair()
    lock = _uniform_lock(payload)
    record = _authorization(private, lock, byte_ceiling_bytes=10_000)
    mirror = tmp_path / "mirror"

    receipts = retrieve_and_verify(lock, record, _chunks(payload), mirror_root=mirror, **_context(private))
    assert receipts
    with pytest.raises(CloudManifestError, match="already occupied"):
        retrieve_and_verify(lock, record, _chunks(payload), mirror_root=mirror, **_context(private))


# ---------------------------------------------------------------------------
# Time is resolved from a trusted clock, never from the caller.
# ---------------------------------------------------------------------------


def test_the_execution_gate_takes_no_caller_supplied_instant() -> None:
    """Regression: an `at` parameter made expiry advisory.

    With a caller-supplied evaluation instant, replaying an expired
    authorization needed nothing more than passing an earlier in-window value.
    The gate now resolves time itself.
    """

    import inspect

    for gate in (require_authorized, retrieve_and_verify):
        assert "at" not in inspect.signature(gate).parameters, gate.__name__
        assert inspect.signature(gate).parameters["clock"].default is trusted_now


def test_an_expired_authorization_is_refused_by_the_trusted_clock(tmp_path: Path) -> None:
    """The default clock rejects a long-expired approval, whatever today is.

    The approval window is set in the past and the key window wide, so this
    stays deterministic no matter when the suite runs — the point is that the
    execution default refuses it, not that a particular date does.
    """

    private = _keypair()
    lock = _uniform_lock(b"pinned-bytes")
    record = _authorization(private, lock, byte_ceiling_bytes=10_000, human_authorization={
        "approver_id": "jerry", "key_id": "approver-primary",
        "granted_timestamp": "2020-01-01T00:00:00Z", "expires_timestamp": "2020-01-02T00:00:00Z",
        "body_sha256": "0" * 64, "signature_ed25519": "0" * 128,
    })
    registry = _registry(private, not_before="2019-01-01T00:00:00Z", not_after="2099-01-01T00:00:00Z")

    # No clock override: this uses trusted_now, and the approval expired in 2020.
    with pytest.raises(CloudManifestError, match="expired at"):
        require_authorized(record, lock, key_registry=registry, ledger_path=LEDGER)

    # Replaying it requires an injected in-window clock, which the execution
    # default does not expose. This is exactly the replay the old `at`
    # parameter made available to any caller.
    replayed = require_authorized(record, lock, key_registry=registry, ledger_path=LEDGER, clock=_clock("2020-01-01T12:00:00Z"))
    assert replayed["status"] == "authorized"


# ---------------------------------------------------------------------------
# Key trust: enumeration, revocation, validity window.
# ---------------------------------------------------------------------------


def test_an_unenumerated_key_authorizes_nothing_even_with_a_valid_signature() -> None:
    """The central property: mathematics is not authority; the registry is."""

    private = _keypair()
    record = _authorization(private, _lock())
    stranger = _registry(_keypair(seed=b"\x02" * 32))
    # The signature is perfectly valid; the key simply is not trusted.
    with pytest.raises(CloudManifestError, match="not in the trusted registry"):
        verify_signature(record, {**stranger, "keys": [{**stranger["keys"][0], "key_id": "other-key"}]}, now=instant(NOW))


def test_a_revoked_key_is_refused() -> None:
    private = _keypair()
    record = _authorization(private, _lock())
    registry = _registry(private, status="revoked", revoked_timestamp="2026-07-31T12:00:00Z", revocation_reason="laptop lost")
    with pytest.raises(CloudManifestError, match="was revoked"):
        verify_signature(record, registry, now=instant(NOW))


@pytest.mark.parametrize("at", ["2025-12-31T23:59:59Z", "2027-01-02T00:00:00Z"])
def test_a_key_outside_its_validity_window_is_refused(at: str) -> None:
    private = _keypair()
    record = _authorization(private, _lock(), human_authorization={
        "approver_id": "jerry", "key_id": "approver-primary",
        "granted_timestamp": "2025-01-01T00:00:00Z", "expires_timestamp": "2028-01-01T00:00:00Z",
        "body_sha256": "0" * 64, "signature_ed25519": "0" * 128,
    })
    with pytest.raises(CloudManifestError, match="outside its validity window"):
        verify_signature(record, _registry(private), now=instant(at))


def test_a_signature_from_a_different_approver_is_refused() -> None:
    private = _keypair()
    record = _authorization(private, _lock())
    registry = _registry(private, approver_id="someone-else")
    with pytest.raises(CloudManifestError, match="belongs to"):
        verify_signature(record, registry, now=instant(NOW))


def test_registry_rejects_incoherent_key_entries() -> None:
    private = _keypair()
    with pytest.raises(CloudManifestError, match="empty validity window"):
        validate_key_registry(_registry(private, not_before="2027-01-01T00:00:00Z", not_after="2026-01-01T00:00:00Z"))
    with pytest.raises(CloudManifestError, match="must record when it was revoked"):
        validate_key_registry(_registry(private, status="revoked"))
    with pytest.raises(CloudManifestError, match="must not carry a revocation timestamp"):
        validate_key_registry(_registry(private, revoked_timestamp="2026-07-31T00:00:00Z"))

    duplicated = _registry(private)
    duplicated["keys"].append(dict(duplicated["keys"][0]))
    with pytest.raises(CloudManifestError, match="duplicate approver key id"):
        validate_key_registry(duplicated)


# ---------------------------------------------------------------------------
# Expiry.
# ---------------------------------------------------------------------------


def test_an_expired_authorization_is_refused() -> None:
    private = _keypair()
    record = _authorization(private, _lock())
    with pytest.raises(CloudManifestError, match="expired at"):
        verify_signature(record, _registry(private), now=instant("2026-08-08T00:00:00Z"))


def test_an_authorization_is_not_valid_before_it_was_granted() -> None:
    private = _keypair()
    record = _authorization(private, _lock())
    with pytest.raises(CloudManifestError, match="not yet valid"):
        verify_signature(record, _registry(private), now=instant("2026-07-30T00:00:00Z"))


def test_fractional_seconds_are_ordered_as_instants_not_as_strings() -> None:
    """Regression: lexical comparison put `…00.001Z` *before* `…00Z`.

    Found by hostile review. Because `.` sorts below `Z`, a string comparison
    made an authorization that had expired a millisecond earlier look live, and
    separately made an in-window key look out of window. Both are now compared
    as parsed instants.
    """

    private = _keypair()
    record = _authorization(private, _lock(), human_authorization={
        "approver_id": "jerry", "key_id": "approver-primary",
        "granted_timestamp": "2026-07-31T00:00:00Z", "expires_timestamp": "2026-08-06T00:00:00Z",
        "body_sha256": "0" * 64, "signature_ed25519": "0" * 128,
    })
    # One millisecond after expiry: genuinely expired, and lexically "earlier".
    with pytest.raises(CloudManifestError, match="expired at"):
        verify_signature(record, _registry(private), now=instant("2026-08-06T00:00:00.001Z"))

    # A fractional not_after must not push an in-window instant out of window.
    registry = _registry(private, not_after="2026-12-31T23:59:59.999Z")
    assert verify_signature(record, registry, now=instant("2026-08-01T00:00:00Z"))["key_id"] == "approver-primary"


def test_a_malformed_timestamp_fails_closed() -> None:
    """Timestamp parsing is the boundary, so it must refuse rather than default."""

    with pytest.raises(CloudManifestError, match="malformed UTC timestamp"):
        instant("not-a-timestamp")


def test_an_authorization_that_expires_before_it_is_granted_is_refused() -> None:
    private = _keypair()
    record = _authorization(private, _lock(), human_authorization={
        "approver_id": "jerry", "key_id": "approver-primary",
        "granted_timestamp": "2026-08-07T00:00:00Z", "expires_timestamp": "2026-07-31T00:00:00Z",
        "body_sha256": "0" * 64, "signature_ed25519": "0" * 128,
    })
    with pytest.raises(CloudManifestError, match="expires no later than it was granted"):
        verify_signature(record, _registry(private), now=instant(NOW))


# ---------------------------------------------------------------------------
# The signature covers the complete body.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("field,value", [
    ("scopes", ["model"]),
    ("byte_ceiling_bytes", 10 ** 12),
    ("mirror_root", "mirror/elsewhere"),
    ("input_lock_sha256", "9" * 64),
    ("ledger_row_id", "CL-025"),
    ("status", "candidate"),
    ("frozen_timestamp", "2026-01-01T00:00:00Z"),
])
def test_tampering_with_any_signed_field_breaks_the_signature(field: str, value: object) -> None:
    """Every field is inside the signed body, so none can be edited after approval."""

    private = _keypair()
    record = _authorization(private, _lock())
    record[field] = value
    with pytest.raises(CloudManifestError, match="does not match the canonical signed body|does not verify"):
        verify_signature(record, _registry(private), now=instant(NOW))


@pytest.mark.parametrize("field,value", [
    ("expires_timestamp", "2029-01-01T00:00:00Z"),
    ("granted_timestamp", "2026-07-01T00:00:00Z"),
    ("key_id", "another-key"),
    ("approver_id", "mallory"),
])
def test_tampering_with_the_approval_metadata_breaks_the_signature(field: str, value: str) -> None:
    """Pushing back an expiry or swapping a key id must not survive verification."""

    private = _keypair()
    record = _authorization(private, _lock())
    record["human_authorization"][field] = value
    with pytest.raises(CloudManifestError):
        verify_signature(record, _registry(private), now=instant(NOW))


def test_a_recorded_body_digest_is_recomputed_not_trusted() -> None:
    private = _keypair()
    record = _authorization(private, _lock())
    record["human_authorization"]["body_sha256"] = "0" * 64
    with pytest.raises(CloudManifestError, match="does not match the canonical signed body"):
        verify_signature(record, _registry(private), now=instant(NOW))


def test_a_signature_over_a_different_record_does_not_transfer() -> None:
    private = _keypair()
    lock = _lock()
    first = _authorization(private, lock)
    second = _authorization(private, lock, byte_ceiling_bytes=2048)
    # Lift the narrow approval onto the wider record.
    second["human_authorization"] = dict(first["human_authorization"])
    with pytest.raises(CloudManifestError):
        verify_signature(second, _registry(private), now=instant(NOW))


def test_body_digest_helper_agrees_with_the_signed_body() -> None:
    private = _keypair()
    record = _authorization(private, _lock())
    assert authorization_body_digest(record) == record["human_authorization"]["body_sha256"]


# ---------------------------------------------------------------------------
# Ledger row existence and content binding.
# ---------------------------------------------------------------------------


def test_a_missing_ledger_row_is_refused(tmp_path: Path) -> None:
    private = _keypair()
    record = _authorization(private, _lock(), ledger_row_id="CL-999", ledger_row_sha256="3" * 64)
    with pytest.raises(CloudManifestError, match="does not exist"):
        verify_ledger_binding(record, LEDGER)


def test_a_rewritten_ledger_row_is_refused(tmp_path: Path) -> None:
    """The row's content is bound, so approving CL-026 does not approve its successor."""

    private = _keypair()
    record = _authorization(private, _lock())
    assert verify_ledger_binding(record, LEDGER) == _ledger_row_digest()

    rewritten = tmp_path / "ledger.md"
    original = LEDGER.read_text(encoding="utf-8")
    prefix = f"| {BOUND_ROW} |"
    line = next(item for item in original.splitlines() if item.startswith(prefix))
    rewritten.write_text(original.replace(line, line.replace("| 0.00 |", "| 9999.00 |", 1)), encoding="utf-8")
    with pytest.raises(CloudManifestError, match="no longer matches the digest"):
        verify_ledger_binding(record, rewritten)


def test_an_ambiguous_ledger_row_is_refused(tmp_path: Path) -> None:
    private = _keypair()
    record = _authorization(private, _lock())
    duplicated = tmp_path / "ledger.md"
    original = LEDGER.read_text(encoding="utf-8")
    line = next(item for item in original.splitlines() if item.startswith(f"| {BOUND_ROW} |"))
    duplicated.write_text(original + "\n" + line + "\n", encoding="utf-8")
    with pytest.raises(CloudManifestError, match="appears 2 times"):
        verify_ledger_binding(record, duplicated)


def test_a_missing_ledger_file_is_refused(tmp_path: Path) -> None:
    private = _keypair()
    record = _authorization(private, _lock())
    with pytest.raises(CloudManifestError, match="spend ledger is missing"):
        verify_ledger_binding(record, tmp_path / "absent.md")


# ---------------------------------------------------------------------------
# Authentication does not substitute for a real input lock.
# ---------------------------------------------------------------------------


def test_a_valid_signature_over_a_synthetic_lock_still_refuses() -> None:
    """A perfect approval to retrieve placeholders is not authority to retrieve."""

    private = _keypair()
    synthetic = json.loads((FIXTURES / "input-lock-fixture.json").read_text(encoding="utf-8"))
    record = _authorization(private, synthetic, input_lock_sha256=verify_input_lock(synthetic))
    registry = _registry(private)

    # The signature itself is entirely valid...
    assert verify_signature(record, registry, now=instant(NOW))["key_id"] == "approver-primary"
    # ...and the gate still refuses, because the lock is a shape demonstration.
    with pytest.raises(CloudManifestError, match="synthetic demonstration"):
        require_authorized(record, synthetic, key_registry=registry, ledger_path=LEDGER, clock=_clock())
