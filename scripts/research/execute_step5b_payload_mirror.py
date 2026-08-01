"""Execute one signed, bounded Step 5B payload mirror action."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pneuma_lab.cloud.authorization_keys import canonical_bytes, canonical_ledger_digest
from pneuma_lab.cloud.errors import CloudManifestError
from pneuma_lab.cloud.payload_inventory import validate_payload_manifest_semantics
from pneuma_lab.cloud.payload_mirror import (
    HostPolicyRedirect,
    host_is_allowed,
    object_key,
    source_url,
    upload_verified_object,
    validate_existing_head,
    verify_stored_object,
)
from pneuma_lab.cloud.payload_mirror_receipt import validate_payload_mirror_semantics
from pneuma_lab.cloud.payload_pricing import validate_payload_pricing_semantics
from pneuma_lab.cloud.payload_retrieval_plan import (
    executor_sources_digest,
    payload_retrieval_plan_digest,
    validate_payload_retrieval_plan_semantics,
)
from pneuma_lab.cloud.preparation_admission import require_preparation_admission
from pneuma_lab.cloud.step5b_lifecycle import step5b_lifecycle_receipt_digest


def require_execution_environment(sts: Any, s3: Any, *, expected_account: str, expected_region: str) -> dict[str, str]:
    region = os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION")
    if region != expected_region:
        raise CloudManifestError(f"execution region must be {expected_region}; observed {region!r}")
    identity = sts.get_caller_identity()
    if identity.get("Account") != expected_account:
        raise CloudManifestError("AWS caller identity does not match the signed account")
    for client, label in ((sts, "STS"), (s3, "S3")):
        host = urllib.parse.urlsplit(client.meta.endpoint_url).hostname or ""
        expected_host = "sts.us-east-1.amazonaws.com" if label == "STS" else "pneuma-phase-b-892077329800.s3.us-east-1.amazonaws.com"
        # Botocore's S3 client normally exposes the regional path-style host;
        # bucket operations become virtual-host requests after signing.
        if label == "S3" and host == "s3.us-east-1.amazonaws.com":
            continue
        if host != expected_host:
            raise CloudManifestError(f"{label} endpoint is outside the signed execution boundary: {host}")
    return {"account_id": identity["Account"], "arn": identity["Arn"], "region": region}


def require_bucket_controls(s3: Any, *, bucket: str, prefix: str, retention_days: int) -> dict[str, Any]:
    encryption = s3.get_bucket_encryption(Bucket=bucket)
    algorithms = {
        rule["ApplyServerSideEncryptionByDefault"]["SSEAlgorithm"]
        for rule in encryption["ServerSideEncryptionConfiguration"]["Rules"]
    }
    if algorithms != {"AES256"}:
        raise CloudManifestError("artifact bucket encryption is not exactly AES256")
    if s3.get_bucket_versioning(Bucket=bucket).get("Status") != "Enabled":
        raise CloudManifestError("artifact bucket versioning is not enabled")
    public = s3.get_public_access_block(Bucket=bucket)["PublicAccessBlockConfiguration"]
    required_public = {"BlockPublicAcls", "IgnorePublicAcls", "BlockPublicPolicy", "RestrictPublicBuckets"}
    if set(public) != required_public or not all(public.values()):
        raise CloudManifestError("artifact bucket public-access block is incomplete")
    ownership = s3.get_bucket_ownership_controls(Bucket=bucket)["OwnershipControls"]["Rules"]
    if ownership != [{"ObjectOwnership": "BucketOwnerEnforced"}]:
        raise CloudManifestError("artifact bucket ownership controls are not exact")

    expected_prefix = prefix.rsplit("/", 1)[0] + "/"
    lifecycle = s3.get_bucket_lifecycle_configuration(Bucket=bucket)["Rules"]
    matches = []
    for rule in lifecycle:
        filtered = rule.get("Filter", {})
        rule_prefix = filtered.get("Prefix")
        if rule.get("ID") == "expire-step5b-payloads" and rule.get("Status") == "Enabled" and rule_prefix == expected_prefix:
            matches.append(rule)
    if len(matches) != 1:
        raise CloudManifestError("exact Step 5B lifecycle rule is absent or ambiguous")
    rule = matches[0]
    if int(rule.get("Expiration", {}).get("Days", retention_days + 1)) > retention_days:
        raise CloudManifestError("Step 5B current-version retention exceeds the signed maximum")
    if int(rule.get("NoncurrentVersionExpiration", {}).get("NoncurrentDays", 31)) > 30:
        raise CloudManifestError("Step 5B noncurrent retention exceeds 30 days")
    if int(rule.get("AbortIncompleteMultipartUpload", {}).get("DaysAfterInitiation", 8)) > 7:
        raise CloudManifestError("Step 5B multipart-abort retention exceeds 7 days")
    return {"encryption": "AES256", "versioning": "Enabled", "lifecycle_rule_id": rule["ID"], "lifecycle_prefix": expected_prefix}


def _docker_token(opener: Any, repository: str, allowed_hosts: list[str]) -> str:
    name = repository.removeprefix("docker.io/")
    url = "https://auth.docker.io/token?" + urllib.parse.urlencode({"service": "registry.docker.io", "scope": f"repository:{name}:pull"})
    response = opener.open(urllib.request.Request(url, headers={"User-Agent": "pneuma-step5b-payload/0.1"}), timeout=30)
    try:
        final_host = urllib.parse.urlsplit(response.geturl()).hostname or ""
        if not host_is_allowed(final_host, allowed_hosts):
            raise CloudManifestError("Docker token response escaped the signed host boundary")
        return json.loads(response.read())["token"]
    finally:
        response.close()


def open_upstream(item: dict[str, Any], allowed_hosts: list[str], docker_tokens: dict[str, str]) -> Any:
    opener = urllib.request.build_opener(HostPolicyRedirect(allowed_hosts))
    url = source_url(item)
    initial_host = urllib.parse.urlsplit(url).hostname or ""
    if not host_is_allowed(initial_host, allowed_hosts):
        raise CloudManifestError("upstream URL is outside the signed host boundary")
    headers = {"User-Agent": "pneuma-step5b-payload/0.1", "Accept-Encoding": "identity"}
    if item["service"] == "docker_registry":
        repository = item["repository"]
        if repository not in docker_tokens:
            docker_tokens[repository] = _docker_token(opener, repository, allowed_hosts)
        token = docker_tokens[repository]
        headers["Authorization"] = f"Bearer {token}"
    response = opener.open(urllib.request.Request(url, headers=headers), timeout=60)
    final_host = urllib.parse.urlsplit(response.geturl()).hostname or ""
    if not host_is_allowed(final_host, allowed_hosts):
        response.close()
        raise CloudManifestError("payload response escaped the signed host boundary")
    return response


def _head_or_none(s3: Any, client_error: type[BaseException], *, bucket: str, key: str) -> dict[str, Any] | None:
    try:
        return s3.head_object(Bucket=bucket, Key=key)
    except client_error as exc:
        status = int(exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode", 0))
        code = str(exc.response.get("Error", {}).get("Code", ""))
        if status == 404 or code in {"404", "NoSuchKey", "NotFound"}:
            return None
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--pricing", type=Path, required=True)
    parser.add_argument("--signing-package", type=Path, required=True)
    parser.add_argument("--lifecycle-receipt", type=Path, required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--key-registry", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    manifest = validate_payload_manifest_semantics(json.loads(args.manifest.read_text(encoding="utf-8")))
    plan = validate_payload_retrieval_plan_semantics(json.loads(args.plan.read_text(encoding="utf-8")), manifest)
    if executor_sources_digest(Path.cwd()) != plan["executor_sources_sha256"]:
        raise CloudManifestError("executor source surface does not match the signed payload plan")
    pricing = validate_payload_pricing_semantics(json.loads(args.pricing.read_text(encoding="utf-8")), manifest)
    if hashlib.sha256(args.pricing.read_bytes()).hexdigest() != plan["pricing_receipt_sha256"]:
        raise CloudManifestError("payload plan is not bound to the exact pricing receipt bytes")
    if plan["status"] != "ready_for_signature" or not pricing["within_ceiling"]:
        raise CloudManifestError("payload plan is not price-qualified for signature")
    lifecycle_receipt = json.loads(args.lifecycle_receipt.read_text(encoding="utf-8"))
    if step5b_lifecycle_receipt_digest(lifecycle_receipt, plan) != plan["lifecycle_live_receipt_sha256"]:
        raise CloudManifestError("payload plan is not bound to the exact live lifecycle receipt bytes")

    package = json.loads(args.signing_package.read_text(encoding="utf-8"))
    registry = json.loads(args.key_registry.read_text(encoding="utf-8"))
    require_preparation_admission(
        package["envelope"], package["admission"], key_registry=registry, ledger_path=args.ledger,
        expected_action_id=plan["action_id"], expected_action_class="input_retrieval",
        expected_provider=plan["provider"], expected_region=plan["region"],
        expected_manifest_sha256=payload_retrieval_plan_digest(plan), expected_input_lock_sha256=None,
        expected_projected_cost_usd=float(pricing["projected_cost_usd"]), expected_max_retries=plan["max_retries"],
        spend_history_sha256=canonical_ledger_digest(args.ledger),
    )

    import boto3  # type: ignore[import-untyped]
    from botocore.exceptions import ClientError  # type: ignore[import-untyped]

    session = boto3.session.Session(region_name=plan["region"])
    sts = session.client("sts", region_name=plan["region"])
    s3 = session.client("s3", region_name=plan["region"])
    identity = require_execution_environment(sts, s3, expected_account=plan["account_id"], expected_region=plan["region"])
    destination = plan["destination"]
    controls = require_bucket_controls(s3, bucket=destination["bucket"], prefix=destination["prefix"], retention_days=plan["retention_days"])

    # Five S3 bucket-control reads occurred above: encryption, versioning,
    # public access, ownership, and lifecycle.
    counters = {"tier1_put": 0, "tier1_list": 0, "tier2_get": 5}
    receipts = []
    docker_tokens: dict[str, str] = {}
    for item in manifest["objects"]:
        if not item["retrieval_required"]:
            continue
        key = object_key(destination["prefix"], item)
        head = _head_or_none(s3, ClientError, bucket=destination["bucket"], key=key)
        counters["tier2_get"] += 1
        if head is None:
            response = open_upstream(item, plan["allowed_hosts"], docker_tokens)
            try:
                length = response.headers.get("Content-Length")
                if length is None:
                    raise CloudManifestError("payload response has no Content-Length")
                uploaded = upload_verified_object(
                    item, response, s3, bucket=destination["bucket"], key=key,
                    declared_size=int(length), content_encoding=response.headers.get("Content-Encoding"),
                )
                counters["tier1_put"] += uploaded["put_requests"]
                version_id = uploaded["version_id"]
            finally:
                response.close()
        else:
            version_id = validate_existing_head(item, head)
        stored = verify_stored_object(item, s3, bucket=destination["bucket"], key=key, version_id=version_id)
        counters["tier2_get"] += stored["get_requests"]
        receipts.append({
            "object_id": item["object_id"], "consumers": item["consumers"], "key": key,
            "version_id": stored["version_id"], "etag": stored["etag"],
            "upstream_identity_algorithm": item["identity_algorithm"], "upstream_identity": item["identity"],
            "payload_sha256": stored["payload_sha256"], "size_bytes": stored["size_bytes"],
        })

    # The final receipt is one PUT followed by one independent GET; account for
    # both before sealing the receipt that reports these counts.
    counters["tier1_put"] += 1
    counters["tier2_get"] += 1
    for kind, observed in counters.items():
        if observed > pricing["request_ceilings"][kind]:
            raise CloudManifestError(f"{kind} request count exceeds the price-qualified ceiling")
    receipt = {
        "record_kind": "cloud_payload_mirror_receipt", "schema_version": "0.1.0",
        "generated_timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "plan_sha256": payload_retrieval_plan_digest(plan), "payload_manifest_sha256": plan["payload_manifest_sha256"],
        "pricing_receipt_sha256": plan["pricing_receipt_sha256"], "identity": identity,
        "bucket_controls": controls, "request_counts": counters,
        "object_count": len(receipts), "payload_bytes": sum(item["size_bytes"] for item in receipts),
        "objects": sorted(receipts, key=lambda item: item["object_id"]),
    }
    receipt = validate_payload_mirror_semantics(receipt, plan, manifest, pricing)
    raw = canonical_bytes(receipt) + b"\n"
    receipt_key = f"{destination['prefix']}/receipts/final.json"
    uploaded_receipt = s3.put_object(
        Bucket=destination["bucket"], Key=receipt_key, Body=raw, ContentLength=len(raw),
        ChecksumSHA256=base64.b64encode(hashlib.sha256(raw).digest()).decode("ascii"),
        ServerSideEncryption="AES256", IfNoneMatch="*",
    )
    reread = s3.get_object(Bucket=destination["bucket"], Key=receipt_key, VersionId=uploaded_receipt.get("VersionId"))
    try:
        if reread["Body"].read() != raw:
            raise CloudManifestError("published final receipt failed independent S3 byte verification")
    finally:
        reread["Body"].close()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(raw)
    print(json.dumps({"sha256": hashlib.sha256(raw).hexdigest(), "objects": len(receipts), "bytes": receipt["payload_bytes"], "request_counts": counters}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
