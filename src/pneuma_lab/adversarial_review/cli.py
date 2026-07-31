"""Command-line entry point for the adversarial-review system.

    python -m pneuma_lab.adversarial_review run   --spec <campaign-spec.json> --out <dir>
    python -m pneuma_lab.adversarial_review prompt --role R03-statistics
    python -m pneuma_lab.adversarial_review roles

``run`` exits non-zero whenever the campaign is blocked or cannot be completed,
so the review is usable as a gate in a shell pipeline without any consumer
having to interpret the artifact.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

from .campaign import run_campaign, write_campaign
from .disposition import NO_BLOCKING_FINDINGS
from .errors import AdversarialReviewError
from .inputs import CampaignInputs, EnvironmentPin, InputObject
from .matrix import load_claims
from .records import Override
from .report import render
from .roles import ROLES, ROLES_BY_ID
from .subprocess_adapter import LiveSource, ReplaySource

EXIT_OK = 0
EXIT_BLOCKED = 1
EXIT_FAIL_CLOSED = 2


def _load_spec(path: Path) -> Mapping[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _build_inputs(spec: Mapping[str, Any], spec_path: Path) -> CampaignInputs:
    root = (spec_path.parent / spec["root"]).resolve()
    environment = spec["environment"]
    return CampaignInputs(
        campaign_id=str(spec["campaign_id"]),
        stage=str(spec["stage"]),
        root=root,
        environment=EnvironmentPin(
            repo_commit=str(environment["repo_commit"]),
            repo_dirty=bool(environment["repo_dirty"]),
            python_version=str(environment["python_version"]),
            platform=str(environment["platform"]),
            dependency_digest=str(environment["dependency_digest"]),
        ),
        objects=tuple(
            InputObject(
                slot=str(item["slot"]),
                path=str(item["path"]),
                declared_digest=str(item["declared_digest"]),
                description=str(item.get("description", "")),
                optional=bool(item.get("optional", False)),
            )
            for item in spec["objects"]
        ),
        receipt_index=dict(spec.get("receipt_index", {})),
        external_sources=tuple(spec.get("external_sources", ())),
    )


def _build_source(spec: Mapping[str, Any], spec_path: Path):
    source = spec.get("source", {})
    mode = str(source.get("mode", "replay"))
    if mode == "replay":
        return ReplaySource(
            transcript_dir=(spec_path.parent / source["transcript_dir"]).resolve(),
            strict_prompt_digest=bool(source.get("strict_prompt_digest", True)),
        )
    if mode == "live":
        return LiveSource(
            engine=str(source["engine"]),
            model=str(source["model"]),
            cwd=(spec_path.parent / source.get("cwd", ".")).resolve(),
        )
    raise AdversarialReviewError(f"unknown proposal source mode {mode!r}")


def _run(args: argparse.Namespace) -> int:
    spec_path = Path(args.spec).resolve()
    spec = _load_spec(spec_path)
    inputs = _build_inputs(spec, spec_path)
    claims = load_claims(spec.get("claims", ()))
    overrides = tuple(
        Override(
            finding_digest=str(item["finding_digest"]),
            signer=str(item["signer"]),
            signer_role=str(item["signer_role"]),
            rationale=str(item["rationale"]),
            signature=str(item["signature"]),
            accepted_risk=str(item["accepted_risk"]),
        )
        for item in spec.get("overrides", ())
    )

    kwargs: dict[str, Any] = {
        "campaign_id": inputs.campaign_id,
        "stage": inputs.stage,
        "inputs": inputs,
        "claims": claims,
        "source": _build_source(spec, spec_path),
        "overrides": overrides,
        "discharged": dict(spec.get("discharged", {})),
    }
    if spec.get("role_ids"):
        kwargs["role_ids"] = tuple(str(item) for item in spec["role_ids"])
    result = run_campaign(**kwargs)

    out_dir = Path(args.out).resolve()
    write_campaign(result, out_dir)
    (out_dir / "rejection-report.md").write_text(render(result), encoding="utf-8")

    print(f"verdict: {result.disposition.verdict}")
    print(f"disposition digest: {result.disposition.disposition_digest}")
    print(f"artifacts: {out_dir}")
    return EXIT_OK if result.disposition.verdict == NO_BLOCKING_FINDINGS else EXIT_BLOCKED


def _prompt(args: argparse.Namespace) -> int:
    role = ROLES_BY_ID.get(args.role)
    if role is None:
        print(f"unknown role {args.role!r}", file=sys.stderr)
        return EXIT_FAIL_CLOSED
    print(role.prompt())
    return EXIT_OK


def _roles(_: argparse.Namespace) -> int:
    for role in ROLES:
        print(f"{role.role_id}\t{role.stage}\t{role.title}")
    return EXIT_OK


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m pneuma_lab.adversarial_review",
        description="Construct the strongest evidence-based case for rejecting PLACEBO.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    run_parser = sub.add_parser("run", help="run a campaign from a spec file")
    run_parser.add_argument("--spec", required=True)
    run_parser.add_argument("--out", required=True)
    run_parser.set_defaults(handler=_run)

    prompt_parser = sub.add_parser("prompt", help="print one reviewer prompt")
    prompt_parser.add_argument("--role", required=True)
    prompt_parser.set_defaults(handler=_prompt)

    roles_parser = sub.add_parser("roles", help="list reviewer roles")
    roles_parser.set_defaults(handler=_roles)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.handler(args))
    except AdversarialReviewError as exc:
        print(f"FAIL CLOSED: {type(exc).__name__}: {exc}", file=sys.stderr)
        return EXIT_FAIL_CLOSED
