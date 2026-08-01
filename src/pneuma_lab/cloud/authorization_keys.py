"""Trusted approver keys, Ed25519 verification, and spend-ledger row binding.

This replaces the earlier binding-digest "signature", which was honest about
its own limits but could not answer the question that actually matters: *who*
approved this retrieval. A digest over a record proves the approval names that
record. It does not prove anybody in particular computed it, so anyone able to
write the file could also write its signature.

What the ceremony here establishes, and what it still does not:

**Established.** The signature is Ed25519 over the canonical signed body bytes,
and it verifies against a public key that must be *enumerated in advance* in a
committed registry. An unknown key fails even if its signature is mathematically
valid, so trust comes from the registry rather than from the signature. The key
must be inside its own validity window and not revoked, and the authorization
must not have expired. The referenced spend-ledger row must exist and its exact
line bytes must match the digest the authorization carries, so an approved row
cannot be quietly rewritten afterwards.

**Not established.** Possession of a private key is not proof of a person: a
stolen or coerced key signs perfectly well. There is no hardware binding, no
threshold or multi-party requirement, and no transparency log, so a single
compromised key is a single point of failure. Nothing here proves the approver
understood what they signed. Revocation is only as timely as the committed
registry, so a key compromised after the last commit still verifies until
someone updates the file. These are real limits, and the correct response to
them is a documented key ceremony, not a stronger adjective in this docstring.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from .errors import CloudManifestError
from .manifests import _validate


LEDGER_RELATIVE_PATH = "docs/research/neurips-2026-workshop/32-cloud-spend-ledger.md"

# A zero-argument callable returning the current instant. The execution gate
# resolves time through one of these rather than accepting a timestamp from its
# caller, because a caller-supplied instant is a replay control: an expired
# authorization verifies again the moment someone passes an earlier in-window
# value. Overriding the clock is a **test seam**, never an execution option.
Clock = Callable[[], "datetime"]


def trusted_now() -> datetime:
    """Return the current UTC instant from the system clock.

    This is the only clock the execution path uses. It is trusted in the narrow
    sense that it is not caller-supplied; it is still only as good as host time,
    and a host whose clock is wrong will make wrong validity decisions. Binding
    validity to an external time authority or to a countersigned execution
    receipt would close that gap and is not implemented here.
    """

    return datetime.now(timezone.utc)


def instant(value: str) -> datetime:
    """Parse a UTC timestamp into a comparable instant.

    Timestamps are compared as parsed instants, never as strings. The schema
    permits optional fractional seconds, and lexical ordering gets those wrong
    in both directions because `.` sorts below `Z`: `…T00:00:00.001Z` compares
    as *earlier* than `…T00:00:00Z`. That is not merely untidy — it would let an
    authorization that expired a millisecond ago verify as live.
    """

    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise CloudManifestError(f"malformed UTC timestamp {value!r}") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def canonical_bytes(value: object) -> bytes:
    """Return the canonical JSON encoding used for every digest and signature."""

    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def signed_body(record: Mapping[str, Any]) -> dict[str, Any]:
    """Return the complete body an approver signs.

    Everything in the record except the signature itself, *plus* the approval's
    own non-signature fields. Omitting any of these would let that field be
    changed after signing: a body that excluded `scopes` would let an approval
    for the tokenizer be replayed for every model, and one that excluded
    `expires_timestamp` would let an expiry be pushed back at will.
    """

    approval = record.get("human_authorization") or {}
    body = {key: value for key, value in record.items() if key != "human_authorization"}
    body["approval"] = {
        "approver_id": approval.get("approver_id"),
        "key_id": approval.get("key_id"),
        "granted_timestamp": approval.get("granted_timestamp"),
        "expires_timestamp": approval.get("expires_timestamp"),
    }
    return body


def authorization_body_digest(record: Mapping[str, Any]) -> str:
    """Return the digest of the canonical signed body, recomputed not trusted."""

    return hashlib.sha256(canonical_bytes(signed_body(record))).hexdigest()


def validate_key_registry(record: Mapping[str, Any]) -> dict[str, Any]:
    """Validate the registry and reject internally incoherent key entries."""

    registry = _validate(record, expected_kind="cloud_approver_key_registry")
    seen: set[str] = set()
    for key in registry["keys"]:
        key_id = key["key_id"]
        if key_id in seen:
            raise CloudManifestError(f"duplicate approver key id {key_id!r}")
        seen.add(key_id)
        if instant(key["not_after"]) <= instant(key["not_before"]):
            raise CloudManifestError(f"approver key {key_id!r} has an empty validity window")
        revoked = key["status"] == "revoked"
        if revoked and key["revoked_timestamp"] is None:
            raise CloudManifestError(f"revoked approver key {key_id!r} must record when it was revoked")
        if not revoked and key["revoked_timestamp"] is not None:
            raise CloudManifestError(f"active approver key {key_id!r} must not carry a revocation timestamp")
    return registry


def resolve_trusted_key(registry: Mapping[str, Any], key_id: str, *, now: datetime) -> dict[str, Any]:
    """Return the trusted key, or fail closed on unknown, revoked, or out-of-window.

    `now` is an already-resolved instant. Callers on the execution path obtain
    it from `trusted_now`; only tests substitute one.
    """

    validated = validate_key_registry(registry)
    moment = now
    for key in validated["keys"]:
        if key["key_id"] != key_id:
            continue
        if key["status"] == "revoked":
            reason = key["revocation_reason"] or "no reason recorded"
            raise CloudManifestError(f"approver key {key_id!r} was revoked at {key['revoked_timestamp']} ({reason})")
        if not (instant(key["not_before"]) <= moment <= instant(key["not_after"])):
            raise CloudManifestError(f"approver key {key_id!r} is outside its validity window at {moment.isoformat()}")
        return key
    raise CloudManifestError(f"approver key {key_id!r} is not in the trusted registry; an unenumerated key authorizes nothing")


def verify_signature(record: Mapping[str, Any], registry: Mapping[str, Any], *, now: datetime) -> dict[str, Any]:
    """Verify the Ed25519 approval on an authorization record.

    Returns the resolved trusted key. Raises on any failure; there is no
    partial-credit path, and no branch that treats an unverifiable signature as
    merely weaker evidence.
    """

    approval = record.get("human_authorization")
    if approval is None:
        raise CloudManifestError("record carries no human authorization to verify")

    key = resolve_trusted_key(registry, approval["key_id"], now=now)
    moment = now
    granted = instant(approval["granted_timestamp"])
    expires = instant(approval["expires_timestamp"])
    if approval["approver_id"] != key["approver_id"]:
        raise CloudManifestError(
            f"authorization names approver {approval['approver_id']!r} but key {key['key_id']!r} belongs to {key['approver_id']!r}"
        )
    if expires <= granted:
        raise CloudManifestError("authorization expires no later than it was granted")
    if moment > expires:
        raise CloudManifestError(f"authorization expired at {approval['expires_timestamp']}")
    if moment < granted:
        raise CloudManifestError(f"authorization is not yet valid at {moment.isoformat()}")

    body = canonical_bytes(signed_body(record))
    observed = hashlib.sha256(body).hexdigest()
    if approval["body_sha256"] != observed:
        raise CloudManifestError("recorded body digest does not match the canonical signed body")

    public_key = Ed25519PublicKey.from_public_bytes(bytes.fromhex(key["public_key_hex"]))
    try:
        # Verified over the body bytes, not over the digest: signing a digest
        # would make the signature reusable for any body that hashes to it.
        public_key.verify(bytes.fromhex(approval["signature_ed25519"]), body)
    except InvalidSignature as exc:
        raise CloudManifestError("Ed25519 signature does not verify against the trusted key") from exc
    return key


def ledger_row(ledger_path: Path, row_id: str) -> str:
    """Return the exact ledger row line, or fail closed when it is absent."""

    if not ledger_path.is_file():
        raise CloudManifestError(f"spend ledger is missing: {ledger_path.as_posix()}")
    prefix = f"| {row_id} |"
    matches = [line for line in ledger_path.read_text(encoding="utf-8").splitlines() if line.startswith(prefix)]
    if not matches:
        raise CloudManifestError(f"spend-ledger row {row_id!r} does not exist; an authorization cannot reference an unwritten row")
    if len(matches) > 1:
        raise CloudManifestError(f"spend-ledger row {row_id!r} appears {len(matches)} times; the reference is ambiguous")
    return matches[0]


def verify_ledger_binding(record: Mapping[str, Any], ledger_path: Path) -> str:
    """Verify the referenced ledger row exists and still has its approved content."""

    row_id = record["ledger_row_id"]
    expected = record["ledger_row_sha256"]
    if row_id is None or expected is None:
        raise CloudManifestError("an authorized record must reference a ledger row and bind its content digest")
    line = ledger_row(ledger_path, row_id)
    observed = hashlib.sha256(line.encode("utf-8")).hexdigest()
    if observed != expected:
        raise CloudManifestError(
            f"spend-ledger row {row_id!r} no longer matches the digest this authorization was approved against"
        )
    return observed
