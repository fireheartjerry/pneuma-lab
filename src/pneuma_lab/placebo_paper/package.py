"""Admission control for the sealed evidence package.

The manuscript accepts numbers from exactly one kind of object: a verified,
sealed Task 10 evidence package produced under an authority that licenses a
scientific result. Everything else is rejected by name, with the reason stated,
so a rejection is diagnosable rather than mysterious.

The rejections that matter most are the ones a hurried author would most like
to bypass:

*Step 4A.* The bounded implementation-verification lineage reached a miniature
power final and a sealed schedule. It is a plumbing proof. Its numbers are
real numbers about a synthetic exercise, which makes them the most dangerous
numbers in the repository, because they look exactly like results.

*An unsealed or partially verified artifact root.* A root whose recursive
verification did not complete cannot support a claim about what was measured.

*A package with no completed unblind ceremony.* Numbers read before the permit
was consumed are numbers the analyst was not allowed to see.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .errors import (
    MissingReceipt,
    PackageRejected,
    UnsealedPackage,
    WrongAuthority,
    WrongLineage,
)

#: The only package kind that may supply a number to the manuscript.
ADMISSIBLE_PACKAGE_KIND = "resampling_task10_sealed"

#: The only lineage that may supply a number to the manuscript.
ADMISSIBLE_LINEAGE = "canonical_confirmation"

#: Lineages that are rejected by name, with the reason the reader deserves.
REJECTED_LINEAGES: Mapping[str, str] = {
    "step_4a": (
        "Step 4A is the bounded implementation-verification lineage. Its power "
        "final and sealed schedule prove plumbing, not efficacy; its numbers "
        "describe a synthetic exercise and may never appear as results."
    ),
    "step_4b": (
        "Step 4B is a separately authorized experiment and is not the "
        "confirmation lineage."
    ),
    "p0_incomplete": (
        "The preserved canonical P0 screen and its ten completed shards are an "
        "explicitly experiment-only incomplete non-result."
    ),
    "synthetic_fixture": (
        "A synthetic fixture validates code and runtime only."
    ),
    "pilot": (
        "Pilot efficacy is labelled and excluded by the design; it cannot "
        "select or report a result."
    ),
}

#: Receipts a package must carry before any number is readable.
REQUIRED_RECEIPTS = (
    "study_manifest",
    "prefix_schedule",
    "assignment_ledger",
    "packet_index",
    "blinded_projection",
    "analysis_freeze",
    "unblind_receipt",
    "artifact_root",
    "power_report",
)

#: Verdicts the preregistered taxonomy defines. A package claiming any other
#: verdict has been edited after the fact.
ADMISSIBLE_VERDICTS = (
    "FEASIBILITY_NO_GO",
    "PIPELINE_INVALID",
    "HARMFUL_OR_MISDIRECTING",
    "CAUSAL_CONTENT",
    "SHAM_PACKET_ONLY",
    "UNRESOLVED_RESAMPLING",
    "RESAMPLING_CONSISTENT",
)

#: Authority tokens that license a scientific result of record.
RESULT_AUTHORITIES = frozenset({"confirmation_execution_authorized"})


@dataclass(frozen=True)
class SealedPackage:
    """A package that passed admission. Construct only via :func:`admit`."""

    path: Path
    package_kind: str
    lineage: str
    authority: str
    verdict: str
    receipts: Mapping[str, str]
    numbers: Mapping[str, Any]
    artifact_root_digest: str

    def number(self, key: str) -> Any:
        """Return an emitted number, or raise if the package did not emit it."""

        if key not in self.numbers:
            raise PackageRejected(
                f"the package emitted no value for {key!r}; the manuscript may "
                "not supply one by hand"
            )
        return self.numbers[key]


def _require(condition: bool, error: type[PackageRejected], message: str) -> None:
    if not condition:
        raise error(message)


def admit(path: Path) -> SealedPackage:
    """Admit a sealed evidence package, or refuse it with a stated reason."""

    manifest_path = Path(path) / "package.json"
    _require(
        manifest_path.is_file(),
        PackageRejected,
        f"no package.json at {manifest_path}; a directory is not a package",
    )
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))

    kind = str(payload.get("package_kind", ""))
    _require(
        kind == ADMISSIBLE_PACKAGE_KIND,
        PackageRejected,
        f"package_kind {kind!r} is not {ADMISSIBLE_PACKAGE_KIND!r}",
    )

    lineage = str(payload.get("lineage", ""))
    if lineage in REJECTED_LINEAGES:
        raise WrongLineage(
            f"lineage {lineage!r} may not supply paper numbers. "
            + REJECTED_LINEAGES[lineage]
        )
    _require(
        lineage == ADMISSIBLE_LINEAGE,
        WrongLineage,
        f"lineage {lineage!r} is not the confirmation lineage "
        f"{ADMISSIBLE_LINEAGE!r}",
    )

    _require(
        bool(payload.get("sealed")),
        UnsealedPackage,
        "package is not sealed",
    )
    root = payload.get("artifact_root") or {}
    _require(
        bool(root.get("verified")),
        UnsealedPackage,
        "the artifact root did not complete recursive verification",
    )
    root_digest = str(root.get("digest", ""))
    _require(
        len(root_digest) == 64,
        UnsealedPackage,
        "the artifact root digest is missing or malformed",
    )

    unblind = payload.get("unblind") or {}
    _require(
        bool(unblind.get("ceremony_completed")),
        UnsealedPackage,
        "no completed unblind ceremony; numbers read before the permit was "
        "consumed are numbers the analyst was not allowed to see",
    )

    authority = str(payload.get("authority", ""))
    _require(
        authority in RESULT_AUTHORITIES,
        WrongAuthority,
        f"authority {authority!r} does not license a scientific result of record",
    )

    receipts = payload.get("receipts") or {}
    missing = [name for name in REQUIRED_RECEIPTS if not receipts.get(name)]
    if missing:
        raise MissingReceipt(
            "package is missing required receipts: " + ", ".join(sorted(missing))
        )

    verdict = str(payload.get("verdict", ""))
    _require(
        verdict in ADMISSIBLE_VERDICTS,
        PackageRejected,
        f"verdict {verdict!r} is not in the preregistered taxonomy",
    )

    numbers = payload.get("numbers") or {}
    _require(
        isinstance(numbers, dict),
        PackageRejected,
        "package 'numbers' must be an object emitted by the analysis",
    )

    return SealedPackage(
        path=Path(path),
        package_kind=kind,
        lineage=lineage,
        authority=authority,
        verdict=verdict,
        receipts={str(k): str(v) for k, v in receipts.items()},
        numbers=dict(numbers),
        artifact_root_digest=root_digest,
    )
