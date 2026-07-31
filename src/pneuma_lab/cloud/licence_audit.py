"""Independently reproducible base-commit licence audit.

The registered SWE eligibility criterion is a permissive licence **at the pinned
base commit**. The only evidence the project currently has is CL-009/DL-128
prose reporting a present-day repository-metadata proxy (9 C, 14 C++, and so
on). That prose is not qualification, and this module exists so the difference
cannot be blurred:

- It was derived from *current* metadata, not base commits, so it answers a
  different question than the criterion asks.
- CL-027 records that no response artifact, URL, or digest was committed for
  the corroboration attempt, so **a reviewer cannot recompute it**. An
  unrecomputable number is not evidence however often it is cited.

What this module provides is the shape of the real thing plus the machinery to
verify one: a deterministic derivation command, an ordered roster carrying every
lineage's base commit, explicit inclusion or exclusion reason, observed licence,
and licence-evidence digest; the pinned dataset and task-manifest identities it
was derived from; per-language counts cross-checked against the roster rather
than asserted beside it; and a qualification receipt bound to the deriving code
and to every input byte.

What it deliberately does **not** do is manufacture the audit. `derive_audit`
requires a caller-supplied observation callable that returns real licence bytes
per lineage; there is no default, no fallback, and no synthesis path. Absent
real observations the command fails closed and writes nothing, which is the
correct state until Step 5B actually runs. Nothing here touches a network.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

from .errors import CloudManifestError
from .manifests import _validate
from .provenance import canonical_text_digest


ADMITTING_REASON = "permissive_licence_at_base_commit"

# Reasons that exclude a lineage. Every lineage carries exactly one reason, so a
# lineage can never fall out of the roster silently.
EXCLUDING_REASONS = frozenset({
    "no_licence_at_base_commit",
    "non_permissive_licence_at_base_commit",
    "licence_unreadable_at_base_commit",
    "base_commit_unavailable",
    "duplicate_root_lineage",
})

# A reason may omit licence evidence only when there were no bytes to record.
_EVIDENCE_OPTIONAL = frozenset({"base_commit_unavailable", "duplicate_root_lineage"})

DERIVATION_COMMAND = ("python", "-m", "pneuma_lab.cloud.licence_audit", "derive")

# The observation a caller must supply per lineage: it returns the licence bytes
# retrieved at the pinned base commit, or None when nothing could be retrieved.
Observer = Callable[[Mapping[str, Any]], "Observation | None"]


class Observation:
    """One lineage's observed licence at its pinned base commit."""

    __slots__ = ("licence", "payload", "relative_path", "admitted", "reason")

    def __init__(self, *, licence: str | None, payload: bytes | None, relative_path: str | None, admitted: bool, reason: str) -> None:
        self.licence = licence
        self.payload = payload
        self.relative_path = relative_path
        self.admitted = admitted
        self.reason = reason


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def roster_digest(lineages: Sequence[Mapping[str, Any]]) -> str:
    """Digest the roster *in order*, so a reordering is a different roster."""

    return _digest(list(lineages))


def inputs_digest(pinned: Mapping[str, Any], evidence: Sequence[Mapping[str, str]]) -> str:
    """Digest the pinned identities together with every licence-evidence digest."""

    return _digest({"pinned_inputs": dict(pinned), "evidence": [dict(item) for item in evidence]})


def qualification_digest(*, code_sha256: str, roster_sha256: str, inputs_sha256: str) -> str:
    """Bind the deriving code to the roster and to every input byte."""

    return _digest({"code_sha256": code_sha256, "roster_sha256": roster_sha256, "inputs_sha256": inputs_sha256})


def language_counts(lineages: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    """Derive per-language admissible counts from the roster."""

    counts: dict[str, int] = {}
    for lineage in lineages:
        if lineage["admitted"]:
            counts[lineage["language"]] = counts.get(lineage["language"], 0) + 1
    return dict(sorted(counts.items()))


def validate_licence_audit(record: Mapping[str, Any]) -> dict[str, Any]:
    """Validate the audit and recompute every derived field it claims.

    The counts and the receipt are recomputed from the roster rather than read,
    so a record whose summary disagrees with its own evidence is rejected rather
    than believed.
    """

    audit = _validate(record, expected_kind="cloud_licence_audit")
    lineages = audit["lineages"]

    seen: set[str] = set()
    for lineage in lineages:
        name = lineage["root_lineage"]
        reason = lineage["reason"]
        admitted = lineage["admitted"]
        if admitted and reason != ADMITTING_REASON:
            raise CloudManifestError(f"lineage {name!r} is admitted but its reason is {reason!r}")
        if not admitted and reason == ADMITTING_REASON:
            raise CloudManifestError(f"lineage {name!r} carries the admitting reason but is excluded")
        if admitted and not lineage["licence"]:
            raise CloudManifestError(f"admitted lineage {name!r} must name the licence observed at its base commit")
        if lineage["licence_evidence"] is None and reason not in _EVIDENCE_OPTIONAL:
            raise CloudManifestError(f"lineage {name!r} must reference the licence bytes its {reason!r} verdict rests on")
        if name in seen and reason != "duplicate_root_lineage":
            raise CloudManifestError(f"root lineage {name!r} appears more than once without a duplicate verdict")
        seen.add(name)

    expected_counts = language_counts(lineages)
    if audit["language_counts"] != expected_counts:
        raise CloudManifestError(f"language counts {audit['language_counts']} disagree with the roster {expected_counts}")

    evidence = [dict(lineage["licence_evidence"]) for lineage in lineages if lineage["licence_evidence"] is not None]
    receipt = audit["receipt"]
    roster = roster_digest(lineages)
    inputs = inputs_digest(audit["pinned_inputs"], evidence)
    if receipt["roster_sha256"] != roster:
        raise CloudManifestError("receipt roster digest does not match the ordered roster")
    if receipt["inputs_sha256"] != inputs:
        raise CloudManifestError("receipt inputs digest does not match the pinned inputs and evidence")
    expected = qualification_digest(code_sha256=audit["derivation"]["code_sha256"], roster_sha256=roster, inputs_sha256=inputs)
    if receipt["qualification_sha256"] != expected:
        raise CloudManifestError("qualification receipt is not bound to this code, roster, and inputs")
    return audit


def verify_licence_evidence(record: Mapping[str, Any], repo_root: Path) -> tuple[str, ...]:
    """Re-hash every referenced licence-evidence file under the evidence root."""

    audit = validate_licence_audit(record)
    root = (repo_root / audit["derivation"]["evidence_root"]).resolve()
    verified: list[str] = []
    for lineage in audit["lineages"]:
        evidence = lineage["licence_evidence"]
        if evidence is None:
            continue
        candidate = root / evidence["relative_path"]
        resolved = candidate.resolve()
        try:
            resolved.relative_to(root)
        except ValueError as exc:
            raise CloudManifestError(f"licence evidence escapes the evidence root: {evidence['relative_path']}") from exc
        if candidate.is_symlink() or not resolved.is_file():
            raise CloudManifestError(f"licence evidence must be a regular non-symlink file: {evidence['relative_path']}")
        if hashlib.sha256(resolved.read_bytes()).hexdigest() != evidence["sha256"]:
            raise CloudManifestError(f"licence evidence digest mismatch: {evidence['relative_path']}")
        verified.append(evidence["relative_path"])
    return tuple(verified)


def derive_audit(
    *,
    frozen_timestamp: str,
    pinned_inputs: Mapping[str, Any],
    roster: Sequence[Mapping[str, Any]],
    observe: Observer,
    evidence_root: str,
    code_sha256: str | None = None,
) -> dict[str, Any]:
    """Derive the audit from real per-lineage observations, or fail closed.

    `roster` supplies the ordered candidate lineages (root lineage, language,
    base commit). `observe` must return a real `Observation` for each; returning
    None fails the derivation rather than defaulting the lineage to excluded,
    because "we did not look" and "we looked and found nothing" are different
    findings and only the second is evidence.
    """

    if not roster:
        raise CloudManifestError("a licence audit needs a candidate roster; an empty derivation is not an audit")
    if code_sha256 is None:
        # Canonical content digest, so a CRLF checkout derives the same receipt.
        code_sha256 = canonical_text_digest(Path(__file__))

    lineages: list[dict[str, Any]] = []
    for candidate in roster:
        observation = observe(candidate)
        if observation is None:
            raise CloudManifestError(
                f"no licence observation for {candidate['root_lineage']!r}; "
                "an unobserved lineage fails the derivation rather than defaulting to excluded"
            )
        reason = observation.reason
        if reason != ADMITTING_REASON and reason not in EXCLUDING_REASONS:
            raise CloudManifestError(f"unknown licence verdict {reason!r} for {candidate['root_lineage']!r}")
        evidence: dict[str, str] | None = None
        if observation.payload is not None:
            if not observation.relative_path:
                raise CloudManifestError(f"licence bytes for {candidate['root_lineage']!r} need an evidence path")
            evidence = {
                "relative_path": observation.relative_path,
                "sha256": hashlib.sha256(observation.payload).hexdigest(),
            }
        lineages.append({
            "root_lineage": candidate["root_lineage"],
            "language": candidate["language"],
            "base_commit": candidate["base_commit"],
            "admitted": observation.admitted,
            "reason": reason,
            "licence": observation.licence,
            "licence_evidence": evidence,
        })

    evidence_refs = [dict(item["licence_evidence"]) for item in lineages if item["licence_evidence"] is not None]
    roster_sha = roster_digest(lineages)
    inputs_sha = inputs_digest(pinned_inputs, evidence_refs)
    record = {
        "record_kind": "cloud_licence_audit",
        "schema_version": "0.1.0",
        "frozen_timestamp": frozen_timestamp,
        "derivation": {
            "command": list(DERIVATION_COMMAND),
            "code_sha256": code_sha256,
            "evidence_root": evidence_root,
        },
        "pinned_inputs": dict(pinned_inputs),
        "lineages": lineages,
        "language_counts": language_counts(lineages),
        "receipt": {
            "roster_sha256": roster_sha,
            "inputs_sha256": inputs_sha,
            "qualification_sha256": qualification_digest(code_sha256=code_sha256, roster_sha256=roster_sha, inputs_sha256=inputs_sha),
        },
    }
    return validate_licence_audit(record)


def main(argv: Sequence[str] | None = None) -> int:
    """Deterministic derivation entry point; refuses to run without observations.

    There is intentionally no flag that supplies synthetic observations. Until a
    real Step 5B licence retrieval exists, the honest outcome of running this
    command is a fail-closed refusal, and that is what it does.
    """

    parser = argparse.ArgumentParser(prog="python -m pneuma_lab.cloud.licence_audit", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    derive = sub.add_parser("derive", help="derive the base-commit licence audit")
    derive.add_argument("--observations", type=Path, required=True, help="path to real per-lineage licence observations")
    verify = sub.add_parser("verify", help="revalidate a committed audit and re-hash its evidence")
    verify.add_argument("--audit", type=Path, required=True)
    verify.add_argument("--repo-root", type=Path, default=Path.cwd())

    args = parser.parse_args(argv)
    if args.command == "verify":
        record = json.loads(args.audit.read_text(encoding="utf-8"))
        verified = verify_licence_evidence(record, args.repo_root)
        print(f"licence audit verified; {len(verified)} evidence files re-hashed")
        return 0

    if not args.observations.is_file():
        print(
            f"refusing to derive: no observation source at {args.observations}. "
            "A base-commit licence audit requires real retrieved licence bytes; "
            "CL-009/DL-128 proxy prose is not qualification and is not accepted here.",
            file=sys.stderr,
        )
        return 2
    print(
        "refusing to derive: observation sources are supplied programmatically through "
        "derive_audit(observe=...) so that each lineage's bytes are retrieved and hashed "
        "by the caller's Step 5B retrieval path. No file-driven synthesis path exists.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
