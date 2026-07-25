"""Donor assignment, leakage audit, and the judge-free manipulation check.

Design source: ``docs/research/neurips-2026-workshop/25-placebo-selfreport-design.md``,
section 6 items 6 and 7.

Four commitments are enforced here rather than documented and hoped for:

1. **One independent derangement per seed, never a self-donation.** The
   derangement is drawn from a seed-salted PRNG, so two seeds produce mappings
   that are independent rather than nudged copies of each other. A mapping with
   a fixed point is not returned under any code path.

2. **Selection sees task text only.** :class:`SelectionTarget` has ``__slots__``
   carrying a problem id and a task string, and nothing else. The selection
   functions refuse any other type. A target's generated output, its reflection,
   and its grade are not representable in the input, so selection cannot depend
   on them even by mistake.

3. **Leakage is audited before assignment, and exclusions apply to ALL arms.**
   Any donor sharing an 8-gram or longer with the target's reference solution is
   excluded everywhere -- not merely from the arm where the overlap was noticed
   -- because a donor present in some arms and absent from others breaks the
   matched design.

4. **The manipulation check is deterministic.** TF-IDF cosine and identifier
   Jaccard overlap. **There is no LLM judge in this module and there must never
   be one**: the paper's central methodological criticism is that judge noise
   gets reported as sampling uncertainty, and a paper making that criticism
   cannot contain a judge. :data:`USES_LLM_JUDGE` is a permanent ``False`` and
   exists so the claim is testable.

The donor manifest is published so the mapping is auditable and cannot be
silently redrawn: it carries a content digest over the canonical serialization,
and :func:`verifyManifest` fails on any post-hoc edit.

Nothing in this module performs network I/O or imports a model backend.
"""

from __future__ import annotations

import hashlib
import json
import math
import random
import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Permanent. Asserted by the test suite. See the module docstring.
USES_LLM_JUDGE: bool = False

LEAKAGE_NGRAM_SIZE: int = 8
DERANGEMENT_SALT: str = "pneuma-placebo-derangement-v1"
MAX_DERANGEMENT_ATTEMPTS: int = 256

METHOD_UNIFORM: str = "uniform_random"
METHOD_TFIDF_MATCHED: str = "tfidf_matched"

MANIFEST_SCHEMA_VERSION: str = "placebo-donor-manifest-v1"
MANIFEST_DIGEST_FIELD: str = "content_digest"

MANIPULATION_METHOD: str = "tfidf_cosine+identifier_jaccard"
TASK_BLIND_SIMILARITY_CEILING: float = 0.10
DONOR_SIMILARITY_MARGIN: float = 0.02

VERDICT_TASK_BLIND: str = "task-blind-confirmed"
VERDICT_DONOR_CONTENT: str = "donor-content-confirmed"
VERDICT_TARGET_CONTENT: str = "target-content-confirmed"
VERDICT_AMBIGUOUS: str = "ambiguous"

TEXT_TOKEN_PATTERN = re.compile(r"[a-z0-9_]+")
CODE_TOKEN_PATTERN = re.compile(r"[A-Za-z_][A-Za-z0-9_]*|\d+|[^\sA-Za-z0-9_]")
IDENTIFIER_PATTERN = re.compile(r"[A-Za-z_][A-Za-z0-9_]{2,}")

# Identifier-overlap noise floor. Deliberately short and fixed: a longer,
# tuned stoplist would become a free parameter of the manipulation check.
IDENTIFIER_STOPWORDS: frozenset[str] = frozenset(
    {
        "and",
        "def",
        "else",
        "for",
        "not",
        "return",
        "the",
        "this",
        "with",
    }
)

# English function words, dropped before TF-IDF. Fixed and short by policy: a
# tuned stoplist would become a free parameter of the manipulation check. Their
# removal matters most on the small per-item corpora the check runs on, where a
# shared "the" would otherwise carry a large IDF weight and manufacture
# similarity between two unrelated strings.
TEXT_STOPWORDS: frozenset[str] = frozenset(
    {
        "a",
        "an",
        "and",
        "any",
        "are",
        "as",
        "at",
        "be",
        "but",
        "by",
        "each",
        "for",
        "from",
        "has",
        "have",
        "if",
        "in",
        "into",
        "is",
        "it",
        "its",
        "of",
        "on",
        "or",
        "so",
        "than",
        "that",
        "the",
        "their",
        "then",
        "there",
        "these",
        "they",
        "this",
        "to",
        "was",
        "were",
        "when",
        "which",
        "will",
        "with",
        "you",
        "your",
    }
)


# ---------------------------------------------------------------------------
# Structurally narrowed inputs
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class SelectionTarget:
    """Everything donor selection may see about a target. Nothing else.

    ``__slots__`` makes it impossible to attach the target's generated output,
    its reflection, or its grade. Selection that cannot see an outcome cannot be
    tuned on one.
    """

    problem_id: str
    task_text: str

    def __post_init__(self) -> None:
        if not self.problem_id:
            raise ValueError("problem_id must be non-empty")
        if not isinstance(self.task_text, str):
            raise TypeError("task_text must be a string of task text only")


@dataclass(frozen=True, slots=True)
class DonorCandidate:
    """A donor as the selector and the leakage audit see it.

    ``payload_material`` is the text that would actually be injected for this
    donor -- a reflection for family R, an exemplar for family M. The leakage
    audit scans it together with the task text, because either can carry a
    solution fragment.
    """

    problem_id: str
    task_text: str
    payload_material: str = ""

    def scannableText(self) -> str:
        return f"{self.task_text}\n{self.payload_material}"


@dataclass(frozen=True, slots=True)
class LeakageTarget:
    """A target as the leakage audit sees it: an id and a reference solution.

    Deliberately a different type from :class:`SelectionTarget`. The audit needs
    the reference solution; selection must never receive it. Keeping them apart
    means no single object grants both capabilities.
    """

    problem_id: str
    reference_solution: str


def toSelectionTarget(problem_id: str, task_text: str) -> SelectionTarget:
    """Narrow arbitrary task metadata down to what selection is allowed to read."""
    return SelectionTarget(problem_id=problem_id, task_text=task_text)


def _requireSelectionTarget(target: object) -> SelectionTarget:
    if not isinstance(target, SelectionTarget):
        raise TypeError(
            "donor selection accepts SelectionTarget only; got "
            f"{type(target).__name__}. Selection must depend on task text alone, "
            "never on the target's output, reflection, or grade."
        )
    return target


# ---------------------------------------------------------------------------
# Seeded derangement
# ---------------------------------------------------------------------------


def _seedFor(*parts: object) -> int:
    label = ":".join([DERANGEMENT_SALT, *(str(p) for p in parts)])
    return int.from_bytes(hashlib.sha256(label.encode("utf-8")).digest()[:8], "big")


def _sattoloDerangement(items: Sequence[str], rng: random.Random) -> list[str]:
    """Sattolo's algorithm: a uniformly random single-cycle permutation.

    A single cycle over two or more elements has no fixed point, so this is a
    guaranteed derangement. It is the fallback for the rejection sampler, which
    is uniform over *all* derangements and is preferred.
    """
    shuffled = list(items)
    for i in range(len(shuffled) - 1, 0, -1):
        j = rng.randrange(i)
        shuffled[i], shuffled[j] = shuffled[j], shuffled[i]
    return shuffled


def buildDerangement(problem_ids: Sequence[str], *, seed: int) -> dict[str, str]:
    """One derangement of ``problem_ids``, deterministic in ``seed``.

    No fixed point, ever -- verified before return, so a self-donation cannot
    escape through a fallback path. The PRNG is salted with the seed through
    SHA-256, so mappings for different seeds are independent draws rather than
    correlated perturbations of one another.
    """
    ids = list(problem_ids)
    if len(ids) < 2:
        raise ValueError(
            f"a derangement needs at least 2 problems, got {len(ids)}: with one "
            f"problem every assignment is a self-donation"
        )
    if len(set(ids)) != len(ids):
        raise ValueError("problem_ids must be unique")

    rng = random.Random(_seedFor("derangement", seed))
    shuffled: list[str] | None = None
    for _ in range(MAX_DERANGEMENT_ATTEMPTS):
        candidate = list(ids)
        rng.shuffle(candidate)
        if all(a != b for a, b in zip(ids, candidate)):
            shuffled = candidate
            break
    if shuffled is None:
        shuffled = _sattoloDerangement(ids, rng)

    mapping = dict(zip(ids, shuffled))
    for target, donor in mapping.items():
        if target == donor:
            raise AssertionError(f"self-donation produced for {target!r}")
    return mapping


# ---------------------------------------------------------------------------
# TF-IDF over task text
# ---------------------------------------------------------------------------


def textTokens(text: str) -> list[str]:
    """Lowercased content tokens: length >= 2 and not an English function word."""
    return [
        t
        for t in TEXT_TOKEN_PATTERN.findall(text.lower())
        if len(t) >= 2 and t not in TEXT_STOPWORDS
    ]


@dataclass(frozen=True)
class TfIdfIndex:
    """A fitted TF-IDF space over task text. Deterministic, dependency-free."""

    idf: dict[str, float]
    vectors: dict[str, dict[str, float]]

    def vectorFor(self, text: str) -> dict[str, float]:
        counts: dict[str, float] = {}
        for token in textTokens(text):
            if token in self.idf:
                counts[token] = counts.get(token, 0.0) + 1.0
        weighted = {t: c * self.idf[t] for t, c in counts.items()}
        return _l2Normalize(weighted)


def _l2Normalize(vector: Mapping[str, float]) -> dict[str, float]:
    norm = math.sqrt(sum(v * v for v in vector.values()))
    if norm == 0.0:
        return {}
    return {k: v / norm for k, v in vector.items()}


def buildTfIdfIndex(documents: Mapping[str, str]) -> TfIdfIndex:
    """Smoothed TF-IDF: ``idf = ln((1 + N) / (1 + df)) + 1``, L2-normalized."""
    tokenized = {doc_id: textTokens(text) for doc_id, text in documents.items()}
    n_docs = len(tokenized)
    document_frequency: dict[str, int] = {}
    for tokens in tokenized.values():
        for token in set(tokens):
            document_frequency[token] = document_frequency.get(token, 0) + 1
    idf = {
        token: math.log((1 + n_docs) / (1 + df)) + 1.0
        for token, df in document_frequency.items()
    }
    vectors: dict[str, dict[str, float]] = {}
    for doc_id, tokens in tokenized.items():
        counts: dict[str, float] = {}
        for token in tokens:
            counts[token] = counts.get(token, 0.0) + 1.0
        vectors[doc_id] = _l2Normalize({t: c * idf[t] for t, c in counts.items()})
    return TfIdfIndex(idf=idf, vectors=vectors)


def cosineSimilarity(a: Mapping[str, float], b: Mapping[str, float]) -> float:
    if len(a) > len(b):
        a, b = b, a
    return sum(weight * b.get(token, 0.0) for token, weight in a.items())


# ---------------------------------------------------------------------------
# Donor selection
# ---------------------------------------------------------------------------


def selectUniformDonor(
    target: object,
    candidates: Sequence[SelectionTarget],
    *,
    seed: int,
    excluded_ids: Iterable[str] = (),
) -> str:
    """Uniform-random donor for one target. Never the target itself."""
    selection_target = _requireSelectionTarget(target)
    banned = set(excluded_ids) | {selection_target.problem_id}
    pool = sorted(
        c.problem_id
        for c in candidates
        if _requireSelectionTarget(c).problem_id not in banned
    )
    if not pool:
        raise ValueError(
            f"no admissible donor for {selection_target.problem_id!r}: the pool is "
            f"empty after removing self-donation and leakage exclusions"
        )
    rng = random.Random(_seedFor("uniform", seed, selection_target.problem_id))
    return pool[rng.randrange(len(pool))]


def rankMatchedDonors(
    target: object,
    candidates: Sequence[SelectionTarget],
    *,
    index: TfIdfIndex | None = None,
    excluded_ids: Iterable[str] = (),
) -> tuple[tuple[str, float], ...]:
    """Rank candidate donors by TF-IDF cosine over TASK TEXT ONLY.

    Ties break on ``problem_id`` so the ranking is total and reproducible.
    """
    selection_target = _requireSelectionTarget(target)
    banned = set(excluded_ids) | {selection_target.problem_id}
    pool = [
        c for c in candidates if _requireSelectionTarget(c).problem_id not in banned
    ]
    if index is None:
        documents = {c.problem_id: c.task_text for c in candidates}
        documents[selection_target.problem_id] = selection_target.task_text
        index = buildTfIdfIndex(documents)
    target_vector = index.vectorFor(selection_target.task_text)
    scored = [
        (c.problem_id, cosineSimilarity(target_vector, index.vectorFor(c.task_text)))
        for c in pool
    ]
    scored.sort(key=lambda pair: (-pair[1], pair[0]))
    return tuple(scored)


def selectMatchedDonor(
    target: object,
    candidates: Sequence[SelectionTarget],
    *,
    index: TfIdfIndex | None = None,
    excluded_ids: Iterable[str] = (),
) -> str:
    """The TF-IDF nearest admissible *other* problem, on task text alone."""
    ranked = rankMatchedDonors(
        target, candidates, index=index, excluded_ids=excluded_ids
    )
    if not ranked:
        raise ValueError(
            f"no admissible donor for {_requireSelectionTarget(target).problem_id!r}"
        )
    return ranked[0][0]


@dataclass(frozen=True)
class DonorAssignment:
    """A full roster assignment for one seed and one arm."""

    seed: int
    method: str
    mapping: dict[str, str]
    unassigned: tuple[str, ...] = ()
    excluded_pairs: tuple[tuple[str, str], ...] = ()

    def assertNoSelfDonation(self) -> None:
        offenders = sorted(t for t, d in self.mapping.items() if t == d)
        if offenders:
            raise AssertionError(f"self-donation in assignment: {offenders}")


def _repairAgainstExclusions(
    mapping: dict[str, str],
    banned: set[tuple[str, str]],
) -> tuple[dict[str, str], list[str]]:
    """Swap donors deterministically until no banned pair remains.

    Swapping preserves the derangement property (both post-swap pairs are
    checked for self-donation) and touches only violating targets, so the draw
    stays a function of the seed plus the published exclusion list rather than
    of the analyst.
    """
    repaired = dict(mapping)
    unassigned: list[str] = []
    ids = sorted(repaired)
    for target in ids:
        if (target, repaired.get(target)) not in banned:
            continue
        swapped = False
        for other in ids:
            if other == target or other not in repaired:
                continue
            donor_t = repaired[target]
            donor_o = repaired[other]
            if donor_o == target or donor_t == other:
                continue
            if (target, donor_o) in banned or (other, donor_t) in banned:
                continue
            repaired[target], repaired[other] = donor_o, donor_t
            swapped = True
            break
        if not swapped:
            repaired.pop(target, None)
            unassigned.append(target)
    return repaired, unassigned


def assignDonorsUniform(
    targets: Sequence[SelectionTarget],
    *,
    seed: int,
    excluded_pairs: Iterable[tuple[str, str]] = (),
) -> DonorAssignment:
    """Roster-wide uniform assignment: one independent derangement per seed."""
    ids = [_requireSelectionTarget(t).problem_id for t in targets]
    mapping = buildDerangement(ids, seed=seed)
    banned = {(t, d) for t, d in excluded_pairs}
    mapping, unassigned = _repairAgainstExclusions(mapping, banned)
    assignment = DonorAssignment(
        seed=seed,
        method=METHOD_UNIFORM,
        mapping=mapping,
        unassigned=tuple(unassigned),
        excluded_pairs=tuple(sorted(banned)),
    )
    assignment.assertNoSelfDonation()
    return assignment


def assignDonorsMatched(
    targets: Sequence[SelectionTarget],
    *,
    seed: int,
    candidates: Sequence[SelectionTarget] | None = None,
    excluded_pairs: Iterable[tuple[str, str]] = (),
) -> DonorAssignment:
    """Roster-wide TF-IDF-matched assignment on task text only.

    Unlike the uniform arm this is not a derangement: nearest-neighbour
    matching may hand the same donor to several targets, which is what
    "the nearest other failed problem" means. Self-donation remains impossible.
    """
    pool = list(candidates) if candidates is not None else list(targets)
    for candidate in pool:
        _requireSelectionTarget(candidate)
    banned = {(t, d) for t, d in excluded_pairs}
    documents = {t.problem_id: t.task_text for t in pool}
    for target in targets:
        documents.setdefault(
            _requireSelectionTarget(target).problem_id, target.task_text
        )
    index = buildTfIdfIndex(documents)

    mapping: dict[str, str] = {}
    unassigned: list[str] = []
    for target in sorted(targets, key=lambda t: t.problem_id):
        excluded = {d for (t, d) in banned if t == target.problem_id}
        ranked = rankMatchedDonors(target, pool, index=index, excluded_ids=excluded)
        if not ranked:
            unassigned.append(target.problem_id)
            continue
        mapping[target.problem_id] = ranked[0][0]
    assignment = DonorAssignment(
        seed=seed,
        method=METHOD_TFIDF_MATCHED,
        mapping=mapping,
        unassigned=tuple(unassigned),
        excluded_pairs=tuple(sorted(banned)),
    )
    assignment.assertNoSelfDonation()
    return assignment


# ---------------------------------------------------------------------------
# Leakage audit
# ---------------------------------------------------------------------------


def normalizeCodeTokens(text: str) -> tuple[str, ...]:
    """Whitespace-insensitive code token sequence, operators retained.

    Operators are kept because a solution fragment reproduced with different
    spacing is still the solution, while a fragment that shares only identifier
    names is much weaker evidence.
    """
    return tuple(CODE_TOKEN_PATTERN.findall(text))


def extractNgrams(text: str, n: int = LEAKAGE_NGRAM_SIZE) -> set[tuple[str, ...]]:
    if n < 1:
        raise ValueError(f"ngram size must be >= 1, got {n}")
    tokens = normalizeCodeTokens(text)
    if len(tokens) < n:
        return set()
    return {tuple(tokens[i : i + n]) for i in range(len(tokens) - n + 1)}


def findSharedNgrams(
    left: str, right: str, n: int = LEAKAGE_NGRAM_SIZE
) -> set[tuple[str, ...]]:
    return extractNgrams(left, n) & extractNgrams(right, n)


@dataclass(frozen=True)
class LeakageFinding:
    target_id: str
    donor_id: str
    ngram_size: int
    shared_ngram_count: int
    example_ngram: tuple[str, ...]


@dataclass(frozen=True)
class LeakageAuditRecord:
    """Result of the pre-assignment leakage scan.

    ``excluded_pairs`` is consumed by every arm. A donor excluded for one arm
    and admitted for another would break the matched design, so exclusion is
    global by construction rather than by discipline.
    """

    ngram_size: int
    scanned_pairs: int
    findings: tuple[LeakageFinding, ...]
    excluded_pairs: tuple[tuple[str, str], ...]

    def isExcluded(self, target_id: str, donor_id: str) -> bool:
        return (target_id, donor_id) in set(self.excluded_pairs)

    def excludedDonorsFor(self, target_id: str) -> tuple[str, ...]:
        return tuple(sorted(d for t, d in self.excluded_pairs if t == target_id))


def auditLeakage(
    targets: Sequence[LeakageTarget],
    candidates: Sequence[DonorCandidate],
    *,
    ngram_size: int = LEAKAGE_NGRAM_SIZE,
) -> LeakageAuditRecord:
    """Exclude, from ALL arms, any donor sharing an n-gram with the reference solution.

    The comparison runs over the donor's task text *and* its payload material,
    since either can quote a solution. Self-pairs are excluded unconditionally:
    a target trivially shares every n-gram with its own solution, and no arm may
    self-donate anyway.
    """
    findings: list[LeakageFinding] = []
    excluded: set[tuple[str, str]] = set()
    scanned = 0
    solution_ngrams = {
        t.problem_id: extractNgrams(t.reference_solution, ngram_size) for t in targets
    }
    for target in targets:
        reference = solution_ngrams[target.problem_id]
        for candidate in candidates:
            if candidate.problem_id == target.problem_id:
                excluded.add((target.problem_id, candidate.problem_id))
                continue
            scanned += 1
            if not reference:
                continue
            shared = reference & extractNgrams(candidate.scannableText(), ngram_size)
            if not shared:
                continue
            example = sorted(shared)[0]
            findings.append(
                LeakageFinding(
                    target_id=target.problem_id,
                    donor_id=candidate.problem_id,
                    ngram_size=ngram_size,
                    shared_ngram_count=len(shared),
                    example_ngram=example,
                )
            )
            excluded.add((target.problem_id, candidate.problem_id))
    return LeakageAuditRecord(
        ngram_size=ngram_size,
        scanned_pairs=scanned,
        findings=tuple(sorted(findings, key=lambda f: (f.target_id, f.donor_id))),
        excluded_pairs=tuple(sorted(excluded)),
    )


# ---------------------------------------------------------------------------
# Manipulation check -- deterministic, judge-free
# ---------------------------------------------------------------------------


def extractIdentifiers(text: str) -> set[str]:
    return {
        m.lower()
        for m in IDENTIFIER_PATTERN.findall(text)
        if m.lower() not in IDENTIFIER_STOPWORDS
    }


def jaccard(left: set[str], right: set[str]) -> float:
    if not left and not right:
        return 0.0
    union = left | right
    if not union:
        return 0.0
    return len(left & right) / len(union)


@dataclass(frozen=True)
class ManipulationCheckRecord:
    """Did the payload actually carry the content the arm claims?

    Deterministic by construction. ``uses_llm_judge`` is a permanent ``False``
    and is serialized into the record so a downstream reader can confirm that
    no judge noise entered the estimate.
    """

    method: str
    uses_llm_judge: bool
    payload_vs_target_tfidf: float
    payload_vs_donor_tfidf: float
    payload_vs_target_identifiers: float
    payload_vs_donor_identifiers: float
    verdict: str
    expectation: str
    consistent_with_expectation: bool


def manipulationCheck(
    payload_text: str,
    *,
    target_task_text: str,
    donor_task_text: str | None = None,
    expectation: str,
    corpus: Mapping[str, str] | None = None,
    similarity_ceiling: float = TASK_BLIND_SIMILARITY_CEILING,
    margin: float = DONOR_SIMILARITY_MARGIN,
) -> ManipulationCheckRecord:
    """Verify the payload's content provenance without an LLM judge.

    ``expectation`` is one of ``"task_blind"``, ``"donor"``, or ``"target"`` --
    what the arm's construction says the payload should resemble. The record
    reports both similarities and whether they are consistent with that
    expectation, so a broken injection path shows up as a manipulation-check
    failure rather than as an inexplicably null contrast.

    ``corpus`` supplies the document collection the IDF weights are fitted on.
    Pass the study roster's task texts when running the check for real: IDF
    estimated from three short strings is noisy, and the defaults are the
    per-item fallback rather than the intended configuration.
    """
    if expectation not in {"task_blind", "donor", "target"}:
        raise ValueError(f"unknown expectation {expectation!r}")
    documents = dict(corpus) if corpus is not None else {}
    documents["payload"] = payload_text
    documents.setdefault("target", target_task_text)
    if donor_task_text is not None:
        documents.setdefault("donor", donor_task_text)
    index = buildTfIdfIndex(documents)
    payload_vector = index.vectorFor(payload_text)
    target_similarity = cosineSimilarity(
        payload_vector, index.vectorFor(target_task_text)
    )
    donor_similarity = (
        cosineSimilarity(payload_vector, index.vectorFor(donor_task_text))
        if donor_task_text is not None
        else 0.0
    )
    payload_identifiers = extractIdentifiers(payload_text)
    target_overlap = jaccard(payload_identifiers, extractIdentifiers(target_task_text))
    donor_overlap = (
        jaccard(payload_identifiers, extractIdentifiers(donor_task_text))
        if donor_task_text is not None
        else 0.0
    )

    if (
        target_similarity <= similarity_ceiling
        and donor_similarity <= similarity_ceiling
    ):
        verdict = VERDICT_TASK_BLIND
    elif donor_similarity > target_similarity + margin:
        verdict = VERDICT_DONOR_CONTENT
    elif target_similarity > donor_similarity + margin:
        verdict = VERDICT_TARGET_CONTENT
    else:
        verdict = VERDICT_AMBIGUOUS

    expected_verdict = {
        "task_blind": VERDICT_TASK_BLIND,
        "donor": VERDICT_DONOR_CONTENT,
        "target": VERDICT_TARGET_CONTENT,
    }[expectation]
    return ManipulationCheckRecord(
        method=MANIPULATION_METHOD,
        uses_llm_judge=USES_LLM_JUDGE,
        payload_vs_target_tfidf=target_similarity,
        payload_vs_donor_tfidf=donor_similarity,
        payload_vs_target_identifiers=target_overlap,
        payload_vs_donor_identifiers=donor_overlap,
        verdict=verdict,
        expectation=expectation,
        consistent_with_expectation=verdict == expected_verdict,
    )


# ---------------------------------------------------------------------------
# Published donor manifest
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DonorManifest:
    """The published donor mapping. Digest-sealed so it cannot be redrawn quietly."""

    schema_version: str
    arm: str
    seed: int
    method: str
    mapping: dict[str, str]
    unassigned: tuple[str, ...] = ()
    excluded_pairs: tuple[tuple[str, str], ...] = ()
    ngram_size: int = LEAKAGE_NGRAM_SIZE
    leakage_findings: tuple[dict[str, object], ...] = ()
    notes: str = ""

    def toDict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "arm": self.arm,
            "seed": self.seed,
            "method": self.method,
            "mapping": dict(sorted(self.mapping.items())),
            "unassigned": sorted(self.unassigned),
            "excluded_pairs": [list(pair) for pair in sorted(self.excluded_pairs)],
            "ngram_size": self.ngram_size,
            "leakage_findings": [
                dict(sorted(finding.items())) for finding in self.leakage_findings
            ],
            "uses_llm_judge": USES_LLM_JUDGE,
            "notes": self.notes,
        }

    def digest(self) -> str:
        canonical = json.dumps(
            self.toDict(), sort_keys=True, separators=(",", ":"), ensure_ascii=True
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def buildDonorManifest(
    assignment: DonorAssignment,
    *,
    arm: str,
    audit: LeakageAuditRecord | None = None,
    notes: str = "",
) -> DonorManifest:
    findings: tuple[dict[str, object], ...] = ()
    ngram_size = LEAKAGE_NGRAM_SIZE
    if audit is not None:
        ngram_size = audit.ngram_size
        findings = tuple(
            {
                "target_id": f.target_id,
                "donor_id": f.donor_id,
                "ngram_size": f.ngram_size,
                "shared_ngram_count": f.shared_ngram_count,
                "example_ngram": " ".join(f.example_ngram),
            }
            for f in audit.findings
        )
    return DonorManifest(
        schema_version=MANIFEST_SCHEMA_VERSION,
        arm=arm,
        seed=assignment.seed,
        method=assignment.method,
        mapping=dict(assignment.mapping),
        unassigned=tuple(assignment.unassigned),
        excluded_pairs=tuple(assignment.excluded_pairs),
        ngram_size=ngram_size,
        leakage_findings=findings,
        notes=notes,
    )


def writeDonorManifest(manifest: DonorManifest, path: str | Path) -> str:
    """Write the manifest with its digest attached. Returns the digest."""
    payload = manifest.toDict()
    digest = manifest.digest()
    payload[MANIFEST_DIGEST_FIELD] = digest
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(payload, indent=4, sort_keys=True) + "\n", encoding="utf-8"
    )
    return digest


def loadDonorManifest(path: str | Path) -> tuple[DonorManifest, str]:
    """Load a published manifest and the digest recorded alongside it."""
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    recorded = payload.get(MANIFEST_DIGEST_FIELD, "")
    manifest = DonorManifest(
        schema_version=payload["schema_version"],
        arm=payload["arm"],
        seed=payload["seed"],
        method=payload["method"],
        mapping=dict(payload["mapping"]),
        unassigned=tuple(payload.get("unassigned", ())),
        excluded_pairs=tuple(tuple(pair) for pair in payload.get("excluded_pairs", ())),
        ngram_size=payload.get("ngram_size", LEAKAGE_NGRAM_SIZE),
        leakage_findings=tuple(payload.get("leakage_findings", ())),
        notes=payload.get("notes", ""),
    )
    return manifest, recorded


def verifyDonorManifest(manifest: DonorManifest, expected_digest: str) -> bool:
    """True only if the mapping is byte-for-byte the one that was published."""
    return manifest.digest() == expected_digest
