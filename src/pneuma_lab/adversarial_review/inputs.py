"""Campaign input contract: exact, digest-bound, and fail-closed.

A campaign declares the precise objects it reviewed. Every declared object is
resolved to bytes on disk and hashed at preflight. A missing path, a digest
mismatch, or an undeclared-but-required input aborts the campaign before any
reviewer runs — the system never reviews an approximation of the artifact.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping

from .canonical import digest_file, digest_value, is_sha256_hex
from .errors import InputContractError, StaleInputError

#: Input slots a role may declare as required. Every slot a configured role
#: needs must be present in the bundle, or the campaign fails closed.
INPUT_SLOTS = (
    "repo_commit",
    "design",
    "plan",
    "manifest",
    "input_lock",
    "artifact_root",
    "power_report",
    "spend_ledger",
    "manuscript",
    "bibliography",
    "citation_queue",
    "venue_policy",
    "environment",
    "reviewer_reports",
    "editor_synthesis",
)


@dataclass(frozen=True)
class InputObject:
    """One declared, digest-bound campaign input."""

    slot: str
    path: str
    declared_digest: str
    description: str
    optional: bool = False

    def __post_init__(self) -> None:
        if self.slot not in INPUT_SLOTS:
            raise InputContractError(f"unknown input slot {self.slot!r}")
        if not is_sha256_hex(self.declared_digest):
            raise InputContractError(
                f"input {self.slot!r} declared_digest must be lowercase hex sha256"
            )

    def to_canonical(self) -> dict[str, Any]:
        return {
            "slot": self.slot,
            "path": self.path,
            "declared_digest": self.declared_digest,
            "description": self.description,
            "optional": self.optional,
        }


@dataclass(frozen=True)
class EnvironmentPin:
    """The exact environment a campaign ran against.

    Recorded so a replay can prove it used the same interpreter, the same
    dependency set, and the same repository state. A replay under a different
    pin is a different campaign, not the same one.
    """

    repo_commit: str
    repo_dirty: bool
    python_version: str
    platform: str
    dependency_digest: str

    def to_canonical(self) -> dict[str, Any]:
        return {
            "repo_commit": self.repo_commit,
            "repo_dirty": self.repo_dirty,
            "python_version": self.python_version,
            "platform": self.platform,
            "dependency_digest": self.dependency_digest,
        }


@dataclass(frozen=True)
class CampaignInputs:
    """The complete, resolved input bundle for one campaign stage."""

    campaign_id: str
    stage: str
    root: Path
    environment: EnvironmentPin
    objects: tuple[InputObject, ...]
    receipt_index: Mapping[str, str] = field(default_factory=dict)
    external_sources: tuple[str, ...] = ()

    def by_slot(self, slot: str) -> tuple[InputObject, ...]:
        return tuple(item for item in self.objects if item.slot == slot)

    def slots(self) -> frozenset[str]:
        return frozenset(item.slot for item in self.objects)

    def resolve(self, item: InputObject) -> Path:
        return (self.root / item.path).resolve()

    def to_canonical(self) -> dict[str, Any]:
        return {
            "campaign_id": self.campaign_id,
            "stage": self.stage,
            "environment": self.environment.to_canonical(),
            "objects": [item.to_canonical() for item in self.objects],
            "receipt_index": dict(sorted(self.receipt_index.items())),
            "external_sources": sorted(self.external_sources),
        }

    @property
    def digest(self) -> str:
        return digest_value(self.to_canonical())


def preflight(inputs: CampaignInputs, required_slots: Iterable[str]) -> dict[str, str]:
    """Verify every declared input resolves and matches its declared digest.

    Returns the observed digest per declared path. Raises ``InputContractError``
    for a missing required slot or unresolvable path, and ``StaleInputError``
    when bytes on disk disagree with the declaration.
    """

    required = set(required_slots)
    present = inputs.slots()
    missing = sorted(required - present)
    if missing:
        raise InputContractError(
            "campaign is missing required input slots: " + ", ".join(missing)
        )

    root = inputs.root.resolve()
    observed: dict[str, str] = {}
    for item in inputs.objects:
        path = inputs.resolve(item)
        try:
            path.relative_to(root)
        except ValueError as exc:  # pragma: no cover - defensive
            raise InputContractError(
                f"input {item.slot!r} path {item.path!r} escapes the campaign root"
            ) from exc
        if not path.exists():
            if item.optional:
                continue
            raise InputContractError(
                f"input {item.slot!r} path {item.path!r} does not exist"
            )
        if path.is_dir():
            actual = _digest_tree(path)
        else:
            actual = digest_file(str(path))
        if actual != item.declared_digest:
            raise StaleInputError(
                f"input {item.slot!r} at {item.path!r} is stale: declared "
                f"{item.declared_digest}, observed {actual}"
            )
        observed[item.path] = actual
    return observed


def _digest_tree(root: Path) -> str:
    """Return a digest over a directory's relative paths and file digests."""

    entries: list[tuple[str, str]] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames.sort()
        for name in sorted(filenames):
            absolute = Path(dirpath) / name
            relative = absolute.relative_to(root).as_posix()
            entries.append((relative, digest_file(str(absolute))))
    return digest_value(entries)


def required_slots_for(role_ids: Iterable[str]) -> frozenset[str]:
    """Return the union of required input slots across ``role_ids``."""

    from .roles import ROLES_BY_ID

    slots: set[str] = set()
    for role_id in role_ids:
        try:
            slots.update(ROLES_BY_ID[role_id].required_inputs)
        except KeyError as exc:
            raise InputContractError(f"unknown role {role_id!r}") from exc
    return frozenset(slots)
