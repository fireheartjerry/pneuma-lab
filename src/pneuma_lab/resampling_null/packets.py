"""Token-exact REAL/SHAM verifier-packet construction."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
import hashlib
import re
from typing import Literal, Protocol

from pneuma_lab.foundation.artifacts import canonical_json_bytes

from .types import ArtifactRef


class PacketInvalid(ValueError):
    """Raised when packet parity or leakage cannot be proven."""


class Tokenizer(Protocol):
    def encode(self, text: str) -> tuple[int, ...]:
        ...


class PacketArtifactStore(Protocol):
    def put_text(
        self,
        relative_path: str,
        text: str,
        *,
        role: Literal["private_guidance"],
    ) -> ArtifactRef:
        ...


class IdentifierKind(str, Enum):
    REPOSITORY_FILE = "repository_file"
    SYMBOL = "symbol"
    TEST_CHECK = "test_check"
    DATABASE_ENTITY = "database_entity"
    POLICY_ACTION = "policy_action"
    TASK_RECORD = "task_record"


@dataclass(frozen=True, slots=True)
class IdentifierAtom:
    entity_id: str
    kind: IdentifierKind

    def __post_init__(self) -> None:
        if type(self.entity_id) is not str or not self.entity_id:
            raise ValueError("identifier entity_id must be non-empty text")
        if not isinstance(self.kind, IdentifierKind):
            raise TypeError("identifier kind must be IdentifierKind")


@dataclass(frozen=True, slots=True)
class LiteralAtom:
    text: str

    def __post_init__(self) -> None:
        if type(self.text) is not str:
            raise TypeError("literal atom text must be exact text")


PacketAtom = IdentifierAtom | LiteralAtom


@dataclass(frozen=True, slots=True)
class VerifierFinding:
    finding_id: str
    component: str
    code: str
    severity: str
    atoms: tuple[PacketAtom, ...]

    def __post_init__(self) -> None:
        for name in ("finding_id", "component", "code", "severity"):
            value = getattr(self, name)
            if type(value) is not str or not value:
                raise ValueError(f"{name} must be non-empty text")
        if not isinstance(self.atoms, tuple) or not self.atoms:
            raise TypeError("finding atoms must be a non-empty tuple")
        if not all(isinstance(atom, (IdentifierAtom, LiteralAtom)) for atom in self.atoms):
            raise TypeError("finding atoms contain an unknown type")


@dataclass(frozen=True, slots=True)
class PacketPolicy:
    max_findings: int
    max_evidence_tokens: int
    normalizer_version: str

    def __post_init__(self) -> None:
        if type(self.max_findings) is not int or self.max_findings <= 0:
            raise ValueError("max_findings must be a positive exact integer")
        if type(self.max_evidence_tokens) is not int or self.max_evidence_tokens <= 0:
            raise ValueError(
                "max_evidence_tokens must be a positive exact integer"
            )
        if type(self.normalizer_version) is not str or not self.normalizer_version:
            raise ValueError("normalizer_version must be non-empty text")


@dataclass(frozen=True, slots=True)
class TruncationReceipt:
    finding_id: str
    original_sha256: str
    retained_sha256: str
    original_chars: int
    retained_chars: int
    original_tokens: int
    retained_tokens: int
    omitted_atom_count: int
    rule: str


@dataclass(frozen=True, slots=True)
class PaddingSearchReceipt:
    pad_unit_set_sha256: str
    target_token_count: int
    states_explored: int
    selected_unit_counts: tuple[tuple[str, int], ...]
    search_algorithm: Literal["exact_dynamic_program_v1"]


@dataclass(frozen=True, slots=True)
class PacketPairReceipt:
    task_id: str
    donor_task_id: str
    prefix_index_sha256: str
    real_ref: ArtifactRef
    sham_ref: ArtifactRef
    real_token_count: int
    sham_token_count: int
    focal_verifier_ref: ArtifactRef
    donor_verifier_ref: ArtifactRef
    assignment_ref: ArtifactRef
    identifier_map_ref: ArtifactRef
    tokenizer_ref: ArtifactRef
    packet_template_ref: ArtifactRef
    normalized_real_ref: ArtifactRef
    normalized_sham_ref: ArtifactRef
    packet_policy_ref: ArtifactRef
    pad_unit_set_ref: ArtifactRef
    padding_search: PaddingSearchReceipt
    field_order: tuple[str, ...]
    severity_multiset: tuple[str, ...]
    schema_parity: Literal[True]
    field_parity: Literal[True]
    severity_parity: Literal[True]
    focal_collision_count: Literal[0]
    rewrite_expected: int
    rewrite_completed: int
    unmapped_identifiers: tuple[str, ...]
    donor_literal_collisions: tuple[str, ...]
    truncation_receipts: tuple[TruncationReceipt, ...]


_FIELD_ORDER = (
    "finding_id",
    "component",
    "code",
    "severity",
    "evidence",
)
_SAFE_PAD = re.compile(r"^[\s.,:;_\-()\[\]]+$")


def _atom_text(atom: PacketAtom) -> str:
    return atom.entity_id if isinstance(atom, IdentifierAtom) else atom.text


def _atoms_text(atoms: Sequence[PacketAtom]) -> str:
    return "".join(_atom_text(atom) for atom in atoms)


def _digest_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _bound_atoms(
    finding: VerifierFinding,
    *,
    tokenizer: Tokenizer,
    budget: int,
) -> tuple[tuple[PacketAtom, ...], TruncationReceipt]:
    original_text = _atoms_text(finding.atoms)
    retained = list(finding.atoms)
    while retained and len(tokenizer.encode(_atoms_text(retained))) > budget:
        retained.pop()
    retained_text = _atoms_text(retained)
    original_tokens = len(tokenizer.encode(original_text))
    retained_tokens = len(tokenizer.encode(retained_text))
    return tuple(retained), TruncationReceipt(
        finding_id=finding.finding_id,
        original_sha256=_digest_text(original_text),
        retained_sha256=_digest_text(retained_text),
        original_chars=len(original_text),
        retained_chars=len(retained_text),
        original_tokens=original_tokens,
        retained_tokens=retained_tokens,
        omitted_atom_count=len(finding.atoms) - len(retained),
        rule="drop_trailing_atoms_until_evidence_token_budget_v1",
    )


def _render(findings: Sequence[VerifierFinding], padding: str) -> str:
    rows = []
    for finding in findings:
        rows.append(
            {
                "finding_id": finding.finding_id,
                "component": finding.component,
                "code": finding.code,
                "severity": finding.severity,
                "evidence": _atoms_text(finding.atoms),
            }
        )
    return canonical_json_bytes(
        {
            "field_order": list(_FIELD_ORDER),
            "findings": rows,
            "padding": padding,
            "record_kind": "private_verifier_guidance_v1",
        },
        indent=None,
    ).decode("utf-8")


def _padding_search(
    shorter: Sequence[VerifierFinding],
    *,
    tokenizer: Tokenizer,
    target: int,
    neutral_pad_units: Sequence[str],
) -> tuple[str, PaddingSearchReceipt]:
    units = _validated_pad_units(neutral_pad_units)
    unit_digest = hashlib.sha256(
        canonical_json_bytes(list(units), indent=None)
    ).hexdigest()
    frontier: dict[str, tuple[int, ...]] = {"": tuple(0 for _ in units)}
    explored = 0
    max_states = max(256, (target + 1) * len(units) * 16)
    while frontier and explored < max_states:
        next_frontier: dict[str, tuple[int, ...]] = {}
        for padding in sorted(frontier, key=lambda value: value.encode("utf-8")):
            counts = frontier[padding]
            explored += 1
            token_count = len(tokenizer.encode(_render(shorter, padding)))
            if token_count == target:
                return padding, PaddingSearchReceipt(
                    pad_unit_set_sha256=unit_digest,
                    target_token_count=target,
                    states_explored=explored,
                    selected_unit_counts=tuple(
                        (unit, count)
                        for unit, count in zip(units, counts, strict=True)
                    ),
                    search_algorithm="exact_dynamic_program_v1",
                )
            if token_count > target:
                continue
            for index, unit in enumerate(units):
                candidate = padding + unit
                candidate_counts = list(counts)
                candidate_counts[index] += 1
                prior = next_frontier.get(candidate)
                frozen_counts = tuple(candidate_counts)
                if prior is None or frozen_counts < prior:
                    next_frontier[candidate] = frozen_counts
        frontier = next_frontier
    raise PacketInvalid("exact neutral padding target is unreachable")


def _validated_pad_units(neutral_pad_units: Sequence[str]) -> tuple[str, ...]:
    if not isinstance(neutral_pad_units, Sequence) or isinstance(
        neutral_pad_units,
        (str, bytes),
    ):
        raise PacketInvalid("neutral padding authority must be a sequence")
    if any(type(unit) is not str for unit in neutral_pad_units):
        raise PacketInvalid("neutral padding units must be exact text")
    units = tuple(
        sorted(
            set(neutral_pad_units),
            key=lambda unit: unit.encode("utf-8"),
        )
    )
    if not units or any(
        not unit or not _SAFE_PAD.fullmatch(unit)
        for unit in units
    ):
        raise PacketInvalid(
            "neutral padding units are empty, executable, or identifying"
        )
    return units


def build_packet_pair(
    real: Sequence[VerifierFinding],
    donor: Sequence[VerifierFinding],
    *,
    tokenizer: Tokenizer,
    policy: PacketPolicy,
    identifier_map: Mapping[IdentifierAtom, IdentifierAtom],
    true_focal_signatures: frozenset[str],
    neutral_pad_units: Sequence[str],
    artifact_store: PacketArtifactStore,
    real_relative_path: str,
    sham_relative_path: str,
    task_id: str,
    donor_task_id: str,
    prefix_index_sha256: str,
    focal_verifier_ref: ArtifactRef,
    donor_verifier_ref: ArtifactRef,
    assignment_ref: ArtifactRef,
    identifier_map_ref: ArtifactRef,
    tokenizer_ref: ArtifactRef,
    packet_template_ref: ArtifactRef,
    packet_policy_ref: ArtifactRef,
    pad_unit_set_ref: ArtifactRef,
) -> PacketPairReceipt:
    """Build one leakage-audited, token-exact REAL/SHAM pair."""

    if not isinstance(policy, PacketPolicy):
        raise TypeError("policy must be PacketPolicy")
    if not real or not donor:
        raise PacketInvalid("REAL and SHAM findings must be non-empty")
    units = _validated_pad_units(neutral_pad_units)
    retained_count = min(len(real), len(donor), policy.max_findings)
    focal = list(real[:retained_count])
    sham_source = list(donor[:retained_count])
    if retained_count == 0:
        raise PacketInvalid("packet policy retained no paired findings")

    rewrite_expected = 0
    rewrite_completed = 0
    unmapped: list[str] = []
    donor_identifiers = {
        atom.entity_id
        for finding in sham_source
        for atom in finding.atoms
        if isinstance(atom, IdentifierAtom)
    }
    literal_collisions: list[str] = []
    normalized_sham: list[VerifierFinding] = []
    for focal_finding, donor_finding in zip(focal, sham_source, strict=True):
        rewritten: list[PacketAtom] = []
        for atom in donor_finding.atoms:
            if isinstance(atom, IdentifierAtom):
                rewrite_expected += 1
                replacement = identifier_map.get(atom)
                if replacement is None:
                    unmapped.append(atom.entity_id)
                    continue
                if type(replacement) is not IdentifierAtom or replacement.kind is not atom.kind:
                    raise PacketInvalid("identifier replacement changes entity kind")
                if replacement.entity_id in donor_identifiers or replacement.entity_id in {
                    donor_task_id,
                    task_id,
                }:
                    raise PacketInvalid("identifier replacement is not focal-safe")
                rewritten.append(replacement)
                rewrite_completed += 1
            else:
                leaked = [
                    identifier
                    for identifier in donor_identifiers | {donor_task_id}
                    if identifier and identifier in atom.text
                ]
                literal_collisions.extend(leaked)
                rewritten.append(atom)
        normalized_sham.append(
            VerifierFinding(
                finding_id=focal_finding.finding_id,
                component=donor_finding.component,
                code=donor_finding.code,
                severity=focal_finding.severity,
                atoms=tuple(rewritten),
            )
        )
    if unmapped or literal_collisions or rewrite_completed != rewrite_expected:
        raise PacketInvalid("donor identifiers are unmapped or leak through literals")

    bounded_real: list[VerifierFinding] = []
    bounded_sham: list[VerifierFinding] = []
    truncations: list[TruncationReceipt] = []
    per_finding_budget = max(1, policy.max_evidence_tokens // retained_count)
    for real_finding, sham_finding in zip(focal, normalized_sham, strict=True):
        real_atoms, real_receipt = _bound_atoms(
            real_finding,
            tokenizer=tokenizer,
            budget=per_finding_budget,
        )
        sham_atoms, sham_receipt = _bound_atoms(
            sham_finding,
            tokenizer=tokenizer,
            budget=per_finding_budget,
        )
        bounded_real.append(
            VerifierFinding(
                real_finding.finding_id,
                real_finding.component,
                real_finding.code,
                real_finding.severity,
                real_atoms,
            )
        )
        bounded_sham.append(
            VerifierFinding(
                sham_finding.finding_id,
                sham_finding.component,
                sham_finding.code,
                sham_finding.severity,
                sham_atoms,
            )
        )
        truncations.extend((real_receipt, sham_receipt))

    sham_signatures = {
        hashlib.sha256(
            canonical_json_bytes(
                {
                    "atoms": _atoms_text(finding.atoms),
                    "code": finding.code,
                    "component": finding.component,
                    "severity": finding.severity,
                },
                indent=None,
            )
        ).hexdigest()
        for finding in bounded_sham
    }
    if sham_signatures & true_focal_signatures:
        raise PacketInvalid("SHAM evidence collides with a true focal finding")

    real_text = _render(bounded_real, "")
    sham_text = _render(bounded_sham, "")
    real_count = len(tokenizer.encode(real_text))
    sham_count = len(tokenizer.encode(sham_text))
    target = max(real_count, sham_count)
    if real_count < target:
        padding, padding_receipt = _padding_search(
            bounded_real,
            tokenizer=tokenizer,
            target=target,
            neutral_pad_units=units,
        )
        real_text = _render(bounded_real, padding)
    elif sham_count < target:
        padding, padding_receipt = _padding_search(
            bounded_sham,
            tokenizer=tokenizer,
            target=target,
            neutral_pad_units=units,
        )
        sham_text = _render(bounded_sham, padding)
    else:
        padding_receipt = PaddingSearchReceipt(
            pad_unit_set_sha256=hashlib.sha256(
                canonical_json_bytes(list(units), indent=None)
            ).hexdigest(),
            target_token_count=target,
            states_explored=1,
            selected_unit_counts=tuple((unit, 0) for unit in units),
            search_algorithm="exact_dynamic_program_v1",
        )
    real_count = len(tokenizer.encode(real_text))
    sham_count = len(tokenizer.encode(sham_text))
    if real_count != sham_count:
        raise PacketInvalid("exact REAL/SHAM token parity is unreachable")
    forbidden = donor_identifiers | {donor_task_id}
    if any(identifier and (identifier in real_text or identifier in sham_text) for identifier in forbidden):
        raise PacketInvalid("packet text contains donor identity")

    real_ref = artifact_store.put_text(
        real_relative_path,
        real_text,
        role="private_guidance",
    )
    sham_ref = artifact_store.put_text(
        sham_relative_path,
        sham_text,
        role="private_guidance",
    )
    severity_multiset = tuple(sorted(finding.severity for finding in bounded_real))
    return PacketPairReceipt(
        task_id=task_id,
        donor_task_id=donor_task_id,
        prefix_index_sha256=prefix_index_sha256,
        real_ref=real_ref,
        sham_ref=sham_ref,
        real_token_count=real_count,
        sham_token_count=sham_count,
        focal_verifier_ref=focal_verifier_ref,
        donor_verifier_ref=donor_verifier_ref,
        assignment_ref=assignment_ref,
        identifier_map_ref=identifier_map_ref,
        tokenizer_ref=tokenizer_ref,
        packet_template_ref=packet_template_ref,
        normalized_real_ref=real_ref,
        normalized_sham_ref=sham_ref,
        packet_policy_ref=packet_policy_ref,
        pad_unit_set_ref=pad_unit_set_ref,
        padding_search=padding_receipt,
        field_order=_FIELD_ORDER,
        severity_multiset=severity_multiset,
        schema_parity=True,
        field_parity=True,
        severity_parity=True,
        focal_collision_count=0,
        rewrite_expected=rewrite_expected,
        rewrite_completed=rewrite_completed,
        unmapped_identifiers=(),
        donor_literal_collisions=(),
        truncation_receipts=tuple(truncations),
    )
