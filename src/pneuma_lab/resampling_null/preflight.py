"""Deterministic, closed imports for resampling-null authority assets."""

from __future__ import annotations

from collections.abc import Collection, Mapping
from dataclasses import dataclass
import errno
import hashlib
import os
from pathlib import Path, PurePosixPath
import stat
from typing import cast
import unicodedata

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from pneuma_lab.foundation.artifacts import canonical_json_bytes

from .errors import RecordValidationError
from .json_io import (
    load_json_bytes as _load_json_bytes,
    plain_json as _plain_json,
    resolve_inside as _resolve_inside,
)
from .types import ArtifactRef


@dataclass(frozen=True, slots=True)
class ClosedJsonImport:
    """One purpose-bound deterministic import grammar."""

    record_kind: str
    fields: frozenset[str]
    exact_integer_fields: frozenset[str] = frozenset()
    semantic_set_fields: frozenset[str] = frozenset()

    def __post_init__(self) -> None:
        if type(self.record_kind) is not str or not self.record_kind:
            raise ValueError("record_kind must be one non-empty exact string")
        if "record_kind" not in self.fields:
            raise ValueError("closed import fields must include record_kind")
        if not self.exact_integer_fields <= self.fields:
            raise ValueError("exact integer fields must belong to the closed grammar")
        if not self.semantic_set_fields <= self.fields:
            raise ValueError("semantic-set fields must belong to the closed grammar")


class ConfirmationPreflightUnavailable(RecordValidationError):
    """Raised while no reviewed live ceremony adapter is installed."""


DRAND_MAINNET_CHAIN_HASH = "8990e7a9aaed2ffed73dbd7092123d6f289930540d7651336225dc172e51b2ce"
_CEREMONY_CAPABILITY_TOKEN = object()


class ConfirmationRosterCeremonyCapability:
    """Opaque capability minted only after the receipt contract verifies."""

    __slots__ = ("_source_sha256s", "_receipt_sha256")

    def __new__(
        cls,
        token: object | None = None,
        source_sha256s: tuple[str, str, str, str, str, str, str] | None = None,
        receipt_sha256: str | None = None,
    ) -> ConfirmationRosterCeremonyCapability:
        if token is not _CEREMONY_CAPABILITY_TOKEN or source_sha256s is None or receipt_sha256 is None:
            raise TypeError(
                "ceremony capabilities have no public constructor; "
                "the reviewed live adapter must mint them"
            )
        instance = cast(ConfirmationRosterCeremonyCapability, object.__new__(cls))
        instance._source_sha256s = source_sha256s
        instance._receipt_sha256 = receipt_sha256
        return instance

    def __init_subclass__(cls, **kwargs: object) -> None:
        del cls, kwargs
        raise TypeError("ceremony capabilities cannot be subclassed")

    @property
    def source_sha256s(self) -> tuple[str, str, str, str, str, str, str]:
        return self._source_sha256s

    @property
    def receipt_sha256(self) -> str:
        return self._receipt_sha256


class ConfirmationPreflightRegistry:
    """Verify externally produced Sigstore/drand/Node ceremony evidence.

    The registry never contacts a service and never selects a roster.  The
    separate live ceremony runner must provide the exact source bytes and a
    receipt signed by the public key declared by the manifest-owned policy.
    """

    __slots__ = ()

    def __init_subclass__(cls, **kwargs: object) -> None:
        del cls, kwargs
        raise TypeError("the core preflight registry cannot be subclassed")

    def claim_roster_ceremony(
        self,
        *,
        qualification_universe_source: Path,
        selection_program_source: Path,
        precommit_source: Path,
        anchor_source: Path,
        reveal_source: Path,
        eligibility_source: Path,
        ceremony_policy_source: Path,
        study_id: str,
        ceremony_receipt_source: Path | None = None,
    ) -> ConfirmationRosterCeremonyCapability:
        if ceremony_receipt_source is None:
            raise ConfirmationPreflightUnavailable(
                "eligible confirmation is unavailable: no reviewed official "
                "Sigstore/drand/Node live receipt was supplied"
            )
        if type(study_id) is not str or not study_id:
            raise RecordValidationError("ceremony study_id must be non-empty exact text")
        source_paths = (
            qualification_universe_source,
            selection_program_source,
            precommit_source,
            anchor_source,
            reveal_source,
            eligibility_source,
            ceremony_policy_source,
        )
        source_raw = tuple(
            _read_ceremony_source(path, field=f"ceremony source[{index}]")
            for index, path in enumerate(source_paths)
        )
        source_sha256s = tuple(
            hashlib.sha256(raw).hexdigest() for raw in source_raw
        )
        policy = _load_canonical_ceremony_object(
            source_raw[6], source=ceremony_policy_source, field="ceremony policy"
        )
        policy_fields = {
            "record_kind", "schema_version", "study_id", "qualification_universe_sha256",
            "selection_program_sha256", "precommit_sha256", "drand", "sigstore", "node",
            "public_key_ed25519_hex",
        }
        policy = _closed_mapping(policy, fields=policy_fields, path="ceremony policy")
        if policy["record_kind"] != "resampling_roster_ceremony_policy_v1" or policy["schema_version"] != "1" or policy["study_id"] != study_id:
            raise RecordValidationError("ceremony policy has wrong identity or study_id")
        for field, expected in (
            ("qualification_universe_sha256", source_sha256s[0]),
            ("selection_program_sha256", source_sha256s[1]),
            ("precommit_sha256", source_sha256s[2]),
        ):
            if policy[field] != expected:
                raise RecordValidationError(f"ceremony policy {field} does not bind source bytes")
            _sha256(policy[field], path=f"ceremony policy.{field}")
        drand = _closed_mapping(
            policy["drand"],
            fields={"chain_hash", "scheme", "client_version", "group_hash", "genesis_time", "period"},
            path="ceremony policy.drand",
        )
        if drand["chain_hash"] != DRAND_MAINNET_CHAIN_HASH or drand["scheme"] != "pedersen-bls-chained" or drand["client_version"] != "drand-client==1.4.2":
            raise RecordValidationError("ceremony policy drand contract differs from the registered mainnet contract")
        _sha256(drand["group_hash"], path="ceremony policy.drand.group_hash")
        if type(drand["genesis_time"]) is not int or type(drand["period"]) is not int or drand["genesis_time"] < 0 or drand["period"] <= 0:
            raise RecordValidationError("ceremony policy drand timing is invalid")
        sigstore = _closed_mapping(
            policy["sigstore"],
            fields={"contract_id", "verifier_source_sha256", "required_rekor_log", "bundle_format"},
            path="ceremony policy.sigstore",
        )
        if sigstore != {
            "contract_id": "sigstore-bundle-verification-v1",
            "verifier_source_sha256": sigstore["verifier_source_sha256"],
            "required_rekor_log": "rekor-public-good",
            "bundle_format": "sigstore-bundle-v0.3",
        }:
            raise RecordValidationError("ceremony policy Sigstore contract is not registered")
        _sha256(sigstore["verifier_source_sha256"], path="ceremony policy.sigstore.verifier_source_sha256")
        node = _closed_mapping(
            policy["node"],
            fields={"contract_id", "program_sha256", "runtime", "output_schema"},
            path="ceremony policy.node",
        )
        if node["contract_id"] != "node-roster-selection-v1" or node["runtime"] != "nodejs-22" or node["output_schema"] != "resampling-eligibility-manifest-v1":
            raise RecordValidationError("ceremony policy Node contract is not registered")
        _sha256(node["program_sha256"], path="ceremony policy.node.program_sha256")
        public_key = policy["public_key_ed25519_hex"]
        _lower_hex(public_key, field="ceremony policy.public_key_ed25519_hex", byte_count=32)

        receipt_raw = _read_ceremony_source(ceremony_receipt_source, field="ceremony receipt")
        receipt = _load_canonical_ceremony_object(receipt_raw, source=ceremony_receipt_source, field="ceremony receipt")
        receipt_fields = {
            "record_kind", "schema_version", "study_id", "qualification_universe_sha256",
            "selection_program_sha256", "precommit_sha256", "anchor_sha256", "reveal_sha256",
            "eligibility_manifest_sha256", "ceremony_policy_sha256", "sigstore", "drand", "node",
            "signature_ed25519_hex",
        }
        receipt = _closed_mapping(receipt, fields=receipt_fields, path="ceremony receipt")
        if receipt["record_kind"] != "resampling_roster_ceremony_receipt_v1" or receipt["schema_version"] != "1" or receipt["study_id"] != study_id:
            raise RecordValidationError("ceremony receipt has wrong identity or study_id")
        expected_bindings = {
            "qualification_universe_sha256": source_sha256s[0],
            "selection_program_sha256": source_sha256s[1],
            "precommit_sha256": source_sha256s[2],
            "anchor_sha256": source_sha256s[3],
            "reveal_sha256": source_sha256s[4],
            "eligibility_manifest_sha256": source_sha256s[5],
            "ceremony_policy_sha256": source_sha256s[6],
        }
        for field, expected in expected_bindings.items():
            if receipt[field] != expected:
                raise RecordValidationError(f"ceremony receipt {field} does not bind exact source bytes")
            _sha256(receipt[field], path=f"ceremony receipt.{field}")
        verify_ed25519_canonical_json(
            receipt,
            public_key_ed25519_hex=cast(str, public_key),
            signature_ed25519_hex=cast(str, receipt["signature_ed25519_hex"]),
            signature_field="signature_ed25519_hex",
        )
        receipt_sigstore = _closed_mapping(
            receipt["sigstore"],
            fields={"verified", "bundle_sha256", "rekor_entry_sha256", "artifact_sha256", "verifier_source_sha256"},
            path="ceremony receipt.sigstore",
        )
        if receipt_sigstore["verified"] is not True or receipt_sigstore["verifier_source_sha256"] != sigstore["verifier_source_sha256"]:
            raise RecordValidationError("ceremony receipt Sigstore verification is not bound to policy")
        for field in ("bundle_sha256", "rekor_entry_sha256", "artifact_sha256", "verifier_source_sha256"):
            _sha256(receipt_sigstore[field], path=f"ceremony receipt.sigstore.{field}")
        receipt_drand = _closed_mapping(
            receipt["drand"],
            fields={"verified", "chain_hash", "round", "randomness_hex", "randomness_sha256", "proof_sha256"},
            path="ceremony receipt.drand",
        )
        if receipt_drand["verified"] is not True or receipt_drand["chain_hash"] != drand["chain_hash"]:
            raise RecordValidationError("ceremony receipt drand proof is not bound to the registered chain")
        _nonnegative_int(receipt_drand["round"], path="ceremony receipt.drand.round")
        randomness = _lower_hex(receipt_drand["randomness_hex"], field="ceremony receipt.drand.randomness_hex", byte_count=32)
        if hashlib.sha256(randomness).hexdigest() != receipt_drand["randomness_sha256"]:
            raise RecordValidationError("ceremony receipt drand randomness digest differs")
        _sha256(receipt_drand["randomness_sha256"], path="ceremony receipt.drand.randomness_sha256")
        _sha256(receipt_drand["proof_sha256"], path="ceremony receipt.drand.proof_sha256")
        receipt_node = _closed_mapping(
            receipt["node"],
            fields={"verified", "program_sha256", "output_sha256"},
            path="ceremony receipt.node",
        )
        if receipt_node["verified"] is not True or receipt_node["program_sha256"] != node["program_sha256"] or receipt_node["output_sha256"] != source_sha256s[5]:
            raise RecordValidationError("ceremony receipt Node output is not bound to policy and eligibility")
        _sha256(receipt_node["program_sha256"], path="ceremony receipt.node.program_sha256")
        _sha256(receipt_node["output_sha256"], path="ceremony receipt.node.output_sha256")

        eligibility = _load_canonical_ceremony_object(
            source_raw[5], source=eligibility_source, field="eligibility manifest"
        )
        if eligibility.get("record_kind") != "resampling_eligibility_manifest_v1" or eligibility.get("schema_version") != "1" or eligibility.get("study_id") != study_id:
            raise RecordValidationError("ceremony receipt rejects non-live or synthetic eligibility authority")
        beacon = eligibility.get("beacon_receipt")
        if not isinstance(beacon, Mapping) or beacon.get("chain_hash") != DRAND_MAINNET_CHAIN_HASH or beacon.get("randomness_hex") != receipt_drand["randomness_hex"]:
            raise RecordValidationError("eligibility beacon does not match the verified drand receipt")
        if eligibility.get("precommit_sha256") != receipt["precommit_sha256"]:
            raise RecordValidationError("eligibility precommit does not match the verified ceremony receipt")
        return ConfirmationRosterCeremonyCapability(
            _CEREMONY_CAPABILITY_TOKEN,
            cast(tuple[str, str, str, str, str, str, str], source_sha256s),
            hashlib.sha256(receipt_raw).hexdigest(),
        )

    def claim_roster_ceremony_from_manifest(
        self,
        *,
        eligibility_source: Path,
        ceremony_policy_source: Path,
        ceremony_receipt_source: Path,
        study_id: str,
    ) -> ConfirmationRosterCeremonyCapability:
        """Verify the manifest-owned compact bundle at the authority boundary.

        The full ceremony adapter above accepts the seven independently
        archived upstream source files.  A sealed study manifest may retain
        only the compact policy, eligibility output, and signed verification
        receipt; this method verifies that compact bundle without inventing or
        re-fetching the omitted source bytes.
        """

        eligibility_raw = _read_ceremony_source(eligibility_source, field="eligibility manifest")
        policy_raw = _read_ceremony_source(ceremony_policy_source, field="ceremony policy")
        receipt_raw = _read_ceremony_source(ceremony_receipt_source, field="ceremony receipt")
        eligibility = _load_canonical_ceremony_object(eligibility_raw, source=eligibility_source, field="eligibility manifest")
        policy = _load_canonical_ceremony_object(policy_raw, source=ceremony_policy_source, field="ceremony policy")
        receipt = _load_canonical_ceremony_object(receipt_raw, source=ceremony_receipt_source, field="ceremony receipt")
        if eligibility.get("record_kind") != "resampling_eligibility_manifest_v1" or eligibility.get("schema_version") != "1" or eligibility.get("study_id") != study_id:
            raise RecordValidationError("manifest ceremony bundle rejects synthetic or IV eligibility")
        if policy.get("record_kind") != "resampling_roster_ceremony_policy_v1" or policy.get("schema_version") != "1" or policy.get("study_id") != study_id:
            raise RecordValidationError("manifest ceremony policy has wrong identity")
        if receipt.get("record_kind") != "resampling_roster_ceremony_receipt_v1" or receipt.get("schema_version") != "1" or receipt.get("study_id") != study_id:
            raise RecordValidationError("manifest ceremony receipt has wrong identity")
        policy_map = _closed_mapping(
            policy,
            fields={"record_kind", "schema_version", "study_id", "qualification_universe_sha256", "selection_program_sha256", "precommit_sha256", "drand", "sigstore", "node", "public_key_ed25519_hex"},
            path="ceremony policy",
        )
        receipt_map = _closed_mapping(
            receipt,
            fields={"record_kind", "schema_version", "study_id", "qualification_universe_sha256", "selection_program_sha256", "precommit_sha256", "anchor_sha256", "reveal_sha256", "eligibility_manifest_sha256", "ceremony_policy_sha256", "sigstore", "drand", "node", "signature_ed25519_hex"},
            path="ceremony receipt",
        )
        policy_digest = hashlib.sha256(policy_raw).hexdigest()
        eligibility_digest = hashlib.sha256(eligibility_raw).hexdigest()
        if receipt_map["eligibility_manifest_sha256"] != eligibility_digest or receipt_map["ceremony_policy_sha256"] != policy_digest:
            raise RecordValidationError("manifest ceremony receipt does not bind manifest-owned bytes")
        for field in ("qualification_universe_sha256", "selection_program_sha256", "precommit_sha256"):
            if receipt_map[field] != policy_map[field]:
                raise RecordValidationError(f"manifest ceremony {field} differs between policy and receipt")
            _sha256(policy_map[field], path=f"ceremony policy.{field}")
        drand = _closed_mapping(policy_map["drand"], fields={"chain_hash", "scheme", "client_version", "group_hash", "genesis_time", "period"}, path="ceremony policy.drand")
        if drand["chain_hash"] != DRAND_MAINNET_CHAIN_HASH or drand["scheme"] != "pedersen-bls-chained" or drand["client_version"] != "drand-client==1.4.2":
            raise RecordValidationError("manifest ceremony drand policy is not the registered mainnet contract")
        _sha256(drand["group_hash"], path="ceremony policy.drand.group_hash")
        sigstore = _closed_mapping(policy_map["sigstore"], fields={"contract_id", "verifier_source_sha256", "required_rekor_log", "bundle_format"}, path="ceremony policy.sigstore")
        if sigstore["contract_id"] != "sigstore-bundle-verification-v1" or sigstore["required_rekor_log"] != "rekor-public-good" or sigstore["bundle_format"] != "sigstore-bundle-v0.3":
            raise RecordValidationError("manifest ceremony Sigstore policy is not registered")
        node = _closed_mapping(policy_map["node"], fields={"contract_id", "program_sha256", "runtime", "output_schema"}, path="ceremony policy.node")
        if node["contract_id"] != "node-roster-selection-v1" or node["runtime"] != "nodejs-22" or node["output_schema"] != "resampling-eligibility-manifest-v1":
            raise RecordValidationError("manifest ceremony Node policy is not registered")
        _lower_hex(policy_map["public_key_ed25519_hex"], field="ceremony policy.public_key_ed25519_hex", byte_count=32)
        verify_ed25519_canonical_json(
            receipt_map,
            public_key_ed25519_hex=cast(str, policy_map["public_key_ed25519_hex"]),
            signature_ed25519_hex=cast(str, receipt_map["signature_ed25519_hex"]),
            signature_field="signature_ed25519_hex",
        )
        receipt_sigstore = _closed_mapping(receipt_map["sigstore"], fields={"verified", "bundle_sha256", "rekor_entry_sha256", "artifact_sha256", "verifier_source_sha256"}, path="ceremony receipt.sigstore")
        if receipt_sigstore["verified"] is not True or receipt_sigstore["verifier_source_sha256"] != sigstore["verifier_source_sha256"]:
            raise RecordValidationError("manifest ceremony Sigstore receipt is not verified under policy")
        for field in ("bundle_sha256", "rekor_entry_sha256", "artifact_sha256", "verifier_source_sha256"):
            _sha256(receipt_sigstore[field], path=f"ceremony receipt.sigstore.{field}")
        receipt_drand = _closed_mapping(receipt_map["drand"], fields={"verified", "chain_hash", "round", "randomness_hex", "randomness_sha256", "proof_sha256"}, path="ceremony receipt.drand")
        if receipt_drand["verified"] is not True or receipt_drand["chain_hash"] != DRAND_MAINNET_CHAIN_HASH:
            raise RecordValidationError("manifest ceremony drand receipt is not verified under policy")
        randomness = _lower_hex(receipt_drand["randomness_hex"], field="ceremony receipt.drand.randomness_hex", byte_count=32)
        if hashlib.sha256(randomness).hexdigest() != receipt_drand["randomness_sha256"]:
            raise RecordValidationError("manifest ceremony drand randomness digest differs")
        _nonnegative_int(receipt_drand["round"], path="ceremony receipt.drand.round")
        for field in ("randomness_sha256", "proof_sha256"):
            _sha256(receipt_drand[field], path=f"ceremony receipt.drand.{field}")
        receipt_node = _closed_mapping(receipt_map["node"], fields={"verified", "program_sha256", "output_sha256"}, path="ceremony receipt.node")
        if receipt_node["verified"] is not True or receipt_node["program_sha256"] != node["program_sha256"] or receipt_node["output_sha256"] != eligibility_digest:
            raise RecordValidationError("manifest ceremony Node receipt is not bound to the eligibility output")
        _sha256(receipt_node["program_sha256"], path="ceremony receipt.node.program_sha256")
        _sha256(receipt_node["output_sha256"], path="ceremony receipt.node.output_sha256")
        beacon = eligibility.get("beacon_receipt")
        if not isinstance(beacon, Mapping) or beacon.get("chain_hash") != DRAND_MAINNET_CHAIN_HASH or beacon.get("randomness_hex") != receipt_drand["randomness_hex"]:
            raise RecordValidationError("manifest eligibility beacon differs from verified drand")
        if eligibility.get("precommit_sha256") != receipt_map["precommit_sha256"]:
            raise RecordValidationError("manifest eligibility precommit differs from ceremony receipt")
        source_sha256s = (
            cast(str, policy_map["qualification_universe_sha256"]),
            cast(str, policy_map["selection_program_sha256"]),
            cast(str, policy_map["precommit_sha256"]),
            cast(str, receipt_map["anchor_sha256"]),
            cast(str, receipt_map["reveal_sha256"]),
            eligibility_digest,
            policy_digest,
        )
        return ConfirmationRosterCeremonyCapability(
            _CEREMONY_CAPABILITY_TOKEN,
            source_sha256s,
            hashlib.sha256(receipt_raw).hexdigest(),
        )


def _read_ceremony_source(path: Path, *, field: str) -> bytes:
    if not isinstance(path, Path):
        raise RecordValidationError(f"{field} must be a pathlib.Path")
    try:
        if path.is_symlink() or not path.is_file():
            raise RecordValidationError(f"{field} must be one regular non-symlink file")
        raw = path.read_bytes()
    except OSError as exc:
        raise RecordValidationError(f"cannot read {field}") from exc
    if not raw:
        raise RecordValidationError(f"{field} must not be empty")
    return raw


def _load_canonical_ceremony_object(
    raw: bytes, *, source: Path, field: str
) -> Mapping[str, object]:
    value = _load_json_bytes(raw, source=source)
    if not isinstance(value, Mapping) or canonical_json_bytes(value, indent=None) != raw:
        raise RecordValidationError(f"{field} must be one compact canonical JSON object")
    _require_canonical_text(value)
    return cast(Mapping[str, object], value)


def _lower_hex(value: object, *, field: str, byte_count: int) -> bytes:
    if type(value) is not str:
        raise RecordValidationError(f"{field} must be exact lowercase hex text")
    text = cast(str, value)
    if len(text) != byte_count * 2 or any(
        character not in "0123456789abcdef" for character in text
    ):
        raise RecordValidationError(
            f"{field} must encode exactly {byte_count} bytes as lowercase hex"
        )
    return bytes.fromhex(text)


def verify_ed25519_canonical_json(
    value: Mapping[str, object],
    *,
    public_key_ed25519_hex: str,
    signature_ed25519_hex: str,
    signature_field: str | None = None,
) -> str:
    """Verify Ed25519 over exact compact canonical JSON and return its digest."""

    if not isinstance(value, Mapping):
        raise RecordValidationError("signed value must be a mapping")
    plain = _plain_json(value)
    if not isinstance(plain, dict):
        raise RecordValidationError("signed value must be a plain JSON object")
    if signature_field is not None:
        if type(signature_field) is not str or not signature_field:
            raise RecordValidationError("signature_field must be non-empty text")
        if plain.get(signature_field) != signature_ed25519_hex:
            raise RecordValidationError(
                "embedded signature differs from verification signature"
            )
        del plain[signature_field]
    _require_canonical_text(plain)
    payload = canonical_json_bytes(plain, indent=None)
    public_key = _lower_hex(
        public_key_ed25519_hex,
        field="public_key_ed25519_hex",
        byte_count=32,
    )
    signature = _lower_hex(
        signature_ed25519_hex,
        field="signature_ed25519_hex",
        byte_count=64,
    )
    try:
        Ed25519PublicKey.from_public_bytes(public_key).verify(signature, payload)
    except (InvalidSignature, ValueError) as exc:
        raise RecordValidationError("Ed25519 signature verification failed") from exc
    return hashlib.sha256(payload).hexdigest()


def _require_canonical_text(value: object, *, path: str = "$") -> None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            _require_canonical_text(key, path=f"{path}.<key>")
            _require_canonical_text(nested, path=f"{path}.{key}")
        return
    if isinstance(value, list):
        for index, nested in enumerate(value):
            _require_canonical_text(nested, path=f"{path}[{index}]")
        return
    if not isinstance(value, str):
        return
    if unicodedata.normalize("NFC", value) != value:
        raise RecordValidationError(f"{path}: text must already be NFC-normalized")
    forbidden = next(
        (
            character
            for character in value
            if unicodedata.category(character).startswith("C")
        ),
        None,
    )
    if forbidden is not None:
        raise RecordValidationError(f"{path}: text contains a forbidden code point")


def _normalize_semantic_set(value: object, *, field: str) -> list[object]:
    if not isinstance(value, list):
        raise RecordValidationError(f"{field} must be an array")
    keyed: list[tuple[bytes, object]] = []
    observed: set[bytes] = set()
    for item in value:
        canonical = canonical_json_bytes(item, indent=None)
        if canonical in observed:
            raise RecordValidationError(f"{field} must not contain duplicates")
        observed.add(canonical)
        keyed.append((canonical, item))
    return [item for _canonical, item in sorted(keyed, key=lambda pair: pair[0])]


def _publish_cas(target: Path, payload: bytes) -> None:
    """Install once without replacing an existing pathname."""

    directory_flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    directory_flags |= getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    directory_descriptor = os.open(target.parent, directory_flags)
    directory_metadata = os.fstat(directory_descriptor)
    try:
        rebound_directory = target.parent.stat()
    except BaseException:
        os.close(directory_descriptor)
        raise
    if (rebound_directory.st_dev, rebound_directory.st_ino) != (
        directory_metadata.st_dev,
        directory_metadata.st_ino,
    ):
        os.close(directory_descriptor)
        raise RecordValidationError("import destination directory changed")

    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    flags |= getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(
            target.name,
            flags,
            0o644,
            dir_fd=directory_descriptor,
        )
    except OSError as exc:
        if exc.errno != errno.EEXIST:
            os.close(directory_descriptor)
            raise
        read_flags = os.O_RDONLY
        read_flags |= getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
        try:
            descriptor = os.open(
                target.name,
                read_flags,
                dir_fd=directory_descriptor,
            )
        except OSError as read_exc:
            os.close(directory_descriptor)
            raise RecordValidationError(
                "cannot bind existing digest-derived import"
            ) from read_exc
        try:
            metadata = os.fstat(descriptor)
            if (
                not stat.S_ISREG(metadata.st_mode)
                or getattr(metadata, "st_nlink", 1) != 1
            ):
                raise RecordValidationError(
                    "existing digest-derived import is not one regular file"
                )
            observed = bytearray()
            while chunk := os.read(descriptor, 1024 * 1024):
                observed.extend(chunk)
            if bytes(observed) != payload:
                raise RecordValidationError(
                    "digest-derived import path contains other bytes"
                )
            rebound = os.stat(
                target.name,
                dir_fd=directory_descriptor,
                follow_symlinks=False,
            )
            if (rebound.st_dev, rebound.st_ino) != (
                metadata.st_dev,
                metadata.st_ino,
            ):
                raise RecordValidationError(
                    "digest-derived import pathname changed while reading"
                )
            rebound_directory = target.parent.stat()
            if (rebound_directory.st_dev, rebound_directory.st_ino) != (
                directory_metadata.st_dev,
                directory_metadata.st_ino,
            ):
                raise RecordValidationError("import destination directory changed")
        finally:
            os.close(descriptor)
            os.close(directory_descriptor)
        return

    try:
        view = memoryview(payload)
        written = 0
        while written < len(view):
            written += os.write(descriptor, view[written:])
        os.fsync(descriptor)
        metadata = os.fstat(descriptor)
        rebound = os.stat(
            target.name,
            dir_fd=directory_descriptor,
            follow_symlinks=False,
        )
        if (rebound.st_dev, rebound.st_ino) != (metadata.st_dev, metadata.st_ino):
            raise RecordValidationError(
                "digest-derived import pathname changed while publishing"
            )
        rebound_directory = target.parent.stat()
        if (rebound_directory.st_dev, rebound_directory.st_ino) != (
            directory_metadata.st_dev,
            directory_metadata.st_ino,
        ):
            raise RecordValidationError("import destination directory changed")
        os.fsync(directory_descriptor)
    except BaseException:
        try:
            rebound = os.stat(
                target.name,
                dir_fd=directory_descriptor,
                follow_symlinks=False,
            )
            metadata = os.fstat(descriptor)
            if (rebound.st_dev, rebound.st_ino) == (
                metadata.st_dev,
                metadata.st_ino,
            ):
                os.unlink(target.name, dir_fd=directory_descriptor)
        except OSError:
            pass
        raise
    finally:
        os.close(descriptor)
        os.close(directory_descriptor)


def _publish_closed_value(
    decoded: object,
    *,
    grammar: ClosedJsonImport,
    run_root: Path,
    destination_template: str,
    role: str,
) -> ArtifactRef:
    if destination_template.count("{sha256}") > 1:
        raise ValueError("destination_template contains repeated {sha256}")
    if not isinstance(decoded, Mapping):
        raise RecordValidationError("closed import must be one JSON object")
    value = dict(cast(Mapping[str, object], decoded))
    observed_fields = frozenset(value)
    if observed_fields != grammar.fields:
        missing = sorted(grammar.fields - observed_fields)
        unknown = sorted(observed_fields - grammar.fields)
        raise RecordValidationError(
            f"closed import fields differ: missing={missing}, unknown={unknown}"
        )
    if value["record_kind"] != grammar.record_kind:
        raise RecordValidationError(
            f"record_kind must equal {grammar.record_kind!r}"
        )
    for field in grammar.exact_integer_fields:
        if type(value[field]) is not int:
            raise RecordValidationError(f"{field} must be an exact integer")
    _require_canonical_text(value)
    for field in grammar.semantic_set_fields:
        value[field] = _normalize_semantic_set(value[field], field=field)

    payload = canonical_json_bytes(value, indent=2)
    digest = hashlib.sha256(payload).hexdigest()
    try:
        relative_path = destination_template.format(sha256=digest)
    except (IndexError, KeyError, ValueError) as exc:
        raise ValueError("destination_template contains another format field") from exc
    if PurePosixPath(relative_path).as_posix() != relative_path:
        raise RecordValidationError("destination path must be canonical POSIX text")
    target, rebound = _resolve_inside(
        Path(relative_path),
        run_root,
        require_exists=False,
    )
    if rebound != relative_path:
        raise RecordValidationError("destination path changed during resolution")
    target.parent.mkdir(parents=True, exist_ok=True)
    rebound_target, rebound_relative = _resolve_inside(
        target,
        run_root,
        require_exists=False,
    )
    if rebound_target != target or rebound_relative != relative_path:
        raise RecordValidationError("destination ancestry changed before import")
    _publish_cas(target, payload)
    return ArtifactRef(
        role=role,
        relative_path=relative_path,
        sha256=digest,
        byte_count=len(payload),
        media_type="application/json",
    )


def import_closed_json(
    source: Path,
    *,
    grammar: ClosedJsonImport,
    run_root: Path,
    destination_template: str,
    role: str,
) -> ArtifactRef:
    """Validate and copy one closed JSON object to a deterministic path.

    ``destination_template`` may be fixed or contain one ``{sha256}`` token.
    A byte-identical existing object is accepted; every mismatch fails closed.
    """

    try:
        source_bytes = Path(source).read_bytes()
    except OSError as exc:
        raise RecordValidationError(f"cannot read import source {source}: {exc}") from exc
    decoded = _load_json_bytes(source_bytes, source=Path(source))
    return _publish_closed_value(
        decoded,
        grammar=grammar,
        run_root=run_root,
        destination_template=destination_template,
        role=role,
    )


def require_declared_fields(
    fields: Collection[str],
    *,
    required: Collection[str],
) -> None:
    """Reject programmatic grammars that silently omit required authority."""

    if frozenset(fields) != frozenset(required):
        raise ValueError("declared import grammar differs from required authority")


_GROUP_ORDER = {"language": 0, "domain": 1, "issue_family": 2}
TASK_REGISTRY_GRAMMAR = ClosedJsonImport(
    record_kind="resampling_task_registry_v1",
    fields=frozenset({"record_kind", "schema_version", "tasks"}),
)
ASSIGNMENT_PROGRAM_GRAMMAR = ClosedJsonImport(
    record_kind="resampling_assignment_program_v1",
    fields=frozenset(
        {
            "record_kind",
            "schema_version",
            "assignment_mode",
            "matching_algorithm",
            "finding_count_band_upper_bounds",
            "report_length_band_upper_bounds",
            "verifier_normalizer_contract",
            "assignment_runtime_contract",
            "backend_receipt_ref",
            "stratum_keys",
        }
    ),
)


def _closed_mapping(
    value: object,
    *,
    fields: Collection[str],
    path: str,
) -> dict[str, object]:
    if not isinstance(value, Mapping):
        raise RecordValidationError(f"{path} must be an object")
    result = dict(cast(Mapping[str, object], value))
    observed = frozenset(result)
    expected = frozenset(fields)
    if observed != expected:
        raise RecordValidationError(
            f"{path} fields differ: "
            f"missing={sorted(expected - observed)}, "
            f"unknown={sorted(observed - expected)}"
        )
    return result


def _strict_text(value: object, *, path: str) -> str:
    if type(value) is not str or not value:
        raise RecordValidationError(f"{path} must be non-empty exact text")
    _require_canonical_text(value, path=path)
    return cast(str, value)


def _nonnegative_int(value: object, *, path: str) -> int:
    if type(value) is not int or cast(int, value) < 0:
        raise RecordValidationError(f"{path} must be an exact non-negative integer")
    return cast(int, value)


def _sha256(value: object, *, path: str) -> str:
    text = _strict_text(value, path=path)
    if len(text) != 64 or any(character not in "0123456789abcdef" for character in text):
        raise RecordValidationError(f"{path} must be lowercase SHA-256")
    return text


def _artifact_ref_value(value: object, *, path: str) -> ArtifactRef:
    mapping = _closed_mapping(
        value,
        fields={"role", "relative_path", "sha256", "byte_count", "media_type"},
        path=path,
    )
    try:
        return ArtifactRef(
            role=cast(str, mapping["role"]),
            relative_path=cast(str, mapping["relative_path"]),
            sha256=cast(str, mapping["sha256"]),
            byte_count=cast(int, mapping["byte_count"]),
            media_type=cast(str, mapping["media_type"]),
        )
    except (TypeError, ValueError) as exc:
        raise RecordValidationError(f"{path} is malformed: {exc}") from exc


def _validate_task_registry(value: dict[str, object]) -> None:
    if value["schema_version"] != "1":
        raise RecordValidationError("task registry schema_version must equal '1'")
    tasks = value["tasks"]
    if not isinstance(tasks, list) or not tasks:
        raise RecordValidationError("task registry tasks must be a non-empty array")
    normalized_tasks: list[
        tuple[tuple[bytes, bytes, bytes, bytes], dict[str, object]]
    ] = []
    task_ids: set[str] = set()
    for index, item in enumerate(tasks):
        task = _closed_mapping(
            item,
            fields={"task_id", "benchmark", "stratum", "lineage", "groups"},
            path=f"tasks[{index}]",
        )
        texts = {
            field: _strict_text(task[field], path=f"tasks[{index}].{field}")
            for field in ("task_id", "benchmark", "stratum", "lineage")
        }
        if texts["task_id"] in task_ids:
            raise RecordValidationError("task registry task_id values must be unique")
        task_ids.add(texts["task_id"])
        groups = task["groups"]
        if not isinstance(groups, list) or not groups:
            raise RecordValidationError(f"tasks[{index}].groups must be non-empty")
        normalized_groups: list[tuple[tuple[int, bytes], dict[str, object]]] = []
        group_kinds: set[str] = set()
        for group_index, group_value in enumerate(groups):
            group = _closed_mapping(
                group_value,
                fields={"kind", "value"},
                path=f"tasks[{index}].groups[{group_index}]",
            )
            kind = _strict_text(
                group["kind"],
                path=f"tasks[{index}].groups[{group_index}].kind",
            )
            label = _strict_text(
                group["value"],
                path=f"tasks[{index}].groups[{group_index}].value",
            )
            if kind not in _GROUP_ORDER or kind in group_kinds:
                raise RecordValidationError(
                    f"tasks[{index}].groups has invalid or repeated kind"
                )
            group_kinds.add(kind)
            normalized_groups.append(
                ((_GROUP_ORDER[kind], label.encode("utf-8")), group)
            )
        task["groups"] = [
            group for _key, group in sorted(normalized_groups, key=lambda row: row[0])
        ]
        normalized_tasks.append(
            (
                (
                texts["benchmark"].encode("utf-8"),
                texts["stratum"].encode("utf-8"),
                texts["lineage"].encode("utf-8"),
                texts["task_id"].encode("utf-8"),
                ),
                task,
            )
        )
    value["tasks"] = [
        task for _key, task in sorted(normalized_tasks, key=lambda row: row[0])
    ]


def import_task_registry(
    source: Path,
    *,
    run_root: Path,
    destination: str = "inputs/task-registry.json",
) -> ArtifactRef:
    """Import the concrete closed task-registry authority."""

    try:
        source_bytes = Path(source).read_bytes()
    except OSError as exc:
        raise RecordValidationError(f"cannot read task registry {source}: {exc}") from exc
    decoded = _load_json_bytes(source_bytes, source=Path(source))
    value = _closed_mapping(
        decoded,
        fields=TASK_REGISTRY_GRAMMAR.fields,
        path="$",
    )
    if value.get("record_kind") != TASK_REGISTRY_GRAMMAR.record_kind:
        raise RecordValidationError("wrong task-registry record_kind")
    _require_canonical_text(value)
    _validate_task_registry(value)
    return _publish_closed_value(
        value,
        grammar=TASK_REGISTRY_GRAMMAR,
        run_root=run_root,
        destination_template=destination,
        role="task_registry",
    )


def _strict_cutpoints(value: object, *, path: str) -> None:
    if not isinstance(value, list):
        raise RecordValidationError(f"{path} must be an array")
    points = [
        _nonnegative_int(item, path=f"{path}[{index}]")
        for index, item in enumerate(value)
    ]
    if points != sorted(set(points)):
        raise RecordValidationError(f"{path} must be strictly increasing")


def _validate_assignment_program(value: dict[str, object]) -> None:
    if value["schema_version"] != "1":
        raise RecordValidationError("assignment program schema_version must equal '1'")
    mode = value["assignment_mode"]
    algorithm = value["matching_algorithm"]
    if (mode, algorithm) not in {
        ("synthetic_derangement", "synthetic_cyclic_offset_v1"),
        ("confirmation_lineage_matching", "exact_constrained_min_cost_v1"),
    }:
        raise RecordValidationError("assignment mode/algorithm pair is not closed")
    _strict_cutpoints(
        value["finding_count_band_upper_bounds"],
        path="finding_count_band_upper_bounds",
    )
    _strict_cutpoints(
        value["report_length_band_upper_bounds"],
        path="report_length_band_upper_bounds",
    )
    normalizer = _closed_mapping(
        value["verifier_normalizer_contract"],
        fields={
            "contract_id",
            "normalizer_source_ref",
            "normalizer_source_sha256",
            "report_tokenizer_sha256",
            "benchmark_component_kinds",
        },
        path="verifier_normalizer_contract",
    )
    if normalizer["contract_id"] != "assignment-verifier-normalizer-v1":
        raise RecordValidationError("wrong verifier normalizer contract_id")
    source_ref = _artifact_ref_value(
        normalizer["normalizer_source_ref"],
        path="verifier_normalizer_contract.normalizer_source_ref",
    )
    if _sha256(
        normalizer["normalizer_source_sha256"],
        path="verifier_normalizer_contract.normalizer_source_sha256",
    ) != source_ref.sha256:
        raise RecordValidationError("normalizer source digest is inconsistent")
    _sha256(
        normalizer["report_tokenizer_sha256"],
        path="verifier_normalizer_contract.report_tokenizer_sha256",
    )
    if normalizer["benchmark_component_kinds"] != {
        "SWE": ["check_runner", "failure_class"],
        "TAU": ["evaluator_component"],
    }:
        raise RecordValidationError("benchmark component kinds are incomplete")
    runtime = _closed_mapping(
        value["assignment_runtime_contract"],
        fields={"implementation", "python_version", "unicodedata_unidata_version"},
        path="assignment_runtime_contract",
    )
    if runtime["implementation"] != "CPython":
        raise RecordValidationError("assignment runtime must be CPython")
    _strict_text(runtime["python_version"], path="assignment_runtime_contract.python_version")
    _strict_text(
        runtime["unicodedata_unidata_version"],
        path="assignment_runtime_contract.unicodedata_unidata_version",
    )
    backend = value["backend_receipt_ref"]
    if mode == "synthetic_derangement":
        if backend is not None:
            raise RecordValidationError("synthetic assignment backend ref must be null")
    else:
        _artifact_ref_value(backend, path="backend_receipt_ref")
    stratum_keys = value["stratum_keys"]
    if not isinstance(stratum_keys, list) or not stratum_keys:
        raise RecordValidationError("stratum_keys must be a non-empty ordered array")
    for index, key in enumerate(stratum_keys):
        _strict_text(key, path=f"stratum_keys[{index}]")
    if len(stratum_keys) != len(set(cast(list[str], stratum_keys))):
        raise RecordValidationError("stratum_keys must be unique")


def import_assignment_program(
    source: Path,
    *,
    run_root: Path,
    destination: str = "inputs/assignment-program.json",
) -> ArtifactRef:
    """Import the concrete non-executable assignment-program authority."""

    if Path(source).suffix.lower() != ".json":
        raise RecordValidationError("assignment program source must be JSON")
    try:
        source_bytes = Path(source).read_bytes()
    except OSError as exc:
        raise RecordValidationError(
            f"cannot read assignment program {source}: {exc}"
        ) from exc
    decoded = _load_json_bytes(source_bytes, source=Path(source))
    value = _closed_mapping(
        decoded,
        fields=ASSIGNMENT_PROGRAM_GRAMMAR.fields,
        path="$",
    )
    if value.get("record_kind") != ASSIGNMENT_PROGRAM_GRAMMAR.record_kind:
        raise RecordValidationError("wrong assignment-program record_kind")
    _require_canonical_text(value)
    _validate_assignment_program(value)
    return _publish_closed_value(
        value,
        grammar=ASSIGNMENT_PROGRAM_GRAMMAR,
        run_root=run_root,
        destination_template=destination,
        role="assignment_program",
    )


def validate_task_registry(value: dict[str, object]) -> None:
    """Validate one already-decoded closed task registry."""

    _validate_task_registry(value)


def validate_assignment_program(value: dict[str, object]) -> None:
    """Validate one already-decoded closed assignment program."""

    _validate_assignment_program(value)


__all__ = [
    "ClosedJsonImport",
    "ConfirmationPreflightRegistry",
    "ConfirmationPreflightUnavailable",
    "ConfirmationRosterCeremonyCapability",
    "DRAND_MAINNET_CHAIN_HASH",
    "import_assignment_program",
    "import_closed_json",
    "import_task_registry",
    "require_declared_fields",
    "validate_assignment_program",
    "validate_task_registry",
    "verify_ed25519_canonical_json",
]
