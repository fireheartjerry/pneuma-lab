"""Execute the authorized Step 5B metadata-only inventory discovery action."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pneuma_lab.cloud.authorization_keys import canonical_bytes, canonical_ledger_digest
from pneuma_lab.cloud.inventory_discovery import inventory_plan_digest, validate_inventory_plan
from pneuma_lab.cloud.preparation_admission import require_preparation_admission


_LINK_NEXT = re.compile(r'<([^>]+)>;\s*rel="next"')
_ACCEPT_MANIFEST = ", ".join((
    "application/vnd.oci.image.manifest.v1+json",
    "application/vnd.docker.distribution.manifest.v2+json",
))


def _request_json(url: str, *, headers: dict[str, str] | None = None) -> tuple[Any, dict[str, str], bytes]:
    request = urllib.request.Request(url, headers={"User-Agent": "pneuma-step5b-inventory/0.1", **(headers or {})})
    with urllib.request.urlopen(request, timeout=30) as response:
        raw = response.read()
        return json.loads(raw), {key.lower(): value for key, value in response.headers.items()}, raw


def _hf_inventory(repository: str, revision: str, *, dataset: bool) -> dict[str, Any]:
    kind = "datasets" if dataset else "models"
    encoded = "/".join(urllib.parse.quote(part, safe="") for part in repository.split("/"))
    url = f"https://huggingface.co/api/{kind}/{encoded}/tree/{revision}?recursive=true&expand=true&limit=100"
    items: list[dict[str, Any]] = []
    pages: list[dict[str, Any]] = []
    while url:
        payload, headers, raw = _request_json(url)
        pages.append({"url": url, "sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw), "etag": headers.get("etag")})
        for item in payload:
            if item.get("type") != "file":
                continue
            lfs = item.get("lfs")
            identity = lfs.get("oid") if isinstance(lfs, dict) else item.get("oid")
            algorithm = "sha256" if isinstance(lfs, dict) else "git_sha1"
            size = lfs.get("size") if isinstance(lfs, dict) else item.get("size")
            items.append({"path": item["path"], "size_bytes": int(size), "identity_algorithm": algorithm, "identity": identity})
        link = headers.get("link", "")
        match = _LINK_NEXT.search(link)
        url = match.group(1) if match else ""
    return {"items": sorted(items, key=lambda item: item["path"]), "pages": pages}


def _github_inventory(repository: str, revision: str) -> dict[str, Any]:
    url = f"https://api.github.com/repos/{repository}/git/trees/{revision}?recursive=1"
    payload, headers, raw = _request_json(url, headers={"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"})
    if payload.get("truncated"):
        raise RuntimeError(f"GitHub returned a truncated tree for {repository}@{revision}")
    items = [
        {"path": item["path"], "type": item["type"], "mode": item["mode"], "size_bytes": item.get("size"), "identity_algorithm": "git_sha1", "identity": item["sha"]}
        for item in payload["tree"] if item["type"] in {"blob", "commit"}
    ]
    return {
        "items": sorted(items, key=lambda item: item["path"]),
        "pages": [{"url": url, "sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw), "etag": headers.get("etag")}],
    }


def _docker_inventory(repository: str, revision: str) -> dict[str, Any]:
    name = repository.removeprefix("docker.io/")
    token_url = "https://auth.docker.io/token?" + urllib.parse.urlencode({"service": "registry.docker.io", "scope": f"repository:{name}:pull"})
    token, _, _ = _request_json(token_url)
    url = f"https://registry-1.docker.io/v2/{name}/manifests/{revision}"
    payload, headers, raw = _request_json(url, headers={"Accept": _ACCEPT_MANIFEST, "Authorization": f"Bearer {token['token']}"})
    observed = hashlib.sha256(raw).hexdigest()
    if observed != revision.removeprefix("sha256:"):
        raise RuntimeError("OCI manifest bytes do not match the frozen digest")
    items = [{"role": "config", **payload["config"]}]
    items.extend({"role": "layer", **layer} for layer in payload["layers"])
    return {
        "items": items,
        "pages": [{"url": url, "sha256": observed, "size_bytes": len(raw), "etag": headers.get("etag"), "content_type": headers.get("content-type")}],
    }


def execute(plan: dict[str, Any]) -> dict[str, Any]:
    resolved = []
    for source in plan["sources"]:
        if source["service"] == "huggingface":
            evidence = _hf_inventory(source["repository"], source["revision"], dataset=source["role"] == "swe_dataset")
        elif source["service"] == "github":
            evidence = _github_inventory(source["repository"], source["revision"])
        elif source["service"] == "docker_registry":
            evidence = _docker_inventory(source["repository"], source["revision"])
        else:
            raise RuntimeError(f"unsupported service {source['service']!r}")
        resolved.append({**source, **evidence})
    return {
        "record_kind": "step5b_inventory_metadata",
        "schema_version": "0.1.0",
        "generated_timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "plan_sha256": inventory_plan_digest(plan),
        "sources": resolved,
    }


def require_execution_region(expected: str = "us-east-1") -> None:
    observed = os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION")
    if observed != expected:
        raise RuntimeError(f"execution region must be {expected!r}; observed {observed!r}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--signing-package", type=Path, required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--key-registry", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    plan = validate_inventory_plan(json.loads(args.plan.read_text(encoding="utf-8")))
    package = json.loads(args.signing_package.read_text(encoding="utf-8"))
    registry = json.loads(args.key_registry.read_text(encoding="utf-8"))
    admission = package["admission"]
    require_preparation_admission(
        package["envelope"], admission, key_registry=registry, ledger_path=args.ledger,
        expected_action_id=plan["action_id"], expected_action_class="input_retrieval",
        expected_provider="aws", expected_region="us-east-1",
        expected_manifest_sha256=inventory_plan_digest(plan), expected_input_lock_sha256=None,
        expected_projected_cost_usd=0.0, expected_max_retries=plan["max_retries"],
        spend_history_sha256=canonical_ledger_digest(args.ledger),
    )
    require_execution_region()
    result = execute(plan)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(canonical_bytes(result) + b"\n")
    print(json.dumps({"sha256": hashlib.sha256(canonical_bytes(result) + b"\n").hexdigest(), "sources": len(result["sources"])}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
