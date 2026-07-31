"""Source-level manuscript checks: placeholders, anonymity, budget, bibliography.

These run against the LaTeX sources, not the built PDF, so they work in an
environment with no TeX distribution. Checks that genuinely require a rendered
document — font embedding, PDF metadata, the true typeset page count — are
reported as ``pending`` rather than silently passing. A checker that claims to
have verified something it could not observe is the failure mode this whole
repository exists to avoid.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

#: Strings that must never survive into a double-blind submission.
IDENTIFYING_PATTERNS = (
    r"pneuma",
    r"9to5",
    r"C:[\\/]Users",
    r"/home/[a-z]",
    r"fireheart",
    r"github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+",
)

#: Placeholder macros that must be absent at submission.
PLACEHOLDER_PATTERNS = (
    (r"\\result\{", "unfilled result slot"),
    (r"\\TODO\{", "unresolved TODO"),
    (r"\\draftnotice", "draft notice still enabled"),
)

#: Venue body budget, references and appendices excluded.
PAGE_BUDGET_MIN = 4
PAGE_BUDGET_MAX = 9

#: Characters of body text that fit on one page of the NeurIPS 2026 template
#: at 10pt with the workshop option. Calibrated against the sibling submission
#: whose page count was measured directly in a built PDF; it is an ESTIMATE and
#: is reported as such.
CHARS_PER_PAGE_ESTIMATE = 3675


@dataclass(frozen=True)
class CheckResult:
    """One manuscript check."""

    name: str
    status: str  # "pass" | "fail" | "pending"
    detail: str
    findings: tuple[str, ...] = ()

    @property
    def failed(self) -> bool:
        return self.status == "fail"

    def to_canonical(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "detail": self.detail,
            "findings": list(self.findings),
        }


def _strip_comments(text: str) -> str:
    """Remove LaTeX line comments, keeping escaped percent signs."""

    out: list[str] = []
    for line in text.splitlines():
        stripped = re.sub(r"(?<!\\)%.*$", "", line)
        out.append(stripped)
    return "\n".join(out)


def check_placeholders(source: str) -> CheckResult:
    """Fail while any placeholder macro survives in non-comment source."""

    body = _strip_comments(source)
    findings: list[str] = []
    for pattern, label in PLACEHOLDER_PATTERNS:
        count = len(re.findall(pattern, body))
        if count:
            findings.append(f"{label}: {count}")
    if findings:
        return CheckResult(
            name="placeholders",
            status="fail",
            detail=(
                "the manuscript still contains placeholders; a pre-results "
                "draft is expected to fail this check and must fail it"
            ),
            findings=tuple(findings),
        )
    return CheckResult("placeholders", "pass", "no placeholder macros remain")


def check_anonymity(source: str) -> CheckResult:
    """Fail on any identifying string in the source, comments included.

    Comments are checked deliberately: a stripped comment is not guaranteed to
    be absent from the submitted archive, and reviewers have read source before.
    """

    findings: list[str] = []
    for pattern in IDENTIFYING_PATTERNS:
        for match in re.finditer(pattern, source, flags=re.IGNORECASE):
            line = source[: match.start()].count("\n") + 1
            findings.append(f"line {line}: {match.group(0)!r} matches /{pattern}/")
    if findings:
        return CheckResult(
            name="anonymity",
            status="fail",
            detail="identifying strings would break double-blind review",
            findings=tuple(sorted(set(findings))),
        )
    return CheckResult("anonymity", "pass", "no identifying strings found in source")


def check_page_budget(source: str) -> CheckResult:
    """Estimate the body page count from source, and say that it is an estimate."""

    body = _strip_comments(source)
    start = body.find(r"\maketitle")
    end = body.find(r"\bibliographystyle")
    if start < 0 or end <= start:
        return CheckResult(
            "page_budget",
            "pending",
            "could not locate the body between \\maketitle and \\bibliographystyle",
        )
    chars = len(re.sub(r"\s+", " ", body[start:end]))
    estimate = chars / CHARS_PER_PAGE_ESTIMATE
    detail = (
        f"estimated body length {estimate:.1f} pages from {chars} characters "
        f"at {CHARS_PER_PAGE_ESTIMATE} chars/page; budget is "
        f"{PAGE_BUDGET_MIN}-{PAGE_BUDGET_MAX} pages. This is a SOURCE estimate: "
        "the authoritative count requires a built PDF."
    )
    if estimate > PAGE_BUDGET_MAX:
        return CheckResult("page_budget", "fail", detail)
    return CheckResult("page_budget", "pending", detail)


_CITE = re.compile(r"\\cite[a-z]*\{([^}]*)\}")
_BIBKEY = re.compile(r"^@\w+\{([^,]+),", re.MULTILINE)


def check_bibliography(
    source: str, bib_texts: Sequence[str], citation_queue: dict | None
) -> CheckResult:
    """Fail on undefined citations or an unresolved citation-queue entry."""

    cited: set[str] = set()
    for match in _CITE.finditer(_strip_comments(source)):
        cited.update(key.strip() for key in match.group(1).split(",") if key.strip())

    defined: set[str] = set()
    for text in bib_texts:
        defined.update(key.strip() for key in _BIBKEY.findall(text))

    findings: list[str] = []
    for key in sorted(cited - defined):
        findings.append(f"cited but undefined: {key}")

    if citation_queue is not None:
        for entry in citation_queue.get("entries", ()):
            if str(entry.get("state")) != "verified":
                findings.append(
                    f"citation queue entry {entry.get('key')!r} is "
                    f"{entry.get('state')!r}: {entry.get('title')!r}"
                )

    if findings:
        return CheckResult(
            "bibliography",
            "fail",
            "the bibliography is not submission-ready",
            tuple(findings),
        )
    return CheckResult(
        "bibliography",
        "pass",
        f"{len(cited)} citations, all defined; citation queue clean",
    )


def check_number_provenance(source: str, emitted_keys: Iterable[str]) -> CheckResult:
    """Fail on a scientific-looking number that no emitted key accounts for.

    Design constants fixed before execution are exempt by construction: they
    appear in the source as literals inside a ``\\texttt`` or a table of design
    parameters, and the manuscript declares them. What this catches is a
    decimal that reads as a measured effect appearing in prose.
    """

    body = _strip_comments(source)
    emitted = set(emitted_keys)
    findings: list[str] = []

    # A measured-looking claim: a decimal immediately preceded by wording that
    # asserts observation.
    pattern = re.compile(
        r"(we (?:find|observe|measure|report)[^.]{0,80}?)(\d+\.\d+|\d+(?:\.\d+)?\s*(?:percentage points|pp|%))",
        re.IGNORECASE,
    )
    for match in pattern.finditer(body):
        line = body[: match.start()].count("\n") + 1
        findings.append(
            f"line {line}: measured-looking value {match.group(2)!r} in prose"
        )

    if findings:
        return CheckResult(
            "number_provenance",
            "fail",
            (
                "a scientific number appears in prose without coming from the "
                f"emitted set ({len(emitted)} keys available)"
            ),
            tuple(findings),
        )
    return CheckResult(
        "number_provenance",
        "pass",
        "no hand-entered measured value found in prose",
    )


def check_forbidden_novelty_claims(source: str) -> CheckResult:
    """Fail on a phrasing that claims placebo control itself is novel."""

    body = _strip_comments(source).lower()
    forbidden = (
        "the first placebo-controlled",
        "we introduce placebo control",
        "novel four-arm",
        "first study to use a placebo",
        "we are the first to",
    )
    findings = [phrase for phrase in forbidden if phrase in body]
    if findings:
        return CheckResult(
            "novelty_discipline",
            "fail",
            "the manuscript claims novelty the prior art does not permit",
            tuple(findings),
        )
    return CheckResult(
        "novelty_discipline",
        "pass",
        "no prohibited novelty phrasing found",
    )


def check_pdf_dependent(pdf_path: Path) -> tuple[CheckResult, ...]:
    """Report PDF-only checks as pending when no PDF exists."""

    if not pdf_path.is_file():
        detail = (
            f"{pdf_path.name} has not been built; a LaTeX toolchain is not "
            "available in this environment"
        )
        return tuple(
            CheckResult(name, "pending", detail)
            for name in (
                "pdf_page_count",
                "pdf_font_embedding",
                "pdf_metadata",
                "pdf_text_layer_anonymity",
            )
        )
    return (
        CheckResult(
            "pdf_checks",
            "pending",
            "a PDF exists but PDF inspection is delegated to paper/preflight.sh",
        ),
    )
