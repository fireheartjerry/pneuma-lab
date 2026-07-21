"""Authorized-only portable cloud reproduction bundle, built locally.

This module packages one already-finalized cloud authorization into a
deterministic tar archive for the optional one-time RunPod reproduction.
It is strictly local and quote-only: it never contacts RunPod, never
creates a Pod, and never opens a network connection.

The bundle contains tracked source at the authorized clean commit, the
final authorization, the exact preparation receipts, the authorized
content-addressed shard plus its manifest, the bound local-gate report,
the pinned model-cache receipt (never model weights), the dependency
lock, and the Linux setup script. From the 2m stage on, the receipts
cover both gradient lanes (including the Open-SWE-Traces license receipt
and the cross-dataset leakage receipt). It contains no secrets, raw
source paths, blocked or unapproved dataset payloads, notebooks,
checkpoints, or Hugging Face cache content.

Both lane license receipts declare ``cloud_redistribution_allowed:
false``. The bundle is not redistribution: it is the private, single-job
transfer of derived, digest-bearing artifacts to an ephemeral pod, and it
is permitted only when the separately finalized cloud authorization
carries the operator-approved ``private_cloud_transfer_allowed: true``
posture.

``build_cloud_reproduction_candidate`` derives a separate, nonauthorizing
cloud candidate from the verified local authorization; it binds the passed
local-gate report and the human-provided quote, and still requires the
exact operator finalization handshake before any bundle can be built.
"""

from __future__ import annotations

import copy
import dataclasses
import json
import os
import subprocess
import tarfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from pneuma_lab.foundation.artifacts import sha256_file, write_atomic_json
from pneuma_lab.foundation.authorization import (
    _validate_manifest,
    artifact_binding,
    authorization_scope_digest,
    verify_foundation_authorization,
)
from pneuma_lab.foundation.budget import (
    MAX_LIFETIME_CLOUD_USD,
    MAX_PREPAID_CREDIT_USD,
    MAX_TERMINATION_HOURS,
    REPRODUCTION_STAGE_TOKENS,
    BudgetViolation,
    CloudQuote,
    ReproductionQuoteAuthorization,
    authorize_reproduction_quote,
)
from pneuma_lab.foundation.snapshot_receipt import _RECEIPT_NAME


BUNDLE_MANIFEST_ARCNAME = "PNEUMA_CLOUD_BUNDLE_MANIFEST.json"
PROTECTED_DATA_ROOTS = (Path(r"C:\pneuma-data"), Path("/mnt/c/pneuma-data"))
_BLOCKED_NAME_FRAGMENTS = ("swe-chat", "sec-bench-pro")
_EXCLUDED_SOURCE_SUFFIXES = {".ipynb", ".pt", ".pth", ".ckpt", ".safetensors"}
_EXCLUDED_SOURCE_PARTS = {".cache", "checkpoints", "huggingface"}
_REGISTRY_RELATIVE = Path("docs/data/training-readiness/dataset-registry.json")
_CANDIDATES_RELATIVE = Path("build/foundation/authorizations/candidates")
_FINAL_RELATIVE = Path("build/foundation/authorizations/final")


class CloudBundleError(ValueError):
    """Raised before any bundle byte is written when a cloud guard fails."""


@dataclass(frozen=True)
class CloudBundleRequest:
    repo_root: Path
    data_root: Path
    authorization_path: Path
    output_path: Path
    stage: str
    quote: CloudQuote
    dry_run: bool = False


def _thaw(value):
    """Deep-copy a possibly deep-frozen manifest into plain JSON types."""

    if isinstance(value, Mapping):
        return {key: _thaw(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_thaw(item) for item in value]
    return value


def _load_json(path: Path) -> dict:
    try:
        payload = Path(path).read_text(encoding="utf-8")
    except OSError as exc:
        raise CloudBundleError(f"cannot read JSON artifact: {path}") from exc
    try:
        value = json.loads(payload)
    except ValueError as exc:
        raise CloudBundleError(f"artifact is not valid JSON: {path}") from exc
    if not isinstance(value, dict):
        raise CloudBundleError(f"artifact must be a JSON object: {path}")
    return value


def _default_data_root() -> Path:
    for root in PROTECTED_DATA_ROOTS:
        if root.is_absolute():
            return root
    return PROTECTED_DATA_ROOTS[0]


def _validate_candidate_quote(quote: CloudQuote) -> None:
    """Enforce the stage-independent hard caps at candidate-build time.

    The full quote gate (stage tokens, measured speed, all-in fit) runs at
    bundle time through :func:`authorize_reproduction_quote`; the candidate
    stage validates every cap that does not depend on the stage.
    """

    numbers = {
        "quoted hourly rate": quote.hourly_usd,
        "quoted tax-inclusive total": quote.tax_inclusive_usd,
        "prepaid credit": quote.prepaid_credit_usd,
        "termination hours": quote.termination_hours,
        "measured tokens per second": quote.measured_tokens_per_second,
        "prior lifetime spend": quote.prior_lifetime_spend_usd,
    }
    for label, value in numbers.items():
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise BudgetViolation(f"{label} must be a real number")
        if value != value or value in (float("inf"), float("-inf")):
            raise BudgetViolation(f"{label} must be finite")
    if quote.hourly_usd <= 0 or quote.tax_inclusive_usd <= 0:
        raise BudgetViolation("quoted cloud amounts must be positive")
    if quote.prepaid_credit_usd < 0 or quote.prior_lifetime_spend_usd < 0:
        raise BudgetViolation("cloud quote amounts cannot be negative")
    if quote.auto_pay_enabled is not False:
        raise BudgetViolation("cloud reproduction requires auto-pay to stay disabled")
    if not 0 < quote.termination_hours <= MAX_TERMINATION_HOURS:
        raise BudgetViolation(
            f"the cloud pod must hard-terminate within {MAX_TERMINATION_HOURS} hours"
        )
    if quote.prepaid_credit_usd > MAX_PREPAID_CREDIT_USD:
        raise BudgetViolation(
            f"prepaid credit may not exceed ${MAX_PREPAID_CREDIT_USD:g}"
        )
    if (
        quote.prior_lifetime_spend_usd + quote.tax_inclusive_usd
        > MAX_LIFETIME_CLOUD_USD
    ):
        raise BudgetViolation(
            "the quote plus prior spend exceeds the "
            f"${MAX_LIFETIME_CLOUD_USD:g} lifetime tax-inclusive cap"
        )


def _candidate_quote(
    quote: CloudQuote | None,
    quoted_hourly_usd: float | None,
    quoted_tax_inclusive_usd: float | None,
) -> CloudQuote:
    """Accept either a full quote or the two CLI primitives, never both."""

    if quote is not None:
        if quoted_hourly_usd is not None or quoted_tax_inclusive_usd is not None:
            raise CloudBundleError(
                "provide either a cloud quote or the quoted primitives, not both"
            )
        return quote
    if quoted_hourly_usd is None or quoted_tax_inclusive_usd is None:
        raise CloudBundleError(
            "a cloud quote requires quoted hourly and tax-inclusive amounts"
        )
    return CloudQuote(
        hourly_usd=float(quoted_hourly_usd),
        tax_inclusive_usd=float(quoted_tax_inclusive_usd),
        prepaid_credit_usd=min(float(quoted_tax_inclusive_usd), MAX_PREPAID_CREDIT_USD),
        auto_pay_enabled=False,
        termination_hours=MAX_TERMINATION_HOURS,
        # Unmeasured: the full bundle-time gate rejects this sentinel, so a
        # candidate built from CLI primitives can never skip a measurement.
        measured_tokens_per_second=0.0,
        prior_lifetime_spend_usd=0.0,
    )


def conservative_cloud_quote(
    stage: str,
    *,
    quoted_hourly_usd: float,
    quoted_tax_inclusive_usd: float,
) -> CloudQuote:
    """Build the worst-case quote the CLI primitives can honestly support.

    The measured speed defaults to the slowest rate that still finishes
    inside the 72-hour termination window, so the cost estimate assumes the
    full window is consumed. For the 8m stage this default sits below the
    required 30.9 tokens/second, which correctly fails the gate until a
    real measurement is supplied.
    """

    tokens = REPRODUCTION_STAGE_TOKENS.get(stage)
    if tokens is None:
        raise CloudBundleError(
            "cloud reproduction supports only the 2m default or the 8m stage"
        )
    return CloudQuote(
        hourly_usd=float(quoted_hourly_usd),
        tax_inclusive_usd=float(quoted_tax_inclusive_usd),
        prepaid_credit_usd=min(float(quoted_tax_inclusive_usd), MAX_PREPAID_CREDIT_USD),
        auto_pay_enabled=False,
        termination_hours=MAX_TERMINATION_HOURS,
        measured_tokens_per_second=tokens / (MAX_TERMINATION_HOURS * 3600.0),
        prior_lifetime_spend_usd=0.0,
    )


def _binding_path(binding, *, repo_root: Path) -> Path:
    relative = binding.get("path") if isinstance(binding, Mapping) else None
    if not isinstance(relative, str) or not relative:
        raise CloudBundleError("authorization artifact binding path is invalid")
    candidate = Path(relative)
    if ".." in candidate.parts:
        raise CloudBundleError("authorization artifact binding path traverses parents")
    if candidate.is_absolute():
        return candidate
    return repo_root / candidate


def _is_excluded_source(name: str) -> bool:
    lowered = PurePosixPath(name.casefold())
    if any(fragment in str(lowered) for fragment in _BLOCKED_NAME_FRAGMENTS):
        return True
    if lowered.suffix in _EXCLUDED_SOURCE_SUFFIXES:
        return True
    if lowered.name.startswith(".env"):
        return True
    if any(part in _EXCLUDED_SOURCE_PARTS for part in lowered.parts):
        return True
    return False


def _tracked_source_paths(repo_root: Path) -> list[Path]:
    """List tracked source at the verified clean checkout, filtered.

    ``verify_foundation_authorization`` has already proven the checkout is
    clean and matches the authorized ``code_commit``, so the current index
    is exactly the authorized source tree.
    """

    try:
        completed = subprocess.run(
            ["git", "ls-files", "-z"],
            cwd=repo_root,
            check=True,
            capture_output=True,
            timeout=60,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise CloudBundleError(f"cannot enumerate tracked source: {exc}") from exc
    names = [name for name in completed.stdout.decode("utf-8").split("\0") if name]
    return [repo_root / name for name in sorted(names) if not _is_excluded_source(name)]


def authorized_bundle_paths(verified, *, repo_root: Path) -> tuple[Path, ...]:
    """Derive every file the bundle may contain from the verified manifest."""

    root = Path(repo_root).resolve()
    scope = _thaw(verified.manifest).get("scope")
    if not isinstance(scope, Mapping):
        raise CloudBundleError("verified authorization scope is missing")
    artifacts = scope.get("artifacts")
    if not isinstance(artifacts, Mapping) or not artifacts:
        raise CloudBundleError("verified authorization artifacts are missing")
    paths = [_binding_path(binding, repo_root=root) for binding in artifacts.values()]
    cloud = scope.get("execution_profile") == "cloud"
    suffix = "-cloud" if cloud else ""
    paths.append(root / _FINAL_RELATIVE / f"{scope.get('stage')}{suffix}.json")
    if cloud:
        gate_binding = scope.get("local_gate_report")
        if not isinstance(gate_binding, Mapping):
            raise CloudBundleError(
                "verified cloud authorization gate-report binding is missing"
            )
        paths.append(_binding_path(gate_binding, repo_root=root))
    snapshot = scope.get("tokenizer_snapshot")
    snapshot_relative = snapshot.get("path") if isinstance(snapshot, Mapping) else None
    if not isinstance(snapshot_relative, str) or not snapshot_relative:
        raise CloudBundleError("verified tokenizer snapshot binding is missing")
    # The model-cache receipt travels; the pinned model weights never do.
    paths.append(root / Path(snapshot_relative) / _RECEIPT_NAME)
    paths.append(root / "uv.lock")
    paths.append(root / "scripts/foundation/setup-linux.sh")
    paths.extend(_tracked_source_paths(root))
    unique = sorted({Path(path) for path in paths})
    return tuple(unique)


def authorize_reproduction_quote_from_request(
    request: CloudBundleRequest,
    verified,
) -> ReproductionQuoteAuthorization:
    """Run the full hard budget gate for one verified bundle request."""

    scope = verified.manifest.get("scope")
    stage = scope.get("stage") if isinstance(scope, Mapping) else None
    if stage != request.stage:
        raise CloudBundleError(
            "requested bundle stage differs from the authorized scope stage"
        )
    quote = request.quote
    return authorize_reproduction_quote(
        stage=request.stage,
        quoted_hourly_usd=quote.hourly_usd,
        quoted_tax_inclusive_usd=quote.tax_inclusive_usd,
        prepaid_credit_usd=quote.prepaid_credit_usd,
        auto_pay_enabled=quote.auto_pay_enabled,
        termination_hours=quote.termination_hours,
        measured_tokens_per_second=quote.measured_tokens_per_second,
        prior_lifetime_spend_usd=quote.prior_lifetime_spend_usd,
    )


def build_bundle_manifest(
    paths: Sequence[Path],
    *,
    authorization,
    quote: ReproductionQuoteAuthorization,
    repo_root: Path,
    stage: str,
) -> tuple[dict, list[tuple[str, Path]]]:
    """Hash every permitted file into a deterministic bundle manifest."""

    root = Path(repo_root).resolve()
    files: list[tuple[str, Path]] = []
    entries = []
    for path in sorted({Path(item).resolve() for item in paths}):
        try:
            relative = path.relative_to(root)
        except ValueError as exc:
            raise CloudBundleError(
                "cloud bundle paths must stay inside the repository checkout"
            ) from exc
        arcname = relative.as_posix()
        if not path.is_file():
            raise CloudBundleError(f"cloud bundle input is missing: {arcname}")
        entries.append(
            {
                "arcname": arcname,
                "sha256": sha256_file(path),
                "size": path.stat().st_size,
            }
        )
        files.append((arcname, path))
    manifest = {
        "manifest_kind": "pneuma_foundation_cloud_bundle",
        "manifest_schema_version": "0.1.0",
        "stage": stage,
        "execution_profile": "cloud",
        "scope_digest": authorization.scope_digest,
        "network_access": "none",
        "quote": dataclasses.asdict(quote),
        "file_count": len(entries),
        "files": entries,
    }
    return manifest, files


def write_reproducible_tar(
    output_path: Path,
    files: Sequence[tuple[str, Path]],
    manifest: Mapping,
) -> None:
    """Write a byte-deterministic tar: fixed order, zero mtime, no owner."""

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    manifest_bytes = (
        json.dumps(dict(manifest), allow_nan=False, indent=4, sort_keys=True) + "\n"
    ).encode("utf-8")
    temporary = output.with_name(output.name + ".tmp")
    try:
        with tarfile.open(
            temporary, "w", format=tarfile.PAX_FORMAT, encoding="utf-8"
        ) as archive:
            _add_tar_bytes(archive, BUNDLE_MANIFEST_ARCNAME, manifest_bytes)
            for arcname, path in sorted(files):
                info = _tar_info(arcname, Path(path).stat().st_size)
                with Path(path).open("rb") as stream:
                    archive.addfile(info, stream)
        os.replace(temporary, output)
    finally:
        if temporary.exists():
            temporary.unlink()


def _tar_info(arcname: str, size: int) -> tarfile.TarInfo:
    info = tarfile.TarInfo(name=arcname)
    info.size = size
    info.mtime = 0
    info.mode = 0o644
    info.uid = 0
    info.gid = 0
    info.uname = ""
    info.gname = ""
    return info


def _add_tar_bytes(archive: tarfile.TarFile, arcname: str, payload: bytes) -> None:
    import io

    archive.addfile(_tar_info(arcname, len(payload)), io.BytesIO(payload))


def _forbidden_roots(request: CloudBundleRequest) -> tuple[Path, ...]:
    roots = [Path(request.data_root)]
    roots.extend(root for root in PROTECTED_DATA_ROOTS if root.is_absolute())
    return tuple({root.resolve() for root in roots})


def build_cloud_bundle(request: CloudBundleRequest) -> dict:
    """Verify, guard, quote-gate, and package one cloud reproduction bundle."""

    root = Path(request.repo_root).resolve()
    verified = verify_foundation_authorization(
        request.authorization_path,
        repo_root=request.repo_root,
        registry_path=root / _REGISTRY_RELATIVE,
    )
    scope = verified.manifest.get("scope")
    if not isinstance(scope, Mapping):
        raise CloudBundleError("verified authorization scope is missing")
    if scope.get("stage") != request.stage:
        raise CloudBundleError(
            "requested bundle stage differs from the authorized scope stage"
        )
    policy = scope.get("source_data_policy")
    transfer_allowed = (
        policy.get("private_cloud_transfer_allowed")
        if isinstance(policy, Mapping)
        else None
    )
    if transfer_allowed is not True:
        raise CloudBundleError(
            "authorization transfer posture does not allow a cloud shard copy"
        )
    paths = authorized_bundle_paths(verified, repo_root=root)
    forbidden = _forbidden_roots(request)
    for path in paths:
        resolved = Path(path).resolve()
        for forbidden_root in forbidden:
            if resolved == forbidden_root or forbidden_root in resolved.parents:
                raise CloudBundleError(
                    "raw corpus paths may never enter a cloud bundle"
                )
        lowered = resolved.as_posix().casefold()
        if any(fragment in lowered for fragment in _BLOCKED_NAME_FRAGMENTS):
            raise CloudBundleError(
                "blocked dataset content may never enter a cloud bundle"
            )
    output = Path(request.output_path).resolve()
    build_root = root / "build"
    if build_root not in output.parents:
        raise CloudBundleError(
            "cloud bundle output must live under the repository build tree"
        )
    quote = authorize_reproduction_quote_from_request(request, verified)
    manifest, files = build_bundle_manifest(
        paths,
        authorization=verified,
        quote=quote,
        repo_root=root,
        stage=request.stage,
    )
    if not request.dry_run:
        write_reproducible_tar(request.output_path, files, manifest)
    return manifest


def build_cloud_bundle_for_cli(
    *,
    stage: str,
    authorization_path: Path,
    quoted_hourly_usd: float,
    quoted_tax_inclusive_usd: float,
    output_path: Path,
    repo_root: Path,
    dry_run: bool,
) -> dict:
    """CLI adapter: primitives in, one guarded bundle request out."""

    quote = conservative_cloud_quote(
        stage,
        quoted_hourly_usd=quoted_hourly_usd,
        quoted_tax_inclusive_usd=quoted_tax_inclusive_usd,
    )
    request = CloudBundleRequest(
        repo_root=Path(repo_root),
        data_root=_default_data_root(),
        authorization_path=Path(authorization_path),
        output_path=Path(output_path),
        stage=stage,
        quote=quote,
        dry_run=bool(dry_run),
    )
    return build_cloud_bundle(request)


def build_cloud_reproduction_candidate(
    local_authorization_path: Path,
    *,
    local_gate_report_path: Path,
    output_path: Path,
    repo_root: Path,
    quote: CloudQuote | None = None,
    quoted_hourly_usd: float | None = None,
    quoted_tax_inclusive_usd: float | None = None,
    _tokenizer_loader=None,
) -> dict:
    """Derive a separate, nonauthorizing cloud candidate from the local final.

    The candidate binds the passed local-gate report and the quoted budget
    ceiling, switches the execution profile to ``cloud``, and points the
    source policy at the bundled shard. It stays a candidate: the exact
    operator finalization handshake is still required, and the full quote
    gate runs again at bundle time.
    """

    root = Path(repo_root).resolve()
    quote = _candidate_quote(quote, quoted_hourly_usd, quoted_tax_inclusive_usd)
    _validate_candidate_quote(quote)
    local = verify_foundation_authorization(
        local_authorization_path,
        repo_root=repo_root,
        registry_path=root / _REGISTRY_RELATIVE,
        _tokenizer_loader=_tokenizer_loader,
    )
    scope = _thaw(local.manifest).get("scope")
    if not isinstance(scope, Mapping):
        raise CloudBundleError("verified authorization scope is missing")
    if scope.get("execution_profile") == "cloud":
        raise CloudBundleError(
            "a cloud candidate must derive from the local authorization"
        )
    gate = _load_json(local_gate_report_path)
    if gate.get("local_gates_passed") is not True:
        raise CloudBundleError("cloud reproduction requires all local gates to pass")
    stage = scope.get("stage")
    expected_output = root / _CANDIDATES_RELATIVE / f"{stage}-cloud.json"
    if Path(output_path).resolve() != expected_output:
        raise CloudBundleError(
            "cloud candidate path must be exactly "
            f"candidates/{stage}-cloud.json under the repository build tree"
        )
    cloud_scope = copy.deepcopy(scope)
    cloud_scope["execution_profile"] = "cloud"
    policy = cloud_scope.get("source_data_policy")
    if not isinstance(policy, dict):
        raise CloudBundleError("local authorization source policy is missing")
    policy["root"] = "bundle://authorized-shard"
    policy["private_cloud_transfer_allowed"] = True
    cloud_scope["local_gate_report"] = artifact_binding(
        Path(local_gate_report_path),
        repo_root=Path(repo_root),
    )
    cloud_scope["budget"] = {
        "paid_compute_usd": 0,
        "cloud_jobs_used": 0,
        "paid_compute_ceiling_usd": quote.tax_inclusive_usd,
        "cloud_job_ceiling": 1,
        "cloud_lifetime_cap_usd": 45,
    }
    candidate = {
        "manifest_kind": "pneuma_foundation_training_authorization",
        "manifest_schema_version": "0.2.0",
        "authorization_status": "candidate",
        "scope": cloud_scope,
        "scope_digest": authorization_scope_digest(cloud_scope),
        "operator_approval": None,
    }
    _validate_manifest(candidate)
    expected_output.parent.mkdir(parents=True, exist_ok=True)
    write_atomic_json(expected_output, candidate)
    return candidate


__all__ = [
    "BUNDLE_MANIFEST_ARCNAME",
    "CloudBundleError",
    "CloudBundleRequest",
    "authorize_reproduction_quote_from_request",
    "authorized_bundle_paths",
    "build_bundle_manifest",
    "build_cloud_bundle",
    "build_cloud_bundle_for_cli",
    "build_cloud_reproduction_candidate",
    "conservative_cloud_quote",
    "write_reproducible_tar",
]
