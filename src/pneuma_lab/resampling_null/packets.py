"""Token-exact REAL/SHAM verifier-packet construction."""

from __future__ import annotations

from collections.abc import Collection, Mapping, Sequence
from dataclasses import asdict, dataclass
from enum import Enum
import hashlib
import json
from pathlib import Path
import re
from typing import Literal, Protocol, cast

from pneuma_lab.foundation.artifacts import canonical_json_bytes, write_atomic_bytes

from .artifacts import RecordValidationError, load_record, write_record
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
class PacketAuthority:
    tokenizer: Tokenizer
    policy: PacketPolicy
    neutral_pad_units: tuple[str, ...]
    field_order: tuple[str, ...]
    tokenizer_ref: ArtifactRef
    packet_template_ref: ArtifactRef
    packet_policy_ref: ArtifactRef
    pad_unit_set_ref: ArtifactRef


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
    normalized_donor_ref: ArtifactRef
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


@dataclass(frozen=True, slots=True)
class PacketRewriteArtifacts:
    identifier_map_ref: ArtifactRef
    normalized_sham_ref: ArtifactRef
    rewrite_count: int


@dataclass(frozen=True, slots=True)
class NoInterventionPacketMarker:
    task_id: str
    prefix_index_sha256: str
    trigger_reason: Literal["no_intervention_opportunity"]

    def __post_init__(self) -> None:
        if type(self.task_id) is not str or not self.task_id:
            raise ValueError("task_id must be non-empty exact text")
        if not re.fullmatch(r"[0-9a-f]{64}", self.prefix_index_sha256):
            raise ValueError("prefix_index_sha256 must be lowercase SHA-256")
        if self.trigger_reason != "no_intervention_opportunity":
            raise ValueError("no-intervention marker has an invalid reason")


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


def _token_count(tokenizer: Tokenizer, text: str) -> int:
    encoded = tokenizer.encode(text)
    if not isinstance(encoded, tuple) or any(
        type(token_id) is not int
        for token_id in encoded
    ):
        raise PacketInvalid(
            "tokenizer must return a tuple of exact integer token IDs"
        )
    return len(encoded)


class _UnicodeWhitespaceTokenizer:
    def encode(self, text: str) -> tuple[int, ...]:
        if type(text) is not str:
            raise TypeError("tokenizer input must be exact text")
        return tuple(
            int.from_bytes(
                hashlib.sha256(token.encode("utf-8")).digest(),
                "big",
            )
            for token in text.split()
        )


def _bound_atoms(
    finding: VerifierFinding,
    *,
    tokenizer: Tokenizer,
    budget: int,
) -> tuple[tuple[PacketAtom, ...], TruncationReceipt]:
    original_text = _atoms_text(finding.atoms)
    retained = list(finding.atoms)
    while retained and _token_count(tokenizer, _atoms_text(retained)) > budget:
        retained.pop()
    retained_text = _atoms_text(retained)
    original_tokens = _token_count(tokenizer, original_text)
    retained_tokens = _token_count(tokenizer, retained_text)
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
            token_count = _token_count(tokenizer, _render(shorter, padding))
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
    if (
        type(task_id) is not str
        or not task_id
        or type(donor_task_id) is not str
        or not donor_task_id
        or task_id == donor_task_id
    ):
        raise PacketInvalid("focal and donor task IDs must be non-empty and distinct")
    if not re.fullmatch(r"[0-9a-f]{64}", prefix_index_sha256):
        raise PacketInvalid("prefix index digest must be lowercase SHA-256")
    if (
        type(real_relative_path) is not str
        or not real_relative_path
        or type(sham_relative_path) is not str
        or not sham_relative_path
        or real_relative_path == sham_relative_path
    ):
        raise PacketInvalid("REAL and SHAM artifact paths must be non-empty and distinct")
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
    real_count = _token_count(tokenizer, real_text)
    sham_count = _token_count(tokenizer, sham_text)
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
    real_count = _token_count(tokenizer, real_text)
    sham_count = _token_count(tokenizer, sham_text)
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
    if (
        real_ref == sham_ref
        or real_ref.relative_path != real_relative_path
        or sham_ref.relative_path != sham_relative_path
        or real_ref.role != "private_guidance"
        or sham_ref.role != "private_guidance"
    ):
        raise PacketInvalid("artifact store did not preserve distinct packet identity")
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
        normalized_donor_ref=donor_verifier_ref,
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


def _require_parent_record(
    ref: ArtifactRef,
    *,
    run_root: Path,
    expected_kind: str,
) -> dict[str, object]:
    root = Path(run_root).resolve(strict=True)
    path = (root / ref.relative_path).resolve(strict=True)
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise RecordValidationError("packet parent escapes run_root") from exc
    payload = path.read_bytes()
    if (
        len(payload) != ref.byte_count
        or hashlib.sha256(payload).hexdigest() != ref.sha256
    ):
        raise RecordValidationError("packet parent bytes do not match ArtifactRef")
    record = load_record(path)
    if record.get("record_kind") != expected_kind:
        raise RecordValidationError(
            f"packet parent must be {expected_kind}"
        )
    return record


def _candidate_entry(entry: PacketPairReceipt | NoInterventionPacketMarker) -> dict[str, object]:
    return cast(dict[str, object], asdict(entry))


def write_packet_candidate(
    entries: Sequence[PacketPairReceipt | NoInterventionPacketMarker],
    *,
    assignment_ref: ArtifactRef,
    prefix_index_ref: ArtifactRef,
    tokenizer_ref: ArtifactRef,
    packet_template_ref: ArtifactRef,
    packet_policy_ref: ArtifactRef,
    pad_unit_set_ref: ArtifactRef,
    run_root: Path,
    out: Path,
) -> ArtifactRef:
    """Publish an immutable candidate index; it is not execution authority."""

    if not entries:
        raise PacketInvalid("packet candidate must cover at least one task")
    task_ids = [entry.task_id for entry in entries]
    if len(set(task_ids)) != len(task_ids):
        raise PacketInvalid("packet candidate task IDs must be unique")
    assignment = _require_parent_record(
        assignment_ref,
        run_root=run_root,
        expected_kind="resampling_assignment_ledger",
    )
    for entry in entries:
        if entry.prefix_index_sha256 != prefix_index_ref.sha256:
            raise PacketInvalid("packet entry names a different prefix index")
        if isinstance(entry, NoInterventionPacketMarker):
            continue
        if (
            entry.assignment_ref != assignment_ref
            or entry.tokenizer_ref != tokenizer_ref
            or entry.packet_template_ref != packet_template_ref
            or entry.packet_policy_ref != packet_policy_ref
            or entry.pad_unit_set_ref != pad_unit_set_ref
        ):
            raise PacketInvalid("packet pair ancestry differs from candidate parents")
        if (
            entry.real_token_count != entry.sham_token_count
            or not entry.schema_parity
            or not entry.field_parity
            or not entry.severity_parity
            or entry.focal_collision_count != 0
            or entry.rewrite_expected != entry.rewrite_completed
            or entry.unmapped_identifiers
            or entry.donor_literal_collisions
        ):
            raise PacketInvalid("packet pair has an open parity or leakage gate")
    record = {
        "record_kind": "resampling_packet_index",
        "schema_version": assignment["schema_version"],
        "study_id": assignment["study_id"],
        "frozen_created_at": assignment["frozen_created_at"],
        "provenance": assignment["provenance"],
        "payload": {
            "stage": "candidate",
            "assignment_ref": asdict(assignment_ref),
            "prefix_index_ref": asdict(prefix_index_ref),
            "tokenizer_ref": asdict(tokenizer_ref),
            "packet_template_ref": asdict(packet_template_ref),
            "packet_policy_ref": asdict(packet_policy_ref),
            "pad_unit_set_ref": asdict(pad_unit_set_ref),
            "entries": [_candidate_entry(entry) for entry in entries],
        },
    }
    return write_record(
        out,
        record,
        run_root=run_root,
        role="packet_index_candidate",
    )


def _artifact_ref(value: object, *, field: str) -> ArtifactRef:
    if not isinstance(value, Mapping):
        raise PacketInvalid(f"{field} must be an ArtifactRef")
    try:
        if set(value) != {
            "role",
            "relative_path",
            "sha256",
            "byte_count",
            "media_type",
        }:
            raise ValueError("ArtifactRef keys are not closed")
        role = value["role"]
        relative_path = value["relative_path"]
        sha256 = value["sha256"]
        byte_count = value["byte_count"]
        media_type = value["media_type"]
        if (
            type(role) is not str
            or type(relative_path) is not str
            or type(sha256) is not str
            or type(byte_count) is not int
            or type(media_type) is not str
        ):
            raise TypeError("ArtifactRef fields have invalid exact types")
        return ArtifactRef(
            role,
            relative_path,
            sha256,
            byte_count,
            media_type,
        )
    except (TypeError, ValueError) as exc:
        raise PacketInvalid(f"{field} is not a valid ArtifactRef") from exc


def _require_artifact_bytes(ref: ArtifactRef, *, run_root: Path) -> bytes:
    root = Path(run_root).resolve(strict=True)
    path = (root / ref.relative_path).resolve(strict=True)
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise PacketInvalid("packet artifact escapes run_root") from exc
    payload = path.read_bytes()
    if (
        len(payload) != ref.byte_count
        or hashlib.sha256(payload).hexdigest() != ref.sha256
    ):
        raise PacketInvalid("packet artifact bytes do not match ArtifactRef")
    return payload


def _strict_json_blob(ref: ArtifactRef, *, run_root: Path) -> dict[str, object]:
    payload = _require_artifact_bytes(ref, run_root=run_root)

    def reject_duplicates(
        pairs: list[tuple[str, object]],
    ) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in pairs:
            if key in result:
                raise PacketInvalid(f"duplicate JSON key {key!r}")
            result[key] = value
        return result

    try:
        value = json.loads(
            payload.decode("utf-8", errors="strict"),
            object_pairs_hook=reject_duplicates,
            parse_constant=lambda constant: (_ for _ in ()).throw(
                PacketInvalid(f"non-finite JSON constant {constant!r}")
            ),
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PacketInvalid("packet audit source is not strict UTF-8 JSON") from exc
    if not isinstance(value, dict):
        raise PacketInvalid("packet audit source must be a JSON object")
    return cast(dict[str, object], value)


def _canonical_json_blob(
    ref: ArtifactRef,
    *,
    run_root: Path,
) -> dict[str, object]:
    value = _strict_json_blob(ref, run_root=run_root)
    if canonical_json_bytes(value, indent=None) != _require_artifact_bytes(
        ref,
        run_root=run_root,
    ):
        raise PacketInvalid("packet authority blob is not compact canonical JSON")
    return value


def load_synthetic_packet_authority(
    *,
    tokenizer_ref: ArtifactRef,
    packet_template_ref: ArtifactRef,
    packet_policy_ref: ArtifactRef,
    pad_unit_set_ref: ArtifactRef,
    run_root: Path,
) -> PacketAuthority:
    """Load one closed manifest-pinned synthetic packet configuration."""

    tokenizer_value = _canonical_json_blob(tokenizer_ref, run_root=run_root)
    if tokenizer_value != {
        "record_kind": "synthetic_report_tokenizer_v1",
        "schema_version": "1",
        "algorithm": "unicode_whitespace_v1",
    }:
        raise PacketInvalid("synthetic packet tokenizer authority is unsupported")
    template_value = _canonical_json_blob(packet_template_ref, run_root=run_root)
    if template_value != {
        "record_kind": "packet_template_v1",
        "schema_version": "1",
        "template_id": "canonical_json_private_verifier_guidance_v1",
        "guidance_record_kind": "private_verifier_guidance_v1",
        "field_order": list(_FIELD_ORDER),
    }:
        raise PacketInvalid("synthetic packet template authority is unsupported")
    policy_value = _canonical_json_blob(packet_policy_ref, run_root=run_root)
    if set(policy_value) != {
        "record_kind",
        "schema_version",
        "max_findings",
        "max_evidence_tokens",
        "normalizer_version",
    } or (
        policy_value.get("record_kind") != "packet_policy_v1"
        or policy_value.get("schema_version") != "1"
    ):
        raise PacketInvalid("synthetic packet policy authority is unsupported")
    try:
        policy = PacketPolicy(
            max_findings=cast(int, policy_value["max_findings"]),
            max_evidence_tokens=cast(
                int,
                policy_value["max_evidence_tokens"],
            ),
            normalizer_version=cast(
                str,
                policy_value["normalizer_version"],
            ),
        )
    except (TypeError, ValueError) as exc:
        raise PacketInvalid("synthetic packet policy fields are invalid") from exc
    if policy.normalizer_version != "synthetic_typed_findings_v1":
        raise PacketInvalid("packet policy names another normalizer")
    pad_value = _canonical_json_blob(pad_unit_set_ref, run_root=run_root)
    if set(pad_value) != {"record_kind", "schema_version", "units"} or (
        pad_value.get("record_kind") != "packet_pad_units_v1"
        or pad_value.get("schema_version") != "1"
        or not isinstance(pad_value.get("units"), list)
    ):
        raise PacketInvalid("synthetic pad-unit authority is unsupported")
    units = _validated_pad_units(cast(list[str], pad_value["units"]))
    if list(units) != pad_value["units"]:
        raise PacketInvalid("pad-unit authority must be sorted and duplicate-free")
    return PacketAuthority(
        tokenizer=_UnicodeWhitespaceTokenizer(),
        policy=policy,
        neutral_pad_units=units,
        field_order=_FIELD_ORDER,
        tokenizer_ref=tokenizer_ref,
        packet_template_ref=packet_template_ref,
        packet_policy_ref=packet_policy_ref,
        pad_unit_set_ref=pad_unit_set_ref,
    )


def _normalized_atom(value: object) -> PacketAtom:
    if not isinstance(value, Mapping):
        raise PacketInvalid("synthetic finding atom must be an object")
    atom_kind = value.get("atom_kind")
    if atom_kind == "literal" and set(value) == {"atom_kind", "text"}:
        return LiteralAtom(cast(str, value["text"]))
    if atom_kind == "identifier" and set(value) == {
        "atom_kind",
        "entity_id",
        "identifier_kind",
    }:
        try:
            return IdentifierAtom(
                cast(str, value["entity_id"]),
                IdentifierKind(cast(str, value["identifier_kind"])),
            )
        except (TypeError, ValueError) as exc:
            raise PacketInvalid("synthetic identifier atom is invalid") from exc
    raise PacketInvalid("synthetic finding atom has an unknown closed arm")


def _normalized_finding(value: object) -> VerifierFinding:
    if not isinstance(value, Mapping) or set(value) != {
        "finding_id",
        "component",
        "code",
        "severity",
        "atoms",
    }:
        raise PacketInvalid("synthetic objective finding is not closed")
    atoms = value["atoms"]
    if not isinstance(atoms, list) or not atoms:
        raise PacketInvalid("synthetic objective finding atoms must be non-empty")
    return VerifierFinding(
        finding_id=cast(str, value["finding_id"]),
        component=cast(str, value["component"]),
        code=cast(str, value["code"]),
        severity=cast(str, value["severity"]),
        atoms=tuple(_normalized_atom(atom) for atom in atoms),
    )


def _finding_document(finding: VerifierFinding) -> dict[str, object]:
    atoms: list[dict[str, object]] = []
    for atom in finding.atoms:
        if isinstance(atom, LiteralAtom):
            atoms.append({"atom_kind": "literal", "text": atom.text})
        else:
            atoms.append(
                {
                    "atom_kind": "identifier",
                    "entity_id": atom.entity_id,
                    "identifier_kind": atom.kind.value,
                }
            )
    return {
        "finding_id": finding.finding_id,
        "component": finding.component,
        "code": finding.code,
        "severity": finding.severity,
        "atoms": atoms,
    }


def _write_canonical_packet_blob(
    value: Mapping[str, object],
    *,
    run_root: Path,
    out: Path,
    role: str,
) -> ArtifactRef:
    root = Path(run_root).resolve(strict=True)
    target = Path(out)
    if not target.is_absolute():
        target = root / target
    target = target.resolve(strict=False)
    try:
        relative = target.relative_to(root).as_posix()
    except ValueError as exc:
        raise PacketInvalid("packet audit destination escapes run_root") from exc
    payload = canonical_json_bytes(dict(value), indent=None)
    if target.exists():
        if target.read_bytes() != payload:
            raise FileExistsError(target)
        return ArtifactRef(
            role=role,
            relative_path=relative,
            sha256=hashlib.sha256(payload).hexdigest(),
            byte_count=len(payload),
            media_type="application/json",
        )
    target.parent.mkdir(parents=True, exist_ok=True)
    write_atomic_bytes(target, payload)
    return ArtifactRef(
        role=role,
        relative_path=relative,
        sha256=hashlib.sha256(payload).hexdigest(),
        byte_count=len(payload),
        media_type="application/json",
    )


def normalize_synthetic_packet_findings(
    verifier_ref: ArtifactRef,
    *,
    task_id: str,
    run_root: Path,
    out: Path,
) -> ArtifactRef:
    """Derive canonical typed findings from one closed synthetic verifier chain."""

    if type(task_id) is not str or not task_id:
        raise PacketInvalid("normalized finding task_id must be non-empty exact text")
    features = _strict_json_blob(verifier_ref, run_root=run_root)
    if set(features) != {
        "record_kind",
        "schema_version",
        "task_id",
        "benchmark",
        "source_verifier_ref",
        "source_report_ref",
        "components",
        "objective_finding_count",
        "normalized_report_token_count",
    } or (
        features.get("record_kind") != "assignment_verifier_features_v1"
        or features.get("schema_version") != "1"
        or features.get("task_id") != task_id
    ):
        raise PacketInvalid("synthetic verifier feature parent is not closed")
    source_ref = _artifact_ref(
        features["source_verifier_ref"],
        field="source_verifier_ref",
    )
    report_ref = _artifact_ref(
        features["source_report_ref"],
        field="source_report_ref",
    )
    source = _strict_json_blob(source_ref, run_root=run_root)
    report = _strict_json_blob(report_ref, run_root=run_root)
    if set(source) != {
        "record_kind",
        "schema_version",
        "task_id",
        "benchmark",
        "components",
        "objective_findings",
    } or (
        source.get("record_kind") != "synthetic_verifier_source_v1"
        or source.get("schema_version") != "1"
        or source.get("task_id") != task_id
        or source.get("benchmark") != features.get("benchmark")
        or source.get("components") != features.get("components")
    ):
        raise PacketInvalid("synthetic source verifier is not closed or bound")
    if set(report) != {
        "record_kind",
        "schema_version",
        "task_id",
        "report_text",
    } or (
        report.get("record_kind") != "synthetic_verifier_report_v1"
        or report.get("schema_version") != "1"
        or report.get("task_id") != task_id
        or type(report.get("report_text")) is not str
        or features.get("normalized_report_token_count")
        != len(cast(str, report["report_text"]).split())
    ):
        raise PacketInvalid("synthetic source report is not closed or bound")
    raw_findings = source["objective_findings"]
    if not isinstance(raw_findings, list):
        raise PacketInvalid("synthetic objective findings must be an array")
    findings = tuple(_normalized_finding(value) for value in raw_findings)
    if (
        type(features["objective_finding_count"]) is not int
        or features["objective_finding_count"] != len(findings)
    ):
        raise PacketInvalid("synthetic objective finding count does not recompute")
    finding_ids = [finding.finding_id for finding in findings]
    if len(finding_ids) != len(set(finding_ids)):
        raise PacketInvalid("synthetic objective finding IDs repeat")
    normalized = {
        "record_kind": "packet_normalized_findings_v1",
        "schema_version": "1",
        "task_id": task_id,
        "source_verifier_ref": asdict(verifier_ref),
        "normalizer_id": "synthetic_typed_findings_v1",
        "findings": [_finding_document(finding) for finding in findings],
    }
    return _write_canonical_packet_blob(
        normalized,
        run_root=run_root,
        out=out,
        role="packet_normalized_findings",
    )


def _load_normalized_findings(
    ref: ArtifactRef,
    *,
    expected_task_id: str,
    run_root: Path,
) -> tuple[VerifierFinding, ...]:
    value = _strict_json_blob(ref, run_root=run_root)
    if set(value) != {
        "record_kind",
        "schema_version",
        "task_id",
        "source_verifier_ref",
        "normalizer_id",
        "findings",
    } or (
        value.get("record_kind") != "packet_normalized_findings_v1"
        or value.get("schema_version") != "1"
        or value.get("task_id") != expected_task_id
        or value.get("normalizer_id") != "synthetic_typed_findings_v1"
    ):
        raise PacketInvalid("normalized finding artifact is not closed or bound")
    _artifact_ref(
        value["source_verifier_ref"],
        field="normalized source_verifier_ref",
    )
    raw_findings = value["findings"]
    if not isinstance(raw_findings, list):
        raise PacketInvalid("normalized findings must be an array")
    findings = tuple(_normalized_finding(finding) for finding in raw_findings)
    finding_ids = [finding.finding_id for finding in findings]
    if len(finding_ids) != len(set(finding_ids)):
        raise PacketInvalid("normalized finding IDs repeat")
    if canonical_json_bytes(value, indent=None) != _require_artifact_bytes(
        ref,
        run_root=run_root,
    ):
        raise PacketInvalid("normalized findings are not compact canonical JSON")
    return findings


def _identifier_document(atom: IdentifierAtom) -> dict[str, str]:
    return {
        "entity_id": atom.entity_id,
        "identifier_kind": atom.kind.value,
    }


def derive_packet_rewrite_artifacts(
    identifier_map: Mapping[IdentifierAtom, IdentifierAtom],
    *,
    focal_task_id: str,
    donor_task_id: str,
    normalized_real_ref: ArtifactRef,
    normalized_donor_ref: ArtifactRef,
    run_root: Path,
    identifier_map_out: Path,
    normalized_sham_out: Path,
) -> PacketRewriteArtifacts:
    """Derive complete typed rewrite authority and normalized SHAM bytes."""

    if (
        type(focal_task_id) is not str
        or not focal_task_id
        or type(donor_task_id) is not str
        or not donor_task_id
        or focal_task_id == donor_task_id
    ):
        raise PacketInvalid("rewrite focal/donor task IDs must be distinct")
    focal = _load_normalized_findings(
        normalized_real_ref,
        expected_task_id=focal_task_id,
        run_root=run_root,
    )
    donor = _load_normalized_findings(
        normalized_donor_ref,
        expected_task_id=donor_task_id,
        run_root=run_root,
    )
    if not focal or not donor:
        raise PacketInvalid("triggered rewrite requires non-empty focal and donor findings")
    focal_identifiers = {
        atom
        for finding in focal
        for atom in finding.atoms
        if isinstance(atom, IdentifierAtom)
    }
    donor_identifiers = {
        atom
        for finding in donor
        for atom in finding.atoms
        if isinstance(atom, IdentifierAtom)
    }
    donor_identity_text = {
        donor_task_id,
        *(atom.entity_id for atom in donor_identifiers),
    }
    if any(
        identity in atom.text
        for finding in donor
        for atom in finding.atoms
        if isinstance(atom, LiteralAtom)
        for identity in donor_identity_text
        if identity
    ):
        raise PacketInvalid("donor identity leaks through a literal atom")
    if set(identifier_map) != donor_identifiers:
        raise PacketInvalid("identifier map does not exactly cover donor identifiers")
    frozen_map = dict(identifier_map)
    if len(frozen_map) != len(identifier_map):
        raise PacketInvalid("identifier map iteration is not stable")
    destinations = list(frozen_map.values())
    if (
        any(type(atom) is not IdentifierAtom for atom in destinations)
        or len(destinations) != len(set(destinations))
    ):
        raise PacketInvalid("identifier map destinations must be unique identifiers")
    for source, destination in frozen_map.items():
        if (
            type(source) is not IdentifierAtom
            or type(destination) is not IdentifierAtom
            or source.kind is not destination.kind
            or destination not in focal_identifiers
            or any(
                identity in destination.entity_id
                for identity in donor_identity_text
                if identity
            )
        ):
            raise PacketInvalid(
                "identifier map is not type-preserving and focal-derived"
            )
    ordered_map = sorted(
        frozen_map.items(),
        key=lambda pair: (
            pair[0].kind.value.encode("utf-8"),
            pair[0].entity_id.encode("utf-8"),
        ),
    )
    map_document = {
        "record_kind": "packet_identifier_map_v1",
        "schema_version": "1",
        "focal_task_id": focal_task_id,
        "donor_task_id": donor_task_id,
        "normalized_real_ref": asdict(normalized_real_ref),
        "normalized_donor_ref": asdict(normalized_donor_ref),
        "entries": [
            {
                "source": _identifier_document(source),
                "destination": _identifier_document(destination),
            }
            for source, destination in ordered_map
        ],
    }
    map_ref = _write_canonical_packet_blob(
        map_document,
        run_root=run_root,
        out=identifier_map_out,
        role="packet_identifier_map",
    )
    sham_findings: list[VerifierFinding] = []
    for focal_finding, donor_finding in zip(focal, donor, strict=False):
        rewritten_atoms = tuple(
            frozen_map[atom]
            if isinstance(atom, IdentifierAtom)
            else atom
            for atom in donor_finding.atoms
        )
        sham_findings.append(
            VerifierFinding(
                finding_id=focal_finding.finding_id,
                component=donor_finding.component,
                code=donor_finding.code,
                severity=focal_finding.severity,
                atoms=rewritten_atoms,
            )
        )
    if any(
        identity in field
        for finding in sham_findings
        for field in (
            finding.finding_id,
            finding.component,
            finding.code,
            finding.severity,
            _atoms_text(finding.atoms),
        )
        for identity in donor_identity_text
        if identity
    ):
        raise PacketInvalid("normalized SHAM retains donor identity")
    sham_document = {
        "record_kind": "packet_normalized_sham_v1",
        "schema_version": "1",
        "focal_task_id": focal_task_id,
        "donor_task_id": donor_task_id,
        "normalized_real_ref": asdict(normalized_real_ref),
        "normalized_donor_ref": asdict(normalized_donor_ref),
        "identifier_map_ref": asdict(map_ref),
        "findings": [_finding_document(finding) for finding in sham_findings],
    }
    sham_ref = _write_canonical_packet_blob(
        sham_document,
        run_root=run_root,
        out=normalized_sham_out,
        role="packet_normalized_sham",
    )
    return PacketRewriteArtifacts(
        identifier_map_ref=map_ref,
        normalized_sham_ref=sham_ref,
        rewrite_count=sum(
            isinstance(atom, IdentifierAtom)
            for finding in donor
            for atom in finding.atoms
        ),
    )


def audit_and_seal_packet_index(
    candidate_ref: ArtifactRef,
    *,
    expected_task_ids: Collection[str],
    assignment_ref: ArtifactRef,
    schedule_ref: ArtifactRef,
    prefix_index_ref: ArtifactRef,
    tokenizer_ref: ArtifactRef,
    packet_template_ref: ArtifactRef,
    packet_policy_ref: ArtifactRef,
    pad_unit_set_ref: ArtifactRef,
    run_root: Path,
    out: Path,
) -> ArtifactRef:
    """Audit candidate ancestry/bytes and publish the only execution authority."""

    candidate = _require_parent_record(
        candidate_ref,
        run_root=run_root,
        expected_kind="resampling_packet_index",
    )
    assignment = _require_parent_record(
        assignment_ref,
        run_root=run_root,
        expected_kind="resampling_assignment_ledger",
    )
    schedule = _require_parent_record(
        schedule_ref,
        run_root=run_root,
        expected_kind="resampling_prefix_schedule",
    )
    prefix = _require_parent_record(
        prefix_index_ref,
        run_root=run_root,
        expected_kind="resampling_prefix_receipt",
    )
    candidate_payload = cast(dict[str, object], candidate["payload"])
    assignment_payload = cast(dict[str, object], assignment["payload"])
    schedule_payload = cast(dict[str, object], schedule["payload"])
    prefix_payload = cast(dict[str, object], prefix["payload"])
    exact_candidate_parents = {
        "assignment_ref": assignment_ref,
        "prefix_index_ref": prefix_index_ref,
        "tokenizer_ref": tokenizer_ref,
        "packet_template_ref": packet_template_ref,
        "packet_policy_ref": packet_policy_ref,
        "pad_unit_set_ref": pad_unit_set_ref,
    }
    if candidate_payload.get("stage") != "candidate":
        raise PacketInvalid("only a candidate packet index can be sealed")
    for field, expected in exact_candidate_parents.items():
        if _artifact_ref(candidate_payload.get(field), field=field) != expected:
            raise PacketInvalid(f"candidate {field} ancestry mismatch")
    for ref in (
        tokenizer_ref,
        packet_template_ref,
        packet_policy_ref,
        pad_unit_set_ref,
    ):
        _require_artifact_bytes(ref, run_root=run_root)
    if (
        _artifact_ref(assignment_payload.get("schedule_ref"), field="schedule_ref")
        != schedule_ref
        or _artifact_ref(
            assignment_payload.get("prefix_index_ref"),
            field="prefix_index_ref",
        )
        != prefix_index_ref
        or _artifact_ref(prefix_payload.get("schedule_ref"), field="schedule_ref")
        != schedule_ref
    ):
        raise PacketInvalid("assignment/prefix chronology is not closed")
    schedule_rows = cast(list[dict[str, object]], schedule_payload["tasks"])
    schedule_task_ids = [
        cast(str, cast(dict[str, object], row["task"])["task_id"])
        for row in schedule_rows
    ]
    if isinstance(expected_task_ids, (str, bytes)) or any(
        type(task_id) is not str or not task_id
        for task_id in expected_task_ids
    ):
        raise PacketInvalid("expected task roster must contain exact task IDs")
    if len(expected_task_ids) != len(set(expected_task_ids)) or set(
        expected_task_ids
    ) != set(schedule_task_ids):
        raise PacketInvalid("expected task roster differs from sealed schedule")
    entries = cast(list[dict[str, object]], candidate_payload["entries"])
    if [cast(str, entry["task_id"]) for entry in entries] != schedule_task_ids:
        raise PacketInvalid("candidate entries do not have exact schedule coverage")
    prefix_rows = cast(list[dict[str, object]], prefix_payload["task_receipts"])
    assignments = cast(list[dict[str, object]], assignment_payload["assignments"])
    if (
        [cast(str, row["task_id"]) for row in prefix_rows] != schedule_task_ids
        or [cast(str, row["task_id"]) for row in assignments] != schedule_task_ids
    ):
        raise PacketInvalid("prefix/assignment arrays differ from schedule order")
    prefix_by_task = {
        cast(str, row["task_id"]): row
        for row in prefix_rows
    }
    assignment_by_task = {
        cast(str, row["task_id"]): row
        for row in assignments
    }
    for entry in entries:
        task_id = cast(str, entry["task_id"])
        prefix_row = prefix_by_task[task_id]
        assignment_row = assignment_by_task[task_id]
        no_trigger = (
            prefix_row["trigger_reason"] == "no_intervention_opportunity"
        )
        is_marker = "trigger_reason" in entry and "real_ref" not in entry
        if no_trigger:
            if (
                not is_marker
                or entry.get("trigger_reason")
                != "no_intervention_opportunity"
                or entry.get("prefix_index_sha256") != prefix_index_ref.sha256
                or assignment_row.get("donor_match_kind")
                != "not_applicable_no_trigger"
            ):
                raise PacketInvalid("no-trigger task lacks its exact typed marker")
            continue
        if is_marker or assignment_row.get("donor_match_kind") != "matched":
            raise PacketInvalid("triggered task lacks one matched packet pair")
        raise PacketInvalid(
            "triggered packet sealing requires the pending independent "
            "normalization/tokenizer recomputation authority"
        )
    sealed = {
        "record_kind": "resampling_packet_index",
        "schema_version": candidate["schema_version"],
        "study_id": candidate["study_id"],
        "frozen_created_at": candidate["frozen_created_at"],
        "provenance": candidate["provenance"],
        "payload": {
            "stage": "sealed",
            "candidate_ref": asdict(candidate_ref),
            **{
                field: asdict(ref)
                for field, ref in exact_candidate_parents.items()
            },
            "audit_gates": {
                "roster_complete": True,
                "ancestry_valid": True,
                "token_parity": True,
                "schema_parity": True,
                "field_parity": True,
                "severity_parity": True,
                "rewrites_complete": True,
                "identifier_collision_free": True,
                "artifact_bytes_verified": True,
            },
        },
    }
    return write_record(
        out,
        sealed,
        run_root=run_root,
        role="packet_index_sealed",
    )
