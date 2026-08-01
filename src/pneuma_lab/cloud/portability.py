"""Platform-neutral receipt bundle sealing and offline verification.

The producer runs once after upstream identities have been frozen.  Other
hosts verify those exact bytes; they do not independently refetch an upstream
object and hope that two network responses happen to agree.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from pathlib import Path, PurePosixPath
from typing import Any

from .authorization_keys import canonical_bytes
from .errors import CloudManifestError
from .inputs import verify_input_lock
from .qualification import REGISTERED_FAMILIES, validate_qualification_audit


_UTC_TIMESTAMP = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$")


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _reject_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON constant {value}")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError(f"duplicate JSON key {key!r}")
        value[key] = item
    return value


def _relative_posix_path(value: str) -> str:
    if "\\" in value:
        raise CloudManifestError(f"bundle path must use POSIX separators: {value!r}")
    path = PurePosixPath(value)
    if not value or path.is_absolute() or str(path) != value or any(part in ("", ".", "..") for part in path.parts):
        raise CloudManifestError(f"bundle path must be canonical and relative: {value!r}")
    return value


def roster_digest(records: Sequence[Mapping[str, Any]]) -> str:
    """Digest one complete, validated G-ROSTER record set in stable order."""

    audits = [validate_qualification_audit(record) for record in records]
    keys = [(audit["tier"], audit["benchmark_family"]) for audit in audits]
    if len(set(keys)) != len(keys):
        raise CloudManifestError("G-ROSTER portability set contains a duplicate tier/family")
    tiers = {tier for tier, _ in keys}
    families = {family for _, family in keys}
    if len(tiers) != 1 or families != set(REGISTERED_FAMILIES):
        raise CloudManifestError("G-ROSTER portability set must cover one tier and every registered family")
    ordered = sorted(audits, key=lambda audit: audit["benchmark_family"])
    return _sha256(canonical_bytes(ordered))


def build_portability_bundle(
    *,
    frozen_timestamp: str,
    input_lock: Mapping[str, Any],
    roster_records: Sequence[Mapping[str, Any]],
    receipt_payloads: Mapping[str, bytes],
) -> bytes:
    """Seal immutable identities and receipt payloads as canonical UTF-8 JSON.

    Payload bytes are not embedded.  Their relative POSIX path, size, and
    SHA-256 are sealed so the same files can be copied and verified offline.
    """

    if not _UTC_TIMESTAMP.fullmatch(frozen_timestamp):
        raise CloudManifestError("portability bundle requires a fixed UTC timestamp")
    if not receipt_payloads:
        raise CloudManifestError("portability bundle must bind at least one receipt payload")
    receipts = []
    for path, payload in sorted(receipt_payloads.items()):
        relative = _relative_posix_path(path)
        if not isinstance(payload, bytes):
            raise CloudManifestError(f"receipt payload must be bytes: {relative}")
        receipts.append({"relative_path": relative, "sha256": _sha256(payload), "size_bytes": len(payload)})
    record = {
        "record_kind": "cloud_receipt_portability_bundle",
        "schema_version": "0.1.0",
        "frozen_timestamp": frozen_timestamp,
        "input_lock_sha256": verify_input_lock(input_lock),
        "g_roster_sha256": roster_digest(roster_records),
        "receipts": receipts,
    }
    return canonical_bytes(record) + b"\n"


def verify_portability_bundle(
    bundle_bytes: bytes,
    *,
    input_lock: Mapping[str, Any],
    roster_records: Sequence[Mapping[str, Any]],
    receipt_root: Path,
) -> str:
    """Verify sealed bytes and all payloads offline; return the bundle digest."""

    try:
        text = bundle_bytes.decode("utf-8")
        record = json.loads(text, parse_constant=_reject_constant, object_pairs_hook=_unique_object)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise CloudManifestError("portability bundle is not UTF-8 JSON") from exc
    if not isinstance(record, dict) or canonical_bytes(record) + b"\n" != bundle_bytes:
        raise CloudManifestError("portability bundle is not newline-terminated canonical JSON")
    required = {
        "record_kind", "schema_version", "frozen_timestamp",
        "input_lock_sha256", "g_roster_sha256", "receipts",
    }
    if set(record) != required or not isinstance(record.get("frozen_timestamp"), str) or not _UTC_TIMESTAMP.fullmatch(record["frozen_timestamp"]):
        raise CloudManifestError("portability bundle has an invalid closed metadata shape")
    if record.get("record_kind") != "cloud_receipt_portability_bundle" or record.get("schema_version") != "0.1.0":
        raise CloudManifestError("unsupported portability bundle contract")
    if record.get("input_lock_sha256") != verify_input_lock(input_lock):
        raise CloudManifestError("portability bundle input-lock digest mismatch")
    if record.get("g_roster_sha256") != roster_digest(roster_records):
        raise CloudManifestError("portability bundle G-ROSTER digest mismatch")

    root = receipt_root.resolve(strict=True)
    seen: set[str] = set()
    receipts = record.get("receipts")
    if not isinstance(receipts, list):
        raise CloudManifestError("portability bundle receipts must be a list")
    if not receipts:
        raise CloudManifestError("portability bundle must bind at least one receipt payload")
    for receipt in receipts:
        if not isinstance(receipt, dict) or set(receipt) != {"relative_path", "sha256", "size_bytes"}:
            raise CloudManifestError("portability bundle receipt has an invalid shape")
        relative = _relative_posix_path(receipt["relative_path"])
        if relative in seen:
            raise CloudManifestError(f"duplicate portability receipt path: {relative}")
        seen.add(relative)
        candidate = receipt_root.joinpath(*PurePosixPath(relative).parts)
        resolved = candidate.resolve(strict=True)
        try:
            resolved.relative_to(root)
        except ValueError as exc:
            raise CloudManifestError(f"portability receipt escapes root: {relative}") from exc
        if candidate.is_symlink() or not resolved.is_file():
            raise CloudManifestError(f"portability receipt must be a regular non-symlink file: {relative}")
        payload = resolved.read_bytes()
        if len(payload) != receipt["size_bytes"] or _sha256(payload) != receipt["sha256"]:
            raise CloudManifestError(f"portability receipt bytes mismatch: {relative}")
    return _sha256(bundle_bytes)


def main(argv: Sequence[str] | None = None) -> int:
    """Run the same offline portability gate on Windows or Linux."""

    parser = argparse.ArgumentParser(description="Seal or verify an immutable cloud receipt bundle offline")
    commands = parser.add_subparsers(dest="command", required=True)
    seal = commands.add_parser("seal")
    seal.add_argument("output", type=Path)
    seal.add_argument("input_lock", type=Path)
    seal.add_argument("frozen_timestamp")
    seal.add_argument("--roster", action="append", required=True, type=Path)
    seal.add_argument("--receipt", action="append", required=True, metavar="POSIX_PATH=FILE")
    verify = commands.add_parser("verify")
    verify.add_argument("bundle", type=Path)
    verify.add_argument("input_lock", type=Path)
    verify.add_argument("receipt_root", type=Path)
    verify.add_argument("roster", nargs="+", type=Path)
    args = parser.parse_args(argv)
    lock = json.loads(args.input_lock.read_text(encoding="utf-8"))
    records = [json.loads(path.read_text(encoding="utf-8")) for path in args.roster]
    if args.command == "seal":
        payloads: dict[str, bytes] = {}
        for binding in args.receipt:
            relative, separator, source = binding.partition("=")
            if not separator:
                raise CloudManifestError("receipt binding must be POSIX_PATH=FILE")
            if relative in payloads:
                raise CloudManifestError(f"duplicate receipt binding: {relative}")
            payloads[relative] = Path(source).read_bytes()
        bundle = build_portability_bundle(
            frozen_timestamp=args.frozen_timestamp,
            input_lock=lock,
            roster_records=records,
            receipt_payloads=payloads,
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(bundle)
        result = {
            "bundle_sha256": _sha256(bundle),
            "g_roster_sha256": roster_digest(records),
            "input_lock_sha256": verify_input_lock(lock),
        }
        print((canonical_bytes(result) + b"\n").decode("utf-8"), end="")
        return 0
    bundle = args.bundle.read_bytes()
    result = {
        "bundle_sha256": verify_portability_bundle(
            bundle, input_lock=lock, roster_records=records, receipt_root=args.receipt_root
        ),
        "g_roster_sha256": roster_digest(records),
        "input_lock_sha256": verify_input_lock(lock),
    }
    print((canonical_bytes(result) + b"\n").decode("utf-8"), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
