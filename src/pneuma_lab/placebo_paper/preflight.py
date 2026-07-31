"""The PLACEBO paper preflight: fail-closed, source-level, honest about gaps.

Running the preflight on a pre-results draft is expected to FAIL. That is the
design. The failure list is the submission checklist, and it shrinks as the
work completes rather than being asserted complete in advance.

Checks that require a built PDF are reported ``pending``, never ``pass``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

from . import checks
from .errors import PackageRejected
from .package import SealedPackage, admit


@dataclass(frozen=True)
class PreflightReport:
    """The complete preflight outcome."""

    manuscript: str
    package_state: str
    package_detail: str
    results: tuple[checks.CheckResult, ...]

    @property
    def failures(self) -> tuple[checks.CheckResult, ...]:
        return tuple(item for item in self.results if item.status == "fail")

    @property
    def pending(self) -> tuple[checks.CheckResult, ...]:
        return tuple(item for item in self.results if item.status == "pending")

    @property
    def submission_ready(self) -> bool:
        return not self.failures and not self.pending

    def to_canonical(self) -> dict[str, Any]:
        return {
            "manuscript": self.manuscript,
            "package_state": self.package_state,
            "package_detail": self.package_detail,
            "submission_ready": self.submission_ready,
            "results": [item.to_canonical() for item in self.results],
        }

    def render(self) -> str:
        lines = [
            f"paper preflight: {self.manuscript}",
            f"  evidence package: {self.package_state} -- {self.package_detail}",
            "",
        ]
        for item in self.results:
            marker = {"pass": "ok   ", "fail": "FAIL ", "pending": "pend "}[item.status]
            lines.append(f"  {marker} {item.name:<24} {item.detail}")
            for finding in item.findings:
                lines.append(f"           - {finding}")
        lines.append("")
        if self.submission_ready:
            lines.append("preflight PASSED: the manuscript is submission-ready")
        else:
            lines.append(
                f"preflight BLOCKED: {len(self.failures)} failing, "
                f"{len(self.pending)} pending"
            )
        return "\n".join(lines) + "\n"


def run(
    manuscript_path: Path,
    *,
    bib_paths: Sequence[Path] = (),
    citation_queue_path: Path | None = None,
    package_path: Path | None = None,
    pdf_path: Path | None = None,
) -> PreflightReport:
    """Run every check and return the report. Never raises on a check failure."""

    source = manuscript_path.read_text(encoding="utf-8")

    package: SealedPackage | None = None
    if package_path is None:
        package_state = "absent"
        package_detail = (
            "no sealed evidence package supplied; every result slot stays "
            "unfilled and the manuscript cannot be submitted"
        )
    else:
        try:
            package = admit(package_path)
        except PackageRejected as exc:
            package_state = "rejected"
            package_detail = f"{type(exc).__name__}: {exc}"
        else:
            package_state = "admitted"
            package_detail = (
                f"lineage {package.lineage}, verdict {package.verdict}, "
                f"artifact root {package.artifact_root_digest[:16]}..."
            )

    queue: dict | None = None
    if citation_queue_path is not None and citation_queue_path.is_file():
        queue = json.loads(citation_queue_path.read_text(encoding="utf-8"))

    bib_texts = [path.read_text(encoding="utf-8") for path in bib_paths if path.is_file()]

    results: list[checks.CheckResult] = [
        checks.check_placeholders(source),
        checks.check_anonymity(source),
        checks.check_page_budget(source),
        checks.check_bibliography(source, bib_texts, queue),
        checks.check_number_provenance(
            source, package.numbers.keys() if package else ()
        ),
        checks.check_forbidden_novelty_claims(source),
    ]

    if package_state != "admitted":
        results.append(
            checks.CheckResult(
                "evidence_package",
                "fail",
                package_detail,
            )
        )
    else:
        results.append(
            checks.CheckResult("evidence_package", "pass", package_detail)
        )

    results.extend(
        checks.check_pdf_dependent(pdf_path or manuscript_path.with_suffix(".pdf"))
    )

    return PreflightReport(
        manuscript=manuscript_path.name,
        package_state=package_state,
        package_detail=package_detail,
        results=tuple(results),
    )
