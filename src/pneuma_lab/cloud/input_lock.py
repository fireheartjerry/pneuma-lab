"""Construct and classify Step 5B input locks without retrieving any bytes.

The committed Step 5A lock is a *shape demonstration*: every repository is a
placeholder, every digest is a repeated nibble, and every artifact shares one
receipt path. It proves the record validates. It proves nothing about the
experiment's actual inputs, and a reader skimming a green test suite could
easily mistake one for the other.

This module makes that distinction machine-checkable and, crucially, **derived
rather than asserted**. There is no `is_real: true` field to set, because such
a field would be exactly as trustworthy as whoever wrote it. Instead the
classification is recomputed from the identities themselves every time:

- `classify_input_lock` returns `synthetic_demonstration` or `real_candidate`.
- `real_candidate_findings` returns the specific reasons, field by field, so a
  refusal is actionable instead of a bare "no".
- `build_candidate_input_lock` refuses to emit a record that does not classify
  as a real candidate, so the constructor cannot be used to launder a
  placeholder into something that looks authoritative.

What "real candidate" does and does not mean, stated plainly, because the gap
matters more than the check:

It means every required identity is *present, immutable, and not obviously a
placeholder* — a 40-hex commit rather than a branch name, a
`linux/amd64@sha256:` digest rather than a floating tag, a named licence, and a
distinct receipt path per artifact.

It does **not** mean the identity exists, that it resolves to anything, that
the bytes behind it were fetched, or that their digests match. Nothing here
touches a network. A `real_candidate` lock is a well-formed *proposal* for the
Step 5B audit to verify; it is not the audit, and it is not evidence that any
external input has been obtained.
"""

from __future__ import annotations

import re
from collections.abc import Iterator, Mapping, Sequence
from typing import Any

from .errors import CloudManifestError
from .manifests import validate_input_lock


SYNTHETIC = "synthetic_demonstration"
REAL_CANDIDATE = "real_candidate"

# Namespaces reserved for documentation and examples (RFC 2606 / RFC 6761) plus
# the local-only suffixes this repository uses for fixtures. A pin inside one of
# these can never denote a real external artifact.
_RESERVED_HOST_SUFFIXES = (".example", ".invalid", ".test", ".local", ".localhost")
_RESERVED_HOST_LABELS = ("example.com", "example.net", "example.org", "example.edu", "registry.example")

# Repository owners that are obviously stand-ins rather than real accounts.
_PLACEHOLDER_OWNERS = frozenset({"org", "owner", "example", "acme", "foo", "test", "placeholder", "your-org", "some-org"})

# Repository names that describe the *slot* rather than a project.
_PLACEHOLDER_NAMES = frozenset({"model", "tokenizer", "benchmark", "dataset", "verifier", "base", "repo", "repository", "image"})

_HEX40 = re.compile(r"^[0-9a-f]{40}$")
_OCI_DIGEST = re.compile(r"^linux/amd64@sha256:([0-9a-f]{64})$")


def _is_placeholder_hex(value: str) -> bool:
    """Return whether a hex string is an obvious filler rather than a digest.

    Catches the single-repeated-nibble family (`aaa…`, `000…`, `fff…`) and the
    short-cycle fillers (`ababab…`, `0123012301…`). A genuine SHA has no such
    structure; the odds of one arising by chance are negligible, and a false
    positive costs a re-derivation rather than a wrong scientific claim.
    """

    if len(set(value)) <= 2 and len(value) > 8:
        return True
    for period in (1, 2, 3, 4, 6, 8):
        if len(value) % period == 0 and value == value[:period] * (len(value) // period):
            return True
    return False


def _is_placeholder_repository(repository: str) -> bool:
    lowered = repository.strip().lower()
    if not lowered:
        return True
    host = lowered.split("/", 1)[0]
    if any(host.endswith(suffix) for suffix in _RESERVED_HOST_SUFFIXES):
        return True
    if any(label in lowered for label in _RESERVED_HOST_LABELS):
        return True
    parts = [part for part in lowered.split("/") if part]
    if len(parts) < 2:
        # A bare name carries no owner, so it cannot identify an upstream repo.
        return True
    if parts[0] in _PLACEHOLDER_OWNERS:
        return True
    return all(part in _PLACEHOLDER_NAMES for part in parts[1:])


def _pins(lock: Mapping[str, Any]) -> Iterator[tuple[str, Mapping[str, Any]]]:
    """Yield `(field path, revision pin)` for every revision-pinned artifact."""

    for index, pin in enumerate(lock["model_pins"]):
        yield f"model_pins[{index}]", pin
    yield "tokenizer_pin", lock["tokenizer_pin"]
    for index, pin in enumerate(lock["benchmark_pins"]):
        yield f"benchmark_pins[{index}]", pin
    for index, pin in enumerate(lock["verifier_sources"]):
        yield f"verifier_sources[{index}]", pin


def _receipts(lock: Mapping[str, Any]) -> Iterator[tuple[str, Mapping[str, Any]]]:
    for path, pin in _pins(lock):
        yield f"{path}.snapshot_receipt", pin["snapshot_receipt"]
    for key in ("contamination_receipts", "license_receipts"):
        for index, receipt in enumerate(lock[key]):
            yield f"{key}[{index}]", receipt


def real_candidate_findings(record: Mapping[str, Any]) -> tuple[dict[str, str], ...]:
    """Return every reason this lock is not yet a real candidate.

    An empty result means the identities are well-formed and immutable. It does
    not mean they exist; see the module docstring.
    """

    lock = validate_input_lock(record)
    findings: list[dict[str, str]] = []

    def note(field: str, reason: str) -> None:
        findings.append({"field": field, "reason": reason})

    for field, pin in _pins(lock):
        repository = str(pin["repository"])
        if _is_placeholder_repository(repository):
            note(f"{field}.repository", f"{repository!r} is a placeholder or reserved-namespace repository")
        revision = str(pin["revision"])
        if not _HEX40.fullmatch(revision):
            note(f"{field}.revision", "revision must be an immutable 40-hex commit, not a tag or branch")
        elif _is_placeholder_hex(revision):
            note(f"{field}.revision", f"{revision!r} is filler rather than a commit identity")
        if not str(pin["license"]).strip():
            note(f"{field}.license", "licence must be named")

    for index, pin in enumerate(lock["benchmark_pins"]):
        dataset = str(pin["dataset_revision"])
        if not _HEX40.fullmatch(dataset) or _is_placeholder_hex(dataset):
            note(f"benchmark_pins[{index}].dataset_revision", "dataset revision must be an immutable 40-hex commit")
        manifest = str(pin["task_manifest_sha256"])
        if _is_placeholder_hex(manifest):
            note(f"benchmark_pins[{index}].task_manifest_sha256", "task-manifest digest is filler rather than a content digest")

    for index, base in enumerate(lock["container_bases"]):
        repository = str(base["repository"])
        if _is_placeholder_repository(repository):
            note(f"container_bases[{index}].repository", f"{repository!r} is a placeholder or reserved-namespace registry")
        match = _OCI_DIGEST.fullmatch(str(base["digest"]))
        if match is None:
            note(f"container_bases[{index}].digest", "image must be pinned as linux/amd64@sha256:<64 hex>")
        elif _is_placeholder_hex(match.group(1)):
            note(f"container_bases[{index}].digest", "image digest is filler rather than a manifest digest")

    seen: dict[str, str] = {}
    for field, receipt in _receipts(lock):
        digest = str(receipt["sha256"])
        if _is_placeholder_hex(digest):
            note(f"{field}.sha256", "receipt digest is filler rather than a content digest")
        path = str(receipt["relative_path"])
        # Distinct artifacts writing one receipt path is the signature of the
        # shape demonstration, and would also make the mirrored receipts
        # mutually unverifiable.
        if path in seen and seen[path] != field:
            note(f"{field}.relative_path", f"receipt path {path!r} is already used by {seen[path]}")
        seen.setdefault(path, field)

    return tuple(findings)


def classify_input_lock(record: Mapping[str, Any]) -> str:
    """Return `real_candidate` or `synthetic_demonstration`, always derived."""

    return SYNTHETIC if real_candidate_findings(record) else REAL_CANDIDATE


def require_real_candidate_lock(record: Mapping[str, Any]) -> dict[str, Any]:
    """Return the lock only when every required identity is real and immutable."""

    findings = real_candidate_findings(record)
    if findings:
        detail = "; ".join(f"{item['field']}: {item['reason']}" for item in findings)
        raise CloudManifestError(f"input lock is a synthetic demonstration, not a real candidate: {detail}")
    return validate_input_lock(record)


def build_candidate_input_lock(
    *,
    frozen_timestamp: str,
    provenance: Mapping[str, str],
    model_pins: Sequence[Mapping[str, Any]],
    tokenizer_pin: Mapping[str, Any],
    benchmark_pins: Sequence[Mapping[str, Any]],
    container_bases: Sequence[Mapping[str, Any]],
    verifier_sources: Sequence[Mapping[str, Any]],
    contamination_receipts: Sequence[Mapping[str, Any]],
    license_receipts: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Assemble a real candidate lock, refusing to emit a placeholder one.

    Every identity must be supplied by the caller from an external source they
    have already established. This function performs no retrieval, no tag
    resolution, and no digest discovery — it cannot invent an identity, only
    refuse a bad one.
    """

    record = {
        "record_kind": "cloud_input_lock",
        "schema_version": "0.2.0",
        "frozen_timestamp": frozen_timestamp,
        "provenance": dict(provenance),
        "model_pins": [dict(pin) for pin in model_pins],
        "tokenizer_pin": dict(tokenizer_pin),
        "benchmark_pins": [dict(pin) for pin in benchmark_pins],
        "container_bases": [dict(base) for base in container_bases],
        "verifier_sources": [dict(source) for source in verifier_sources],
        "contamination_receipts": [dict(receipt) for receipt in contamination_receipts],
        "license_receipts": [dict(receipt) for receipt in license_receipts],
    }
    return require_real_candidate_lock(record)
