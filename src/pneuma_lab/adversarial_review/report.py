"""The readable rejection report.

Rendered deterministically from the sealed campaign record. The report never
introduces a fact that is not already in the record, so it can be regenerated
from ``campaign.json`` alone and compared byte for byte.
"""

from __future__ import annotations

from typing import Sequence

from .campaign import CampaignResult
from .chair import underspecified_items
from .records import Finding
from .severity import BLOCKER, MAJOR, MINOR, SPECULATION

_SEVERITY_ORDER = (BLOCKER, MAJOR, MINOR, SPECULATION)
_SEVERITY_TITLES = {
    BLOCKER: "Blocking findings",
    MAJOR: "Major findings",
    MINOR: "Minor findings",
    SPECULATION: "Speculation (recorded, cannot block)",
}


def render(result: CampaignResult) -> str:
    """Render the full rejection report as Markdown."""

    lines: list[str] = [
        f"# Adversarial review — {result.campaign_id}",
        "",
        f"**Stage:** `{result.stage}`",
        f"**Verdict:** `{result.disposition.verdict}`",
        f"**Inputs digest:** `{result.inputs_digest}`",
        f"**Disposition digest:** `{result.disposition.disposition_digest}`",
        "",
        "> " + result.disposition.non_authorization_notice.replace("\n", " "),
        "",
        "## Strongest case for rejection",
        "",
        result.synthesis.strongest_rejection_argument,
        "",
    ]

    if result.conflicts:
        lines.extend(["## Independence and conflicts of interest", ""])
        for conflict in result.conflicts:
            marker = "BLOCKING" if conflict.blocking else "advisory"
            lines.append(
                f"- **{conflict.kind}** ({marker}) — {', '.join(conflict.role_ids)}: "
                f"{conflict.detail}"
            )
        lines.append("")

    findings = result.all_findings()
    for severity in _SEVERITY_ORDER:
        group = [item for item in findings if item.severity == severity]
        if not group:
            continue
        lines.extend([f"## {_SEVERITY_TITLES[severity]}", ""])
        for finding in sorted(group, key=lambda item: (item.role_id, item.finding_id)):
            lines.extend(_render_finding(finding))
        lines.append("")

    lines.extend(["## Evidence-to-claim matrix", ""])
    lines.append("| claim | supporting evidence | attacking findings | unsupported |")
    lines.append("| --- | --- | --- | --- |")
    for row in result.synthesis.claim_matrix:
        support = ", ".join(row.supporting_evidence) or "—"
        attacks = ", ".join(digest[:12] for digest in row.attacking_findings) or "—"
        lines.append(
            f"| `{row.claim_id}` | {support} | {attacks} | "
            f"{'**yes**' if row.unsupported else 'no'} |"
        )
    lines.append("")

    lines.extend(["## Falsification schedule", ""])
    if result.falsification:
        lines.append("| gate | severity | owner | disposition | test |")
        lines.append("| --- | --- | --- | --- | --- |")
        for item in result.falsification:
            test = item.test_statement.replace("|", "\\|")
            lines.append(
                f"| `{item.gate}` | {item.severity} | {item.owner} | "
                f"`{item.disposition}` | {test} |"
            )
    else:
        lines.append("No finding required conversion into a falsification test.")
    lines.append("")

    stragglers = underspecified_items(result.falsification)
    if stragglers:
        lines.extend(
            [
                "### Findings the chair could not convert into a decidable test",
                "",
            ]
        )
        lines.extend(
            f"- `{item.finding_digest[:12]}` from {item.role_id}" for item in stragglers
        )
        lines.append("")

    if result.synthesis.dissent_notes:
        lines.extend(["## Preserved dissent", ""])
        lines.extend(f"- {note}" for note in result.synthesis.dissent_notes)
        lines.append("")

    if result.disposition.overridden_finding_digests:
        lines.extend(
            [
                "## Human overrides",
                "",
                "Each override below records accepted risk. The underlying "
                "finding remains in this report verbatim and was not erased.",
                "",
            ]
        )
        lines.extend(
            f"- `{digest[:12]}`" for digest in result.disposition.overridden_finding_digests
        )
        lines.append("")

    lines.extend(["## Subprocess receipts", ""])
    lines.append("| role | engine | model | output tokens | cost bound (USD) | status |")
    lines.append("| --- | --- | --- | ---: | ---: | --- |")
    for report in result.reports:
        receipt = report.receipt
        if receipt is None:
            lines.append(f"| {report.role_id} | — | — | — | — | no receipt |")
            continue
        lines.append(
            f"| {receipt.role_id} | {receipt.engine} | {receipt.model} | "
            f"{receipt.output_tokens if receipt.output_tokens is not None else '—'} | "
            f"{receipt.cost_usd_upper_bound:.2f} | {receipt.exit_status} |"
        )
    lines.append("")

    return "\n".join(lines) + "\n"


def _render_finding(finding: Finding) -> Sequence[str]:
    lines = [
        f"### `{finding.finding_id}` {finding.title}",
        "",
        f"- **Role:** {finding.role_id}",
        f"- **Digest:** `{finding.digest}`",
        f"- **Claims attacked:** {', '.join(finding.claim_ids) or '—'}",
        "",
        finding.statement,
        "",
        f"**Failure mode.** {finding.failure_mode}",
        "",
    ]
    if finding.what_would_refute:
        lines.extend([f"**Refuted by.** {finding.what_would_refute}", ""])
    if finding.evidence:
        lines.append("**Evidence.**")
        lines.append("")
        for ref in finding.evidence:
            span = ""
            if ref.start_line:
                span = f":{ref.start_line}"
                if ref.end_line and ref.end_line != ref.start_line:
                    span += f"-{ref.end_line}"
            lines.append(f"- `{ref.kind}` `{ref.locator}{span}` — {ref.detail}")
        lines.append("")
    if finding.reproduction:
        lines.append("**Reproduction.**")
        lines.append("")
        lines.append("```sh")
        lines.extend(finding.reproduction)
        lines.append("```")
        lines.append("")
    return lines
